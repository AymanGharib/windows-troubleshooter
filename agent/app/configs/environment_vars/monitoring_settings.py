"""
MonitoringSettings: Prometheus/Loki configuration loaded from environment.

Env vars:
- PROMETHEUS_BASE_URL (default: http://localhost:9090)
- LOKI_BASE_URL (default: http://localhost:3100)
- MONITORING_TIMEOUT (seconds, default: 10)
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from ._env import env_int


@dataclass(frozen=True)
class MonitoringSettings:
    PROMETHEUS_BASE_URL: str
    LOKI_BASE_URL: str
    MONITORING_TIMEOUT: int


def load_monitoring_settings() -> MonitoringSettings:
    return MonitoringSettings(
        PROMETHEUS_BASE_URL=os.getenv("PROMETHEUS_BASE_URL", "http://localhost:9090"),
        LOKI_BASE_URL=os.getenv("LOKI_BASE_URL", "http://localhost:3100"),
        MONITORING_TIMEOUT=env_int("MONITORING_TIMEOUT", 10),
    )


monitoring_settings: MonitoringSettings = load_monitoring_settings()
