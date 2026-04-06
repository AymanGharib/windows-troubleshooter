"""
Helper functions for ClaudeAIAgent to reduce file complexity while keeping customization centralized.

Developers can modify these functions to customize agent behavior without needing to edit
multiple files. All agent configuration and behavior is controlled through these helpers.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

# Claude Agent SDK imports
from claude_agent_sdk import (
    ClaudeAgentOptions,
    create_sdk_mcp_server,
    tool,
)

from app.config import AppConfig
from app.agent.tool_callbacks import default_callback

logger = logging.getLogger(__name__)


def _debug_enabled() -> bool:
    try:
        return bool(getattr(AppConfig.get_agent_config(), "AGENT_DEBUG", False))
    except Exception:
        return False


def build_header_string(custom_headers: dict) -> str:
    """Build header string using simple join for Claude SDK compatibility.

    Args:
        custom_headers: Dictionary of header key-value pairs

    Returns:
        String format "key1:value1\nkey2:value2" for Claude SDK
    """
    if not custom_headers:
        return ""

    return "\n".join(f"{key}:{value}" for key, value in custom_headers.items())


# ============================================================================
# Claude Agent SDK Functions
# ============================================================================

def build_claude_options(
    api_key: Optional[str] = None,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    top_p: Optional[float] = None,
    top_k: Optional[int] = None,
    permission_mode: Optional[str] = None,
    setting_sources: Optional[list] = None,
    disallowed_tools: Optional[list] = None,
    cwd: Optional[str] = None,
    max_turns: Optional[int] = None,
    # MCP server integration parameters
    local_mcp_server: Optional[Any] = None,
    custom_headers: Optional[dict] = None,
    # Runtime injection support
    base_options: Optional[ClaudeAgentOptions] = None,
    # Session management parameters
    resume: Optional[str] = None,
    fork_session: Optional[bool] = None
) -> ClaudeAgentOptions:
    """Build Claude Agent Options with unified configuration including MCP integration.

    Supports both initial setup and runtime header injection through optional base_options.

    Args:
        api_key: API authentication key (required for initial setup, ignored for runtime injection)
        system_prompt: System prompt for the agent (required for initial setup, ignored for runtime injection)
        model: Model name/identifier (required for initial setup, ignored for runtime injection)
        base_url: Base URL for API endpoints
        temperature: Response temperature (0.0 to 1.0)
        max_tokens: Maximum tokens to generate
        top_p: Top-p sampling parameter
        top_k: Top-k sampling parameter
        permission_mode: Claude SDK permission mode
        setting_sources: Setting sources for Claude SDK
        disallowed_tools: List of disallowed tool names
        cwd: Working directory for agent
        max_turns: Maximum conversation turns
        local_mcp_server: Local MCP server instance
        custom_headers: Custom headers dictionary
        base_options: Existing ClaudeAgentOptions to use as foundation (runtime injection mode)
        resume: Session ID to resume from
        fork_session: Whether to fork from the resumed session

    Returns:
        ClaudeAgentOptions configured with all specified parameters
    """

    try:
        debug_enabled = _debug_enabled()
        # If base_options provided, use as foundation (runtime injection mode)
        if base_options is not None:
            base_env = getattr(base_options, 'env', {}).copy()

            # Update custom headers if provided
            if custom_headers:
                base_env['ANTHROPIC_CUSTOM_HEADERS'] = build_header_string(custom_headers)

            # Create new options with updated environment and session management
            if debug_enabled:
                logger.info(
                    "Claude options runtime update: resume=%s fork_session=%s custom_headers=%s",
                    bool(resume),
                    bool(fork_session),
                    list(custom_headers.keys()) if custom_headers else [],
                )
            return ClaudeAgentOptions(
                system_prompt=getattr(base_options, 'system_prompt', None),
                env=base_env,
                allowed_tools=getattr(base_options, 'allowed_tools', None),
                permission_mode=getattr(base_options, 'permission_mode', None),
                setting_sources=getattr(base_options, 'setting_sources', None),
                disallowed_tools=getattr(base_options, 'disallowed_tools', None),
                cwd=getattr(base_options, 'cwd', None),
                max_turns=getattr(base_options, 'max_turns', None),
                mcp_servers=getattr(base_options, 'mcp_servers', None),
                can_use_tool=getattr(base_options, 'can_use_tool', None),
                hooks=getattr(base_options, 'hooks', None),
                agents=getattr(base_options, 'agents', None),
                resume=resume,
                fork_session=fork_session
            )

        # Otherwise, build from scratch (initial setup mode)
        # Validate required parameters for initial setup
        if api_key is None or system_prompt is None or model is None:
            raise ValueError("api_key, system_prompt, and model are required when base_options is not provided")

        # Get model configuration for tier-specific models
        model_config = AppConfig.get_model_config()

        # Build environment variables
        env_vars = {
            "ANTHROPIC_AUTH_TOKEN": api_key,
            "ANTHROPIC_MODEL": model,
            'ANTHROPIC_DEFAULT_HAIKU_MODEL': model_config.MODEL_NAME_HAIKU,
            'ANTHROPIC_DEFAULT_OPUS_MODEL': model_config.MODEL_NAME_OPUS,
            'ANTHROPIC_DEFAULT_SONNET_MODEL': model_config.MODEL_NAME_SONNET,
        }

        # Add custom headers if provided
        if custom_headers:
            header_string = build_header_string(custom_headers)
            env_vars['ANTHROPIC_CUSTOM_HEADERS'] = header_string

        options_kwargs = {
            "system_prompt": system_prompt,
            "env": env_vars
        }

        # Add base URL if provided (for custom endpoints)
        if base_url:
            options_kwargs["env"]["ANTHROPIC_BASE_URL"] = base_url

        # NOT SUPPORTED YET: Add temperature and max tokens if provided
        if temperature is not None:
            options_kwargs["env"]["TEMPERATURE"] = str(temperature) # NOT SUPPORTED YET
        if max_tokens is not None:
            options_kwargs["env"]["MAX_TOKENS"] = str(max_tokens) # NOT SUPPORTED YET
        if top_p is not None:
            options_kwargs["env"]["TOP_P"] = str(top_p) # NOT SUPPORTED YET
        if top_k is not None:
            options_kwargs["env"]["TOP_K"] = str(top_k) # NOT SUPPORTED YET

        # Add agent-specific options if provided (only when not None)
        if permission_mode is not None:
            options_kwargs["permission_mode"] = permission_mode
        if setting_sources is not None:
            options_kwargs["setting_sources"] = setting_sources
        if disallowed_tools is not None:
            options_kwargs["disallowed_tools"] = disallowed_tools
        if cwd is not None:
            options_kwargs["cwd"] = cwd
        if max_turns is not None:
            options_kwargs["max_turns"] = max_turns

        # Tool callback setup
        agent_config = AppConfig.get_agent_config()
        #Setting default callback to allow all tools:
        options_kwargs["can_use_tool"] = default_callback

        if agent_config.USE_TOOL_CALLBACK and agent_config.TOOL_CALLBACK_METHOD:
            from app.agent import tool_callbacks
            # Dynamically get the callback function from tool_callbacks module
            tool_callback = getattr(tool_callbacks, agent_config.TOOL_CALLBACK_METHOD, None)
            if tool_callback is not None:
                options_kwargs["can_use_tool"] = tool_callback
                logger.debug(f"Using tool callback: {agent_config.TOOL_CALLBACK_METHOD}")
            else:
                logger.warning(f"Tool callback method '{agent_config.TOOL_CALLBACK_METHOD}' not found in tool_callbacks, using default callback")

        # MCP server integration
        mcp_servers = {}
        if local_mcp_server:
            mcp_servers["local_tools"] = local_mcp_server
            logger.info("Added local tools MCP server")


        if mcp_servers:
            options_kwargs["mcp_servers"] = mcp_servers
            logger.info("Added MCP servers to Claude options")

        if debug_enabled:
            logger.info(
                "Claude options built: model=%s base_url=%s permission_mode=%s cwd=%s max_turns=%s mcp_enabled=%s setting_sources=%s",
                model,
                bool(base_url),
                permission_mode,
                cwd,
                max_turns,
                bool(mcp_servers),
                setting_sources,
            )

        # Add session management parameters if provided
        if resume is not None:
            options_kwargs["resume"] = resume
            logger.info(f"Added resume session: {resume}")
        
        if fork_session is not None:
            options_kwargs["fork_session"] = fork_session
            logger.info(f"Added fork_session: {fork_session}")

        return ClaudeAgentOptions(**options_kwargs)
    except Exception as e:
        logger.exception("Failed to build Claude Agent Options")
        raise ValueError("Failed to build Claude Agent Options") from e


def build_claude_sdk_mcp_server() -> Any:
    """
    Build Claude SDK MCP server using auto-discovered tools.

    Uses the tools package auto-discovery system to find and register
    all MCP tools without manual configuration.
    """
    try:
        from app.tools import discover_local_mcp_tools

        start_time = time.perf_counter()
        # Auto-discover all MCP tools
        tools = discover_local_mcp_tools()

        if not tools:
            logger.warning("No MCP tools discovered for local server")
            return None

        # Create SDK MCP server with auto-discovered tools
        server = create_sdk_mcp_server(
            name="local_tools",
            version="1.0.0",
            tools=tools,
        )

        logger.info("Created Claude SDK MCP server with %d auto-discovered tools", len(tools))
        if _debug_enabled():
            logger.info("MCP server creation took %.2f ms", (time.perf_counter() - start_time) * 1000)
        return server

    except Exception as e:
        logger.exception("Failed to create Claude SDK MCP server")
        return None


def get_claude_allowed_tools() -> list[str]:
    """
    Get list of allowed tool names for Claude SDK using auto-discovery.

    Returns:
        List of tool names formatted as mcp__local_tools__tool_name
    """
    try:
        from app.tools import get_tool_names
        return get_tool_names()
    except Exception as e:
        logger.warning("Failed to get tool names: %s", e)
        return []




def log_mcp_server_state(mcp_servers: Any) -> None:
    """
    Debug: log current MCP server objects and any init/connected flags to validate setup.
    """
    try:
        if not mcp_servers:
            logger.info("MCP: no servers configured")
            return

        # Claude SDK format - dict of server configurations
        logger.info("MCP: %d server(s) configured (Claude SDK format)", len(mcp_servers))
        for name, config in mcp_servers.items():
            logger.info("MCP[%s]: configured with keys: %s", name, list(config.keys()) if isinstance(config, dict) else type(config).__name__)
    except Exception as e:
        logger.warning("MCP: failed to introspect servers: %s", e)


def extract_final_text(result: Any) -> str:
    """
    Normalize final text from a non-streaming Agents SDK result.
    """
    final = (
        getattr(result, "final_output", None)
        or getattr(result, "final_text", None)
        or getattr(result, "text", None)
        or getattr(result, "content", None)
    )
    if isinstance(final, list):
        return "".join(str(x) for x in final)
    if isinstance(final, str):
        return final
    return str(result)


def extract_stream_text_piece(event: Any) -> Optional[str]:
    """
    Normalize a streamed event to a text delta if present.
    """
    text_piece = (
        getattr(event, "delta", None)
        or getattr(event, "text", None)
        or getattr(event, "content", None)
    )

    if text_piece is None and isinstance(event, dict):
        text_piece = event.get("delta") or event.get("text") or event.get("content")

    if isinstance(text_piece, list):
        text_piece = "".join(str(x) for x in text_piece)

    if text_piece:
        return str(text_piece)
    return None

