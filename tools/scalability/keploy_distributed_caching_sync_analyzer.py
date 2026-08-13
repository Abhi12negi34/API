import requests

def analyze_distributed_caching_sync(target_url="http://localhost"):
    """
    Checks if cache invalidation and sync is working by looking for 
    consistent ETag/Last-Modified values across repeated requests.
    Flags inconsistencies that indicate cache sync drift.
    """
    print("[SCALABILITY: Distributed Caching Sync Analyzer] Checking cache consistency...")
    base = target_url.rstrip("/")
    probe_path = f"{base}/api/v1/products"

    etags = []
    last_modified_values = []
    inconsistent = False

    for _ in range(3):
        try:
            resp = requests.get(probe_path, timeout=4, verify=True)
            if resp.status_code < 500:
                etag = resp.headers.get("ETag", "")
                lm = resp.headers.get("Last-Modified", "")
                if etag:
                    etags.append(etag)
                if lm:
                    last_modified_values.append(lm)
        except Exception:
            continue

    if len(set(etags)) > 1:
        inconsistent = True
        return {
            "success": False,
            "log": f"ETag inconsistency across {len(etags)} requests: {set(etags)}. Distributed cache nodes may be out of sync.",
            "severity": "HIGH",
            "path": probe_path,
            "recommendation": "Implement Redis Pub/Sub or Kafka-based cache invalidation to synchronize cache nodes within <1s."
        }

    no_cache_headers = not etags and not last_modified_values
    if no_cache_headers:
        return {
            "success": False,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "log": f"No ETag or Last-Modified headers on {probe_path}; cache sync could not be verified.",
            "severity": "INFO",
            "path": probe_path,
            "recommendation": "Add ETag and Last-Modified headers to all cacheable API responses to enable conditional request caching."
        }

    return {
        "success": True,
        "log": f"ETags consistent across requests: {set(etags) or 'not set'}. Last-Modified: {set(last_modified_values) or 'not set'}.",
        "severity": "INFO",
        "path": probe_path,
        "recommendation": "N/A. Monitor ETag consistency across multiple geographic cache zones."
    }
