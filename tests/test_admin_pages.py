from fastapi.testclient import TestClient

from main import create_app


def test_admin_model_test_page_exists():
    client = TestClient(create_app())

    response = client.get("/admin/model-test")

    assert response.status_code == 200
    assert "model-test.js" in response.text


def test_admin_testable_models_endpoint_filters_non_chat_models(monkeypatch):
    client = TestClient(create_app())
    app_key = "test-admin-key"

    monkeypatch.setattr(
        "app.core.auth.get_app_key",
        lambda: app_key,
    )

    response = client.get(
        "/v1/admin/tokens/test/models",
        headers={"Authorization": f"Bearer {app_key}"},
    )

    assert response.status_code == 200
    payload = response.json()
    ids = {item["id"] for item in payload["data"]}
    assert "grok-4" in ids
    assert "grok-auto" not in ids
    assert "grok-auto-lite" not in ids
    assert "grok-imagine-image" not in ids
    assert "grok-imagine-video" not in ids
