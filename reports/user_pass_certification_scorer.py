import json
import os
from .generators.pdf_generator import PDFReportGenerator
from .generators.excel_generator import ExcelReportGenerator
from .generators.json_generator import JSONReportGenerator

# Canonical USER PASS attribute order
USER_PASS_ORDER = [
    "usability", "security", "efficiency", "reliability",
    "performance", "accessibility", "scalability", "stability"
]

SEVERITY_WEIGHTS = {
    "CRITICAL": 0.0,
    "HIGH": 0.3,
    "MEDIUM": 0.6,
    "LOW": 0.8,
    "INFO": 1.0,
    "N/A": 1.0
}


def _parse_json_blob(value):
    if not isinstance(value, str):
        return None

    raw = value.strip()
    if not raw:
        return None

    try:
        return json.loads(raw)
    except Exception:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(raw):
        if char not in "{[":
            continue
        try:
            parsed, _ = decoder.raw_decode(raw[index:])
            return parsed
        except Exception:
            continue

    return None

class CertificationScorer:
    def __init__(self, weights):
        self.weights = weights
        self.pdf_gen = PDFReportGenerator()
        self.excel_gen = ExcelReportGenerator()
        self.json_gen = JSONReportGenerator()

    def _normalize_results_payload(self, results_dict):
        if isinstance(results_dict, str):
            parsed = _parse_json_blob(results_dict)
            if isinstance(parsed, dict):
                results_dict = parsed
            elif isinstance(parsed, list):
                results_dict = {"scenarios": parsed}
            else:
                return {}
        elif not isinstance(results_dict, dict):
            return {}

        normalized = dict(results_dict)
        metadata = normalized.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        else:
            metadata = dict(metadata)
        normalized["metadata"] = metadata

        raw_output = normalized.get("raw_output")
        if isinstance(raw_output, str):
            parsed = _parse_json_blob(raw_output)
            if isinstance(parsed, dict):
                normalized = parsed
                metadata = normalized.get("metadata")
                if not isinstance(metadata, dict):
                    metadata = {}
                else:
                    metadata = dict(metadata)
                normalized["metadata"] = metadata
            elif isinstance(parsed, list):
                normalized = {"scenarios": parsed, "metadata": metadata}

        def _first_list(*candidates):
            for candidate in candidates:
                if isinstance(candidate, list) and candidate:
                    return candidate
            return []

        discovery_baseline = _first_list(
            metadata.get("discovery_baseline"),
            metadata.get("service_mesh_discovery", {}).get("baseline") if isinstance(metadata.get("service_mesh_discovery"), dict) else None,
            normalized.get("discovered_apis"),
            normalized.get("baseline"),
            metadata.get("discovered_apis"),
        )
        if discovery_baseline:
            metadata["discovery_baseline"] = discovery_baseline
            service_mesh = metadata.get("service_mesh_discovery")
            if not isinstance(service_mesh, dict):
                service_mesh = {}
            service_mesh["baseline"] = discovery_baseline
            service_mesh["total_apis_discovered"] = len(discovery_baseline)
            metadata["service_mesh_discovery"] = service_mesh

        traffic_capture = metadata.get("traffic_capture")
        if not isinstance(traffic_capture, dict):
            traffic_capture = {}

        traffic_requests = _first_list(
            traffic_capture.get("captured_requests"),
            normalized.get("traffic_requests"),
            normalized.get("captured_requests"),
            metadata.get("traffic_requests"),
            metadata.get("traffic_inventory", {}).get("captured_requests") if isinstance(metadata.get("traffic_inventory"), dict) else None,
        )
        if traffic_requests:
            captured_requests = [request for request in traffic_requests if isinstance(request, dict)]
            traffic_capture["captured_requests"] = captured_requests
            traffic_capture["captured_request_count"] = len(captured_requests)
            traffic_capture["unique_endpoint_count"] = len({
                (
                    str(request.get("method") or "").upper(),
                    str(request.get("path") or "").strip(),
                    str(request.get("host") or "").strip(),
                )
                for request in captured_requests
            })
            traffic_capture["unique_hosts"] = sorted({
                str(request.get("host") or "").strip()
                for request in captured_requests
                if str(request.get("host") or "").strip()
            })
            metadata["traffic_capture"] = traffic_capture

        active_resilience = metadata.get("active_resilience")
        if not isinstance(active_resilience, dict) or not active_resilience:
            for candidate in (
                normalized.get("active_resilience"),
                normalized.get("active_resilience_matrix"),
            ):
                if isinstance(candidate, dict) and candidate:
                    active_resilience = candidate
                    break

        if not isinstance(active_resilience, dict) or not active_resilience:
            active_resilience = {
                "capture_profile": traffic_capture if traffic_capture else {},
                "coverage_booster": {
                    "source_path": "N/A",
                    "generated_trace_count": len(discovery_baseline) if isinstance(discovery_baseline, list) else 0,
                    "generated_traces": discovery_baseline if isinstance(discovery_baseline, list) else [],
                    "output_path": "N/A",
                    "log": "Derived from merged execution payload.",
                },
                "chaos_profile": {
                    "mutated_files": [],
                    "mutations_applied": [],
                    "scenario": None,
                    "log": "N/A",
                },
                "pii_audit": {
                    "files_scanned": 0,
                    "leaks_found": [],
                    "log": "N/A",
                },
                "behavioral_drift": {
                    "baseline_source": "N/A",
                    "behavioral_similarity_percent": 100.0,
                    "behavioral_drift_percent": 0.0,
                    "matched_tools": 0,
                    "changed_tools": 0,
                    "new_tools": 0,
                    "missing_tools": 0,
                    "log": "Derived from merged execution payload.",
                },
                "resilience_index": 0.0,
            }

        metadata["active_resilience"] = active_resilience
        return normalized

    def _build_active_resilience_summary(self, results_dict):
        metadata = results_dict.get("metadata", {}) if isinstance(results_dict, dict) else {}
        active = metadata.get("active_resilience", {}) if isinstance(metadata, dict) else {}
        if not active:
            return {}

        capture = active.get("capture_profile", {}) if isinstance(active, dict) else {}
        coverage = active.get("coverage_booster", {}) if isinstance(active, dict) else {}
        chaos = active.get("chaos_profile", {}) if isinstance(active, dict) else {}
        pii = active.get("pii_audit", {}) if isinstance(active, dict) else {}
        drift = active.get("behavioral_drift", {}) if isinstance(active, dict) else {}

        return {
            "capture_mode": capture.get("capture_mode", "N/A"),
            "capture_command": capture.get("command", "N/A"),
            "openapi_source": coverage.get("source_path") or coverage.get("path", "N/A"),
            "openapi_trace_count": coverage.get("generated_trace_count", 0),
            "chaos_mutated_files": len(chaos.get("mutated_files", [])) if isinstance(chaos, dict) else 0,
            "chaos_mutations": chaos.get("mutations_applied", []) if isinstance(chaos, dict) else [],
            "pii_files_scanned": pii.get("files_scanned", 0),
            "pii_leaks": len(pii.get("leaks_found", [])) if isinstance(pii, dict) else 0,
            "drift_similarity_percent": drift.get("behavioral_similarity_percent", 100.0),
            "drift_percent": drift.get("behavioral_drift_percent", 0.0),
            "drift_baseline": drift.get("baseline_source", "N/A"),
            "resilience_index": active.get("resilience_index", 0.0),
            "coverage_percent": active.get("coverage_percent", 100.0),
            "pii_score": active.get("pii_score", 100.0),
            "chaos_score": active.get("chaos_score", 0.0),
        }

    def generate_user_pass_scorecard(self, results_dict):
        results_dict = self._normalize_results_payload(results_dict)
        print("====== STRATEGIC USER PASS CERTIFICATION DASHBOARD ======")
        active_resilience = self._build_active_resilience_summary(results_dict)

        # Build detailed per-attribute scoring logic
        scorecard = {}
        for attribute in USER_PASS_ORDER:
            data = results_dict.get(attribute, {})
            findings = data.get("findings", {}) if isinstance(data, dict) else {}
            assessed_tools = 0
            
            tool_sum = 0.0
            failed_count = 0
            blocker_count = 0 
            skipped_count = 0
            
            for tool_data in findings.values():
                status = str(tool_data.get("status", "")).upper()
                if status == "SKIPPED" or str(tool_data.get("mode", "")).upper() == "SKIPPED":
                    skipped_count += 1
                    continue

                assessed_tools += 1
                success = tool_data.get("success", False)
                severity = tool_data.get("severity", "INFO" if success else "CRITICAL")
                
                if success:
                    tool_sum += 1.0
                else:
                    failed_count += 1
                    tool_sum += SEVERITY_WEIGHTS.get(severity, 0.0)
                    if severity in ["CRITICAL", "HIGH"]:
                        blocker_count += 1

            if assessed_tools > 0:
                attr_score = round((tool_sum / assessed_tools) * 100, 1)
            else:
                attr_score = 0.0
                
            weight = self.weights.get(attribute, 0)
            weighted_contribution = round(attr_score * weight, 2)

            if assessed_tools == 0:
                verdict = "SKIPPED" if skipped_count > 0 else "N/A"
                attr_tier = "N/A"
            else:
                verdict = "PASS" if failed_count == 0 else "FAIL"
                # Graduated tier — same scale as the overall score
                if blocker_count > 0:
                    attr_tier = "Needs Work"
                elif attr_score >= 90:
                    attr_tier = "Platinum"
                elif attr_score >= 80:
                    attr_tier = "Gold"
                elif attr_score >= 70:
                    attr_tier = "Silver"
                elif attr_score >= 60:
                    attr_tier = "Bronze"
                else:
                    attr_tier = "Not Certified"

            scorecard[attribute] = {
                "total_tools": assessed_tools,
                "passed": assessed_tools - failed_count,
                "failed": failed_count,
                "skipped": skipped_count,
                "blockers": blocker_count,
                "attribute_score": attr_score,
                "weight": weight,
                "weighted_contribution": weighted_contribution,
                "verdict": verdict,        # strict zero-defect: PASS only if zero failures
                "tier": attr_tier,         # graduated: Platinum/Gold/Silver/Bronze/Needs Work
            }

        final_score = round(sum(s["weighted_contribution"] for s in scorecard.values()), 2)
        tier = self._compute_tier(final_score, scorecard)

        report_text = self._format_console_report(scorecard, final_score, tier, active_resilience)
        total_tools = sum(s["total_tools"] for s in scorecard.values())
        if total_tools == 0:
            execution_reason = results_dict.get("metadata", {}).get("execution_reason", "No executable tools were resolved.")
            report_text += (
                "\nNOTICE: No executable tools were resolved for this run.\n"
                f"Reason: {execution_reason}\n"
                "The report was generated from discovery and metadata only.\n"
            )
        print(report_text)

        # Pass raw active_resilience (with sub-keys) to generators
        # so capture_profile / coverage_booster / pii_audit etc. are readable.
        raw_active_resilience = results_dict.get("metadata", {}).get("active_resilience", {})

        # Generate each format independently to prevent failure cascades
        try:
            self.excel_gen.generate(results_dict, scorecard, final_score, tier, report_insights=raw_active_resilience)
        except Exception as e:
            print(f"[!] Critical Excel Error: {str(e)}")

        try:
            self.pdf_gen.generate(results_dict, scorecard, final_score, tier, report_insights=raw_active_resilience)
        except Exception as e:
            print(f"[!] Critical PDF Error (Possible Character Render): {str(e)}")

        try:
            self.json_gen.generate(results_dict, scorecard, final_score, tier, report_insights=raw_active_resilience)
        except Exception as e:
            print(f"[!] Critical JSON Error: {str(e)}")

        return report_text

    def _compute_tier(self, final_score, scorecard):
        total_blockers = sum(s["blockers"] for s in scorecard.values())
        if total_blockers > 0 and final_score >= 80:
            return "Silver-Awaiting Fixes" 
        
        if final_score >= 90: return "Platinum"
        elif final_score >= 80: return "Gold"
        elif final_score >= 70: return "Silver"
        elif final_score >= 60: return "Bronze"
        else: return "Not Certified"

    def _format_console_report(self, scorecard, final_score, tier, active_resilience=None):
        lines = ["=" * 80]
        lines.append(f"  {'Attribute':<16} {'Score':>7}  {'Weight':>7}  {'Tools':>9}  {'Skip':>5}  {'Blockers':>8}  {'Tier':<18}  {'Zero-Defect':>11}")
        lines.append("-" * 80)
        for attr in USER_PASS_ORDER:
            s = scorecard[attr]
            v = s.get("verdict", "N/A")
            t = s.get("tier", "N/A")
            w = f"{s['weight'] * 100:.0f}%"
            tools_str = f"{s['passed']}/{s['total_tools']}"
            lines.append(f"  {attr.upper():<16} {s['attribute_score']:>6.1f}%  {w:>7}  {tools_str:>9}  {s.get('skipped', 0):>5}  {s['blockers']:>8}  {t:<18}  {v:>11}")
        lines.append("-" * 80)
        lines.append(f"  FINAL SCORE : {final_score:.2f} / 100 | TIER : [{tier.upper()}]")
        total_blockers = sum(s['blockers'] for s in scorecard.values())
        lines.append(f"  TOTAL BLOCKERS : {total_blockers} (CRITICAL/HIGH issues detected)")
        if active_resilience:
            lines.append("  ACTIVE RESILIENCE:")
            lines.append(
                f"    Capture Mode: {active_resilience.get('capture_mode', 'N/A')} | "
                f"OpenAPI Traces: {active_resilience.get('openapi_trace_count', 0)} | "
                f"Chaos Files: {active_resilience.get('chaos_mutated_files', 0)}"
            )
            lines.append(
                f"    PII Files Scanned: {active_resilience.get('pii_files_scanned', 0)} | "
                f"PII Leaks: {active_resilience.get('pii_leaks', 0)} | "
                f"Drift Similarity: {active_resilience.get('drift_similarity_percent', 100.0):.1f}% | "
                f"Drift Gap: {active_resilience.get('drift_percent', 0.0):.1f}%"
            )
            lines.append(
                f"    Resilience Index: {active_resilience.get('resilience_index', 0.0):.1f}% | "
                f"Coverage Score: {active_resilience.get('coverage_percent', 100.0):.1f}% | "
                f"PII Score: {active_resilience.get('pii_score', 100.0):.1f}% | "
                f"Chaos Score: {active_resilience.get('chaos_score', 0.0):.1f}%"
            )
        lines.append("=" * 80)
        return "\n".join(lines)
