import json
import os
from pathlib import Path


def _workspace_root(workspace_root=None):
    return Path(workspace_root or os.getcwd()).resolve()


def _load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _current_findings_map(current_results):
    findings = {}
    for attribute, payload in (current_results or {}).items():
        if attribute == "metadata" or not isinstance(payload, dict):
            continue
        for tool_id, details in payload.get("findings", {}).items():
            findings[tool_id] = {
                "status": str(details.get("status", "")).upper(),
                "success": bool(details.get("success", False)),
            }
    return findings


def _baseline_findings_map(report_data):
    findings = {}
    for attr_payload in (report_data or {}).get("detailed_findings_by_attribute", {}).values():
        for item in attr_payload.get("findings", []):
            tool_id = item.get("tool_id")
            if not tool_id:
                continue
            findings[tool_id] = {
                "status": str(item.get("status", "")).upper(),
                "success": bool(item.get("success", False)),
            }
    return findings


def _candidate_paths(workspace_root=None, baseline_report_path=None):
    candidates = []
    if baseline_report_path:
        candidates.append(Path(baseline_report_path))

    root = _workspace_root(workspace_root)
    candidates.extend(
        [
            root / "keploy" / "reports" / "report.json",
            root / "reports" / "output" / "user_pass_certification_report.json",
        ]
    )

    seen = set()
    ordered = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        ordered.append(resolved)
    return ordered


def calculate_behavioral_drift(current_results, baseline_report_path=None, workspace_root=None):
    """
    Compares the current tool outcomes against the latest available baseline report.
    The score is a similarity percentage where 100 means no behavioral drift.
    """
    baseline_path = None
    baseline_data = None
    for candidate in _candidate_paths(workspace_root=workspace_root, baseline_report_path=baseline_report_path):
        if candidate.exists():
            baseline_path = candidate
            baseline_data = _load_json(candidate)
            break

    if baseline_data is None:
        return {
            "success": True,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "severity": "INFO",
            "path": str(baseline_path) if baseline_path else "N/A",
            "log": "No baseline report found. Behavioral drift certification deferred until a golden report exists.",
            "recommendation": "Persist a baseline report so future runs can be compared for drift.",
            "baseline_source": None,
            "behavioral_similarity_percent": 100.0,
            "behavioral_drift_percent": 0.0,
            "matched_tools": 0,
            "changed_tools": 0,
            "new_tools": 0,
            "missing_tools": 0,
        }

    current_map = _current_findings_map(current_results)
    baseline_map = _baseline_findings_map(baseline_data)
    union_tools = sorted(set(current_map) | set(baseline_map))

    if not union_tools:
        similarity = 100.0
        matched = changed = new_tools = missing = 0
    else:
        score_total = 0.0
        matched = changed = new_tools = missing = 0
        for tool_id in union_tools:
            current = current_map.get(tool_id)
            baseline = baseline_map.get(tool_id)
            if current and baseline:
                if current == baseline:
                    score_total += 1.0
                    matched += 1
                elif current["status"] == baseline["status"] and current["success"] == baseline["success"]:
                    score_total += 0.85
                    matched += 1
                else:
                    changed += 1
            elif current and not baseline:
                score_total += 0.75
                new_tools += 1
            else:
                missing += 1

        similarity = round((score_total / len(union_tools)) * 100, 1)

    drift = round(100 - similarity, 1)
    severity = "INFO"
    success = similarity >= 80.0
    if similarity < 80.0:
        severity = "HIGH"
    elif similarity < 90.0:
        severity = "MEDIUM"
    elif similarity < 95.0:
        severity = "LOW"

    return {
        "success": success,
        "status": "PASS" if success else "FAIL",
        "mode": "SIMULATED",
        "severity": severity,
        "path": str(baseline_path) if baseline_path else "N/A",
        "log": f"Behavioral similarity {similarity:.1f}% across {len(union_tools)} tool(s). Drift gap {drift:.1f}%.",
        "recommendation": "N/A" if success else "Review changed tool behavior, mock outcomes, and response contracts against the golden baseline.",
        "baseline_source": str(baseline_path) if baseline_path else None,
        "behavioral_similarity_percent": similarity,
        "behavioral_drift_percent": drift,
        "matched_tools": matched,
        "changed_tools": changed,
        "new_tools": new_tools,
        "missing_tools": missing,
    }
