"""
AIPlatformSettings: AI Platform-related configuration loaded from environment.

Env vars:
- AIPLATFORM_API_KEY (required for runtime)
- AIPLATFORM_BASE_URL (optional)
- AIPLATFORM_TIMEOUT (seconds, default: 120)
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from ._env import env_int


@dataclass(frozen=True)
class AIPlatformSettings:
    AIPLATFORM_API_KEY: str
    AIPLATFORM_BASE_URL: Optional[str]
    AIPLATFORM_TIMEOUT: int


def load_aiplatform_settings() -> AIPlatformSettings:
    settings = AIPlatformSettings(
        AIPLATFORM_API_KEY=os.getenv("AIPLATFORM_API_KEY", ""),
        AIPLATFORM_BASE_URL=os.getenv("AIPLATFORM_BASE_URL"),
        AIPLATFORM_TIMEOUT=env_int("AIPLATFORM_TIMEOUT", 120),
    )

    # Map to what Claude CLI subprocess actually looks for
    if settings.AIPLATFORM_BASE_URL:
        os.environ["ANTHROPIC_BASE_URL"] = settings.AIPLATFORM_BASE_URL

    if settings.AIPLATFORM_API_KEY:
        os.environ["ANTHROPIC_AUTH_TOKEN"] = settings.AIPLATFORM_API_KEY

    
    return settings
    




# Singleton settings object used across the app
aiplatform_settings: AIPlatformSettings = load_aiplatform_settings()