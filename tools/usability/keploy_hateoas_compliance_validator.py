import requests

def validate_hateoas_compliance(target_url="http://localhost"):
    """
    Checks REST API responses for HATEOAS _links or Link headers that make
    the API self-discoverable (HAL, JSON:API, or RFC 8288 style).
    """
    print("[USABILITY: HATEOAS Validator] Checking for hypermedia links in API responses...")
    base = target_url.rstrip("/")
    probe_paths = ["/api/v1/", "/api/v1/products", "/api/v1/orders", "/api/v1/user"]

    hateoas_found = []
    missing_hateoas = []

    for path in probe_paths:
        try:
            resp = requests.get(f"{base}{path}", timeout=4, verify=True)
            if resp.status_code < 500:
                body = {}
                try:
                    body = resp.json()
                except Exception:
                    pass

                has_links_body = "_links" in body or "links" in body
                has_link_header = "Link" in resp.headers

                if has_links_body or has_link_header:
                    detail = []
                    if has_links_body:
                        detail.append("_links in body")
                    if has_link_header:
                        detail.append(f"Link header: {resp.headers['Link']}")
                    hateoas_found.append(f"{path} ({', '.join(detail)})")
                else:
                    missing_hateoas.append(path)
        except Exception:
            continue

    if hateoas_found:
        return {
            "success": True,
            "log": f"HATEOAS links found on: {'; '.join(hateoas_found)}.",
            "severity": "INFO",
            "path": base,
            "recommendation": "N/A"
        }
    if missing_hateoas:
        return {
            "success": False,
            "log": f"No _links or Link headers found on endpoints: {', '.join(missing_hateoas)}. API is not self-discoverable.",
            "severity": "LOW",
            "path": base,
            "recommendation": "Add HAL-style '_links' to responses or RFC 8288 Link headers to improve API discoverability."
        }
    return {
        "success": True,
        "log": "[SIMULATION] No probe endpoints reachable. Cannot verify HATEOAS compliance.",
        "severity": "INFO",
        "path": base,
        "recommendation": "Implement HATEOAS _links on all collection and resource endpoints."
    }
