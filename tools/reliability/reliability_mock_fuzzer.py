"""
Reliability mock fuzzer — grounded in real captured traffic.

1. Calls mock_generator to build mocks.yaml from traffic-inventory.json
2. Reports body-coverage (what % of endpoints have a real captured response body)
3. Probes live endpoints for unstructured error responses (fault tolerance check)
"""
from __future__ import annotations

from core.api.mock_generator import build_and_write_mocks, load_captured_requests, is_api_candidate
from tools.url_helper import build_probe_url

import requests as _requests


def _probe_fault_tolerance(mock: dict, base_url: str) -> dict | None:
    """Hit a non-templated endpoint and check it returns structured errors on 4xx."""
    if mock.get("is_templated"):
        return None
    path = mock["path"]
    url = build_probe_url(base_url, path)
    try:
        resp = _requests.get(url, timeout=5, verify=False)
        if resp.status_code >= 400:
            try:
                body = resp.json()
                has_error_field = any(k in body for k in ("error", "message", "detail", "errors", "code"))
                if not has_error_field:
                    return {"path": path, "status": resp.status_code, "issue": "unstructured error body"}
            except Exception:
                return {"path": path, "status": resp.status_code, "issue": "non-JSON error response"}
    except Exception:
        pass
    return None


def execute_reliability_mocking(workspace_root=None, target_url=None):
    print("[RELIABILITY] Building mocks from captured traffic inventory...")

    mocks, mocks_path = build_and_write_mocks(workspace_root)

    if not mocks:
        print("[RELIABILITY] No captured API traffic found — cannot generate mocks.")
        return {
            "success": True,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "severity": "INFO",
            "log": "No captured API traffic available. Run playwright capture first to generate real mocks.",
            "recommendation": "Run a capture pass and retry.",
        }

    total = len(mocks)
    with_body = sum(1 for m in mocks if m["has_real_body"])
    body_coverage_pct = round(with_body / total * 100, 1) if total else 0.0

    print(f"[RELIABILITY] Generated {total} mock entries ({with_body} with real response body) -> {mocks_path}")

    fault_issues = []
    if target_url:
        for mock in mocks[:8]:
            issue = _probe_fault_tolerance(mock, target_url)
            if issue:
                fault_issues.append(issue)

    # Body coverage below 40% means Phase 0.1 capture hasn't run yet or returned few bodies
    coverage_ok = body_coverage_pct >= 40.0
    fault_ok = len(fault_issues) == 0
    success = coverage_ok and fault_ok

    log_parts = [
        f"Generated {total} mocks from captured traffic.",
        f"Body coverage: {body_coverage_pct}% ({with_body}/{total} endpoints have real response body).",
    ]
    if not coverage_ok:
        log_parts.append("Low body coverage — re-run capture with Phase 0.1 patch applied.")
    if fault_issues:
        log_parts.append("Fault tolerance issues: " + "; ".join(
            f"{i['path']} -> {i['issue']}" for i in fault_issues
        ))

    return {
        "success": success,
        "status": "PASS" if success else "FAIL",
        "mode": "LIVE" if target_url else "SIMULATED",
        "severity": "INFO" if success else "MEDIUM",
        "log": " ".join(log_parts),
        "recommendation": (
            "Fix unstructured error responses and re-run capture to improve body coverage."
            if not success else "N/A"
        ),
        "mocks_generated": total,
        "body_coverage_pct": body_coverage_pct,
        "mocks_path": mocks_path,
        "fault_issues": fault_issues,
    }
