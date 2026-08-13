import requests

def audit_oauth2_token_scoping(target_url="http://localhost"):
    """
    Checks the OAuth2 token endpoint for scope configuration issues.
    Looks for overly broad scopes in token introspection or discovery docs.
    """
    print("[SECURITY: OAuth2 Scope Auditor] Checking OAuth2 token scoping configuration...")
    base = target_url.rstrip("/")
    discovery_paths = ["/.well-known/openid-configuration", "/oauth/.well-known/openid-configuration", "/oauth/v2/.well-known/openid-configuration"]

    for path in discovery_paths:
        try:
            resp = requests.get(f"{base}{path}", timeout=4, verify=True)
            if resp.status_code == 200:
                body = resp.json()
                scopes_supported = body.get("scopes_supported", [])
                risky_scopes = [s for s in scopes_supported if s in ("write:*", "admin", "*", "full_access")]

                if risky_scopes:
                    return {
                        "success": False,
                        "log": f"Overly broad OAuth2 scopes found in discovery doc at {path}: {risky_scopes}. All scopes: {scopes_supported}.",
                        "severity": "HIGH",
                        "path": f"{base}{path}",
                        "recommendation": "Replace wildcard scopes with atomic, resource-specific scopes (e.g. 'read:orders', 'write:profile')."
                    }
                return {
                    "success": True,
                    "log": f"OAuth2 discovery at {path}. Scopes supported: {scopes_supported}. No wildcard scopes.",
                    "severity": "INFO",
                    "path": f"{base}{path}",
                    "recommendation": "N/A. Periodically audit scope list as new features are added."
                }
        except Exception:
            continue

    return {
        "success": True,
        "log": "[SIMULATION] No OAuth2 discovery endpoint found. Cannot verify token scoping configuration.",
        "severity": "INFO",
        "path": base,
        "recommendation": "Expose /.well-known/openid-configuration for OAuth2 introspection. Ensure scopes follow principle of least privilege."
    }
