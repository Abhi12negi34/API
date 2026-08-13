import requests

def audit_payload_compression(target_url="http://localhost"):
    """
    Sends a request with Accept-Encoding: gzip, br and checks if the server
    responds with compressed content.
    """
    print("[EFFICIENCY: Payload Compression Auditor] Checking for GZIP/Brotli content encoding...")
    base = target_url.rstrip("/")
    probe_path = f"{base}/"

    try:
        resp = requests.get(probe_path, headers={"Accept-Encoding": "gzip, br, deflate"}, timeout=5, verify=True)
        encoding = resp.headers.get("Content-Encoding", "none")
        content_len = resp.headers.get("Content-Length", "unknown")

        if encoding in ("gzip", "br", "deflate", "zstd"):
            return {
                "success": True,
                "log": f"Response compressed with '{encoding}'. Content-Length: {content_len}.",
                "severity": "INFO",
                "path": probe_path,
                "recommendation": "N/A. Consider Brotli (br) for ~15% better compression than GZIP on text payloads."
            }
        return {
            "success": False,
            "log": f"No content compression detected (Content-Encoding: {encoding}). Raw payload size may be excessive.",
            "severity": "MEDIUM",
            "path": probe_path,
            "recommendation": "Enable GZIP or Brotli compression at the web server/API gateway level for all text/json responses."
        }
    except Exception as e:
        return {
            "success": False,
            "log": f"Compression check failed: {str(e)}",
            "severity": "LOW",
            "path": probe_path,
            "recommendation": "Ensure target is reachable. Enable GZIP in Nginx/Apache/API gateway config."
        }
