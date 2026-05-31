"""Runtime account invalidation rules."""

from __future__ import annotations

from app.platform.config.snapshot import get_config


def invalid_account_keywords() -> list[str]:
    raw = get_config().get_str("account.invalid_keywords", "")
    parts = [part.strip().lower() for part in raw.replace("\n", ",").split(",")]
    return [part for part in parts if part]


def invalid_account_status_codes() -> frozenset[int]:
    raw = get_config().get("account.invalid_status_codes", "401,403")
    if isinstance(raw, (list, tuple, set)):
        parts = [str(item).strip() for item in raw]
    else:
        parts = [part.strip() for part in str(raw or "").split(",")]
    codes = {int(part) for part in parts if part.isdigit()}
    return frozenset(codes or {401, 403})


def body_has_invalid_account_keyword(body: str) -> bool:
    text = str(body or "").lower()
    return any(keyword in text for keyword in invalid_account_keywords())


def status_is_invalid_account(status_code: int | None) -> bool:
    return int(status_code or 0) in invalid_account_status_codes()


def response_is_invalid_account(status_code: int | None, body: str = "") -> bool:
    if status_is_invalid_account(status_code):
        return True
    return body_has_invalid_account_keyword(body)


__all__ = [
    "body_has_invalid_account_keyword",
    "invalid_account_keywords",
    "invalid_account_status_codes",
    "response_is_invalid_account",
    "status_is_invalid_account",
]
