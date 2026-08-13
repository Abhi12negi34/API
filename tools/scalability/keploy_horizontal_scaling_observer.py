"""
Horizontal scaling observer — checks captured traffic for signs of
multi-instance issues: inconsistent responses for the same endpoint
across calls, missing idempotency on GETs, and cache inconsistency signals.
"""
from __future__ import annotations
from collections import defaultdict
from core.api.mock_generator import load_captured_requests, is_api_candidate, generalize_path, schema_fingerprint


def observe_horizontal_scaling(workspace_root=None):
    print("[SCALABILITY: Horizontal Scaling] Checking for multi-instance consistency signals...")

    entries = load_captured_requests(workspace_root)
    api_entries = [e for e in entries if is_api_candidate(e)]

    if not api_entries:
        return {
            "success": True, "status": "SKIPPED", "mode": "SIMULATED", "severity": "INFO",
            "log": "No captured API traffic. Run capture first.",
            "recommendation": "Run playwright capture and retry.",
        }

    # Group status codes by generalized path
    status_map: dict[str, set] = defaultdict(set)
    schema_map: dict[str, set] = defaultdict(set)

    for e in api_entries:
        key = f"{e.get('method','GET')} {generalize_path(str(e.get('path') or '/'))}"
        status = e.get("status")
        if status:
            status_map[key].add(status)
        body = e.get("response_body")
        if isinstance(body, dict):
            fp = frozenset(schema_fingerprint(body))
            if fp:
                schema_map[key].add(fp)

    issues = []
    # Flag endpoints that returned different status codes across calls (not counting 200 vs 304)
    for path, statuses in status_map.items():
        real_statuses = {s for s in statuses if s not in (304,)}
        success_codes = {s for s in real_statuses if 200 <= s < 300}
        error_codes = {s for s in real_statuses if s >= 400}
        if success_codes and error_codes:
            issues.append(f"{path}: inconsistent status codes {sorted(real_statuses)}")

    # Flag endpoints that returned different response schemas across calls
    for path, schemas in schema_map.items():
        if len(schemas) > 1:
            issues.append(f"{path}: schema drift across {len(schemas)} response variants")

    success = len(issues) == 0
    return {
        "success": success, "status": "PASS" if success else "FAIL",
        "mode": "LIVE", "severity": "INFO" if success else "HIGH",
        "log": (
            f"Horizontal scaling OK — {len(status_map)} endpoints consistent across "
            f"{len(api_entries)} captured calls." if success else
            f"Scaling consistency issues ({len(issues)}): {'; '.join(issues[:4])}"
        ),
        "recommendation": "Ensure shared session state, sticky sessions, or distributed cache for inconsistent endpoints." if not success else "N/A",
        "endpoints_checked": len(status_map),
        "issues": issues,
    }
