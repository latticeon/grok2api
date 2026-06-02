"""Admin model/token testing endpoints."""

from __future__ import annotations

from time import perf_counter
from typing import Any

import orjson
from fastapi import APIRouter
from pydantic import BaseModel

from app.control.model.enums import Capability
from app.control.model import registry as model_registry
from app.dataplane.proxy import get_proxy_runtime
from app.dataplane.proxy.adapters.headers import build_http_headers
from app.dataplane.proxy.adapters.session import ResettableSession, build_session_kwargs
from app.dataplane.reverse.protocol.xai_chat import (
    StreamAdapter,
    build_chat_payload,
    classify_line,
)
from app.dataplane.reverse.runtime.endpoint_table import CHAT
from app.platform.config.snapshot import get_config
from app.platform.errors import UpstreamError, ValidationError

router = APIRouter(prefix="/testing", tags=["Admin - Testing"])


class TokenTestRequest(BaseModel):
    token: str
    model: str
    message: str = "你好"


class ModelBatchTestRequest(BaseModel):
    token: str
    models: list[str]
    message: str = "你好"


def _headers_to_dict(headers: Any) -> dict[str, str]:
    if headers is None:
        return {}
    try:
        return {str(k): str(v) for k, v in headers.items()}
    except Exception:
        return {}


def _chat_content(adapter: StreamAdapter) -> str:
    parts = list(adapter.text_buf)
    if adapter.image_urls:
        parts.extend(url for url, _ in adapter.image_urls)
    refs = adapter.references_suffix()
    if refs:
        parts.append(refs)
    return "".join(parts)


async def _response_body_text(response: Any, *, limit: int = 4000) -> str:
    """Best-effort body reader for curl_cffi streaming responses."""
    try:
        body = response.content or b""
    except Exception:
        body = b""
    if not body:
        try:
            reader = getattr(response, "aread", None)
            if callable(reader):
                body = await reader()
        except Exception:
            body = b""
    if not body:
        return ""
    return body.decode("utf-8", "replace")[:limit]


async def run_single_token_chat_test(
    *,
    token: str,
    model: str,
    message: str,
) -> dict[str, Any]:
    spec = model_registry.get(model)
    if spec is None or not spec.enabled or not spec.is_chat() or spec.is_auto_model():
        raise ValidationError("请选择一个真实聊天模型", param="model")
    token = str(token or "").strip()
    if not token:
        raise ValidationError("Token 不能为空", param="token")
    message = str(message or "").strip() or "你好"

    proxy = await get_proxy_runtime()
    lease = await proxy.acquire()
    payload = build_chat_payload(message=message, mode_id=spec.mode_id)
    payload_bytes = orjson.dumps(payload)
    headers = build_http_headers(
        token,
        content_type="application/json",
        origin="https://grok.com",
        referer="https://grok.com/",
        lease=lease,
    )
    session_kwargs = build_session_kwargs(lease=lease)
    timeout_s = get_config().get_float("chat.timeout", 120.0)

    adapter = StreamAdapter()
    raw_lines: list[str] = []
    status_code = 0
    response_headers: dict[str, str] = {}
    start = perf_counter()
    try:
        async with ResettableSession(**session_kwargs) as session:
            response = await session.post(
                CHAT,
                headers=headers,
                data=payload_bytes,
                timeout=timeout_s,
                stream=True,
            )
            status_code = int(response.status_code)
            response_headers = _headers_to_dict(response.headers)
            if response.status_code != 200:
                body = await _response_body_text(response)
                raw_lines.append(body)
                raise UpstreamError(
                    f"Chat upstream returned {response.status_code}",
                    status=response.status_code,
                    body=body,
                )

            async for line in response.aiter_lines():
                raw_line = line.decode("utf-8", "replace") if isinstance(line, bytes) else str(line)
                raw_lines.append(raw_line)
                event_type, data = classify_line(raw_line)
                if event_type == "done":
                    break
                if event_type != "data" or not data:
                    continue
                ended = False
                for ev in adapter.feed(data):
                    if ev.kind == "soft_stop":
                        ended = True
                        break
                if ended:
                    break
    except UpstreamError as exc:
        duration_ms = round((perf_counter() - start) * 1000, 2)
        return {
            "ok": False,
            "status_code": getattr(exc, "status", status_code) or status_code,
            "error": str(exc),
            "request_body": payload,
            "request_headers": headers,
            "response_body": "\n".join(raw_lines),
            "response_headers": response_headers,
            "ai_content": _chat_content(adapter),
            "duration_ms": duration_ms,
        }

    duration_ms = round((perf_counter() - start) * 1000, 2)
    ai_content = _chat_content(adapter)
    ok = bool(ai_content.strip() or adapter.thinking_buf or adapter.image_urls)
    return {
        "ok": ok,
        "status_code": status_code,
        "error": "" if ok else "empty_response",
        "request_body": payload,
        "request_headers": headers,
        "response_body": "\n".join(raw_lines),
        "response_headers": response_headers,
        "ai_content": ai_content,
        "duration_ms": duration_ms,
    }


@router.get("/chat-models")
async def list_chat_models():
    return {
        "models": [
            {"id": m.model_name, "name": m.public_name}
            for m in model_registry.list_by_capability(Capability.CHAT)
            if not m.is_auto_model()
        ]
    }


@router.post("/token")
async def test_token(req: TokenTestRequest):
    return await run_single_token_chat_test(
        token=req.token,
        model=req.model,
        message=req.message,
    )


@router.post("/models")
async def test_models(req: ModelBatchTestRequest):
    token = str(req.token or "").strip()
    if not token:
        raise ValidationError("Token 不能为空", param="token")
    models = [str(model).strip() for model in req.models if str(model).strip()]
    if not models:
        raise ValidationError("请选择至少一个模型", param="models")

    results: list[dict[str, Any]] = []
    ok = fail = 0

    for model in models:
        result = await run_single_token_chat_test(
            token=token,
            model=model,
            message=req.message,
        )
        spec = model_registry.get(model)
        item = {
            "model": model,
            "name": spec.public_name if spec else model,
            **result,
        }
        if result.get("ok"):
            ok += 1
        else:
            fail += 1
        results.append(item)

    return {
        "status": "success",
        "summary": {"total": len(results), "ok": ok, "fail": fail},
        "results": results,
    }


__all__ = ["router", "run_single_token_chat_test"]
