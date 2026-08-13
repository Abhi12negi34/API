import json
import os
import platform
from pathlib import Path

import yaml

from core.api.discovery_inventory import build_discovery_inventory


def _workspace_root(workspace_root=None):
    return Path(workspace_root or os.getcwd()).resolve()


def _artifact_root(workspace_root=None):
    return _workspace_root(workspace_root) / "keploy"


def _ensure_directories(root_path):
    tests_dir = root_path / "tests" / "keploy"
    mocks_dir = root_path / "mocks"
    reports_dir = root_path / "reports"
    for directory in (tests_dir, mocks_dir, reports_dir):
        directory.mkdir(parents=True, exist_ok=True)
    return tests_dir, mocks_dir, reports_dir


def _should_use_ebpf():
    forced = os.environ.get("KEPLOY_USE_EBPF", "").strip().lower() in {"1", "true", "yes", "on"}
    return platform.system().lower() == "linux" and forced


def start_keploy_record(target_url=None, workspace_root=None, start_command=None):
    """
    Loads Keploy discovery artifacts from the local workspace and produces a
    discovery baseline from those files instead of a hardcoded in-memory list.

    On Linux, the returned profile advertises the eBPF command path.
    On Windows or when eBPF is not enabled, it transparently falls back to proxy mode.
    """
    root = _artifact_root(workspace_root)
    tests_dir, mocks_dir, reports_dir = _ensure_directories(root)

    use_ebpf = _should_use_ebpf()
    capture_mode = "ebpf" if use_ebpf else "proxy"
    app_command = start_command or os.environ.get("KEPLOY_APP_COMMAND", "python main.py <target-url>")
    command = f'sudo keploy record -c "{app_command}"' if use_ebpf else "keploy record --proxy-mode"

    print(f"[KEPLOY] Starting Keploy capture in {capture_mode.upper()} mode...")
    print(f"[KEPLOY] Capture command: {command}")
    print("[KEPLOY] Loading discovery artifacts from local keploy/ workspace.")

    inventory = build_discovery_inventory(target_url, workspace_root=workspace_root)
    discovered_apis = inventory["discovered_apis"]
    source_files = inventory["inventory_summary"].get("source_files", [])

    capture_profile = {
        "capture_mode": capture_mode,
        "execution_mode": "SIMULATED",
        "command": command,
        "target_url": target_url or "N/A",
        "platform": platform.platform(),
        "root": str(root),
        "notes": [
            "Discovery artifacts are loaded from the local keploy/tests/keploy directory.",
            "Windows-native runs automatically fall back to proxy mode.",
            "Only confirmed API candidates are written to discovery-baseline.yaml.",
        ],
        "discovery_source_files": source_files,
        "discovered_api_count": len(discovered_apis),
        "inventory_summary": inventory["inventory_summary"],
    }

    if inventory["inventory_summary"].get("discovered_api_count", 0) == 0:
        capture_profile["notes"].append(
            "No confirmed API endpoints were discovered; the captured traffic was classified as page routes, static assets, or noise."
        )

    baseline_payload = {
        "capture_profile": capture_profile,
        "discovered_apis": discovered_apis,
    }
    baseline_path = tests_dir / "discovery-baseline.yaml"
    capture_path = root / "capture-profile.json"
    report_seed_path = reports_dir / "capture-profile.json"

    with open(baseline_path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(baseline_payload, handle, sort_keys=False)
    with open(capture_path, "w", encoding="utf-8") as handle:
        json.dump(capture_profile, handle, indent=2)
    with open(report_seed_path, "w", encoding="utf-8") as handle:
        json.dump(capture_profile, handle, indent=2)

    return {
        "capture_mode": capture_mode,
        "execution_mode": "SIMULATED",
        "command": command,
        "artifact_root": str(root),
        "tests_dir": str(tests_dir),
        "mocks_dir": str(mocks_dir),
        "baseline_path": str(baseline_path),
        "generated_files": [str(baseline_path), str(capture_path), str(report_seed_path)],
        "baseline": discovered_apis,
        "discovered_api_count": len(discovered_apis),
        "inventory_summary": inventory["inventory_summary"],
        "notes": capture_profile["notes"],
        "discovery_source_files": source_files,
    }
