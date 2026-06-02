"""Grok device-id selection and optional bootstrap."""

import random
import re
from http.cookies import SimpleCookie

from app.platform.config.snapshot import get_config
from app.platform.logging.logger import logger
from app.control.proxy.models import ProxyLease
from .session import ResettableSession, build_session_kwargs

_DEVICE_COOKIE = "grok_device_id"
_cached_device_id = ""


def split_device_ids(value: str | None) -> list[str]:
    """Split comma/semicolon/newline separated grok_device_id values."""
    if not value:
        return []
    parts = [part.strip() for part in re.split(r"[;,\r\n]+", str(value))]
    return [part for part in parts if part]


def configured_device_id() -> str:
    """Return one configured device id, randomly selected from the pool."""
    cfg = get_config()
    value = cfg.get_str("features.grok_device_id", "") or cfg.get_str(
        "proxy.grok_device_id", ""
    ) or cfg.get_str(
        "proxy.clearance.grok_device_id", ""
    )
    ids = split_device_ids(value)
    return random.choice(ids) if ids else ""


def current_device_id() -> str:
    """Return the configured device id or a cached auto-fetched value."""
    return configured_device_id() or _cached_device_id


def auto_device_enabled() -> bool:
    """Return whether automatic grok_device_id bootstrap is enabled."""
    return get_config().get_bool("features.grok_device_id_auto", False)


def _extract_set_cookie_device(headers) -> str:
    values = []
    try:
        values = list(headers.get_list("set-cookie"))
    except Exception:
        try:
            raw = headers.get("set-cookie")
        except Exception:
            raw = ""
        if raw:
            values = [raw]
    for value in values:
        cookie = SimpleCookie()
        try:
            cookie.load(value)
        except Exception:
            continue
        morsel = cookie.get(_DEVICE_COOKIE)
        if morsel and morsel.value:
            return morsel.value.strip()
    return ""


def _sso_cookie(token: str | None) -> str:
    token = str(token or "").strip()
    if token.startswith("sso="):
        token = token[4:]
    if not token:
        return ""
    return f"sso={token}; sso-rw={token}"


async def ensure_device_id(
    token: str | None = None,
    *,
    lease: ProxyLease | None = None,
) -> str:
    """Auto-fetch a grok_device_id from grok.com when enabled and needed."""
    global _cached_device_id
    device_id = current_device_id()
    if device_id or not auto_device_enabled():
        return device_id

    try:
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Origin": "https://grok.com",
            "Referer": "https://grok.com/",
        }
        cookie = _sso_cookie(token)
        if cookie:
            headers["Cookie"] = cookie
        async with ResettableSession(**build_session_kwargs(lease=lease)) as session:
            response = await session.get(
                "https://grok.com/",
                headers=headers,
                timeout=20.0,
            )
        device_id = _extract_set_cookie_device(response.headers)
    except Exception as exc:
        logger.warning("grok device id auto-fetch failed: error={}", exc)
        return ""

    if device_id:
        _cached_device_id = device_id
        logger.info("grok device id auto-fetched")
    else:
        logger.warning("grok device id auto-fetch returned no device cookie")
    return _cached_device_id


__all__ = [
    "auto_device_enabled",
    "configured_device_id",
    "current_device_id",
    "ensure_device_id",
    "split_device_ids",
]
