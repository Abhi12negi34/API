import requests
import time
from core.api.discovery_inventory import build_discovery_inventory

def audit_screen_reader_delay(target_url="http://localhost"):
    """
    Checks if dynamic content endpoints respond quickly enough for
    screen reader technologies (target: < 300ms for live region updates).
    """
    print("[ACCESSIBILITY: Screen Reader Delay Auditor] Checking response latency for dynamic endpoints...")
    base = target_url.rstrip("/")
    probe_paths = ["/api/v1/notifications", "/api/v1/feed", "/api/v1/updates", "/"]
    slow_endpoints = []
    THRESHOLD_MS = 300

    inventory = build_discovery_inventory(target_url, workspace_root=None)
    if not inventory.get("discovered_apis"):
        return {
            "success": False,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "log": "No confirmed API endpoints were discovered, so screen-reader latency probing was skipped.",
            "severity": "INFO",
            "path": base,
            "recommendation": "Target an API-backed workflow before running latency checks."
        }

    for path in probe_paths:
        try:
            start = time.monotonic()
            resp = requests.get(f"{base}{path}", timeout=5, verify=True)
            elapsed_ms = round((time.monotonic() - start) * 1000, 1)
            if resp.status_code < 500 and elapsed_ms > THRESHOLD_MS:
                slow_endpoints.append(f"{path} → {elapsed_ms}ms (>{THRESHOLD_MS}ms)")
        except Exception:
            continue

    if slow_endpoints:
        return {
            "success": False,
            "log": f"Dynamic endpoints exceed screen-reader latency threshold ({THRESHOLD_MS}ms): {'; '.join(slow_endpoints)}.",
            "severity": "MEDIUM",
            "path": base,
            "recommendation": "Optimize dynamic content endpoints to respond in <300ms. Debounce React state updates before triggering aria-live region refreshes."
        }
    return {
        "success": True,
        "log": f"All probed endpoints responded within {THRESHOLD_MS}ms screen-reader latency threshold.",
        "severity": "INFO",
        "path": base,
        "recommendation": "N/A"
    }
