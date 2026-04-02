"""
PowerShellSettings: PowerShell execution configuration loaded from environment.

Env vars:
- POWERSHELL_EXECUTABLE (default: powershell)
- POWERSHELL_TIMEOUT (seconds, default: 20)
- POWERSHELL_MAX_OUTPUT_CHARS (default: 12000)
- POWERSHELL_MODE (default: readonly)
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from ._env import env_int


@dataclass(frozen=True)
class PowerShellSettings:
    POWERSHELL_EXECUTABLE: str
    POWERSHELL_TIMEOUT: int
    POWERSHELL_MAX_OUTPUT_CHARS: int
    POWERSHELL_MODE: str


def load_powershell_settings() -> PowerShellSettings:
    return PowerShellSettings(
        POWERSHELL_EXECUTABLE=os.getenv("POWERSHELL_EXECUTABLE", "powershell"),
        POWERSHELL_TIMEOUT=env_int("POWERSHELL_TIMEOUT", 20),
        POWERSHELL_MAX_OUTPUT_CHARS=env_int("POWERSHELL_MAX_OUTPUT_CHARS", 12000),
        POWERSHELL_MODE=os.getenv("POWERSHELL_MODE", "readonly").strip().lower() or "readonly",
    )


powershell_settings: PowerShellSettings = load_powershell_settings()
