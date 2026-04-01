from __future__ import annotations

from typing import Any

import httpx

from .time_utils import ns_to_seconds


class PrometheusClient:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def query_range(self, query: str, start_ns: int, end_ns: int, step: str = "15s") -> dict[str, Any]:
        params = {
            "query": query,
            "start": ns_to_seconds(start_ns),
            "end": ns_to_seconds(end_ns),
            "step": step,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(f"{self.base_url}/api/v1/query_range", params=params)
            r.raise_for_status()
            return r.json()


class LokiClient:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def query_range(
        self,
        query: str,
        start_ns: int,
        end_ns: int,
        limit: int = 200,
        direction: str = "BACKWARD",
    ) -> dict[str, Any]:
        params = {
            "query": query,
            "start": str(start_ns),
            "end": str(end_ns),
            "limit": str(limit),
            "direction": direction,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(f"{self.base_url}/loki/api/v1/query_range", params=params)
            r.raise_for_status()
            return r.json()
