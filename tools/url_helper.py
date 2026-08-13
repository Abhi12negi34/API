"""
Shared URL helper — prevents the /app prefix bug from recurring.

Every tool that builds a URL from target_url + discovered path should use:
    from tools.url_helper import build_probe_url
    url = build_probe_url(target_url, path)

This always resolves against the origin (scheme+host), never the full
target_url path — so http://localhost:9000/app + /admin/products gives
http://localhost:9000/admin/products, NOT http://localhost:9000/app/admin/products.
"""
from urllib.parse import urlparse


def get_origin(target_url: str) -> str:
    """Extract scheme://host:port from a full URL, dropping any path."""
    parsed = urlparse(str(target_url or "").strip())
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return str(target_url or "").strip().rstrip("/")


def build_probe_url(target_url: str, path: str) -> str:
    """
    Build a probe URL from target_url and a discovered path.
    Always resolves against origin only — never prepends target_url's path.

    Examples:
        build_probe_url("http://localhost:9000/app", "/admin/products")
        → "http://localhost:9000/admin/products"

        build_probe_url("http://localhost:9000/app", "admin/products")
        → "http://localhost:9000/admin/products"
    """
    origin = get_origin(target_url)
    path = str(path or "/").strip()
    if not path.startswith("/"):
        path = "/" + path
    return origin.rstrip("/") + path
