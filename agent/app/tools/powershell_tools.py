"""
Guarded PowerShell MCP tool for host diagnostics.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from claude_agent_sdk import tool

from app.config import AppConfig

READONLY_ALLOWED_PREFIXES = ("Get-", "Test-", "Resolve-", "Select-", "Measure-", "Format-", "Where-", "Sort-", "Group-", "Find-", "Out-")
READONLY_ALLOWED_COMMANDS = (
    "hostname", "whoami", "Get-Date", "Get-CimInstance", "Get-WinEvent", "Get-Service",
    "Get-Process", "Get-Item", "Get-ChildItem", "Get-Content", "Get-Volume", "Get-PSDrive",
    "Get-ComputerInfo", "Get-NetTCPConnection", "Get-NetIPAddress", "Get-NetIPConfiguration",
    "Get-EventLog", "Get-Counter", "Test-NetConnection", "Select-String",
)
BLOCKED_PATTERNS = (
    r"(?i)\bremove-item\b", r"(?i)\bset-item\b", r"(?i)\bset-content\b", r"(?i)\badd-content\b",
    r"(?i)\bnew-item\b", r"(?i)\bclear-content\b", r"(?i)\bcopy-item\b", r"(?i)\bmove-item\b",
    r"(?i)\brename-item\b", r"(?i)\bstart-process\b", r"(?i)\bstop-process\b", r"(?i)\brestart-service\b",
    r"(?i)\bstart-service\b", r"(?i)\bstop-service\b", r"(?i)\bset-service\b", r"(?i)\binvoke-expression\b",
)


def _to_mcp_text(payload: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}]}


def _is_allowed_readonly_command(command: str) -> tuple[bool, str | None]:
    stripped = command.strip()
    if not stripped:
        return False, "Command is empty."
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, stripped):
            return False, f"Blocked by safety pattern: {pattern}"
    head = stripped.split("|", 1)[0].strip()
    first_token = head.split(maxsplit=1)[0] if head else ""
    if first_token in READONLY_ALLOWED_COMMANDS:
        return True, None
    if any(first_token.startswith(prefix) for prefix in READONLY_ALLOWED_PREFIXES):
        return True, None
    return False, f"Command '{first_token}' is not in the readonly allowlist."


@tool("execute_powershell", "Execute a guarded PowerShell command for host diagnostics. Readonly mode is the default.", {"command": str})
async def execute_powershell_mcp(args: dict[str, Any]) -> dict[str, Any]:
    powershell = AppConfig.get_powershell_config()
    command = str(args.get("command", "")).strip()
    if powershell.POWERSHELL_MODE != "unsafe":
        allowed, reason = _is_allowed_readonly_command(command)
        if not allowed:
            return _to_mcp_text({"ok": False, "tool": "execute_powershell", "mode": powershell.POWERSHELL_MODE, "error": reason, "command": command})
    try:
        process = await asyncio.create_subprocess_exec(
            powershell.POWERSHELL_EXECUTABLE, "-NoProfile", "-NonInteractive", "-Command", command,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=powershell.POWERSHELL_TIMEOUT)
    except asyncio.TimeoutError:
        return _to_mcp_text({"ok": False, "tool": "execute_powershell", "mode": powershell.POWERSHELL_MODE, "error": f"Timed out after {powershell.POWERSHELL_TIMEOUT} seconds.", "command": command})
    except FileNotFoundError:
        return _to_mcp_text({"ok": False, "tool": "execute_powershell", "mode": powershell.POWERSHELL_MODE, "error": f"PowerShell executable not found: {powershell.POWERSHELL_EXECUTABLE}", "command": command})
    except Exception as exc:
        return _to_mcp_text({"ok": False, "tool": "execute_powershell", "mode": powershell.POWERSHELL_MODE, "error": f"{type(exc).__name__}: {exc}", "command": command})
    stdout_text = stdout.decode("utf-8", errors="replace")
    stderr_text = stderr.decode("utf-8", errors="replace")
    max_chars = powershell.POWERSHELL_MAX_OUTPUT_CHARS
    return _to_mcp_text({
        "ok": process.returncode == 0,
        "tool": "execute_powershell",
        "mode": powershell.POWERSHELL_MODE,
        "command": command,
        "exit_code": process.returncode,
        "stdout": stdout_text[:max_chars],
        "stderr": stderr_text[:max_chars],
        "stdout_truncated": len(stdout_text) > max_chars,
        "stderr_truncated": len(stderr_text) > max_chars,
    })
