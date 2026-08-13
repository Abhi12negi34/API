import json
import os
from datetime import datetime
from pathlib import Path

from reports.report_sanitizer import sanitize_report_tree


def _attribute_verdict(results_data):
    findings = results_data.get("findings", {}) if isinstance(results_data, dict) else {}
    if not findings:
        return "N/A"

    statuses = [str(details.get("status", "")).upper() for details in findings.values()]
    if statuses and all(status == "SKIPPED" for status in statuses):
        return "SKIPPED"
    if any(status == "FAIL" for status in statuses):
        return "FAIL"
    return "PASS"


class JSONReportGenerator:
    def __init__(self, output_dir="reports/output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate(self, raw_results, scorecard, final_score, tier, filepath="user_pass_certification_report.json", report_insights=None):
        print("[*] Generating Rich JSON Validation Report...")

        total_tools = sum(s["total_tools"] for s in scorecard.values())
        total_passed = sum(s["passed"] for s in scorecard.values())
        total_failed = sum(s["failed"] for s in scorecard.values())
        total_skipped = sum(s.get("skipped", 0) for s in scorecard.values())
        total_blockers = sum(s["blockers"] for s in scorecard.values())

        active_resilience = report_insights or raw_results.get("metadata", {}).get("active_resilience", {})
        target_url = raw_results.get("metadata", {}).get("target_url", "N/A")
        traffic_capture = raw_results.get("metadata", {}).get("traffic_capture", {})
        capture_profile = active_resilience.get("capture_profile", {}) if isinstance(active_resilience, dict) else {}
        coverage_profile = active_resilience.get("coverage_booster", {}) if isinstance(active_resilience, dict) else {}
        chaos_profile = active_resilience.get("chaos_profile", {}) if isinstance(active_resilience, dict) else {}
        pii_profile = active_resilience.get("pii_audit", {}) if isinstance(active_resilience, dict) else {}
        drift_profile = active_resilience.get("behavioral_drift", {}) if isinstance(active_resilience, dict) else {}
        execution_state = raw_results.get("metadata", {}).get("execution_state", "COMPLETED")
        execution_reason = raw_results.get("metadata", {}).get("execution_reason", "")

        detailed_findings = {}
        if isinstance(raw_results, dict):
            for attr, results_data in raw_results.items():
                if attr == "metadata" or not isinstance(results_data, dict):
                    continue

                findings = results_data.get("findings", {})
                if not isinstance(findings, dict):
                    findings = {}

                detailed_findings[attr] = {
                    "attribute_verdict": _attribute_verdict(results_data),
                    "findings": [
                        {
                            "tool_id": tool_id,
                            "success": details.get("success", False) if isinstance(details, dict) else False,
                            "status": details.get("status", "PASS" if details.get("success", False) else "FAIL") if isinstance(details, dict) else "FAIL",
                            "mode": details.get("mode", "LIVE") if isinstance(details, dict) else "LIVE",
                            "severity": details.get("severity", "INFO") if isinstance(details, dict) else "INFO",
                            "impacted_path": details.get("path", "-") if isinstance(details, dict) else "-",
                            "diagnostic_log": details.get("log", "") if isinstance(details, dict) else "",
                            "remediation_guidance": details.get("recommendation", "N/A") if isinstance(details, dict) else "N/A",
                        }
                        for tool_id, details in findings.items()
                    ],
                }

        report_data = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "agent_version": "2.4.0 (World-Class Elite Edition)",
                "target_url": target_url,
                "certification_tier": tier.upper(),
                "final_weighted_score": final_score,
                "active_resilience_index": active_resilience.get("resilience_index", 0.0) if isinstance(active_resilience, dict) else 0.0,
            },
            "service_mesh_discovery": {
                "total_apis_discovered": len(raw_results.get("metadata", {}).get("discovery_baseline", [])),
                "baseline": raw_results.get("metadata", {}).get("discovery_baseline", []),
            },
            "executive_metric_summary": {
                "total_tools_executed": total_tools,
                "total_passed": total_passed,
                "total_failed": total_failed,
                "total_skipped": total_skipped,
                "total_blockers": total_blockers,
                "pass_ratio_percent": round((total_passed / total_tools) * 100, 2) if total_tools > 0 else 0,
            },
            "user_pass_scorecard_breakdown": {
                attr: {
                    "score_percent": s["attribute_score"],
                    "weight": s["weight"],
                    "tools_passed": s["passed"],
                    "tools_failed": s["failed"],
                    "tools_skipped": s.get("skipped", 0),
                    "blocker_count": s["blockers"],
                    "verdict": s.get("verdict", "N/A"),
                }
                for attr, s in scorecard.items()
            },
            "detailed_findings_by_attribute": detailed_findings,
            "active_resilience_matrix": {
                "capture_profile": capture_profile,
                "coverage_booster": {
                    "source_path": coverage_profile.get("source_path"),
                    "generated_trace_count": coverage_profile.get("generated_trace_count", 0),
                    "generated_traces": coverage_profile.get("generated_traces", []),
                    "output_path": coverage_profile.get("path"),
                    "log": coverage_profile.get("log"),
                },
                "chaos_profile": {
                    "mutated_files": chaos_profile.get("mutated_files", []),
                    "mutations_applied": chaos_profile.get("mutations_applied", []),
                    "scenario": chaos_profile.get("scenario"),
                    "log": chaos_profile.get("log"),
                },
                "pii_audit": {
                    "files_scanned": pii_profile.get("files_scanned", 0),
                    "leaks_found": pii_profile.get("leaks_found", []),
                    "log": pii_profile.get("log"),
                },
                "behavioral_drift": {
                    "baseline_source": drift_profile.get("baseline_source"),
                    "behavioral_similarity_percent": drift_profile.get("behavioral_similarity_percent", 100.0),
                    "behavioral_drift_percent": drift_profile.get("behavioral_drift_percent", 0.0),
                    "matched_tools": drift_profile.get("matched_tools", 0),
                    "changed_tools": drift_profile.get("changed_tools", 0),
                    "new_tools": drift_profile.get("new_tools", 0),
                    "missing_tools": drift_profile.get("missing_tools", 0),
                    "log": drift_profile.get("log"),
                },
                "resilience_index": active_resilience.get("resilience_index", 0.0) if isinstance(active_resilience, dict) else 0.0,
            },
            "traffic_inventory": {
                "captured_request_count": traffic_capture.get("captured_request_count", 0) if isinstance(traffic_capture, dict) else 0,
                "unique_endpoint_count": traffic_capture.get("unique_endpoint_count", 0) if isinstance(traffic_capture, dict) else 0,
                "unique_hosts": traffic_capture.get("unique_hosts", []) if isinstance(traffic_capture, dict) else [],
                "captured_requests": traffic_capture.get("captured_requests", []) if isinstance(traffic_capture, dict) else [],
            },
            "execution_notice": {
                "state": execution_state,
                "reason": execution_reason,
                "requested_tool_count": raw_results.get("metadata", {}).get("requested_tool_count", 0),
                "resolved_tool_count": raw_results.get("metadata", {}).get("resolved_tool_count", 0),
                "unmapped_tool_count": raw_results.get("metadata", {}).get("unmapped_tool_count", 0),
            },
        }

        report_data = sanitize_report_tree(report_data, target_url)

        out_path = os.path.join(self.output_dir, filepath)
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=4)
        except PermissionError:
            fallback_name = f"{Path(filepath).stem}_clean{Path(filepath).suffix}"
            out_path = os.path.join(self.output_dir, fallback_name)
            print(f"[!] Report file is locked. Writing JSON output to {out_path}")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=4)

        print(f"[+] Rich JSON report with Discovery Baseline saved -> {out_path}")
        return out_path
