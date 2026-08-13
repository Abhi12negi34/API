from core.api.discovery_inventory import _classify_entry, build_discovery_inventory


def test_classify_entry_promotes_query_based_json_request():
    entry = {
        "method": "GET",
        "path": "https://example.com/api/products?id=1",
        "resource_type": "document",
        "response_headers": {"content-type": "application/json"},
    }

    classified = _classify_entry(entry, "https://example.com")

    assert classified["is_api_candidate"] is True
    assert classified["path"] == "/api/products"
    assert classified["full_url"] == "https://example.com/api/products"
    assert classified["observed_url"] == "https://example.com/api/products?id=1"


def test_build_discovery_inventory_keeps_query_based_api_and_excludes_static_assets(monkeypatch, tmp_path):
    artifact_path = tmp_path / "traffic-inventory.yaml"

    payload = {
        "capture_profile": {
            "target_url": "https://example.com",
            "captured_requests": [
                {
                    "method": "GET",
                    "url": "https://example.com/api/products?id=1",
                    "path": "/api/products?id=1",
                    "host": "example.com",
                    "resource_type": "document",
                    "status": 200,
                    "response_headers": {"content-type": "application/json"},
                },
                {
                    "method": "GET",
                    "url": "https://example.com/assets/logo.webp",
                    "path": "/assets/logo.webp",
                    "host": "example.com",
                    "resource_type": "image",
                    "status": 200,
                    "response_headers": {"content-type": "image/webp"},
                },
            ],
        },
        "captured_requests": [
            {
                "method": "GET",
                "url": "https://example.com/api/products?id=1",
                "path": "/api/products?id=1",
                "host": "example.com",
                "resource_type": "document",
                "status": 200,
                "response_headers": {"content-type": "application/json"},
            },
            {
                "method": "GET",
                "url": "https://example.com/assets/logo.webp",
                "path": "/assets/logo.webp",
                "host": "example.com",
                "resource_type": "image",
                "status": 200,
                "response_headers": {"content-type": "image/webp"},
            },
        ],
    }

    monkeypatch.setattr(
        "core.api.discovery_inventory.iter_artifact_files",
        lambda workspace_root=None: [artifact_path],
    )
    monkeypatch.setattr(
        "core.api.discovery_inventory._load_artifact",
        lambda path: payload,
    )

    inventory = build_discovery_inventory("https://example.com", workspace_root=tmp_path)

    assert inventory["inventory_summary"]["traffic_request_count"] == 2
    api = next(
        item
        for item in inventory["discovered_apis"]
        if item["path"] == "/api/products" and item["full_url"] == "https://example.com/api/products"
    )
    assert api["path"] == "/api/products"
    assert api["full_url"] == "https://example.com/api/products"
    assert api["observed_url"] == "https://example.com/api/products?id=1"
    assert api["request_kind"] in {"api_candidate", "probable_api_candidate"}
    assert all(item["path"] != "/assets/logo.webp" for item in inventory["discovered_apis"])
