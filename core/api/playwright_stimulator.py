from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from collections import deque
from urllib.parse import urljoin, urlparse

import yaml

from core.api.discovery_inventory import build_discovery_inventory, _same_site_host


def _workspace_root(workspace_root=None):
    return Path(workspace_root or os.getcwd()).resolve()


# ---------------------------------------------------------------------------
# Phase 0.1 — full request/response body capture helpers
# ---------------------------------------------------------------------------

import re as _re
import time as _time

_MAX_BODY_BYTES = int(os.environ.get("KEPLOY_MAX_BODY_CAPTURE_BYTES", 200_000))

_BODY_CAPTURE_RESOURCE_TYPES = {"xhr", "fetch", "websocket", "document"}

_SENSITIVE_KEY_RE = _re.compile(
    r"password|passwd|token|secret|authorization|api.?key|session|cookie|ssn|card.?number|cvv|otp",
    _re.IGNORECASE,
)


def _now_ms() -> float:
    return _time.monotonic() * 1000


def _redact_value(v: str) -> str:
    """Keep first+last 2 chars so shape is visible; mask middle."""
    if len(v) <= 4:
        return "***"
    return v[:2] + "*" * (len(v) - 4) + v[-2:]


def _redact_json(obj):
    """Recursively redact sensitive keys in a parsed JSON object."""
    if isinstance(obj, dict):
        return {
            k: _redact_value(str(v)) if isinstance(v, str) and _SENSITIVE_KEY_RE.search(k) else _redact_json(v)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_redact_json(item) for item in obj]
    return obj


def _redact_raw_text(text: str) -> str:
    """Redact key=value and key:value patterns in raw text."""
    return _re.sub(
        r'(?i)(password|token|secret|api.?key|authorization|session|cookie)["\s:=]+[^\s&"\']+',
        lambda m: m.group(1) + "=***",
        text,
    )


def _redact_headers(headers: dict) -> dict:
    redacted = {}
    for k, v in headers.items():
        if _SENSITIVE_KEY_RE.search(k):
            redacted[k] = _redact_value(str(v))
        else:
            redacted[k] = v
    return redacted


def _redact_post_data_string(raw: str, content_type: str = "") -> str:
    """
    Redact a raw post_data string correctly.

    If the content looks like JSON (by content-type or leading brace/bracket),
    parse → redact the structure → re-serialize. This guarantees the output
    is always valid JSON and can never produce corrupted syntax like
    "password=***" (which the naive regex produces by matching across the : separator).

    Falls back to regex-based redaction only for non-JSON bodies
    (form-encoded, plain text, etc.).
    """
    if not raw:
        return ""

    is_json = "json" in content_type.lower() or "graphql" in content_type.lower()
    if not is_json:
        stripped = raw.strip()
        is_json = stripped.startswith(("{", "["))

    if is_json:
        try:
            import json as _json
            parsed = _json.loads(raw)
            redacted = _redact_json(parsed)
            return _json.dumps(redacted, ensure_ascii=False)
        except Exception:
            pass  # fall through to regex redaction below

    # Non-JSON: form-encoded or plain text — regex is safe here
    return _redact_raw_text(raw)


def _capture_body_snapshot(raw: str, content_type: str) -> tuple:
    """
    Returns (body, format, byte_count).
    body  — parsed+redacted dict/list, or redacted string, or None if omitted
    format — "json" | "json_truncated" | "text" | "text_truncated" | "omitted"
    """
    if not raw:
        return None, "empty", 0

    byte_count = len(raw.encode("utf-8", errors="replace"))

    is_json = "json" in content_type.lower() or "graphql" in content_type.lower()
    if not is_json:
        # Try to auto-detect
        stripped = raw.strip()
        is_json = stripped.startswith(("{", "["))

    if is_json:
        try:
            import json as _json
            parsed = _json.loads(raw[:_MAX_BODY_BYTES])
            redacted = _redact_json(parsed)
            truncated = byte_count > _MAX_BODY_BYTES
            return redacted, "json_truncated" if truncated else "json", byte_count
        except Exception:
            pass

    # Plain text — cap and redact
    if byte_count > _MAX_BODY_BYTES:
        raw = raw[:_MAX_BODY_BYTES]
        return _redact_raw_text(raw), "text_truncated", byte_count

    return _redact_raw_text(raw), "text", byte_count



def _artifact_root(workspace_root=None):
    return _workspace_root(workspace_root) / "keploy"


def _ensure_dirs(root):
    tests_dir = root / "tests" / "keploy"
    traffic_dir = root / "traffic"
    reports_dir = root / "reports"
    for directory in (tests_dir, traffic_dir, reports_dir):
        directory.mkdir(parents=True, exist_ok=True)
    return tests_dir, traffic_dir, reports_dir


def _coerce_str(value, default=""):
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _looks_like_env_name(value: str) -> bool:
    value = _coerce_str(value)
    if not value:
        return False
    if any(ch in value for ch in ("@", " ", "\t", "\n", "\r", ":", "/", "\\", ".")):
        return False
    return value.upper() == value and value.replace("_", "").isalnum() and value[0].isalpha()


def _resolve_env_or_literal(value: str, env_name: str) -> str:
    value = _coerce_str(value)
    if not value:
        return ""

    env_value = _coerce_str(os.getenv(value))
    if env_value:
        return env_value

    if _looks_like_env_name(value):
        env_value = _coerce_str(os.getenv(env_name))
        if env_value:
            return env_value
        return ""

    return value


def _resolve_auth_settings(auth_config=None, workspace_root=None):
    auth_config = auth_config if isinstance(auth_config, dict) else {}
    root = _artifact_root(workspace_root)
    default_storage_state = root / "reports" / "playwright-storage-state.json"

    def _bool(key, default=False):
        return _coerce_bool(auth_config.get(key), default=default)

    def _text(key, default=""):
        return _coerce_str(auth_config.get(key), default=default)

    storage_state_path = _text("storage_state_path", str(default_storage_state))
    storage_state_path = Path(storage_state_path)
    if not storage_state_path.is_absolute():
        storage_state_path = (root / storage_state_path).resolve()

    return {
        "enabled": _bool("enabled", False),
        "login_url": _text("login_url"),
        "username_env": _text("username_env", "PLAYWRIGHT_USERNAME"),
        "email_env": _text("email_env", "PLAYWRIGHT_EMAIL"),
        "password_env": _text("password_env", "PLAYWRIGHT_PASSWORD"),
        "username": _text("username"),
        "email": _text("email"),
        "password": _text("password"),
        "success_selector": _text("success_selector"),
        "post_login_url_contains": _text("post_login_url_contains"),
        "manual_login": _bool("manual_login", False),
        "reuse_storage_state": _bool("reuse_storage_state", True),
        "require_auth": _bool("require_auth", False),
        "login_timeout_ms": _coerce_int(auth_config.get("login_timeout_ms"), default=45000),
        "post_login_wait_ms": _coerce_int(auth_config.get("post_login_wait_ms"), default=3000),
        "manual_login_wait_ms": _coerce_int(auth_config.get("manual_login_wait_ms"), default=120000),
        "storage_state_path": storage_state_path,
    }


def _serialize_auth_settings(auth_settings: dict) -> dict:
    serialized = dict(auth_settings or {})
    storage_state_path = serialized.get("storage_state_path")
    if storage_state_path is not None:
        serialized["storage_state_path"] = str(storage_state_path)
    return serialized


def _auth_source_label(auth_settings: dict, value_key: str, env_keys: list[str], fallback_keys: list[str] | None = None) -> str:
    fallback_keys = fallback_keys or []
    if _coerce_str(auth_settings.get(value_key)):
        return f"config.auth.{value_key}"
    for env_key in env_keys:
        if _coerce_str(os.getenv(env_key)):
            return f"env:{env_key}"
    for fallback_key in fallback_keys:
        if _coerce_str(auth_settings.get(fallback_key)):
            return f"config.auth.{fallback_key}"
        if fallback_key == "email" and _coerce_str(os.getenv("PLAYWRIGHT_EMAIL")):
            return "env:PLAYWRIGHT_EMAIL"
    return "not provided"


def _print_auth_banner(auth_settings: dict):
    auth_enabled = bool(auth_settings.get("enabled"))
    reuse_storage = bool(auth_settings.get("reuse_storage_state"))
    storage_state_path = auth_settings.get("storage_state_path")
    login_url = _coerce_str(auth_settings.get("login_url"))
    username_source = _auth_source_label(
        auth_settings,
        "username",
        ["PLAYWRIGHT_USERNAME"],
        fallback_keys=["email"],
    )
    password_source = _auth_source_label(
        auth_settings,
        "password",
        ["PLAYWRIGHT_PASSWORD"],
    )

    print("[AUTH] Authentication banner")
    print(f"[AUTH] Enabled: {auth_enabled}")
    print(f"[AUTH] Username source: {username_source}")
    print(f"[AUTH] Password source: {password_source}")
    print(f"[AUTH] Login URL: {login_url if login_url else 'auto-detect on visited pages'}")
    print(f"[AUTH] Session reuse: {'enabled' if reuse_storage else 'disabled'}")
    print(f"[AUTH] Storage state: {storage_state_path}")
    print(f"[AUTH] Require auth: {bool(auth_settings.get('require_auth'))}")
    if not _looks_like_env_name(_coerce_str(auth_settings.get("username_env"), "PLAYWRIGHT_USERNAME")):
        print("[AUTH] Warning: auth.username_env looks like a literal value, not an env var name.")
    if not _looks_like_env_name(_coerce_str(auth_settings.get("email_env"), "PLAYWRIGHT_EMAIL")):
        print("[AUTH] Warning: auth.email_env looks like a literal value, not an env var name.")
    if not _looks_like_env_name(_coerce_str(auth_settings.get("password_env"), "PLAYWRIGHT_PASSWORD")):
        print("[AUTH] Warning: auth.password_env looks like a literal value, not an env var name.")


def _resolve_auth_credentials(auth_settings: dict) -> tuple[str, str]:
    username = _coerce_str(auth_settings.get("username"))
    if not username:
        username = _coerce_str(auth_settings.get("email"))
    password = _coerce_str(auth_settings.get("password"))

    if not username:
        username_env = _coerce_str(auth_settings.get("username_env"), "PLAYWRIGHT_USERNAME")
        username = _resolve_env_or_literal(username_env, "PLAYWRIGHT_USERNAME")
    if not username:
        email_env = _coerce_str(auth_settings.get("email_env"), "PLAYWRIGHT_EMAIL")
        username = _resolve_env_or_literal(email_env, "PLAYWRIGHT_EMAIL")
    if not password:
        password_env = _coerce_str(auth_settings.get("password_env"), "PLAYWRIGHT_PASSWORD")
        password = _resolve_env_or_literal(password_env, "PLAYWRIGHT_PASSWORD")

    return username, password


def _state_file_exists(path: Path) -> bool:
    try:
        return path.exists() and path.is_file()
    except Exception:
        return False


def _login_signals_for_scope(scope):
    try:
        title = _coerce_str(scope.title()).lower()
    except Exception:
        title = ""

    try:
        body_text = _coerce_str(scope.locator("body").inner_text(timeout=1500)).lower()
    except Exception:
        body_text = ""

    try:
        page_url = _coerce_str(scope.url).lower()
    except Exception:
        page_url = ""

    keywords = (
        "login",
        "log in",
        "sign in",
        "signin",
        "authenticate",
        "authentication",
        "account",
        "password",
        "enter password",
        "verify",
        "two-factor",
        "mfa",
    )
    signal_text = " ".join([title, body_text, page_url])
    if any(keyword in signal_text for keyword in keywords):
        return True

    try:
        infos = _collect_login_field_infos(scope)
    except Exception:
        infos = []

    visible_inputs = [info for info in infos if info.get("visible") and info.get("tag") in {"input", "textarea"}]
    visible_buttons = [info for info in infos if info.get("visible") and info.get("tag") == "button"]

    has_password_field = any(info.get("type") == "password" or "password" in " ".join(
        str(info.get(key) or "") for key in ("text", "name", "id", "placeholder", "autocomplete", "role", "type")
    ).lower() for info in visible_inputs)
    if has_password_field:
        return True

    has_username_like_field = any(
        info.get("type") in {"email", "text", "search", ""}
        and any(token in " ".join(str(info.get(key) or "") for key in ("text", "name", "id", "placeholder", "autocomplete", "role", "type")).lower() for token in ("email", "e-mail", "user", "username", "login", "account", "phone", "mobile", "id"))
        for info in visible_inputs
    )
    has_submit_like_button = any(
        any(token in " ".join(str(info.get(key) or "") for key in ("text", "name", "id", "placeholder", "autocomplete", "role", "type")).lower() for token in ("sign in", "log in", "login", "submit", "continue", "next", "enter"))
        or info.get("type") == "submit"
        for info in visible_buttons
    )

    return bool(has_username_like_field and has_submit_like_button)


def _page_login_signals(page):
    if _login_signals_for_scope(page):
        return True

    try:
        for frame in page.frames:
            if frame == page.main_frame:
                continue
            if _login_signals_for_scope(frame):
                return True
    except Exception:
        pass

    return False


def _looks_like_login_url(value) -> bool:
    text = _coerce_str(value).lower()
    if not text:
        return False
    if any(token in text for token in ("/login", "/signin", "/sign-in", "/auth", "/session", "/account/login")):
        return True
    try:
        parsed = urlparse(text)
    except Exception:
        return False
    path = (parsed.path or "").lower()
    return any(token in path for token in ("/login", "/signin", "/sign-in", "/auth", "/session", "/account/login"))


def _iter_login_scopes(page):
    scopes = [(page, "page")]
    try:
        for frame in page.frames:
            if frame == page.main_frame:
                continue
            scopes.append((frame, f"frame:{_coerce_str(frame.url, 'about:blank')}"))
    except Exception:
        pass
    return scopes


def _collect_login_field_infos(page):
    try:
        return page.locator("input, textarea, button").evaluate_all(
            """
            elements => elements.map((el, index) => {
                const textFromLabels = el.labels ? Array.from(el.labels).map(label => label.innerText || label.textContent || '').join(' ') : '';
                const text = [
                    el.getAttribute('aria-label') || '',
                    el.getAttribute('title') || '',
                    el.getAttribute('name') || '',
                    el.id || '',
                    el.getAttribute('placeholder') || '',
                    el.getAttribute('autocomplete') || '',
                    textFromLabels,
                    el.innerText || '',
                    el.textContent || '',
                ].join(' ').trim();

                const rect = el.getBoundingClientRect();
                const visible = !!(rect.width || rect.height || el.offsetParent);

                return {
                    index,
                    tag: (el.tagName || '').toLowerCase(),
                    type: (el.type || '').toLowerCase(),
                    name: (el.getAttribute('name') || '').toLowerCase(),
                    id: (el.id || '').toLowerCase(),
                    placeholder: (el.getAttribute('placeholder') || '').toLowerCase(),
                    autocomplete: (el.getAttribute('autocomplete') || '').toLowerCase(),
                    role: (el.getAttribute('role') || '').toLowerCase(),
                    text: text.toLowerCase(),
                    visible,
                    formIndex: el.form ? Array.from(document.forms).indexOf(el.form) : -1,
                };
            })
            """
        )
    except Exception:
        return []


def _score_login_field(info: dict, kind: str, preferred_form_index: int = -1) -> int:
    if not isinstance(info, dict):
        return -1
    if not info.get("visible"):
        return -1

    text = " ".join(
        str(info.get(key) or "")
        for key in ("text", "name", "id", "placeholder", "autocomplete", "role", "type")
    ).lower()
    score = 0
    if kind in {"email", "password"} and info.get("tag") == "button":
        return -1

    # Fix: disqualify non-fillable input types (radio, checkbox, hidden, file, etc.)
    if kind in {"email", "password"} and info.get("tag") == "input":
        fillable_types = {"", "text", "email", "search", "tel", "password", "username"}
        if info.get("type") not in fillable_types:
            return -1

    if preferred_form_index >= 0 and info.get("formIndex") == preferred_form_index:
        score += 20

    if kind == "password":
        if info.get("type") == "password":
            score += 120
        if "password" in text:
            score += 80
        if "pass" in text:
            score += 20
        if info.get("autocomplete") == "current-password":
            score += 40
    elif kind == "email":
        if info.get("type") == "email":
            score += 120
        if info.get("autocomplete") == "username":
            score += 60
        if any(token in text for token in ("email", "e-mail", "username", "user", "login", "sign in", "signin", "account")):
            score += 50
        if info.get("type") in {"text", "", "search"}:
            score += 10
    elif kind == "submit":
        if info.get("type") == "submit":
            score += 100
        if info.get("tag") == "button":
            score += 20
        if any(token in text for token in ("sign in", "log in", "login", "submit", "continue", "next", "enter")):
            score += 60

    if info.get("tag") == "button" and kind == "submit":
        score += 10

    return score


def _select_best_login_info(infos, kind: str, preferred_form_index: int = -1, allowed_tags=None):
    allowed_tags = {str(tag).lower() for tag in (allowed_tags or [])} if allowed_tags else None
    scored = []
    for info in infos:
        if allowed_tags and str(info.get("tag") or "").lower() not in allowed_tags:
            continue
        score = _score_login_field(info, kind, preferred_form_index=preferred_form_index)
        if score < 0:
            continue
        scored.append((score, info))

    if not scored:
        return None

    scored.sort(key=lambda item: (-item[0], item[1].get("index", 0)))
    return scored[0][1]


def _first_visible_locator(scope, selectors):
    for selector in selectors:
        try:
            locator = scope.locator(selector)
            if locator.count() == 0:
                continue
            candidate = locator.first
            try:
                if not candidate.is_visible(timeout=1000):
                    continue
            except Exception:
                pass
            return candidate
        except Exception:
            continue
    return None


def _first_matching_text_locator(scope, texts, role_name=None):
    for text in texts:
        try:
            if role_name:
                locator = scope.get_by_role(role_name, name=text)
            else:
                locator = scope.get_by_text(text, exact=False)
            if locator.count() == 0:
                continue
            candidate = locator.first
            try:
                if not candidate.is_visible(timeout=1000):
                    continue
            except Exception:
                pass
            return candidate
        except Exception:
            continue
    return None


def _first_visible_accessible_locator(scope, *, labels=None, placeholders=None, selectors=None):
    for label in labels or []:
        try:
            locator = scope.get_by_label(label, exact=False)
            if locator.count() == 0:
                continue
            candidate = locator.first
            try:
                if not candidate.is_visible(timeout=1000):
                    continue
            except Exception:
                pass
            return candidate
        except Exception:
            continue

    for placeholder in placeholders or []:
        try:
            locator = scope.get_by_placeholder(placeholder, exact=False)
            if locator.count() == 0:
                continue
            candidate = locator.first
            try:
                if not candidate.is_visible(timeout=1000):
                    continue
            except Exception:
                pass
            return candidate
        except Exception:
            continue

    return _first_visible_locator(scope, selectors or [])


def _click_common_login_entry(page):
    entry_texts = [
        "Sign in",
        "Log in",
        "Login",
        "Continue with Email",
        "Continue",
        "Use email",
        "Use email instead",
        "Account",
    ]
    href_selectors = [
        "a[href*='login' i]",
        "a[href*='signin' i]",
        "a[href*='sign-in' i]",
        "a[href*='auth' i]",
        "button[href*='login' i]",
        "button[href*='signin' i]",
    ]

    for scope, scope_label in _iter_login_scopes(page):
        candidate = _first_visible_locator(scope, href_selectors)
        if not candidate:
            candidate = _first_matching_text_locator(scope, entry_texts, role_name="link")
        if not candidate:
            candidate = _first_matching_text_locator(scope, entry_texts, role_name="button")
        if not candidate:
            candidate = _first_matching_text_locator(scope, entry_texts)
        if not candidate:
            continue

        try:
            print(f"[AUTH] Trying login entry point in {scope_label}...")
            candidate.click(timeout=5000)
            try:
                page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception:
                pass
            try:
                page.wait_for_timeout(1000)
            except Exception:
                pass
            return True
        except Exception:
            continue

    return False


def _auto_detect_login_locators(page):
    best = None
    for scope, scope_label in _iter_login_scopes(page):
        infos = _collect_login_field_infos(scope)
        if not infos:
            continue

        password_info = _select_best_login_info(infos, "password")
        email_info = _select_best_login_info(
            infos,
            "email",
            preferred_form_index=int(password_info.get("formIndex", -1) or -1) if password_info else -1,
            allowed_tags={"input", "textarea"},
        )
        submit_info = _select_best_login_info(
            infos,
            "submit",
            preferred_form_index=int(password_info.get("formIndex", -1) or -1) if password_info else -1,
            allowed_tags={"input", "textarea", "button"},
        )
        if not submit_info:
            submit_info = _select_best_login_info(infos, "submit", allowed_tags={"input", "textarea", "button"})

        if not email_info and not password_info:
            continue

        score = 0
        if password_info:
            score += 100
        if email_info:
            score += 60
        if submit_info:
            score += 20
        if "frame:" in scope_label:
            score += 10

        candidate = {
            "score": score,
            "scope": scope,
            "scope_label": scope_label,
            "email_info": email_info,
            "password_info": password_info,
            "submit_info": submit_info,
        }
        if best is None or candidate["score"] > best["score"]:
            best = candidate

    if not best:
        best = {}

    scope = best.get("scope")
    email_locator = None
    password_locator = None
    submit_locator = None

    if scope:
        if best.get("email_info"):
            email_locator = scope.locator("input, textarea, button").nth(int(best["email_info"]["index"]))
        if best.get("password_info"):
            password_locator = scope.locator("input, textarea, button").nth(int(best["password_info"]["index"]))
        if best.get("submit_info"):
            submit_locator = scope.locator("input, textarea, button").nth(int(best["submit_info"]["index"]))

        if not email_locator:
            email_locator = _first_visible_accessible_locator(
                scope,
                labels=[
                    "Email",
                    "Email address",
                    "Username",
                    "User name",
                    "Login",
                    "Account",
                    "Phone",
                    "Mobile",
                ],
                placeholders=[
                    "Email",
                    "Email address",
                    "Username",
                    "User name",
                    "Login",
                    "Account",
                    "Phone",
                    "Mobile",
                ],
                selectors=[
                    "input[type='email']",
                    "input[type='text']",
                    "input[autocomplete='username']",
                    "input[placeholder*='email' i]",
                    "input[placeholder*='username' i]",
                    "input[placeholder*='login' i]",
                    "input[placeholder*='account' i]",
                    "input[name*='email' i]",
                    "input[name*='user' i]",
                    "input[id*='email' i]",
                    "input[id*='user' i]",
                    "input[aria-label*='email' i]",
                    "input[aria-label*='username' i]",
                ],
            )
        if not password_locator:
            password_locator = _first_visible_accessible_locator(
                scope,
                labels=[
                    "Password",
                    "Current password",
                    "Passcode",
                    "PIN",
                ],
                placeholders=[
                    "Password",
                    "Current password",
                    "Passcode",
                    "PIN",
                ],
                selectors=[
                    "input[type='password']",
                    "input[autocomplete='current-password']",
                    "input[placeholder*='password' i]",
                    "input[name*='password' i]",
                    "input[id*='password' i]",
                    "input[aria-label*='password' i]",
                ],
            )
        if not submit_locator:
            submit_locator = _first_visible_accessible_locator(
                scope,
                labels=[
                    "Continue",
                    "Sign in",
                    "Log in",
                    "Login",
                    "Next",
                    "Submit",
                ],
                placeholders=[],
                selectors=[
                    "button[type='submit']",
                    "input[type='submit']",
                    "button:has-text('Continue')",
                    "button:has-text('Continue with Email')",
                    "button:has-text('Sign in')",
                    "button:has-text('Log in')",
                    "button:has-text('Login')",
                    "button:has-text('Next')",
                ],
            )
        if not submit_locator:
            submit_locator = _first_matching_text_locator(
                scope,
                ["Continue with Email", "Continue", "Sign in", "Log in", "Login", "Next"],
                role_name="button",
            )

    return email_locator, password_locator, submit_locator


def _attempt_browser_login(page, auth_settings: dict, target_url: str, force: bool = False):
    username, password = _resolve_auth_credentials(auth_settings)
    login_url = _coerce_str(auth_settings.get("login_url"))
    success_selector = _coerce_str(auth_settings.get("success_selector"))
    post_login_url_contains = _coerce_str(auth_settings.get("post_login_url_contains"))
    login_timeout_ms = _coerce_int(auth_settings.get("login_timeout_ms"), default=45000)
    post_login_wait_ms = _coerce_int(auth_settings.get("post_login_wait_ms"), default=3000)
    page_is_login_like = _page_login_signals(page)

    if auth_settings.get("reuse_storage_state") and _state_file_exists(Path(auth_settings["storage_state_path"])) and not force:
        return {
            "attempted": False,
            "success": True,
            "mode": "STORAGE_STATE",
            "message": f"Reusing saved browser session from {auth_settings['storage_state_path']}.",
        }
    if auth_settings.get("reuse_storage_state") and _state_file_exists(Path(auth_settings["storage_state_path"])) and force:
        print(
            f"[AUTH] Ignoring saved browser session at {auth_settings['storage_state_path']} "
            "because a fresh login was requested."
        )

    if not auth_settings.get("enabled") and not (username and password):
        return {
            "attempted": False,
            "success": True,
            "mode": "PUBLIC",
            "message": "Authentication not enabled; continuing with public browsing.",
        }

    if login_url and (force or not page_is_login_like):
        current_url = _coerce_str(page.url)
        if login_url != current_url:
            try:
                page.goto(login_url, wait_until="networkidle", timeout=login_timeout_ms)
            except Exception:
                try:
                    page.goto(login_url, wait_until="domcontentloaded", timeout=login_timeout_ms)
                except Exception:
                    pass

        try:
            page.wait_for_timeout(1000)
        except Exception:
            pass
    entry_clicked = False
    if not page_is_login_like:
        try:
            entry_clicked = _click_common_login_entry(page)
        except Exception:
            entry_clicked = False
        if entry_clicked:
            page_is_login_like = _page_login_signals(page)

    if username and password:
        email_locator, password_locator, submit_locator = _auto_detect_login_locators(page)
        try:
            if not email_locator or not password_locator:
                try:
                    entry_clicked = _click_common_login_entry(page) or entry_clicked
                except Exception:
                    pass
                email_locator, password_locator, submit_locator = _auto_detect_login_locators(page)

            if email_locator and not password_locator:
                email_locator.fill(username)
                if submit_locator:
                    submit_locator.click(timeout=5000)
                else:
                    email_locator.press("Enter")
                try:
                    page.wait_for_load_state("networkidle", timeout=login_timeout_ms)
                except Exception:
                    pass
                try:
                    page.wait_for_timeout(post_login_wait_ms)
                except Exception:
                    pass

                email_locator, password_locator, submit_locator = _auto_detect_login_locators(page)

            if not email_locator or not password_locator:
                return {
                    "attempted": True,
                    "success": False,
                    "mode": "AUTO",
                    "message": "Login fields were not detected after trying common login entry points.",
                }

            email_locator.fill(username)
            password_locator.fill(password)
            if submit_locator:
                submit_locator.click(timeout=5000)
            else:
                password_locator.press("Enter")
            try:
                page.wait_for_load_state("networkidle", timeout=login_timeout_ms)
            except Exception:
                pass
            try:
                page.wait_for_timeout(post_login_wait_ms)
            except Exception:
                pass
        except Exception as exc:
            return {
                "attempted": True,
                "success": False,
                "mode": "AUTO",
                "message": f"Automatic login failed: {exc}",
            }
    elif auth_settings.get("manual_login"):
        try:
            print("[STIMULATOR] Manual login mode enabled. Complete sign-in in the opened browser window.")
            page.wait_for_timeout(login_timeout_ms)
        except Exception:
            pass
    else:
        return {
            "attempted": False,
            "success": False,
            "mode": "SKIPPED",
            "message": "Authentication is enabled but no credentials were provided.",
        }

    authenticated = True
    if success_selector:
        try:
            authenticated = page.locator(success_selector).count() > 0
        except Exception:
            authenticated = authenticated and True
    if post_login_url_contains:
        try:
            authenticated = authenticated and (post_login_url_contains in page.url)
        except Exception:
            pass

    if auth_settings.get("reuse_storage_state"):
        try:
            storage_state_path = Path(auth_settings["storage_state_path"])
            storage_state_path.parent.mkdir(parents=True, exist_ok=True)
            page.context.storage_state(path=str(storage_state_path))
        except Exception as exc:
            return {
                "attempted": True,
                "success": False,
                "mode": "AUTO",
                "message": f"Login succeeded but saving storage state failed: {exc}",
            }

    return {
        "attempted": True,
        "success": bool(authenticated),
        "mode": "AUTO" if username and password else "MANUAL",
        "message": "Authenticated browser session established." if authenticated else "Authentication may not have completed; review the login checks.",
    }


def _ensure_authentication_on_page(page, auth_settings: dict, auth_state: dict, target_url: str):
    if not isinstance(auth_state, dict):
        auth_state = {}

    page_is_login_like = _page_login_signals(page)
    forced_login_page = _looks_like_login_url(target_url) or _looks_like_login_url(page.url) or bool(_coerce_str(auth_settings.get("login_url")))
    should_force_login = forced_login_page or bool(auth_settings.get("manual_login"))

    if auth_state.get("authenticated") and not (page_is_login_like or forced_login_page):
        return {
            "attempted": False,
            "success": True,
            "mode": "AUTHENTICATED",
            "message": "Session already authenticated.",
        }

    if not (page_is_login_like or forced_login_page):
        return {
            "attempted": False,
            "success": bool(auth_state.get("authenticated")),
            "mode": "SKIPPED",
            "message": "Current page does not look like a login page yet.",
        }

    if auth_state.get("last_login_url") == _coerce_str(page.url) and auth_state.get("login_attempts", 0) > 0 and not forced_login_page:
        return {
            "attempted": False,
            "success": bool(auth_state.get("authenticated")),
            "mode": "SKIPPED",
            "message": "Login already attempted on this page.",
        }

    if forced_login_page and not page_is_login_like:
        print(f"[AUTH] Forcing login attempt on {page.url} because the URL looks like a login page.")

    login_result = _attempt_browser_login(page, auth_settings, target_url, force=should_force_login)
    auth_state["login_attempts"] = int(auth_state.get("login_attempts", 0)) + int(bool(login_result.get("attempted")))
    auth_state["last_login_url"] = _coerce_str(page.url)
    if login_result.get("success"):
        auth_state["authenticated"] = True
    auth_state["last_auth_result"] = login_result
    if login_result.get("attempted") or login_result.get("success"):
        print(f"[AUTH] {login_result.get('mode', 'AUTO')}: {login_result.get('message')}")
    return login_result


def _coerce_bool(value, default=False):
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    raw = str(value).strip().lower()
    if not raw:
        return bool(default)
    return raw in {"1", "true", "yes", "on"}


def _coerce_int(value, default=0):
    if value is None:
        return int(default)
    try:
        return int(value)
    except Exception:
        return int(default)


def _normalize_endpoint(value: str) -> str:
    parsed = urlparse(str(value or "").strip())
    # Full URL — extract path (+ query) only
    if parsed.scheme and parsed.netloc:
        path = parsed.path or "/"
        if parsed.query:
            return f"{path}?{parsed.query}"
        return path
    # Already an absolute path
    raw = str(value or "").strip()
    if raw.startswith("/"):
        return raw
    # Relative URL that slipped through (e.g. "web/index.php/api/...") — make absolute
    if raw and not raw.startswith(("http://", "https://")):
        return "/" + raw
    return "/"


def _normalize_host(value: str) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    if raw.startswith(("http://", "https://")):
        raw = urlparse(raw).netloc.lower()
    raw = raw.split("@")[-1].split(":", 1)[0]
    if raw.startswith("www."):
        raw = raw[4:]
    return raw


def _base_domain(host: str) -> str:
    parts = [part for part in str(host or "").split(".") if part]
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return str(host or "").lower()


def _same_site_navigation(base_url: str, candidate: str) -> bool:
    """
    Crawling can be broader than API classification: any same registrable-domain
    subdomain is worth visiting because it may surface hidden fetch/XHR traffic.
    """
    left_host = _normalize_host(base_url)
    right_host = _normalize_host(candidate)
    if not left_host or not right_host:
        return False
    if left_host == right_host:
        return True
    return _base_domain(left_host) == _base_domain(right_host)


def _collect_seeds(page, base_url, max_links=10):
    try:
        hrefs = page.eval_on_selector_all(
            "a[href], area[href], link[href], form[action], [data-href], [data-url]",
            """
            els => els.map(el => {
                if (el.tagName === 'FORM') return el.action || '';
                return el.href || el.dataset.href || el.dataset.url || '';
            }).filter(Boolean)
            """,
        )
    except Exception:
        hrefs = []

    seeds = []
    for href in hrefs:
        if not isinstance(href, str):
            continue
        if _same_site_navigation(base_url, href):
            seeds.append(href)

    unique = []
    seen = set()
    for href in seeds:
        if href in seen:
            continue
        seen.add(href)
        unique.append(href)
        if len(unique) >= max_links:
            break
    return unique


def _collect_interaction_urls(page, base_url, max_clicks=6):
    """
    Click a small number of likely navigation controls to surface lazy-loaded
    requests, client-side route changes, and additional API fetches.
    """
    selectors = [
        "button",
        "[role='button']",
        "input[type='button']",
        "input[type='submit']",
        "[data-href]",
        "[data-url]",
        "[aria-controls]",
    ]

    discovered = []
    seen = set()
    for selector in selectors:
        try:
            locator = page.locator(selector)
            count = locator.count()
        except Exception:
            continue

        for index in range(min(count, max_clicks)):
            try:
                candidate = locator.nth(index)
                if not candidate.is_visible(timeout=1000):
                    continue
                before_url = page.url
                try:
                    candidate.scroll_into_view_if_needed(timeout=1500)
                except Exception:
                    pass
                candidate.click(timeout=2500)
                try:
                    page.wait_for_load_state("networkidle", timeout=2000)
                except Exception:
                    pass
                after_url = page.url
                if after_url != before_url and _same_site_navigation(base_url, after_url) and after_url not in seen:
                    seen.add(after_url)
                    discovered.append(after_url)
            except Exception:
                continue

    return discovered


# FIX 1: Single top-level simulate_user_flows (removed duplicate inside run_playwright_stimulator)
def simulate_user_flows(page):
    try:
        start_url = _coerce_str(page.url)

        # Search simulation
        inputs = page.locator("input[type='text']")
        if inputs.count() > 0:
            try:
                search_box = inputs.first
                search_box.fill("test")
                search_box.press("Enter")
                page.wait_for_timeout(500)
            except Exception:
                pass

        # Scroll to trigger lazy-loaded content
        for _ in range(2):
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(300)

        # Click links (product/category simulation)
        links = page.locator("a[href]")
        for i in range(min(3, links.count())):
            try:
                links.nth(i).click(timeout=2000)
                page.wait_for_timeout(500)
                if start_url:
                    try:
                        page.goto(start_url, wait_until="domcontentloaded", timeout=15000)
                    except Exception:
                        try:
                            page.go_back()
                        except Exception:
                            pass
                else:
                    try:
                        page.go_back()
                    except Exception:
                        pass
                page.wait_for_timeout(300)
            except Exception:
                continue

    except Exception:
        pass


def _navigate_page(page, url: str, timeout_ms: int = 60000) -> bool:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    except Exception as exc:
        print(f"[STIMULATOR] Navigation failed for {url}: {exc}")
        return False

    try:
        page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 5000))
    except Exception:
        pass

    current_url = _coerce_str(page.url).lower()
    if not current_url or current_url == "about:blank":
        print(f"[STIMULATOR] Navigation to {url} did not leave about:blank; skipping deep dive.")
        return False

    return True


def _crawl_pages(page, target_url, max_pages=200, max_links=50, max_clicks=20,
                 stable_page_limit=3, time_budget_s=None, captured_dict=None,
                 on_visit=None, auth_settings=None, auth_state=None):
    """
    Adaptive crawl with:
      - Phase 1: Coverage-plateau stopping (stop after N pages with 0 new requests)
      - Phase 2: Priority queue (score by path depth + nav-text heuristics)
      - Phase 4: Time budget (stop if elapsed > time_budget_s)
    """
    import heapq

    auth_settings = auth_settings if isinstance(auth_settings, dict) else {}
    auth_state = auth_state if isinstance(auth_state, dict) else {}
    visited = set()
    ordered_urls = []
    stable_count = 0
    insertion_order = 0
    start_time = _time.monotonic()

    def _score_seed(url, depth):
        score = 100
        score -= depth * 15
        url_lower = url.lower()
        if any(kw in url_lower for kw in ("admin", "api", "order", "product", "customer", "inventory", "settings", "payout", "payment", "finance", "report", "analytics", "shipping", "discount", "promotion", "campaign")):
            score -= 20
        if any(kw in url_lower for kw in ("login", "signup", "register", "forgot")):
            score += 30
        return score

    initial_score = _score_seed(target_url, 0)
    pq = [(initial_score, 0, target_url, 0)]
    insertion_order = 1

    while pq and len(visited) < max_pages:
        if time_budget_s and (_time.monotonic() - start_time) > time_budget_s:
            print(f"[STIMULATOR] Time budget exhausted ({time_budget_s}s). Stopping crawl.")
            break

        _, _, url, depth = heapq.heappop(pq)
        if url in visited:
            continue
        visited.add(url)
        ordered_urls.append(url)

        requests_before = len(captured_dict) if captured_dict is not None else 0

        try:
            if not _navigate_page(page, url, timeout_ms=60000):
                continue

            # Also mark the actual URL after redirect as visited (avoids duplicates)
            actual_url = _coerce_str(page.url)
            if actual_url and actual_url != url:
                visited.add(actual_url)

            for _ in range(2):
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(500)
            page.wait_for_timeout(1000)

            auth_result = _ensure_authentication_on_page(page, auth_settings, auth_state, target_url)
            auth_state["last_auth_result"] = auth_result
            if auth_result.get("success"):
                auth_state["authenticated"] = True

            if not auth_state.get("authenticated"):
                simulate_user_flows(page)
            else:
                page.wait_for_timeout(500)
            if callable(on_visit):
                try:
                    on_visit(page, url, depth)
                except Exception:
                    pass
        except Exception as exc:
            print(f"[STIMULATOR] Crawl step failed for {url}: {exc}")

        requests_after = len(captured_dict) if captured_dict is not None else 0
        new_requests = requests_after - requests_before
        if new_requests == 0:
            stable_count += 1
        else:
            stable_count = 0

        if stable_count >= stable_page_limit and len(visited) > 2:
            print(f"[STIMULATOR] Coverage plateau: {stable_page_limit} pages with 0 new requests. Stopping.")
            break

        if depth >= 5:
            continue

        for seed in _collect_seeds(page, target_url, max_links=max_links):
            if not _same_site_navigation(target_url, seed) or seed in visited:
                continue
            score = _score_seed(seed, depth + 1)
            heapq.heappush(pq, (score, insertion_order, seed, depth + 1))
            insertion_order += 1

        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.5)")
            page.wait_for_timeout(300)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(300)
        except Exception:
            pass

        for discovered_url in _collect_interaction_urls(page, target_url, max_clicks=max_clicks):
            if discovered_url in visited:
                continue
            score = _score_seed(discovered_url, depth + 1)
            heapq.heappush(pq, (score, insertion_order, discovered_url, depth + 1))
            insertion_order += 1

    elapsed = round(_time.monotonic() - start_time, 1)
    print(f"[STIMULATOR] Crawl complete: {len(visited)} pages in {elapsed}s (plateau_stop={stable_count >= stable_page_limit})")
    return ordered_urls


def _write_inventory_files(tests_dir, traffic_dir, capture_profile, captured_requests):
    inventory_payload = {
        "capture_profile": capture_profile,
        "captured_requests": captured_requests,
        "unique_api_count": len(
            {
                (entry.get("method"), entry.get("path"), entry.get("host"))
                for entry in captured_requests
            }
        ),
    }

    yaml_path = tests_dir / "traffic-inventory.yaml"
    json_path = traffic_dir / "traffic-inventory.json"
    with open(yaml_path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(inventory_payload, handle, sort_keys=False)
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(inventory_payload, handle, indent=2)

    return str(yaml_path), str(json_path)


def _build_api_probe_plan(target_url, workspace_root=None, max_probes=None):
    """
    Reuse local discovery artifacts to generate a same-site API probe plan.
    Phase 3: adaptive budget — scales with discovered endpoints, capped by ceiling.
    """
    try:
        inventory = build_discovery_inventory(target_url, workspace_root=workspace_root)
    except Exception:
        inventory = {}

    discovered_apis = inventory.get("discovered_apis", []) if isinstance(inventory, dict) else []
    base = str(target_url or "").strip().rstrip("/")
    if not base:
        return [], {}

    parsed_base = urlparse(base)
    origin = f"{parsed_base.scheme}://{parsed_base.netloc}"  # http://localhost:9000 — no path!
    target_host = parsed_base.netloc.lower()
    probe_ceiling = int(max_probes or 100)

    real_candidates = []
    inferred_candidates = []
    seen = set()
    for entry in discovered_apis:
        if not isinstance(entry, dict):
            continue

        entry_target = str(entry.get("target_url") or entry.get("full_url") or "").strip()
        if entry_target:
            entry_host = urlparse(entry_target).netloc.lower()
            if entry_host and target_host and not _same_site_host(entry_host, target_host):
                continue

        source = str(entry.get("source_file") or entry.get("capture_mode") or "")
        is_inferred = source in {"pattern-inference", "inferred"}

        path = str(entry.get("path") or "").strip()
        if not path or path in {"/", ""}:
            continue
        if not path.startswith("/"):
            path = f"/{path.lstrip('/')}"

        method = str(entry.get("method") or "GET").upper()
        if method not in {"GET", "HEAD"}:
            method = "GET"

        url = f"{origin}{path}" if path.startswith("/") else f"{origin}/{path}"
        key = (method, url)
        if key in seen:
            continue
        seen.add(key)
        candidate = {
            "method": method,
            "url": url,
            "path": path,
            "source": entry.get("source_file", "discovery"),
            "description": entry.get("description", "Discovered API endpoint"),
        }
        if is_inferred:
            inferred_candidates.append(candidate)
        else:
            real_candidates.append(candidate)

    # Phase 3: adaptive budget — scale with real candidates, cap by ceiling
    total_candidates = len(real_candidates) + len(inferred_candidates)
    if max_probes is None:
        max_probes = min(total_candidates, probe_ceiling)

    plan = real_candidates[:max_probes]
    plan_keys = {(item["method"], item["url"]) for item in plan}
    if len(plan) < max_probes:
        for candidate in inferred_candidates:
            candidate_key = (candidate["method"], candidate["url"])
            if candidate_key in plan_keys:
                continue
            plan.append(candidate)
            plan_keys.add(candidate_key)
            if len(plan) >= max_probes:
                break

    # Phase 3: observability — report why probes were skipped
    probe_metadata = {
        "total_candidates": total_candidates,
        "probes_planned": len(plan),
        "probes_skipped_count": max(0, total_candidates - len(plan)),
    }
    if len(plan) < total_candidates:
        probe_metadata["probing_skipped_reason"] = "probe_ceiling_reached"
    else:
        probe_metadata["probing_skipped_reason"] = None

    return plan, probe_metadata


def _probe_api_endpoints(page, probe_plan, per_probe_wait_ms=500):
    """
    Fire lightweight same-origin fetches so the capture listener records API traffic.
    """
    executed = []
    for probe in probe_plan:
        url = probe.get("url")
        method = str(probe.get("method") or "GET").upper()
        if not url:
            continue

        try:
            result = page.evaluate(
                """
                async ({ url, method }) => {
                    try {
                        const response = await fetch(url, {
                            method,
                            credentials: 'include',
                            headers: {
                                'Accept': 'application/json, text/plain, */*'
                            }
                        });
                        return {
                            ok: true,
                            status: response.status,
                            redirected: response.redirected
                        };
                    } catch (error) {
                        return {
                            ok: false,
                            error: String(error)
                        };
                    }
                }
                """,
                {"url": url, "method": method},
            )
            executed.append({**probe, "result": result})
            page.wait_for_timeout(per_probe_wait_ms)
        except Exception as exc:
            executed.append({**probe, "result": {"ok": False, "error": str(exc)}})

    return executed


def run_playwright_stimulator(
    target_url=None,
    workspace_root=None,
    max_links=None,
    max_pages=None,
    max_clicks=None,
    time_budget_s=None,
    stable_page_limit=None,
    probe_ceiling=None,
    headless=None,
    slow_mo_ms=None,
    capture_trace=None,
    capture_screenshots=None,
    devtools=None,
    aggressive_discovery=None,
    auth_config=None,
):
    headless = _coerce_bool(headless, default=True)
    slow_mo_ms = _coerce_int(slow_mo_ms, default=0)
    capture_trace = _coerce_bool(capture_trace, default=False)
    capture_screenshots = _coerce_bool(capture_screenshots, default=False)
    devtools = _coerce_bool(devtools, default=False)
    aggressive_discovery = _coerce_bool(aggressive_discovery, default=False)
    auth_settings = _resolve_auth_settings(auth_config, workspace_root=workspace_root)
    serialized_auth_settings = _serialize_auth_settings(auth_settings)

    launch_mode = "Headless" if headless else "Headed"
    print(f"[STIMULATOR] Launching {launch_mode} Chromium via Playwright...")
    _print_auth_banner(auth_settings)
    root = _artifact_root(workspace_root)
    tests_dir, traffic_dir, reports_dir = _ensure_dirs(root)

    max_links = int(max_links if max_links is not None else 25)
    max_pages = int(max_pages if max_pages is not None else 50)
    max_clicks = int(max_clicks if max_clicks is not None else 8)

    target = str(target_url or "").strip()
    if not target:
        print("[STIMULATOR] No target URL provided. Skipping browser capture.")
        capture_profile = {
            "capture_mode": "playwright",
            "execution_mode": "SIMULATED",
            "target_url": "N/A",
            "captured_request_count": 0,
            "unique_endpoint_count": 0,
            "unique_hosts": [],
            "traffic_inventory_path": None,
            "traffic_inventory_json_path": None,
            "notes": ["No target URL provided."],
        }
        return capture_profile

    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        print(f"[STIMULATOR] Playwright unavailable: {exc}")
        capture_profile = {
            "capture_mode": "playwright",
            "execution_mode": "SIMULATED",
            "target_url": target,
            "captured_request_count": 0,
            "unique_endpoint_count": 0,
            "unique_hosts": [],
            "traffic_inventory_path": None,
            "traffic_inventory_json_path": None,
            "notes": [f"Playwright unavailable: {exc}"],
        }
        _write_inventory_files(tests_dir, traffic_dir, capture_profile, [])
        return capture_profile

    captured = {}
    crawled_urls = [target]
    page = None
    navigation_log = []
    console_messages = []
    page_errors = []
    screenshot_paths = []
    final_page_title = ""
    trace_path = reports_dir / f"playwright-trace-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.zip"
    auth_state = {
        "authenticated": False,
        "login_attempts": 0,
        "last_login_url": "",
        "last_auth_result": {
            "attempted": False,
            "success": False,
            "mode": "SKIPPED",
            "message": "Authentication not attempted yet.",
        },
    }
    auth_result = auth_state["last_auth_result"]
    try:
        with sync_playwright() as playwright:
            launch_kwargs = {"headless": headless}
            if slow_mo_ms > 0:
                launch_kwargs["slow_mo"] = slow_mo_ms
            if devtools and not headless:
                launch_kwargs["devtools"] = True
            # Disable Chromium autofill/password-manager to prevent credential leakage
            # into search boxes and other text inputs during the crawl
            launch_kwargs["args"] = [
                "--disable-features=AutofillServerCommunication,PasswordManager,AutofillCreditCardFilling",
                "--disable-autofill",
                "--disable-save-password-bubble",
            ]
            browser = playwright.chromium.launch(**launch_kwargs)
            # Use a realistic browser profile to improve capture coverage on sites
            # that reduce responses for headless automation.
            context_kwargs = {
                "ignore_https_errors": True,
                "viewport": {"width": 1440, "height": 900},
                "user_agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.6367.207 Safari/537.36"
                ),
                "extra_http_headers": {
                    "Accept-Language": "en-US,en;q=0.9",
                },
                "java_script_enabled": True,
            }
            if auth_settings.get("reuse_storage_state") and _state_file_exists(Path(auth_settings["storage_state_path"])):
                context_kwargs["storage_state"] = str(auth_settings["storage_state_path"])
            context = browser.new_context(**context_kwargs)
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            if capture_trace:
                context.tracing.start(screenshots=True, snapshots=True, sources=True)

            page = context.new_page()

            def _on_console(message):
                try:
                    console_messages.append(
                        {
                            "type": message.type,
                            "text": message.text,
                            "location": message.location,
                        }
                    )
                except Exception:
                    pass

            def _on_page_error(exc):
                page_errors.append(str(exc))

            page.on("console", _on_console)
            page.on("pageerror", _on_page_error)

            def _scrub_credential_from_url(url: str) -> str:
                """Strip the configured password from query strings if Chromium autofill leaked it."""
                auth_password = str(auth_settings.get("password") or "").strip()
                if auth_password and auth_password in url:
                    url = url.replace(auth_password, "***REDACTED***")
                return url

            def on_request(request):
                # Early-exit: skip Vite dev-server bundles, node_modules, and
                # local filesystem paths (privacy + noise)
                req_url = request.url or ""
                if any(marker in req_url for marker in (
                    "/@fs/", "/@vite/", "/.vite/", "/node_modules/",
                    "/__vite_ping", "/@react-refresh",
                )):
                    return

                # Scrub leaked credentials from URL/query strings
                clean_url = _scrub_credential_from_url(req_url)

                request_id = id(request)
                # Redact sensitive headers, keep all others for API analysis
                raw_headers = dict(request.headers or {})
                safe_headers = _redact_headers(raw_headers)

                # Capture request body with redaction and size cap
                raw_post = request.post_data or ""
                content_type = raw_headers.get("content-type", "")
                req_body, req_body_format, req_body_bytes = _capture_body_snapshot(raw_post, content_type)

                captured[request_id] = {
                    "method": request.method,
                    "url": clean_url,
                    "path": _normalize_endpoint(clean_url),
                    "host": urlparse(clean_url).netloc,
                    "resource_type": request.resource_type,
                    "frame_url": request.frame.url if request.frame else None,
                    "is_navigation": request.is_navigation_request(),
                    "timestamp": datetime.utcnow().isoformat(),
                    "timestamp_ms": _now_ms(),
                    "headers": safe_headers,
                    "post_data": _redact_post_data_string(raw_post, content_type) if raw_post else "",
                    "request_body": req_body,
                    "request_body_format": req_body_format,
                    "request_body_bytes": req_body_bytes,
                    "request_content_type": content_type,
                }

            def on_response(response):
                request_id = id(response.request)
                entry = captured.get(request_id)
                if not entry:
                    return

                # Timing
                try:
                    timing = response.request.timing
                    response_time_ms = timing.get("responseEnd", 0) - timing.get("requestStart", 0)
                    if response_time_ms < 0:
                        response_time_ms = None
                except Exception:
                    response_time_ms = None

                if response_time_ms is None:
                    start_ms = entry.get("timestamp_ms")
                    response_time_ms = round(_now_ms() - start_ms, 1) if start_ms else None

                entry["status"] = response.status
                entry["response_time_ms"] = response_time_ms

                raw_resp_headers = dict(response.headers or {})
                entry["response_headers"] = _redact_headers(raw_resp_headers)

                # Capture response body only for API-relevant resource types
                resource_type = entry.get("resource_type", "")
                if resource_type in _BODY_CAPTURE_RESOURCE_TYPES:
                    resp_content_type = raw_resp_headers.get("content-type", "")
                    try:
                        raw_body = response.text()
                    except Exception:
                        raw_body = None

                    if raw_body is not None:
                        resp_body, resp_body_format, resp_body_bytes = _capture_body_snapshot(raw_body, resp_content_type)
                        entry["response_body"] = resp_body
                        entry["response_body_format"] = resp_body_format
                        entry["response_body_bytes"] = resp_body_bytes
                        entry["response_content_type"] = resp_content_type
                    else:
                        entry["response_body"] = None
                        entry["response_body_format"] = "unreadable"
                        entry["response_body_bytes"] = 0
                        entry["response_content_type"] = raw_resp_headers.get("content-type", "")


            page.on("request", on_request)
            page.on("response", on_response)
            if auth_settings.get("login_url"):
                auth_result = _attempt_browser_login(page, auth_settings, target, force=True)
                auth_state["last_auth_result"] = auth_result
                auth_state["authenticated"] = bool(auth_result.get("success"))
                print(f"[STIMULATOR] Auth: {auth_result.get('message')}")
                if auth_settings.get("require_auth") and not auth_result.get("success"):
                    raise RuntimeError(auth_result.get("message") or "Authentication was required but did not succeed.")

            def _on_visit(current_page, requested_url, depth):
                nonlocal final_page_title
                try:
                    final_page_title = current_page.title()
                except Exception:
                    final_page_title = final_page_title or ""

                snapshot = {
                    "requested_url": requested_url,
                    "current_url": current_page.url,
                    "depth": depth,
                    "title": final_page_title,
                }
                navigation_log.append(snapshot)
                print(f"[STIMULATOR] Visited depth={depth}: {current_page.url}")

                if capture_screenshots:
                    snapshot_name = f"playwright-visit-{len(navigation_log):03d}.png"
                    snapshot_path = reports_dir / snapshot_name
                    try:
                        current_page.screenshot(path=str(snapshot_path), full_page=True)
                        screenshot_paths.append(str(snapshot_path))
                        print(f"[STIMULATOR] Screenshot saved -> {snapshot_path}")
                    except Exception as exc:
                        print(f"[STIMULATOR] Screenshot skipped: {exc}")

            print(f"[STIMULATOR] Crawling same-origin pages and recording network traffic for {target}...")
            try:
                time_budget_s = int(time_budget_s if time_budget_s is not None else 600)
                stable_page_limit = int(stable_page_limit if stable_page_limit is not None else 3)
                crawled_urls = _crawl_pages(
                    page,
                    target,
                    max_pages=max_pages,
                    max_links=max_links,
                    max_clicks=max_clicks,
                    stable_page_limit=stable_page_limit,
                    time_budget_s=time_budget_s,
                    captured_dict=captured,
                    on_visit=_on_visit,
                    auth_settings=auth_settings,
                    auth_state=auth_state,
                )
                api_probe_plan, probe_metadata = _build_api_probe_plan(
                    target,
                    workspace_root=workspace_root,
                    max_probes=int(probe_ceiling) if probe_ceiling else None,
                )
                if api_probe_plan:
                    print(f"[STIMULATOR] Probing {len(api_probe_plan)} discovered API endpoint(s) to surface network traffic...")
                    executed_api_probes = _probe_api_endpoints(
                        page,
                        api_probe_plan,
                        per_probe_wait_ms=int(os.getenv("KEPLOY_API_PROBE_WAIT_MS", 500)),
                    )
                else:
                    executed_api_probes = []

                if not crawled_urls:
                    try:
                        page.goto(target, wait_until="domcontentloaded", timeout=45000)
                        page.wait_for_load_state("networkidle", timeout=15000)
                        _on_visit(page, target, 0)
                    except PlaywrightTimeoutError:
                        pass
                    except Exception:
                        pass
            finally:
                if capture_trace:
                    try:
                        context.tracing.stop(path=str(trace_path))
                        print(f"[STIMULATOR] Playwright trace saved -> {trace_path}")
                    except Exception as exc:
                        print(f"[STIMULATOR] Trace capture skipped: {exc}")

            try:
                context.close()
                browser.close()
            except Exception:
                pass
    except Exception as exc:
        print(f"[STIMULATOR] Browser capture unavailable: {exc}")
        capture_profile = {
            "capture_mode": "playwright",
            "execution_mode": "SIMULATED",
            "target_url": target,
            "headless": headless,
            "headed": not headless,
            "slow_mo_ms": slow_mo_ms,
            "devtools": devtools,
            "capture_trace": capture_trace,
            "capture_screenshots": capture_screenshots,
            "aggressive_discovery": aggressive_discovery,
            "auth": serialized_auth_settings,
            "auth_result": auth_result,
            "auth_state": {
                "authenticated": auth_state.get("authenticated", False),
                "login_attempts": auth_state.get("login_attempts", 0),
                "last_login_url": auth_state.get("last_login_url", ""),
                "last_auth_result": auth_result,
            },
            "captured_request_count": 0,
            "unique_endpoint_count": 0,
            "unique_hosts": [],
            "captured_requests": [],
            "traffic_inventory_path": None,
            "traffic_inventory_json_path": None,
            "navigation_log": navigation_log,
            "console_messages": console_messages,
            "page_errors": page_errors,
            "screenshot_paths": screenshot_paths,
            "trace_path": str(trace_path) if capture_trace else None,
            "notes": [
                f"Playwright capture failed: {exc}",
                "The pipeline will continue with whatever discovery artifacts already exist.",
            ],
        }
        yaml_path, json_path = _write_inventory_files(tests_dir, traffic_dir, capture_profile, [])
        capture_profile["traffic_inventory_path"] = yaml_path
        capture_profile["traffic_inventory_json_path"] = json_path
        report_seed_path = reports_dir / "capture-profile.json"
        with open(report_seed_path, "w", encoding="utf-8") as handle:
            json.dump(capture_profile, handle, indent=2)
        return capture_profile

    captured_requests = list(captured.values())
    unique_endpoints = sorted({entry.get("path", "/") for entry in captured_requests})
    unique_hosts = sorted({entry.get("host", "") for entry in captured_requests if entry.get("host")})
    auth_result = auth_state.get("last_auth_result", auth_result)

    capture_profile = {
        "capture_mode": "playwright",
        "execution_mode": "LIVE",
        "target_url": target,
        "headless": headless,
        "headed": not headless,
        "slow_mo_ms": slow_mo_ms,
        "devtools": devtools,
        "capture_trace": capture_trace,
        "capture_screenshots": capture_screenshots,
        "aggressive_discovery": aggressive_discovery,
        "auth": serialized_auth_settings,
        "auth_result": auth_result,
        "auth_state": {
            "authenticated": auth_state.get("authenticated", False),
            "login_attempts": auth_state.get("login_attempts", 0),
            "last_login_url": auth_state.get("last_login_url", ""),
            "last_auth_result": auth_result,
        },
        "captured_request_count": len(captured_requests),
        "unique_endpoint_count": len(unique_endpoints),
        "unique_hosts": unique_hosts,
        "captured_requests": captured_requests,
        "notes": [
            "Captured browser traffic using Playwright request/response listeners.",
            f"Same-site crawl visited {len(crawled_urls)} page(s).",
            f"Probed {len(executed_api_probes)} discovered API endpoint(s) from local inventory.",
            f"Interactive stimuli attempted up to {max_clicks} clicks per page.",
            f"Browser launch mode: {launch_mode}.",
            f"Aggressive discovery: {aggressive_discovery}.",
            f"Auth mode: {auth_result.get('mode')}.",
            "Traffic inventory is persisted under keploy/tests/keploy/traffic-inventory.yaml.",
        ],
        "navigation_log": navigation_log,
        "console_messages": console_messages,
        "page_errors": page_errors,
        "screenshot_paths": screenshot_paths,
        "trace_path": str(trace_path) if capture_trace else None,
        "final_page_url": page.url if page else target,
        "final_page_title": final_page_title,
    }

    yaml_path, json_path = _write_inventory_files(tests_dir, traffic_dir, capture_profile, captured_requests)
    capture_profile["traffic_inventory_path"] = yaml_path
    capture_profile["traffic_inventory_json_path"] = json_path
    capture_profile["unique_endpoints"] = unique_endpoints
    capture_profile["crawled_pages"] = crawled_urls
    capture_profile["api_probe_count"] = len(executed_api_probes)
    capture_profile["api_probe_plan"] = api_probe_plan if api_probe_plan else []

    report_seed_path = reports_dir / "capture-profile.json"
    with open(report_seed_path, "w", encoding="utf-8") as handle:
        json.dump(capture_profile, handle, indent=2)

    print(f"[STIMULATOR] Captured {len(captured_requests)} network request(s).")
    print(f"[STIMULATOR] Traffic inventory saved -> {yaml_path}")

    return capture_profile
