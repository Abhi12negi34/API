"""
openapi_spec_builder.py — Phase 3

Builds an OpenAPI 3.0 spec from the mock corpus produced by
build_mock_corpus() in mock_generator.py.

  - paths       : from corpus method + generalized path + inferred schemas
  - components  : deduplicated named schemas from response bodies
  - security    : from auth_pattern detection (Phase 2)
  - shadow flag : endpoints in corpus not found in any existing spec

Validates the output with openapi-spec-validator before writing.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import requests
import yaml

from core.api.mock_generator import build_mock_corpus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _method_lower(method: str) -> str:
    return method.lower()


def _path_to_openapi(gen_path: str) -> str:
    """Convert generalized path /foo/{param}/bar → /foo/{id}/bar for OpenAPI."""
    # Replace positional {param} with named {id0}, {id1} etc.
    counter = [0]
    def _replace(m):
        name = f"id{counter[0]}"
        counter[0] += 1
        return "{" + name + "}"
    return re.sub(r"\{param\}", _replace, gen_path.split("?")[0])


def _extract_path_params(openapi_path: str) -> list[dict]:
    """Return OpenAPI parameter objects for {param} placeholders."""
    names = re.findall(r"\{(\w+)\}", openapi_path)
    return [
        {
            "name": name,
            "in": "path",
            "required": True,
            "schema": {"type": "string"},
        }
        for name in names
    ]


def _schema_name(method: str, path: str) -> str:
    """Derive a PascalCase schema name from method + path."""
    parts = [p for p in path.split("/") if p and not p.startswith("{")]
    label = "".join(p.title() for p in parts[-3:]) or "Resource"
    return f"{method.title()}{label}Response"


def _simplify_schema(schema: dict | None, _depth: int = 0) -> dict:
    """Strip genson internal keys and cap nesting depth at 4 levels."""
    if not isinstance(schema, dict):
        return {"type": "object"}
    if _depth > 4:
        return {"type": "object"}
    cleaned = {}
    for k, v in schema.items():
        if k == "$schema":
            continue
        if k == "properties" and isinstance(v, dict):
            cleaned[k] = {
                pk: _simplify_schema(pv, _depth + 1)
                for pk, pv in v.items()
            }
        elif k == "items" and isinstance(v, dict):
            cleaned[k] = _simplify_schema(v, _depth + 1)
        elif k in ("anyOf", "oneOf", "allOf") and isinstance(v, list):
            cleaned[k] = [_simplify_schema(s, _depth + 1) for s in v]
        else:
            cleaned[k] = v
    return cleaned or {"type": "object"}


def _security_requirement(auth_pattern: str) -> list[dict]:
    if auth_pattern == "bearer":
        return [{"BearerAuth": []}]
    if auth_pattern == "apikey":
        return [{"ApiKeyAuth": []}]
    if auth_pattern == "cookie":
        return [{"CookieAuth": []}]
    return []


def _fetch_existing_spec(target_url: str) -> dict | None:
    """Try to fetch an existing OpenAPI spec from the target."""
    base = target_url.rstrip("/")
    for path in ("/openapi.json", "/swagger.json", "/api-docs",
                 "/api/openapi.json", "/v1/openapi.json"):
        try:
            r = requests.get(base + path, timeout=5, verify=False)
            if r.status_code == 200:
                return r.json()
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# Core builder
# ---------------------------------------------------------------------------

def build_openapi_spec(
    workspace_root=None,
    target_url: str = "",
    title: str = "Discovered API",
    version: str = "1.0.0",
) -> dict:
    """
    Returns an OpenAPI 3.0 dict built from the mock corpus.
    """
    corpus = build_mock_corpus(workspace_root)

    # Fetch existing spec for shadow-endpoint detection
    existing_spec_paths: set[str] = set()
    if target_url:
        existing = _fetch_existing_spec(target_url)
        if existing:
            existing_spec_paths = set((existing.get("paths") or {}).keys())

    # Security schemes
    auth_patterns = {e["auth_pattern"] for e in corpus if e.get("auth_pattern") != "none"}
    security_schemes: dict[str, Any] = {}
    if "bearer" in auth_patterns:
        security_schemes["BearerAuth"] = {
            "type": "http", "scheme": "bearer", "bearerFormat": "JWT"
        }
    if "apikey" in auth_patterns:
        security_schemes["ApiKeyAuth"] = {
            "type": "apiKey", "in": "header", "name": "X-Api-Key"
        }
    if "cookie" in auth_patterns:
        security_schemes["CookieAuth"] = {
            "type": "apiKey", "in": "cookie", "name": "session"
        }

    paths: dict[str, Any] = {}
    named_schemas: dict[str, dict] = {}

    for entry in corpus:
        openapi_path = _path_to_openapi(entry["path"])
        method = _method_lower(entry["method"])
        auth_pattern = entry.get("auth_pattern", "none")
        status_codes_seen = entry.get("status_codes_seen") or [entry["response"]["status"]]
        resp_schema = entry["response"].get("schema")
        req_schema = entry["request"].get("schema")
        is_shadow = (
            bool(existing_spec_paths)
            and openapi_path not in existing_spec_paths
        )

        # Build named schema reference for response
        resp_schema_ref: dict | None = None
        if resp_schema:
            schema_name = _schema_name(entry["method"], entry["path"])
            # Deduplicate: reuse existing schema if identical
            clean = _simplify_schema(resp_schema)
            if schema_name not in named_schemas:
                named_schemas[schema_name] = clean
            resp_schema_ref = {"$ref": f"#/components/schemas/{schema_name}"}

        # Build responses dict
        responses: dict[str, Any] = {}
        for status in status_codes_seen:
            status_str = str(status)
            if resp_schema_ref and status < 400:
                responses[status_str] = {
                    "description": "Success",
                    "content": {
                        entry["response"].get("content_type", "application/json")
                        .split(";")[0].strip()
                        or "application/json": {
                            "schema": resp_schema_ref
                        }
                    },
                }
            else:
                desc = {
                    400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
                    404: "Not Found", 409: "Conflict", 422: "Unprocessable Entity",
                    500: "Internal Server Error", 503: "Service Unavailable",
                }.get(status, "Response")
                responses[status_str] = {"description": desc}

        if not responses:
            responses["200"] = {"description": "Success"}

        # Build operation
        operation: dict[str, Any] = {
            "summary": f"{entry['method']} {entry['path']}",
            "operationId": f"{method}_{'_'.join(p for p in entry['path'].split('/') if p)[:40]}",
            "parameters": _extract_path_params(openapi_path),
            "responses": responses,
            "x-sample-count": entry["sample_count"],
            "x-auth-pattern": auth_pattern,
        }

        if is_shadow:
            operation["x-shadow-endpoint"] = True

        if entry["response"].get("median_latency_ms"):
            operation["x-median-latency-ms"] = entry["response"]["median_latency_ms"]

        sec = _security_requirement(auth_pattern)
        if sec:
            operation["security"] = sec

        # Request body
        if method in ("post", "put", "patch") and req_schema:
            operation["requestBody"] = {
                "required": True,
                "content": {
                    entry["request"].get("content_type", "application/json")
                    .split(";")[0].strip()
                    or "application/json": {
                        "schema": _simplify_schema(req_schema)
                    }
                },
            }

        paths.setdefault(openapi_path, {})[method] = operation

    spec: dict[str, Any] = {
        "openapi": "3.0.3",
        "info": {
            "title": title,
            "version": version,
            "description": (
                f"Auto-generated from {len(corpus)} captured API endpoints. "
                f"Source: Playwright traffic capture."
            ),
        },
        "paths": paths,
    }

    if named_schemas or security_schemes:
        spec["components"] = {}
        if named_schemas:
            spec["components"]["schemas"] = named_schemas
        if security_schemes:
            spec["components"]["securitySchemes"] = security_schemes

    if target_url:
        spec["servers"] = [{"url": target_url, "description": "Captured target"}]

    return spec


# ---------------------------------------------------------------------------
# Validate + write
# ---------------------------------------------------------------------------

def validate_spec(spec: dict) -> list[str]:
    """Returns list of validation error strings (empty = valid)."""
    try:
        from openapi_spec_validator import validate
        validate(spec)
        return []
    except Exception as exc:
        # Return first error message only — full trace is too verbose
        msg = str(exc)
        return [msg[:200]]


def write_spec(spec: dict, workspace_root=None, fmt: str = "both") -> dict[str, str]:
    """
    Write the spec to disk. fmt: "yaml" | "json" | "both".
    Returns dict of {format: path}.
    """
    root = Path(workspace_root or ".").resolve()
    out_dir = root / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    written = {}

    if fmt in ("yaml", "both"):
        yaml_path = out_dir / "api_spec.yaml"
        yaml_path.write_text(
            yaml.dump(spec, sort_keys=False, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
        written["yaml"] = str(yaml_path)

    if fmt in ("json", "both"):
        json_path = out_dir / "api_spec.json"
        json_path.write_text(
            json.dumps(spec, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        written["json"] = str(json_path)

    return written


# ---------------------------------------------------------------------------
# One-shot: build + validate + write
# ---------------------------------------------------------------------------

def generate_api_spec(
    workspace_root=None,
    target_url: str = "",
    title: str = "Discovered API",
) -> dict:
    """
    Full pipeline: corpus → spec → validate → write.
    Returns result dict with spec, paths_count, shadow_count, errors, written_files.
    """
    spec = build_openapi_spec(workspace_root, target_url=target_url, title=title)
    errors = validate_spec(spec)
    paths_count = len(spec.get("paths") or {})
    shadow_count = sum(
        1
        for path_item in (spec.get("paths") or {}).values()
        for op in path_item.values()
        if isinstance(op, dict) and op.get("x-shadow-endpoint")
    )

    written: dict[str, str] = {}
    if not errors:
        written = write_spec(spec, workspace_root)
    else:
        # Write anyway so user can inspect, but mark invalid
        written = write_spec(spec, workspace_root)
        print(f"[SPEC] WARNING: spec has {len(errors)} validation errors — written for inspection.")

    return {
        "spec": spec,
        "paths_count": paths_count,
        "shadow_count": shadow_count,
        "errors": errors,
        "written_files": written,
        "endpoint_count": paths_count,
    }
