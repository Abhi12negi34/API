"""
UX consistency auditor — checks captured API error responses for
consistent error shape (same keys across all 4xx responses), and
checks content-type consistency across same-path repeated calls.
"""
from __future__ import annotations
from collections import defaultdict
from core.api.mock_generator import load_captured_requests, is_api_candidate, generalize_path


def audit_ux_consistency(workspace_root=None):
    print("[USABILITY: UX Consistency] Checking API response shape consistency...")

    entries = load_captured_requests(workspace_root)
    api_entries = [e for e in entries if is_api_candidate(e)]

    if not api_entries:
        return {
            "success": True, "status": "SKIPPED", "mode": "SIMULATED", "severity": "INFO",
            "log": "No captured API traffic. Run capture first.",
            "recommendation": "Run playwright capture and retry.",
        }

    issues = []

    # Check error response consistency — all 4xx should have same top-level keys
    error_shapes: list[set] = []
    for e in api_entries:
        status = e.get("status") or 0
        body = e.get("response_body")
        if 400 <= status < 500 and isinstance(body, dict):
            error_shapes.append(set(body.keys()))

    if len(error_shapes) >= 2:
        first = error_shapes[0]
        for i, shape in enumerate(error_shapes[1:], 1):
            if shape != first:
                issues.append(
                    f"Inconsistent error response shape: {sorted(first)} vs {sorted(shape)}"
                )
                break  # one example is enough

    # Check content-type consistency per endpoint
    ct_map: dict[str, set] = defaultdict(set)
    for e in api_entries:
        ct = str(e.get("response_content_type") or "").split(";")[0].strip()
        if ct:
            key = generalize_path(str(e.get("path") or "/"))
            ct_map[key].add(ct)

    inconsistent_ct = {k: sorted(v) for k, v in ct_map.items() if len(v) > 1}
    if inconsistent_ct:
        for path, cts in list(inconsistent_ct.items())[:3]:
            issues.append(f"{path}: mixed content-types {cts}")

    success = len(issues) == 0
    return {
        "success": success, "status": "PASS" if success else "FAIL",
        "mode": "LIVE", "severity": "INFO" if success else "MEDIUM",
        "log": (
            f"UX consistency OK — {len(api_entries)} responses checked, "
            f"{len(error_shapes)} error shapes consistent."
            if success else
            f"UX consistency issues ({len(issues)}): {'; '.join(issues[:3])}"
        ),
        "recommendation": "Standardise error response shape (RFC 7807: type, title, status, detail) and content-type across all endpoints." if not success else "N/A",
        "error_shapes_checked": len(error_shapes),
        "inconsistent_content_types": inconsistent_ct,
        "issues": issues,
    }
