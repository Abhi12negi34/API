import threading
import requests

def simulate_thread_pool_exhaustion(target_url="http://localhost"):
    """
    Fires 50 concurrent requests and measures how many succeed vs time out,
    to detect thread pool exhaustion under concurrency.
    """
    print("[STABILITY: Thread Pool Exhaustion Simulator] Firing 50 concurrent requests...")
    base = target_url.rstrip("/")
    probe_path = f"{base}/api/v1/health"

    results = {"success": 0, "timeout": 0, "error": 0}
    lock = threading.Lock()

    def fire():
        try:
            resp = requests.get(probe_path, timeout=5, verify=True)
            with lock:
                if resp.status_code == 200:
                    results["success"] += 1
                else:
                    results["error"] += 1
        except requests.exceptions.Timeout:
            with lock:
                results["timeout"] += 1
        except Exception:
            with lock:
                results["error"] += 1

    threads = [threading.Thread(target=fire) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    total = sum(results.values())
    success_rate = round(results["success"] / max(total, 1) * 100, 1)
    timeout_rate = round(results["timeout"] / max(total, 1) * 100, 1)

    if timeout_rate > 20:
        return {
            "success": False,
            "log": f"Thread pool stress (50 concurrent): {results['success']} OK, {results['timeout']} timeout, {results['error']} error. {timeout_rate}% timeout rate suggests thread pool exhaustion.",
            "severity": "CRITICAL",
            "path": probe_path,
            "recommendation": "Increase thread pool size or switch to async/non-blocking I/O (e.g. asyncio, Netty). Profile under load to identify blocking operations."
        }
    return {
        "success": True,
        "log": f"Thread pool stress (50 concurrent): {results['success']} OK ({success_rate}%), {results['timeout']} timeout ({timeout_rate}%), {results['error']} error.",
        "severity": "INFO" if success_rate > 90 else "MEDIUM",
        "path": probe_path,
        "recommendation": "N/A" if success_rate > 90 else "Investigate partial failures under concurrency. Profile thread utilization."
    }
