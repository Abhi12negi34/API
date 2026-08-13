import json
import os

os.environ.setdefault("CREWAI_STORAGE_DIR", "ai-api-testing-agent")

import agents.api_execution_agent as api_execution_agent


def _tool_result(tool_name):
    return {
        "success": True,
        "status": "PASS",
        "log": f"{tool_name} ok",
        "severity": "INFO",
        "mode": "LIVE",
    }


def test_empty_scenarios_still_run_registry_when_enabled(monkeypatch):
    called = {"unused": False}

    def build_registry(*args, **kwargs):
        def unused_tool():
            called["unused"] = True
            return _tool_result("unused_tool")

        return {"unused_tool": unused_tool}

    monkeypatch.setattr(api_execution_agent, "_build_tool_registry", build_registry)

    payload = json.loads(
        api_execution_agent.execute_scenarios_core(
            json.dumps({"scenarios": []})
        )
    )

    assert payload["metadata"]["run_all_registry_tools"] is True
    assert "__registry_coverage__" in payload["results"]
    assert payload["results"]["__registry_coverage__"]["unused_tool"]["status"] == "PASS"
    assert called["unused"] is True


def test_alias_tool_mapping_executes_only_requested_tools(monkeypatch):
    called = {"unused": False}

    def build_registry(*args, **kwargs):
        def unused_tool():
            called["unused"] = True
            return _tool_result("unused_tool")

        return {
            "k6_perf_scale": lambda: _tool_result("k6_perf_scale"),
            "keyboard_a11y": lambda: _tool_result("keyboard_a11y"),
            "unused_tool": unused_tool,
        }

    monkeypatch.setattr(api_execution_agent, "_build_tool_registry", build_registry)

    payload = json.loads(
        api_execution_agent.execute_scenarios_core(
            json.dumps(
                {
                    "scenarios": [
                        {
                            "scenario_id": "scenario-1",
                            "scenario_name": "Alias Mapping",
                            "tools": ["k6", "playwright"],
                        }
                    ],
                    "run_all_registry_tools": True,
                }
            )
        )
    )

    scenario = payload["results"]["scenario-1_Alias Mapping"]
    assert payload["metadata"]["run_all_registry_tools"] is True
    assert payload["metadata"]["supplemental_tool_count"] == 0
    assert "__registry_coverage__" not in payload["results"]
    assert "scenario-1_unused_tool" in payload["usability"]["findings"]
    assert scenario["k6"]["resolved_tool"] == "k6_perf_scale"
    assert scenario["playwright"]["resolved_tool"] == "keyboard_a11y"
    assert scenario["unused_tool"]["status"] == "PASS"
    assert called["unused"] is True


def test_string_tool_list_is_normalized(monkeypatch):
    called = {"k6": False}

    def build_registry(*args, **kwargs):
        def k6_tool():
            called["k6"] = True
            return _tool_result("k6_perf_scale")

        return {"k6_perf_scale": k6_tool}

    monkeypatch.setattr(api_execution_agent, "_build_tool_registry", build_registry)

    payload = json.loads(
        api_execution_agent.execute_scenarios_core(
            json.dumps(
                {
                    "scenarios": [
                        {
                            "scenario_id": "scenario-1",
                            "scenario_name": "String Tools",
                            "tools": "k6, playwright",
                        }
                    ],
                    "run_all_registry_tools": False,
                }
            )
        )
    )

    assert payload["metadata"].get("execution_state") != "SKIPPED"
    assert payload["metadata"]["resolved_tool_count"] == 1
    assert called["k6"] is True


def test_unmapped_tools_do_not_trigger_execution(monkeypatch):
    called = {"unused": False}

    def build_registry(*args, **kwargs):
        def unused_tool():
            called["unused"] = True
            return _tool_result("unused_tool")

        return {"unused_tool": unused_tool}

    monkeypatch.setattr(api_execution_agent, "_build_tool_registry", build_registry)

    payload = json.loads(
        api_execution_agent.execute_scenarios_core(
            json.dumps(
                {
                    "scenarios": [
                        {
                            "scenario_id": "scenario-2",
                            "scenario_name": "Unknown Tool",
                            "tools": ["not_a_real_tool"],
                        }
                    ],
                    "run_all_registry_tools": False,
                }
            )
        )
    )

    assert payload["metadata"]["requested_tool_count"] == 1
    assert payload["metadata"]["resolved_tool_count"] == 0
    assert payload["metadata"]["unmapped_tool_count"] == 1
    assert "__registry_coverage__" not in payload["results"]
    assert called["unused"] is False


def test_target_url_is_derived_from_scenario_endpoint(monkeypatch):
    observed = {}

    def build_registry(target_url, *args, **kwargs):
        observed["target_url"] = target_url

        def health_tool():
            return _tool_result("health_tool")

        return {"health_tool": health_tool}

    monkeypatch.setattr(api_execution_agent, "_build_tool_registry", build_registry)

    payload = json.loads(
        api_execution_agent.execute_scenarios_core(
            json.dumps(
                {
                    "scenarios": [
                        {
                            "scenario_id": "scenario-3",
                            "scenario_name": "Derived URL",
                            "endpoints": [
                                {
                                    "method": "GET",
                                    "url": "https://example.com/api/v1/health",
                                    "source": "traffic-inventory",
                                    "expected_behavior": "Returns OK",
                                }
                            ],
                            "tools": ["health_tool"],
                        }
                    ]
                }
            )
        )
    )

    assert observed["target_url"] == "https://example.com/api/v1/health"
    assert payload["metadata"]["target_url"] == "https://example.com/api/v1/health"


def test_missing_tools_are_derived_from_endpoints(monkeypatch):
    called = {"k6": False}

    def build_registry(*args, **kwargs):
        def k6_tool():
            called["k6"] = True
            return _tool_result("k6_perf_scale")

        return {"k6_perf_scale": k6_tool}

    monkeypatch.setattr(api_execution_agent, "_build_tool_registry", build_registry)

    payload = json.loads(
        api_execution_agent.execute_scenarios_core(
            json.dumps(
                {
                    "scenarios": [
                        {
                            "scenario_id": "scenario-6",
                            "scenario_name": "Endpoint Only",
                            "endpoints": [
                                {
                                    "method": "GET",
                                    "url": "https://example.com/api/v1/orders",
                                    "source": "traffic-inventory",
                                    "expected_behavior": "Returns orders",
                                }
                            ],
                        }
                    ],
                    "run_all_registry_tools": False,
                }
            )
        )
    )

    assert payload["metadata"]["requested_tool_count"] == 1
    assert payload["metadata"]["resolved_tool_count"] == 1
    assert called["k6"] is True


def test_environmental_tool_errors_are_simulated(monkeypatch):
    def build_registry(*args, **kwargs):
        def flaky_tool():
            raise RuntimeError("Invalid URL '/': No scheme supplied. Perhaps you meant https:///?")

        return {"flaky_tool": flaky_tool}

    monkeypatch.setattr(api_execution_agent, "_build_tool_registry", build_registry)

    payload = json.loads(
        api_execution_agent.execute_scenarios_core(
            json.dumps(
                {
                    "scenarios": [
                        {
                            "scenario_id": "scenario-4",
                            "scenario_name": "Environmental Fallback",
                            "tools": ["flaky_tool"],
                        }
                    ]
                }
            )
        )
    )

    result = payload["results"]["scenario-4_Environmental Fallback"]["flaky_tool"]
    assert result["mode"] == "SIMULATED"


def test_registry_coverage_can_be_disabled(monkeypatch):
    called = {"coverage": False}

    def build_registry(*args, **kwargs):
        def k6_tool():
            return _tool_result("k6_perf_scale")

        def extra_tool():
            called["coverage"] = True
            return _tool_result("unused_tool")

        return {
            "k6_perf_scale": k6_tool,
            "unused_tool": extra_tool,
        }

    monkeypatch.setattr(api_execution_agent, "_build_tool_registry", build_registry)

    payload = json.loads(
        api_execution_agent.execute_scenarios_core(
            json.dumps(
                {
                    "scenarios": [
                        {
                            "scenario_id": "scenario-5",
                            "scenario_name": "No Coverage",
                            "tools": ["k6"],
                        }
                    ],
                    "run_all_registry_tools": False,
                }
            )
        )
    )

    assert payload["metadata"]["run_all_registry_tools"] is False
    assert "__registry_coverage__" not in payload["results"]
    assert called["coverage"] is False


def test_all_registry_tools_run_inside_each_scenario_when_enabled(monkeypatch):
    called = {"extra": False}

    def build_registry(*args, **kwargs):
        def k6_tool():
            return _tool_result("k6_perf_scale")

        def extra_tool():
            called["extra"] = True
            return _tool_result("unused_tool")

        return {
            "k6_perf_scale": k6_tool,
            "unused_tool": extra_tool,
        }

    monkeypatch.setattr(api_execution_agent, "_build_tool_registry", build_registry)

    payload = json.loads(
        api_execution_agent.execute_scenarios_core(
            json.dumps(
                {
                    "scenarios": [
                        {
                            "scenario_id": "scenario-7",
                            "scenario_name": "Full Coverage",
                            "endpoints": [
                                {
                                    "method": "GET",
                                    "url": "https://example.com/api/v1/orders",
                                    "source": "traffic-inventory",
                                    "expected_behavior": "Returns orders",
                                }
                            ],
                            "tools": ["k6"],
                        }
                    ],
                    "run_all_registry_tools": True,
                }
            )
        )
    )

    scenario = payload["results"]["scenario-7_Full Coverage"]
    assert payload["metadata"]["run_all_registry_tools"] is True
    assert "unused_tool" in scenario
    assert scenario["unused_tool"]["status"] == "PASS"
    assert called["extra"] is True
