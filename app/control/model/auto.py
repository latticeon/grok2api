"""Runtime helpers for auto model sets and per-model success-rate stats."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Literal

from app.platform.config.snapshot import get_config
from app.control.model.registry import resolve

AutoModelName = Literal["grok-auto", "grok-auto-lite"]

_AUTO_MODEL_KEYS: dict[str, str] = {
    "grok-auto": "auto_models.grok_auto",
    "grok-auto-lite": "auto_models.grok_auto_lite",
}


@dataclass(slots=True)
class AutoModelStat:
    total: int = 0
    success: int = 0
    failed: int = 0
    updated_at: int = 0
    attempts: list[tuple[int, bool]] = field(default_factory=list)

    def record(self, ok: bool) -> None:
        now = int(time())
        self.total += 1
        if ok:
            self.success += 1
        else:
            self.failed += 1
        self.updated_at = now
        self.attempts.append((now, ok))
        cutoff = now - 3600
        self.attempts = [item for item in self.attempts if item[0] >= cutoff]

    def success_rate(self) -> float:
        total = self.success + self.failed
        return (self.success / total) if total else 0.0

    def success_rate_hour(self) -> float:
        total = 0
        ok = 0
        cutoff = int(time()) - 3600
        for ts, succeeded in self.attempts:
            if ts < cutoff:
                continue
            total += 1
            if succeeded:
                ok += 1
        return (ok / total) if total else 0.0


@dataclass(slots=True)
class TargetModelStat:
    attempts: list[tuple[int, bool]] = field(default_factory=list)

    def record(self, ok: bool) -> None:
        now = int(time())
        self.attempts.append((now, ok))
        cutoff = now - 3600
        self.attempts = [item for item in self.attempts if item[0] >= cutoff]

    def success_rate_hour(self) -> float:
        cutoff = int(time()) - 3600
        total = 0
        ok = 0
        for ts, succeeded in self.attempts:
            if ts < cutoff:
                continue
            total += 1
            if succeeded:
                ok += 1
        return (ok / total) if total else 0.0

    def total_hour(self) -> int:
        cutoff = int(time()) - 3600
        return sum(1 for ts, _ in self.attempts if ts >= cutoff)


_STATS: dict[str, AutoModelStat] = {
    "grok-auto": AutoModelStat(),
    "grok-auto-lite": AutoModelStat(),
}
_TARGET_STATS: dict[str, TargetModelStat] = {}

_TARGET_BASELINE: dict[str, float] = {}


def is_auto_model(model_name: str) -> bool:
    return model_name in _AUTO_MODEL_KEYS


def auto_models_for(model_name: str) -> list[str]:
    cfg = get_config()
    raw = cfg.get_str(_AUTO_MODEL_KEYS.get(model_name, ""), "")
    models = [line.strip() for line in raw.splitlines() if line.strip()]
    result: list[str] = []
    for item in models:
        if is_auto_model(item):
            continue
        try:
            spec = resolve(item)
        except Exception:
            continue
        if spec.is_chat():
            result.append(spec.model_name)
    return result


def auto_model_success_rate_routing() -> bool:
    return get_config().get_bool("auto_models.success_rate_routing", False)


def snapshot_auto_model_stats() -> dict[str, dict]:
    return {
        name: {
            "total": stat.total,
            "success": stat.success,
            "failed": stat.failed,
            "success_rate": round(stat.success_rate(), 4),
            "success_rate_hour": round(stat.success_rate_hour(), 4),
            "updated_at": stat.updated_at,
        }
        for name, stat in _STATS.items()
    }


def snapshot_auto_model_target_stats() -> dict[str, dict]:
    names: set[str] = set(_TARGET_STATS)
    for model_name in _AUTO_MODEL_KEYS:
        names.update(auto_models_for(model_name))
    return {
        name: {
            "success_rate_hour": round(_model_score(name), 4),
            "actual_success_rate_hour": round(
                _TARGET_STATS.get(name, TargetModelStat()).success_rate_hour(), 4
            ),
            "total_hour": _TARGET_STATS.get(name, TargetModelStat()).total_hour(),
        }
        for name in sorted(names)
    }


def record_auto_model_attempt(model_name: str, ok: bool) -> None:
    stat = _STATS.get(model_name)
    if stat is None:
        return
    stat.record(ok)


def record_target_model_attempt(model_name: str, ok: bool) -> None:
    stat = _TARGET_STATS.setdefault(model_name, TargetModelStat())
    stat.record(ok)
    current = stat.success_rate_hour()
    baseline = _TARGET_BASELINE.get(model_name)
    if baseline is None:
        _TARGET_BASELINE[model_name] = current
    else:
        _TARGET_BASELINE[model_name] = baseline * 0.7 + current * 0.3


def _model_score(model_name: str) -> float:
    stat = _TARGET_STATS.get(model_name)
    if stat is not None and stat.total_hour() > 0:
        return stat.success_rate_hour()
    baseline = _TARGET_BASELINE.get(model_name)
    if baseline is not None:
        return baseline
    return 1.0


def order_auto_model_targets(model_names: list[str], *, by_success_rate: bool) -> list[str]:
    if not by_success_rate:
        return model_names
    indexed = list(enumerate(model_names))
    indexed.sort(key=lambda item: (-_model_score(item[1]), item[0]))
    return [name for _, name in indexed]


def resolve_auto_model_target(model_name: str) -> tuple[list[str], bool]:
    return auto_models_for(model_name), auto_model_success_rate_routing()


__all__ = [
    "AutoModelStat",
    "auto_models_for",
    "auto_model_success_rate_routing",
    "is_auto_model",
    "order_auto_model_targets",
    "record_auto_model_attempt",
    "record_target_model_attempt",
    "resolve_auto_model_target",
    "snapshot_auto_model_stats",
    "snapshot_auto_model_target_stats",
]
