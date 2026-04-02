"""
ADOSettings: Azure DevOps-related configuration loaded from environment.

Env vars:
- ADO_ORG_URL (required for Azure DevOps operations)
- ADO_PAT (required for Azure DevOps authentication)
- ADO_PROJECT_NAME (optional, default: "eee")
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ADOSettings:
    ADO_ORG_URL: Optional[str]
    ADO_PAT: Optional[str]
    ADO_PROJECT_NAME: str


def load_ado_settings() -> ADOSettings:
    return ADOSettings(
        ADO_ORG_URL=os.getenv("ADO_ORG_URL"),
        ADO_PAT=os.getenv("ADO_PAT"),
        ADO_PROJECT_NAME=os.getenv("ADO_PROJECT_NAME", "eee"),
    )


# Singleton settings object used across the app
ado_settings: ADOSettings = load_ado_settings()