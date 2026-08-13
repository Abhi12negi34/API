"""
Webhook contract tester — scans captured traffic for outbound webhook
patterns and checks they include standard headers (X-Signature, Content-Type).
Falls back to probing known webhook registration endpoints.
"""
from __future__ import annotations
import requests
from core.api.mock_generator import load_captured_requests


_WEBHOOK_PATH_MARKERS = ("webhook", "hook", "callback", "notify", "event", "subscribe")


def test_webhook_contracts(workspace_root=None, target_url=None):
    print("[RELIABILITY: Webhook Contracts] Scanning traffic for webhook patterns...")

    entries = load_captured_requests(workspace_root)
    webhook_entries = [
        e for e in entries
        if any(m in str(e.get("path") or "").lower() for m in _WEBHOOK_PATH_MARKERS)
    ]

    issues = []
    tested = 0

    for entry in webhook_entries[:10]:
        tested += 1
        headers = entry.get("response_headers") or {}
        req_headers = entry.get("headers") or {}
        # Outbound webhooks should include a signature header
        has_sig = any(
            k.lower() in ("x-signature", "x-hub-signature", "x-signature-256", "x-webhook-signature")
            for k in {**headers, **req_headers}
        )
        content_type = str(headers.get("content-type") or req_headers.get("content-type") or "")
        if not has_sig:
            issues.append(f"{entry.get('method','?')} {entry.get('path','?')}: missing signature header")
        if "json" not in content_type.lower() and content_type:
            issues.append(f"{entry.get('path','?')}: non-JSON content-type ({content_type})")

    # Live probe for webhook registration endpoint
    if target_url and not tested:
        base = target_url.rstrip("/")
        for suffix in ("/api/webhooks", "/api/v1/webhooks", "/webhooks"):
            try:
                r = requests.get(base + suffix, timeout=4, verify=False)
                tested += 1
                if r.status_code not in (200, 401, 403, 404):
                    issues.append(f"GET {suffix}: unexpected status {r.status_code}")
                break
            except Exception:
                continue

    if not tested:
        return {
            "success": True,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "severity": "INFO",
            "log": "No webhook endpoints found in captured traffic or live probing.",
            "recommendation": "N/A — skip if app has no webhook surface.",
        }

    success = len(issues) == 0
    return {
        "success": success,
        "status": "PASS" if success else "FAIL",
        "mode": "LIVE",
        "severity": "INFO" if success else "MEDIUM",
        "log": (
            f"Webhook contracts OK — {tested} webhook endpoints checked."
            if success else
            f"Webhook issues ({len(issues)}): {'; '.join(issues[:4])}"
        ),
        "recommendation": (
            "Add HMAC signature headers (X-Signature-256) to all outbound webhook calls."
            if not success else "N/A"
        ),
        "tested": tested,
        "issues": issues,
    }
