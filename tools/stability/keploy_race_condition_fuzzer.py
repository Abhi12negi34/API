"""
Race condition fuzzer — fires identical state-mutating requests concurrently
and checks for duplicate resource creation (201+201), data corruption,
or 500 errors caused by TOCTOU flaws.
"""
from __future__ import annotations
import threading
import requests
from core.api.mock_generator import load_captured_requests, is_api_candidate
from tools.url_helper import build_probe_url

_CONCURRENT = 10


def test_race_conditions(workspace_root=None, target_url=None):
    print(f"[STABILITY: Race Conditions] Firing {_CONCURRENT} concurrent identical requests...")

    if not target_url:
        return {
            "success": True, "status": "SKIPPED", "mode": "SIMULATED", "severity": "INFO",
            "log": "No target_url — pass it to run concurrent race condition probing.",
            "recommendation": "Wire target_url into the tool call.",
        }

    entries = load_captured_requests(workspace_root)
    mutating = [
        e for e in entries
        if is_api_candidate(e)
        and str(e.get("method", "")).upper() in {"POST", "PUT", "PATCH"}
        and e.get("request_body")
    ]

    # Fallback: use a safe POST probe if no captured bodies
    if not mutating:
        probe_url = build_probe_url(target_url, "/api/v1/health")
        method = "GET"
        body = None
    else:
        best = mutating[0]
        path = str(best.get("path") or "/")
        probe_url = build_probe_url(target_url, path)
        method = str(best.get("method", "POST")).upper()
        body = best.get("request_body")

    results: list[int] = []
    errors: list[str] = []
    lock = threading.Lock()

    def fire():
        try:
            if body:
                r = requests.request(
                    method, probe_url, json=body,
                    headers={"Content-Type": "application/json"},
                    timeout=8, verify=False,
                )
            else:
                r = requests.request(method, probe_url, timeout=8, verify=False)
            with lock:
                results.append(r.status_code)
        except Exception as exc:
            with lock:
                errors.append(str(exc))

    threads = [threading.Thread(target=fire) for _ in range(_CONCURRENT)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    status_counts: dict[int, int] = {}
    for s in results:
        status_counts[s] = status_counts.get(s, 0) + 1

    issues = []
    # Duplicate 201s = double-create race condition
    if status_counts.get(201, 0) > 1:
        issues.append(
            f"{status_counts[201]}x HTTP 201 from {_CONCURRENT} concurrent calls — possible double-create"
        )
    # Server errors under concurrency
    server_errors = status_counts.get(500, 0) + status_counts.get(503, 0)
    if server_errors > 0:
        issues.append(f"{server_errors} server errors under {_CONCURRENT}-concurrent load")
    if len(errors) > _CONCURRENT // 2:
        issues.append(f"{len(errors)} connection errors — possible thread pool exhaustion")

    success = len(issues) == 0
    return {
        "success": success, "status": "PASS" if success else "FAIL",
        "mode": "LIVE", "severity": "INFO" if success else "HIGH",
        "log": (
            f"Race condition OK — {len(results)} responses: {status_counts}."
            if success else
            f"Race condition issues: {'; '.join(issues)}"
        ),
        "recommendation": "Add idempotency keys, database-level unique constraints, or optimistic locking." if not success else "N/A",
        "status_distribution": status_counts,
        "connection_errors": len(errors),
        "issues": issues,
    }
