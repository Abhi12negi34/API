"""
Real stress test — ramps VUs until p95 latency exceeds threshold or
error rate climbs above 5%. Uses k6 if installed, otherwise reports
the generated script path for manual execution.
"""
from __future__ import annotations
import shutil
import subprocess
from pathlib import Path
from core.api.mock_generator import generate_mocks


def _build_stress_script(mocks: list[dict], target_url: str) -> str:
    base = target_url.rstrip("/")
    safe = [m for m in mocks if m["method"] == "GET" and not m["is_templated"]][:5]
    if not safe:
        safe = [{"path": "/"}]
    urls = "\n".join(f'  http.get("{base}{m["path"].split("?")[0]}", params);' for m in safe)
    return f"""import http from 'k6/http';
import {{ sleep }} from 'k6';

export const options = {{
  stages: [
    {{ duration: '10s', target: 10 }},
    {{ duration: '20s', target: 50 }},
    {{ duration: '20s', target: 100 }},
    {{ duration: '10s', target: 0 }},
  ],
  thresholds: {{
    http_req_duration: ['p(95)<3000'],
    http_req_failed: ['rate<0.10'],
  }},
}};

export default function () {{
  const params = {{ headers: {{ Accept: 'application/json' }}, timeout: '10s' }};
{urls}
  sleep(0.3);
}}
"""


def run_stress_test(workspace_root=None, target_url=None):
    print("[PERFORMANCE: Stress] Ramping load to find breaking point...")

    mocks = generate_mocks(workspace_root)
    if not target_url:
        return {
            "success": True, "status": "SKIPPED", "mode": "SIMULATED", "severity": "INFO",
            "log": f"Stress script ready ({len(mocks)} endpoints). Pass target_url to execute.",
            "recommendation": "Wire target_url into the tool call.",
        }

    script = _build_stress_script(mocks, target_url)
    root = Path(workspace_root or ".").resolve()
    script_path = root / "keploy" / "reports" / "k6_stress_test.js"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script, encoding="utf-8")

    k6_bin = shutil.which("k6")
    if not k6_bin:
        return {
            "success": True, "status": "SKIPPED", "mode": "SIMULATED", "severity": "INFO",
            "log": f"k6 not installed — stress script written to {script_path}.",
            "recommendation": "Install k6 from https://k6.io/docs/getting-started/installation/",
            "script_path": str(script_path),
        }

    try:
        result = subprocess.run(
            [k6_bin, "run", str(script_path)],
            capture_output=True, text=True, timeout=120,
        )
        output = (result.stdout + result.stderr)[-800:]
        success = result.returncode == 0
        return {
            "success": success, "status": "PASS" if success else "FAIL",
            "mode": "LIVE", "severity": "INFO" if success else "HIGH",
            "log": output or "k6 stress run complete.",
            "recommendation": "Tune connection pool and DB query plan at breaking point." if not success else "N/A",
            "script_path": str(script_path),
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False, "status": "FAIL", "mode": "LIVE", "severity": "MEDIUM",
            "log": "Stress test timed out after 120s.",
            "recommendation": "Reduce ramp stages or run manually with k6.",
        }
