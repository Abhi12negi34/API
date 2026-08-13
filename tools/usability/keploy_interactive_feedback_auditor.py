"""
Interactive feedback auditor — checks that 4xx error responses contain
field-level validation details (RFC 7807 Problem Details), not generic messages.
"""
from __future__ import annotations
from core.api.mock_generator import load_captured_requests, is_api_candidate


_RFC7807_KEYS = {"type", "title", "status", "detail", "instance"}
_ACCEPTABLE_ERROR_KEYS = {"error", "message", "errors", "detail", "details", "code", "msg"}


def validate_interactive_feedback(workspace_root=None):
    print("[USABILITY: Interactive Feedback] Checking 4xx error response quality...")

    entries = load_captured_requests(workspace_root)
    error_entries = [
        e for e in entries
        if is_api_candidate(e)
        and 400 <= (e.get("status") or 0) < 500
        and isinstance(e.get("response_body"), dict)
    ]

    if not error_entries:
        return {
            "success": True, "status": "SKIPPED", "mode": "SIMULATED", "severity": "INFO",
            "log": "No 4xx responses with JSON bodies found in captured traffic.",
            "recommendation": "Trigger validation errors during capture (submit bad form data) to test error shape.",
        }

    issues = []
    for e in error_entries:
        body = e.get("response_body") or {}
        keys = {k.lower() for k in body}
        has_useful_error = bool(keys & _ACCEPTABLE_ERROR_KEYS)
        if not has_useful_error:
            issues.append(
                f"HTTP {e.get('status')} {e.get('path','?')}: "
                f"no error/message/detail key in response {sorted(keys)[:4]}"
            )

    success = len(issues) == 0
    return {
        "success": success, "status": "PASS" if success else "FAIL",
        "mode": "LIVE", "severity": "INFO" if success else "MEDIUM",
        "log": (
            f"Error feedback OK — {len(error_entries)} 4xx responses all contain descriptive error fields."
            if success else
            f"Poor error feedback on {len(issues)}/{len(error_entries)} responses: {'; '.join(issues[:3])}"
        ),
        "recommendation": "Return RFC 7807 Problem Details (type, title, status, detail) on all 4xx responses." if not success else "N/A",
        "error_responses_checked": len(error_entries),
        "issues": issues,
    }
