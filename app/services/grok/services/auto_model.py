"""
Special auto model routing.
"""

from dataclasses import dataclass
import re
from typing import Any

from app.core.config import get_config
from app.core.exceptions import ValidationException
from app.services.grok.services.model import ModelService


AUTO_MODEL_ID = "grok-auto"
AUTO_LITE_MODEL_ID = "grok-auto-lite"

_AUTO_CONFIG_KEYS = {
    AUTO_MODEL_ID: "auto_model.grok_auto_models",
    AUTO_LITE_MODEL_ID: "auto_model.grok_auto_lite_models",
}


@dataclass(frozen=True)
class AutoModelRoute:
    requested_model: str
    models: tuple[str, ...]

    @property
    def enabled(self) -> bool:
        return self.requested_model in _AUTO_CONFIG_KEYS

    def model_for_attempt(self, attempt: int) -> str:
        if not self.models:
            return self.requested_model
        return self.models[attempt % len(self.models)]

    def attempt_budget(self, configured_attempts: int) -> int:
        return max(1, int(configured_attempts or 1))


def is_auto_model(model_id: str) -> bool:
    return model_id in _AUTO_CONFIG_KEYS


def _coerce_model_list(value: Any) -> list[str]:
    if isinstance(value, str):
        items = re.split(r"[\r\n,]+", value)
    elif isinstance(value, (list, tuple)):
        items = value
    else:
        items = []

    return [str(item).strip() for item in items if str(item).strip()]


def _validate_concrete_models(requested_model: str, models: list[str]) -> tuple[str, ...]:
    if not models:
        raise ValidationException(
            message=f"No models configured for {requested_model}.",
            param="model",
            code="auto_model_empty",
        )

    invalid: list[str] = []
    for model_id in models:
        model_info = ModelService.get(model_id)
        if (
            not model_info
            or is_auto_model(model_id)
            or model_info.is_image
            or model_info.is_image_edit
            or model_info.is_video
        ):
            invalid.append(model_id)

    if invalid:
        raise ValidationException(
            message=(
                f"Invalid models configured for {requested_model}: "
                f"{', '.join(invalid)}"
            ),
            param="model",
            code="auto_model_invalid",
        )

    return tuple(models)


def resolve_auto_model_route(model_id: str) -> AutoModelRoute:
    config_key = _AUTO_CONFIG_KEYS.get(model_id)
    if not config_key:
        return AutoModelRoute(requested_model=model_id, models=(model_id,))

    models = _coerce_model_list(get_config(config_key, []))
    return AutoModelRoute(
        requested_model=model_id,
        models=_validate_concrete_models(model_id, models),
    )


__all__ = [
    "AUTO_LITE_MODEL_ID",
    "AUTO_MODEL_ID",
    "AutoModelRoute",
    "is_auto_model",
    "resolve_auto_model_route",
]
