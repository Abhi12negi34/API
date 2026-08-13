"""
mitm_addon.py — mitmproxy addon that writes captured request/response
pairs as JSONL to a file, using the same schema as playwright_stimulator.

Usage (standalone):
    mitmdump -s core/api/mitm_addon.py --set output_path=capture.jsonl

Or programmatically via mitm_capture.py.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime
from urllib.parse import urlparse

try:
    from mitmproxy import http
except ImportError:
    http = None  # allows syntax-checking without mitmproxy installed

# Import shared utilities
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from core.api.capture_utils import (
    should_skip_url,
    redact_headers,
    redact_post_data_string,
    capture_body_snapshot,
)

_OUTPUT_PATH = os.environ.get("MITM_CAPTURE_OUTPUT", "mitm_capture.jsonl")
_START_TIME = time.monotonic()


class CaptureAddon:
    def __init__(self):
        self.output_path = os.environ.get("MITM_CAPTURE_OUTPUT", _OUTPUT_PATH)
        self.handle = open(self.output_path, "a", encoding="utf-8")

    def response(self, flow: "http.HTTPFlow"):
        url = flow.request.pretty_url
        if should_skip_url(url):
            return

        parsed = urlparse(url)
        req_headers = dict(flow.request.headers)
        resp_headers = dict(flow.response.headers)
        content_type = req_headers.get("content-type", "")
        resp_content_type = resp_headers.get("content-type", "")

        # Request body
        raw_post = ""
        try:
            raw_post = flow.request.get_text() or ""
        except Exception:
            pass

        req_body, req_body_format, req_body_bytes = capture_body_snapshot(raw_post, content_type)

        # Response body
        raw_resp = ""
        try:
            raw_resp = flow.response.get_text() or ""
        except Exception:
            pass

        resp_body, resp_body_format, resp_body_bytes = capture_body_snapshot(raw_resp, resp_content_type)

        # Elapsed time
        elapsed_ms = None
        if flow.response.timestamp_end and flow.request.timestamp_start:
            elapsed_ms = round((flow.response.timestamp_end - flow.request.timestamp_start) * 1000, 1)

        entry = {
            "method": flow.request.method,
            "url": url,
            "path": parsed.path or "/",
            "host": parsed.netloc,
            "resource_type": "fetch",  # mitmproxy can't distinguish xhr/fetch/document
            "frame_url": None,
            "is_navigation": flow.request.method == "GET" and "text/html" in resp_content_type,
            "timestamp": datetime.utcnow().isoformat(),
            "headers": redact_headers(req_headers),
            "post_data": redact_post_data_string(raw_post, content_type) if raw_post else "",
            "request_body": req_body,
            "request_body_format": req_body_format,
            "request_body_bytes": req_body_bytes,
            "request_content_type": content_type,
            "status": flow.response.status_code,
            "response_time_ms": elapsed_ms,
            "response_headers": redact_headers(resp_headers),
            "response_body": resp_body,
            "response_body_format": resp_body_format,
            "response_body_bytes": resp_body_bytes,
            "response_content_type": resp_content_type,
            "capture_source": "mitmproxy",
        }

        self.handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.handle.flush()

    def done(self):
        if self.handle and not self.handle.closed:
            self.handle.close()


addons = [CaptureAddon()]
