"""
Keyboard navigation auditor — checks live HTML for keyboard accessibility
signals: focusable elements, skip links, tabindex usage, and form labels.
Checks captured API responses for interactive component metadata.
"""
from __future__ import annotations
import re
import requests
from core.api.mock_generator import load_captured_requests, is_api_candidate

_TABINDEX_POSITIVE_RE = re.compile(r'tabindex=["\']?([1-9]\d*)["\']?', re.IGNORECASE)
_OUTLINE_NONE_RE = re.compile(r'outline\s*:\s*none|outline\s*:\s*0', re.IGNORECASE)


def audit_keyboard_navigation(workspace_root=None, target_url=None):
    print("[ACCESSIBILITY: Keyboard Navigation] Checking focusability and keyboard access signals...")

    issues = []
    checked = 0

    if target_url:
        try:
            r = requests.get(target_url.rstrip("/") + "/", timeout=8, verify=False)
            html = r.text
            lower_html = html.lower()
            checked += 1

            # Skip navigation link
            has_skip = (
                'href="#main"' in lower_html
                or 'href="#content"' in lower_html
                or 'skip' in lower_html[:2000]
            )
            if not has_skip:
                issues.append("No skip-navigation link found (WCAG 2.4.1)")

            # Positive tabindex is an anti-pattern (disrupts natural tab order)
            positive_tabindex = _TABINDEX_POSITIVE_RE.findall(html)
            if positive_tabindex:
                issues.append(
                    f"Positive tabindex values found {positive_tabindex[:3]} — disrupts natural tab order (WCAG 2.4.3)"
                )

            # outline:none removes focus ring visibility
            if _OUTLINE_NONE_RE.search(html):
                issues.append("CSS outline:none detected — removes visible focus ring (WCAG 2.4.7)")

            # Forms should have associated labels
            input_count = lower_html.count("<input")
            label_count = lower_html.count("<label")
            aria_label_count = lower_html.count("aria-label")
            if input_count > 0 and (label_count + aria_label_count) < input_count:
                issues.append(
                    f"{input_count} inputs but only {label_count + aria_label_count} labels/aria-labels (WCAG 1.3.1)"
                )
        except Exception:
            pass

    # Check API responses for keyboard-relevant interactive metadata
    entries = load_captured_requests(workspace_root)
    for entry in entries[:20]:
        body = entry.get("response_body")
        if not isinstance(body, dict):
            continue
        checked += 1
        # Buttons/links without labels are inaccessible
        for item in (body.get("actions") or body.get("buttons") or body.get("links") or []):
            if isinstance(item, dict):
                has_label = any(k in item for k in ("label", "text", "aria_label", "title"))
                if not has_label:
                    issues.append(
                        f"{entry.get('path','?')}: interactive item missing label field: {list(item.keys())[:4]}"
                    )
                    break

    if not checked:
        return {
            "success": True, "status": "SKIPPED", "mode": "SIMULATED", "severity": "INFO",
            "log": "No target_url or captured traffic for keyboard navigation check.",
            "recommendation": "Pass target_url or re-run capture.",
        }

    success = len(issues) == 0
    return {
        "success": success, "status": "PASS" if success else "FAIL",
        "mode": "LIVE" if target_url else "SIMULATED",
        "severity": "INFO" if success else "MEDIUM",
        "log": (
            f"Keyboard navigation OK — {checked} resources checked."
            if success else
            f"Keyboard navigation issues ({len(issues)}): {'; '.join(issues[:4])}"
        ),
        "recommendation": "Add skip-nav links, remove outline:none, fix positive tabindex, and ensure all inputs have labels." if not success else "N/A",
        "checked": checked,
        "issues": issues,
    }
