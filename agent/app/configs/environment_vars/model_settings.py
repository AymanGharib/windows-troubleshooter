"""
ModelSettings: Model-tuning configuration loaded from environment.

Env vars like:
- MODEL (str; default: baseten/deepseek-ai/deepseek-v3.1)
- MODEL_TEMPERATURE (float; default: 0.7)
- MODEL_MAX_TOKENS (int; default: 800)
- MODEL_TOP_P (float; default: 0.9)
- MODEL_TOP_K (int; default: 50)
- MODEL_HAIKU (str; optional Claude Haiku model via env var)
- MODEL_OPUS (str; optional Claude Opus model via env var)
- MODEL_SONNET (str; optional Claude Sonnet model via env var)
"""
from __future__ import annotations

from dataclasses import dataclass
import os

from ._env import env_float, env_int


@dataclass(frozen=True)
class ModelSettingsConfig:
    MODEL_NAME: str
    TEMPERATURE: float
    MAX_TOKENS: int
    TOP_P: float
    TOP_K: int
    MODEL_NAME_HAIKU: str
    MODEL_NAME_OPUS: str
    MODEL_NAME_SONNET: str


def load_model_settings() -> ModelSettingsConfig:
    # Get the main model name which will be used as fallback for tier-specific models
    main_model = os.getenv("MODEL", "baseten/deepseek-ai/deepseek-v3.1")

    return ModelSettingsConfig(
        MODEL_NAME=main_model,
        TEMPERATURE=env_float("MODEL_TEMPERATURE", None),
        MAX_TOKENS=env_int("MODEL_MAX_TOKENS", None),
        TOP_P=env_float("MODEL_TOP_P", None),
        TOP_K=env_int("MODEL_TOP_K", None),
        MODEL_NAME_HAIKU=os.getenv("MODEL_HAIKU", main_model),
        MODEL_NAME_OPUS=os.getenv("MODEL_OPUS", main_model),
        MODEL_NAME_SONNET=os.getenv("MODEL_SONNET", main_model),
    )


# Singleton config object used across the app
model_settings: ModelSettingsConfig = load_model_settings()