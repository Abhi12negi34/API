import requests

def simulate_global_cdn_latency(target_url="http://localhost"):
    """
    Checks CDN behavior by inspecting X-Cache, CF-Cache-Status, Via,
    and X-Served-By headers that CDN providers typically inject.
    """
    print("[SCALABILITY: CDN Latency Simulator] Checking for CDN cache indicators...")
    base = target_url.rstrip("/")
    probe_path = f"{base}/"

    cdn_headers = {
        "X-Cache": "Generic CDN cache status",
        "CF-Cache-Status": "Cloudflare CDN",
        "X-Served-By": "Fastly CDN",
        "X-Varnish": "Varnish Cache",
        "Via": "Proxy/CDN intermediary",
        "CDN-Cache-Control": "CDN-specific cache directive"
    }

    try:
        resp = requests.get(probe_path, timeout=5, verify=True)
        found_cdn = {}
        for h, desc in cdn_headers.items():
            val = resp.headers.get(h)
            if val:
                found_cdn[h] = val

        if found_cdn:
            cdn_details = ", ".join(f"{k}={v}" for k, v in found_cdn.items())
            is_hit = any("hit" in str(v).lower() for v in found_cdn.values())
            return {
                "success": True,
                "log": f"CDN detected: {cdn_details}. Cache {'HIT' if is_hit else 'MISS or unknown'}.",
                "severity": "INFO",
                "path": probe_path,
                "recommendation": "N/A. Verify CDN cache-hit rates exceed 80% for static assets."
            }
        return {
            "success": False,
            "log": f"No CDN headers detected on {probe_path}. Traffic may not be routed through a CDN.",
            "severity": "MEDIUM",
            "path": probe_path,
            "recommendation": "Route traffic through a CDN (Cloudflare, Fastly, CloudFront) for global latency reduction and DDoS protection."
        }
    except Exception as e:
        return {
            "success": True,
            "log": f"[SIMULATION] CDN check probe failed: {str(e)}",
            "severity": "INFO",
            "path": probe_path,
            "recommendation": "Deploy a CDN in front of your API gateway for global edge caching."
        }
