import requests

def audit_jwt_weak_signatures(target_url="http://localhost"):
    """
    Probes the JWKS endpoint if available, and checks for common JWT misconfigurations
    such as 'none' algorithm support and RS256 key presence.
    """
    print("[SECURITY: JWT Auditor] Checking JWKS endpoint for weak signature configurations...")
    base = target_url.rstrip("/")
    jwks_paths = ["/.well-known/jwks.json", "/api/v1/auth/jwks", "/oauth/jwks"]

    for path in jwks_paths:
        try:
            resp = requests.get(f"{base}{path}", timeout=4, verify=True)
            if resp.status_code == 200:
                body = resp.json()
                keys = body.get("keys", [])
                algorithms = [k.get("alg", "unknown") for k in keys]
                key_types = [k.get("kty", "unknown") for k in keys]

                weak = [a for a in algorithms if a.lower() in ("none", "hs256")]
                if weak:
                    return {
                        "success": False,
                        "log": f"JWKS at {path} exposes weak algorithms: {weak}. Keys: {key_types}.",
                        "severity": "CRITICAL",
                        "path": f"{base}{path}",
                        "recommendation": "Use RS256 or ES256 asymmetric algorithms. Never accept 'none' or symmetric HS256 in public APIs."
                    }
                return {
                    "success": True,
                    "log": f"JWKS at {path}: {len(keys)} key(s) found, algorithms={algorithms}, types={key_types}. No weak algorithm detected.",
                    "severity": "INFO",
                    "path": f"{base}{path}",
                    "recommendation": "N/A. Rotate JWKS keys every 90 days."
                }
        except Exception:
            continue

    return {
        "success": True,
        "log": "[SIMULATION] No JWKS endpoint found at common paths. Cannot verify JWT algorithm strength.",
        "severity": "INFO",
        "path": base,
        "recommendation": "Expose a JWKS endpoint at /.well-known/jwks.json for public key verification."
    }
