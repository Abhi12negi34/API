import requests

REQUIRED_HEADERS = {
    "Strict-Transport-Security": "HSTS missing — browsers won't enforce HTTPS",
    "X-Frame-Options": "Clickjacking protection missing",
    "X-Content-Type-Options": "MIME sniffing attack vector open",
    "Content-Security-Policy": "CSP missing — XSS attack surface exposed",
    "Referrer-Policy": "Referrer leakage possible",
}

def audit_secure_configurations(target_url="http://localhost"):
    """
    GETs the target root and checks for OWASP Secure Headers recommendations.
    """
    print("[SECURITY: Secure Headers Auditor] Checking HTTP response headers...")
    base = target_url.rstrip("/")
    missing = []
    present = []

    try:
        resp = requests.get(base, timeout=6, verify=True)
        headers = {k.lower(): v for k, v in resp.headers.items()}

        for header, risk in REQUIRED_HEADERS.items():
            if header.lower() in headers:
                present.append(header)
            else:
                missing.append(f"{header} ({risk})")

    except Exception as e:
        return {
            "success": False,
            "log": f"Could not connect to {base}: {str(e)}",
            "severity": "HIGH",
            "path": base,
            "recommendation": "Ensure the target is reachable and returning HTTP responses."
        }

    if missing:
        severity = "HIGH" if len(missing) >= 3 else "MEDIUM"
        return {
            "success": False,
            "log": f"Missing security headers: {', '.join(missing)}. Present: {', '.join(present)}.",
            "severity": severity,
            "path": base,
            "recommendation": "Add all OWASP recommended security response headers. See https://owasp.org/www-project-secure-headers/"
        }
    return {
        "success": True,
        "log": f"All {len(REQUIRED_HEADERS)} OWASP security headers present: {', '.join(present)}.",
        "severity": "INFO",
        "path": base,
        "recommendation": "N/A"
    }
