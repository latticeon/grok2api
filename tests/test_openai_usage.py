import asyncio

import orjson
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from types import SimpleNamespace

from app.core.exceptions import EmptyResponseError, register_exception_handlers
from app.services.grok.services.chat import ChatService, CollectProcessor, StreamProcessor
from app.services.grok.services.responses import ResponsesService
from app.api.v1.chat import router as chat_router
from app.api.v1.response import router as response_router


def _json_line(payload: dict) -> bytes:
    return orjson.dumps(payload)


async def _iter_lines(lines):
    for line in lines:
        yield line


def _decode_sse_json(chunk: str) -> dict:
    assert chunk.startswith("data: ")
    return orjson.loads(chunk[6:])


def _build_test_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(chat_router, prefix="/v1")
    app.include_router(response_router, prefix="/v1")
    return app


def test_collect_processor_returns_estimated_usage(monkeypatch):
    monkeypatch.setattr(
        "app.services.grok.services.chat.get_config",
        lambda key, default=None: 0 if key == "chat.stream_timeout" else [],
    )

    async def _run():
        processor = CollectProcessor("grok-4", prompt_tokens=17)
        result = await processor.process(
            _iter_lines(
                [
                    _json_line(
                        {
                            "result": {
                                "response": {
                                    "llmInfo": {"modelHash": "fp_test"},
                                    "modelResponse": {
                                        "responseId": "resp_collect",
                                        "message": "你好，世界",
                                    },
                                }
                            }
                        }
                    )
                ]
            )
        )
        assert result["usage"]["prompt_tokens"] == 17
        assert result["usage"]["completion_tokens"] > 0
        assert (
            result["usage"]["total_tokens"]
            == result["usage"]["prompt_tokens"] + result["usage"]["completion_tokens"]
        )

    asyncio.run(_run())


def test_stream_processor_final_chunk_has_usage(monkeypatch):
    monkeypatch.setattr(
        "app.services.grok.services.chat.get_config",
        lambda key, default=None: 0 if key == "chat.stream_timeout" else [],
    )

    async def _run():
        processor = StreamProcessor("grok-4", prompt_tokens=11)
        chunks = []
        async for chunk in processor.process(
            _iter_lines(
                [
                    _json_line(
                        {
                            "result": {
                                "response": {
                                    "responseId": "resp_stream",
                                    "llmInfo": {"modelHash": "fp_test"},
                                    "token": "Hello",
                                }
                            }
                        }
                    ),
                    _json_line(
                        {
                            "result": {
                                "response": {
                                    "responseId": "resp_stream",
                                    "token": " world",
                                }
                            }
                        }
                    ),
                ]
            )
        ):
            chunks.append(chunk)

        assert chunks[-1] == "data: [DONE]\n\n"
        final_payload = _decode_sse_json(chunks[-2])
        assert final_payload["choices"][0]["finish_reason"] == "stop"
        assert final_payload["usage"]["prompt_tokens"] == 11
        assert final_payload["usage"]["completion_tokens"] > 0
        assert (
            final_payload["usage"]["total_tokens"]
            == final_payload["usage"]["prompt_tokens"]
            + final_payload["usage"]["completion_tokens"]
        )

    asyncio.run(_run())


def test_stream_processor_empty_response_raises_before_done(monkeypatch):
    monkeypatch.setattr(
        "app.services.grok.services.chat.get_config",
        lambda key, default=None: 0 if key == "chat.stream_timeout" else [],
    )

    async def _run():
        processor = StreamProcessor("grok-4", prompt_tokens=11)
        chunks = []
        with pytest.raises(EmptyResponseError):
            async for chunk in processor.process(
                _iter_lines(
                    [
                        _json_line(
                            {
                                "result": {
                                    "response": {
                                        "responseId": "resp_stream_empty",
                                        "llmInfo": {"modelHash": "fp_test"},
                                    }
                                }
                            }
                        )
                    ]
                )
            ):
                chunks.append(chunk)

        assert "data: [DONE]\n\n" not in chunks

    asyncio.run(_run())


def test_chat_service_stream_retries_empty_response(monkeypatch):
    config_map = {
        "app.thinking": False,
        "app.stream": True,
        "retry.max_retry": 2,
        "chat.stream_timeout": 0,
        "app.filter_tags": [],
    }
    monkeypatch.setattr(
        "app.services.grok.services.chat.get_config",
        lambda key, default=None: config_map.get(key, default),
    )

    class FakeTokenManager:
        def __init__(self):
            self.record_fail_calls = []
            self.consume_calls = []

        async def reload_if_stale(self):
            return None

        async def record_fail(self, token, status_code=401, reason="", threshold=None):
            self.record_fail_calls.append((token, status_code, reason))
            return True

        async def consume(self, token, effort):
            self.consume_calls.append((token, getattr(effort, "value", effort)))
            return True

        async def mark_rate_limited(self, token):
            raise AssertionError("mark_rate_limited should not be called")

        def get_token(self, pool_name, exclude=None):
            return None

    fake_mgr = FakeTokenManager()

    async def fake_get_token_manager():
        return fake_mgr

    async def fake_pick_token(token_mgr, model, tried_tokens):
        if "tok1" not in tried_tokens:
            return "tok1"
        if "tok2" not in tried_tokens:
            return "tok2"
        return None

    async def fake_chat_openai(
        self,
        token,
        model,
        messages,
        stream=None,
        reasoning_effort=None,
        temperature=0.8,
        top_p=0.95,
        tools=None,
        tool_choice=None,
        parallel_tool_calls=True,
        message_assembly=None,
    ):
        if token == "tok1":
            lines = [
                _json_line(
                    {
                        "result": {
                            "response": {
                                "responseId": "resp_empty",
                                "llmInfo": {"modelHash": "fp_empty"},
                            }
                        }
                    }
                )
            ]
        else:
            lines = [
                _json_line(
                    {
                        "result": {
                            "response": {
                                "responseId": "resp_ok",
                                "llmInfo": {"modelHash": "fp_ok"},
                                "token": "Hello",
                            }
                        }
                    }
                )
            ]
        return _iter_lines(lines), True, model, 7

    monkeypatch.setattr(
        "app.services.grok.services.chat.get_token_manager",
        fake_get_token_manager,
    )
    monkeypatch.setattr("app.services.grok.services.chat.pick_token", fake_pick_token)
    monkeypatch.setattr(
        "app.services.grok.services.chat.GrokChatService.chat_openai",
        fake_chat_openai,
    )
    monkeypatch.setattr(
        "app.services.grok.utils.stream.ModelService.get",
        lambda model: SimpleNamespace(cost=SimpleNamespace(value="low")),
    )

    async def _run():
        stream = await ChatService.completions(
            model="grok-4",
            messages=[{"role": "user", "content": "hi"}],
            stream=True,
        )
        chunks = []
        async for chunk in stream:
            chunks.append(chunk)

        assert any('"content":"Hello"' in chunk for chunk in chunks)
        assert chunks[-1] == "data: [DONE]\n\n"
        assert fake_mgr.record_fail_calls == [("tok1", 0, "empty_response")]
        assert fake_mgr.consume_calls == [("tok2", "low")]

    asyncio.run(_run())


def test_responses_stream_completed_event_uses_chat_usage(monkeypatch):
    async def fake_chat_completions(**kwargs):
        async def _gen():
            yield (
                'data: {"id":"chatcmpl_test","object":"chat.completion.chunk","created":1,'
                '"model":"grok-4","choices":[{"index":0,"delta":{"role":"assistant","content":""},'
                '"logprobs":null,"finish_reason":null}]}\n\n'
            )
            yield (
                'data: {"id":"chatcmpl_test","object":"chat.completion.chunk","created":1,'
                '"model":"grok-4","choices":[{"index":0,"delta":{"content":"Hello"},'
                '"logprobs":null,"finish_reason":null}]}\n\n'
            )
            yield (
                'data: {"id":"chatcmpl_test","object":"chat.completion.chunk","created":1,'
                '"model":"grok-4","choices":[{"index":0,"delta":{},'
                '"logprobs":null,"finish_reason":"stop"}],'
                '"usage":{"prompt_tokens":13,"completion_tokens":5,"total_tokens":18,'
                '"prompt_tokens_details":{"cached_tokens":0,"text_tokens":13,"audio_tokens":0,"image_tokens":0},'
                '"completion_tokens_details":{"text_tokens":5,"audio_tokens":0,"reasoning_tokens":0}}}\n\n'
            )
            yield "data: [DONE]\n\n"

        return _gen()

    monkeypatch.setattr(
        "app.services.grok.services.responses.ChatService.completions",
        fake_chat_completions,
    )

    async def _run():
        stream = await ResponsesService.create(
            model="grok-4",
            input_value="hi",
            stream=True,
        )
        chunks = []
        async for chunk in stream:
            chunks.append(chunk)

        completed_chunk = next(
            chunk for chunk in reversed(chunks) if "response.completed" in chunk
        )
        completed = orjson.loads(completed_chunk.split("data: ", 1)[1])
        usage = completed["response"]["usage"]
        assert usage["input_tokens"] == 13
        assert usage["output_tokens"] == 5
        assert usage["total_tokens"] == 18

    asyncio.run(_run())


@pytest.mark.parametrize(
    ("path", "body"),
    [
        (
            "/v1/chat/completions",
            {
                "model": "grok-4",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": False,
            },
        ),
        (
            "/v1/responses",
            {
                "model": "grok-4",
                "input": "hi",
                "stream": False,
            },
        ),
    ],
)
def test_x_message_assembly_header_rejects_invalid_value(monkeypatch, path, body):
    client = TestClient(_build_test_app())

    response = client.post(
        path,
        json=body,
        headers={"X-Message-Assembly": "bad-mode"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "invalid_message_assembly"


@pytest.mark.parametrize(
    ("path", "body", "service_path", "expected_key"),
    [
        (
            "/v1/chat/completions",
            {
                "model": "grok-4",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": False,
            },
            "app.api.v1.chat.ChatService.completions",
            "messages",
        ),
        (
            "/v1/responses",
            {
                "model": "grok-4",
                "input": "hi",
                "stream": False,
            },
            "app.api.v1.response.ResponsesService.create",
            "input_value",
        ),
    ],
)
def test_x_message_assembly_header_overrides_default(monkeypatch, path, body, service_path, expected_key):
    captured = {}

    async def fake_service(**kwargs):
        captured.update(kwargs)
        return {
            "id": "ok",
            "object": "chat.completion",
            "created": 1,
            "model": kwargs.get("model", "grok-4"),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "ok"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
        }

    monkeypatch.setattr(service_path, fake_service)
    client = TestClient(_build_test_app())

    response = client.post(
        path,
        json=body,
        headers={"X-Message-Assembly": "json"},
    )

    assert response.status_code == 200
    assert captured["message_assembly"] == "json"
    assert expected_key in captured


def test_message_extractor_json_assembly_returns_json_string():
    message, file_attachments, image_attachments = MessageExtractor.extract(
        [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
        ],
        assembly="json",
    )

    assert isinstance(message, str)
    payload = orjson.loads(message)
    assert payload == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
    ]
    assert file_attachments == []
    assert image_attachments == []
