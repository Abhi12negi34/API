import requests
import time
from core.api.discovery_inventory import build_discovery_inventory

P95_THRESHOLD_MS = 500  # P95 must be under 500ms

def analyze_backend_profiling(target_url="http://localhost"):
    """
    Makes 10 sequential requests to the API, measures latency, and inspects
    Server-Timing headers for backend breakdown data.
    """
    print("[PERFORMANCE: Server Timing Profiler] Measuring backend response breakdown...")
    base = target_url.rstrip("/")
    inventory = build_discovery_inventory(target_url, workspace_root=None)
    discovered = inventory.get("discovered_apis", []) if isinstance(inventory, dict) else []
    if not discovered:
        return {
            "success": False,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "log": "No confirmed API endpoint was discovered, so server timing profiling was skipped.",
            "severity": "INFO",
            "path": base,
            "recommendation": "Provide a reachable API endpoint or discovery baseline before profiling backend timing."
        }

    probe_path = f"{base}{str(discovered[0].get('path') or '/').rstrip('/')}"
    if probe_path.endswith(base):
        probe_path = f"{base}/"
    latencies = []
    server_timing_found = False
    server_timing_detail = ""

    for _ in range(10):
        try:
            start = time.monotonic()
            resp = requests.get(probe_path, timeout=5, verify=True)
            elapsed_ms = round((time.monotonic() - start) * 1000, 1)
            latencies.append(elapsed_ms)

            if "Server-Timing" in resp.headers and not server_timing_found:
                server_timing_found = True
                server_timing_detail = resp.headers["Server-Timing"]
        except Exception:
            latencies.append(5000)  # Timeout counts as worst-case

    latencies.sort()
    p95_idx = int(len(latencies) * 0.95)
    p95 = latencies[min(p95_idx, len(latencies) - 1)]
    avg = round(sum(latencies) / len(latencies), 1)

    timing_note = f" Server-Timing: [{server_timing_detail}]" if server_timing_found else " No Server-Timing header present."

    if p95 > P95_THRESHOLD_MS:
        return {
            "success": False,
            "log": f"P95 latency = {p95}ms (threshold: {P95_THRESHOLD_MS}ms), avg = {avg}ms.{timing_note}",
            "severity": "HIGH",
            "path": probe_path,
            "recommendation": "Profile backend hot-paths. Add Server-Timing headers to expose DB/cache breakdown. Consider query indexing."
        }
    return {
        "success": True,
        "log": f"P95 latency = {p95}ms, avg = {avg}ms — within threshold.{timing_note}",
        "severity": "INFO",
        "path": probe_path,
        "recommendation": "N/A. Add Server-Timing headers for richer backend observability." if not server_timing_found else "N/A"
    }
