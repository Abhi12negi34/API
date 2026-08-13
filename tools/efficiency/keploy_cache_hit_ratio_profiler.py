import requests

def audit_cache_hit_ratio(target_url="http://localhost"):
    """
    Makes duplicate identical requests and checks for Cache-Control, ETag,
    X-Cache, and Age headers to determine cache effectiveness.
    """
    print("[EFFICIENCY: Cache Hit Ratio Profiler] Analyzing caching behavior...")
    base = target_url.rstrip("/")
    probe_path = f"{base}/"
    cache_hits = []
    cache_misses = []

    for i in range(3):
        try:
            resp = requests.get(probe_path, timeout=5, verify=True)
            x_cache = resp.headers.get("X-Cache", "")
            age = resp.headers.get("Age", "")
            cache_control = resp.headers.get("Cache-Control", "no-cache")
            etag = resp.headers.get("ETag", "")

            if "hit" in x_cache.lower() or (age and int(age) > 0):
                cache_hits.append(f"Request {i+1}: X-Cache={x_cache}, Age={age}")
            else:
                cache_misses.append(f"Request {i+1}: X-Cache={x_cache}, Cache-Control={cache_control}, ETag={'present' if etag else 'absent'}")
        except Exception:
            continue

    if not cache_hits and cache_misses:
        return {
            "success": False,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "log": f"Cache hit ratio could not be proven from origin responses alone on {probe_path}. {'; '.join(cache_misses)}.",
            "severity": "INFO",
            "path": probe_path,
            "recommendation": "Expose cache-hit telemetry such as X-Cache/Age, or run this check behind a CDN/reverse proxy that surfaces cache status."
        }
    hit_rate = round(len(cache_hits) / max(len(cache_hits) + len(cache_misses), 1) * 100)
    return {
        "success": True,
        "log": f"Cache hit rate: {hit_rate}%. Hits: {len(cache_hits)}, Misses: {len(cache_misses)}. {'; '.join(cache_hits)}",
        "severity": "INFO",
        "path": probe_path,
        "recommendation": "N/A" if hit_rate > 50 else "Investigate why cache hit rate is below 50%. Check TTL configuration."
    }
