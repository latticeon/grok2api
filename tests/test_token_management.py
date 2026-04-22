import asyncio

from app.core import storage as storage_module
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
