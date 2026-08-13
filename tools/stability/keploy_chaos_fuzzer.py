import copy
import os
from pathlib import Path

try:
    from ruamel.yaml import YAML  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    YAML = None

import yaml


def _workspace_root(workspace_root=None):
    return Path(workspace_root or os.getcwd()).resolve()


def _yaml_load(path):
    with open(path, "r", encoding="utf-8") as handle:
        if YAML is not None:
            parser = YAML()
            return parser.load(handle)
        return yaml.safe_load(handle)


def _yaml_dump(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        if YAML is not None:
            dumper = YAML()
            dumper.default_flow_style = False
            dumper.sort_base_mapping_type_on_output = False
            dumper.dump(payload, handle)
        else:
            yaml.safe_dump(payload, handle, sort_keys=False)


def _iter_mock_files(base_path):
    if base_path.is_file():
        return [base_path]
    if base_path.is_dir():
        files = list(base_path.rglob("*.yaml")) + list(base_path.rglob("*.yml"))
        return sorted({path.resolve() for path in files})
    return []


def _mutate_response_block(response, scenario):
    mutated = copy.deepcopy(response) if isinstance(response, dict) else {"body": response}
    mutations = []

    if scenario in {"mixed", "fault", "status"}:
        mutated["status_code"] = 503
        mutated["status"] = 503
        mutations.append("status_code=503")

    if scenario in {"mixed", "latency"}:
        mutated["delay_ms"] = 750
        mutated["delay"] = "750ms"
        mutations.append("delay=750ms")

    if scenario in {"mixed", "corruption"}:
        mutated["body"] = "{\"invalid_json\": true"
        mutations.append("corrupted_json_body")

    return mutated, mutations


def inject_chaos(mock_path="keploy/mocks", output_path=None, scenario="mixed", workspace_root=None):
    """
    Mutates Keploy mock responses to exercise fault, latency, and corruption paths.
    """
    root = _workspace_root(workspace_root)
    base_path = Path(mock_path)
    if not base_path.is_absolute():
        base_path = (root / base_path).resolve()

    mock_files = _iter_mock_files(base_path)
    if not mock_files:
        return {
            "success": True,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "severity": "INFO",
            "log": f"No Keploy mock files found under {base_path}. Chaos fuzzing was skipped instead of inventing sample mocks.",
            "path": str(base_path),
            "recommendation": "Provide recorded Keploy mocks first, then rerun chaos fuzzing.",
        }

    mutated_files = []
    applied_mutations = []
    for file_path in mock_files:
        try:
            payload = _yaml_load(file_path)
        except Exception:
            payload = {"mocks": []}

        mutated_payload = copy.deepcopy(payload)
        file_mutations = []

        if isinstance(mutated_payload, dict):
            for key in ("mocks", "responses", "items"):
                entries = mutated_payload.get(key)
                if isinstance(entries, list):
                    for entry in entries:
                        response_key = "response" if isinstance(entry, dict) and "response" in entry else None
                        if response_key:
                            mutated_response, mutations = _mutate_response_block(entry.get(response_key), scenario)
                            entry[response_key] = mutated_response
                            file_mutations.extend(mutations)
                        elif isinstance(entry, dict):
                            mutated_response, mutations = _mutate_response_block(entry, scenario)
                            entry.update(mutated_response)
                            file_mutations.extend(mutations)
        else:
            mutated_payload, file_mutations = _mutate_response_block(mutated_payload, scenario)

        mutated_dir = root / "keploy" / "chaos"
        mutated_dir.mkdir(parents=True, exist_ok=True)
        target_file = Path(output_path) if output_path else mutated_dir / f"{file_path.stem}.chaos.yaml"
        if not target_file.is_absolute():
            target_file = (root / target_file).resolve()

        _yaml_dump(target_file, mutated_payload)
        mutated_files.append(str(target_file))
        applied_mutations.extend(file_mutations or ["no-op mutation"])

    success = bool(mutated_files)
    severity = "HIGH" if success else "MEDIUM"
    mode = "LIVE" if mock_files and base_path.exists() else "SIMULATED"
    return {
        "success": success,
        "status": "PASS" if success else "FAIL",
        "mode": mode,
        "severity": severity,
        "path": mutated_files[0] if mutated_files else str(base_path),
        "log": f"Chaos fuzzed {len(mutated_files)} mock file(s) using scenario '{scenario}': {', '.join(sorted(set(applied_mutations)))}.",
        "recommendation": "N/A" if success else "Create Keploy mocks so chaos mutations can be applied.",
        "mutated_files": mutated_files,
        "mutations_applied": sorted(set(applied_mutations)),
        "scenario": scenario,
    }
