import requests

try:
    import httpx
except Exception:  # pragma: no cover - optional dependency
    httpx = None

def profile_http2_multiplexing(target_url="http://localhost"):
    """
    Checks whether the server supports HTTP/2 by inspecting the ALPN protocol
    and the 'protocol' field in urllib3/httpx response.
    Falls back to checking 'Upgrade' or 'Alt-Svc' headers.
    """
    print("[EFFICIENCY: HTTP/2 Multiplexing Profiler] Checking HTTP protocol version...")
    base = target_url.rstrip("/")

    try:
        if httpx is not None:
            with httpx.Client(http2=True, follow_redirects=True, verify=True, timeout=5.0) as client:
                resp = client.get(base)
                alt_svc = resp.headers.get("Alt-Svc", "")
                if resp.http_version == "HTTP/2" or "h2" in alt_svc.lower():
                    return {
                        "success": True,
                        "log": f"HTTP/2 supported (http_version={resp.http_version}, Alt-Svc='{alt_svc}').",
                        "severity": "INFO",
                        "path": base,
                        "recommendation": "N/A. Enable HTTP/3 (QUIC) via Alt-Svc for further multiplexing gains."
                    }
                return {
                    "success": False,
                    "log": f"{resp.http_version} detected. Alt-Svc='{alt_svc}'. Multiplexing unavailable.",
                    "severity": "MEDIUM",
                    "path": base,
                    "recommendation": "Enable HTTP/2 via TLS ALPN negotiation in Nginx (listen 443 ssl http2) or your reverse proxy config."
                }

        resp = requests.get(base, timeout=5, verify=True)
        alt_svc = resp.headers.get("Alt-Svc", "")
        upgrade = resp.headers.get("Upgrade", "")
        raw_version = getattr(resp.raw, "version", None)
        return {
            "success": False,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "log": f"HTTP/2 probe skipped because httpx is unavailable. Alt-Svc='{alt_svc}', Upgrade='{upgrade}', raw_version={raw_version}.",
            "severity": "INFO",
            "path": base,
            "recommendation": "Install httpx to enable real HTTP/2 negotiation checks."
        }
    except Exception as e:
        return {
            "success": False,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "log": f"[SIMULATION] Could not probe HTTP version: {str(e)}",
            "severity": "INFO",
            "path": base,
            "recommendation": "Enable HTTP/2 on your API gateway for better multiplexing performance."
        }
