"""
Loki-backed Windows event MCP tools for incident investigation.
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


def _build_loki_query(host: str, resource_name: str) -> str:
    selector = f'{{host="{host}",job="windows-eventlog"}}'
    if resource_name:
        escaped_name = resource_name.replace('"', '\\"')
        return f'{selector} |= "{escaped_name}"'
    return selector


@tool(
    "get_windows_events",
    "Fetch Windows event log lines from Loki for a host and incident time window.",
    {
        "host": str,
        "time_start": str,
        "time_end": str,
        "resource_name": str,
        "query": str,
        "limit": int,
    },
)
async def get_windows_events_mcp(args: dict[str, Any]) -> dict[str, Any]:
    monitoring = AppConfig.get_monitoring_config()
    timeout = monitoring.MONITORING_TIMEOUT
    base_url = monitoring.LOKI_BASE_URL.rstrip("/")

    host = args["host"]
    query = args.get("query") or _build_loki_query(host=host, resource_name=args.get("resource_name", ""))
    params = {
        "query": query,
        "start": args["time_start"],
        "end": args["time_end"],
        "limit": str(args.get("limit") or 50),
        "direction": "BACKWARD",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{base_url}/loki/api/v1/query_range", params=params)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        return _to_mcp_text(
            {
                "ok": False,
                "tool": "get_windows_events",
                "base_url": base_url,
                "error": f"{type(exc).__name__}: {exc}",
                "params": params,
            }
        )

    return _to_mcp_text(
        {
            "ok": True,
            "tool": "get_windows_events",
            "base_url": base_url,
            "params": params,
            "resultType": data.get("data", {}).get("resultType"),
            "result": data.get("data", {}).get("result", []),
        }
    )
