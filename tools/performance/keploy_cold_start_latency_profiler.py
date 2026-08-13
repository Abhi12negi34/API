import requests
import time
from core.api.discovery_inventory import build_discovery_inventory

COLD_START_THRESHOLD_MS = 2000  # Flag if first-byte > 2 seconds

def profile_cold_start_latency(target_url="http://localhost"):
    """
    Measures time-to-first-byte (TTFB) on a cold HTTP request to detect
    cold start / bootstrap overhead (lambda, container spin-up, etc.)
    """
    print("[PERFORMANCE: Cold Start Profiler] Measuring TTFB for cold response...")
    base = target_url.rstrip("/")
    inventory = build_discovery_inventory(target_url, workspace_root=None)
    discovered = inventory.get("discovered_apis", []) if isinstance(inventory, dict) else []
    if not discovered:
        return {
            "success": False,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "log": "No confirmed API endpoint was discovered, so cold start profiling was skipped.",
            "severity": "INFO",
            "path": base,
            "recommendation": "Provide a reachable API endpoint or discovery baseline before profiling cold start latency."
        }

    probe_path = f"{base}{str(discovered[0].get('path') or '/').rstrip('/')}"
    if probe_path.endswith(base):
        probe_path = f"{base}/"

    try:
        start = time.monotonic()
        resp = requests.get(probe_path, timeout=10, verify=True)
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)

        if elapsed_ms > COLD_START_THRESHOLD_MS:
            return {
                "success": False,
                "log": f"Cold start TTFB = {elapsed_ms}ms on {probe_path} (threshold: {COLD_START_THRESHOLD_MS}ms). Likely container/lambda initialization delay.",
                "severity": "HIGH",
                "path": probe_path,
                "recommendation": "Pre-warm instances or reduce initialization code. Consider connection pooling and lazy loading."
            }
        return {
            "success": True,
            "log": f"Cold start TTFB = {elapsed_ms}ms on {probe_path}. Within {COLD_START_THRESHOLD_MS}ms threshold.",
            "severity": "INFO",
            "path": probe_path,
            "recommendation": "N/A"
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "log": f"Cold start probe timed out after 10s on {probe_path}. Severe initialization bottleneck detected.",
            "severity": "CRITICAL",
            "path": probe_path,
            "recommendation": "Investigate initialization blocking I/O and reduce startup dependencies."
        }
    except Exception as e:
        return {
            "success": False,
            "log": f"Cold start probe failed: {str(e)}",
            "severity": "MEDIUM",
            "path": probe_path,
            "recommendation": "Ensure health endpoint is reachable and returns quickly."
        }
