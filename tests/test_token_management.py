import asyncio

from app.core import storage as storage_module
from app.core.exceptions import UpstreamException
from app.services.reverse.app_chat import AppChatReverse
from app.services.token.manager import TokenManager
from app.services.token.models import TokenInfo, TokenStatus
from app.services.token.pool import TokenPool


def test_mark_rate_limited_does_not_persist_cooling_state():
    async def _run():
        manager = TokenManager()
        pool = TokenPool("ssoBasic")
        token = TokenInfo(token="tok_active", status=TokenStatus.ACTIVE, quota=80)
        pool.add(token)
        manager.pools[pool.name] = pool

        ok = await manager.mark_rate_limited("tok_active")

        assert ok is True
        assert token.status == TokenStatus.ACTIVE
        assert token.quota == 80
        assert manager._dirty_tokens == {}
        assert manager._dirty_deletes == set()

    asyncio.run(_run())


def test_local_storage_allows_saving_empty_token_payload(tmp_path, monkeypatch):
    async def _run():
        token_file = tmp_path / "token.json"
        monkeypatch.setattr(storage_module, "TOKEN_FILE", token_file)

        storage = storage_module.LocalStorage()
        original = {
            "ssoBasic": [
                {
                    "token": "tok_to_delete",
                    "status": "active",
                    "quota": 80,
                }
            ]
        }

        await storage.save_tokens(original)
        assert await storage.load_tokens() == original

        await storage.save_tokens({})

        assert await storage.load_tokens() == {}

    asyncio.run(_run())


def test_app_chat_marks_configured_400_auth_block_as_expired(monkeypatch):
    async def _run():
        calls = []

        class DummyManager:
            async def record_fail(self, token, status_code=401, reason="", threshold=None):
                calls.append(
                    {
                        "token": token,
                        "status_code": status_code,
                        "reason": reason,
                        "threshold": threshold,
                    }
                )
                return True

        class DummySession:
            async def close(self):
                return None

        monkeypatch.setattr(
            "app.services.reverse.app_chat.get_config",
            lambda key, default=None: {
                "proxy.base_proxy_url": "",
                "proxy.browser": "chrome",
                "chat.timeout": 1,
                "video.timeout": 1,
                "image.timeout": 1,
                "app.disable_memory": False,
                "app.temporary": False,
                "app.custom_instruction": "",
            }.get(key, default),
        )
        monkeypatch.setattr(
            "app.services.reverse.utils.auth_detection.get_config",
            lambda key, default=None: {
                "app.auth_block_status_codes": [401, 403, 400],
                "app.auth_block_keywords": ["WKE=account:email-domain-rejected"],
            }.get(key, default),
        )
        monkeypatch.setattr(
            "app.services.reverse.app_chat.retry_on_status",
            lambda func, *args, **kwargs: func(),
        )
        monkeypatch.setattr(
            "app.services.token.service.TokenService._get_manager",
            staticmethod(lambda: DummyManager()),
        )

        async def _record_fail(*args, **kwargs):
            raise AssertionError("non-expired path should not be used")

        monkeypatch.setattr(
            "app.services.token.service.TokenService.record_fail",
            staticmethod(_record_fail),
        )

        async def _post(*args, **kwargs):
            class DummyResponse:
                status_code = 400
                headers = {"content-type": "application/json"}
                content = b'{"error":{"message":"WKE=account:email-domain-rejected"}}'

                async def text(self):
                    return self.content.decode("utf-8")

            return DummyResponse()

        session = DummySession()
        session.post = _post

        try:
            await AppChatReverse.request(
                session,
                "tok_blocked",
                message="hello",
                model="grok-4",
            )
        except UpstreamException:
            pass
        else:
            raise AssertionError("expected UpstreamException")

        assert calls == [
            {
                "token": "tok_blocked",
                "status_code": 400,
                "reason": "app_chat_error_400",
                "threshold": 1,
            }
        ]

    asyncio.run(_run())
