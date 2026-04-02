from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "os-correlation-engine"
    app_env: str = "dev"

    prometheus_base_url: str = "http://localhost:9090"
    loki_base_url: str = "http://localhost:3100"
    watched_process_regex: str = "(?i)wordpad|write"
    watched_process_names: str = ""

    default_lookback_seconds: int = 300
    max_logs_per_event: int = 30
    max_metric_points_per_series: int = 120
    debug_include_query_output: bool = False
    debug_max_chars_per_payload: int = 4000

    output_mode: str = Field(default="stdout", description="stdout|file|noop")
    output_file_path: str = "output/incidents.jsonl"

    def get_watched_process_names(self) -> list[str]:
        if self.watched_process_names.strip():
            names = [item.strip() for item in self.watched_process_names.split(",")]
            return [item for item in names if item]

        cleaned = self.watched_process_regex.replace("(?i)", "")
        parts = [item.strip() for item in cleaned.split("|")]
        return [item for item in parts if item]


settings = Settings()
