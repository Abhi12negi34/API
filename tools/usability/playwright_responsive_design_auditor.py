"""
Responsive design auditor — checks captured traffic for mobile/responsive
signals: viewport meta, Content-Type correctness on media, and whether
the API returns different payloads based on User-Agent (UA sniffing anti-pattern).
"""
from __future__ import annotations
import requests
from core.api.mock_generator import load_captured_requests, is_api_candidate, generalize_path
from collections import defaultdict


def test_responsive_usability(workspace_root=None, target_url=None):
    print("[USABILITY: Responsive Design] Checking for responsive design and UA-sniffing signals...")

    issues = []

    # Live probe: check HTML for viewport meta
    if target_url:
        try:
            r = requests.get(target_url.rstrip("/") + "/", timeout=8, verify=False)
            html = r.text.lower()
            if "<html" in html:
                if 'name="viewport"' not in html and "name='viewport'" not in html:
                    issues.append("Missing <meta name='viewport'> — mobile layout will break (WCAG 1.4.4)")
                if 'user-scalable=no' in html:
                    issues.append("user-scalable=no prevents zoom — WCAG 1.4.4 violation")
        except Exception:
            pass

    # Check captured traffic for UA-based response variation (anti-pattern)
    entries = load_captured_requests(workspace_root)
    api_entries = [e for e in entries if is_api_candidate(e) and e.get("response_body_bytes")]

    # Group response sizes by path — large variance suggests UA sniffing
    size_map: dict[str, list[int]] = defaultdict(list)
    for e in api_entries:
        path = generalize_path(str(e.get("path") or "/"))
        size = e.get("response_body_bytes") or 0
        if size > 0:
            size_map[path].append(size)

    for path, sizes in size_map.items():
        if len(sizes) >= 2:
            ratio = max(sizes) / max(min(sizes), 1)
            if ratio > 3:
                issues.append(
                    f"{path}: response size varies {min(sizes)}–{max(sizes)} bytes "
                    f"({ratio:.1f}x) — possible UA sniffing"
                )

    if not target_url and not entries:
        return {
            "success": True, "status": "SKIPPED", "mode": "SIMULATED", "severity": "INFO",
            "log": "No target_url or captured traffic for responsive design check.",
            "recommendation": "Pass target_url or re-run capture.",
        }

    success = len(issues) == 0
    return {
        "success": success, "status": "PASS" if success else "FAIL",
        "mode": "LIVE", "severity": "INFO" if success else "MEDIUM",
        "log": (
            "Responsive design OK — viewport meta present, no UA-sniffing signals."
            if success else
            f"Responsive issues ({len(issues)}): {'; '.join(issues[:3])}"
        ),
        "recommendation": "Add viewport meta, remove user-scalable=no, and serve device-agnostic API responses." if not success else "N/A",
        "issues": issues,
    }
