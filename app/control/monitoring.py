"""In-memory monitor for OpenAI chat requests."""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any


class ChatRequestMonitor:
    def __init__(self) -> None:
        self._enabled = False
        self._records: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def start(self) -> dict[str, Any]:
        async with self._lock:
            self._enabled = True
            return self.status_unlocked()

    async def stop(self) -> dict[str, Any]:
        async with self._lock:
            self._enabled = False
            return self.status_unlocked()

    async def clear(self) -> dict[str, Any]:
        async with self._lock:
            self._records.clear()
            return self.status_unlocked()

    async def status(self) -> dict[str, Any]:
        async with self._lock:
            return self.status_unlocked()

    def status_unlocked(self) -> dict[str, Any]:
        return {
            "recording": self._enabled,
            "count": len(self._records),
        }

    @staticmethod
    def _preview(text: Any, *, limit: int = 160) -> str:
        value = "" if text is None else str(text)
        value = " ".join(value.split())
        if len(value) <= limit:
            return value
        return value[: max(0, limit - 1)] + "…"

    async def append(self, record: dict[str, Any]) -> None:
        async with self._lock:
            item = dict(record)
            item.setdefault("id", uuid.uuid4().hex)
            item.setdefault("created_at", time.time())
            self._records.append(item)

    async def list(self) -> dict[str, Any]:
        async with self._lock:
            return {
                **self.status_unlocked(),
                "records": [
                    {
                        "id": item["id"],
                        "created_at": item["created_at"],
                        "method": item.get("method", ""),
                        "path": item.get("path", ""),
                        "token": item.get("token", ""),
                        "status_code": item.get("response_status", 0),
                        "duration_ms": item.get("duration_ms", 0),
                        "request_body_size": item.get("request_body_size", 0),
                        "response_body_size": item.get("response_body_size", 0),
                        "ai_content": self._preview(item.get("ai_content", "")),
                    }
                    for item in reversed(self._records)
                ],
            }

    async def detail(self, record_id: str) -> dict[str, Any] | None:
        async with self._lock:
            for item in self._records:
                if item["id"] == record_id:
                    return dict(item)
        return None


monitor = ChatRequestMonitor()


__all__ = ["monitor", "ChatRequestMonitor"]
