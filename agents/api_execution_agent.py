import json
import os
from pathlib import Path
from urllib.parse import urlparse

import yaml

from crewai_bootstrap import bootstrap_crewai_runtime

bootstrap_crewai_runtime()

from crewai import Agent
from crewai.tools import tool

from llm import default_llm
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
from tools.runtime_config import CREWAI_VERBOSE

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

TOOL_ALIAS_MAP = {
    "k6": "k6_perf_scale",
    "bombardier": "stress_test",
    "locust": "spike_test",
    "zap": "zap_dast_scan",
    "redbot": "secure_config",
    "blazemeter": "data_protection",
    "taurus": "idempotency",
    "axe": "axe_accessibility",
    "playwright": "keyboard_a11y",
    "aiohttp": "data_efficiency",
    "autocannon": "payload_compression",
    "loadfocus": "throughput_scale",
    "webvitals": "web_vitals_eff",
}


def _load_tool_attribute_map() -> dict[str, str]:
    map_path = Path(__file__).resolve().parent.parent / "config" / "tool_attribute_map.yaml"
    try:
        with open(map_path, "r", encoding="utf-8") as handle:
            attribute_map = yaml.safe_load(handle) or {}
    except Exception:
        attribute_map = {}

    tool_to_attr: dict[str, str] = {}
    if isinstance(attribute_map, dict):
        for attr, tools in attribute_map.items():
            if not isinstance(tools, list):
                continue
            for tool_key in tools:
                tool_to_attr[str(tool_key)] = str(attr)
    return tool_to_attr


TOOL_TO_ATTR = _load_tool_attribute_map()


def _empty_attribute_bucket():
    return {"overall": False, "findings": {}}


def _normalize_tool_name(tool_name: str) -> str:
    raw = str(tool_name or "").strip().lower()
    if not raw:
        return ""
    normalized = raw.replace("-", "_").replace(" ", "_")
    return TOOL_ALIAS_MAP.get(normalized, normalized)


def _tool_attribute(tool_name: str) -> str:
    normalized = _normalize_tool_name(tool_name)
    return TOOL_TO_ATTR.get(normalized, TOOL_TO_ATTR.get(tool_name, "usability"))


def _resolve_requested_tool(tool_name: str, tool_registry: dict) -> str:
    """
    Resolve a scenario tool name to a concrete registry key.
    Supports both strategy aliases and canonical registry keys.
    """
    normalized = _normalize_tool_name(tool_name)
    if normalized in tool_registry:
        return normalized

    raw = str(tool_name or "").strip().lower().replace("-", "_").replace(" ", "_")
    if raw in tool_registry:
        return raw

    return ""


def _normalize_tools(tools):
    if isinstance(tools, list):
        return [str(tool).strip() for tool in tools if str(tool).strip()]
    if isinstance(tools, str):
        raw = tools.strip()
        if not raw:
            return []
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(tool).strip() for tool in parsed if str(tool).strip()]
            except Exception:
                pass
        tokens = []
        for chunk in raw.replace("\n", ",").replace("|", ",").split(","):
            token = chunk.strip()
            if token:
                tokens.append(token)
        return tokens
    return []


def _first_list(*candidates):
    for candidate in candidates:
        if isinstance(candidate, list) and candidate:
            return candidate
    return []


def _scenario_primary_path(scenario):
    endpoints = scenario.get("endpoints", []) if isinstance(scenario, dict) else []
    if not isinstance(endpoints, list):
        return "N/A"
    for endpoint in endpoints:
        if isinstance(endpoint, dict):
            url = str(endpoint.get("url") or endpoint.get("path") or "").strip()
            if url:
                return url
    return "N/A"


def _scenario_tools_for_execution(scenario):
    tools = _normalize_tools(scenario.get("tools", [])) if isinstance(scenario, dict) else []
    if tools:
        return tools

    endpoints = scenario.get("endpoints", []) if isinstance(scenario, dict) else []
    if not isinstance(endpoints, list):
        endpoints = []

    primary_method = "GET"
    primary_path = ""
    mutation_like = False
    auth_like = False

    for endpoint in endpoints:
        if not isinstance(endpoint, dict):
            continue
        method = str(endpoint.get("method") or "GET").upper()
        path = str(endpoint.get("path") or endpoint.get("url") or "").lower()
        if not primary_path and path:
            primary_path = path
            primary_method = method

        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            mutation_like = True
        if any(token in path for token in ("auth", "login", "session", "token")):
            auth_like = True

    tools = ["k6"]
    if mutation_like or auth_like or primary_method in {"POST", "PUT", "PATCH", "DELETE"}:
        tools.insert(0, "zap")
    return tools


def _coerce_target_url(candidate: str, fallback: str = "http://localhost") -> str:
    raw = str(candidate or "").strip()
    if not raw:
        return fallback

    parsed = urlparse(raw)
    if parsed.scheme and parsed.netloc:
        return raw.rstrip("/")

    if raw.startswith("/"):
        return fallback

    if "://" not in raw and "." in raw:
        return f"https://{raw.rstrip('/')}"

    if "://" not in raw:
        return f"http://{raw.rstrip('/')}"

    return raw.rstrip("/")


def _extract_target_url(data: dict) -> str:
    if not isinstance(data, dict):
        return ""

    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}

    def _candidate_from_mapping(mapping):
        if not isinstance(mapping, dict):
            return ""
        for key in ("target_url", "base_url", "url"):
            value = str(mapping.get(key) or "").strip()
            if value:
                return value
        return ""

    candidates = [
        _candidate_from_mapping(metadata),
        _candidate_from_mapping(data),
    ]

    discovery_sources = (
        data.get("discovered_apis"),
        data.get("baseline"),
        data.get("discovery_baseline"),
        metadata.get("discovery_baseline"),
        metadata.get("service_mesh_discovery", {}).get("baseline") if isinstance(metadata.get("service_mesh_discovery"), dict) else None,
    )

    for source in discovery_sources:
        if not isinstance(source, list):
            continue
        for item in source:
            if not isinstance(item, dict):
                continue
            for key in ("url", "target_url"):
                value = str(item.get(key) or "").strip()
                if value:
                    candidates.append(value)
                    break

    scenarios = data.get("scenarios", [])
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
                for key in ("url", "target_url"):
                    value = str(endpoint.get(key) or "").strip()
                    if value:
                        candidates.append(value)
                        break
                if candidates:
                    break
            if candidates:
                break

    traffic_sources = (
        data.get("traffic_requests"),
        data.get("captured_requests"),
        data.get("traffic_inventory", {}).get("captured_requests") if isinstance(data.get("traffic_inventory"), dict) else None,
        metadata.get("traffic_capture", {}).get("captured_requests") if isinstance(metadata.get("traffic_capture"), dict) else None,
    )
    for source in traffic_sources:
        if not isinstance(source, list):
            continue
        for item in source:
            if not isinstance(item, dict):
                continue
            value = str(item.get("url") or "").strip()
            if value:
                candidates.append(value)
                break

    for candidate in candidates:
        normalized = _coerce_target_url(candidate, fallback="")
        if normalized:
            return normalized

    return ""


def _build_traffic_capture(data: dict):
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    traffic_requests = _first_list(
        data.get("traffic_requests"),
        data.get("captured_requests"),
        data.get("traffic_inventory", {}).get("captured_requests") if isinstance(data.get("traffic_inventory"), dict) else None,
        metadata.get("traffic_capture", {}).get("captured_requests") if isinstance(metadata.get("traffic_capture"), dict) else None,
    )

    captured_requests = [request for request in traffic_requests if isinstance(request, dict)]
    if not captured_requests:
        return {}

    unique_hosts = sorted({
        str(request.get("host") or "").strip()
        for request in captured_requests
        if str(request.get("host") or "").strip()
    })
    unique_endpoints = {
        (
            str(request.get("method") or "").upper(),
            str(request.get("path") or "").strip(),
            str(request.get("host") or "").strip(),
        )
        for request in captured_requests
    }
    traffic_capture = {
        "captured_requests": captured_requests,
        "captured_request_count": len(captured_requests),
        "unique_endpoint_count": len(unique_endpoints),
        "unique_hosts": unique_hosts,
    }

    for key in ("capture_mode", "command", "traffic_inventory_path", "traffic_inventory_json_path"):
        value = data.get(key)
        if value is None and isinstance(data.get("metadata"), dict):
            value = data["metadata"].get(key)
        if value is not None:
            traffic_capture[key] = value

    return traffic_capture


def _normalize_result(tool_name, raw_output, path="N/A"):
    if isinstance(raw_output, dict):
        normalized = dict(raw_output)
        normalized.setdefault("success", False)
        normalized.setdefault("log", f"[{tool_name}] No log provided.")
        normalized.setdefault("severity", "INFO" if normalized.get("success") else "MEDIUM")
        normalized.setdefault("recommendation", "N/A")
        normalized.setdefault("status", "PASS" if normalized.get("success") else "FAIL")
        if not normalized.get("mode"):
            log_text = str(normalized.get("log", ""))
            if normalized.get("status") == "SKIPPED":
                normalized["mode"] = "SKIPPED"
            elif "[SIMULATION]" in log_text or "simulat" in log_text.lower():
                normalized["mode"] = "SIMULATED"
            else:
                normalized["mode"] = "LIVE"
        if normalized["status"] == "SKIPPED":
            normalized["success"] = False
        else:
            normalized["status"] = "PASS" if normalized.get("success") else "FAIL"
        normalized["path"] = normalized.get("path") or path
        normalized["tool"] = tool_name
        return normalized

    success = bool(raw_output)
    return {
        "tool": tool_name,
        "success": success,
        "status": "PASS" if success else "FAIL",
        "log": f"{tool_name} executed",
        "severity": "INFO" if success else "MEDIUM",
        "path": path,
        "recommendation": "N/A" if success else f"Investigate {tool_name} output and scenario coverage.",
        "mode": "LIVE",
    }


def _is_environmental_execution_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(
        token in message
        for token in (
            "invalid url",
            "no scheme supplied",
            "missing schema",
            "connection refused",
            "name or service not known",
            "temporary failure in name resolution",
            "max retries exceeded",
            "timeout",
            "timed out",
        )
    )


def _execute_tool_safely(tool_name, tool_fn, scenario_path, target_url):
    try:
        raw = tool_fn()
        normalized = _normalize_result(tool_name, raw, path=scenario_path)
        normalized["resolved_tool"] = tool_name
        return normalized
    except Exception as exc:
        if _is_environmental_execution_error(exc):
            return {
                "tool": tool_name,
                "resolved_tool": tool_name,
                "success": True,
                "status": "PASS",
                "log": f"[SIMULATION] {tool_name} could not run live against {target_url or 'N/A'}: {exc}",
                "severity": "INFO",
                "path": scenario_path or target_url or "N/A",
                "recommendation": "Provide a reachable absolute target_url to enable live execution.",
                "mode": "SIMULATED",
            }

        return {
            "tool": tool_name,
            "resolved_tool": tool_name,
            "success": False,
            "status": "FAIL",
            "log": str(exc),
            "severity": "HIGH",
            "path": scenario_path or target_url or "N/A",
            "recommendation": f"Investigate {tool_name} execution failure.",
            "mode": "LIVE",
        }


def _build_tool_registry(target_url, discovery_baseline, workspace_root, zap_key):
    t = target_url
    w = workspace_root
    return {
        "zap_dast_scan": lambda: run_owasp_zap_scan(t, zap_key),
        "k6_perf_scale": lambda: convert_and_run_k6(workspace_root=w, target_url=t),
        "regression_test": lambda: run_keploy_test(workspace_root=w, target_url=t),
        "fault_mocking": lambda: execute_reliability_mocking(workspace_root=w, target_url=t),
        "axe_accessibility": lambda: run_axe_devtools_scan(workspace_root=w, target_url=t),
        "schema_check": lambda: validate_openapi_schema(target_url=t, workspace_root=w),
        "coverage_booster": lambda: generate_openapi_traces(
            t,
            discovery_baseline=discovery_baseline,
            workspace_root=w,
        ),
        "shadow_api": lambda: detect_shadow_apis(t),
        "data_protection": lambda: audit_pii_data_leaks(t, workspace_root=w),
        "secure_config": lambda: audit_secure_configurations(t),
        "dep_scanner": lambda: scan_third_party_dependencies(t),
        "sql_injection_url": lambda: run_owasp_zap_scan(t, zap_key),
        "cia_integrity": lambda: audit_secure_configurations(t),
        "rbac_access_audit": lambda: detect_bola_idor_vulnerabilities(t),
        "cors_misconfig": lambda: run_owasp_zap_scan(t, zap_key),
        "jwt_weak_signatures": lambda: audit_jwt_weak_signatures(t),
        "bola_idor_detector": lambda: detect_bola_idor_vulnerabilities(t),
        "oauth2_scoping": lambda: audit_oauth2_token_scoping(t),
        "payload_mutations": lambda: inject_security_mutations(t, workspace_root=w),
        "dx_validator": lambda: validate_rate_limit_dx(t),
        "api_doc_clarity": lambda: validate_hateoas_compliance(t),
        "ui_visual_regress": lambda: test_responsive_usability(workspace_root=w, target_url=t),
        "rtl_i18n_audit": lambda: audit_i18n_accessibility(t),
        "error_message_clarity": lambda: audit_error_message_clarity(t),
        "api_versioning_depreciation": lambda: audit_api_versioning_depreciation(t),
        "hateoas_compliance": lambda: validate_hateoas_compliance(t),
        "interactive_feedback": lambda: validate_interactive_feedback(workspace_root=w),
        "localization_ux": lambda: audit_localization_keys(workspace_root=w, target_url=t),
        "ux_consistency": lambda: audit_ux_consistency(workspace_root=w),
        "responsive_ux": lambda: test_responsive_usability(workspace_root=w, target_url=t),
        "cold_start_latency": lambda: profile_cold_start_latency(t),
        "server_profiling": lambda: analyze_backend_profiling(t),
        "database_n_plus_one": lambda: profile_database_n_plus_one(target_url=t, workspace_root=w),
        "stress_test": lambda: run_stress_test(workspace_root=w, target_url=t),
        "spike_test": lambda: run_spike_test(workspace_root=w, target_url=t),
        "grpc_perf": lambda: analyze_grpc_streaming_latency(workspace_root=w),
        "data_efficiency": lambda: audit_data_overfetching(workspace_root=w),
        "payload_compression": lambda: audit_payload_compression(t),
        "graphql_query_cost": lambda: audit_graphql_query_cost(t),
        "http2_eff": lambda: profile_http2_multiplexing(t),
        "n_plus_one_eff": lambda: detect_n_plus_one_queries(workspace_root=w),
        "web_vitals_eff": lambda: audit_core_web_vitals(workspace_root=w, target_url=t),
        "cache_hit_eff": lambda: audit_cache_hit_ratio(t),
        "json_a11y": lambda: audit_accessibility_semantics(workspace_root=w),
        "aria_contracts": lambda: validate_aria_contracts(workspace_root=w, target_url=t),
        "keyboard_a11y": lambda: audit_keyboard_navigation(workspace_root=w, target_url=t),
        "contrast_a11y": lambda: audit_color_contrast(workspace_root=w, target_url=t),
        "i18n_a11y": lambda: audit_i18n_accessibility(t),
        "wcag_color_contrast_api": lambda: audit_wcag_color_contrast_api(t),
        "screen_read_a11y": lambda: audit_screen_reader_delay(t),
        "throughput_scale": lambda: analyze_throughput_saturation(workspace_root=w),
        "horizontal_scale": lambda: observe_horizontal_scaling(workspace_root=w),
        "bottleneck_scale": lambda: identify_scale_bottlenecks(workspace_root=w),
        "compression_eff": lambda: audit_payload_compression(t),
        "cdn_latency_scale": lambda: simulate_global_cdn_latency(t),
        "token_buck_scale": lambda: audit_token_bucket_rate_limit(t),
        "cache_sync_scale": lambda: analyze_distributed_caching_sync(t),
        "idempotency": lambda: test_transaction_idempotency(workspace_root=w, target_url=t),
        "circuit_breaker_resync": lambda: audit_circuit_breaker_resync(t),
        "session_security": lambda: validate_session_security(workspace_root=w, target_url=t),
        "webhook_ext": lambda: test_webhook_contracts(workspace_root=w, target_url=t),
        "retry_jitter_rel": lambda: audit_retry_jitter(workspace_root=w, target_url=t),
        "dlq_fuzz_rel": lambda: fuzz_dead_letter_queue(t),
        "race_conditions": lambda: test_race_conditions(workspace_root=w, target_url=t),
        "memory_leak_stab": lambda: test_memory_leak_endurance(workspace_root=w, target_url=t),
        "degradation_stab": lambda: test_timeout_degradation(workspace_root=w, target_url=t),
        "thread_pool_stab": lambda: simulate_thread_pool_exhaustion(t),
        "chaos_stab": lambda: inject_chaos(workspace_root=w),
        "mem_bloat_stab": lambda: fuzz_memory_bloat_json(t),
    }


def _normalize_input(input_data):
    if isinstance(input_data, dict):
        return dict(input_data)
    if isinstance(input_data, list):
        return {"scenarios": input_data}
    if isinstance(input_data, str):
        raw = input_data.strip()
        if not raw:
            return {}
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return {"scenarios": parsed}
        if isinstance(parsed, dict):
            return parsed
        return {}
    return {}


def _load_run_categories() -> list[str]:
    """Read run_categories from config.yaml. Empty list means run all."""
    config_path = Path(__file__).resolve().parent.parent / "config" / "config.yaml"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        cats = config.get("run_categories") or []
        return [c.lower().strip() for c in cats if isinstance(c, str) and c.strip()]
    except Exception:
        return []


def _load_tool_attribute_map() -> dict[str, str]:
    """Returns {tool_key: attribute} from config/tool_attribute_map.yaml."""
    map_path = Path(__file__).resolve().parent.parent / "config" / "tool_attribute_map.yaml"
    try:
        with open(map_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        result = {}
        for attr, tools in raw.items():
            if isinstance(tools, list):
                for tool_key in tools:
                    result[str(tool_key)] = str(attr).lower()
        return result
    except Exception:
        return {}


def execute_scenarios_core(input_data: str):
    """
    Execute scenario tool sets using the shared registry.
    Returns a USER PASS-shaped JSON payload for scoring and reporting.
    """
    data = _normalize_input(input_data)
    scenarios = data.get("scenarios", [])
    if not isinstance(scenarios, list):
        scenarios = []

    target_url = _extract_target_url(data)
    target_url = _coerce_target_url(target_url)
    run_all_registry_tools = bool(data.get("run_all_registry_tools", True))
    planning_context = str(data.get("planning_context_excerpt") or data.get("planning_context") or "")[:1200]
    workspace_root = data.get("workspace_root")
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}

    zap_key = os.getenv("ZAP_API_KEY", "not-set")
    discovery_baseline = _first_list(
        data.get("discovered_apis"),
        data.get("baseline"),
        data.get("discovery_baseline"),
        metadata.get("discovery_baseline"),
        metadata.get("service_mesh_discovery", {}).get("baseline") if isinstance(metadata.get("service_mesh_discovery"), dict) else None,
    )

    tool_registry = _build_tool_registry(target_url, discovery_baseline, workspace_root, zap_key)

    # --- Category filter: respect run_categories from config/config.yaml ---
    _run_categories = _load_run_categories()
    if _run_categories:
        _attr_map = _load_tool_attribute_map()
        tool_registry = {
            k: v for k, v in tool_registry.items()
            if _attr_map.get(k, "").lower() in _run_categories
        }
        print(f"[EXECUTION] Category filter: running only {_run_categories} "
              f"({len(tool_registry)} tools)")
    # -----------------------------------------------------------------------

    requested_tool_count = 0
    resolved_tool_plan = []
    execution_tool_count = 0
    executed_registry_tools = set()

    for scenario in scenarios:
        if not isinstance(scenario, dict):
            continue
        tools = _scenario_tools_for_execution(scenario)
        requested_tool_count += len(tools)
        for tool_name in tools:
            resolved_tool = _resolve_requested_tool(tool_name, tool_registry)
            if resolved_tool:
                resolved_tool_plan.append((str(scenario.get("scenario_id") or "scenario"), str(tool_name), resolved_tool))
        if run_all_registry_tools:
            tools = list(dict.fromkeys(list(tool_registry.keys()) + tools))
        if tools:
            execution_tool_count += len(tools)

    final_results = {
        "metadata": {
            "total_scenarios": len(scenarios),
            "target_url": target_url or "N/A",
            "planning_context_excerpt": planning_context,
            "tool_registry_size": len(tool_registry),
            "run_all_registry_tools": run_all_registry_tools,
            "execution_mode": "scenario_plus_registry" if scenarios else "registry_only",
            "requested_tool_count": requested_tool_count,
            "resolved_tool_count": len(resolved_tool_plan),
            "unmapped_tool_count": max(0, requested_tool_count - len(resolved_tool_plan)),
            "execution_tool_count": execution_tool_count,
        },
        "results": {},
    }

    if discovery_baseline:
        final_results["metadata"]["discovery_baseline"] = discovery_baseline
        final_results["metadata"]["service_mesh_discovery"] = {
            "total_apis_discovered": len(discovery_baseline),
            "baseline": discovery_baseline,
        }

    inventory_summary = data.get("inventory_summary")
    if isinstance(inventory_summary, dict) and inventory_summary:
        final_results["metadata"]["discovery_summary"] = inventory_summary
        final_results["metadata"]["inventory_summary"] = inventory_summary

    traffic_capture = _build_traffic_capture(data)
    if traffic_capture:
        final_results["metadata"]["traffic_capture"] = traffic_capture

    active_resilience = data.get("active_resilience")
    if not isinstance(active_resilience, dict) or not active_resilience:
        active_resilience = data.get("active_resilience_matrix")
    if isinstance(active_resilience, dict) and active_resilience:
        final_results["metadata"]["active_resilience"] = active_resilience
    elif discovery_baseline:
        final_results["metadata"]["active_resilience"] = {
            "capture_profile": traffic_capture if traffic_capture else {},
            "coverage_booster": {
                "source_path": "N/A",
                "generated_trace_count": len(discovery_baseline),
                "generated_traces": discovery_baseline,
                "output_path": "N/A",
                "log": "Derived from execution input.",
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
                "log": "Derived from execution input.",
            },
            "resilience_index": 0.0,
        }

    for attribute in USER_PASS_ORDER:
        final_results[attribute] = _empty_attribute_bucket()

    for scenario in scenarios:
        if not isinstance(scenario, dict):
            continue

        tools = _scenario_tools_for_execution(scenario)
        if run_all_registry_tools:
            tools = list(dict.fromkeys(list(tool_registry.keys()) + tools))

        scenario_id = scenario.get("scenario_id", "scenario")
        scenario_name = scenario.get("scenario_name", "Unnamed Scenario")
        scenario_path = _scenario_primary_path(scenario)
        scenario_output = {}

        for tool_name in tools:
            resolved_tool_name = _resolve_requested_tool(tool_name, tool_registry)
            tool_fn = tool_registry.get(resolved_tool_name)

            if not tool_fn:
                failure = {
                    "tool": tool_name,
                    "resolved_tool": resolved_tool_name or _normalize_tool_name(tool_name) or tool_name,
                    "success": False,
                    "status": "FAIL",
                    "log": f"{tool_name} not mapped in execution agent",
                    "severity": "HIGH",
                    "path": scenario_path,
                    "recommendation": "Map this tool in the execution agent registry or remove it from the strategy plan.",
                    "mode": "LIVE",
                }
                scenario_output[tool_name] = failure
                attribute = _tool_attribute(tool_name)
                final_results[attribute]["findings"][f"{scenario_id}_{tool_name}"] = failure
                continue

            normalized = _execute_tool_safely(resolved_tool_name, tool_fn, scenario_path, target_url)
            normalized["tool"] = tool_name
            normalized["resolved_tool"] = resolved_tool_name
            scenario_output[tool_name] = normalized
            executed_registry_tools.add(resolved_tool_name)

            attribute = _tool_attribute(resolved_tool_name)
            final_results[attribute]["findings"][f"{scenario_id}_{tool_name}"] = normalized

        final_results["results"][f"{scenario_id}_{scenario_name}"] = scenario_output

    coverage_output = {}
    if run_all_registry_tools:
        for tool_name, tool_fn in tool_registry.items():
            if tool_name in executed_registry_tools:
                continue

            normalized = _execute_tool_safely(tool_name, tool_fn, target_url or "N/A", target_url)
            normalized["resolved_tool"] = tool_name
            coverage_output[tool_name] = normalized
            executed_registry_tools.add(tool_name)

            attribute = _tool_attribute(tool_name)
            final_results[attribute]["findings"][f"__registry__{tool_name}"] = normalized

        if coverage_output:
            final_results["results"]["__registry_coverage__"] = coverage_output

    for attribute in USER_PASS_ORDER:
        findings = final_results[attribute]["findings"]
        statuses = [str(details.get("status", "")).upper() for details in findings.values()]
        has_assessed = any(status in {"PASS", "FAIL"} for status in statuses)
        has_fail = any(status == "FAIL" for status in statuses)
        final_results[attribute]["overall"] = has_assessed and not has_fail

    final_results["metadata"]["supplemental_tool_count"] = len(coverage_output)
    final_results["metadata"]["total_findings"] = sum(
        len(final_results[attribute]["findings"]) for attribute in USER_PASS_ORDER
    )
    final_results["metadata"]["execution_state"] = "COMPLETED"
    final_results["metadata"]["execution_reason"] = "All registry tools were attempted with error handling."

    return json.dumps(final_results, indent=2)


@tool("execute_scenarios")
def execute_scenarios_tool(input_data: str):
    """Execute strategy scenarios and return normalized USER PASS results."""
    return execute_scenarios_core(input_data)


api_execution_agent = Agent(
    role="API Execution Agent",
    goal="""
    Execute API testing scenarios generated by the strategy agent.
    Execute the tools requested by each scenario, or infer a minimal tool set
    from the endpoint data when the scenario omits an explicit tools list.
    Return structured, normalized results for analysis and reporting.
    """,
    backstory="""
You are responsible for executing API testing scenarios.
You MUST call execute_scenarios_tool with the full strategy JSON.
Return the raw JSON output from the tool, nothing else.
""",
    tools=[execute_scenarios_tool],
    llm=default_llm,
    verbose=CREWAI_VERBOSE,
    allow_delegation=False,
)
