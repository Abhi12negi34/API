"""
capture_utils.py — shared redaction and body-capture logic.

Both playwright_stimulator.py and mitm_capture.py use these helpers
so they produce identical schemas in traffic-inventory.json.
"""
from __future__ import annotations

import json
import os
import re
import time

_MAX_BODY_BYTES = int(os.environ.get("KEPLOY_MAX_BODY_CAPTURE_BYTES", 200_000))

_BODY_CAPTURE_RESOURCE_TYPES = {"xhr", "fetch", "websocket", "document"}

_SENSITIVE_KEY_RE = re.compile(
    r"password|passwd|token|secret|authorization|api.?key|session|cookie|ssn|card.?number|cvv|otp",
    re.IGNORECASE,
)

_SKIP_CAPTURE_MARKERS = ("/@fs/", "/@vite/", "/.vite/", "/node_modules/", "/__vite_ping", "/@react-refresh")


def now_ms() -> float:
    return time.monotonic() * 1000


def should_skip_url(url: str) -> bool:
    """Return True if this URL should be excluded from capture entirely."""
    return any(marker in url for marker in _SKIP_CAPTURE_MARKERS)


def redact_value(v: str) -> str:
    """Keep first+last 2 chars; mask middle."""
    if len(v) <= 4:
        return "***"
    return v[:2] + "*" * (len(v) - 4) + v[-2:]


def redact_json(obj):
    """Recursively redact sensitive keys in a parsed JSON object."""
    if isinstance(obj, dict):
        return {
            k: redact_value(str(v)) if isinstance(v, str) and _SENSITIVE_KEY_RE.search(k) else redact_json(v)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [redact_json(item) for item in obj]
    return obj


def redact_raw_text(text: str) -> str:
    """Redact key=value and key:value patterns in raw text."""
    return re.sub(
        r'(?i)(password|token|secret|api.?key|authorization|session|cookie)["\s:=]+[^\s&"\']+',
        lambda m: m.group(1) + "=***",
        text,
    )


def redact_headers(headers: dict) -> dict:
    redacted = {}
    for k, v in headers.items():
        if _SENSITIVE_KEY_RE.search(k):
            redacted[k] = redact_value(str(v))
        else:
            redacted[k] = v
    return redacted


def redact_post_data_string(raw: str, content_type: str = "") -> str:
    """
    Redact a raw post_data string correctly.
    Parses JSON first to avoid corrupting syntax; falls back to regex for non-JSON.
    """
    if not raw:
        return ""

    is_json = "json" in content_type.lower() or "graphql" in content_type.lower()
    if not is_json:
        stripped = raw.strip()
        is_json = stripped.startswith(("{", "["))

    if is_json:
        try:
            parsed = json.loads(raw)
            redacted = redact_json(parsed)
            return json.dumps(redacted, ensure_ascii=False)
        except Exception:
            pass

    return redact_raw_text(raw)


def capture_body_snapshot(raw: str, content_type: str) -> tuple:
    """
    Returns (body, format, byte_count).
    body  — parsed+redacted dict/list, or redacted string, or None
    format — "json" | "json_truncated" | "text" | "text_truncated" | "empty"
    """
    if not raw:
        return None, "empty", 0

    byte_count = len(raw.encode("utf-8", errors="replace"))

    is_json = "json" in content_type.lower() or "graphql" in content_type.lower()
    if not is_json:
        stripped = raw.strip()
        is_json = stripped.startswith(("{", "["))

    if is_json:
        try:
            parsed = json.loads(raw[:_MAX_BODY_BYTES])
            redacted = redact_json(parsed)
            truncated = byte_count > _MAX_BODY_BYTES
            return redacted, "json_truncated" if truncated else "json", byte_count
        except Exception:
            pass

    if byte_count > _MAX_BODY_BYTES:
        raw = raw[:_MAX_BODY_BYTES]
        return redact_raw_text(raw), "text_truncated", byte_count

    return redact_raw_text(raw), "text", byte_count
