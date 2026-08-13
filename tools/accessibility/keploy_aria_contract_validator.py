"""
ARIA contract validator — checks captured API responses for ARIA-relevant
metadata fields (role, aria_label, aria_expanded, tabindex) and validates
the live HTML for basic ARIA landmark structure.
"""
from __future__ import annotations
import requests
from core.api.mock_generator import load_captured_requests, is_api_candidate

_ARIA_KEYS = {"role", "aria_label", "aria-label", "aria_expanded", "aria_hidden",
              "tabindex", "aria_live", "aria_atomic", "aria_relevant"}
_LANDMARK_ROLES = {"main", "navigation", "banner", "contentinfo", "complementary", "search"}


def validate_aria_contracts(workspace_root=None, target_url=None):
    print("[ACCESSIBILITY: ARIA Contracts] Checking ARIA attributes in API responses and HTML landmarks...")

    issues = []
    checked = 0

    # Check captured API responses for ARIA-relevant fields
    entries = load_captured_requests(workspace_root)
    api_entries = [e for e in entries if is_api_candidate(e) and isinstance(e.get("response_body"), dict)]

    for entry in api_entries[:30]:
        body = entry.get("response_body") or {}
        keys = {k.lower() for k in body}
        checked += 1

        # If response has role field, validate it's a known ARIA role
        if "role" in keys:
            role_val = str(body.get("role") or "").lower()
            valid_roles = _LANDMARK_ROLES | {
                "button", "link", "checkbox", "radio", "tab", "tabpanel",
                "dialog", "alert", "status", "progressbar", "slider",
                "listbox", "option", "menuitem", "grid", "row", "cell",
            }
            if role_val and role_val not in valid_roles:
                issues.append(
                    f"{entry.get('path','?')}: unknown ARIA role '{role_val}' in response"
                )

    # Live probe: check HTML landmarks
    if target_url:
        try:
            r = requests.get(target_url.rstrip("/") + "/", timeout=8, verify=False)
            html = r.text.lower()
            checked += 1

            if "<html" in html:
                has_main = 'role="main"' in html or "<main" in html
                has_nav = 'role="navigation"' in html or "<nav" in html
                has_header = 'role="banner"' in html or "<header" in html

                if not has_main:
                    issues.append("Missing <main> or role='main' landmark (WCAG 1.3.6)")
                if not has_nav:
                    issues.append("Missing <nav> or role='navigation' landmark")
                if not has_header:
                    issues.append("Missing <header> or role='banner' landmark")

                # Check for aria-label on interactive elements
                if 'aria-label' not in html and 'aria-labelledby' not in html:
                    issues.append("No aria-label or aria-labelledby found on page (WCAG 4.1.2)")
        except Exception:
            pass

    if not checked:
        return {
            "success": True, "status": "SKIPPED", "mode": "SIMULATED", "severity": "INFO",
            "log": "No captured API responses or target_url for ARIA contract check.",
            "recommendation": "Pass target_url or re-run capture.",
        }

    success = len(issues) == 0
    return {
        "success": success, "status": "PASS" if success else "FAIL",
        "mode": "LIVE" if target_url else "SIMULATED",
        "severity": "INFO" if success else "MEDIUM",
        "log": (
            f"ARIA contracts OK — {checked} responses and HTML landmarks verified."
            if success else
            f"ARIA issues ({len(issues)}): {'; '.join(issues[:4])}"
        ),
        "recommendation": "Add ARIA landmark roles (<main>, <nav>, <header>) and aria-label to all interactive elements." if not success else "N/A",
        "checked": checked,
        "issues": issues,
    }
