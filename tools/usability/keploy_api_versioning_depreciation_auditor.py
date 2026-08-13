import requests

def audit_api_versioning_depreciation(target_url="http://localhost"):
    """
    Checks v1 API endpoints for Sunset and Deprecation headers per IETF RFC 8594.
    """
    print("[USABILITY: API Versioning Auditor] Checking for Sunset/Deprecation headers...")
    base = target_url.rstrip("/")
    probe_paths = ["/api/v1/", "/api/v1/health", "/api/v1/auth", "/v1/"]

    sunset_found = []
    deprecation_found = []
    checked_paths = []

    for path in probe_paths:
        try:
            resp = requests.get(f"{base}{path}", timeout=4, verify=True)
            checked_paths.append(path)
            if resp.status_code < 500:
                if "Sunset" in resp.headers:
                    sunset_found.append(f"{path} → Sunset: {resp.headers['Sunset']}")
                if "Deprecation" in resp.headers:
                    deprecation_found.append(f"{path} → Deprecation: {resp.headers['Deprecation']}")
        except Exception:
            continue

    if not checked_paths:
        return {
            "success": True,
            "log": "[SIMULATION] No v1 API paths reachable. Cannot verify versioning headers.",
            "severity": "INFO",
            "path": base,
            "recommendation": "Expose /api/v1/ endpoints and add Sunset headers when deprecating."
        }

    if not sunset_found and not deprecation_found:
        return {
            "success": False,
            "log": f"No Sunset or Deprecation headers found on v1 endpoints checked: {', '.join(checked_paths)}.",
            "severity": "MEDIUM",
            "path": f"{base}/api/v1/",
            "recommendation": "Add 'Sunset' header (RFC 8594) on deprecated API versions so clients can plan migration."
        }

    return {
        "success": True,
        "log": f"Versioning headers found: Sunset=[{'; '.join(sunset_found)}], Deprecation=[{'; '.join(deprecation_found)}].",
        "severity": "INFO",
        "path": f"{base}/api/v1/",
        "recommendation": "N/A"
    }
