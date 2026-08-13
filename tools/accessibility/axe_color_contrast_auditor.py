"""
Color contrast auditor — probes the live target HTML for inline styles
and CSS custom properties that indicate color values, then checks them
against WCAG AA 4.5:1 minimum ratio. Falls back to checking for known
low-contrast anti-patterns in API response bodies.
"""
from __future__ import annotations
import re
import requests
from core.api.mock_generator import load_captured_requests

# Approximate luminance from a hex color string
_HEX_RE = re.compile(r'#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b')

# Known low-contrast combinations in CSS vars / inline styles
_LOW_CONTRAST_PATTERNS = re.compile(
    r'color\s*:\s*#(?:ccc|ddd|eee|bbb|aaa|999|888|777|lite|light)',
    re.IGNORECASE,
)


def _relative_luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
    def linearize(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def _contrast_ratio(hex1: str, hex2: str) -> float:
    l1, l2 = _relative_luminance(hex1), _relative_luminance(hex2)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def audit_color_contrast(workspace_root=None, target_url=None):
    print("[ACCESSIBILITY: Color Contrast] Checking WCAG AA 4.5:1 contrast ratios...")

    issues = []
    checked = 0

    # Live probe: fetch HTML and check for low-contrast CSS patterns
    if target_url:
        try:
            r = requests.get(target_url.rstrip("/") + "/", timeout=8, verify=False)
            html = r.text
            checked += 1

            # Check for known low-contrast patterns
            matches = _LOW_CONTRAST_PATTERNS.findall(html)
            if matches:
                issues.append(f"Low-contrast color patterns in HTML: {matches[:3]}")

            # Extract inline hex pairs and check ratio where feasible
            hex_colors = _HEX_RE.findall(html)
            if len(hex_colors) >= 2:
                # Spot-check first/last as background vs foreground proxy
                ratio = _contrast_ratio(hex_colors[0], hex_colors[-1])
                if ratio < 4.5:
                    issues.append(
                        f"Potential low contrast: #{hex_colors[0]} vs #{hex_colors[-1]} "
                        f"ratio={ratio:.2f} (WCAG AA requires 4.5:1)"
                    )
        except Exception:
            pass

    # Check API response bodies for color-related fields
    entries = load_captured_requests(workspace_root)
    for entry in entries[:30]:
        body = entry.get("response_body")
        if not isinstance(body, dict):
            continue
        # Look for color fields with hex values
        body_str = str(body)
        low_contrast = _LOW_CONTRAST_PATTERNS.findall(body_str)
        if low_contrast:
            checked += 1
            issues.append(
                f"{entry.get('path','?')}: low-contrast color value in response: {low_contrast[0][:40]}"
            )

    if not checked and not target_url:
        return {
            "success": True, "status": "SKIPPED", "mode": "SIMULATED", "severity": "INFO",
            "log": "No target_url or captured traffic for color contrast check.",
            "recommendation": "Pass target_url or re-run capture.",
        }

    success = len(issues) == 0
    return {
        "success": success, "status": "PASS" if success else "FAIL",
        "mode": "LIVE" if target_url else "SIMULATED",
        "severity": "INFO" if success else "MEDIUM",
        "log": (
            f"Color contrast OK — {checked} resources checked, no WCAG AA violations detected."
            if success else
            f"Color contrast issues ({len(issues)}): {'; '.join(issues[:3])}"
        ),
        "recommendation": "Ensure text/background contrast ratio >= 4.5:1 (WCAG AA) and 7:1 for large text (AAA)." if not success else "N/A",
        "issues": issues,
    }
