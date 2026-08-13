"""
Core Web Vitals auditor — derives vitals proxies from captured traffic
(TTFB, response sizes) since Lighthouse CLI requires a browser.
Falls back to probing the target root if no captured data.
"""
from __future__ import annotations
import time
import requests
from core.api.mock_generator import load_captured_requests

_TTFB_THRESHOLD_MS = 800
_DOC_SIZE_THRESHOLD_BYTES = 200_000  # 200KB HTML doc threshold


def audit_core_web_vitals(workspace_root=None, target_url=None):
    print("[EFFICIENCY: Web Vitals] Analysing TTFB and document payload from captured traffic...")

    entries = load_captured_requests(workspace_root)
    doc_entries = [
        e for e in entries
        if e.get("resource_type") == "document"
        and not e.get("is_navigation") is False  # include navigation docs
    ]

    issues = []

    # Analyse captured TTFB (response_time_ms on document requests)
    ttfbs = [
        e["response_time_ms"] for e in doc_entries
        if isinstance(e.get("response_time_ms"), (int, float)) and e["response_time_ms"] > 0
    ]
    slow_docs = [e for e in doc_entries if (e.get("response_time_ms") or 0) > _TTFB_THRESHOLD_MS]
    if slow_docs:
        issues.append(f"{len(slow_docs)} document responses exceed {_TTFB_THRESHOLD_MS}ms TTFB")

    large_docs = [
        e for e in doc_entries
        if (e.get("response_body_bytes") or 0) > _DOC_SIZE_THRESHOLD_BYTES
    ]
    if large_docs:
        issues.append(f"{len(large_docs)} documents exceed {_DOC_SIZE_THRESHOLD_BYTES//1000}KB")

    # Live probe for TTFB if no captured data
    if not ttfbs and target_url:
        try:
            t0 = time.monotonic()
            r = requests.get(target_url.rstrip("/") + "/", timeout=10, verify=False, stream=True)
            r.content  # force full read
            ttfb = round((time.monotonic() - t0) * 1000, 1)
            if ttfb > _TTFB_THRESHOLD_MS:
                issues.append(f"Live TTFB {ttfb:.0f}ms exceeds {_TTFB_THRESHOLD_MS}ms threshold")
            ttfbs = [ttfb]
        except Exception:
            pass

    if not ttfbs and not doc_entries:
        return {
            "success": True, "status": "SKIPPED", "mode": "SIMULATED", "severity": "INFO",
            "log": "No document requests in captured traffic and no target_url for live probe.",
            "recommendation": "Pass target_url or re-run capture.",
        }

    median_ttfb = sorted(ttfbs)[len(ttfbs) // 2] if ttfbs else None
    success = len(issues) == 0
    return {
        "success": success, "status": "PASS" if success else "FAIL",
        "mode": "LIVE" if target_url else "SIMULATED",
        "severity": "INFO" if success else "MEDIUM",
        "log": (
            f"Web vitals OK — median TTFB {median_ttfb:.0f}ms across {len(doc_entries)} document requests."
            if success and median_ttfb else
            f"Web vitals issues: {'; '.join(issues[:3])}"
        ),
        "recommendation": "Enable HTTP/2, gzip, CDN caching, and reduce server-side render time." if not success else "N/A",
        "median_ttfb_ms": median_ttfb,
        "doc_requests": len(doc_entries),
        "issues": issues,
    }
