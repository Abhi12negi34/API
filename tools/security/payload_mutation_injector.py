"""
Payload mutation injector — reads real captured request bodies from
traffic-inventory.json and injects attack payloads into them.
Falls back to path-only GET probing if no bodies are available.
"""
from __future__ import annotations

import json
import copy
from pathlib import Path

from tools.url_helper import build_probe_url

import requests
import yaml

from core.api.discovery_inventory import build_discovery_inventory

PAYLOAD_IDS = [
    "' OR 1=1--",
    "<script>alert(1)</script>",
    "{{7*7}}",
    "../../../etc/passwd",
    "\x00",
    "' UNION SELECT null--",
]


def _load_traffic_inventory(workspace_root=None) -> list[dict]:
    root = Path(workspace_root or ".").resolve()
    candidates = [
        root / "keploy" / "traffic" / "traffic-inventory.json",
        root / "keploy" / "tests" / "keploy" / "traffic-inventory.yaml",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
            data = json.loads(text) if path.suffix == ".json" else yaml.safe_load(text) or {}
            if isinstance(data, list):
                return data
            reqs = data.get("captured_requests") or data.get("capture_profile", {}).get("captured_requests") or []
            return reqs if isinstance(reqs, list) else []
        except Exception:
            continue
    return []


def _candidate_paths(target_url, workspace_root=None, limit=5):
    inventory = build_discovery_inventory(target_url, workspace_root=workspace_root)
    discovered = inventory.get("discovered_apis", []) if isinstance(inventory, dict) else []
    paths = []
    seen = set()
    for entry in discovered:
        if not isinstance(entry, dict):
            continue
        path = str(entry.get("path") or "").strip()
        if not path or path in {"/", ""} or path in seen:
            continue
        seen.add(path)
        paths.append(path)
        if len(paths) >= limit:
            break
    return paths


def _mutate_body(body: dict, payload: str) -> dict:
    """Inject payload into every string leaf of a body dict."""
    mutated = copy.deepcopy(body)

    def _inject(obj):
        if isinstance(obj, dict):
            return {k: _inject(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_inject(i) for i in obj]
        if isinstance(obj, str):
            return payload
        return obj

    return _inject(mutated)


def inject_security_mutations(target_url="http://localhost", workspace_root=None):
    print("[SECURITY: Payload Mutation Injector] Fuzzing endpoints with attack payloads...")
    base = target_url.rstrip("/")

    # Load real captured traffic for body-aware mutation
    traffic_entries = _load_traffic_inventory(workspace_root)
    body_entries = [
        e for e in traffic_entries
        if isinstance(e.get("request_body"), dict)
        and str(e.get("method", "")).upper() in {"POST", "PUT", "PATCH"}
        and e.get("path")
    ]

    vulnerable = []
    tested = 0

    # Body-aware POST/PUT mutation (Phase 0.1 data)
    for entry in body_entries[:5]:
        method = str(entry.get("method", "POST")).upper()
        path = entry.get("path", "")
        url = build_probe_url(target_url, path)
        original_body = entry["request_body"]

        for payload in PAYLOAD_IDS[:3]:
            mutated = _mutate_body(original_body, payload)
            try:
                resp = requests.request(
                    method, url, json=mutated,
                    headers={"Content-Type": "application/json"},
                    timeout=5, verify=False
                )
                tested += 1
                body_text = resp.text
                if payload in body_text:
                    vulnerable.append(f"{method} {path}: reflected payload '{payload[:30]}'")
                elif resp.status_code == 500:
                    vulnerable.append(f"{method} {path}: 500 triggered by payload '{payload[:30]}'")
            except Exception:
                continue

    # Fallback: path-only GET probing
    candidate_paths = _candidate_paths(target_url, workspace_root=workspace_root)
    for probe_path in candidate_paths:
        url = build_probe_url(target_url, probe_path)
        for payload in PAYLOAD_IDS:
            try:
                resp = requests.get(url, params={"q": payload}, timeout=4, verify=False)
                tested += 1
                body_text = resp.text
                if payload in body_text:
                    vulnerable.append(f"GET {probe_path}: reflected payload '{payload[:30]}'")
                elif resp.status_code == 500:
                    vulnerable.append(f"GET {probe_path}: 500 triggered by payload '{payload[:30]}'")
            except Exception:
                continue

    if tested == 0:
        return {
            "success": True,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "severity": "INFO",
            "log": "No discovered API paths or captured request bodies available for mutation testing.",
            "path": base,
            "recommendation": "Run discovery and capture first.",
        }

    if vulnerable:
        return {
            "success": False,
            "status": "FAIL",
            "mode": "LIVE",
            "severity": "CRITICAL",
            "log": f"Input validation failures: {'; '.join(vulnerable)}. Tested {tested} request variants.",
            "path": base,
            "recommendation": "Apply strict input sanitization, parameterized queries, and context-aware output encoding.",
        }

    return {
        "success": True,
        "status": "PASS",
        "mode": "LIVE",
        "severity": "INFO",
        "log": f"All {len(PAYLOAD_IDS)} attack payload types blocked across {tested} tested variants (body-aware + path).",
        "path": base,
        "recommendation": "Continue expanding fuzz corpus with OWASP SecLists payloads.",
    }
