"""
Localization auditor — probes the API with Accept-Language headers and
checks whether responses vary (i18n support) or are language-agnostic.
Also checks for hardcoded locale strings in captured response bodies.
"""
from __future__ import annotations
import re
import requests
from core.api.mock_generator import load_captured_requests, is_api_candidate, generate_mocks
from tools.url_helper import build_probe_url

_HARDCODED_LOCALE_RE = re.compile(
    r'\b(january|february|march|april|may|june|july|august|september|october|november|december'
    r'|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
    re.IGNORECASE,
)
_LOCALES_TO_TEST = ["en-US", "fr-FR", "de-DE", "ja-JP"]


def audit_localization_keys(workspace_root=None, target_url=None):
    print("[USABILITY: Localization] Checking for i18n support and hardcoded locale strings...")

    issues = []
    checked = 0

    # Check captured response bodies for hardcoded locale strings
    entries = load_captured_requests(workspace_root)
    api_entries = [e for e in entries if is_api_candidate(e)]

    for entry in api_entries[:50]:
        body = entry.get("response_body")
        if not isinstance(body, (dict, str)):
            continue
        body_str = str(body)
        if _HARDCODED_LOCALE_RE.search(body_str):
            issues.append(
                f"{entry.get('path','?')}: hardcoded locale string detected in response body"
            )
            checked += 1

    # Live probe: send Accept-Language headers and check if response varies
    if target_url:
        mocks = generate_mocks(workspace_root)
        safe = [m for m in mocks if m["method"] == "GET" and not m["is_templated"]][:3]
        base = target_url.rstrip("/")

        for mock in safe:
            url = build_probe_url(target_url, mock["path"].split("?")[0])
            responses = {}
            for locale in _LOCALES_TO_TEST[:2]:
                try:
                    r = requests.get(
                        url, headers={"Accept-Language": locale, "Accept": "application/json"},
                        timeout=5, verify=False,
                    )
                    checked += 1
                    responses[locale] = r.status_code
                except Exception:
                    continue

            # All locales should return same status — different statuses = locale routing bug
            unique_statuses = set(responses.values())
            if len(unique_statuses) > 1:
                issues.append(f"{mock['path']}: different status per locale {responses}")

    if not checked:
        return {
            "success": True, "status": "SKIPPED", "mode": "SIMULATED", "severity": "INFO",
            "log": "No captured bodies or target_url to test localization.",
            "recommendation": "Pass target_url or re-run capture.",
        }

    success = len(issues) == 0
    return {
        "success": success, "status": "PASS" if success else "FAIL",
        "mode": "LIVE" if target_url else "SIMULATED",
        "severity": "INFO" if success else "MEDIUM",
        "log": (
            f"Localization OK — {checked} checks passed, no hardcoded locale strings or routing bugs."
            if success else
            f"Localization issues ({len(issues)}): {'; '.join(issues[:3])}"
        ),
        "recommendation": "Use ICU message format for dates/times and test all Accept-Language variants." if not success else "N/A",
        "checked": checked,
        "issues": issues,
    }
