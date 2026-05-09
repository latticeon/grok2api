"""
Grok 模型管理服务
"""

from enum import Enum
from typing import Optional, Tuple, List
from pydantic import BaseModel, Field

from app.core.exceptions import ValidationException


class Tier(str, Enum):
    """模型档位"""

    BASIC = "basic"
    SUPER = "super"
    HEAVY = "heavy"


class Cost(str, Enum):
    """计费类型"""

    LOW = "low"
    HIGH = "high"


class ModelInfo(BaseModel):
    """模型信息"""

    model_id: str
    grok_model: str
    model_mode: str
    tier: Tier = Field(default=Tier.BASIC)
    cost: Cost = Field(default=Cost.LOW)
    display_name: str
    description: str = ""
    is_image: bool = False
    is_image_edit: bool = False
    is_video: bool = False
    prefer_best: bool = False


class ModelService:
    """模型管理服务"""

    MODELS = [
        ModelInfo(
            model_id="grok-3",
            grok_model="grok-3",
            model_mode="MODEL_MODE_GROK_3",
            tier=Tier.BASIC,
            cost=Cost.LOW,
            display_name="GROK-3",
            is_image=False,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-3-mini",
            grok_model="grok-3",
            model_mode="MODEL_MODE_GROK_3_MINI_THINKING",
            tier=Tier.BASIC,
            cost=Cost.LOW,
            display_name="GROK-3-MINI",
            is_image=False,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-3-thinking",
            grok_model="grok-3",
            model_mode="MODEL_MODE_GROK_3_THINKING",
            tier=Tier.BASIC,
            cost=Cost.LOW,
            display_name="GROK-3-THINKING",
            is_image=False,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-4",
            grok_model="grok-4",
            model_mode="MODEL_MODE_GROK_4",
            tier=Tier.BASIC,
            cost=Cost.LOW,
            display_name="GROK-4",
            is_image=False,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-4-thinking",
            grok_model="grok-4",
            model_mode="MODEL_MODE_GROK_4_THINKING",
            tier=Tier.BASIC,
            cost=Cost.LOW,
            display_name="GROK-4-THINKING",
            is_image=False,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-4-heavy",
            grok_model="grok-4",
            model_mode="MODEL_MODE_HEAVY",
            tier=Tier.SUPER,
            cost=Cost.HIGH,
            display_name="GROK-4-HEAVY",
            is_image=False,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-4.1-mini",
            grok_model="grok-4-1-thinking-1129",
            model_mode="MODEL_MODE_GROK_4_1_MINI_THINKING",
            tier=Tier.BASIC,
            cost=Cost.LOW,
            display_name="GROK-4.1-MINI",
            is_image=False,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-4.1-fast",
            grok_model="grok-4-1-thinking-1129",
            model_mode="MODEL_MODE_FAST",
            tier=Tier.BASIC,
            cost=Cost.LOW,
            display_name="GROK-4.1-FAST",
            is_image=False,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-4.1-expert",
            grok_model="grok-4-1-thinking-1129",
            model_mode="MODEL_MODE_EXPERT",
            tier=Tier.BASIC,
            cost=Cost.HIGH,
            display_name="GROK-4.1-EXPERT",
            is_image=False,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-4.1-thinking",
            grok_model="grok-4-1-thinking-1129",
            model_mode="MODEL_MODE_GROK_4_1_THINKING",
            tier=Tier.BASIC,
            cost=Cost.HIGH,
            display_name="GROK-4.1-THINKING",
            is_image=False,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-4.20-beta",
            grok_model="grok-420",
            model_mode="MODEL_MODE_GROK_420",
            tier=Tier.BASIC,
            cost=Cost.LOW,
            display_name="GROK-4.20-BETA",
            is_image=False,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-4.20-0309-non-reasoning",
            grok_model="grok-420",
            model_mode="MODEL_MODE_FAST",
            tier=Tier.BASIC,
            cost=Cost.LOW,
            display_name="Grok 4.20 0309 Non-Reasoning",
            is_image=False,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-4.20-0309",
            grok_model="grok-420",
            model_mode="MODEL_MODE_AUTO_ID",
            tier=Tier.SUPER,
            cost=Cost.HIGH,
            display_name="Grok 4.20 0309",
            is_image=False,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-4.20-0309-reasoning",
            grok_model="grok-420",
            model_mode="MODEL_MODE_EXPERT",
            tier=Tier.SUPER,
            cost=Cost.HIGH,
            display_name="Grok 4.20 0309 Reasoning",
            is_image=False,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-4.20-0309-non-reasoning-super",
            grok_model="grok-420",
            model_mode="MODEL_MODE_FAST",
            tier=Tier.SUPER,
            cost=Cost.HIGH,
            display_name="Grok 4.20 0309 Non-Reasoning Super",
            is_image=False,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-4.20-0309-super",
            grok_model="grok-420",
            model_mode="MODEL_MODE_AUTO_ID",
            tier=Tier.SUPER,
            cost=Cost.HIGH,
            display_name="Grok 4.20 0309 Super",
            is_image=False,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-4.20-0309-reasoning-super",
            grok_model="grok-420",
            model_mode="MODEL_MODE_EXPERT",
            tier=Tier.SUPER,
            cost=Cost.HIGH,
            display_name="Grok 4.20 0309 Reasoning Super",
            is_image=False,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-4.20-0309-non-reasoning-heavy",
            grok_model="grok-420",
            model_mode="MODEL_MODE_FAST",
            tier=Tier.HEAVY,
            cost=Cost.HIGH,
            display_name="Grok 4.20 0309 Non-Reasoning Heavy",
            is_image=False,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-4.20-0309-heavy",
            grok_model="grok-420",
            model_mode="MODEL_MODE_AUTO_ID",
            tier=Tier.HEAVY,
            cost=Cost.HIGH,
            display_name="Grok 4.20 0309 Heavy",
            is_image=False,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-4.20-0309-reasoning-heavy",
            grok_model="grok-420",
            model_mode="MODEL_MODE_EXPERT",
            tier=Tier.HEAVY,
            cost=Cost.HIGH,
            display_name="Grok 4.20 0309 Reasoning Heavy",
            is_image=False,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-4.20-multi-agent-0309",
            grok_model="grok-420",
            model_mode="MODEL_MODE_HEAVY",
            tier=Tier.HEAVY,
            cost=Cost.HIGH,
            display_name="Grok 4.20 Multi-Agent 0309",
            is_image=False,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-4.20-fast",
            grok_model="grok-420",
            model_mode="MODEL_MODE_FAST",
            tier=Tier.BASIC,
            cost=Cost.LOW,
            display_name="Grok 4.20 Fast",
            is_image=False,
            is_image_edit=False,
            is_video=False,
            prefer_best=True,
        ),
        ModelInfo(
            model_id="grok-4.20-auto",
            grok_model="grok-420",
            model_mode="MODEL_MODE_AUTO_ID",
            tier=Tier.SUPER,
            cost=Cost.HIGH,
            display_name="Grok 4.20 Auto",
            is_image=False,
            is_image_edit=False,
            is_video=False,
            prefer_best=True,
        ),
        ModelInfo(
            model_id="grok-4.20-expert",
            grok_model="grok-420",
            model_mode="MODEL_MODE_EXPERT",
            tier=Tier.SUPER,
            cost=Cost.HIGH,
            display_name="Grok 4.20 Expert",
            is_image=False,
            is_image_edit=False,
            is_video=False,
            prefer_best=True,
        ),
        ModelInfo(
            model_id="grok-4.20-heavy",
            grok_model="grok-420",
            model_mode="MODEL_MODE_HEAVY",
            tier=Tier.HEAVY,
            cost=Cost.HIGH,
            display_name="Grok 4.20 Heavy",
            is_image=False,
            is_image_edit=False,
            is_video=False,
            prefer_best=True,
        ),
        ModelInfo(
            model_id="grok-4.3-beta",
            grok_model="grok-420-computer-use-sa",
            model_mode="MODEL_MODE_GROK_4_3",
            tier=Tier.SUPER,
            cost=Cost.HIGH,
            display_name="Grok 4.3 Beta",
            is_image=False,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-imagine-image-lite",
            grok_model="grok-3",
            model_mode="MODEL_MODE_FAST",
            tier=Tier.BASIC,
            cost=Cost.HIGH,
            display_name="Grok Imagine Image Lite",
            description="Image generation model",
            is_image=True,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-imagine-image",
            grok_model="grok-3",
            model_mode="MODEL_MODE_AUTO_ID",
            tier=Tier.SUPER,
            cost=Cost.HIGH,
            display_name="Grok Imagine Image",
            description="Image generation model",
            is_image=True,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-imagine-image-pro",
            grok_model="grok-3",
            model_mode="MODEL_MODE_AUTO_ID",
            tier=Tier.SUPER,
            cost=Cost.HIGH,
            display_name="Grok Imagine Image Pro",
            description="Image generation model",
            is_image=True,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-imagine-image-edit",
            grok_model="imagine-image-edit",
            model_mode="MODEL_MODE_AUTO_ID",
            tier=Tier.SUPER,
            cost=Cost.HIGH,
            display_name="Grok Imagine Image Edit",
            description="Image edit model",
            is_image=False,
            is_image_edit=True,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-imagine-video",
            grok_model="grok-3",
            model_mode="MODEL_MODE_AUTO_ID",
            tier=Tier.SUPER,
            cost=Cost.HIGH,
            display_name="Grok Imagine Video",
            description="Video generation model",
            is_image=False,
            is_image_edit=False,
            is_video=True,
        ),
        ModelInfo(
            model_id="grok-imagine-1.0-fast",
            grok_model="grok-3",
            model_mode="MODEL_MODE_FAST",
            tier=Tier.BASIC,
            cost=Cost.HIGH,
            display_name="Grok Image Fast",
            description="Imagine waterfall image generation model for chat completions",
            is_image=True,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-imagine-1.0",
            grok_model="grok-3",
            model_mode="MODEL_MODE_FAST",
            tier=Tier.BASIC,
            cost=Cost.HIGH,
            display_name="Grok Image",
            description="Image generation model",
            is_image=True,
            is_image_edit=False,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-imagine-1.0-edit",
            grok_model="imagine-image-edit",
            model_mode="MODEL_MODE_FAST",
            tier=Tier.BASIC,
            cost=Cost.HIGH,
            display_name="Grok Image Edit",
            description="Image edit model",
            is_image=False,
            is_image_edit=True,
            is_video=False,
        ),
        ModelInfo(
            model_id="grok-imagine-1.0-video",
            grok_model="grok-3",
            model_mode="MODEL_MODE_FAST",
            tier=Tier.BASIC,
            cost=Cost.HIGH,
            display_name="Grok Video",
            description="Video generation model",
            is_image=False,
            is_image_edit=False,
            is_video=True,
        ),
    ]

    _map = {m.model_id: m for m in MODELS}
    _pool_by_tier = {
        Tier.BASIC: "ssoBasic",
        Tier.SUPER: "ssoSuper",
        Tier.HEAVY: "ssoHeavy",
    }
    _pool_candidates = {
        Tier.BASIC: ["ssoBasic", "ssoSuper", "ssoHeavy"],
        Tier.SUPER: ["ssoSuper", "ssoHeavy"],
        Tier.HEAVY: ["ssoHeavy"],
    }
    _prefer_best_candidates = {
        Tier.BASIC: ["ssoHeavy", "ssoSuper", "ssoBasic"],
        Tier.SUPER: ["ssoHeavy", "ssoSuper"],
        Tier.HEAVY: ["ssoHeavy"],
    }

    @classmethod
    def get(cls, model_id: str) -> Optional[ModelInfo]:
        """获取模型信息"""
        return cls._map.get(model_id)

    @classmethod
    def list(cls) -> list[ModelInfo]:
        """获取所有模型"""
        return list(cls._map.values())

    @classmethod
    def valid(cls, model_id: str) -> bool:
        """模型是否有效"""
        return model_id in cls._map

    @classmethod
    def to_grok(cls, model_id: str) -> Tuple[str, str]:
        """转换为 Grok 参数"""
        model = cls.get(model_id)
        if not model:
            raise ValidationException(f"Invalid model ID: {model_id}")
        return model.grok_model, model.model_mode

    @classmethod
    def pool_for_model(cls, model_id: str) -> str:
        """根据模型选择 Token 池"""
        model = cls.get(model_id)
        if model:
            return cls._pool_by_tier.get(model.tier, "ssoBasic")
        return "ssoBasic"

    @classmethod
    def pool_candidates_for_model(cls, model_id: str) -> List[str]:
        """按优先级返回可用 Token 池列表"""
        model = cls.get(model_id)
        if model and model.prefer_best:
            return list(cls._prefer_best_candidates.get(model.tier, ["ssoBasic"]))
        if model:
            return list(cls._pool_candidates.get(model.tier, ["ssoBasic"]))
        return ["ssoBasic", "ssoSuper"]


__all__ = ["ModelService"]
