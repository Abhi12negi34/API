import requests

from core.api.discovery_inventory import build_discovery_inventory


def _candidate_path(target_url, workspace_root=None):
    inventory = build_discovery_inventory(target_url, workspace_root=workspace_root)
    discovered = inventory.get("discovered_apis", []) if isinstance(inventory, dict) else []
    for entry in discovered:
        if not isinstance(entry, dict):
            continue
        path = str(entry.get("path") or "").strip()
        if path and path not in {"/", ""}:
            return path
    return ""


def audit_token_bucket_rate_limit(target_url="http://localhost", workspace_root=None):
    """
    Sends a burst of requests against a discovered API path and checks whether
    the rate limiter uses token bucket semantics (burst tolerance + Retry-After).
    """
    print("[SCALABILITY: Token Bucket Rate Limit Auditor] Testing burst tolerance and rate limit headers...")
    base = target_url.rstrip("/")
    probe_path = _candidate_path(target_url, workspace_root=workspace_root)
    if not probe_path:
        return {
            "success": True,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "severity": "INFO",
            "log": "No discovered API paths were available, so token bucket rate limiting was skipped.",
            "path": base,
            "recommendation": "Run discovery first and rerun the rate-limit auditor against the captured API surface.",
        }

    probe_url = f"{base}{probe_path if probe_path.startswith('/') else '/' + probe_path}"

    statuses = []
    retry_after_values = []

    for _ in range(30):
        try:
            resp = requests.get(probe_url, timeout=3, verify=True)
            statuses.append(resp.status_code)
            if resp.status_code == 429:
                ra = resp.headers.get("Retry-After", "")
                if ra:
                    retry_after_values.append(ra)
        except Exception:
            statuses.append(0)

    hit_429 = statuses.count(429)
    has_retry_after = len(retry_after_values) > 0

    if hit_429 > 0 and not has_retry_after:
        return {
            "success": False,
            "log": f"Rate limiter triggered ({hit_429} 429s in 30 requests) but Retry-After header missing. Client cannot back off.",
            "severity": "MEDIUM",
            "path": probe_url,
            "recommendation": "Add Retry-After header to all 429 responses so clients implement proper exponential backoff.",
        }
    if hit_429 > 20:
        return {
            "success": False,
            "log": f"Rate limiter too aggressive: {hit_429}/30 requests rejected. Token bucket burst size may be too small for normal traffic.",
            "severity": "MEDIUM",
            "path": probe_url,
            "recommendation": "Increase token bucket burst capacity to allow short legitimate traffic spikes without false positives.",
        }
    return {
        "success": True,
        "log": f"Rate limit behavior: {hit_429} 429s in 30 requests. Retry-After: {retry_after_values or 'N/A (no 429 triggered)'}.",
        "severity": "INFO",
        "path": probe_url,
        "recommendation": "N/A" if hit_429 == 0 else "Ensure Retry-After is always present on 429 responses.",
    }
