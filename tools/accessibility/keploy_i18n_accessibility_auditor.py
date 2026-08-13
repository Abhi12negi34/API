import requests
from core.api.discovery_inventory import build_discovery_inventory

def audit_i18n_accessibility(target_url="http://localhost"):
    """
    Checks if the API respects Accept-Language headers and returns
    locale-appropriate content or proper i18n headers.
    """
    print("[ACCESSIBILITY: i18n Auditor] Checking Accept-Language header honor...")
    base = target_url.rstrip("/")
    probe_path = f"{base}/"

    inventory = build_discovery_inventory(target_url, workspace_root=None)
    if not inventory.get("discovered_apis"):
        return {
            "success": False,
            "status": "SKIPPED",
            "mode": "SIMULATED",
            "log": "No confirmed API surface was discovered, so i18n probing was skipped.",
            "severity": "INFO",
            "path": probe_path,
            "recommendation": "Populate the discovery baseline or target an API-backed endpoint to evaluate Content-Language behavior."
        }

    results = {}
    for lang in ["en-US", "ar", "zh-CN", "fr-FR"]:
        try:
            resp = requests.get(probe_path, headers={"Accept-Language": lang}, timeout=4, verify=True)
            content_lang = resp.headers.get("Content-Language", "not-set")
            results[lang] = {"status": resp.status_code, "content_language": content_lang}
        except Exception:
            results[lang] = {"status": "error", "content_language": "N/A"}

    honored = [l for l, r in results.items() if r["content_language"] != "not-set"]
    not_honored = [l for l, r in results.items() if r["content_language"] == "not-set"]

    if not_honored and not honored:
        return {
            "success": False,
            "log": f"Content-Language header absent for all probed locales: {', '.join(not_honored)}.",
            "severity": "MEDIUM",
            "path": probe_path,
            "recommendation": "Return Content-Language header matching Accept-Language. Support at minimum EN, AR (RTL), and ZH for global accessibility."
        }
    return {
        "success": True,
        "log": f"Content-Language honored for: {', '.join(honored) or 'N/A'}. Not honored: {', '.join(not_honored) or 'none'}.",
        "severity": "INFO" if honored else "LOW",
        "path": probe_path,
        "recommendation": "N/A" if len(not_honored) == 0 else f"Extend i18n support to: {', '.join(not_honored)}."
    }
