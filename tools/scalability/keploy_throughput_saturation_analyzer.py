"""
Throughput saturation analyzer — derives a saturation estimate from
captured latency data. Flags endpoints whose p95 > 1000ms as likely
saturation candidates, and checks for 429/503 responses.
"""
from __future__ import annotations
from collections import defaultdict
from core.api.mock_generator import load_captured_requests, is_api_candidate, generalize_path


def analyze_throughput_saturation(workspace_root=None):
    print("[SCALABILITY: Throughput] Analysing captured latency for saturation signals...")

    entries = load_captured_requests(workspace_root)
    api_entries = [e for e in entries if is_api_candidate(e)]

    if not api_entries:
        return {
            "success": True, "status": "SKIPPED", "mode": "SIMULATED", "severity": "INFO",
            "log": "No captured API traffic. Run capture first.",
            "recommendation": "Run playwright capture and retry.",
        }

    # Group latencies by generalized path
    latency_map: dict[str, list[float]] = defaultdict(list)
    throttled = []

    for e in api_entries:
        status = e.get("status") or 0
        if status in (429, 503):
            throttled.append(f"{e.get('method','?')} {e.get('path','?')}")
        lat = e.get("response_time_ms")
        if isinstance(lat, (int, float)) and lat > 0:
            key = generalize_path(str(e.get("path") or "/"))
            latency_map[key].append(lat)

    if not latency_map and not throttled:
        return {
            "success": True, "status": "SKIPPED", "mode": "SIMULATED", "severity": "INFO",
            "log": "No latency data in captured traffic (pre-Phase-0.1 capture).",
            "recommendation": "Re-run capture with Phase 0.1 applied.",
        }

    slow_endpoints = []
    for path, lats in latency_map.items():
        p95 = sorted(lats)[int(len(lats) * 0.95)] if len(lats) >= 2 else lats[0]
        if p95 > 1000:
            slow_endpoints.append(f"{path} p95={p95:.0f}ms ({len(lats)} samples)")

    issues = slow_endpoints[:5] + ([f"Throttled: {'; '.join(throttled[:3])}"] if throttled else [])
    success = len(issues) == 0

    all_lats = [l for lats in latency_map.values() for l in lats]
    overall_p95 = sorted(all_lats)[int(len(all_lats) * 0.95)] if len(all_lats) >= 2 else None

    return {
        "success": success, "status": "PASS" if success else "FAIL",
        "mode": "LIVE", "severity": "INFO" if success else "HIGH",
        "log": (
            f"Throughput OK — {len(latency_map)} endpoint patterns analysed, "
            f"overall p95 {overall_p95:.0f}ms." if success and overall_p95 else
            f"Saturation signals: {'; '.join(issues[:3])}"
        ),
        "recommendation": "Add caching, connection pooling, or horizontal scaling for slow endpoints." if not success else "N/A",
        "endpoints_analysed": len(latency_map),
        "overall_p95_ms": overall_p95,
        "slow_endpoints": slow_endpoints,
        "throttled_requests": throttled,
    }
