"""
Accessibility JSON auditor — checks captured API response bodies for
fields that screen readers depend on: user_message, error descriptions,
label fields, and internationalization keys.
"""
from __future__ import annotations
from core.api.mock_generator import load_captured_requests, is_api_candidate

_SCREEN_READER_KEYS = {"user_message", "message", "description", "label", "title", "alt", "caption"}
_ERROR_KEYS = {"error", "errors", "detail", "details", "code"}


def audit_accessibility_semantics(workspace_root=None):
    print("[ACCESSIBILITY: JSON Semantics] Checking API responses for screen-reader-friendly fields...")

    entries = load_captured_requests(workspace_root)
    api_entries = [e for e in entries if is_api_candidate(e) and isinstance(e.get("response_body"), dict)]

    if not api_entries:
        return {
            "success": True, "status": "SKIPPED", "mode": "SIMULATED", "severity": "INFO",
            "log": "No captured API responses with JSON bodies. Re-run capture with Phase 0.1 applied.",
            "recommendation": "Run a fresh capture to populate response bodies.",
        }

    issues = []
    checked = 0

    for entry in api_entries[:40]:
        body = entry.get("response_body") or {}
        status = entry.get("status") or 200
        keys = {k.lower() for k in body}
        checked += 1

        # Error responses should have human-readable message fields
        if status >= 400:
            has_human_message = bool(keys & (_SCREEN_READER_KEYS | _ERROR_KEYS))
            if not has_human_message:
                issues.append(
                    f"HTTP {status} {entry.get('path','?')}: no human-readable error field "
                    f"({sorted(keys)[:4]})"
                )

        # Responses with image/media arrays should have alt/caption
        if isinstance(body.get("items") or body.get("data") or body.get("results"), list):
            items = body.get("items") or body.get("data") or body.get("results") or []
            if items and isinstance(items[0], dict):
                item_keys = {k.lower() for k in items[0]}
                has_media = bool(item_keys & {"image", "img", "photo", "thumbnail", "url", "src"})
                has_alt = bool(item_keys & {"alt", "alt_text", "caption", "description"})
                if has_media and not has_alt:
                    issues.append(
                        f"{entry.get('path','?')}: media items missing alt/caption field"
                    )

    success = len(issues) == 0
    return {
        "success": success, "status": "PASS" if success else "FAIL",
        "mode": "LIVE", "severity": "INFO" if success else "MEDIUM",
        "log": (
            f"JSON accessibility OK — {checked} responses checked, all error responses have human-readable fields."
            if success else
            f"JSON accessibility issues ({len(issues)}): {'; '.join(issues[:4])}"
        ),
        "recommendation": "Add 'message' or 'description' to all error responses, and 'alt'/'caption' to media item arrays." if not success else "N/A",
        "responses_checked": checked,
        "issues": issues,
    }
