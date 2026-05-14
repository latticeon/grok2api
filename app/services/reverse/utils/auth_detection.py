"""Helpers for upstream auth/block detection."""

from app.core.config import get_config


AUTH_ERROR_KEYWORDS = (
    "unauthorized",
    "not logged in",
    "unauthenticated",
    "bad-credentials",
    "bot abuse",
    "user is blocked",
)
DEFAULT_AUTH_ERROR_STATUS_CODES = (401, 403)


def get_auth_error_keywords() -> tuple[str, ...]:
    """Return built-in and configured auth/block keywords."""
    raw_value = get_config("app.auth_block_keywords", [])
    configured: list[str] = []

    if isinstance(raw_value, str):
        candidates = raw_value.splitlines()
    elif isinstance(raw_value, (list, tuple)):
        candidates = raw_value
    else:
        candidates = []

    seen = {item.casefold() for item in AUTH_ERROR_KEYWORDS}
    for item in candidates:
        text = str(item or "").strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        configured.append(text)

    return AUTH_ERROR_KEYWORDS + tuple(configured)


def get_auth_error_status_codes() -> tuple[int, ...]:
    """Return built-in and configured status codes for auth/block detection."""
    raw_value = get_config(
        "app.auth_block_status_codes", list(DEFAULT_AUTH_ERROR_STATUS_CODES)
    )
    configured: list[int] = []

    if isinstance(raw_value, str):
        candidates = raw_value.splitlines()
    elif isinstance(raw_value, (list, tuple)):
        candidates = raw_value
    else:
        candidates = []

    seen = set(DEFAULT_AUTH_ERROR_STATUS_CODES)
    for item in candidates:
        try:
            code = int(item)
        except (TypeError, ValueError):
            continue
        if code in seen:
            continue
        seen.add(code)
        configured.append(code)

    return DEFAULT_AUTH_ERROR_STATUS_CODES + tuple(configured)


def is_blocked_or_auth_expired_response(
    status_code: int,
    content_type: str,
    response_text: str,
) -> bool:
    """Return True when upstream response strongly indicates token auth/block failure."""
    if status_code not in get_auth_error_status_codes():
        return False
    if "application/json" not in (content_type or "").lower():
        return False

    body_lower = (response_text or "").lower()
    return any(keyword.lower() in body_lower for keyword in get_auth_error_keywords())


__all__ = [
    "AUTH_ERROR_KEYWORDS",
    "DEFAULT_AUTH_ERROR_STATUS_CODES",
    "get_auth_error_keywords",
    "get_auth_error_status_codes",
    "is_blocked_or_auth_expired_response",
]
