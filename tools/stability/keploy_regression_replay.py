"""
Real regression replay — replays safe (GET/HEAD/OPTIONS) requests from
the captured baseline against the live target and diffs:
  - status code
  - response schema (structural key presence, not exact values)
  - latency (flags >3x baseline median)

Authenticates against the target using config credentials before replaying,
so protected endpoints are reached with a valid session.

Skips templated paths (e.g. /api/users/{param}/orders) that need a real
ID to be useful — reports them as skipped rather than guessing.
"""
from __future__ import annotations

import time
from pathlib import Path

import requests as _requests
import yaml

from core.api.mock_generator import generate_mocks, schema_fingerprint


_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _load_auth_config(workspace_root=None) -> dict:
    try:
        root = Path(workspace_root or ".").resolve()
        cfg_path = root / "config" / "config.yaml"
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        return data.get("auth") or {}
    except Exception:
        return {}


def _attempt_live_auth(target_url: str, auth_cfg: dict) -> dict:
    """
    Try to obtain a session by POSTing credentials to the login endpoint.
    Returns a dict of headers to include on subsequent requests.
    """
    email = auth_cfg.get("email") or auth_cfg.get("username") or ""
    password = auth_cfg.get("password") or ""
    if not email or not password:
        return {}

    base = target_url.rstrip("/")

    # Common admin/auth login paths — Medusa v2 first
    login_candidates = [
        (f"{base}/auth/user/emailpass", {"email": email, "password": password}),
        (f"{base}/auth/token", {"email": email, "password": password}),
        (f"{base}/api/auth", {"email": email, "password": password}),
        (f"{base}/api/v1/auth/token", {"email": email, "password": password}),
        (f"{base}/api/token", {"email": email, "password": password}),
        (f"{base}/api/v2/auth/token", {"email": email, "password": password}),
        (f"{base}/admin/auth/token", {"email": email, "password": password}),
    ]

    session = _requests.Session()
    for url, payload in login_candidates:
        try:
            r = session.post(url, json=payload, timeout=10, verify=False)
            if r.status_code in (200, 201):
                try:
                    body = r.json()
                except Exception:
                    continue
                # Medusa v2 / common JWT patterns
                token = (
                    body.get("token")
                    or body.get("access_token")
                    or (body.get("data") or {}).get("token")
                    or (body.get("user") or {}).get("token")
                )
                if token:
                    print(f"[REPLAY] Auth OK via {url} — Bearer token obtained.")
                    return {"Authorization": f"Bearer {token}"}
                # Maybe cookie-based auth worked (session cookies set)
                if session.cookies:
                    print(f"[REPLAY] Auth OK via {url} — session cookies obtained.")
                    return {"Cookie": "; ".join(f"{k}={v}" for k, v in session.cookies.items())}
        except Exception:
            continue

    print("[REPLAY] Could not authenticate — replaying without auth headers.")
    return {}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_keploy_test(workspace_root=None, target_url=None):
    print("[KEPLOY] Starting regression replay against live target...")

    mocks = generate_mocks(workspace_root)
    if not mocks:
        print("[KEPLOY] No captured API traffic found for replay — skipping.")
        return {
            "success": True,
            "status": "SKIPPED",
            "mode": "SKIPPED",
            "severity": "INFO",
            "log": "No captured API traffic available for regression replay. Run a capture first.",
            "recommendation": "Run playwright capture and retry.",
        }

    if not target_url:
        safe = sum(1 for m in mocks if m["method"] in _SAFE_METHODS and not m["is_templated"])
        return {
            "success": True,
            "status": "SKIPPED",
            "mode": "SKIPPED",
            "severity": "INFO",
            "log": f"Baseline has {len(mocks)} endpoints ({safe} replayable). Pass target_url to run live replay.",
            "recommendation": "Wire target_url into the tool call to enable live replay.",
            "baseline_size": len(mocks),
            "replayable": safe,
        }

    # Authenticate first — use origin (scheme+host) not full path
    from urllib.parse import urlparse as _urlparse
    parsed_target = _urlparse(target_url)
    origin = f"{parsed_target.scheme}://{parsed_target.netloc}"

    auth_cfg = _load_auth_config(workspace_root)
    auth_headers = _attempt_live_auth(origin, auth_cfg)

    replayable = [
        m for m in mocks
        if m["method"] in _SAFE_METHODS
        and not m["is_templated"]
        and m["response"].get("content_type", "").startswith("application/json")
    ]
    skipped_templated = len(mocks) - len(replayable)

    total = passed = failed = 0
    diffs = []

    for mock in replayable[:30]:
        url = origin.rstrip("/") + mock["path"].split("?")[0]
        baseline_status = mock["response"]["status"]
        baseline_schema: set[str] = set(mock.get("schema_fingerprint") or [])
        baseline_latency = mock["response"].get("median_latency_ms")

        headers = {"Accept": "application/json", **auth_headers}
        total += 1

        try:
            t0 = time.monotonic()
            resp = _requests.request(
                mock["method"], url,
                headers=headers,
                timeout=8, verify=False, allow_redirects=True,
            )
            elapsed_ms = round((time.monotonic() - t0) * 1000, 1)

            issues = []

            if baseline_status and resp.status_code != baseline_status:
                issues.append(f"status {baseline_status}→{resp.status_code}")

            if baseline_schema:
                try:
                    live_body = resp.json()
                    live_schema = schema_fingerprint(live_body)
                    missing = baseline_schema - live_schema
                    new_keys = live_schema - baseline_schema
                    if missing:
                        issues.append(f"missing_keys: {', '.join(sorted(missing)[:4])}")
                    if new_keys:
                        issues.append(f"new_keys: {', '.join(sorted(new_keys)[:4])}")
                except Exception:
                    pass

            if baseline_latency and elapsed_ms > baseline_latency * 3:
                issues.append(f"latency_regression {baseline_latency:.0f}ms→{elapsed_ms:.0f}ms")

            if issues:
                failed += 1
                diffs.append(f"{mock['method']} {mock['path']}: {'; '.join(issues)}")
            else:
                passed += 1

        except Exception as exc:
            failed += 1
            diffs.append(f"{mock['method']} {mock['path']}: request_failed ({type(exc).__name__})")

    success = failed == 0
    log = (
        f"Regression replay: {total} replayed, {passed} passed, {failed} failed, "
        f"{skipped_templated} skipped (templated paths)."
    )
    if diffs:
        log += " Diffs: " + " | ".join(diffs[:8])

    print(f"[KEPLOY] {log}")
    return {
        "success": success,
        "status": "PASS" if success else "FAIL",
        "mode": "LIVE",
        "severity": "INFO" if success else "HIGH",
        "log": log,
        "recommendation": (
            "Review diffs — schema/status changes indicate breaking API changes."
            if diffs else "N/A"
        ),
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped_templated": skipped_templated,
        "diffs": diffs,
        "auth_used": bool(auth_headers),
    }
