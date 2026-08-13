"""
api_doc_generator.py — Phase 5

Generates human-readable API documentation from the OpenAPI spec built
in Phase 3:
  - api_spec.yaml / api_spec.json  (already written by openapi_spec_builder)
  - api_docs.html                  (Redoc static HTML, pure template — no Node.js)
  - Injects a "Discovered API Surface" section into the PDF report

Redoc HTML uses the CDN bundle — no Node.js required.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Redoc static HTML (no Node.js — uses CDN)
# ---------------------------------------------------------------------------

_REDOC_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — API Documentation</title>
  <style>
    body {{ margin: 0; padding: 0; font-family: sans-serif; }}
    #redoc-container {{ height: 100vh; }}
  </style>
</head>
<body>
  <div id="redoc-container"></div>
  <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
  <script>
    Redoc.init({spec_json}, {{
      scrollYOffset: 50,
      hideDownloadButton: false,
      theme: {{
        colors: {{ primary: {{ main: '#0070f3' }} }},
        typography: {{ fontSize: '14px', fontFamily: 'Inter, sans-serif' }}
      }}
    }}, document.getElementById('redoc-container'));
  </script>
</body>
</html>
"""


def generate_redoc_html(spec: dict, workspace_root=None, title: str = "Discovered API") -> str:
    """
    Write api_docs.html to reports/ directory.
    Returns the output path.
    """
    root = Path(workspace_root or ".").resolve()
    out_dir = root / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / "api_docs.html"

    spec_json = json.dumps(spec, indent=2, ensure_ascii=False)
    html = _REDOC_TEMPLATE.format(title=title, spec_json=spec_json)
    html_path.write_text(html, encoding="utf-8")
    return str(html_path)


# ---------------------------------------------------------------------------
# Markdown summary (pure-Python fallback, no external deps)
# ---------------------------------------------------------------------------

def generate_markdown_summary(spec: dict, workspace_root=None) -> str:
    """
    Write api_docs.md — a readable plain-text summary of the API surface.
    Returns the output path.
    """
    root = Path(workspace_root or ".").resolve()
    out_dir = root / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "api_docs.md"

    info = spec.get("info", {})
    title = info.get("title", "Discovered API")
    version = info.get("version", "")
    paths = spec.get("paths") or {}

    lines = [
        f"# {title}",
        f"**Version:** {version}  ",
        f"**Endpoints:** {len(paths)}",
        "",
        "## API Surface",
        "",
    ]

    for path, methods in sorted(paths.items()):
        for method, op in sorted(methods.items()):
            if not isinstance(op, dict):
                continue
            summary = op.get("summary", f"{method.upper()} {path}")
            auth = op.get("x-auth-pattern", "none")
            latency = op.get("x-median-latency-ms")
            samples = op.get("x-sample-count", 0)
            shadow = " ⚠️ *undocumented*" if op.get("x-shadow-endpoint") else ""
            statuses = ", ".join(
                str(s) for s in (op.get("responses") or {}).keys()
            )

            lines.append(f"### `{method.upper()} {path}`{shadow}")
            lines.append(f"- **Auth:** {auth}")
            if latency:
                lines.append(f"- **Latency (median):** {latency}ms")
            lines.append(f"- **Status codes:** {statuses or 'unknown'}")
            lines.append(f"- **Samples captured:** {samples}")
            lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return str(md_path)


# ---------------------------------------------------------------------------
# PDF section injection
# ---------------------------------------------------------------------------

def build_api_surface_section(spec: dict) -> list[dict]:
    """
    Returns a list of row dicts for the PDF generator's API Surface table.
    Each row: {method, path, auth, statuses, latency_ms, shadow}
    """
    rows = []
    for path, methods in sorted((spec.get("paths") or {}).items()):
        for method, op in sorted(methods.items()):
            if not isinstance(op, dict):
                continue
            rows.append({
                "method": method.upper(),
                "path": path,
                "auth": op.get("x-auth-pattern", "none"),
                "statuses": ", ".join(str(s) for s in (op.get("responses") or {}).keys()),
                "latency_ms": op.get("x-median-latency-ms", ""),
                "shadow": "YES" if op.get("x-shadow-endpoint") else "",
                "samples": op.get("x-sample-count", 0),
            })
    return rows


# ---------------------------------------------------------------------------
# One-shot: generate all doc outputs
# ---------------------------------------------------------------------------

def generate_api_docs(workspace_root=None, target_url: str = "") -> dict:
    """
    Full pipeline:
      1. Load spec from reports/api_spec.json (written by openapi_spec_builder)
      2. If missing, build it on the fly
      3. Write Redoc HTML + Markdown summary
      Returns dict with paths to all generated files.
    """
    root = Path(workspace_root or ".").resolve()
    spec_path = root / "reports" / "api_spec.json"

    if spec_path.exists():
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    else:
        # Build spec on the fly
        from core.api.openapi_spec_builder import generate_api_spec
        result = generate_api_spec(workspace_root, target_url=target_url)
        spec = result["spec"]

    title = spec.get("info", {}).get("title", "Discovered API")
    html_path = generate_redoc_html(spec, workspace_root, title=title)
    md_path = generate_markdown_summary(spec, workspace_root)

    paths_count = len(spec.get("paths") or {})
    shadow_count = sum(
        1
        for path_item in (spec.get("paths") or {}).values()
        for op in path_item.values()
        if isinstance(op, dict) and op.get("x-shadow-endpoint")
    )

    print(f"[DOCS] Generated API docs: {paths_count} endpoints, {shadow_count} shadow.")
    print(f"[DOCS] HTML: {html_path}")
    print(f"[DOCS] Markdown: {md_path}")

    return {
        "html": html_path,
        "markdown": md_path,
        "spec_json": str(spec_path) if spec_path.exists() else "",
        "paths_count": paths_count,
        "shadow_count": shadow_count,
    }
