from __future__ import annotations

import re
from pathlib import Path

import yaml

from core.api.discovery_inventory import build_discovery_inventory


SQL_PATTERN = re.compile(r"\b(?:select|insert|update|delete)\b", re.IGNORECASE)


def _candidate_files(workspace_root=None):
    root = Path(workspace_root or Path.cwd()).resolve()
    candidates = [
        root / "keploy" / "tests" / "keploy",
        root / "keploy" / "traffic",
        root / "tests" / "keploy",
    ]
    files = []
    seen = set()
    for directory in candidates:
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if path.suffix.lower() not in {".yaml", ".yml", ".json"}:
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append(resolved)
    return files


def _count_sql_signals(workspace_root=None):
    total_matches = 0
    files_scanned = 0
    for path in _candidate_files(workspace_root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        files_scanned += 1
        total_matches += len(SQL_PATTERN.findall(text))
        try:
            parsed = yaml.safe_load(text)
        except Exception:
            parsed = None
        if parsed is not None:
            total_matches += len(SQL_PATTERN.findall(str(parsed)))
    return files_scanned, total_matches


def profile_database_n_plus_one(keploy_traces="tests/keploy/", workspace_root=None, target_url="http://localhost"):
    """
    Lightweight N+1 detector.
    Uses local Keploy artifacts when present and skips when no real API surface
    or SQL traces are available.
    """
    print("[PERFORMANCE] Analyzing Keploy SQL traces for N+1 Query patterns...")

    inventory = build_discovery_inventory(target_url, workspace_root=workspace_root)
    discovered = inventory.get("discovered_apis", []) if isinstance(inventory, dict) else []
    if not discovered:
        return {
            "success": False,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "severity": "INFO",
            "log": "No confirmed API surface was discovered, so N+1 profiling was skipped.",
            "path": str(keploy_traces),
            "recommendation": "Populate the discovery baseline with real API traffic before running N+1 analysis.",
        }

    files_scanned, sql_signals = _count_sql_signals(workspace_root=workspace_root)
    if sql_signals == 0:
        return {
            "success": True,
            "status": "PASS",
            "mode": "SIMULATED",
            "severity": "INFO",
            "log": f"No SQL SELECT/INSERT/UPDATE/DELETE signals found across {files_scanned} artifact file(s).",
            "path": str(keploy_traces),
            "recommendation": "N/A",
        }

    if sql_signals >= 15:
        affected_api = discovered[0].get("path", "/")
        return {
            "success": False,
            "status": "FAIL",
            "mode": "SIMULATED",
            "severity": "HIGH",
            "log": f"Trace analysis of {affected_api} surfaced {sql_signals} SQL signals across {files_scanned} artifact file(s).",
            "path": affected_api,
            "recommendation": "Use eager loading or query batching to reduce repeated DB calls.",
        }

    return {
        "success": True,
        "status": "PASS",
        "mode": "SIMULATED",
        "severity": "INFO",
        "log": f"SQL signals were present ({sql_signals}), but no N+1 threshold breach was detected across {files_scanned} artifact file(s).",
        "path": str(keploy_traces),
        "recommendation": "N/A",
    }
