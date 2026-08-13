"""
mitm_capture.py — orchestrator for mitmproxy capture.

Launches mitmdump as a subprocess with the CaptureAddon, manages its
lifecycle, and merges captured JSONL back into the traffic-inventory
schema that everything downstream reads from.

Usage from main.py or playwright_stimulator:
    from core.api.mitm_capture import start_mitm_capture, stop_mitm_capture, load_mitm_results

    result = start_mitm_capture(workspace_root=".", port=8080)
    # ... run the crawl with proxy_url=result["proxy_url"] ...
    captured = stop_mitm_capture(result)
    mitm_requests = load_mitm_results(result["output_path"])
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path


def _find_mitmdump() -> str | None:
    return shutil.which("mitmdump")


def start_mitm_capture(
    workspace_root=None,
    port: int = 8080,
    output_filename: str = "mitm_capture.jsonl",
) -> dict:
    """
    Start mitmdump as a background subprocess.
    Returns a dict with proxy_url, output_path, process handle, and status.
    """
    root = Path(workspace_root or ".").resolve()
    output_path = root / "keploy" / "traffic" / output_filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Clean previous capture
    if output_path.exists():
        output_path.unlink()

    mitmdump_bin = _find_mitmdump()
    if not mitmdump_bin:
        print("[MITM] mitmdump not found — mitmproxy capture disabled.")
        return {
            "running": False,
            "proxy_url": None,
            "output_path": str(output_path),
            "process": None,
            "reason": "mitmdump not installed",
        }

    addon_path = str(Path(__file__).parent / "mitm_addon.py")
    env = {**os.environ, "MITM_CAPTURE_OUTPUT": str(output_path)}

    try:
        proc = subprocess.Popen(
            [
                mitmdump_bin,
                "--listen-port", str(port),
                "--set", "flow_detail=0",
                "--quiet",
                "-s", addon_path,
            ],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Give it a moment to start
        time.sleep(1.5)
        if proc.poll() is not None:
            return {
                "running": False,
                "proxy_url": None,
                "output_path": str(output_path),
                "process": None,
                "reason": f"mitmdump exited immediately (code {proc.returncode})",
            }

        print(f"[MITM] Capture running on port {port} -> {output_path}")
        return {
            "running": True,
            "proxy_url": f"http://127.0.0.1:{port}",
            "output_path": str(output_path),
            "process": proc,
            "port": port,
        }
    except Exception as exc:
        return {
            "running": False,
            "proxy_url": None,
            "output_path": str(output_path),
            "process": None,
            "reason": str(exc),
        }


def stop_mitm_capture(result: dict) -> dict:
    """Stop the mitmdump process and return capture stats."""
    proc = result.get("process")
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    output_path = result.get("output_path", "")
    count = 0
    if output_path and Path(output_path).exists():
        with open(output_path, "r", encoding="utf-8") as f:
            count = sum(1 for _ in f)

    print(f"[MITM] Capture stopped. {count} requests captured.")
    return {"stopped": True, "captured_count": count, "output_path": output_path}


def load_mitm_results(output_path: str) -> list[dict]:
    """Load JSONL capture file into a list of dicts."""
    path = Path(output_path)
    if not path.exists():
        return []
    results = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                results.append(json.loads(line))
            except Exception:
                continue
    return results


def merge_captured_requests(playwright_requests: list[dict], mitm_requests: list[dict]) -> list[dict]:
    """
    Merge and deduplicate requests from both capture sources.
    Deduplicates by (method, url) — prefers Playwright entries (richer metadata).
    """
    seen = set()
    merged = []

    for entry in playwright_requests:
        key = (entry.get("method", ""), entry.get("url", ""))
        if key in seen:
            continue
        seen.add(key)
        entry.setdefault("capture_source", "playwright")
        merged.append(entry)

    for entry in mitm_requests:
        key = (entry.get("method", ""), entry.get("url", ""))
        if key in seen:
            continue
        seen.add(key)
        entry.setdefault("capture_source", "mitmproxy")
        merged.append(entry)

    return merged
