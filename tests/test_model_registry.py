from app.services.grok.services.model import Cost, ModelService, Tier
from app.services.reverse.app_chat import AppChatReverse


def test_old_models_are_kept():
    assert ModelService.get("grok-3") is not None
    assert ModelService.get("grok-4") is not None
    assert ModelService.get("grok-imagine-1.0") is not None
    assert ModelService.get("grok-imagine-1.0-video") is not None


def test_new_upstream_models_are_registered():
    expected = {
        "grok-4.20-0309-non-reasoning",
        "grok-4.20-0309",
        "grok-4.20-0309-reasoning",
        "grok-4.20-0309-non-reasoning-super",
        "grok-4.20-0309-super",
        "grok-4.20-0309-reasoning-super",
        "grok-4.20-0309-non-reasoning-heavy",
        "grok-4.20-0309-heavy",
        "grok-4.20-0309-reasoning-heavy",
        "grok-4.20-multi-agent-0309",
        "grok-4.20-fast",
        "grok-4.20-auto",
        "grok-4.20-expert",
        "grok-4.20-heavy",
        "grok-4.3-beta",
        "grok-imagine-image-lite",
        "grok-imagine-image",
        "grok-imagine-image-pro",
        "grok-imagine-image-edit",
        "grok-imagine-video",
    }

    registered = {model.model_id for model in ModelService.list()}

    assert expected <= registered


def test_new_model_metadata_matches_current_runtime_shape():
    model = ModelService.get("grok-4.3-beta")

    assert model is not None
    assert model.grok_model == "grok-420-computer-use-sa"
    assert model.model_mode == "MODEL_MODE_GROK_4_3"
    assert model.tier == Tier.SUPER
    assert model.cost == Cost.HIGH


def test_pool_candidates_include_heavy_and_prefer_best_ordering():
    assert ModelService.pool_for_model("grok-4.20-heavy") == "ssoHeavy"
    assert ModelService.pool_candidates_for_model("grok-4.20-0309") == [
        "ssoSuper",
        "ssoHeavy",
    ]
    assert ModelService.pool_candidates_for_model("grok-4.20-0309-heavy") == [
        "ssoHeavy"
    ]
    assert ModelService.pool_candidates_for_model("grok-4.20-fast") == [
        "ssoHeavy",
        "ssoSuper",
        "ssoBasic",
    ]


def test_new_mode_ids_are_serialized_as_mode_id_payloads(monkeypatch):
    monkeypatch.setattr(
        "app.services.reverse.app_chat.get_config",
        lambda key, default=None: default,
    )

    payload = AppChatReverse.build_payload(
        message="hello",
        model="grok-420",
        mode="MODEL_MODE_AUTO_ID",
    )

    assert payload["modeId"] == "auto"
    assert "modelName" not in payload
    assert "modelMode" not in payload

    payload = AppChatReverse.build_payload(
        message="hello",
        model="grok-420-computer-use-sa",
        mode="MODEL_MODE_GROK_4_3",
    )

    assert payload["modeId"] == "grok-420-computer-use-sa"
    assert "modelName" not in payload
    assert "modelMode" not in payload
