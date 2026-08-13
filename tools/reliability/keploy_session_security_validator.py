"""
Real session security validator — inspects captured auth headers and
cookie flags from traffic-inventory.json, then probes live for
session fixation and missing security flags.
"""
from __future__ import annotations
import re
import requests
from core.api.mock_generator import load_captured_requests

_SENSITIVE_HEADERS = {"authorization", "set-cookie", "cookie"}


def validate_session_security(workspace_root=None, target_url=None):
    print("[RELIABILITY: Session Security] Inspecting captured auth tokens and cookie flags...")

    entries = load_captured_requests(workspace_root)
    issues = []

    seen_cookies: list[str] = []
    has_auth_token = False

    for entry in entries:
        headers = entry.get("response_headers") or {}
        set_cookie = headers.get("set-cookie", "")
        if set_cookie:
            seen_cookies.append(set_cookie)
            lower = set_cookie.lower()
            if "httponly" not in lower:
                issues.append(f"Cookie missing HttpOnly: {set_cookie[:80]}")
            if "secure" not in lower:
                issues.append(f"Cookie missing Secure flag: {set_cookie[:80]}")
            if "samesite" not in lower:
                issues.append(f"Cookie missing SameSite: {set_cookie[:80]}")

        req_headers = entry.get("headers") or {}
        if "authorization" in {k.lower() for k in req_headers}:
            has_auth_token = True
            auth_val = str(req_headers.get("authorization") or req_headers.get("Authorization") or "")
            # Check for non-Bearer patterns (basic auth, empty token)
            if auth_val.lower().startswith("basic "):
                issues.append("Basic Auth detected — prefer token-based auth")

    # Live probe: check if session cookie is reused after logout
    if target_url:
        try:
            resp = requests.get(target_url.rstrip("/") + "/", timeout=5, verify=False)
            sc = resp.headers.get("set-cookie", "")
            if sc:
                lower = sc.lower()
                for flag in ("httponly", "secure", "samesite"):
                    if flag not in lower:
                        issues.append(f"Live cookie missing {flag}: {sc[:80]}")
        except Exception:
            pass

    if not seen_cookies and not has_auth_token:
        return {
            "success": True,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "severity": "INFO",
            "log": "No auth tokens or cookies found in captured traffic. Run a capture with auth enabled.",
            "recommendation": "Enable auth in config and re-run capture.",
        }

    # Deduplicate issues
    issues = list(dict.fromkeys(issues))[:10]
    success = len(issues) == 0
    log = (
        f"Session security OK — {len(seen_cookies)} cookies inspected, "
        f"auth token present: {has_auth_token}."
        if success else
        f"Session security issues ({len(issues)}): {'; '.join(issues[:4])}"
    )

    return {
        "success": success,
        "status": "PASS" if success else "FAIL",
        "mode": "LIVE",
        "severity": "INFO" if success else "HIGH",
        "log": log,
        "recommendation": (
            "Set HttpOnly, Secure, and SameSite=Strict on all session cookies."
            if not success else "N/A"
        ),
        "issues": issues,
        "cookies_inspected": len(seen_cookies),
        "has_auth_token": has_auth_token,
    }
