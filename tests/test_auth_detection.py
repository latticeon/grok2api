from app.services.reverse.utils.auth_detection import (
    get_auth_error_status_codes,
    get_auth_error_keywords,
    is_blocked_or_auth_expired_response,
)


def test_blocked_user_body_is_treated_as_expired_signal():
    assert is_blocked_or_auth_expired_response(
        403,
        "application/json",
        '{"error":{"message":"User is blocked [WKE=unauthorized:blocked-user]"}}',
    )


def test_non_json_403_is_not_treated_as_expired_signal():
    assert not is_blocked_or_auth_expired_response(
        403,
        "text/html",
        "User is blocked",
    )


def test_configured_keywords_are_loaded(monkeypatch):
    monkeypatch.setattr(
        "app.services.reverse.utils.auth_detection.get_config",
        lambda key, default=None: ["custom blocked marker"]
        if key == "app.auth_block_keywords"
        else default,
    )

    assert "custom blocked marker" in get_auth_error_keywords()
    assert is_blocked_or_auth_expired_response(
        403,
        "application/json",
        '{"error":{"message":"custom blocked marker"}}',
    )


def test_configured_status_codes_are_loaded(monkeypatch):
    monkeypatch.setattr(
        "app.services.reverse.utils.auth_detection.get_config",
        lambda key, default=None: [401, 403, 451]
        if key == "app.auth_block_status_codes"
        else default,
    )

    assert 451 in get_auth_error_status_codes()
    assert is_blocked_or_auth_expired_response(
        451,
        "application/json",
        '{"error":{"message":"User is blocked"}}',
    )
