"""
Auto model success-rate stats service.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from app.core.logger import logger
from app.core.storage import get_storage

RECENT_STATS_WINDOW_SECONDS = 60 * 60
_MAX_EVENTS_PER_MODEL = 1000


@dataclass(frozen=True)
class AutoModelMetric:
    model_id: str
    attempts: int
    successes: int
    success_rate: float
    updated_at: int


class AutoModelStatsService:
    def __init__(self):
        self._cache: dict[str, dict[str, dict[str, Any]]] | None = None
        self._load_lock = asyncio.Lock()

    async def _ensure_loaded(self) -> None:
        if self._cache is not None:
            return
        async with self._load_lock:
            if self._cache is not None:
                return
        storage = get_storage()
        data = await storage.load_auto_model_stats()
        self._cache = data if isinstance(data, dict) else {}

    async def _reload(self) -> None:
        storage = get_storage()
        data = await storage.load_auto_model_stats()
        self._cache = data if isinstance(data, dict) else {}

    def reset_cache(self) -> None:
        self._cache = None

    def _cutoff(self, now: int | None = None) -> int:
        return int(now or time.time()) - RECENT_STATS_WINDOW_SECONDS

    def _normalize_events(self, stats: dict[str, Any], cutoff: int) -> list[dict[str, int | bool]]:
        events = stats.get("events")
        if not isinstance(events, list):
            return []

        normalized: list[dict[str, int | bool]] = []
        for item in events:
            if not isinstance(item, dict):
                continue
            ts = int(item.get("ts") or 0)
            if ts < cutoff:
                continue
            normalized.append({"ts": ts, "success": bool(item.get("success"))})
        return normalized[-_MAX_EVENTS_PER_MODEL:]

    def _compact_stats(self, data: dict[str, Any], now: int | None = None) -> dict[str, Any]:
        cutoff = self._cutoff(now)
        compacted: dict[str, Any] = {}
        for route_id, route_stats in (data or {}).items():
            if not isinstance(route_stats, dict):
                continue
            compacted_route: dict[str, Any] = {}
            for model_id, stats in route_stats.items():
                if not isinstance(stats, dict):
                    continue
                events = self._normalize_events(stats, cutoff)
                updated_at = int(stats.get("updated_at") or 0)
                if events or updated_at >= cutoff:
                    compacted_route[model_id] = {
                        "events": events,
                        "updated_at": updated_at,
                    }
            if compacted_route:
                compacted[route_id] = compacted_route
        return compacted

    async def record_attempt(self, route_id: str, model_id: str, success: bool) -> None:
        storage = get_storage()
        try:
            async with storage.acquire_lock("auto_model_stats_save", timeout=10):
                data = await storage.load_auto_model_stats()
                latest = data if isinstance(data, dict) else {}
                now = int(time.time())
                latest = self._compact_stats(latest, now)
                route_stats = latest.setdefault(route_id, {})
                model_stats = route_stats.setdefault(
                    model_id,
                    {"events": [], "updated_at": now},
                )
                events = self._normalize_events(model_stats, self._cutoff(now))
                events.append({"ts": now, "success": bool(success)})
                model_stats["events"] = events[-_MAX_EVENTS_PER_MODEL:]
                model_stats["updated_at"] = now
                await storage.save_auto_model_stats(latest)
                self._cache = latest
        except Exception as e:
            logger.warning(f"Failed to persist auto model stats: {e}")

    async def get_route_metrics(
        self,
        route_id: str,
        configured_models: list[str] | tuple[str, ...],
    ) -> list[AutoModelMetric]:
        await self._reload()
        route_stats = (self._cache or {}).get(route_id, {})
        metrics: list[AutoModelMetric] = []
        cutoff = self._cutoff()
        for model_id in configured_models:
            stats = route_stats.get(model_id, {})
            events = self._normalize_events(stats, cutoff) if isinstance(stats, dict) else []
            attempts = len(events)
            successes = sum(1 for item in events if item["success"])
            success_rate = (successes / attempts) if attempts > 0 else 0.0
            metrics.append(
                AutoModelMetric(
                    model_id=model_id,
                    attempts=attempts,
                    successes=successes,
                    success_rate=success_rate,
                    updated_at=int(stats.get("updated_at") or 0),
                )
            )
        return metrics

    async def order_models(
        self,
        route_id: str,
        configured_models: list[str] | tuple[str, ...],
        prefer_success_rate: bool,
    ) -> tuple[str, ...]:
        models = list(configured_models)
        if not prefer_success_rate or len(models) <= 1:
            return tuple(models)
        metrics = await self.get_route_metrics(route_id, models)
        metric_map = {item.model_id: item for item in metrics}
        indexed = list(enumerate(models))
        indexed.sort(
            key=lambda item: (
                -(metric_map[item[1]].success_rate if item[1] in metric_map else 0.0),
                -(metric_map[item[1]].successes if item[1] in metric_map else 0),
                item[0],
            )
        )
        return tuple(model for _, model in indexed)

    async def get_all_stats(self, route_models: dict[str, tuple[str, ...]]) -> dict[str, Any]:
        await self._reload()
        result: dict[str, Any] = {}
        for route_id, models in route_models.items():
            metrics = await self.get_route_metrics(route_id, models)
            result[route_id] = [
                {
                    "model_id": item.model_id,
                    "attempts": item.attempts,
                    "successes": item.successes,
                    "success_rate": item.success_rate,
                    "updated_at": item.updated_at,
                }
                for item in metrics
            ]
        return result


_service = AutoModelStatsService()


def get_auto_model_stats_service() -> AutoModelStatsService:
    return _service


__all__ = [
    "AutoModelMetric",
    "AutoModelStatsService",
    "get_auto_model_stats_service",
]
