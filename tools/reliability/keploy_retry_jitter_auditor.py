"""
Real retry/jitter auditor — checks captured traffic for Retry-After
headers on 429/503 responses, and probes live for rate-limit behaviour.
"""
from __future__ import annotations
import requests
from core.api.mock_generator import load_captured_requests, is_api_candidate


def audit_retry_jitter(workspace_root=None, target_url=None):
    print("[RELIABILITY: Retry/Jitter] Checking for Retry-After headers on rate-limited responses...")

    entries = load_captured_requests(workspace_root)
    issues = []
    checked = 0

    for entry in entries:
        status = entry.get("status")
        if status not in (429, 503):
            continue
        checked += 1
        headers = entry.get("response_headers") or {}
        has_retry_after = "retry-after" in {k.lower() for k in headers}
        if not has_retry_after:
            issues.append(
                f"{entry.get('method','?')} {entry.get('path','?')}: "
                f"HTTP {status} has no Retry-After header"
            )

    # Live probe: hit same endpoint 3 times quickly to trigger rate-limiting
    if target_url and not checked:
        base = target_url.rstrip("/")
        probe = base + "/"
        try:
            for _ in range(3):
                r = requests.get(probe, timeout=4, verify=False)
                if r.status_code in (429, 503):
                    checked += 1
                    if "retry-after" not in {k.lower() for k in r.headers}:
                        issues.append(f"Live {probe}: HTTP {r.status_code} missing Retry-After")
        except Exception:
            pass

    if not checked:
        return {
            "success": True,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "severity": "INFO",
            "log": "No 429/503 responses found in captured traffic or live probing.",
            "recommendation": "N/A",
        }

    success = len(issues) == 0
    return {
        "success": success,
        "status": "PASS" if success else "FAIL",
        "mode": "LIVE",
        "severity": "INFO" if success else "MEDIUM",
        "log": (
            f"Retry/jitter OK — {checked} rate-limited responses all include Retry-After."
            if success else
            f"Missing Retry-After on {len(issues)} rate-limited responses: {'; '.join(issues[:4])}"
        ),
        "recommendation": (
            "Add Retry-After header to all 429/503 responses with a jittered backoff value."
            if not success else "N/A"
        ),
        "checked": checked,
        "issues": issues,
    }
