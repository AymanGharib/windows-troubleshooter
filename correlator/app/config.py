from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "os-correlation-engine"
    app_env: str = "dev"

    prometheus_base_url: str = "http://localhost:9090"
    loki_base_url: str = "http://localhost:3100"

    default_lookback_seconds: int = 300
    max_logs_per_event: int = 30
    max_metric_points_per_series: int = 120
    debug_include_query_output: bool = False
    debug_max_chars_per_payload: int = 4000

    output_mode: str = Field(default="stdout", description="stdout|file|noop")
    output_file_path: str = "output/incidents.jsonl"


settings = Settings()
