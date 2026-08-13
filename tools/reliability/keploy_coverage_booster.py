import json
import os
from pathlib import Path

import yaml


DEFAULT_SPEC_NAMES = (
    "openapi.yaml",
    "openapi.yml",
    "swagger.yaml",
    "swagger.yml",
    "openapi.json",
    "swagger.json",
)


def _workspace_root(workspace_root=None):
    return Path(workspace_root or os.getcwd()).resolve()


def _load_spec(path):
    suffix = path.suffix.lower()
    with open(path, "r", encoding="utf-8") as handle:
        if suffix == ".json":
            return json.load(handle)
        return yaml.safe_load(handle)


def _extract_traces_from_spec(spec, target_url, source_path):
    traces = []
    paths = (spec or {}).get("paths", {}) if isinstance(spec, dict) else {}
    for route, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method in methods:
            if method.startswith("x-"):
                continue
            traces.append(
                {
                    "method": method.upper(),
                    "path": route,
                    "target_url": target_url,
                    "source": str(source_path),
                    "discovery": "openapi",
                    "status": 200,
                }
            )
    return traces


def _discover_spec_file(workspace_root=None, openapi_path=None):
    candidates = []
    if openapi_path:
        path = Path(openapi_path)
        if path.exists():
            candidates.append(path)

    root = _workspace_root(workspace_root)
    for name in DEFAULT_SPEC_NAMES:
        candidates.extend(root.rglob(name))

    seen = set()
    ordered = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        ordered.append(resolved)
    return ordered


def generate_openapi_traces(target_url="http://localhost", discovery_baseline=None, workspace_root=None, openapi_path=None):
    """
    Generates OpenAPI-backed golden traces when a schema is available.

    If no schema is present, the function falls back to the discovered baseline
    so the agent still emits a useful coverage artifact.
    """
    root = _workspace_root(workspace_root)
    keploy_dir = root / "keploy"
    traces_dir = keploy_dir / "tests" / "keploy"
    traces_dir.mkdir(parents=True, exist_ok=True)
    output_path = traces_dir / "openapi-generated-traces.yaml"

    discovered = discovery_baseline or []
    spec_file = None
    traces = []
    mode = "SIMULATED"
    log = ""

    for candidate in _discover_spec_file(workspace_root=root, openapi_path=openapi_path):
        try:
            spec = _load_spec(candidate)
            traces = _extract_traces_from_spec(spec, target_url, candidate)
            spec_file = candidate
            mode = "LIVE"
            log = f"Generated {len(traces)} OpenAPI trace(s) from schema {candidate}."
            break
        except Exception:
            continue

    if not traces and discovered:
        from core.api.discovery_inventory import _is_static_asset, _looks_like_api_path, STATIC_EXTENSIONS

        traces = []
        for api in discovered:
            path = str(api.get("path") or "/")
            clean_path = path.split("?")[0].lower()

            # Defensive re-filter: skip static assets that leaked into baseline
            if any(clean_path.endswith(ext) for ext in STATIC_EXTENSIONS):
                continue
            if _is_static_asset(path, str(api.get("resource_type") or "")):
                continue
            # Skip entries explicitly marked as non-API
            if api.get("is_api_candidate") is False:
                continue
            # Skip Vite dev-server paths
            if any(marker in path for marker in ("@fs/", "@vite/", ".vite/", "node_modules/")):
                continue

            traces.append({
                "method": api.get("method", "GET"),
                "path": path,
                "target_url": target_url,
                "source": "discovery-baseline-fallback",
                "discovery": "stimulator",
                "status": api.get("status", 200),
                "is_api_candidate": api.get("is_api_candidate", True),
                "confidence": api.get("confidence", "medium"),
            })

        mode = "SIMULATED"
        log = f"OpenAPI schema not found. Generated {len(traces)} golden trace(s) from the discovery baseline fallback (filtered)."
    elif not traces:
        return {
            "success": False,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "severity": "INFO",
            "path": str(output_path),
            "log": "No OpenAPI schema or discovery baseline available, so coverage expansion was skipped.",
            "recommendation": "Provide an OpenAPI schema or a discovered API baseline to enable coverage expansion.",
            "generated_trace_count": 0,
            "source_path": None,
            "generated_traces": [],
        }

    with open(output_path, "w", encoding="utf-8") as handle:
        yaml.safe_dump({"source": str(spec_file) if spec_file else "discovery-baseline-fallback", "generated_traces": traces}, handle, sort_keys=False)

    success = bool(traces)
    severity = "INFO" if success else "MEDIUM"
    return {
        "success": success,
        "status": "PASS" if success else "FAIL",
        "mode": mode,
        "severity": severity,
        "path": str(output_path),
        "log": log or "No OpenAPI schema or discovery baseline available for coverage expansion.",
        "recommendation": "N/A" if success else "Add an OpenAPI schema or enable traffic discovery so golden traces can be generated.",
        "generated_trace_count": len(traces),
        "source_path": str(spec_file) if spec_file else None,
        "generated_traces": traces,
    }
