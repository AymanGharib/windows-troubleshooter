"""
Windows process MCP tools for incident investigation.
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
    "get_windows_process_status",
    "Get the current live status of a Windows process by name.",
    {
        "process_name": str,
    },
)
async def get_windows_process_status_mcp(args: dict[str, Any]) -> dict[str, Any]:
    powershell = AppConfig.get_powershell_config()
    process_name = str(args.get("process_name", "")).strip()

    if not process_name:
        return _to_mcp_text(
            {
                "ok": False,
                "tool": "get_windows_process_status",
                "error": "process_name is required",
            }
        )

    escaped_name = process_name.replace("'", "''")
    command = (
        "$p = Get-Process -Name '{name}' -ErrorAction SilentlyContinue | "
        "Select-Object ProcessName,Id,CPU,WS,StartTime,Path; "
        "if ($p) {{ $p | ConvertTo-Json -Depth 3 }} else {{ '[]' }}"
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
                "tool": "get_windows_process_status",
                "process_name": process_name,
                "error": f"Timed out after {powershell.POWERSHELL_TIMEOUT} seconds.",
            }
        )
    except FileNotFoundError:
        return _to_mcp_text(
            {
                "ok": False,
                "tool": "get_windows_process_status",
                "process_name": process_name,
                "error": f"PowerShell executable not found: {powershell.POWERSHELL_EXECUTABLE}",
            }
        )
    except Exception as exc:
        return _to_mcp_text(
            {
                "ok": False,
                "tool": "get_windows_process_status",
                "process_name": process_name,
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
            "tool": "get_windows_process_status",
            "process_name": process_name,
            "exit_code": process.returncode,
            "running": bool(parsed),
            "result": parsed,
            "stderr": stderr_text[:powershell.POWERSHELL_MAX_OUTPUT_CHARS],
        }
    )
