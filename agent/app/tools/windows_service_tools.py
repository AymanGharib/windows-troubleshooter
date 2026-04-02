"""
Windows service MCP tools for incident investigation.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

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
    "get_windows_service_status",
    "Get the current live status of a Windows service by service name or display name.",
    {
        "service_name": str,
    },
)
async def get_windows_service_status_mcp(args: dict[str, Any]) -> dict[str, Any]:
    powershell = AppConfig.get_powershell_config()
    service_name = str(args.get("service_name", "")).strip()

    if not service_name:
        return _to_mcp_text(
            {
                "ok": False,
                "tool": "get_windows_service_status",
                "error": "service_name is required",
            }
        )

    escaped_name = service_name.replace("'", "''")
    command = (
        "$svc = Get-CimInstance Win32_Service | "
        "Where-Object {{ $_.Name -eq '{name}' -or $_.DisplayName -eq '{name}' }} | "
        "Select-Object Name,DisplayName,State,StartMode,Status,ProcessId; "
        "if ($svc) {{ $svc | ConvertTo-Json -Depth 3 }} else {{ '[]' }}"
    ).format(name=escaped_name)

    try:
        process = await asyncio.create_subprocess_exec(
            powershell.POWERSHELL_EXECUTABLE,
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=powershell.POWERSHELL_TIMEOUT,
        )
    except asyncio.TimeoutError:
        return _to_mcp_text(
            {
                "ok": False,
                "tool": "get_windows_service_status",
                "service_name": service_name,
                "error": f"Timed out after {powershell.POWERSHELL_TIMEOUT} seconds.",
            }
        )
    except FileNotFoundError:
        return _to_mcp_text(
            {
                "ok": False,
                "tool": "get_windows_service_status",
                "service_name": service_name,
                "error": f"PowerShell executable not found: {powershell.POWERSHELL_EXECUTABLE}",
            }
        )
    except Exception as exc:
        return _to_mcp_text(
            {
                "ok": False,
                "tool": "get_windows_service_status",
                "service_name": service_name,
                "error": f"{type(exc).__name__}: {exc}",
            }
        )

    stdout_text = stdout.decode("utf-8", errors="replace").strip()
    stderr_text = stderr.decode("utf-8", errors="replace").strip()

    parsed: Any = []
    if stdout_text:
        try:
            parsed = json.loads(stdout_text)
        except json.JSONDecodeError:
            parsed = stdout_text

    return _to_mcp_text(
        {
            "ok": process.returncode == 0,
            "tool": "get_windows_service_status",
            "service_name": service_name,
            "exit_code": process.returncode,
            "found": bool(parsed),
            "result": parsed,
            "stderr": stderr_text[:powershell.POWERSHELL_MAX_OUTPUT_CHARS],
        }
    )
