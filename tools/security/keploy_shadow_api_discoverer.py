import requests

from tools.url_helper import build_probe_url

COMMON_SHADOW_PATHS = [
    "/v1/admin/sync", "/v1/internal/debug", "/v1/admin/purge",
    "/api/v0/", "/api/internal/", "/admin/", "/internal/metrics",
    "/actuator/", "/actuator/env", "/actuator/beans", "/_debug",
    "/.well-known/", "/graphql", "/v2/", "/swagger.json", "/openapi.json"
]

def detect_shadow_apis(target_url="http://localhost"):
    """
    Probes a list of common shadow/undocumented API paths and flags any that
    return an unexpected 2xx response (indicating an undocumented endpoint).
    """
    print("[SECURITY: Shadow API Discoverer] Scanning for undocumented/shadow endpoints...")
    base = target_url.rstrip("/")
    found_shadow = []
    accessible_count = 0

    for path in COMMON_SHADOW_PATHS:
        try:
            resp = requests.get(build_probe_url(target_url, path), timeout=3, verify=True, allow_redirects=False)
            if resp.status_code in (200, 201, 204, 301, 302, 307):
                accessible_count += 1
                if path in ["/actuator/env", "/actuator/beans", "/v1/admin/sync",
                            "/v1/internal/debug", "/v1/admin/purge", "/admin/", "/internal/metrics"]:
                    found_shadow.append(f"{path} → HTTP {resp.status_code} (risky internal route)")
        except Exception:
            continue

    if found_shadow:
        return {
            "success": False,
            "log": f"Shadow/internal endpoints accessible from public network: {'; '.join(found_shadow)}.",
            "severity": "CRITICAL",
            "path": base,
            "recommendation": "Block internal/admin paths behind VPC/firewall rules. Remove unauthenticated actuator endpoints from public exposure."
        }
    return {
        "success": True,
        "log": f"Probed {len(COMMON_SHADOW_PATHS)} common shadow API paths. {accessible_count} accessible, none flagged as dangerous.",
        "severity": "INFO",
        "path": base,
        "recommendation": "N/A. Continue periodic shadow API scans as new routes are added."
    }
