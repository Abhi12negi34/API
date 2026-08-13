import requests

def validate_rate_limit_dx(target_url="http://localhost"):
    """
    Sends rapid requests to detect rate limiting and validates that
    the API communicates limits via standard headers.
    """
    print("[USABILITY: Rate Limit DX Validator] Probing for rate-limit headers...")
    base = target_url.rstrip("/")
    probe_path = f"{base}/api/v1/auth"

    rate_limit_headers = ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset", "Retry-After"]
    found_headers = []
    missing_headers = []
    got_429 = False

    try:
        # Send a burst of 20 requests to trigger rate limiting
        for i in range(20):
            resp = requests.get(probe_path, timeout=4, verify=True)
            if resp.status_code == 429:
                got_429 = True
                for h in rate_limit_headers:
                    if h in resp.headers:
                        found_headers.append(h)
                    else:
                        missing_headers.append(h)
                break

        if not got_429:
            # Check on a normal response
            resp = requests.get(probe_path, timeout=4, verify=True)
            for h in rate_limit_headers:
                if h in resp.headers:
                    found_headers.append(h)

        if missing_headers:
            return {
                "success": False,
                "log": f"Rate limit triggered (429): {got_429}. Missing headers: {', '.join(missing_headers)}. Present: {', '.join(found_headers)}.",
                "severity": "MEDIUM",
                "path": probe_path,
                "recommendation": "Add Retry-After and X-RateLimit-* headers on all 429 responses so clients can back off gracefully."
            }
        if found_headers:
            return {
                "success": True,
                "log": f"Rate limit headers present: {', '.join(found_headers)}. API communicates throttle state correctly.",
                "severity": "INFO",
                "path": probe_path,
                "recommendation": "N/A"
            }
        return {
            "success": True,
            "log": "[SIMULATION] No rate limiting triggered in 20 requests. Rate limiting may not be configured or threshold is very high.",
            "severity": "INFO",
            "path": probe_path,
            "recommendation": "Configure rate limiting on auth endpoints (recommend: 10 req/min). Use 429 + Retry-After."
        }

    except Exception as e:
        return {
            "success": False,
            "log": f"Rate limit probe failed: {str(e)}",
            "severity": "LOW",
            "path": probe_path,
            "recommendation": "Ensure target endpoint is reachable."
        }
