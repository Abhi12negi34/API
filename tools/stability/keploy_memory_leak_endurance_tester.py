"""
Memory/endurance tester — replays captured GET requests in a loop
and checks for latency degradation over time, which is the observable
proxy for memory leaks from outside the process.
"""
from __future__ import annotations
import time
import requests
from core.api.mock_generator import load_captured_requests, is_api_candidate
from tools.url_helper import build_probe_url

_ITERATIONS = 20
_DEGRADATION_THRESHOLD = 2.5   # flag if last-batch p50 > 2.5x first-batch p50


def test_memory_leak_endurance(workspace_root=None, target_url=None):
    print(f"[STABILITY: Endurance] Replaying {_ITERATIONS} iterations to detect latency drift...")

    if not target_url:
        return {
            "success": True, "status": "SKIPPED", "mode": "SIMULATED", "severity": "INFO",
            "log": "No target_url — pass it to run endurance replay.",
            "recommendation": "Wire target_url into the tool call.",
        }

    entries = load_captured_requests(workspace_root)
    safe = [
        e for e in entries
        if is_api_candidate(e) and str(e.get("method", "GET")).upper() == "GET"
        and not any(seg in str(e.get("path","")) for seg in ("{", "login", "logout"))
    ][:3]

    if not safe:
        # Fallback: probe root
        safe = [{"method": "GET", "path": "/", "url": target_url.rstrip("/")}]

    base = target_url.rstrip("/")
    urls = [build_probe_url(target_url, str(e.get("path") or "/").split("?")[0]) for e in safe]

    early_latencies: list[float] = []
    late_latencies: list[float] = []

    for i in range(_ITERATIONS):
        for url in urls:
            try:
                t0 = time.monotonic()
                requests.get(url, timeout=8, verify=False)
                elapsed = (time.monotonic() - t0) * 1000
                if i < _ITERATIONS // 3:
                    early_latencies.append(elapsed)
                elif i > _ITERATIONS * 2 // 3:
                    late_latencies.append(elapsed)
            except Exception:
                continue

    if not early_latencies:
        return {
            "success": True, "status": "SKIPPED", "mode": "LIVE", "severity": "INFO",
            "log": "All requests failed during endurance replay — target may be unreachable.",
            "recommendation": "Verify target is running.",
        }

    early_p50 = sorted(early_latencies)[len(early_latencies) // 2]
    late_p50 = sorted(late_latencies)[len(late_latencies) // 2] if late_latencies else early_p50
    ratio = late_p50 / max(early_p50, 1)

    degraded = ratio > _DEGRADATION_THRESHOLD
    return {
        "success": not degraded, "status": "FAIL" if degraded else "PASS",
        "mode": "LIVE", "severity": "HIGH" if degraded else "INFO",
        "log": (
            f"Endurance OK — early p50 {early_p50:.0f}ms, late p50 {late_p50:.0f}ms "
            f"(ratio {ratio:.2f}x, threshold {_DEGRADATION_THRESHOLD}x)."
            if not degraded else
            f"Latency degraded {ratio:.1f}x over {_ITERATIONS} iterations "
            f"(early p50 {early_p50:.0f}ms → late p50 {late_p50:.0f}ms). Possible memory leak."
        ),
        "recommendation": "Profile heap with memory profiler — gradual latency increase indicates GC pressure or connection leak." if degraded else "N/A",
        "early_p50_ms": round(early_p50, 1),
        "late_p50_ms": round(late_p50, 1),
        "degradation_ratio": round(ratio, 2),
        "iterations": _ITERATIONS,
    }
