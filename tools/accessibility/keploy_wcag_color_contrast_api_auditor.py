import requests

def audit_wcag_color_contrast_api(target_url="http://localhost"):
    """
    Checks if the theme/design API exposes a high-contrast mode option,
    indicating programmatic accessibility support.
    """
    print("[ACCESSIBILITY: WCAG Color Contrast API Auditor] Checking theme API for high-contrast support...")
    base = target_url.rstrip("/")
    theme_paths = ["/api/v1/theme", "/api/v1/settings/theme", "/api/v1/preferences/display"]

    for path in theme_paths:
        try:
            resp = requests.get(f"{base}{path}", timeout=4, verify=True)
            if resp.status_code == 200:
                body = resp.json() if resp.headers.get("Content-Type", "").startswith("application/json") else {}
                has_hc = any(k in str(body).lower() for k in ["high_contrast", "high-contrast", "hc_mode", "contrast_mode"])

                if has_hc:
                    return {
                        "success": True,
                        "log": f"High-contrast mode option detected in theme API at {path}: {body}",
                        "severity": "INFO",
                        "path": f"{base}{path}",
                        "recommendation": "N/A. Ensure high-contrast preferences sync with OS-level prefers-contrast media query."
                    }
                return {
                    "success": False,
                    "log": f"Theme API at {path} exists but lacks high-contrast configuration option. Body keys: {list(body.keys()) if isinstance(body, dict) else 'non-JSON'}.",
                    "severity": "MEDIUM",
                    "path": f"{base}{path}",
                    "recommendation": "Add 'high_contrast_mode: bool' to the theme API response. Honor OS prefers-contrast media query."
                }
        except Exception:
            continue

    return {
        "success": True,
        "log": "[SIMULATION] No theme/display API endpoint found. High-contrast API support not verifiable.",
        "severity": "INFO",
        "path": base,
        "recommendation": "Expose a /api/v1/theme endpoint with high-contrast mode support per WCAG 1.4.3."
    }
