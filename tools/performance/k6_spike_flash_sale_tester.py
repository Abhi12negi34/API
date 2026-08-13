"""
Real spike test — fires a sudden burst of traffic then checks recovery.
Uses k6 if installed, otherwise writes the script for manual execution.
"""
from __future__ import annotations
import shutil
import subprocess
from pathlib import Path
from core.api.mock_generator import generate_mocks


def _build_spike_script(mocks: list[dict], target_url: str) -> str:
    base = target_url.rstrip("/")
    safe = [m for m in mocks if m["method"] == "GET" and not m["is_templated"]][:5]
    if not safe:
        safe = [{"path": "/"}]
    urls = "\n".join(f'  http.get("{base}{m["path"].split("?")[0]}", params);' for m in safe)
    return f"""import http from 'k6/http';
import {{ sleep }} from 'k6';

export const options = {{
  stages: [
    {{ duration: '5s',  target: 5   }},
    {{ duration: '5s',  target: 200 }},
    {{ duration: '5s',  target: 5   }},
    {{ duration: '10s', target: 5   }},
  ],
  thresholds: {{
    http_req_duration: ['p(95)<5000'],
    http_req_failed: ['rate<0.15'],
  }},
}};

export default function () {{
  const params = {{ headers: {{ Accept: 'application/json' }}, timeout: '10s' }};
{urls}
  sleep(0.1);
}}
"""


def run_spike_test(workspace_root=None, target_url=None):
    print("[PERFORMANCE: Spike] Injecting traffic spike to test recovery...")

    mocks = generate_mocks(workspace_root)
    if not target_url:
        return {
            "success": True, "status": "SKIPPED", "mode": "SIMULATED", "severity": "INFO",
            "log": f"Spike script ready ({len(mocks)} endpoints). Pass target_url to execute.",
            "recommendation": "Wire target_url into the tool call.",
        }

    script = _build_spike_script(mocks, target_url)
    root = Path(workspace_root or ".").resolve()
    script_path = root / "keploy" / "reports" / "k6_spike_test.js"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script, encoding="utf-8")

    k6_bin = shutil.which("k6")
    if not k6_bin:
        return {
            "success": True, "status": "SKIPPED", "mode": "SIMULATED", "severity": "INFO",
            "log": f"k6 not installed — spike script written to {script_path}.",
            "recommendation": "Install k6 and re-run.",
            "script_path": str(script_path),
        }

    try:
        result = subprocess.run(
            [k6_bin, "run", str(script_path)],
            capture_output=True, text=True, timeout=90,
        )
        output = (result.stdout + result.stderr)[-800:]
        success = result.returncode == 0
        return {
            "success": success, "status": "PASS" if success else "FAIL",
            "mode": "LIVE", "severity": "INFO" if success else "HIGH",
            "log": output or "k6 spike run complete.",
            "recommendation": "Add autoscaling or circuit breaker to absorb spikes." if not success else "N/A",
            "script_path": str(script_path),
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False, "status": "FAIL", "mode": "LIVE", "severity": "MEDIUM",
            "log": "Spike test timed out.",
            "recommendation": "Run manually: k6 run keploy/reports/k6_spike_test.js",
        }
