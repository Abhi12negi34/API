from __future__ import annotations

from collections import Counter
import os
from pathlib import Path
from urllib.parse import urlparse

import yaml


DISCOVERY_KEYS = (
    "discovered_apis",
    "generated_traces",
    "baseline",
    "traces",
    "captured_requests",
    "requests",
    "traffic",
    "network_events",
)

API_VERSION_SEGMENTS = {f"v{i}" for i in range(1, 11)}

# FIX 4: Extended static extensions to include .webp, .htm, .html which
# were previously being added to discovered APIs as "Discovered API endpoint"
STATIC_EXTENSIONS = {
    ".css",
    ".gif",
    ".htm",   # FIX 4 — was missing, caused /howto/tryhow_js_slideshow_ifr.htm to appear as API
    ".html",  # FIX 4
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".map",
    ".mp3",
    ".mp4",
    ".png",
    ".svg",
    ".ttf",
    ".webm",
    ".webp",  # FIX 4 — was missing, caused /codeeditor.webp etc to appear as APIs
    ".woff",
    ".woff2",
}

PAGE_EXTENSIONS = {
    ".asp",
    ".aspx",
    ".cgi",
    ".cfm",
    ".cfml",
    ".do",
    ".htm",
    ".html",
    ".jsp",
    ".php",
}

API_ROOT_SEGMENTS = {
    "api",
    "auth",
    "cart",
    "checkout",
    "graphql",
    "health",
    "metrics",
    "order",
    "orders",
    "profile",
    "search",
    "session",
    "user",
    "webhook",
    "admin",
}

SERVICE_SUBDOMAIN_PREFIXES = {
    "api",
    "app",
    "auth",
    "backend",
    "m",
    "mobile",
    "service",
    "services",
    "www",
}

# FIX 4: Extended noise markers to filter beacon/tracking endpoints
NOISE_MARKERS = (
    "g/collect",
    "gtag/js",
    "analytics",
    "beacon",
    "google-analytics",
    "recaptcha",
    "ads/",
    "pixel",
    "crossfire.js",
    "consent-require",
    "fastcmp",
    "cdn-cgi",
)

RESOURCE_TYPE_NOISE = {
    "document",
    "image",
    "manifest",
    "media",
    "script",
    "stylesheet",
    "font",
    "ping",        # FIX 4 — ping is analytics/beacon traffic
    "eventsource", # not noise per se but rarely a testable API
}

# FIX 4: Resource types that indicate real API calls
RESOURCE_TYPE_API = {
    "fetch",
    "xhr",
    "websocket",
}


def _workspace_root(workspace_root=None) -> Path:
    return Path(workspace_root or Path.cwd()).resolve()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = str(os.getenv(name, str(default))).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _artifact_directories(workspace_root=None) -> list[Path]:
    root = _workspace_root(workspace_root)
    return [
        root / "keploy" / "tests" / "keploy",
        root / "keploy" / "traffic",
    ]

def classify_api_quality(api):
    source = api.get("source_file", "")

    if "discovery-baseline" in source:
        return "high"

    if "traffic" in source:
        return "medium"

    if "pattern-inference" in source:
        return "low"

    return "unknown"

def iter_artifact_files(workspace_root=None) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()

    for directory in _artifact_directories(workspace_root):
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if path.suffix.lower() not in {".yaml", ".yml", ".json"}:
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append(resolved)

    return sorted(files)


def _is_baseline_artifact(path: str | Path) -> bool:
    return "discovery-baseline" in Path(path).name.lower()


def _load_artifact(path: Path):
    with open(path, "r", encoding="utf-8") as handle:
        if path.suffix.lower() == ".json":
            import json
            return json.load(handle)
        return yaml.safe_load(handle)


def _normalize_route(value) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "/"
    if raw.startswith(("http://", "https://")):
        parsed = urlparse(raw)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        return path
    if " " in raw and raw.split(" ", 1)[0].isalpha():
        _, maybe_path = raw.split(" ", 1)
        if maybe_path.startswith("/"):
            raw = maybe_path
    return raw if raw.startswith("/") else f"/{raw.lstrip('/')}"


def _normalize_full_url(base_url: str, value: str) -> str:
    raw = str(value or "").strip()
    base = str(base_url or "").strip().rstrip("/")
    if not raw:
        return base
    if raw.startswith(("http://", "https://")):
        return raw
    if base:
        # Use origin (scheme+host) only — don't prepend the path component of base_url
        parsed = urlparse(base)
        origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else base
        normalized = _normalize_route(raw)
        return f"{origin}{normalized}"
    return _normalize_route(raw)


def _strip_query_string(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.startswith(("http://", "https://")):
        parsed = urlparse(raw)
        clean_path = parsed.path or "/"
        if parsed.fragment:
            clean_path = f"{clean_path}#{parsed.fragment}"
        return parsed._replace(query="").geturl().split("?", 1)[0]
    return raw.split("?", 1)[0]


def _canonicalize_full_url(base_url: str, value: str) -> str:
    return _strip_query_string(_normalize_full_url(base_url, value))


def _extract_host(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if not raw.startswith(("http://", "https://")):
        return ""
    parsed = urlparse(raw)
    return parsed.netloc.lower()


def _normalize_host(value: str) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""

    if raw.startswith(("http://", "https://")):
        parsed = urlparse(raw)
        raw = parsed.netloc.lower()

    raw = raw.split("@")[-1].split(":", 1)[0]
    if raw.startswith("www."):
        raw = raw[4:]
    return raw


def _host_parts(value: str) -> tuple[str, str]:
    host = _normalize_host(value)
    if not host:
        return "", ""

    parts = host.split(".")
    if len(parts) >= 2:
        base = ".".join(parts[-2:])
    else:
        base = host

    prefix = parts[0] if len(parts) > 2 else ""
    return prefix, base


def _same_site_host(left: str, right: str) -> bool:
    left_host = _normalize_host(left)
    right_host = _normalize_host(right)
    if not left_host or not right_host:
        return False
    if left_host == right_host:
        return True

    left_prefix, left_base = _host_parts(left_host)
    right_prefix, right_base = _host_parts(right_host)
    if left_base != right_base:
        return False

    return (
        left_prefix in SERVICE_SUBDOMAIN_PREFIXES
        or right_prefix in SERVICE_SUBDOMAIN_PREFIXES
    )


def _looks_like_api_path(path: str) -> bool:
    """
    Returns True if the path looks like a real API endpoint rather than a
    static asset, page route, or tracking beacon.
    """
    normalized = _normalize_route(path).lower()

    # Skip homepage
    if normalized in {"", "/"}:
        return False

    # FIX 4: Skip static file extensions
    clean_path = normalized.split("?")[0]
    for ext in PAGE_EXTENSIONS:
        if clean_path.endswith(ext):
            return False
    for ext in STATIC_EXTENSIONS:
        if clean_path.endswith(ext):
            return False

    # FIX 4: Skip analytics/beacon noise
    for marker in NOISE_MARKERS:
        if marker in normalized:
            return False

    return True


def _path_has_api_hint(path: str) -> bool:
    normalized = _normalize_route(path).lower().split("?")[0]
    parts = [part for part in normalized.split("/") if part]
    if not parts:
        return False

    for part in parts[:3]:
        if part in API_ROOT_SEGMENTS or part in API_VERSION_SEGMENTS:
            return True

    if "graphql" in normalized:
        return True

    if normalized.startswith("/api") or "/api/" in normalized:
        return True

    if "/rest/" in normalized or normalized.startswith("/rest"):
        return True

    if "/rpc/" in normalized or normalized.startswith("/rpc"):
        return True

    return False


def _response_content_type(entry: dict) -> str:
    headers = entry.get("response_headers") or entry.get("headers") or {}
    if isinstance(headers, dict):
        for key in ("content-type", "Content-Type"):
            value = str(headers.get(key) or "").strip().lower()
            if value:
                return value
    return str(entry.get("content_type") or "").strip().lower()


def _resource_type(entry: dict) -> str:
    return str(entry.get("resource_type") or entry.get("type") or "").strip().lower()


def _is_static_asset(path: str, resource_type: str) -> bool:
    normalized = _normalize_route(path).lower()
    clean_path = normalized.split("?")[0]

    # FIX 4: Use the complete STATIC_EXTENSIONS set (now includes .webp, .htm, .html)
    for ext in STATIC_EXTENSIONS:
        if clean_path.endswith(ext):
            return True

    # Remove analytics noise
    for marker in NOISE_MARKERS:
        if marker in normalized:
            return True

    return False


def _entry_target_url(entry: dict, fallback_target_url: str) -> str:
    for key in ("target_url", "full_url", "url", "path", "endpoint"):
        value = str(entry.get(key) or "").strip()
        if value:
            if value.startswith(("http://", "https://")):
                return value
            if key in {"url", "full_url"}:
                return _normalize_full_url(fallback_target_url, value)
    return str(fallback_target_url or "").strip()


def _classify_entry(entry: dict, requested_target_url: str, aggressive: bool = False) -> dict:
    requested_host = _extract_host(requested_target_url)
    observed_url = _entry_target_url(entry, requested_target_url)
    canonical_observed_url = _strip_query_string(observed_url)
    observed_host = _extract_host(observed_url)

    path = _strip_query_string(
        _normalize_route(entry.get("path") or entry.get("endpoint") or entry.get("url") or "")
    )

    method = str(
        entry.get("method")
        or entry.get("request", {}).get("method")
        or "GET"
    ).upper()

    resource_type = _resource_type(entry)
    content_type = _response_content_type(entry)
    clean_path = path.split("?")[0].lower()
    page_like = any(clean_path.endswith(ext) for ext in PAGE_EXTENSIONS)
    query_based = "?" in observed_url and not page_like and not _is_static_asset(path, resource_type)

    # Remove foreign hosts
    if requested_host and observed_host and not _same_site_host(requested_host, observed_host):
        return {
            "is_api_candidate": False,
            "reason": "foreign_host",
            "observed_url": observed_url,
            "canonical_url": canonical_observed_url,
            "full_url": canonical_observed_url,
            "observed_host": observed_host,
            "requested_host": requested_host,
            "path": path,
            "method": method,
            "resource_type": resource_type,
        }

    # FIX 4: Remove static assets using the full extension list
    if _is_static_asset(path, resource_type):
        return {
            "is_api_candidate": False,
            "reason": "static_asset",
            "observed_url": observed_url,
            "canonical_url": canonical_observed_url,
            "full_url": canonical_observed_url,
            "observed_host": observed_host or requested_host,
            "requested_host": requested_host,
            "path": path,
            "method": method,
            "resource_type": resource_type,
        }

    api_signal = (
        resource_type == "websocket"
        or _path_has_api_hint(path)
        or "json" in content_type
        or "graphql" in content_type
        or query_based
        or (
            method not in {"GET", "HEAD"}
            and not _is_static_asset(path, resource_type)
        )
    )
    if not api_signal and aggressive:
        api_signal = (
            resource_type in RESOURCE_TYPE_API
            or (
                method not in {"GET", "HEAD"}
                and not _is_static_asset(path, resource_type)
            )
        )
    if not api_signal:
        return {
            "is_api_candidate": False,
            "reason": "page_route",
            "observed_url": observed_url,
            "canonical_url": canonical_observed_url,
            "full_url": canonical_observed_url,
            "observed_host": observed_host or requested_host,
            "requested_host": requested_host,
            "path": path,
            "method": method,
            "resource_type": resource_type,
        }

    if not _looks_like_api_path(path):
        return {
            "is_api_candidate": True,
            "reason": "probable_api_candidate" if "json" in content_type and resource_type not in RESOURCE_TYPE_API and not _path_has_api_hint(path) else "api_candidate",
            "observed_url": observed_url,
            "canonical_url": canonical_observed_url,
            "full_url": canonical_observed_url,
            "observed_host": observed_host or requested_host,
            "requested_host": requested_host,
            "path": path,
            "method": method,
            "resource_type": resource_type,
        }

    # Everything else = API candidate
    return {
        "is_api_candidate": True,
        "reason": "api_candidate",
        "observed_url": observed_url,
        "canonical_url": canonical_observed_url,
        "full_url": canonical_observed_url,
        "observed_host": observed_host or requested_host,
        "requested_host": requested_host,
        "path": path,
        "method": method,
        "resource_type": resource_type,
    }


def _extract_entry(entry, source_file: str, target_url: str, aggressive: bool = False):
    if not isinstance(entry, dict):
        return None

    method = entry.get("method")
    path = entry.get("path") or entry.get("endpoint") or entry.get("url")
    status = entry.get("status") or entry.get("status_code")
    description = entry.get("description") or entry.get("name") or "Discovered API endpoint"

    if not method or not path:
        request = entry.get("request", {})
        response = entry.get("response", {})
        method = method or (request.get("method") if isinstance(request, dict) else None)
        path = path or (
            request.get("path") if isinstance(request, dict) else None
        ) or (
            request.get("url") if isinstance(request, dict) else None
        )
        status = status or (
            response.get("status_code") if isinstance(response, dict) else None
        ) or (
            response.get("status") if isinstance(response, dict) else None
        )

    if not method or not path:
        return None

    classification = _classify_entry(entry, target_url, aggressive=aggressive)
    normalized_path = classification["path"]
    observed_url = classification["observed_url"] or _normalize_full_url(target_url, normalized_path)
    canonical_url = classification.get("canonical_url") or _strip_query_string(observed_url) or _canonicalize_full_url(target_url, normalized_path)

    return {
        "method": str(method).upper(),
        "path": normalized_path,
        "full_url": canonical_url,
        "observed_url": observed_url,
        "status": int(status) if isinstance(status, int) or str(status).isdigit() else status or 200,
        "description": description,
        "capture_mode": entry.get("capture_mode", "file"),
        "target_url": entry.get("target_url", target_url or "N/A"),
        "observed_host": classification.get("observed_host", "") or "",
        "requested_host": classification.get("requested_host", "") or "",
        "resource_type": classification.get("resource_type", "") or "",
        "request_kind": classification.get("reason", "api_candidate"),
        "is_api_candidate": classification.get("is_api_candidate", False),
        "source_file": source_file,
        # Phase 4 — body fields from Phase 0.1 capture
        "request_body": entry.get("request_body"),
        "request_content_type": entry.get("request_content_type") or entry.get("content_type", ""),
        "response_body": entry.get("response_body"),
        "response_content_type": entry.get("response_content_type", ""),
        "response_time_ms": entry.get("response_time_ms"),
        "inferred_schema": entry.get("inferred_schema"),   # populated by enrichment pass
        "auth_pattern": entry.get("auth_pattern", "none"),
        "status_codes_seen": entry.get("status_codes_seen") or [],
    }


def _payload_has_live_traffic(payload) -> bool:
    if not isinstance(payload, dict):
        return False

    capture_profile = payload.get("capture_profile")
    if isinstance(capture_profile, dict):
        captured_requests = capture_profile.get("captured_requests")
        if isinstance(captured_requests, list) and captured_requests:
            return True

    captured_requests = payload.get("captured_requests")
    if isinstance(captured_requests, list) and captured_requests:
        return True

    return False


def _artifact_target_url(payload) -> str:
    if not isinstance(payload, dict):
        return ""

    capture_profile = payload.get("capture_profile")
    if isinstance(capture_profile, dict):
        value = str(capture_profile.get("target_url") or "").strip()
        if value:
            return value

    value = str(payload.get("target_url") or "").strip()
    if value:
        return value

    return ""


def _extract_entries(payload, source_file: str, target_url: str, include_existing_inventory: bool = True, aggressive: bool = False):
    discovered = []

    def collect(entries):
        if isinstance(entries, list):
            for entry in entries:
                api_entry = _extract_entry(entry, source_file, target_url, aggressive=aggressive)
                if api_entry:
                    discovered.append(api_entry)

    if not include_existing_inventory:
        return discovered

    if isinstance(payload, dict):
        for key in DISCOVERY_KEYS:
            collect(payload.get(key))

        capture_profile = payload.get("capture_profile")
        if isinstance(capture_profile, dict):
            for key in ("discovered_apis", "generated_traces", "baseline", "traces", "captured_requests", "requests"):
                collect(capture_profile.get(key))
    elif isinstance(payload, list):
        collect(payload)

    return discovered


def _extract_traffic_inventory(payload):
    if not isinstance(payload, dict):
        return []

    if isinstance(payload.get("capture_profile"), dict):
        capture_profile = payload["capture_profile"]
        if isinstance(capture_profile.get("captured_requests"), list):
            return capture_profile.get("captured_requests", [])

    if isinstance(payload.get("captured_requests"), list):
        return payload.get("captured_requests", [])

    return []


def _dedupe_apis(apis):
    seen = set()
    deduped = []

    for api in apis:
        key = (
            api.get("method"),
            api.get("path"),
            api.get("full_url"),
            api.get("observed_host"),
            api.get("target_url"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(api)

    return deduped


def build_discovery_inventory(target_url: str, workspace_root=None, aggressive=None):
    if aggressive is None:
        aggressive = _env_bool("DISCOVERY_AGGRESSIVE", False)

    discovered = []
    traffic_requests = []
    source_files = []
    excluded_reason_counts: Counter[str] = Counter()
    unique_hosts: set[str] = set()
    observed_hosts: set[str] = set()
    artifact_records: list[tuple[Path, object]] = []
    has_live_traffic = False

    for artifact_file in iter_artifact_files(workspace_root):
        try:
            payload = _load_artifact(artifact_file)
        except Exception:
            continue

        artifact_records.append((artifact_file, payload))
        if not _is_baseline_artifact(artifact_file) and _payload_has_live_traffic(payload):
            has_live_traffic = True

    for artifact_file, payload in artifact_records:
        artifact_target_url = _artifact_target_url(payload)
        if target_url and artifact_target_url:
            requested_host = _extract_host(target_url)
            artifact_host = _extract_host(artifact_target_url)
            if requested_host and artifact_host and not _same_site_host(requested_host, artifact_host):
                continue

        include_existing_inventory = not (_is_baseline_artifact(artifact_file) and has_live_traffic)

        extracted = _extract_entries(
            payload,
            str(artifact_file),
            target_url,
            include_existing_inventory=include_existing_inventory,
            aggressive=aggressive,
        )
        if extracted:
            source_file_str = str(artifact_file)
            source_files.append(source_file_str)
            for entry in extracted:
                observed_host = str(entry.get("observed_host") or "").strip()
                if observed_host:
                    observed_hosts.add(observed_host)
                if entry.get("is_api_candidate"):
                    discovered.append(entry)
                    if observed_host:
                        unique_hosts.add(observed_host)
                else:
                    excluded_reason_counts[str(entry.get("request_kind") or "excluded")] += 1

        traffic_entries = _extract_traffic_inventory(payload)
        if traffic_entries:
            traffic_requests.extend(traffic_entries)

    discovered = _dedupe_apis(discovered)
    source_files = sorted(dict.fromkeys(source_files))

    # FIX 5: Only extend discovered with traffic requests that are genuine API calls.
    # Previously ALL non-root-path traffic was included, causing .webp, .htm files
    # to appear as "Discovered API endpoints". Now we require:
    #   (a) resource_type must be fetch, xhr, or websocket
    #   (b) path must pass the _looks_like_api_path() check (no static extensions)
    if traffic_requests:
        target_host = _extract_host(str(target_url or ""))
        probable_api_request_count = 0
        for req in traffic_requests:
            path = _strip_query_string(str(req.get("path", "/")))
            resource_type = str(req.get("resource_type") or "").lower()
            req_host = str(req.get("host") or "").lower()
            content_type = _response_content_type(req)
            clean_path = str(path or "").split("?")[0].lower()
            page_like = any(clean_path.endswith(ext) for ext in PAGE_EXTENSIONS)

            # Keep legitimate API traffic, even when the route itself looks like
            # a page route. A fetch/xhr/websocket call that returns JSON is often
            # the only signal we get from SPAs and backend-for-frontend apps.
            strong_api_signal = (
                resource_type == "websocket"
                or _path_has_api_hint(path)
                or (
                    resource_type in {"fetch", "xhr"}
                    and not page_like
                    and _looks_like_api_path(path)
                )
            )
            weak_api_signal = "json" in content_type and not page_like
            aggressive_api_signal = (
                aggressive
                and resource_type in RESOURCE_TYPE_API
                and not _is_static_asset(path, resource_type)
            )
            api_signal = strong_api_signal or weak_api_signal or aggressive_api_signal
            if not api_signal:
                continue

            # Skip obvious static assets, but allow browser fetch/XHR calls to
            # document-shaped routes when they clearly return API-ish payloads.
            if not _looks_like_api_path(path):
                if not strong_api_signal and not weak_api_signal and not aggressive_api_signal:
                    continue

            # Static asset paths should never be promoted just because they were
            # fetched during navigation.
            if _is_static_asset(path, resource_type):
                continue

            # Allow same-site API hosts such as api.example.com vs www.example.com.
            if target_host and req_host and not _same_site_host(target_host, req_host):
                continue

            discovered.append({
                "method": req.get("method", "GET"),
                "path": path,
                "full_url": _strip_query_string(str(req.get("url") or "")) or req.get("url"),
                "observed_url": req.get("url"),
                "status": req.get("status", 200),
                "description": "Captured from live traffic",
                "capture_mode": "playwright",
                "target_url": target_url,
                "observed_host": req_host,
                "is_api_candidate": True,
                "source_file": "traffic-inventory",
                "request_kind": "api_candidate" if strong_api_signal else "probable_api_candidate",
                "confidence": "high" if strong_api_signal else "medium",
            })
            if not strong_api_signal:
                probable_api_request_count += 1

    # Pattern inference — only run when we have real API base paths to expand from.
    # We keep this conservative, but allow more common API version / service
    # prefixes so the baseline can grow on apps that expose APIs on subdomains.
    expanded_apis = []
    base_segments = set()

    for api in discovered:
        path = api.get("path", "")
        parts = [p for p in path.split("/") if p]
        api["confidence"] = classify_api_quality(api)

        # Only expand routes that look like actual API families.
        if len(parts) >= 2:
            for index, segment in enumerate(parts[:3]):
                lower_segment = segment.lower()
                if lower_segment in API_ROOT_SEGMENTS or lower_segment in API_VERSION_SEGMENTS:
                    base_segments.add("/" + "/".join(parts[: max(2, index + 2)]))
                    break
            else:
                if _path_has_api_hint(path):
                    base_segments.add("/" + "/".join(parts[:2]))

    for base in base_segments:
        variations = [
            base,
            f"{base}/list",
            f"{base}/search",
            f"{base}/{{id}}",
        ]
        for path in variations:
            expanded_apis.append({
                "method": "GET",
                "path": path,
                "full_url": _canonicalize_full_url(target_url, path),
                "observed_url": _normalize_full_url(target_url, path),
                "status": 200,
                "description": "Inferred API endpoint (pattern-based)",
                "capture_mode": "inferred",
                "target_url": target_url,
                "is_api_candidate": True,
                "source_file": "pattern-inference",
                "confidence": "low",
            })

    # Merge + dedupe
    discovered.extend(expanded_apis)
    discovered = _dedupe_apis(discovered)

    summary = {
        "discovered_api_count": len(discovered),
        "traffic_request_count": len(traffic_requests),
        "excluded_request_count": sum(excluded_reason_counts.values()),
        "foreign_host_request_count": excluded_reason_counts.get("foreign_host", 0),
        "static_asset_request_count": excluded_reason_counts.get("static_asset", 0),
        "page_route_request_count": excluded_reason_counts.get("page_route", 0),
        "probable_api_request_count": probable_api_request_count if traffic_requests else 0,
        "unique_hosts": sorted(unique_hosts),
        "observed_hosts": sorted(observed_hosts),
        "source_files": source_files,
        "request_kind_counts": dict(sorted(excluded_reason_counts.items())),
    }

    # Phase 4 — enrich discovery entries with bodies + inferred schemas from corpus
    try:
        from core.api.mock_generator import build_mock_corpus, generalize_path
        corpus = build_mock_corpus(workspace_root)
        corpus_index = {
            (e["method"], e["path"]): e
            for e in corpus
        }
        enriched = 0
        for api in discovered:
            method = str(api.get("method") or "GET").upper()
            gen_path = generalize_path(str(api.get("path") or "/"))
            corpus_entry = corpus_index.get((method, gen_path))
            if corpus_entry:
                if not api.get("request_body") and corpus_entry["request"].get("body"):
                    api["request_body"] = corpus_entry["request"]["body"]
                if not api.get("response_body") and corpus_entry["response"].get("body"):
                    api["response_body"] = corpus_entry["response"]["body"]
                if corpus_entry["response"].get("schema"):
                    api["inferred_schema"] = corpus_entry["response"]["schema"]
                if not api.get("auth_pattern") or api.get("auth_pattern") == "none":
                    api["auth_pattern"] = corpus_entry.get("auth_pattern", "none")
                if not api.get("status_codes_seen"):
                    api["status_codes_seen"] = corpus_entry.get("status_codes_seen", [])
                if not api.get("response_time_ms") and corpus_entry["response"].get("median_latency_ms"):
                    api["response_time_ms"] = corpus_entry["response"]["median_latency_ms"]
                enriched += 1
        summary["corpus_enriched_count"] = enriched
    except Exception:
        pass

    return {
        "site_type": "API_PLATFORM",
        "site_description": "Backend API surface with discovered traffic inventory and testable service workflows",
        "inventory_summary": summary,
        "discovered_apis": discovered,
        "traffic_requests": traffic_requests,
    }

