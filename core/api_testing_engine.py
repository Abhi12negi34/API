import os
from urllib.parse import urlparse, urlunparse

import yaml

from core.api.keploy_intercept_proxy import start_keploy_record
from core.api.playwright_stimulator import run_playwright_stimulator
from tools.accessibility.axe_accessibility_bridge import run_axe_devtools_scan
from tools.accessibility.axe_color_contrast_auditor import audit_color_contrast
from tools.accessibility.keploy_accessibility_json_auditor import audit_accessibility_semantics
from tools.accessibility.keploy_aria_contract_validator import validate_aria_contracts
from tools.accessibility.keploy_i18n_accessibility_auditor import audit_i18n_accessibility
from tools.accessibility.keploy_screen_reader_delay_auditor import audit_screen_reader_delay
from tools.accessibility.keploy_wcag_color_contrast_api_auditor import audit_wcag_color_contrast_api
from tools.accessibility.playwright_keyboard_navigation_auditor import audit_keyboard_navigation
from tools.efficiency.keploy_cache_hit_ratio_profiler import audit_cache_hit_ratio
from tools.efficiency.keploy_data_overfetch_auditor import audit_data_overfetching
from tools.efficiency.keploy_graphql_query_cost_analyzer import audit_graphql_query_cost
from tools.efficiency.keploy_http2_multiplexing_profiler import profile_http2_multiplexing
from tools.efficiency.keploy_n_plus_one_query_detector import detect_n_plus_one_queries
from tools.efficiency.keploy_payload_compression_auditor import audit_payload_compression
from tools.efficiency.lighthouse_core_web_vitals_auditor import audit_core_web_vitals
from tools.performance.k6_prometheus_load_auditor import convert_and_run_k6
from tools.performance.k6_spike_flash_sale_tester import run_spike_test
from tools.performance.k6_stress_breaking_point_tester import run_stress_test
from tools.performance.keploy_cold_start_latency_profiler import profile_cold_start_latency
from tools.performance.keploy_database_n_plus_one_profiler import profile_database_n_plus_one
from tools.performance.keploy_grpc_streaming_latency_analyzer import analyze_grpc_streaming_latency
from tools.performance.keploy_server_timing_profiler import analyze_backend_profiling
from tools.reliability.keploy_circuit_breaker_resync_auditor import audit_circuit_breaker_resync
from tools.reliability.keploy_coverage_booster import generate_openapi_traces
from tools.reliability.keploy_dead_letter_queue_fuzzer import fuzz_dead_letter_queue
from tools.reliability.keploy_drift_certifier import calculate_behavioral_drift
from tools.reliability.keploy_idempotency_fuzzer import test_transaction_idempotency
from tools.reliability.keploy_retry_jitter_auditor import audit_retry_jitter
from tools.reliability.keploy_session_security_validator import validate_session_security
from tools.reliability.keploy_webhook_contract_tester import test_webhook_contracts
from tools.reliability.openapi_schema_extensibility import validate_openapi_schema
from tools.reliability.reliability_mock_fuzzer import execute_reliability_mocking
from tools.scalability.keploy_distributed_caching_sync_analyzer import analyze_distributed_caching_sync
from tools.scalability.keploy_global_cdn_latency_simulator import simulate_global_cdn_latency
from tools.scalability.keploy_horizontal_scaling_observer import observe_horizontal_scaling
from tools.scalability.keploy_throughput_saturation_analyzer import analyze_throughput_saturation
from tools.scalability.keploy_token_bucket_rate_limit_auditor import audit_token_bucket_rate_limit
from tools.scalability.prometheus_bottleneck_identifier import identify_scale_bottlenecks
from tools.security.dependency_vulnerability_scanner import scan_third_party_dependencies
from tools.security.keploy_bola_idor_detector import detect_bola_idor_vulnerabilities
from tools.security.keploy_jwt_weak_signature_auditor import audit_jwt_weak_signatures
from tools.security.keploy_oauth2_token_scoping_auditor import audit_oauth2_token_scoping
from tools.security.keploy_pii_leak_auditor import audit_pii_data_leaks
from tools.security.keploy_secure_headers_auditor import audit_secure_configurations
from tools.security.keploy_shadow_api_discoverer import detect_shadow_apis
from tools.security.owasp_zap_dast_bridge import run_owasp_zap_scan
from tools.security.payload_mutation_injector import inject_security_mutations
from tools.stability.keploy_chaos_fuzzer import inject_chaos
from tools.stability.keploy_memory_bloat_json_fuzzer import fuzz_memory_bloat_json
from tools.stability.keploy_memory_leak_endurance_tester import test_memory_leak_endurance
from tools.stability.keploy_race_condition_fuzzer import test_race_conditions
from tools.stability.keploy_regression_replay import run_keploy_test
from tools.stability.keploy_thread_pool_exhaustion_simulator import simulate_thread_pool_exhaustion
from tools.stability.keploy_timeout_graceful_degradation import test_timeout_degradation
from tools.usability.keploy_api_versioning_depreciation_auditor import audit_api_versioning_depreciation
from tools.usability.keploy_error_message_clarity_auditor import audit_error_message_clarity
from tools.usability.keploy_hateoas_compliance_validator import validate_hateoas_compliance
from tools.usability.keploy_interactive_feedback_auditor import validate_interactive_feedback
from tools.usability.keploy_localization_key_auditor import audit_localization_keys
from tools.usability.keploy_rate_limit_dx_validator import validate_rate_limit_dx
from tools.usability.playwright_responsive_design_auditor import test_responsive_usability
from tools.usability.playwright_ux_consistency_auditor import audit_ux_consistency

USER_PASS_ORDER = [
    "usability",
    "security",
    "efficiency",
    "reliability",
    "performance",
    "accessibility",
    "scalability",
    "stability",
]


def _normalize_mode(value):
    return str(value or "").strip().upper()


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
            return urlunparse((target_parts.scheme or parsed.scheme, target_parts.netloc, parsed.path or "/", parsed.params, parsed.query, parsed.fragment))
        return raw_path

    methodless_path = raw_path
    if " " in raw_path and raw_path.split(" ", 1)[0].isalpha():
        maybe_method, maybe_path = raw_path.split(" ", 1)
        if maybe_path.startswith("/"):
            methodless_path = maybe_path

    if methodless_path.startswith("/"):
        return f"{target}{methodless_path}"

    if target_parts.netloc and target_parts.netloc in raw_path:
        return raw_path.replace(target_parts.netloc, target_parts.netloc)

    return raw_path


def _coerce_result(raw, tool_key, target_url):
    """
    Normalizes any tool return value into the standard result dict.
    Tools that return a plain bool (legacy) are converted; dicts are passed through.
    """
    if isinstance(raw, dict):
        raw.setdefault("success", False)
        raw.setdefault("log", f"[{tool_key}] No log provided.")
        raw.setdefault("severity", "INFO" if raw.get("success") else "MEDIUM")
        raw["path"] = _normalize_target_path(target_url, raw.get("path", target_url))
        raw.setdefault("recommendation", "N/A")
        raw.setdefault("status", "PASS" if raw.get("success") else "FAIL")
        inferred_mode = raw.get("mode")
        if not inferred_mode:
            log_text = str(raw.get("log", ""))
            if raw.get("status") == "SKIPPED":
                inferred_mode = "SKIPPED"
            elif "[SIMULATION]" in log_text or "simulat" in log_text.lower():
                inferred_mode = "SIMULATED"
            else:
                inferred_mode = "LIVE"
        raw["mode"] = _normalize_mode(inferred_mode)
        if raw["status"] == "SKIPPED":
            raw["success"] = False
        else:
            raw["status"] = "PASS" if raw.get("success") else "FAIL"
        return raw

    success = bool(raw)
    return {
        "success": success,
        "log": f"[{tool_key}] {'Check passed.' if success else 'Check failed.'}",
        "severity": "INFO" if success else "MEDIUM",
        "path": target_url,
        "recommendation": "N/A" if success else f"Investigate {tool_key} failure.",
        "status": "PASS" if success else "FAIL",
        "mode": "SIMULATED",
    }


class ApiTestingEngine:
    def __init__(self, config, planning_context=None, workspace_root=None):
        self.config = config
        self.planning_context = planning_context or ""
        self.workspace_root = workspace_root or os.getcwd()
        self.discovery_baseline = []
        self.capture_profile = {}

        map_path = os.path.join(os.path.dirname(__file__), "..", "config", "tool_attribute_map.yaml")
        with open(map_path, "r", encoding="utf-8") as f:
            self.attribute_map = yaml.safe_load(f)

        self.tool_to_attr = {}
        for attr, tools in self.attribute_map.items():
            for tool_key in tools:
                self.tool_to_attr[tool_key] = attr

    def _build_tool_registry(self, target_url):
        """
        Returns the full tool registry as a dict of tool_key -> callable.
        All callables accept no arguments (target_url is captured via closure).
        """
        t = target_url
        zap_key = self.config.get("zaproxy", {}).get("api_key", "not-set")
        discovery_baseline = self.discovery_baseline
        workspace_root = self.workspace_root

        return {
            "zap_dast_scan": lambda: run_owasp_zap_scan(t, zap_key),
            "k6_perf_scale": lambda: convert_and_run_k6(workspace_root=workspace_root, target_url=t),
            "regression_test": lambda: run_keploy_test(workspace_root=workspace_root, target_url=t),
            "fault_mocking": lambda: execute_reliability_mocking(workspace_root=workspace_root, target_url=t),
            "axe_accessibility": lambda: run_axe_devtools_scan(workspace_root=workspace_root, target_url=t),
            "schema_check": lambda: validate_openapi_schema(target_url=t, workspace_root=workspace_root),
            "coverage_booster": lambda: generate_openapi_traces(
                t,
                discovery_baseline=discovery_baseline,
                workspace_root=workspace_root,
            ),

            "shadow_api": lambda: detect_shadow_apis(t),
            "data_protection": lambda: audit_pii_data_leaks(t, workspace_root=workspace_root),
            "secure_config": lambda: audit_secure_configurations(t),
            "dep_scanner": lambda: scan_third_party_dependencies(t),
            "sql_injection_url": lambda: run_owasp_zap_scan(t, zap_key),
            "cia_integrity": lambda: audit_secure_configurations(t),
            "rbac_access_audit": lambda: detect_bola_idor_vulnerabilities(t),
            "cors_misconfig": lambda: run_owasp_zap_scan(t, zap_key),
            "jwt_weak_signatures": lambda: audit_jwt_weak_signatures(t),
            "bola_idor_detector": lambda: detect_bola_idor_vulnerabilities(t),
            "oauth2_scoping": lambda: audit_oauth2_token_scoping(t),
            "payload_mutations": lambda: inject_security_mutations(t, workspace_root=workspace_root),

            "dx_validator": lambda: validate_rate_limit_dx(t),
            "api_doc_clarity": lambda: validate_hateoas_compliance(t),
            "ui_visual_regress": lambda: test_responsive_usability(workspace_root=workspace_root, target_url=t),
            "rtl_i18n_audit": lambda: audit_i18n_accessibility(t),
            "error_message_clarity": lambda: audit_error_message_clarity(t),
            "api_versioning_depreciation": lambda: audit_api_versioning_depreciation(t),
            "hateoas_compliance": lambda: validate_hateoas_compliance(t),
            "interactive_feedback": lambda: validate_interactive_feedback(workspace_root=workspace_root),
            "localization_ux": lambda: audit_localization_keys(workspace_root=workspace_root, target_url=t),
            "ux_consistency": lambda: audit_ux_consistency(workspace_root=workspace_root),
            "responsive_ux": lambda: test_responsive_usability(workspace_root=workspace_root, target_url=t),

            "cold_start_latency": lambda: profile_cold_start_latency(t),
            "server_profiling": lambda: analyze_backend_profiling(t),
            "database_n_plus_one": lambda: profile_database_n_plus_one(target_url=t, workspace_root=workspace_root),
            "stress_test": lambda: run_stress_test(workspace_root=workspace_root, target_url=t),
            "spike_test": lambda: run_spike_test(workspace_root=workspace_root, target_url=t),
            "grpc_perf": lambda: analyze_grpc_streaming_latency(workspace_root=workspace_root),

            "data_efficiency": lambda: audit_data_overfetching(workspace_root=workspace_root),
            "payload_compression": lambda: audit_payload_compression(t),
            "graphql_query_cost": lambda: audit_graphql_query_cost(t),
            "http2_eff": lambda: profile_http2_multiplexing(t),
            "n_plus_one_eff": lambda: detect_n_plus_one_queries(workspace_root=workspace_root),
            "web_vitals_eff": lambda: audit_core_web_vitals(workspace_root=workspace_root, target_url=t),
            "cache_hit_eff": lambda: audit_cache_hit_ratio(t),

            "json_a11y": lambda: audit_accessibility_semantics(workspace_root=workspace_root),
            "aria_contracts": lambda: validate_aria_contracts(workspace_root=workspace_root, target_url=t),
            "keyboard_a11y": lambda: audit_keyboard_navigation(workspace_root=workspace_root, target_url=t),
            "contrast_a11y": lambda: audit_color_contrast(workspace_root=workspace_root, target_url=t),
            "i18n_a11y": lambda: audit_i18n_accessibility(t),
            "wcag_color_contrast_api": lambda: audit_wcag_color_contrast_api(t),
            "screen_read_a11y": lambda: audit_screen_reader_delay(t),

            "throughput_scale": lambda: analyze_throughput_saturation(workspace_root=workspace_root),
            "horizontal_scale": lambda: observe_horizontal_scaling(workspace_root=workspace_root),
            "bottleneck_scale": lambda: identify_scale_bottlenecks(workspace_root=workspace_root),
            "compression_eff": lambda: audit_payload_compression(t),
            "cdn_latency_scale": lambda: simulate_global_cdn_latency(t),
            "token_buck_scale": lambda: audit_token_bucket_rate_limit(t),
            "cache_sync_scale": lambda: analyze_distributed_caching_sync(t),

            "idempotency": lambda: test_transaction_idempotency(workspace_root=workspace_root, target_url=t),
            "circuit_breaker_resync": lambda: audit_circuit_breaker_resync(t),
            "session_security": lambda: validate_session_security(workspace_root=workspace_root, target_url=t),
            "webhook_ext": lambda: test_webhook_contracts(workspace_root=workspace_root, target_url=t),
            "retry_jitter_rel": lambda: audit_retry_jitter(workspace_root=workspace_root, target_url=t),
            "dlq_fuzz_rel": lambda: fuzz_dead_letter_queue(t),

            "race_conditions": lambda: test_race_conditions(workspace_root=workspace_root, target_url=t),
            "memory_leak_stab": lambda: test_memory_leak_endurance(workspace_root=workspace_root, target_url=t),
            "degradation_stab": lambda: test_timeout_degradation(workspace_root=workspace_root, target_url=t),
            "thread_pool_stab": lambda: simulate_thread_pool_exhaustion(t),
            "chaos_stab": lambda: inject_chaos(workspace_root=workspace_root),
            "mem_bloat_stab": lambda: fuzz_memory_bloat_json(t),
        }

    def _truncate_text(self, value, limit=240):
        text = str(value or "").strip()
        if len(text) <= limit:
            return text
        return f"{text[: limit - 3]}..."

    def build_analysis_brief(self, raw_results, max_failures=24):
        """
        Produce a compact, deterministic analysis payload for the LLM.
        This keeps the analyzer prompt small enough to fit within context.
        """
        if not isinstance(raw_results, dict):
            return {"error": "raw_results must be a dict"}

        metadata = raw_results.get("metadata", {}) if isinstance(raw_results.get("metadata", {}), dict) else {}
        target_url = metadata.get("target_url", "N/A")
        traffic_capture = metadata.get("traffic_capture", {})
        discovery_baseline = metadata.get("discovery_baseline", [])
        discovery_summary = {
            "target_url": target_url,
            "discovered_api_count": len(discovery_baseline) if isinstance(discovery_baseline, list) else 0,
            "capture_mode": traffic_capture.get("capture_mode", "N/A") if isinstance(traffic_capture, dict) else "N/A",
            "captured_request_count": traffic_capture.get("captured_request_count", 0) if isinstance(traffic_capture, dict) else 0,
            "unique_endpoint_count": traffic_capture.get("unique_endpoint_count", 0) if isinstance(traffic_capture, dict) else 0,
            "unique_hosts": traffic_capture.get("unique_hosts", []) if isinstance(traffic_capture, dict) else [],
            "source_files": traffic_capture.get("discovery_source_files", []) if isinstance(traffic_capture, dict) else [],
            "inventory_summary": traffic_capture.get("inventory_summary", {}) if isinstance(traffic_capture, dict) else {},
        }

        attribute_overview = {}
        failures = []
        for attr in USER_PASS_ORDER:
            attr_data = raw_results.get(attr, {})
            findings = attr_data.get("findings", {}) if isinstance(attr_data, dict) else {}
            passed = failed = skipped = blockers = 0

            for tool_id, details in findings.items():
                status = str(details.get("status", "")).upper()
                mode = str(details.get("mode", "")).upper()
                if status == "SKIPPED" or mode == "SKIPPED":
                    skipped += 1
                    continue
                if status == "PASS":
                    passed += 1
                    continue

                failed += 1
                severity = str(details.get("severity", "INFO")).upper()
                if severity in {"CRITICAL", "HIGH"}:
                    blockers += 1
                failures.append(
                    {
                        "attribute": attr,
                        "tool_id": tool_id,
                        "status": status or "FAIL",
                        "severity": severity,
                        "path": details.get("path", "N/A"),
                        "log": self._truncate_text(details.get("log", ""), 260),
                        "recommendation": self._truncate_text(details.get("recommendation", "N/A"), 220),
                    }
                )

            attribute_overview[attr] = {
                "overall": bool(attr_data.get("overall", False)) if isinstance(attr_data, dict) else False,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "blockers": blockers,
                "total_tools": passed + failed + skipped,
            }

        failures.sort(key=lambda item: (0 if item["severity"] == "CRITICAL" else 1 if item["severity"] == "HIGH" else 2 if item["severity"] == "MEDIUM" else 3, item["attribute"], item["tool_id"]))

        tool_registry = self._build_tool_registry(target_url)
        configured_tools = {tool for tools in self.attribute_map.values() for tool in tools}
        implemented_tools = set(tool_registry.keys())
        mapped_tools = configured_tools & implemented_tools
        mapping_gaps = {
            "configured_but_unimplemented": sorted(configured_tools - implemented_tools),
            "implemented_but_unmapped": sorted(implemented_tools - configured_tools),
            "mapped_tool_count": len(mapped_tools),
            "configured_tool_count": len(configured_tools),
            "implemented_tool_count": len(implemented_tools),
        }

        active_resilience = metadata.get("active_resilience", {})
        active_resilience_brief = {}
        if isinstance(active_resilience, dict):
            active_resilience_brief = {
                "resilience_index": active_resilience.get("resilience_index", 0.0),
                "coverage_percent": active_resilience.get("coverage_percent", 0.0),
                "pii_score": active_resilience.get("pii_score", 0.0),
                "chaos_score": active_resilience.get("chaos_score", 0.0),
                "drift_score": active_resilience.get("drift_score", 0.0),
            }

        return {
            "target_url": target_url,
            "planning_context_excerpt": self._truncate_text(metadata.get("planning_context", ""), 1200),
            "discovery_summary": discovery_summary,
            "attribute_overview": attribute_overview,
            "failures": failures[:max_failures],
            "mapping_gaps": mapping_gaps,
            "active_resilience": active_resilience_brief,
        }

    def _build_active_resilience_profile(self, raw_tool_results, drift_profile):
        coverage = raw_tool_results.get("coverage_booster", {})
        chaos = raw_tool_results.get("chaos_stab", {})
        pii = raw_tool_results.get("data_protection", {})

        generated_traces = coverage.get("generated_trace_count", 0) if isinstance(coverage, dict) else 0
        discovered_apis = len(self.discovery_baseline or [])
        coverage_percent = round((generated_traces / discovered_apis) * 100, 1) if discovered_apis else 100.0
        pii_leaks = len(pii.get("leaks_found", [])) if isinstance(pii, dict) else 0
        pii_score = 100.0 if pii_leaks == 0 else max(0.0, 100.0 - (pii_leaks * 20.0))
        chaos_score = 100.0 if isinstance(chaos, dict) and chaos.get("mutated_files") else 0.0
        drift_score = drift_profile.get("behavioral_similarity_percent", 100.0) if isinstance(drift_profile, dict) else 100.0
        resilience_index = round((coverage_percent + pii_score + chaos_score + drift_score) / 4, 1)

        return {
            "coverage_booster": coverage,
            "chaos_profile": chaos,
            "pii_audit": pii,
            "behavioral_drift": drift_profile,
            "capture_profile": self.capture_profile,
            "resilience_index": resilience_index,
            "coverage_percent": coverage_percent,
            "pii_score": pii_score,
            "chaos_score": chaos_score,
            "drift_score": drift_score,
        }

    def run_comprehensive_assessment(self, target_url, planning_context=None):
        print(f"[*] Starting Comprehensive USER PASS Assessment on {target_url}...")

        # Respect run_categories config — empty/absent means run all
        run_categories = self.config.get("run_categories") or []
        if isinstance(run_categories, list) and run_categories:
            run_categories = [c.lower().strip() for c in run_categories]
            print(f"[*] Category filter active: running only {run_categories}")
        else:
            run_categories = []

        print("[*] Phase 1: Capturing API traffic surface...")
        capture_telemetry = run_playwright_stimulator(target_url, workspace_root=self.workspace_root)
        capture_profile = start_keploy_record(target_url, workspace_root=self.workspace_root)
        self.capture_profile = capture_profile
        discovery_baseline = capture_profile.get("baseline", [])
        self.discovery_baseline = discovery_baseline
        if isinstance(capture_profile, dict) and capture_telemetry:
            self.capture_profile["traffic_capture"] = capture_telemetry

        print("[*] Phase 2: Executing tool checks...")
        tool_registry = self._build_tool_registry(target_url)

        # Filter tools to only those belonging to the requested categories
        if run_categories:
            tool_registry = {
                key: fn
                for key, fn in tool_registry.items()
                if self.tool_to_attr.get(key, "").lower() in run_categories
            }
            print(f"[*] Running {len(tool_registry)} tool(s) for categories: {run_categories}")

        raw_tool_results = {}

        for tool_key, tool_fn in tool_registry.items():
            try:
                print(f"    -> Running [{tool_key}]...")
                raw = tool_fn()
                raw_tool_results[tool_key] = _coerce_result(raw, tool_key, target_url)
            except Exception as exc:
                raw_tool_results[tool_key] = {
                    "success": False,
                    "log": f"[{tool_key}] Tool raised exception: {str(exc)}",
                    "severity": "HIGH",
                    "path": target_url,
                    "recommendation": f"Investigate tool [{tool_key}] - check imports and dependencies.",
                    "status": "FAIL",
                    "mode": "LIVE",
                }

        drift_profile = calculate_behavioral_drift(raw_tool_results, workspace_root=self.workspace_root)

        print("[*] Phase 3: Composing USER PASS attribute buckets...")
        active_resilience = self._build_active_resilience_profile(raw_tool_results, drift_profile)
        results = self._map_to_user_pass(
            raw_tool_results,
            target_url,
            discovery_baseline,
            planning_context or self.planning_context,
            active_resilience=active_resilience,
            active_categories=run_categories or None,
        )
        return results

    def _map_to_user_pass(self, raw_tool_results, target_url, discovery_baseline, planning_context=None, active_resilience=None, active_categories=None):
        """
        Routes each tool result to its USER PASS attribute bucket using
        config/tool_attribute_map.yaml. Builds the final structured results dict.
        If active_categories is set, non-matching categories are marked as SKIPPED.
        """
        user_pass_attrs = [
            "usability",
            "security",
            "efficiency",
            "reliability",
            "performance",
            "accessibility",
            "scalability",
            "stability",
        ]

        structured = {
            "metadata": {
                "discovery_baseline": discovery_baseline,
                "target_url": target_url,
                "planning_context": planning_context or "",
                "traffic_capture": self.capture_profile,
                "active_categories": active_categories or user_pass_attrs,
            }
        }
        if active_resilience:
            structured["metadata"]["active_resilience"] = active_resilience

        for attr in user_pass_attrs:
            structured[attr] = {"overall": False, "findings": {}}

        for tool_key, result in raw_tool_results.items():
            attr = self.tool_to_attr.get(tool_key)
            if attr:
                structured[attr]["findings"][tool_key] = result

        for attr in user_pass_attrs:
            # Mark non-active categories as skipped rather than failed
            if active_categories and attr not in active_categories:
                structured[attr]["overall"] = None  # None = not evaluated
                structured[attr]["skipped"] = True
                continue

            findings = structured[attr]["findings"]
            evaluated = [finding for finding in findings.values() if finding.get("status") != "SKIPPED"]
            all_pass = bool(evaluated) and all(finding.get("status", "FAIL") == "PASS" for finding in evaluated)
            structured[attr]["overall"] = all_pass

        return structured
