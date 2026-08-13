import re
from pathlib import Path

import requests
import yaml

PII_PATTERNS = {
    "Credit Card": r"\b(?:\d[ -]?){13,16}\b",
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
    "Email (raw)": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "Password field": r'"password"\s*:\s*"[^"]+"',
    "API Key": r'(?i)(api[_-]?key|secret|token)\s*[:=]\s*["\']?[A-Za-z0-9_\-]{16,}',
    "JWT": r"eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}",
    "Bearer Token": r"(?i)bearer\s+[A-Za-z0-9_\-\.]{20,}",
}


def _workspace_root(workspace_root=None):
    if workspace_root:
        return Path(workspace_root).resolve()
    return Path.cwd().resolve()


def _candidate_artifact_dirs(workspace_root=None):
    root = _workspace_root(workspace_root)
    candidates = [
        root / "keploy" / "tests",
        root / "keploy" / "mocks",
        root / "keploy",
        root / "tests" / "keploy",
        root / "tests",
    ]
    seen = set()
    ordered = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        ordered.append(resolved)
    return ordered


def _iter_yaml_files(root_path):
    if not root_path.exists():
        return []
    if root_path.is_file():
        return [root_path]
    files = (
        list(root_path.rglob("*.yaml"))
        + list(root_path.rglob("*.yml"))
        + list(root_path.rglob("*.json"))   # also scan JSON traffic inventory
    )
    return sorted({path.resolve() for path in files})


def _flatten_strings(payload):
    values = []
    if isinstance(payload, dict):
        for value in payload.values():
            values.extend(_flatten_strings(value))
    elif isinstance(payload, list):
        for item in payload:
            values.extend(_flatten_strings(item))
    elif isinstance(payload, str):
        values.append(payload)
    else:
        values.append(str(payload))
    return values


SENSITIVE_KEYWORDS = {
    "body",
    "response",
    "request",
    "headers",
    "header",
    "post_data",
    "cookie",
    "authorization",
    "auth",
    "token",
    "password",
    "secret",
    "email",
}


def _luhn_check(candidate: str) -> bool:
    digits = [int(char) for char in candidate if char.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False

    total = 0
    reverse_digits = list(reversed(digits))
    for index, digit in enumerate(reverse_digits):
        if index % 2 == 1:
            doubled = digit * 2
            total += doubled - 9 if doubled > 9 else doubled
        else:
            total += digit
    return total % 10 == 0


def _scan_credit_cards(text, file_path):
    findings = []
    for match in re.findall(PII_PATTERNS["Credit Card"], text):
        digits = re.sub(r"\D", "", match)
        if _luhn_check(digits):
            findings.append(
                {
                    "file": str(file_path),
                    "label": "Credit Card",
                    "match_count": 1,
                }
            )
    return findings


def _scan_text(text, file_path):
    findings = []
    for label, pattern in PII_PATTERNS.items():
        if label == "Credit Card":
            continue
        matches = re.findall(pattern, text)
        if matches:
            findings.append(
                {
                    "file": str(file_path),
                    "label": label,
                    "match_count": len(matches),
                }
            )
    return findings


def _scan_yaml_payload(payload, file_path, key_path=None):
    findings = []
    key_path = key_path or []

    if isinstance(payload, dict):
        for key, value in payload.items():
            next_path = key_path + [str(key).lower()]
            findings.extend(_scan_yaml_payload(value, file_path, next_path))
    elif isinstance(payload, list):
        for item in payload:
            findings.extend(_scan_yaml_payload(item, file_path, key_path))
    elif isinstance(payload, str):
        path_hints = set(key_path)
        if path_hints & SENSITIVE_KEYWORDS:
            findings.extend(_scan_text(payload, file_path))
            findings.extend(_scan_credit_cards(payload, file_path))
    return findings
    return findings


def _scan_local_artifacts(workspace_root=None):
    artifact_findings = []
    seen_findings = set()
    files_scanned = 0
    for artifact_dir in _candidate_artifact_dirs(workspace_root):
        for artifact_file in _iter_yaml_files(artifact_dir):
            files_scanned += 1
            try:
                text = artifact_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            artifact_findings.extend(_scan_text(text, artifact_file))
            try:
                if artifact_file.suffix == ".json":
                    import json as _json
                    parsed = _json.loads(text)
                else:
                    parsed = yaml.safe_load(text)
            except Exception:
                parsed = None
            if parsed is not None:
                artifact_findings.extend(_scan_yaml_payload(parsed, artifact_file))

    deduped = []
    for finding in artifact_findings:
        key = (finding["file"], finding["label"])
        if key in seen_findings:
            continue
        seen_findings.add(key)
        deduped.append(finding)

    return deduped, files_scanned


def _scan_live_endpoints(target_url, probe_paths):
    from tools.url_helper import build_probe_url
    leaks_found = []
    for path in probe_paths:
        url = build_probe_url(target_url, path)
        try:
            resp = requests.get(url, timeout=5, verify=True)
            leaks_found.extend(
                {"file": url, "label": label, "match_count": 1}
                for label, pattern in PII_PATTERNS.items()
                if re.search(pattern, resp.text)
            )
        except Exception:
            continue
    return leaks_found


PROBE_PATHS = ["/api/v1/user", "/api/v1/profile", "/api/v1/auth", "/"]


def audit_pii_data_leaks(target_url="http://localhost", workspace_root=None):
    """
    Scans recorded Keploy traffic first, then falls back to live probing if no artifacts exist.
    """
    print("[SECURITY: PII Leak Auditor] Scanning Keploy artifacts for PII exposure...")
    artifact_findings, files_scanned = _scan_local_artifacts(workspace_root=workspace_root)

    if not artifact_findings:
        print("[SECURITY: PII Leak Auditor] No local Keploy artifacts found. Falling back to live probes.")
        artifact_findings = _scan_live_endpoints(target_url, PROBE_PATHS)

    if artifact_findings:
        leak_summary = []
        for finding in artifact_findings:
            leak_summary.append(
                f"{finding['label']} detected in {finding['file']} ({finding['match_count']} match{'es' if finding['match_count'] != 1 else ''})"
            )
        return {
            "success": False,
            "status": "FAIL",
            "mode": "LIVE" if files_scanned == 0 else "SIMULATED",
            "severity": "CRITICAL",
            "path": str(_workspace_root(workspace_root)),
            "log": f"PII LEAKS DETECTED: {'; '.join(leak_summary)}",
            "recommendation": "Mask or redact all PII fields before serializing API responses. Apply output filtering middleware and sanitize Keploy recordings.",
            "files_scanned": files_scanned,
            "leaks_found": artifact_findings,
        }

    return {
        "success": True,
        "status": "PASS",
        "mode": "LIVE" if files_scanned == 0 else "SIMULATED",
        "severity": "INFO",
        "path": str(_workspace_root(workspace_root)),
        "log": f"No PII patterns (Credit Card, SSN, JWT, raw passwords, API keys) detected across {files_scanned} Keploy artifact file(s).",
        "recommendation": "N/A",
        "files_scanned": files_scanned,
        "leaks_found": [],
    }
