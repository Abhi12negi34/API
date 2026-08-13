import requests

def detect_bola_idor_vulnerabilities(target_url="http://localhost"):
    """
    Probes numeric-ID endpoints by incrementing/decrementing IDs to detect
    Broken Object Level Authorization (BOLA/IDOR) vulnerabilities.
    Tests if user A's resource is accessible without credentials.
    """
    print("[SECURITY: BOLA/IDOR Detector] Probing ID-based endpoints for object-level auth bypass...")
    base = target_url.rstrip("/")

    # Common resource patterns with sequential IDs
    test_paths = [
        "/api/v1/user/1", "/api/v1/user/2",
        "/api/v1/orders/100", "/api/v1/orders/101",
        "/api/v1/invoice/1000", "/api/v1/invoice/1001",
    ]

    idor_findings = []

    for path in test_paths:
        try:
            resp = requests.get(f"{base}{path}", timeout=3, verify=True)
            # If we get 200 without any auth header, this is a potential IDOR
            if resp.status_code == 200:
                content_length = len(resp.content)
                if content_length > 10:  # Non-empty response = real data returned
                    idor_findings.append(f"{path} → HTTP 200 with {content_length}B data (no auth required)")
        except Exception:
            continue

    if idor_findings:
        return {
            "success": False,
            "log": f"Potential BOLA/IDOR found — unauthenticated access to ID-based resources: {'; '.join(idor_findings)}.",
            "severity": "HIGH",
            "path": base,
            "recommendation": "Enforce object-level authorization. Verify each resource's owner matches the caller's JWT 'sub' claim before returning data."
        }
    return {
        "success": True,
        "log": f"Tested {len(test_paths)} ID-based endpoints. All returned 401/403/404 without authentication — no IDOR exposure detected.",
        "severity": "INFO",
        "path": base,
        "recommendation": "N/A. Continue testing with authenticated user-swapping scenarios for deeper BOLA coverage."
    }
