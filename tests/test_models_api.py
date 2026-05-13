from fastapi.testclient import TestClient

from main import create_app


def test_models_api_is_public_and_returns_registered_models():
    client = TestClient(create_app())

    response = client.get("/v1/models")

    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "list"
    ids = {item["id"] for item in payload["data"]}
    assert "grok-4.20-0309" in ids
    assert "grok-4.3-beta" in ids
