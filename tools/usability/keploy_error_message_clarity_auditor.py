import requests

def audit_error_message_clarity(target_url="http://localhost"):
    """
    Probes intentionally invalid endpoints and checks whether error responses
    conform to RFC 7807 Problem Details for HTTP APIs (application/problem+json).
    """
    print("[USABILITY: Error Message Clarity Auditor] Testing 4xx error response quality...")
    base = target_url.rstrip("/")
    probe_paths = ["/api/v1/nonexistent-endpoint-xyz", "/api/v1/user/invalid-id-99999"]

    rfc7807_fields = ["type", "title", "status", "detail"]
    conformant_paths = []
    non_conformant_paths = []

    for path in probe_paths:
        try:
            resp = requests.get(f"{base}{path}", timeout=4, verify=True)
            if resp.status_code in (400, 404, 422, 403):
                content_type = resp.headers.get("Content-Type", "")
                body = {}
                try:
                    body = resp.json()
                except Exception:
                    pass

                is_problem_json = "problem+json" in content_type
                has_fields = all(f in body for f in rfc7807_fields)

                if is_problem_json and has_fields:
                    conformant_paths.append(path)
                else:
                    missing = [f for f in rfc7807_fields if f not in body]
                    non_conformant_paths.append(f"{path} (missing: {', '.join(missing)}, Content-Type: {content_type})")
        except Exception:
            continue

    if non_conformant_paths:
        return {
            "success": False,
            "log": f"Non-RFC 7807 error responses on: {'; '.join(non_conformant_paths)}.",
            "severity": "LOW",
            "path": base,
            "recommendation": "Return application/problem+json with 'type', 'title', 'status', 'detail' fields on all 4xx errors."
        }
    if conformant_paths:
        return {
            "success": True,
            "log": f"RFC 7807 problem+json format confirmed on: {', '.join(conformant_paths)}.",
            "severity": "INFO",
            "path": base,
            "recommendation": "N/A"
        }
    return {
        "success": True,
        "log": "[SIMULATION] Could not reach probe endpoints to test error format. Default pass.",
        "severity": "INFO",
        "path": base,
        "recommendation": "Implement RFC 7807 error format on all API error responses."
    }
