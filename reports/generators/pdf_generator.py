import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from fpdf import FPDF

from reports.report_sanitizer import sanitize_report_tree

USER_PASS_ORDER = [
    "usability", "security", "efficiency", "reliability",
    "performance", "accessibility", "scalability", "stability"
]


class PDFReportGenerator:
    def __init__(self, output_dir="reports/output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate(self, raw_results, scorecard, final_score, tier, filepath="user_pass_certification_report.pdf", report_insights=None):
        print("[*] Generating Detailed PDF Validation Report...")
        pdf = FPDF()
        pdf.add_page()
        target_url = raw_results.get("metadata", {}).get("target_url", "")
        raw_results = sanitize_report_tree(raw_results, target_url)

        def reset_x():
            pdf.set_x(10)

        reset_x()
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_fill_color(31, 78, 120)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(190, 10, "USER PASS CERTIFICATION REPORT", 1, 1, "C", True)

        reset_x()
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(190, 8, f"Score: {final_score:.2f}/100 | Tier: {tier.upper()}", 0, 1, "C")
        traffic_capture = raw_results.get("metadata", {}).get("traffic_capture", {})
        if isinstance(traffic_capture, dict) and traffic_capture.get("captured_request_count") is not None:
            pdf.cell(
                190,
                8,
                f"Captured Requests: {traffic_capture.get('captured_request_count', 0)} | Unique Endpoints: {traffic_capture.get('unique_endpoint_count', 0)}",
                0,
                1,
                "C",
            )
        pdf.ln(5)

        reset_x()
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(190, 10, "SCORECARD SUMMARY", 0, 1, "L")

        reset_x()
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(220, 230, 241)
        pdf.cell(45, 7, "Attribute", 1, 0, "L", True)
        pdf.cell(22, 7, "Score %", 1, 0, "C", True)
        pdf.cell(18, 7, "Weight", 1, 0, "C", True)
        pdf.cell(28, 7, "Tools (P/F/S)", 1, 0, "C", True)
        pdf.cell(22, 7, "Blockers", 1, 0, "C", True)
        pdf.cell(28, 7, "Tier", 1, 0, "C", True)
        pdf.cell(27, 7, "Zero-Defect", 1, 1, "C", True)

        for attr in USER_PASS_ORDER:
            sc = scorecard.get(attr, {})
            verdict = sc.get("verdict", "N/A")
            attr_tier = sc.get("tier", "N/A")
            score_val = sc.get("attribute_score", 0)
            weight_val = f"{sc.get('weight', 0) * 100:.0f}%"
            tools_val = f"{sc.get('passed', 0)}/{sc.get('failed', 0)}/{sc.get('skipped', 0)}"
            blockers = sc.get("blockers", 0)

            reset_x()
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(45, 7, attr.upper(), 1)
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(22, 7, f"{score_val:.1f}%", 1, 0, "C")
            pdf.cell(18, 7, weight_val, 1, 0, "C")
            pdf.cell(28, 7, tools_val, 1, 0, "C")
            pdf.cell(22, 7, str(blockers), 1, 0, "C")
            pdf.cell(28, 7, attr_tier, 1, 0, "C")
            pdf.cell(27, 7, verdict, 1, 1, "C")

        pdf.ln(10)
        reset_x()
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(190, 10, "SERVICE-MESH DISCOVERY: Discovered API Baseline", 0, 1, "L")

        reset_x()
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(20, 7, "Method", 1, 0, "C", True)
        pdf.cell(80, 7, "API Endpoint Path", 1, 0, "L", True)
        pdf.cell(15, 7, "Status", 1, 0, "C", True)
        pdf.cell(75, 7, "Discovery Internal Tag", 1, 1, "L", True)

        pdf.set_font("Helvetica", "", 8)
        discovery_baseline = self._resolve_discovery_baseline(raw_results)
        for api in discovery_baseline:
            reset_x()
            pdf.cell(20, 6, api.get("method", "GET"), 1, 0, "C")
            pdf.cell(80, 6, _normalize_target_path(target_url, api.get("path", "/")), 1, 0, "L")
            pdf.cell(15, 6, str(api.get("status", 200)), 1, 0, "C")
            pdf.cell(75, 6, api.get("description", "Discovered Interface"), 1, 1, "L")

        active_resilience = report_insights or raw_results.get("metadata", {}).get("active_resilience", {})
        if active_resilience:
            capture = active_resilience.get("capture_profile") or {}
            coverage = active_resilience.get("coverage_booster") or {}
            chaos = active_resilience.get("chaos_profile") or {}
            pii = active_resilience.get("pii_audit") or {}
            drift = active_resilience.get("behavioral_drift") or {}
            is_flat = not any([capture, coverage, chaos, pii, drift])

            pdf.ln(10)
            reset_x()
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(190, 10, "ACTIVE RESILIENCE MATRIX", 0, 1, "L")

            reset_x()
            pdf.set_font("Helvetica", "", 9)
            if is_flat:
                pdf.multi_cell(190, 5, f"Capture Mode: {active_resilience.get('capture_mode', 'N/A')}")
                pdf.multi_cell(190, 5, f"OpenAPI Source: {active_resilience.get('openapi_source') or 'N/A'} | Traces: {active_resilience.get('openapi_trace_count', 0)}")
                pdf.multi_cell(190, 5, f"Chaos Files: {active_resilience.get('chaos_mutated_files', 0)} | Mutations: {', '.join(active_resilience.get('chaos_mutations', [])) or 'N/A'}")
                pdf.multi_cell(190, 5, f"PII Files Scanned: {active_resilience.get('pii_files_scanned', 0)} | PII Leaks: {active_resilience.get('pii_leaks', 0)}")
                pdf.multi_cell(190, 5, f"Behavioral Similarity: {active_resilience.get('drift_similarity_percent', 100.0):.1f}% | Drift Gap: {active_resilience.get('drift_percent', 0.0):.1f}%")
                pdf.multi_cell(190, 5, f"Resilience Index: {active_resilience.get('resilience_index', 0.0):.1f}% | Coverage: {active_resilience.get('coverage_percent', 0.0):.1f}% | PII Score: {active_resilience.get('pii_score', 100.0):.1f}% | Chaos Score: {active_resilience.get('chaos_score', 0.0):.1f}%")
            else:
                pdf.multi_cell(190, 5, f"Capture Mode: {capture.get('capture_mode', 'N/A')} | Requests: {capture.get('captured_request_count', 0)} | Endpoints: {capture.get('unique_endpoint_count', 0)}")
                pdf.multi_cell(190, 5, f"OpenAPI Traces: {coverage.get('generated_trace_count', 0)} | Source: {coverage.get('source_path') or 'N/A'}")
                pdf.multi_cell(190, 5, f"Chaos Files: {len(chaos.get('mutated_files', [])) if isinstance(chaos, dict) else 0} | Mutations: {', '.join(chaos.get('mutations_applied', [])) if isinstance(chaos, dict) and chaos.get('mutations_applied') else 'N/A'}")
                pdf.multi_cell(190, 5, f"PII Files Scanned: {pii.get('files_scanned', 0)} | PII Leaks: {len(pii.get('leaks_found', [])) if isinstance(pii, dict) else 0}")
                pdf.multi_cell(190, 5, f"Behavioral Similarity: {drift.get('behavioral_similarity_percent', 100.0):.1f}% | Drift Gap: {drift.get('behavioral_drift_percent', 0.0):.1f}%")
                pdf.multi_cell(190, 5, f"Resilience Index: {active_resilience.get('resilience_index', 0.0):.1f}% | Coverage: {active_resilience.get('coverage_percent', 0.0):.1f}% | PII Score: {active_resilience.get('pii_score', 100.0):.1f}% | Chaos Score: {active_resilience.get('chaos_score', 0.0):.1f}%")

        pdf.ln(10)
        reset_x()
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(190, 10, "DETAILED FINDINGS (PATH-TRACED)", 0, 1, "L")

        execution_state = raw_results.get("metadata", {}).get("execution_state", "COMPLETED")
        execution_reason = raw_results.get("metadata", {}).get("execution_reason", "")
        has_findings = any(
            isinstance(raw_results.get(attr, {}), dict) and raw_results.get(attr, {}).get("findings")
            for attr in USER_PASS_ORDER
        )

        if execution_state == "SKIPPED" or not has_findings:
            reset_x()
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(120, 120, 120)
            pdf.multi_cell(
                190,
                6,
                "No executable tools were resolved for this run.\n"
                f"Reason: {execution_reason or 'The strategy output did not yield any runnable tools.'}\n"
                "The report was still generated to preserve discovery and execution metadata.",
            )
            pdf.set_text_color(0, 0, 0)
            pdf.ln(4)

        SEV_MAP = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}

        for attr in USER_PASS_ORDER:
            data = raw_results.get(attr, {})
            if not isinstance(data, dict) or "findings" not in data:
                continue

            sc = scorecard.get(attr, {})
            reset_x()
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(190, 8, f"{attr.upper()} (Score: {sc.get('attribute_score',0):.1f}%)", 0, 1, "L", True)

            findings = sorted(
                data["findings"].items(),
                key=lambda x: (x[1].get("success", False), SEV_MAP.get(x[1].get("severity", "INFO"), 99))
            )

            for tool_key, details in findings:
                success = details.get("success", False)
                status = details.get("status", "PASS" if success else "FAIL")
                mode = details.get("mode", "LIVE")
                severity = details.get("severity", "INFO" if success else "CRITICAL")
                log_msg = details.get("log", "")
                rec = details.get("recommendation", "N/A")
                path = _normalize_target_path(target_url, details.get("path", "-"))

                reset_x()
                if status == "SKIPPED":
                    pdf.set_text_color(120, 120, 120)
                    pdf.set_font("Helvetica", "B", 9)
                    pdf.cell(190, 6, f"  [SKIPPED] {tool_key.replace('_', ' ').upper()}", 0, 1)
                elif not success:
                    pdf.set_text_color(180, 0, 0)
                    pdf.set_font("Helvetica", "B", 9)
                    pdf.cell(190, 6, f"  [FAIL] {tool_key.replace('_', ' ').upper()} | SEVERITY: {severity}", 0, 1)
                else:
                    pdf.set_text_color(0, 120, 0)
                    pdf.set_font("Helvetica", "B", 9)
                    pdf.cell(190, 6, f"  [PASS] {tool_key.replace('_', ' ').title()}", 0, 1)

                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Helvetica", "I", 8)
                reset_x()
                pdf.cell(190, 5, f"    Target Path: {path}", 0, 1)
                reset_x()
                pdf.cell(190, 5, f"    Execution Mode: {mode}", 0, 1)

                pdf.set_font("Helvetica", "", 8)
                reset_x()
                clean_log = log_msg.encode("latin-1", "replace").decode("latin-1")
                pdf.multi_cell(180, 5, f"    Diagnostic: {clean_log}")

                if not success:
                    reset_x()
                    pdf.set_font("Helvetica", "B", 8)
                    clean_rec = rec.encode("latin-1", "replace").decode("latin-1")
                    pdf.multi_cell(180, 5, f"    Remediation: {clean_rec}")

            pdf.ln(4)

        pdf.set_font("Helvetica", "", 8)
        pdf.cell(w=0, h=10, text="--- End of World-Class Certification Report ---", align="C")

        out_path = os.path.join(self.output_dir, filepath)
        try:
            pdf.output(out_path)
        except PermissionError:
            fallback_name = f"{Path(filepath).stem}_clean{Path(filepath).suffix}"
            out_path = os.path.join(self.output_dir, fallback_name)
            print(f"[!] Report file is locked. Writing PDF output to {out_path}")
            pdf.output(out_path)
        print(f"[+] Professionally styled PDF with 100% path-traceability saved -> {out_path}")
        return out_path

    def _resolve_discovery_baseline(self, raw_results):
        metadata = raw_results.get("metadata", {}) if isinstance(raw_results, dict) else {}
        service_mesh = metadata.get("service_mesh_discovery", {}) if isinstance(metadata, dict) else {}
        scenarios = raw_results.get("scenarios", []) if isinstance(raw_results, dict) else []

        def _first_list(*candidates):
            for candidate in candidates:
                if isinstance(candidate, list) and candidate:
                    return candidate
            return []

        discovery_baseline = _first_list(
            metadata.get("discovery_baseline"),
            service_mesh.get("baseline") if isinstance(service_mesh, dict) else None,
            raw_results.get("discovered_apis"),
            raw_results.get("baseline"),
            raw_results.get("discovery_baseline"),
            metadata.get("discovered_apis"),
            metadata.get("inventory_summary", {}).get("discovered_apis") if isinstance(metadata.get("inventory_summary"), dict) else None,
        )
        if discovery_baseline:
            return discovery_baseline

        derived = []
        seen = set()
        if isinstance(scenarios, list):
            for scenario in scenarios:
                if not isinstance(scenario, dict):
                    continue
                endpoints = scenario.get("endpoints", [])
                if not isinstance(endpoints, list):
                    continue
                for endpoint in endpoints:
                    if not isinstance(endpoint, dict):
                        continue
                    method = str(endpoint.get("method") or "GET").upper()
                    raw_path = str(endpoint.get("path") or "").strip()
                    raw_url = str(endpoint.get("url") or "").strip()
                    path = raw_path
                    if not path and raw_url:
                        parsed = urlparse(raw_url)
                        path = parsed.path or raw_url
                    if not path:
                        continue
                    key = (method, path)
                    if key in seen:
                        continue
                    seen.add(key)
                    derived.append({
                        "method": method,
                        "path": path,
                        "status": endpoint.get("status", 200),
                        "description": endpoint.get("expected_behavior") or endpoint.get("description") or "Discovered Interface",
                        "source": endpoint.get("source", "scenario"),
                    })

        return derived


def _normalize_target_path(target_url, path):
    target = str(target_url or "").strip().rstrip("/")
    raw_path = str(path or "").strip()

    if not target:
        return raw_path or "N/A"
    if not raw_path:
        return target

    target_parts = urlparse(target)
    if raw_path.startswith(("http://", "https://")):
        parsed = urlparse(raw_path)
        if parsed.netloc and parsed.netloc != target_parts.netloc:
            return urlunparse(
                (
                    target_parts.scheme or parsed.scheme,
                    target_parts.netloc,
                    parsed.path or "/",
                    parsed.params,
                    parsed.query,
                    parsed.fragment,
                )
            )
        return raw_path

    methodless_path = raw_path
    if " " in raw_path and raw_path.split(" ", 1)[0].isalpha():
        _, maybe_path = raw_path.split(" ", 1)
        if maybe_path.startswith("/"):
            methodless_path = maybe_path

    if methodless_path.startswith("/"):
        return f"{target}{methodless_path}"

    return raw_path
