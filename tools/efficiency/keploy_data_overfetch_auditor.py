"""
Real data overfetch auditor — inspects captured response bodies from
traffic-inventory.json and flags endpoints that return large payloads
or deeply nested objects likely to contain unused fields.
"""
from __future__ import annotations
import json
from core.api.mock_generator import load_captured_requests, is_api_candidate, schema_fingerprint


_OVERFETCH_FIELD_THRESHOLD = 20   # flag if response has >20 top-level or total schema keys
_OVERFETCH_BYTES_THRESHOLD = 50_000  # flag if body > 50KB


def audit_data_overfetching(workspace_root=None):
    print("[EFFICIENCY: Overfetch] Analysing captured response body sizes and field counts...")

    entries = load_captured_requests(workspace_root)
    api_entries = [e for e in entries if is_api_candidate(e) and e.get("response_body")]

    if not api_entries:
        return {
            "success": True,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "severity": "INFO",
            "log": "No captured response bodies found. Re-run capture with Phase 0.1 patch.",
            "recommendation": "Run a fresh capture to populate response bodies.",
        }

    issues = []
    checked = 0

    for entry in api_entries[:50]:
        body = entry.get("response_body")
        body_bytes = entry.get("response_body_bytes", 0) or 0
        path = entry.get("path", "?")

        if not isinstance(body, (dict, list)):
            continue

        checked += 1
        keys = schema_fingerprint(body if isinstance(body, dict) else (body[0] if body else {}))
        field_count = len(keys)

        if field_count > _OVERFETCH_FIELD_THRESHOLD:
            issues.append(
                f"{entry.get('method','GET')} {path}: "
                f"{field_count} response fields (>{_OVERFETCH_FIELD_THRESHOLD} threshold)"
            )
        elif body_bytes > _OVERFETCH_BYTES_THRESHOLD:
            issues.append(
                f"{entry.get('method','GET')} {path}: "
                f"{body_bytes//1024}KB response body (>{_OVERFETCH_BYTES_THRESHOLD//1024}KB threshold)"
            )

    if not checked:
        return {
            "success": True,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "severity": "INFO",
            "log": "No structured JSON response bodies in captured traffic yet.",
            "recommendation": "Re-run capture with Phase 0.1 applied.",
        }

    success = len(issues) == 0
    return {
        "success": success,
        "status": "PASS" if success else "FAIL",
        "mode": "LIVE",
        "severity": "INFO" if success else "MEDIUM",
        "log": (
            f"Data overfetch OK — {checked} endpoints checked, all within field/size thresholds."
            if success else
            f"Overfetch detected on {len(issues)} endpoints: {'; '.join(issues[:4])}"
        ),
        "recommendation": (
            "Use field selection (GraphQL, sparse fieldsets, or ?fields= param) to reduce payload size."
            if not success else "N/A"
        ),
        "checked": checked,
        "issues": issues,
    }
