import os
import re

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import verify_app_key
from app.core.config import config
from app.core.logger import logger, reload_logging_from_config
from app.core.storage import (
    LocalStorage,
    RedisStorage,
    SQLStorage,
    get_storage as resolve_storage,
)
from app.services.grok.services.auto_model import (
    get_auto_model_route_map,
    resolve_auto_model_route_async,
)
from app.services.grok.services.auto_model_stats import get_auto_model_stats_service

router = APIRouter()

_CFG_CHAR_REPLACEMENTS = str.maketrans(
    {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00a0": " ",
        "\u2007": " ",
        "\u202f": " ",
        "\u200b": "",
        "\u200c": "",
        "\u200d": "",
        "\ufeff": "",
    }
)


def _sanitize_proxy_text(value, *, remove_all_spaces: bool = False) -> str:
    text = "" if value is None else str(value)
    text = text.translate(_CFG_CHAR_REPLACEMENTS)
    if remove_all_spaces:
        text = re.sub(r"\s+", "", text)
    else:
        text = text.strip()
    return text.encode("latin-1", errors="ignore").decode("latin-1")


def _sanitize_proxy_config_payload(data: dict) -> dict:
    if not isinstance(data, dict):
        return data
    payload = dict(data)
    app_cfg = payload.get("app")
    if isinstance(app_cfg, dict) and (
        "auth_block_keywords" in app_cfg or "auth_block_status_codes" in app_cfg
    ):
        app_copy = dict(app_cfg)

        if "auth_block_keywords" in app_copy:
            raw_keywords = app_copy.get("auth_block_keywords")
            normalized_keywords: list[str] = []
            if isinstance(raw_keywords, str):
                candidates = raw_keywords.splitlines()
            elif isinstance(raw_keywords, list):
                candidates = raw_keywords
            else:
                candidates = []
            for item in candidates:
                text = _sanitize_proxy_text(item, remove_all_spaces=False).strip()
                if text:
                    normalized_keywords.append(text)
            app_copy["auth_block_keywords"] = normalized_keywords

        if "auth_block_status_codes" in app_copy:
            raw_codes = app_copy.get("auth_block_status_codes")
            normalized_codes: list[int] = []
            if isinstance(raw_codes, str):
                candidates = raw_codes.splitlines()
            elif isinstance(raw_codes, list):
                candidates = raw_codes
            else:
                candidates = []
            for item in candidates:
                text = _sanitize_proxy_text(item, remove_all_spaces=False).strip()
                if not text:
                    continue
                try:
                    code = int(text)
                except (TypeError, ValueError):
                    continue
                if code not in normalized_codes:
                    normalized_codes.append(code)
            app_copy["auth_block_status_codes"] = normalized_codes

        payload["app"] = app_copy

    proxy = payload.get("proxy")
    if not isinstance(proxy, dict):
        return payload

    sanitized_proxy = dict(proxy)
    changed = False

    if "user_agent" in sanitized_proxy:
        raw = sanitized_proxy.get("user_agent")
        val = _sanitize_proxy_text(raw, remove_all_spaces=False)
        if val != raw:
            sanitized_proxy["user_agent"] = val
            changed = True

    if "cf_cookies" in sanitized_proxy:
        raw = sanitized_proxy.get("cf_cookies")
        val = _sanitize_proxy_text(raw, remove_all_spaces=False)
        if val != raw:
            sanitized_proxy["cf_cookies"] = val
            changed = True

    if "cf_clearance" in sanitized_proxy:
        raw = sanitized_proxy.get("cf_clearance")
        val = _sanitize_proxy_text(raw, remove_all_spaces=True)
        if val != raw:
            sanitized_proxy["cf_clearance"] = val
            changed = True

    if changed:
        logger.warning("Sanitized proxy config fields before saving")
        payload["proxy"] = sanitized_proxy
    return payload


@router.get("/verify", dependencies=[Depends(verify_app_key)])
async def admin_verify():
    """验证后台访问密钥（app_key）"""
    return {"status": "success"}


@router.get("/config", dependencies=[Depends(verify_app_key)])
async def get_config():
    """获取当前配置"""
    # 暴露原始配置字典
    return config._config


@router.get("/config/auto-model-stats", dependencies=[Depends(verify_app_key)])
async def get_auto_model_stats():
    """获取自动模型成功率统计与当前排序"""
    route_map = get_auto_model_route_map()
    stats_service = get_auto_model_stats_service()
    stats = await stats_service.get_all_stats(route_map)

    current_order: dict[str, list[str]] = {}
    for route_id in route_map:
        route = await resolve_auto_model_route_async(route_id)
        current_order[route_id] = list(route.models)

    return {
        "prefer_success_rate": bool(config.get("auto_model.prefer_success_rate", False)),
        "current_order": current_order,
        "stats": stats,
    }


@router.post("/config", dependencies=[Depends(verify_app_key)])
async def update_config(data: dict):
    """更新配置"""
    try:
        await config.update(_sanitize_proxy_config_payload(data))
        reload_logging_from_config(
            default_level=os.getenv("LOG_LEVEL", "INFO"),
            json_console=False,
        )
        return {"status": "success", "message": "配置已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/storage", dependencies=[Depends(verify_app_key)])
async def get_storage_mode():
    """获取当前存储模式"""
    storage_type = os.getenv("SERVER_STORAGE_TYPE", "").lower()
    if not storage_type:
        storage = resolve_storage()
        if isinstance(storage, LocalStorage):
            storage_type = "local"
        elif isinstance(storage, RedisStorage):
            storage_type = "redis"
        elif isinstance(storage, SQLStorage):
            storage_type = {
                "mysql": "mysql",
                "mariadb": "mysql",
                "postgres": "pgsql",
                "postgresql": "pgsql",
                "pgsql": "pgsql",
            }.get(storage.dialect, storage.dialect)
    return {"type": storage_type or "local"}
