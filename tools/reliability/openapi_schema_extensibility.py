"""
Real OpenAPI schema validator — tries to fetch /openapi.json, /swagger.json,
/api-docs etc, validates it parses, and checks captured endpoints appear in it.
"""
from __future__ import annotations
import requests
from core.api.mock_generator import generate_mocks

_SPEC_PATHS = [
    "/openapi.json", "/swagger.json", "/api-docs",
    "/api/openapi.json", "/api/swagger.json",
    "/v1/openapi.json", "/api/v1/swagger.json",
]


def validate_openapi_schema(target_url=None, workspace_root=None):
    print("[RELIABILITY: OpenAPI Schema] Probing for OpenAPI/Swagger spec...")

    if not target_url:
        return {
            "success": True,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "severity": "INFO",
            "log": "No target_url — pass it to probe for OpenAPI spec.",
            "recommendation": "Wire target_url into the tool call.",
        }

    from tools.url_helper import build_probe_url

    base = target_url.rstrip("/")
    spec = None
    spec_url = None

    for path in _SPEC_PATHS:
        try:
            url = build_probe_url(target_url, path)
            r = requests.get(url, timeout=5, verify=False)
            if r.status_code == 200:
                try:
                    spec = r.json()
                    spec_url = url
                    break
                except Exception:
                    continue
        except Exception:
            continue

    if not spec:
        return {
            "success": False,
            "status": "FAIL",
            "mode": "LIVE",
            "severity": "MEDIUM",
            "log": f"No OpenAPI/Swagger spec found at any of {_SPEC_PATHS}.",
            "recommendation": "Expose an OpenAPI spec at /openapi.json or /api-docs for discoverability.",
        }

    # Validate structure
    issues = []
    if "openapi" not in spec and "swagger" not in spec:
        issues.append("spec missing 'openapi' or 'swagger' version key")

    paths_in_spec = set((spec.get("paths") or {}).keys())

    # Cross-check captured endpoints against spec
    mocks = generate_mocks(workspace_root)
    undocumented = []
    for mock in mocks:
        path = mock["path"].split("?")[0]
        if path not in paths_in_spec:
            undocumented.append(path)

    if undocumented:
        issues.append(
            f"{len(undocumented)} captured endpoints not in spec: "
            + ", ".join(undocumented[:5])
        )

    success = len(issues) == 0
    return {
        "success": success,
        "status": "PASS" if success else "FAIL",
        "mode": "LIVE",
        "severity": "INFO" if success else "MEDIUM",
        "log": (
            f"OpenAPI spec found at {spec_url} with {len(paths_in_spec)} paths. All captured endpoints documented."
            if success else
            f"OpenAPI issues: {'; '.join(issues[:3])}"
        ),
        "recommendation": (
            "Add missing captured endpoints to your OpenAPI spec."
            if undocumented else "N/A"
        ),
        "spec_url": spec_url,
        "paths_in_spec": len(paths_in_spec),
        "undocumented_endpoints": undocumented[:20],
        "issues": issues,
    }
