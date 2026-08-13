from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse


_URL_PATTERN = re.compile(r"https?://[^\s'\"<>]+")


def _rewrite_url(value: str, target_url: str) -> str:
    target = str(target_url or "").strip().rstrip("/")
    if not target:
        return value

    target_parts = urlparse(target)

    def _replace(match: re.Match) -> str:
        raw_url = match.group(0)
        parsed = urlparse(raw_url)
        if not parsed.netloc:
            return raw_url
        if parsed.netloc == target_parts.netloc:
            return raw_url
        return urlunparse(
            (
                target_parts.scheme or parsed.scheme,
                target_parts.netloc,
                parsed.path or "/",
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )

    return _URL_PATTERN.sub(_replace, value)


def sanitize_report_tree(payload, target_url: str):
    if isinstance(payload, dict):
        return {key: sanitize_report_tree(value, target_url) for key, value in payload.items()}
    if isinstance(payload, list):
        return [sanitize_report_tree(item, target_url) for item in payload]
    if isinstance(payload, str):
        return _rewrite_url(payload, target_url)
    return payload
