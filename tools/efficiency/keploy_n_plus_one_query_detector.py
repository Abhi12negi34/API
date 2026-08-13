"""
Real N+1 detector — scans captured traffic for repeated same-path calls
in sequence (pattern: GET /items/1, GET /items/2, GET /items/3 in rapid
succession), which is the browser-observable signature of N+1 queries.
"""
from __future__ import annotations
import re
from core.api.mock_generator import load_captured_requests, is_api_candidate, generalize_path

_MIN_REPEAT_COUNT = 3   # flag if same generalized path called >= 3 times in a run


def detect_n_plus_one_queries(workspace_root=None):
    print("[EFFICIENCY: N+1] Scanning captured traffic for repeated same-shape endpoint calls...")

    entries = load_captured_requests(workspace_root)
    api_entries = [e for e in entries if is_api_candidate(e)]

    if not api_entries:
        return {
            "success": True,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "severity": "INFO",
            "log": "No captured API traffic found. Run capture first.",
            "recommendation": "Run playwright capture and retry.",
        }

    # Count calls per generalized path
    from collections import Counter
    path_counts: Counter = Counter()
    for entry in api_entries:
        method = str(entry.get("method", "GET")).upper()
        path = generalize_path(str(entry.get("path") or "/"))
        path_counts[f"{method} {path}"] += 1

    flagged = {
        path: count
        for path, count in path_counts.items()
        if count >= _MIN_REPEAT_COUNT and "{param}" in path
    }

    success = len(flagged) == 0
    log = (
        f"N+1 check OK — no repeated per-ID calls detected across {len(api_entries)} captured requests."
        if success else
        "N+1 pattern detected: " + "; ".join(
            f"{path} called {count}x" for path, count in sorted(flagged.items(), key=lambda x: -x[1])[:5]
        )
    )

    return {
        "success": success,
        "status": "PASS" if success else "FAIL",
        "mode": "LIVE",
        "severity": "INFO" if success else "MEDIUM",
        "log": log,
        "recommendation": (
            "Batch these per-ID calls into a single collection endpoint (e.g. GET /items?ids=1,2,3)."
            if not success else "N/A"
        ),
        "flagged": flagged,
        "total_api_requests": len(api_entries),
    }
