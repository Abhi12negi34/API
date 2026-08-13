"""
gRPC streaming latency analyzer — checks captured traffic for gRPC
endpoints (content-type: application/grpc) and reports their latency
profile. Falls back to SKIPPED if no gRPC traffic was captured.
"""
from __future__ import annotations
from core.api.mock_generator import load_captured_requests


def analyze_grpc_streaming_latency(workspace_root=None):
    print("[PERFORMANCE: gRPC] Scanning captured traffic for gRPC endpoints...")

    entries = load_captured_requests(workspace_root)
    grpc_entries = [
        e for e in entries
        if "grpc" in str(e.get("request_content_type") or e.get("response_content_type") or "").lower()
        or "grpc" in str(e.get("path") or "").lower()
    ]

    if not grpc_entries:
        return {
            "success": True, "status": "SKIPPED", "mode": "SIMULATED", "severity": "INFO",
            "log": "No gRPC traffic detected in captured requests. App may not use gRPC.",
            "recommendation": "N/A — skip if app is REST/HTTP only.",
        }

    latencies = [
        e["response_time_ms"] for e in grpc_entries
        if isinstance(e.get("response_time_ms"), (int, float)) and e["response_time_ms"] > 0
    ]
    slow = [e for e in grpc_entries if (e.get("response_time_ms") or 0) > 2000]

    median_ms = sorted(latencies)[len(latencies) // 2] if latencies else None
    p95_ms = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) >= 2 else None

    issues = []
    if slow:
        issues.append(f"{len(slow)} gRPC calls exceeded 2000ms")
    if p95_ms and p95_ms > 3000:
        issues.append(f"p95 latency {p95_ms:.0f}ms exceeds 3000ms threshold")

    success = len(issues) == 0
    return {
        "success": success, "status": "PASS" if success else "FAIL",
        "mode": "LIVE", "severity": "INFO" if success else "HIGH",
        "log": (
            f"gRPC latency OK — {len(grpc_entries)} streams, median {median_ms:.0f}ms, p95 {p95_ms:.0f}ms."
            if success and median_ms else
            f"gRPC issues: {'; '.join(issues)}" if issues else
            f"{len(grpc_entries)} gRPC streams found, no latency data (pre-Phase-0.1 capture)."
        ),
        "recommendation": "Enable server-side streaming or reduce payload size for slow gRPC calls." if not success else "N/A",
        "grpc_endpoints": len(grpc_entries),
        "median_ms": median_ms,
        "p95_ms": p95_ms,
        "issues": issues,
    }
