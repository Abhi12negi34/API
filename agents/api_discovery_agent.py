"""
agents/api_discovery_agent.py

Discovers the target API surface from local Keploy discovery artifacts and
returns a structured inventory for downstream API testing.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlparse

import yaml

from crewai_bootstrap import bootstrap_crewai_runtime

bootstrap_crewai_runtime()

from crewai import Agent
from crewai.tools import tool

from core.api.discovery_inventory import build_discovery_inventory, _same_site_host
from llm import default_llm
from tools.runtime_config import CREWAI_VERBOSE

# State set by main.py or by direct tool invocation.
_TARGET_URL: str = ""


def set_discovery_url(url: str) -> None:
    global _TARGET_URL
    _TARGET_URL = url


def _workspace_root() -> Path:
    return Path.cwd().resolve()


def _artifact_directories() -> list[Path]:
    root = _workspace_root()
    return [
        root / "keploy" / "tests" / "keploy",
        root / "keploy" / "traffic",
    ]


def _iter_artifact_files() -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()

    for directory in _artifact_directories():
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

    return sorted(files)


def _load_artifact(path: Path):
    with open(path, "r", encoding="utf-8") as handle:
        if path.suffix.lower() == ".json":
            return json.load(handle)
        return yaml.safe_load(handle)


def _normalize_path(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "/"
    if raw.startswith(("http://", "https://")):
        return raw
    if " " in raw and raw.split(" ", 1)[0].isalpha():
        maybe_path = raw.split(" ", 1)[1]
        if maybe_path.startswith("/"):
            return maybe_path
    return raw if raw.startswith("/") else f"/{raw.lstrip('/')}"


def _normalize_full_url(target_url: str, value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return target_url.rstrip("/") if target_url else ""
    if raw.startswith(("http://", "https://")):
        return raw
    if target_url:
        return f"{target_url.rstrip('/')}{_normalize_path(raw)}"
    return _normalize_path(raw)


def _extract_entry(entry, source_file: str, target_url: str):
    if not isinstance(entry, dict):
        return None

    method = entry.get("method")
    path = entry.get("path") or entry.get("endpoint") or entry.get("url")
    status = entry.get("status") or entry.get("status_code")
    description = entry.get("description") or entry.get("name") or "Discovered API endpoint"

    if not method or not path:
        request = entry.get("request", {})
        response = entry.get("response", {})
        method = method or (request.get("method") if isinstance(request, dict) else None)
        path = path or (
            request.get("path")
            if isinstance(request, dict)
            else None
        ) or (
            request.get("url")
            if isinstance(request, dict)
            else None
        )
        status = status or (
            response.get("status_code")
            if isinstance(response, dict)
            else None
        ) or (
            response.get("status")
            if isinstance(response, dict)
            else None
        )

    if not method or not path:
        return None

    normalized_path = _normalize_path(path)
    full_url = str(entry.get("full_url") or entry.get("url") or "").strip()
    if full_url:
        full_url = _normalize_full_url(target_url, full_url)
    else:
        full_url = _normalize_full_url(target_url, normalized_path)

    return {
        "method": str(method).upper(),
        "path": normalized_path,
        "full_url": full_url,
        "status": int(status) if isinstance(status, int) or str(status).isdigit() else status or 200,
        "description": description,
        "capture_mode": entry.get("capture_mode", "file"),
        "target_url": entry.get("target_url", target_url or "N/A"),
        "source_file": source_file,
    }


def _extract_apis(payload, source_file: str, target_url: str):
    discovered = []

    if not isinstance(payload, dict):
        return discovered

    captured = payload.get("capture_profile", {}).get("captured_requests", [])
    if not captured:
        captured = payload.get("captured_requests", [])

    target_host = urlparse(target_url).netloc.lower() if target_url else ""
    for req in captured:
        if not isinstance(req, dict):
            continue
        resource_type = str(req.get("resource_type", "")).lower()
        if resource_type not in {"xhr", "fetch", "websocket", "ping"}:
            continue
        host = str(req.get("host", "")).lower()
        if target_host and host and not _same_site_host(target_host, host):
            continue
        entry = _extract_entry(req, source_file, target_url)
        if entry:
            discovered.append(entry)

    return discovered


def _extract_traffic_inventory(payload):
    if not isinstance(payload, dict):
        return []

    if isinstance(payload.get("capture_profile"), dict):
        capture_profile = payload["capture_profile"]
        if isinstance(capture_profile.get("captured_requests"), list):
            return capture_profile.get("captured_requests", [])

    if isinstance(payload.get("captured_requests"), list):
        return payload.get("captured_requests", [])

    return []


def _dedupe_apis(apis):
    seen = set()
    deduped = []

    for api in apis:
        key = (
            api.get("method"),
            api.get("path"),
            api.get("full_url"),
            api.get("target_url"),
            api.get("source_file"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(api)

    return deduped


def _load_inventory(target_url: str):
    return build_discovery_inventory(target_url, workspace_root=_workspace_root())


@tool("discover_api_surface")
def discover_api_surface_tool(url: str = "") -> str:
    """
    Load the discovered API surface from local Keploy artifacts and return raw JSON.
    """
    target = url or _TARGET_URL or os.getenv("TARGET_URL", "")

    if not target:
        return "ERROR: No URL provided for API discovery."

    inventory = _load_inventory(target)
    if not inventory["discovered_apis"] and not inventory["traffic_requests"]:
        return f"ERROR: No API discovery artifacts found for {target}."

    return json.dumps(inventory, indent=2)


api_discovery_agent = Agent(
    role="API Surface Discovery and Inventory Agent",
    goal="""
    Build a structured inventory of discovered API endpoints and traffic traces
    for downstream API testing. Return only raw JSON.
    """,
    backstory="""
    You are an expert API discovery analyst. Your job is to load the local
    Keploy discovery artifacts, normalize the discovered endpoints, and return
    the raw inventory with no analysis or commentary.

    RULES:
    1. Call discover_api_surface_tool with the target URL.
    2. Return only the JSON produced by the tool.
    3. Do not invent endpoints, hosts, or traffic entries.
    4. Prefer discovered API inventory and traffic traces from local artifacts.
    5. If the tool returns an error, report it clearly.
    """,
    tools=[discover_api_surface_tool],
    llm=default_llm,
    verbose=CREWAI_VERBOSE,
    allow_delegation=False,
)
