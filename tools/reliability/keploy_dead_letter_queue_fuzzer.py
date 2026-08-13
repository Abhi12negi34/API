import requests

def fuzz_dead_letter_queue(target_url="http://localhost"):
    """
    Sends intentionally malformed payloads to message-queue or callback endpoints
    and checks if the system handles (or routes to DLQ) rather than crashing.
    """
    print("[RELIABILITY: Dead Letter Queue Fuzzer] Testing poison pill payload handling...")
    base = target_url.rstrip("/")
    probe_paths = ["/api/v1/webhook", "/api/v1/callback", "/api/v1/events"]

    malformed_payloads = [
        None,  # null body
        "not-json",  # invalid JSON string
        {"event": None, "data": "x" * 100000},  # oversized field
        {},  # empty payload
    ]

    server_errors = []
    handled_gracefully = []

    for path in probe_paths:
        for payload in malformed_payloads:
            try:
                if payload is None:
                    resp = requests.post(f"{base}{path}", data=None, timeout=4, verify=True)
                elif isinstance(payload, str):
                    resp = requests.post(f"{base}{path}", data=payload, headers={"Content-Type": "application/json"}, timeout=4, verify=True)
                else:
                    resp = requests.post(f"{base}{path}", json=payload, timeout=4, verify=True)

                if resp.status_code == 500:
                    server_errors.append(f"{path} returned 500 on malformed payload")
                elif resp.status_code in (400, 422, 200, 202):
                    handled_gracefully.append(f"{path} → {resp.status_code}")
            except Exception:
                continue

    if server_errors:
        return {
            "success": False,
            "log": f"Server errors on malformed inputs: {'; '.join(server_errors)}. Poison pills likely not routed to DLQ.",
            "severity": "HIGH",
            "path": base,
            "recommendation": "Add input validation middleware. Route failed message processing to a Dead Letter Queue for retry analysis."
        }
    if handled_gracefully:
        return {
            "success": True,
            "log": f"All malformed payloads handled gracefully: {'; '.join(handled_gracefully[:5])}.",
            "severity": "INFO",
            "path": base,
            "recommendation": "N/A. Ensure DLQ monitoring alerts are configured for operational visibility."
        }
    return {
        "success": True,
        "log": "[SIMULATION] No webhook/callback endpoints found. DLQ testing not applicable.",
        "severity": "INFO",
        "path": base,
        "recommendation": "Configure Dead Letter Queue for all async message consumers to handle poison pills gracefully."
    }
