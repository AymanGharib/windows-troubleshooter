"""
Prometheus MCP tools for incident investigation.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from claude_agent_sdk import tool

from app.config import AppConfig


def _to_mcp_text(payload: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, ensure_ascii=False, indent=2),
            }
        ]
    }


@tool(
    "get_prometheus_range",
    "Query a Prometheus range for a metric or expression during an incident window.",
    {
        "query": str,
        "start": str,
        "end": str,
        "step": str,
    },
)
async def get_prometheus_range_mcp(args: dict[str, Any]) -> dict[str, Any]:
    monitoring = AppConfig.get_monitoring_config()
    timeout = monitoring.MONITORING_TIMEOUT
    base_url = monitoring.PROMETHEUS_BASE_URL.rstrip("/")

    params = {
        "query": args["query"],
        "start": args["start"],
        "end": args["end"],
        "step": args.get("step") or "15s",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{base_url}/api/v1/query_range", params=params)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        return _to_mcp_text(
            {
                "ok": False,
                "tool": "get_prometheus_range",
                "base_url": base_url,
                "error": f"{type(exc).__name__}: {exc}",
                "params": params,
            }
        )

    return _to_mcp_text(
        {
            "ok": True,
            "tool": "get_prometheus_range",
            "base_url": base_url,
            "params": params,
            "resultType": data.get("data", {}).get("resultType"),
            "result": data.get("data", {}).get("result", []),
        }
    )
