import requests

def audit_circuit_breaker_resync(target_url="http://localhost"):
    """
    Probes a known health endpoint repeatedly to check for inconsistent states
    (half-open circuit breaker) by detecting intermittent 503s among 200s.
    """
    print("[RELIABILITY: Circuit Breaker Resync Auditor] Detecting circuit breaker stability...")
    base = target_url.rstrip("/")
    probe_path = f"{base}/api/v1/health"

    statuses = []
    for _ in range(10):
        try:
            resp = requests.get(probe_path, timeout=3, verify=True)
            statuses.append(resp.status_code)
        except Exception:
            statuses.append(0)

    errors = [s for s in statuses if s in (503, 502, 0)]
    successes = [s for s in statuses if s == 200]

    if errors and successes:
        return {
            "success": False,
            "log": f"Intermittent responses detected: {statuses}. {len(errors)} errors + {len(successes)} successes suggest circuit breaker in Half-Open state.",
            "severity": "HIGH",
            "path": probe_path,
            "recommendation": "Tune circuit breaker successThreshold to require 3+ consecutive successes before Closed state. Investigate upstream dependency flapping."
        }
    if errors and not successes:
        return {
            "success": False,
            "log": f"All {len(errors)} requests to health endpoint failed: {set(statuses)}. Circuit breaker may be Open.",
            "severity": "CRITICAL",
            "path": probe_path,
            "recommendation": "Investigate upstream service dependencies. Check circuit breaker configuration and fallback strategy."
        }
    return {
        "success": True,
        "log": f"Health endpoint consistently returned 200 across {len(successes)} requests. Circuit breaker appears Closed (stable).",
        "severity": "INFO",
        "path": probe_path,
        "recommendation": "N/A. Configure alerting for circuit breaker state transitions."
    }
