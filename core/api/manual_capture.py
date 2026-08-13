"""
manual_capture.py — Manual browser capture mode.

Opens a headed Chromium window with capture handlers attached. The user
manually navigates the app (login, create orders, delete records, etc.)
while all network traffic is recorded. Press Enter in the terminal to
stop and save.

Usage:
    python main.py <target_url> --manual
"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import yaml

from core.api.capture_utils import (
    should_skip_url,
    redact_headers,
    redact_post_data_string,
    capture_body_snapshot,
    now_ms,
)


def _workspace_root(workspace_root=None):
    return Path(workspace_root or os.getcwd()).resolve()


def _ensure_dirs(root):
    tests_dir = root / "keploy" / "tests" / "keploy"
    traffic_dir = root / "keploy" / "traffic"
    reports_dir = root / "keploy" / "reports"
    for d in (tests_dir, traffic_dir, reports_dir):
        d.mkdir(parents=True, exist_ok=True)
    return tests_dir, traffic_dir, reports_dir


def _normalize_endpoint(value: str) -> str:
    parsed = urlparse(str(value or "").strip())
    if parsed.scheme and parsed.netloc:
        path = parsed.path or "/"
        if parsed.query:
            return f"{path}?{parsed.query}"
        return path
    raw = str(value or "").strip()
    if raw.startswith("/"):
        return raw
    if raw and not raw.startswith(("http://", "https://")):
        return "/" + raw
    return "/"


def run_manual_capture_session(
    target_url: str,
    workspace_root=None,
    slow_mo_ms: int = 100,
    auth_password: str = "",
):
    """
    Opens a browser for manual interaction. Captures all traffic.
    Returns the same capture_profile dict as run_playwright_stimulator.
    """
    from playwright.sync_api import sync_playwright

    root = _workspace_root(workspace_root)
    tests_dir, traffic_dir, reports_dir = _ensure_dirs(root)

    captured: dict[int, dict] = {}
    request_count = [0]
    stop_flag = [False]

    # Counter thread — prints progress every 10 requests
    def _counter_thread():
        last = 0
        while not stop_flag[0]:
            current = request_count[0]
            if current > last and current % 10 == 0:
                print(f"  [MANUAL CAPTURE] {current} requests captured so far...")
                last = current
            time.sleep(1)

    def _scrub_url(url: str) -> str:
        if auth_password and auth_password in url:
            return url.replace(auth_password, "***REDACTED***")
        return url

    print("\n" + "=" * 60)
    print("  MANUAL CAPTURE MODE")
    print("=" * 60)
    print(f"  Target: {target_url}")
    print(f"  A browser window will open. Navigate freely.")
    print(f"  Perform logins, create/update/delete records, etc.")
    print(f"  Press ENTER in this terminal when done to save & exit.")
    print("=" * 60 + "\n")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=False,
            slow_mo=slow_mo_ms,
            args=[
                "--disable-features=AutofillServerCommunication,PasswordManager,AutofillCreditCardFilling",
                "--disable-autofill",
                "--disable-save-password-bubble",
            ],
        )
        context = browser.new_context(
            ignore_https_errors=True,
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.6367.207 Safari/537.36"
            ),
            java_script_enabled=True,
        )

        page = context.new_page()

        # Attach capture handlers
        def on_request(request):
            req_url = request.url or ""
            if should_skip_url(req_url):
                return

            request_id = id(request)
            raw_headers = dict(request.headers or {})
            safe_headers = redact_headers(raw_headers)
            raw_post = request.post_data or ""
            content_type = raw_headers.get("content-type", "")
            req_body, req_body_format, req_body_bytes = capture_body_snapshot(raw_post, content_type)
            clean_url = _scrub_url(req_url)

            captured[request_id] = {
                "method": request.method,
                "url": clean_url,
                "path": _normalize_endpoint(clean_url),
                "host": urlparse(clean_url).netloc,
                "resource_type": request.resource_type,
                "frame_url": request.frame.url if request.frame else None,
                "is_navigation": request.is_navigation_request(),
                "timestamp": datetime.utcnow().isoformat(),
                "timestamp_ms": now_ms(),
                "headers": safe_headers,
                "post_data": redact_post_data_string(raw_post, content_type) if raw_post else "",
                "request_body": req_body,
                "request_body_format": req_body_format,
                "request_body_bytes": req_body_bytes,
                "request_content_type": content_type,
                "capture_source": "manual",
            }
            request_count[0] += 1

        def on_response(response):
            request_id = id(response.request)
            entry = captured.get(request_id)
            if not entry:
                return

            start_ms = entry.get("timestamp_ms")
            response_time_ms = round(now_ms() - start_ms, 1) if start_ms else None

            entry["status"] = response.status
            entry["response_time_ms"] = response_time_ms

            raw_resp_headers = dict(response.headers or {})
            entry["response_headers"] = redact_headers(raw_resp_headers)

            resource_type = entry.get("resource_type", "")
            if resource_type in {"xhr", "fetch", "websocket", "document"}:
                resp_content_type = raw_resp_headers.get("content-type", "")
                try:
                    raw_body = response.text()
                except Exception:
                    raw_body = None

                if raw_body is not None:
                    resp_body, resp_body_format, resp_body_bytes = capture_body_snapshot(raw_body, resp_content_type)
                    entry["response_body"] = resp_body
                    entry["response_body_format"] = resp_body_format
                    entry["response_body_bytes"] = resp_body_bytes
                    entry["response_content_type"] = resp_content_type
                else:
                    entry["response_body"] = None
                    entry["response_body_format"] = "unreadable"
                    entry["response_body_bytes"] = 0
                    entry["response_content_type"] = resp_content_type

        page.on("request", on_request)
        page.on("response", on_response)

        # Auto-dismiss JS dialogs (alert/confirm/prompt) so they don't block or crash
        page.on("dialog", lambda dialog: dialog.dismiss())

        # Handle user closing the browser window
        def on_page_close():
            stop_flag[0] = True

        page.on("close", lambda _=None: on_page_close())

        # Navigate to target
        try:
            page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as exc:
            print(f"[MANUAL CAPTURE] Initial navigation failed: {exc}")

        # Start counter thread
        counter = threading.Thread(target=_counter_thread, daemon=True)
        counter.start()

        # Block until user presses Enter or closes browser
        print("[MANUAL CAPTURE] Browser is open. Navigate and interact freely.")
        print("[MANUAL CAPTURE] Press ENTER here when done...\n")

        try:
            while not stop_flag[0]:
                # Check every 0.5s if stop flag set (browser closed)
                import select
                import sys
                if sys.platform == "win32":
                    import msvcrt
                    if msvcrt.kbhit():
                        msvcrt.getch()  # consume the keypress
                        break
                    time.sleep(0.5)
                else:
                    # Unix: use select on stdin
                    ready, _, _ = select.select([sys.stdin], [], [], 0.5)
                    if ready:
                        sys.stdin.readline()
                        break
        except (KeyboardInterrupt, EOFError):
            pass

        stop_flag[0] = True
        print(f"\n[MANUAL CAPTURE] Stopping. {request_count[0]} total requests captured.")

        # Save session storage state for future reuse
        storage_state_path = reports_dir / "playwright-storage-state.json"
        try:
            context.storage_state(path=str(storage_state_path))
            print(f"[MANUAL CAPTURE] Session state saved -> {storage_state_path}")
        except Exception:
            pass

        # Dismiss any open dialogs and close gracefully
        try:
            page.on("dialog", lambda dialog: dialog.dismiss())
        except Exception:
            pass
        try:
            context.close()
        except Exception:
            pass
        try:
            browser.close()
        except Exception:
            pass

    # Write output
    captured_requests = list(captured.values())

    # Build capture profile
    unique_hosts = sorted({e.get("host", "") for e in captured_requests if e.get("host")})
    unique_endpoints = {(e.get("method"), e.get("path"), e.get("host")) for e in captured_requests}

    capture_profile = {
        "capture_mode": "manual",
        "execution_mode": "LIVE",
        "target_url": target_url,
        "captured_request_count": len(captured_requests),
        "unique_endpoint_count": len(unique_endpoints),
        "unique_hosts": unique_hosts,
        "captured_requests": captured_requests,
        "auth_result": {"attempted": False, "success": True, "mode": "MANUAL", "message": "User performed login manually."},
        "notes": [
            "Manual capture mode — user navigated the browser directly.",
            f"Captured {len(captured_requests)} network request(s).",
        ],
    }

    # Write inventory files
    inventory_payload = {
        "capture_profile": capture_profile,
        "captured_requests": captured_requests,
        "unique_api_count": len(unique_endpoints),
    }

    yaml_path = tests_dir / "traffic-inventory.yaml"
    json_path = traffic_dir / "traffic-inventory.json"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(inventory_payload, f, sort_keys=False)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(inventory_payload, f, indent=2)

    print(f"[MANUAL CAPTURE] Traffic saved -> {json_path}")
    return capture_profile
