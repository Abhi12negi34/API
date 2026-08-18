import json
import copy
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen

import yaml

from core.api.discovery_inventory import build_discovery_inventory
from reports.user_pass_certification_scorer import CertificationScorer
from crewai_bootstrap import bootstrap_crewai_runtime
from tools.runtime_config import CREWAI_VERBOSE


os.environ.setdefault("OPENAI_API_KEY", "mock_key")
bootstrap_crewai_runtime()


def _configure_crewai_storage():
    storage_root = Path.cwd() / ".crewai_storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    os.environ["CREWAI_STORAGE_DIR"] = Path.cwd().name or "ai-api-testing-agent"
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    def _local_db_storage_path() -> str:
        storage_root.mkdir(parents=True, exist_ok=True)
        return str(storage_root)

    import crewai.utilities.paths as crew_paths
    import crewai.memory.storage.kickoff_task_outputs_storage as kickoff_storage

    crew_paths.db_storage_path = _local_db_storage_path
    kickoff_storage.db_storage_path = _local_db_storage_path


def _probe_ollama_backend(timeout_seconds: int = 2) -> tuple[bool, str]:
    base_url = os.environ.get("OLLAMA_BASE_URL") or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434"
    base_url = base_url.rstrip("/")
    if base_url.endswith("/v1"):
        base_url = base_url[:-3]
    probe_url = f"{base_url}/api/tags"
    try:
        with urlopen(probe_url, timeout=timeout_seconds) as response:
            status = getattr(response, "status", 200)
            return True, f"{probe_url} responded with HTTP {status}"
    except Exception as exc:
        return False, f"{probe_url} unavailable: {exc}"


def _resolve_ollama_base_url(config: dict | None = None) -> str:
    env_base_url = os.environ.get("OLLAMA_BASE_URL") or os.environ.get("OLLAMA_HOST")
    if env_base_url:
        return env_base_url

    if isinstance(config, dict):
        ollama_config = config.get("ollama", {})
        host = str(ollama_config.get("host", "")).strip()
        if host:
            return host

    return "http://127.0.0.1:11434"
def _crew_output_raw(crew_output) -> str:
    if crew_output is None:
        return ""

    raw = getattr(crew_output, "raw", None)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()

    json_dict = getattr(crew_output, "json_dict", None)
    if isinstance(json_dict, dict) and json_dict:
        try:
            return json.dumps(json_dict, indent=2)
        except Exception:
            return str(json_dict)

    return str(crew_output).strip()
def _run_crewai_planning_phase(target_url: str, discovery_result: dict, capture_telemetry=None) -> dict:
    from crewai import Crew, Process, Task
    from agents.api_discovery_agent import api_discovery_agent, set_discovery_url
    from agents.api_strategy_agent import api_strategy_agent

    set_discovery_url(target_url)
    print("[CrewAI] Initializing planning crew.")
    print(f"[CrewAI] Discovery agent: {api_discovery_agent.role}")
    print(f"[CrewAI] Strategy agent: {api_strategy_agent.role}")

    discovery_task = Task(
        name="discover_api_surface",
        description=(
            f"Load the API discovery inventory for {target_url}. "
            "Use discover_api_surface_tool with the provided URL and return only raw JSON."
        ),
        expected_output="Raw JSON inventory with discovered_apis and traffic_requests.",
        agent=api_discovery_agent,
        markdown=False,
    )

    strategy_task = Task(
        name="design_api_strategy",
        description=(
            f"Design grounded API testing scenarios for {target_url}. "
            "Use the discovery output from the previous task, the provided traffic capture, "
            "and the inventory summary. Return raw JSON only."
        ),
        expected_output="Raw JSON containing target_url, site_type, inventory_summary, and scenarios.",
        agent=api_strategy_agent,
        context=[discovery_task],
        markdown=False,
    )

    crew = Crew(
        name="api_planning_crew",
        agents=[api_discovery_agent, api_strategy_agent],
        tasks=[discovery_task, strategy_task],
        process=Process.sequential,
        verbose=CREWAI_VERBOSE,
        cache=False,
        memory=False,
    )

    backend_ok, backend_message = _probe_ollama_backend()
    if backend_ok:
        print(f"[CrewAI] Backend check passed: {backend_message}")
    else:
        print(f"[CrewAI] Backend check failed: {backend_message}")
        print("[CrewAI] Crew will still try to run, but output may fall back if no LLM is reachable.")

    print("[CrewAI] Starting kickoff.")
    crew_output = crew.kickoff(
        inputs={
            "target_url": target_url,
            "inventory_summary": discovery_result.get("inventory_summary", {}) if isinstance(discovery_result, dict) else {},
            "site_type": discovery_result.get("site_type", "api") if isinstance(discovery_result, dict) else "api",
            "discovered_apis": discovery_result.get("discovered_apis", []) if isinstance(discovery_result, dict) else [],
            "traffic_capture": capture_telemetry if isinstance(capture_telemetry, dict) else {},
            "grounded_discovery_json": json.dumps(discovery_result, indent=2) if isinstance(discovery_result, dict) else "{}",
        }
    )

    parsed = _parse_json_blob(_crew_output_raw(crew_output))
    if isinstance(parsed, list):
        parsed = {"scenarios": parsed}

    base_payload = _build_grounded_strategy_payload(target_url, discovery_result, capture_telemetry)
    if isinstance(parsed, dict) and _strategy_payload_is_grounded(parsed, target_url):
        merged = base_payload.copy()  # Start with a copy to avoid modifying the original

        for key in ("target_url", "site_type", "inventory_summary", "scenarios", "planning_context_excerpt"):
            if key in parsed and parsed[key] is not None:
                merged[key] = parsed[key].copy() if isinstance(parsed[key], dict) or isinstance(parsed[key], list) else parsed[key]

        for key in ("discovered_apis", "baseline", "discovery_baseline", "traffic_capture", "metadata"):
            if key in parsed and parsed[key] is not None:
                if key == "metadata" and isinstance(parsed[key], dict):
                    merged_metadata = merged.get("metadata") if isinstance(merged.get("metadata"), dict) else {}
                    merged_metadata.update(parsed[key].copy())
                    merged["metadata"] = merged_metadata
                else:
                    merged[key] = parsed[key].copy() if isinstance(parsed[key], dict) or isinstance(parsed[key], list) else parsed[key]

        base_scenarios = base_payload.get("scenarios", [])
        merged_scenarios = merged.get("scenarios", [])
        for index, scenario in enumerate(merged_scenarios):
            if not isinstance(scenario, dict) or scenario.get("steps") is None:
                continue
            if index < len(base_scenarios) and isinstance(base_scenarios[index], dict) and base_scenarios[index].get("steps") is not None:
                scenario["steps"] = base_scenarios[index]["steps"].copy()

        merged["run_all_registry_tools"] = True
        if "metadata" not in merged:
            merged["metadata"] = {}
        merged["metadata"].setdefault("target_url", target_url)
        merged["metadata"].setdefault("site_type", merged.get("site_type", "api"))
        merged["metadata"].setdefault("inventory_summary", merged.get("inventory_summary", {}))
        merged["metadata"].setdefault("discovery_baseline", merged.get("discovered_apis", []))
        merged["metadata"].setdefault("traffic_capture", merged.get("traffic_capture", {}))
        return merged

    return base_payload
def load_config():
    with open("config/config.yaml", "r") as f:
        return yaml.safe_load(f)


def _task_output_to_dict(task):
    output = getattr(task, "output", None)
    if output is None:
        return {}

    json_dict = getattr(output, "json_dict", None)
    if isinstance(json_dict, dict):
        return json_dict

    raw = getattr(output, "raw", "")
    if not raw:
        return {}

    try:
        return json.loads(raw)
    except Exception:
        parsed = _parse_json_blob(raw)
        if isinstance(parsed, dict):
            return parsed
        elif isinstance(parsed, list):
            return {"scenarios": parsed}
        else:
            return {"raw_output": raw}
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


def _normalize_host(value: str) -> str:
    parsed = urlparse(str(value or "").strip())
    host = (parsed.netloc or parsed.path or "").strip().lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _same_host(left: str, right: str) -> bool:
    return bool(_normalize_host(left) and _normalize_host(left) == _normalize_host(right))


from urllib.parse import urljoin

def _normalize_strategy_url(base_url: str, value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return str(base_url or "").strip()
    if raw.startswith(("http://", "https://")):
        return raw

    base = str(base_url or "").strip().rstrip("/")
    if not base:
        return raw
    
    return urljoin(f"{base}/", raw.lstrip("/"))
def _path_family(path: str) -> str:
    raw = str(path or "").strip()
    if not raw:
        return "/"

    parsed = urlparse(raw)
    if parsed.scheme or parsed.netloc:
        raw_path = parsed.path
    else:
        raw_path = raw.split("?", 1)[0]

    parts = []
    for segment in raw_path.split("/"):
        cleaned = segment.strip()
        if not cleaned or cleaned.isdigit():
            continue

        if re.fullmatch(r"[0-9a-fA-F]{8,}", cleaned) and any(ch.isdigit() for ch in cleaned):
            continue
        parts.append(cleaned)

    if not parts:
        return "/"
    return "/" + "/".join(parts[:3])
def _scenario_name_from_family(family: str, method: str) -> str:
    tokens = [piece for piece in str(family or "").strip("/").split("/") if piece]
    if not tokens:
        return f"{method.upper()} API Root"
    name = " ".join(token.replace("-", " ").replace("_", " ").title() for token in tokens)
    return f"{name} {method.upper()} Scenario"


def _build_scenario_steps(api: dict, target_url: str) -> list[dict]:
    method = str(api.get("method") or "GET").upper()
    path = str(api.get("path") or api.get("full_url") or "").strip()
    full_url = str(api.get("observed_url") or api.get("full_url") or _normalize_strategy_url(target_url, path)).strip()

    steps = [
        {
            "step_id": 1,
            "action": "Identify the endpoint from the discovery inventory",
            "expected_result": f"{method} {path or full_url} is selected for execution.",
        },
        {
            "step_id": 2,
            "action": "Prepare the request context from the captured traffic or endpoint metadata",
            "expected_result": "The request inputs are grounded in the current run.",
        },
        {
            "step_id": 3,
            "action": f"Execute the {method} request against the live target",
            "expected_result": "The API responds with a live response or a simulation-safe fallback.",
        },
        {
            "step_id": 4,
            "action": "Validate the response payload, status, and behavioral expectations",
            "expected_result": "The response matches the discovered behavior for this endpoint.",
        },
    ]

    if method in {"POST", "PUT", "PATCH", "DELETE"} or any(token in path.lower() for token in ("auth", "login", "session", "token")):
        steps.append(
            {
                "step_id": 5,
                "action": "Verify mutation, authorization, or session-specific side effects",
                "expected_result": "Security-sensitive behavior is confirmed for the workflow.",
            }
        )

    if len(path.split("/")) > 4 or "?" in full_url:
        steps.append(
            {
                "step_id": len(steps) + 1,
                "action": "Check edge-case query parameters and nested resource behavior",
                "expected_result": "Parameterized or nested routes remain stable.",
            }
        )

    return steps


def _scenario_tools_for_endpoint(endpoint: dict) -> list[str]:
    method = str(endpoint.get("method") or "GET").upper()
    path = str(endpoint.get("path") or endpoint.get("url") or "").lower()
    tools = ["k6"]
    if method in {"POST", "PUT", "PATCH", "DELETE"} or any(token in path for token in ("auth", "login", "session", "token")):
        tools.insert(0, "zap")
    return list(dict.fromkeys(tools))


def _request_is_api_candidate(request: dict) -> bool:
    if not isinstance(request, dict):
        return False
    if request.get("is_navigation"):
        return False

    path = str(request.get("path") or "").strip().lower()
    if not path:
        return False

    resource_type = str(request.get("resource_type") or "").strip().lower()
    if resource_type in {"fetch", "xhr", "websocket", "ping"}:
        return True

    response_headers = request.get("response_headers")
    content_type = ""
    if isinstance(response_headers, dict):
        content_type = str(response_headers.get("content-type") or "").lower()
    if "json" in content_type or "graphql" in content_type:
        return True

    if str(request.get("method") or "GET").upper() not in {"GET", "HEAD"}:
        return True

    api_markers = ("api/", "/api", "auth", "login", "session", "token", "graphql", "admin", "orders", "products", "notifications")
    if any(marker in path for marker in api_markers):
        return True

    if "?" in path and not any(path.endswith(ext) for ext in (".css", ".gif", ".htm", ".html", ".ico", ".jpeg", ".jpg", ".js", ".map", ".mp3", ".mp4", ".png", ".svg", ".ttf", ".webm", ".webp", ".woff", ".woff2")):
        return True

    return False


def _build_grounded_strategy_payload(target_url: str, discovery_data=None, capture_telemetry=None) -> dict:
    discovery_data = discovery_data if isinstance(discovery_data, dict) else {}
    discovered_apis = discovery_data.get("discovered_apis", [])
    if not isinstance(discovered_apis, list):
        discovered_apis = []

    normalized_discovered = []
    seen = set()
    for api in discovered_apis:
        if not isinstance(api, dict):
            continue
        method = str(api.get("method") or "GET").upper()
        path = str(api.get("path") or "").strip()
        full_url = _normalize_strategy_url(target_url, api.get("full_url") or api.get("url") or path)
        full_url = full_url.split("?", 1)[0] if full_url else full_url
        key = (method, full_url, path)
        if key in seen:
            continue
        seen.add(key)
        normalized_discovered.append({
            "method": method,
            "path": path or urlparse(full_url).path or "/",
            "full_url": full_url,
            "observed_url": api.get("observed_url") or api.get("full_url") or full_url,
            "status": api.get("status", 200),
            "description": api.get("description") or "Discovered API endpoint",
            "capture_mode": api.get("capture_mode", "discovery"),
            "target_url": target_url,
            "source_file": api.get("source_file", "discovery"),
            "observed_host": api.get("observed_host"),
            "requested_host": api.get("requested_host"),
            "resource_type": api.get("resource_type"),
            "request_kind": api.get("request_kind"),
            "is_api_candidate": api.get("is_api_candidate"),
            "confidence": api.get("confidence"),
        })

    capture_requests = []
    if isinstance(capture_telemetry, dict):
        capture_requests = capture_telemetry.get("captured_requests", [])
    if isinstance(capture_requests, list):
        for request in capture_requests:
            if not _request_is_api_candidate(request):
                continue
            method = str(request.get("method") or "GET").upper()
            full_url = str(request.get("url") or "").strip()
            path = str(request.get("path") or "").strip()
            if not full_url:
                full_url = _normalize_strategy_url(target_url, path)
            full_url = full_url.split("?", 1)[0] if full_url else full_url
            if not path and full_url:
                path = urlparse(full_url).path or "/"
            if not path:
                continue
            key = (method, full_url, path)
            if key in seen:
                continue
            seen.add(key)
            normalized_discovered.append({
                "method": method,
                "path": path,
                "full_url": full_url,
                "observed_url": request.get("url") or full_url,
                "status": request.get("status", 200),
                "description": "Captured from Playwright traffic",
                "capture_mode": "playwright",
                "target_url": target_url,
                "source_file": "traffic-capture",
                "observed_host": request.get("host"),
                "requested_host": request.get("host"),
                "resource_type": request.get("resource_type"),
                "request_kind": "api_candidate",
                "is_api_candidate": True,
                "confidence": "high",
            })

    scenarios = []
    for index, api in enumerate(normalized_discovered, start=1):
        method = str(api.get("method") or "GET").upper()
        path = str(api.get("path") or api.get("full_url") or "").strip()
        family = _path_family(path)
        scenario_name = _scenario_name_from_family(family, method)
        scenario_path = api.get("full_url") or _normalize_strategy_url(target_url, path)
        scenarios.append(
            {
                "scenario_id": f"SCN-{index:03d}",
                "scenario_name": scenario_name,
                "description": f"Exercise the discovered endpoint {path or scenario_path} using live traffic-derived data.",
                "user_story": f"As a user, I want the {path or 'API'} endpoint to respond correctly so the application workflow stays stable.",
                "api_role": "api",
                "endpoints": [
                    {
                        "method": method,
                        "url": scenario_path,
                        "source": api.get("source_file", "discovery"),
                        "expected_behavior": api.get("description") or "Returns a valid API response.",
                    }
                ],
                "steps": _build_scenario_steps(api, target_url),
                "performance_intent": "Validate live API behavior using the discovered endpoint surface.",
                "testing_goal": f"Confirm the {path or scenario_path} endpoint behaves as discovered.",
            }
        )

    traffic_capture = {}
    if isinstance(capture_telemetry, dict) and capture_telemetry:
        traffic_capture = copy.deepcopy(capture_telemetry)
    elif isinstance(discovery_data.get("traffic_capture"), dict):
        traffic_capture = copy.deepcopy(discovery_data.get("traffic_capture"))

    inventory_summary = discovery_data.get("inventory_summary")
    if not isinstance(inventory_summary, dict):
        inventory_summary = {}

    site_type = discovery_data.get("site_type") or "api"
    metadata = {
        "target_url": target_url,
        "site_type": site_type,
        "inventory_summary": inventory_summary,
        "discovered_apis": normalized_discovered,
        "discovery_baseline": normalized_discovered,
        "discovery_summary": inventory_summary,
        "traffic_capture": traffic_capture,
    }

    return {
        "target_url": target_url,
        "site_type": site_type,
        "inventory_summary": inventory_summary,
        "discovered_apis": normalized_discovered,
        "baseline": normalized_discovered,
        "discovery_baseline": normalized_discovered,
        "traffic_capture": traffic_capture,
        "metadata": metadata,
        "scenarios": scenarios,
        "run_all_registry_tools": True,
        "planning_context_excerpt": "Deterministic strategy derived from the discovered API inventory.",
    }


def _strategy_payload_is_grounded(strategy_payload: dict, target_url: str) -> bool:
    if not isinstance(strategy_payload, dict):
        return False
    metadata = strategy_payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    payload_target = str(strategy_payload.get("target_url") or metadata.get("target_url") or "").strip()
    if not payload_target:
        return False
    if not _same_host(payload_target, target_url):
        return False
    scenarios = strategy_payload.get("scenarios", [])
    if not isinstance(scenarios, list) or not scenarios:
        return False
    return True


def _build_report_payload(execution_data, discovery_data=None, strategy_data=None):
    payload = copy.deepcopy(execution_data) if isinstance(execution_data, dict) else {}
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    payload["metadata"] = metadata

    def _first_list(*candidates):
        for candidate in candidates:
            if isinstance(candidate, list) and candidate:
                return candidate
        return []

    def _build_traffic_capture(requests, source=None):
        captured_requests = [request for request in requests if isinstance(request, dict)]
        unique_hosts = sorted(
            {
                str(request.get("host") or "").strip()
                for request in captured_requests
                if str(request.get("host") or "").strip()
            }
        )
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
        if isinstance(source, dict):
            for key in ("capture_mode", "command", "traffic_inventory_path", "traffic_inventory_json_path"):
                if source.get(key) is not None:
                    traffic_capture[key] = source.get(key)
        return traffic_capture

    discovery_sources = []
    if isinstance(discovery_data, dict):
        discovery_sources.append(discovery_data)
    if isinstance(strategy_data, dict):
        discovery_sources.append(strategy_data)

    discovery_baseline = metadata.get("discovery_baseline")
    if not isinstance(discovery_baseline, list) or not discovery_baseline:
        for source in discovery_sources:
            metadata_source = source.get("metadata") if isinstance(source.get("metadata"), dict) else {}
            discovery_baseline = _first_list(
                source.get("discovered_apis"),
                source.get("baseline"),
                source.get("discovery_baseline"),
                metadata_source.get("discovery_baseline"),
                metadata_source.get("service_mesh_discovery", {}).get("baseline") if isinstance(metadata_source.get("service_mesh_discovery"), dict) else None,
            )
            if discovery_baseline:
                break

    if discovery_baseline:
        metadata["discovery_baseline"] = discovery_baseline
        service_mesh = metadata.get("service_mesh_discovery")
        if not isinstance(service_mesh, dict):
            service_mesh = {}
        service_mesh["baseline"] = discovery_baseline
        service_mesh["total_apis_discovered"] = len(discovery_baseline)
        metadata["service_mesh_discovery"] = service_mesh

    inventory_summary = metadata.get("discovery_summary")
    if not isinstance(inventory_summary, dict):
        inventory_summary = {}
    for source in discovery_sources:
        candidate_summary = source.get("inventory_summary")
        if isinstance(candidate_summary, dict) and candidate_summary:
            inventory_summary.update(candidate_summary)
    if inventory_summary:
        metadata["discovery_summary"] = inventory_summary

    traffic_capture = metadata.get("traffic_capture")
    if not isinstance(traffic_capture, dict):
        traffic_capture = {}

    traffic_requests = _first_list(
        traffic_capture.get("captured_requests"),
        metadata.get("traffic_requests"),
        metadata.get("traffic_inventory", {}).get("captured_requests") if isinstance(metadata.get("traffic_inventory"), dict) else None,
    )
    if not traffic_requests:
        for source in discovery_sources:
            source_meta = source.get("metadata") if isinstance(source.get("metadata"), dict) else {}
            traffic_requests = _first_list(
                source.get("traffic_requests"),
                source.get("captured_requests"),
                source_meta.get("traffic_capture", {}).get("captured_requests") if isinstance(source_meta.get("traffic_capture"), dict) else None,
                source_meta.get("traffic_inventory", {}).get("captured_requests") if isinstance(source_meta.get("traffic_inventory"), dict) else None,
            )
            if traffic_requests:
                break

    if traffic_requests:
        traffic_capture = _build_traffic_capture(traffic_requests, source=traffic_capture)
        metadata["traffic_capture"] = traffic_capture

    if "site_type" not in metadata:
        for source in discovery_sources:
            site_type = source.get("site_type")
            if site_type:
                metadata["site_type"] = site_type
                break

    if "inventory_summary" not in metadata and isinstance(discovery_data, dict):
        inventory_summary = discovery_data.get("inventory_summary")
        if isinstance(inventory_summary, dict):
            metadata["inventory_summary"] = inventory_summary

    active_resilience = metadata.get("active_resilience")
    if not isinstance(active_resilience, dict) or not active_resilience:
        for candidate in (
            payload.get("active_resilience_matrix"),
            payload.get("active_resilience"),
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
                "log": "Derived from merged discovery and execution payload.",
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
                "log": "Derived from merged discovery and execution payload.",
            },
            "resilience_index": 0.0,
        }

    metadata["active_resilience"] = active_resilience

    if isinstance(strategy_data, dict):
        for key in ("scenarios", "site_type", "inventory_summary", "discovered_apis", "baseline", "discovery_baseline", "traffic_capture"):
            if key in strategy_data and key not in payload:
                payload[key] = copy.deepcopy(strategy_data[key])

    return payload


def main():
    print("Initializing Autonomous AI API Testing Agent (USER PASS Certification Authority)")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    verbose_state = "enabled" if CREWAI_VERBOSE else "disabled"
    print(f"[CrewAI] Verbose logging is {verbose_state}. Set CREWAI_VERBOSE=true for more detail.")

    _configure_crewai_storage()
    config = load_config()
    ollama_base_url = _resolve_ollama_base_url(config)
    os.environ.setdefault("OLLAMA_BASE_URL", ollama_base_url)
    os.environ.setdefault("OLLAMA_HOST", ollama_base_url)

    target_url = sys.argv[1] if len(sys.argv) > 1 else None
    if not target_url:
        print("Error: Target URL required.")
        sys.exit(1)

    manual_mode = "--manual" in sys.argv

    from agents.api_discovery_agent import set_discovery_url

    set_discovery_url(target_url)

    from core.api.playwright_stimulator import run_playwright_stimulator

    playwright_config = config.get("playwright", {})
    if not isinstance(playwright_config, dict):
        playwright_config = {}
    auth_config = config.get("auth", {})
    if not isinstance(auth_config, dict):
        auth_config = {}

    aggressive_discovery = playwright_config.get("aggressive_discovery")
    if isinstance(aggressive_discovery, str):
        aggressive_discovery = aggressive_discovery.strip().lower() in {"1", "true", "yes", "on"}
    if aggressive_discovery is not None:
        os.environ["DISCOVERY_AGGRESSIVE"] = "true" if aggressive_discovery else "false"

    if manual_mode:
        from core.api.manual_capture import run_manual_capture_session
        print("\n[Pre-Step] Manual capture mode enabled.")
        capture_telemetry = run_manual_capture_session(
            target_url=target_url,
            workspace_root=Path.cwd(),
            slow_mo_ms=playwright_config.get("slow_mo_ms") or 100,
            auth_password=auth_config.get("password") or "",
        )
    else:
        print("\n[Pre-Step] Running Playwright traffic capture...")
        capture_telemetry = run_playwright_stimulator(
            target_url=target_url,
            workspace_root=Path.cwd(),
            headless=playwright_config.get("headless"),
            slow_mo_ms=playwright_config.get("slow_mo_ms"),
            capture_trace=playwright_config.get("capture_trace"),
            capture_screenshots=playwright_config.get("capture_screenshots"),
            devtools=playwright_config.get("devtools"),
            aggressive_discovery=aggressive_discovery,
            auth_config=auth_config,
            max_pages=playwright_config.get("max_pages"),
            max_links=playwright_config.get("max_links"),
            max_clicks=playwright_config.get("max_clicks"),
            time_budget_s=playwright_config.get("time_budget_s"),
            stable_page_limit=playwright_config.get("stable_page_limit"),
            probe_ceiling=playwright_config.get("probe_ceiling"),
        )

    discovery_result = build_discovery_inventory(
        target_url,
        workspace_root=Path.cwd(),
        aggressive=aggressive_discovery,
    )
    if not isinstance(discovery_result, dict):
        discovery_result = {}

    # ==============================
    # Phase 1: Discovery + Strategy
    # ==============================
    print(f"\n[Phase 1] Discovery & Strategy: Mapping API surface for {target_url}...")
    print("[Phase 1] Running CrewAI discovery and strategy planning.")
    from agents.api_execution_agent import execute_scenarios_core

    backend_ok, backend_message = _probe_ollama_backend()
    if not backend_ok:
        print(f"[Phase 1] CrewAI backend unavailable, skipping live crew run: {backend_message}")
        strategy_payload = _build_grounded_strategy_payload(target_url, discovery_result, capture_telemetry)
    else:
        print(f"[Phase 1] CrewAI backend ready: {backend_message}")

        try:
            strategy_payload = _run_crewai_planning_phase(target_url, discovery_result, capture_telemetry)
            print("[Phase 1] CrewAI planning completed successfully.")
        except Exception as exc:
            print(f"[Phase 1] CrewAI planning failed, falling back to deterministic strategy: {exc}")
            strategy_payload = _build_grounded_strategy_payload(target_url, discovery_result, capture_telemetry)

    deterministic_execution_raw = execute_scenarios_core(json.dumps(strategy_payload))
    try:
        deterministic_execution_result = json.loads(deterministic_execution_raw)
    except Exception:
        deterministic_execution_result = {"raw_output": deterministic_execution_raw}

    parsed_result = _build_report_payload(deterministic_execution_result, discovery_result, strategy_payload)
    if not parsed_result:
        parsed_result = {"raw_output": deterministic_execution_raw}

    scorer = CertificationScorer(config["weights"])
    scorer.generate_user_pass_scorecard(parsed_result)

    print("\nAssessment complete. USER PASS Certificate generated.")


if __name__ == "__main__":
    main()

