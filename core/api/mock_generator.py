"""
mock_generator.py — single source of truth for mock generation and
corpus building.

Phase 2 extensions:
  - _infer_schema()     : uses genson to union JSON schemas across all
                          observed samples for an endpoint
  - status_codes_seen   : full set of status codes seen per endpoint group
  - auth_pattern        : Bearer / ApiKey / Cookie presence per group
  - build_mock_corpus() : richer output used by openapi_spec_builder.py
                          and discovery_inventory.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

import yaml

try:
    from genson import SchemaBuilder
    _GENSON_AVAILABLE = True
except ImportError:
    _GENSON_AVAILABLE = False


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def _find_traffic_inventory(workspace_root=None) -> Path | None:
    root = Path(workspace_root or ".").resolve()
    candidates = [
        root / "keploy" / "traffic" / "traffic-inventory.json",
        root / "keploy" / "tests" / "keploy" / "traffic-inventory.yaml",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def load_captured_requests(workspace_root=None) -> list[dict]:
    path = _find_traffic_inventory(workspace_root)
    if not path:
        return []
    try:
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            data = json.loads(text)
        else:
            data = yaml.safe_load(text) or {}
        if isinstance(data, list):
            return data
        cp = data.get("capture_profile", {})
        reqs = (
            cp.get("captured_requests")
            or data.get("captured_requests")
            or []
        )
        return reqs if isinstance(reqs, list) else []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Path generalization
# ---------------------------------------------------------------------------

_ID_RE = re.compile(
    r"^([0-9]+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[0-9a-f]{24,})$",
    re.IGNORECASE,
)


def generalize_path(path: str) -> str:
    """Replace numeric/UUID path segments with {param}."""
    parts = path.split("/")
    generalized = []
    for part in parts:
        clean = part.split("?")[0]
        if _ID_RE.match(clean):
            generalized.append("{param}")
        else:
            generalized.append(part)
    result = "/".join(generalized)
    if "?" in path:
        result = result.split("?")[0] + "?" + path.split("?", 1)[1]
    return result


def is_templated(path: str) -> bool:
    return "{param}" in generalize_path(path)


# ---------------------------------------------------------------------------
# API candidate filter
# ---------------------------------------------------------------------------

_STATIC_EXTS = {
    ".css", ".js", ".map", ".ico", ".png", ".jpg", ".jpeg", ".gif",
    ".svg", ".webp", ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".webm",
}

_API_RESOURCE_TYPES = {"fetch", "xhr", "websocket"}

_API_PATH_MARKERS = (
    "/api/", "/v1/", "/v2/", "/v3/", "/graphql", "/auth", "/login",
    "/session", "/token", "/user", "/order", "/product", "/admin",
)


def is_api_candidate(entry: dict) -> bool:
    resource_type = str(entry.get("resource_type") or "").lower()
    if resource_type in _API_RESOURCE_TYPES:
        return True
    path = str(entry.get("path") or "").lower().split("?")[0]
    if any(path.endswith(ext) for ext in _STATIC_EXTS):
        return False
    if entry.get("is_navigation") and not any(m in path for m in _API_PATH_MARKERS):
        return False
    return any(m in path for m in _API_PATH_MARKERS)


# ---------------------------------------------------------------------------
# Schema fingerprinting (for drift detection)
# ---------------------------------------------------------------------------

def schema_fingerprint(obj, prefix: str = "") -> set[str]:
    """Return set of dotted key paths for a JSON body."""
    paths: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            full = f"{prefix}.{k}" if prefix else k
            paths.add(full)
            paths |= schema_fingerprint(v, full)
    elif isinstance(obj, list) and obj:
        paths |= schema_fingerprint(obj[0], prefix + "[]")
    return paths


# ---------------------------------------------------------------------------
# Phase 2: Schema inference via genson
# ---------------------------------------------------------------------------

def _infer_schema(samples: list) -> dict | None:
    """
    Build a union JSON Schema from all sample objects using genson.
    Returns None if genson is unavailable or no valid samples exist.
    """
    if not _GENSON_AVAILABLE:
        return None
    objects = [s for s in samples if isinstance(s, (dict, list))]
    if not objects:
        return None
    try:
        builder = SchemaBuilder()
        for obj in objects[:20]:   # cap at 20 samples to keep it fast
            builder.add_object(obj)
        return builder.to_schema()
    except Exception:
        return None


def _detect_auth_pattern(samples: list[dict]) -> str:
    """
    Inspect request headers across samples to identify auth pattern.
    Returns: "bearer" | "apikey" | "cookie" | "none"
    """
    for sample in samples:
        headers = sample.get("headers") or {}
        h_lower = {k.lower(): str(v) for k, v in headers.items()}
        auth_val = h_lower.get("authorization", "")
        if auth_val.lower().startswith("bearer") or auth_val.startswith("be**"):
            return "bearer"
        if "x-api-key" in h_lower or "api-key" in h_lower:
            return "apikey"
        if "cookie" in h_lower:
            return "cookie"
    return "none"


# ---------------------------------------------------------------------------
# Phase 2: build_mock_corpus() — extended generate_mocks()
# ---------------------------------------------------------------------------

def build_mock_corpus(workspace_root=None) -> list[dict]:
    """
    Full corpus builder — extends generate_mocks() with:
      - request_schema   : inferred JSON Schema of request body (genson)
      - response_schema  : inferred JSON Schema of response body (genson)
      - status_codes_seen: full set of status codes observed
      - auth_pattern     : "bearer" | "apikey" | "cookie" | "none"

    Used by openapi_spec_builder.py and discovery_inventory.py.
    """
    requests_raw = load_captured_requests(workspace_root)
    api_entries = [e for e in requests_raw if is_api_candidate(e)]

    groups: dict[tuple, list[dict]] = {}
    for entry in api_entries:
        method = str(entry.get("method") or "GET").upper()
        path = str(entry.get("path") or "/")
        gen_path = generalize_path(path)
        key = (method, gen_path)
        groups.setdefault(key, []).append(entry)

    corpus = []
    for (method, gen_path), samples in groups.items():
        best = next((s for s in samples if s.get("response_body")), samples[0])

        latencies = [
            s["response_time_ms"]
            for s in samples
            if isinstance(s.get("response_time_ms"), (int, float)) and s["response_time_ms"] > 0
        ]
        median_latency = sorted(latencies)[len(latencies) // 2] if latencies else None

        status_codes = [s.get("status") for s in samples if s.get("status")]
        modal_status = max(set(status_codes), key=status_codes.count) if status_codes else 200
        status_codes_seen = sorted(set(status_codes))

        resp_bodies = [s.get("response_body") for s in samples if s.get("response_body")]
        req_bodies = [s.get("request_body") for s in samples if s.get("request_body")]

        resp_body = best.get("response_body")
        req_body = best.get("request_body")

        # Phase 2 additions
        response_schema = _infer_schema(resp_bodies)
        request_schema = _infer_schema(req_bodies)
        auth_pattern = _detect_auth_pattern(samples)

        corpus.append({
            "method": method,
            "path": gen_path,
            "original_path": str(best.get("path") or gen_path),
            "is_templated": is_templated(gen_path),
            "host": str(best.get("host") or ""),
            "capture_source": str(best.get("capture_source") or "playwright"),
            "request": {
                "body": req_body,
                "content_type": best.get("request_content_type", ""),
                "schema": request_schema,
            },
            "response": {
                "status": modal_status,
                "body": resp_body,
                "content_type": best.get("response_content_type", "application/json"),
                "median_latency_ms": round(median_latency, 1) if median_latency else None,
                "schema": response_schema,
            },
            "status_codes_seen": status_codes_seen,
            "auth_pattern": auth_pattern,
            "schema_fingerprint": sorted(schema_fingerprint(resp_body)) if isinstance(resp_body, dict) else [],
            "sample_count": len(samples),
            "has_real_body": resp_body is not None,
            "has_inferred_schema": response_schema is not None,
        })

    corpus.sort(key=lambda e: (e["method"], e["path"]))
    return corpus


# ---------------------------------------------------------------------------
# generate_mocks() — thin wrapper kept for backward compat
# ---------------------------------------------------------------------------

def generate_mocks(workspace_root=None) -> list[dict]:
    """Backward-compatible alias for build_mock_corpus()."""
    return build_mock_corpus(workspace_root)


# ---------------------------------------------------------------------------
# Write mocks.yaml
# ---------------------------------------------------------------------------

def write_mocks_yaml(mocks: list[dict], workspace_root=None) -> str:
    root = Path(workspace_root or ".").resolve()
    out_path = root / "keploy" / "mocks" / "mocks.yaml"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump({"mocks": mocks}, f, sort_keys=False, allow_unicode=True)
    return str(out_path)


def build_and_write_mocks(workspace_root=None) -> tuple[list[dict], str]:
    """Returns (corpus_list, output_path)."""
    corpus = build_mock_corpus(workspace_root)
    if not corpus:
        return [], ""
    path = write_mocks_yaml(corpus, workspace_root)
    return corpus, path



# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def _find_traffic_inventory(workspace_root=None) -> Path | None:
    root = Path(workspace_root or ".").resolve()
    candidates = [
        root / "keploy" / "traffic" / "traffic-inventory.json",
        root / "keploy" / "tests" / "keploy" / "traffic-inventory.yaml",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def load_captured_requests(workspace_root=None) -> list[dict]:
    path = _find_traffic_inventory(workspace_root)
    if not path:
        return []
    try:
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            data = json.loads(text)
        else:
            data = yaml.safe_load(text) or {}
        # Support both raw list and nested structure
        if isinstance(data, list):
            return data
        cp = data.get("capture_profile", {})
        reqs = (
            cp.get("captured_requests")
            or data.get("captured_requests")
            or []
        )
        return reqs if isinstance(reqs, list) else []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Path generalization
# ---------------------------------------------------------------------------

_ID_RE = re.compile(
    r"^([0-9]+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[0-9a-f]{24,})$",
    re.IGNORECASE,
)


def generalize_path(path: str) -> str:
    """Replace numeric/UUID path segments with {param}."""
    parts = path.split("/")
    generalized = []
    for part in parts:
        clean = part.split("?")[0]  # strip query from last segment
        if _ID_RE.match(clean):
            generalized.append("{param}")
        else:
            generalized.append(part)
    result = "/".join(generalized)
    # Preserve query string on last segment
    if "?" in path:
        result = result.split("?")[0] + "?" + path.split("?", 1)[1]
    return result


def is_templated(path: str) -> bool:
    return "{param}" in generalize_path(path)


# ---------------------------------------------------------------------------
# API candidate filter
# ---------------------------------------------------------------------------

_STATIC_EXTS = {
    ".css", ".js", ".map", ".ico", ".png", ".jpg", ".jpeg", ".gif",
    ".svg", ".webp", ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".webm",
}

_API_RESOURCE_TYPES = {"fetch", "xhr", "websocket"}

_API_PATH_MARKERS = (
    "/api/", "/v1/", "/v2/", "/v3/", "/graphql", "/auth", "/login",
    "/session", "/token", "/user", "/order", "/product", "/admin",
)


def is_api_candidate(entry: dict) -> bool:
    resource_type = str(entry.get("resource_type") or "").lower()
    if resource_type in _API_RESOURCE_TYPES:
        return True

    path = str(entry.get("path") or "").lower().split("?")[0]
    # Skip static assets
    if any(path.endswith(ext) for ext in _STATIC_EXTS):
        return False
    # Skip navigations unless they look like API paths
    if entry.get("is_navigation") and not any(m in path for m in _API_PATH_MARKERS):
        return False

    return any(m in path for m in _API_PATH_MARKERS)


# ---------------------------------------------------------------------------
# Schema fingerprinting (for drift detection)
# ---------------------------------------------------------------------------

def schema_fingerprint(obj, prefix: str = "") -> set[str]:
    """Return set of dotted key paths for a JSON body."""
    paths: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            full = f"{prefix}.{k}" if prefix else k
            paths.add(full)
            paths |= schema_fingerprint(v, full)
    elif isinstance(obj, list) and obj:
        paths |= schema_fingerprint(obj[0], prefix + "[]")
    return paths


# ---------------------------------------------------------------------------
# Core: generate mocks
# ---------------------------------------------------------------------------

def generate_mocks(workspace_root=None) -> list[dict]:
    """
    Returns a list of mock entries, deduplicated by (method, generalized_path).
    Each entry has:
      - method, path, generalized_path
      - request_body, request_content_type
      - status, response_body, response_content_type
      - response_time_ms (median across samples)
      - sample_count, has_real_body
    """
    requests_raw = load_captured_requests(workspace_root)
    api_entries = [e for e in requests_raw if is_api_candidate(e)]

    # Group by (method, generalized_path)
    groups: dict[tuple, list[dict]] = {}
    for entry in api_entries:
        method = str(entry.get("method") or "GET").upper()
        path = str(entry.get("path") or "/")
        gen_path = generalize_path(path)
        key = (method, gen_path)
        groups.setdefault(key, []).append(entry)

    mocks = []
    for (method, gen_path), samples in groups.items():
        # Pick the best sample — prefer ones with a real response body
        best = next((s for s in samples if s.get("response_body")), samples[0])

        latencies = [
            s["response_time_ms"]
            for s in samples
            if isinstance(s.get("response_time_ms"), (int, float)) and s["response_time_ms"] > 0
        ]
        median_latency = sorted(latencies)[len(latencies) // 2] if latencies else None

        status_codes = [s.get("status") for s in samples if s.get("status")]
        status = max(set(status_codes), key=status_codes.count) if status_codes else 200

        resp_body = best.get("response_body")
        req_body = best.get("request_body")

        mocks.append({
            "method": method,
            "path": gen_path,
            "original_path": str(best.get("path") or gen_path),
            "is_templated": is_templated(gen_path),
            "request": {
                "body": req_body,
                "content_type": best.get("request_content_type", ""),
            },
            "response": {
                "status": status,
                "body": resp_body,
                "content_type": best.get("response_content_type", "application/json"),
                "median_latency_ms": round(median_latency, 1) if median_latency else None,
            },
            "schema_fingerprint": sorted(schema_fingerprint(resp_body)) if isinstance(resp_body, dict) else [],
            "sample_count": len(samples),
            "has_real_body": resp_body is not None,
            "status_variants": sorted(set(status_codes)),
        })

    # Sort by method + path for deterministic output
    mocks.sort(key=lambda m: (m["method"], m["path"]))
    return mocks


# ---------------------------------------------------------------------------
# Write mocks.yaml
# ---------------------------------------------------------------------------

def write_mocks_yaml(mocks: list[dict], workspace_root=None) -> str:
    root = Path(workspace_root or ".").resolve()
    out_path = root / "keploy" / "mocks" / "mocks.yaml"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump({"mocks": mocks}, f, sort_keys=False, allow_unicode=True)
    return str(out_path)


# ---------------------------------------------------------------------------
# Convenience: generate + write in one call
# ---------------------------------------------------------------------------

def build_and_write_mocks(workspace_root=None) -> tuple[list[dict], str]:
    """Returns (mocks_list, output_path)."""
    mocks = generate_mocks(workspace_root)
    if not mocks:
        return [], ""
    path = write_mocks_yaml(mocks, workspace_root)
    return mocks, path
