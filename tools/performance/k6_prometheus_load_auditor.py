"""
Real k6 load auditor — generates a k6 script from captured traffic and
either runs it (if k6 is installed) or reports a SKIPPED with the
generated script path so the user can run it manually.
"""
from __future__ import annotations
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from core.api.mock_generator import generate_mocks

_K6_VUS = 10
_K6_DURATION = "15s"


def _build_k6_script(mocks: list[dict], target_url: str) -> str:
    base = target_url.rstrip("/")
    safe = [m for m in mocks if m["method"] in {"GET", "HEAD"} and not m["is_templated"]][:20]
    if not safe:
        safe = [{"method": "GET", "path": "/", "is_templated": False}]

    scenarios = "\n".join(
        f'  http.get("{base}{m["path"].split("?")[0]}", params);'
        for m in safe
    )
    return f"""import http from 'k6/http';
import {{ sleep, check }} from 'k6';

export const options = {{
  vus: {_K6_VUS},
  duration: '{_K6_DURATION}',
  thresholds: {{
    http_req_duration: ['p(95)<2000'],
    http_req_failed: ['rate<0.05'],
  }},
}};

export default function () {{
  const params = {{ headers: {{ 'Accept': 'application/json' }}, timeout: '8s' }};
{scenarios}
  sleep(0.5);
}}
"""


def convert_and_run_k6(workspace_root=None, target_url=None):
    print("[PERFORMANCE: k6] Building load test script from captured traffic...")

    mocks = generate_mocks(workspace_root)
    if not target_url:
        return {
            "success": True,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "severity": "INFO",
            "log": f"Generated k6 script from {len(mocks)} captured endpoints — pass target_url to run.",
            "recommendation": "Wire target_url into the tool call to execute the load test.",
        }

    script = _build_k6_script(mocks, target_url)

    # Write script to workspace
    root = Path(workspace_root or ".").resolve()
    script_path = root / "keploy" / "reports" / "k6_load_test.js"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script, encoding="utf-8")

    # Run if k6 is installed
    k6_bin = shutil.which("k6")
    if not k6_bin:
        return {
            "success": True,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "severity": "INFO",
            "log": f"k6 not installed — script written to {script_path}. Install k6 to auto-run.",
            "recommendation": "Install k6 from https://k6.io/docs/getting-started/installation/ and re-run.",
            "script_path": str(script_path),
        }

    try:
        result = subprocess.run(
            [k6_bin, "run", "--summary-trend-stats", "avg,p(95),max", str(script_path)],
            capture_output=True, text=True, timeout=120,
        )
        output = result.stdout + result.stderr
        success = result.returncode == 0
        return {
            "success": success,
            "status": "PASS" if success else "FAIL",
            "mode": "LIVE",
            "severity": "INFO" if success else "HIGH",
            "log": output[-800:] if output else "k6 run complete.",
            "recommendation": "Review p95 latency — target <2s. Increase VUs to find breaking point." if not success else "N/A",
            "script_path": str(script_path),
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "status": "FAIL",
            "mode": "LIVE",
            "severity": "MEDIUM",
            "log": "k6 run timed out after 120s.",
            "recommendation": "Reduce duration or VUs in config.",
        }
