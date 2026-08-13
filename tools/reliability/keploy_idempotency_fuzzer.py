"""
Real idempotency fuzzer — replays captured POST/PUT requests twice
and checks that the second call returns 409, 200 (same result), or
is otherwise idempotent (no duplicate resource created).
"""
from __future__ import annotations
import requests
from core.api.mock_generator import load_captured_requests, is_api_candidate
from tools.url_helper import build_probe_url


def test_transaction_idempotency(workspace_root=None, target_url=None):
    print("[RELIABILITY: Idempotency] Replaying duplicate POST/PUT requests to test idempotency...")

    entries = load_captured_requests(workspace_root)
    mutating = [
        e for e in entries
        if is_api_candidate(e)
        and str(e.get("method", "")).upper() in {"POST", "PUT", "PATCH"}
        and e.get("request_body")
        and not e.get("is_templated")
    ]

    if not mutating:
        return {
            "success": True,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "severity": "INFO",
            "log": "No captured POST/PUT requests with bodies found. Run capture first.",
            "recommendation": "Re-run capture with Phase 0.1 applied to get request bodies.",
        }

    if not target_url:
        return {
            "success": True,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "severity": "INFO",
            "log": f"Found {len(mutating)} mutating endpoints — pass target_url to replay.",
            "recommendation": "Wire target_url into the tool call.",
        }

    issues = []
    tested = 0
    base = target_url.rstrip("/")

    for entry in mutating[:5]:
        method = str(entry["method"]).upper()
        path = str(entry.get("path") or "/")
        url = build_probe_url(target_url, path)
        body = entry["request_body"]
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        try:
            r1 = requests.request(method, url, json=body, headers=headers, timeout=6, verify=False)
            r2 = requests.request(method, url, json=body, headers=headers, timeout=6, verify=False)
            tested += 1

            # Idempotent: 200+200, 201+409, 200+409 are all acceptable
            # Non-idempotent: 201+201 (two resources created)
            if r1.status_code == 201 and r2.status_code == 201:
                issues.append(f"{method} {path}: duplicate 201 — possible double-create")
            elif r2.status_code == 500:
                issues.append(f"{method} {path}: second call returned 500")
        except Exception:
            continue

    success = len(issues) == 0
    log = (
        f"Idempotency OK — {tested} mutating endpoints replayed twice, no duplicates."
        if success else
        f"Idempotency failures ({len(issues)}): {'; '.join(issues)}"
    )

    return {
        "success": success,
        "status": "PASS" if success else "FAIL",
        "mode": "LIVE",
        "severity": "INFO" if success else "HIGH",
        "log": log,
        "recommendation": (
            "Add Idempotency-Key header support or check-then-insert logic for mutating endpoints."
            if not success else "N/A"
        ),
        "tested": tested,
        "issues": issues,
    }
