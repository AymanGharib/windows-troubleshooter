# v3e Azure DevOps Access Bot - Developer Guide

## Overview

A production-ready A2A (Agent-to-Agent) compliant agent powered by Claude Agent SDK with standalone server deployment. This agent automates user access management for the v3e Azure DevOps organization by extracting email addresses from JIRA tickets and adding users with appropriate permissions.

**Status**: 🎉 Production Ready

### Key Features

- ✅ Claude Agent SDK integration with A2A protocol support
- ✅ JSON-RPC 2.0 compliant API
- ✅ Standalone HTTP server deployment
- ✅ Azure DevOps User Management via Member Entitlement API
- ✅ Local MCP (Model Context Protocol) tools integration
- ✅ Automated user provisioning with Basic license and Project Contributors permissions
- ✅ Email extraction and validation from JIRA descriptions
- ✅ Centralized logging with environment-based control
- ✅ Session correlation and metadata tracking
- ✅ Cost and usage tracking per request

## ⚠️ Important: Session ID Behavior

### Standalone Server Deployment
- ✅ **Session continuity supported**
- ✅ Conversation context maintained across requests
- ✅ Session IDs enable conversation resumption

---

## Quick Start

### Prerequisites

- Python 3.10+
- pip package manager
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd 3e-oracle-standards
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv .venv

   # Windows
   .venv\Scripts\activate

   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   Copy and edit the `.env` file with your API credentials:
   ```bash
   # Required
   AIPLATFORM_API_KEY=your-api-key-here
   AIPLATFORM_BASE_URL=https://aiapidev.3ecompany.com
   MODEL=xai/grok-4-fast-reasoning

   # Optional - adjust as needed
   LOG_LEVEL=INFO
   PORT=10005
   ```

5. **Run the server**
   ```bash
   python -m app
   ```

   The server will start at `http://localhost:10005`



---

## Project Structure

```
ado-agent/
├── app/
│   ├── agent/
│   │   ├── claude_agent.py          # Main Claude Agent SDK wrapper
│   │   ├── agent_support.py         # Helper functions for agent
│   │   ├── agent_skills.json        # Agent skills configuration
│   │   └── tool_callbacks.py        # Tool permission callbacks
│   ├── a2a_core/
│   │   ├── a2a_conversions.py       # A2A protocol conversions
│   │   ├── agent_executor.py        # A2A → Claude bridge
│   │   └── agent_card.py            # A2A AgentCard definition
│   ├── tools/
│   │   └── tool_ado_user.py         # Azure DevOps user management
│   ├── configs/
│   │   └── environment_vars/        # Environment variable configs
│   │       ├── ado_settings.py      # Azure DevOps configuration
│   │       ├── agent_settings.py    # Agent configuration
│   │       ├── model_settings.py    # Model configuration
│   │       ├── aiplatform_settings.py # AI Platform configuration
│   │       ├── general_settings.py  # General configuration
│   │       └── a2a_settings.py      # A2A protocol configuration
│   ├── common/
│   │   └── utils.py                 # Centralized logging
│   ├── prompts/
│   │   └── agent_system_prompt.txt  # System prompt file
│   ├── config.py                    # Unified configuration access
│   └── __main__.py                  # Standalone server entry
├── requirements.txt                 # Python dependencies
├── .env                             # Environment configuration
├── .env.example                     # Environment template
├── Dockerfile                       # Docker configuration
└── README.md                        # This file
```

---

## Configuration

### Environment Variables

All configuration is managed through the `.env` file. Key settings:

#### AI Platform Settings
```bash
# Required: API authentication
AIPLATFORM_API_KEY=sk-lf-xxxxx:pk-lf-xxxxx
AIPLATFORM_BASE_URL=https://aiapidev.3ecompany.com
AIPLATFORM_TIMEOUT=120
```

#### Model Settings
```bash
# Primary model
MODEL=baseten/moonshotai/kimi-k2-instruct-0905
MODEL_TEMPERATURE=0.2
MODEL_MAX_TOKENS=1000

# Claude SDK tier-specific models (optional)
MODEL_HAIKU=baseten/moonshotai/kimi-k2-instruct-0905
MODEL_OPUS=baseten/moonshotai/kimi-k2-instruct-0905
MODEL_SONNET=baseten/moonshotai/kimi-k2-instruct-0905

AGENT_MAX_TOKENS=16000
```


#### Agent Settings
```bash
AGENT_NAME=v3e Organization Access Bot
AGENT_SYSTEM_PROMPT=You are the v3e Organization Access Bot. Your goal is to extract a user's email address from a JIRA description and add them to Azure DevOps.
USE_TOOL_CALLBACK=true
TOOL_CALLBACK_METHOD=security_callback
AGENT_ENABLE_LOCAL_MCP=true
AGENT_DEBUG=false
```

#### Azure DevOps Settings
```bash
# Azure DevOps Organization URL
ADO_ORG_URL=https://dev.azure.com/v3e

# Azure DevOps Personal Access Token
ADO_PAT=your-pat-token-here

# Azure DevOps Project Name
ADO_PROJECT_NAME=eee
```

#### General Settings
```bash
PORT=10005
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
STREAMING=false
```

#### Monitoring Settings
```bash
PROMETHEUS_BASE_URL=http://localhost:9090
LOKI_BASE_URL=http://localhost:3100
MONITORING_TIMEOUT=10
```

#### PowerShell MCP Settings
```bash
POWERSHELL_EXECUTABLE=powershell
POWERSHELL_TIMEOUT=20
POWERSHELL_MAX_OUTPUT_CHARS=12000
POWERSHELL_MODE=readonly
```

### Logging Configuration

Control logging verbosity via `LOG_LEVEL` environment variable:

```bash
# Show all debug messages (verbose)
LOG_LEVEL=DEBUG

# Standard info messages (recommended for development)
LOG_LEVEL=INFO

# Only warnings and errors (recommended for production)
LOG_LEVEL=WARNING
```

---

## Running the Project

### Standalone Server Mode

```bash
# Start the server
python -m app

# Server runs at http://localhost:10005
# Endpoints:
#   GET  /agent  - AgentCard discovery
#   POST /       - JSON-RPC 2.0 message handling
```


---

## Development

### Adding a New Tool

Tools follow the Claude Agent SDK pattern with auto-discovery. Here's how to create one:

1. **Create tool file** in `app/tools/`
   ```python
   # app/tools/tool_example.py
   from __future__ import annotations
   import logging
   from typing import Any
   from claude_agent_sdk import tool

   logger = logging.getLogger(__name__)

   # Core implementation
   def example_tool(input_text: str) -> str:
       """Core tool logic."""
       return f"Processed: {input_text}"

   # MCP wrapper for Claude SDK
   @tool(
       name="example",
       description="Example tool that processes text",
       input_schema={
           "type": "object",
           "properties": {
               "input_text": {
                   "type": "string",
                   "description": "Text to process"
               }
           },
           "required": ["input_text"]
       }
   )
   async def example_tool_mcp(args: dict[str, Any]) -> dict[str, Any]:
       """MCP wrapper for example tool."""
       input_text = args.get("input_text", "")
       logger.info(f"Example tool called with: {input_text}")

       try:
           result = example_tool(input_text)
           return {
               "content": [
                   {"type": "text", "text": result}
               ]
           }
       except Exception as e:
           error_msg = f"Error: {e}"
           logger.error(error_msg)
           return {
               "content": [
                   {"type": "text", "text": error_msg}
               ]
           }

   __all__ = ["example_tool", "example_tool_mcp"]
   ```

2. **Tool auto-discovery**

   The tool is automatically discovered by the system (see `app/tools/__init__.py`). No manual registration needed!

3. **Create a test file**
   ```python
   import asyncio
   from app.agent.claude_agent import ClaudeAIAgent

   async def test_example():
       agent = ClaudeAIAgent()
       response = await agent.invoke(
           "Use the example tool to process 'hello world'",
           "test-context-123"
       )
       print(response)

   if __name__ == "__main__":
       asyncio.run(test_example())
   ```

4. **Test your tool**
   ```bash
   python test_example_tool.py
   ```

### Tool Naming Convention

- Tool file: `tool_<name>.py`
- Core function: `<name>_tool()`
- MCP wrapper: `<name>_tool_mcp()`
- Claude SDK tool name: Match the `name` parameter in `@tool()` decorator

### Available Built-in Tools

| Tool | Name | Description |
|------|------|-------------|
| Azure DevOps User Management | `mcp__local_tools__add_user_to_v3e` | Add users to v3e Azure DevOps organization with Basic license and Project Contributors permissions |

---

## API Reference

### A2A Protocol Endpoints

#### GET `/agent` - AgentCard Discovery
Returns agent metadata and capabilities.

**Response**:
```json
{
  "id": "claude-agent-id",
  "name": "v3e Organization Access Bot",
  "description": "v3e Organization Access Bot that automates user access management for Azure DevOps",
  "version": "1.0.0",
  "skills": [...]
}
```

#### POST `/` - JSON-RPC 2.0 Message Handling
Send messages to the agent.

**Request**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "send",
  "params": {
    "message": {
      "parts": [
        {
          "kind": "text",
          "text": "Please add john.doe@example.com to the v3e organization for the eee project"
        }
      ]
    },
    "contextId": "session-123"
  }
}
```

**A2A-SDK Types Equivalent (for Python clients):**
```python
from a2a.types import SendMessageRequest, Message, TextPart, Role

# Create the request using proper A2A types
request = SendMessageRequest(
    message=Message(
        role=Role("user"),
        parts=[TextPart(text="Please add john.doe@example.com to the v3e organization for the eee project")]
    ),
    context_id="session-123"
)

# Serialize for HTTP request
import json
payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "send",
    "params": request.model_dump(exclude_none=True)
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "artifacts": [
      {
        "name": "agent_response",
        "parts": [
          {
            "kind": "text",
            "text": "SUCCESS: Added john.doe@example.com to v3e/eee with Basic license and Project Contributors permissions."
          }
        ]
      },
      {
        "name": "agent_metadata",
        "parts": [
          {
            "kind": "data",
            "data": {
              "session_id": "claude-session-id",
              "duration_ms": 1234,
              "tools_used": ["mcp__local_tools__add_user_to_v3e"]
            }
          }
        ]
      }
    ],
    "contextId": "session-123",
    "status": {
      "state": "completed"
    }
  }
}
```

---

## Architecture

### Request Flow

```
User Request → Starlette App → A2A Protocol Handler
    ↓
A2A Agent Executor → Claude Agent SDK
    ↓
Claude SDK → AI Platform API
    ↓
Response + Metadata → A2A Format → User
```

### Key Components

#### 1. **Claude Agent (`app/agent/claude_agent.py`)**
- Wraps Claude Agent SDK
- Handles agent initialization and lifecycle
- Manages tool discovery and MCP integration
- Provides both `invoke` (single-shot) and `stream` (streaming) modes

#### 2. **A2A Bridge (`app/a2a_core/agent_executor.py`)**
- Translates A2A protocol to Claude SDK calls
- Maps metadata between formats
- Tracks session correlation (A2A ↔ Claude)
- Handles artifacts and response formatting

#### 3. **Tool System (`app/tools/`)**
- Auto-discovery of local MCP tools
- Convention-based tool registration using `_mcp` suffix
- Standardized response format
- Built-in tools + extensible architecture

#### 4. **MCP Integration (`app/tools/`)**
- Local MCP tools auto-discovery
- Convention-based tool registration
- Built-in Azure DevOps user management tool

#### 5. **Centralized Logging (`app/common/utils.py`)**
- `get_logger()` function for consistent logging
- Environment-based log level control
- Structured log format

---

## Deployment

### Local Development
```bash
python -m app
```


### Docker Deployment

```bash
# Build the Docker image
docker build -t claude-a2a-agent .

# Run the container
docker run -p 10005:10005 -e AIPLATFORM_API_KEY=your-key claude-a2a-agent
```

---

## Troubleshooting

### Common Issues

#### 1. **403 Forbidden Error**
```
requests.exceptions.HTTPError: 403 Client Error: Forbidden
```

**Solution**: Add API key to request headers. Check that `AIPLATFORM_API_KEY` is set correctly.

#### 2. **Dependency Conflicts**
```
ERROR: Cannot install because these package versions have conflicting dependencies
```

**Solution**:
- Use `pip install -r requirements.txt --upgrade`
- Check for incompatible version pins in `requirements.txt`
- For httpx conflicts between a2a-sdk and litellm, use `litellm>=1.55.11` instead of pinned version

#### 3. **Tool Not Discovered**
If your tool isn't being auto-discovered:
- Check tool filename follows pattern: `tool_<name>.py`
- Ensure MCP wrapper function ends with `_mcp`
- Verify `@tool()` decorator is used correctly
- Check `__all__` exports both functions


#### 4. **Module Import Errors**
```
ModuleNotFoundError: No module named 'app'
```

**Solution**: Run from project root and ensure virtual environment is activated:
```bash
# From project root
python -m app
```

### Debugging Tips

1. **Enable Debug Logging**
   ```bash
   LOG_LEVEL=DEBUG
   ```

2. **Check Agent Initialization**
   ```python
   from app.agent.claude_agent import ClaudeAIAgent
   agent = ClaudeAIAgent()
   print(agent._ensure_agent())  # Should print agent ID
   ```

3. **Test Tool Directly**
    ```python
    from app.tools.tool_ado_user import add_user_to_v3e_mcp
    import asyncio
    
    async def test_ado():
        result = await add_user_to_v3e_mcp({"email": "test@example.com"})
        print(result)  # Should print user addition result
    
    asyncio.run(test_ado())
    ```

4. **Inspect MCP Servers**
   ```python
   from app.agent.agent_support import load_mcp_servers_helper
   servers = load_mcp_servers_helper()
   print(f"Loaded {len(servers)} MCP servers")
   ```

---

## Contributing

### Development Workflow

1. Create a feature branch
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make changes and test
   ```bash
   python test_claude_agent.py
   ```

3. Update documentation if needed

4. Commit with clear messages
   ```bash
   git commit -m "Add: New tool "
   ```

5. Create pull request

### Code Style

- Follow PEP 8 Python style guide
- Use type hints for function parameters and returns
- Add docstrings to all functions and classes
- Use centralized logging: `from app.common.utils import get_logger`

### Testing Guidelines

- Write tests for all new tools
- Test both direct tool calls and via agent
- Include edge cases and error handling
- Verify tool auto-discovery works



## 🚀 Quick Start: Creating Your First Agent

**New to agent creation? Follow these 4 essential steps:**

1. **Configure `.env`** - Set `AGENT_NAME`, `AGENT_DESCRIPTION`, and `AIPLATFORM_API_KEY`
2. **Define skills** - Edit [`app/agent/agent_skills.json`](app/agent/agent_skills.json) with your agent's capabilities
3. **Create prompt** - Add your system prompt to [`app/prompts/agent_system_prompt.txt`](app/prompts/agent_system_prompt.txt)
4. **Add tools** - Create custom tools in [`app/tools/`](app/tools/) (optional - auto-discovery enabled)

**That's it! Your agent is ready to deploy.** 🎉

---

## 🚀 Creating New Agents

This section provides a step-by-step guide for creating new A2A-compliant agents using the existing framework. The agent creation process involves four main components: environment configuration, skills definition, prompt creation, and tool integration.

### Overview of Agent Creation Workflow

```
1. Environment Configuration (.env) → 2. Agent Skills (agent_skills.json) →
3. System Prompt (agent_system_prompt.txt) → 4. Tools (app/tools/) →
5. Agent Ready for Deployment
```

### Step 1: Configure Environment Variables

Create or update your `.env` file with the following essential settings:

#### Required Basic Configuration
```bash
# AI Platform Settings
AIPLATFORM_API_KEY=your-api-key-here
AIPLATFORM_BASE_URL=https://aiapidev.3ecompany.com
MODEL=baseten/deepseek-ai/deepseek-v3.1

# Agent Identity
AGENT_NAME=Your Agent Name
AGENT_DESCRIPTION=Describe what your agent does
AGENT_VERSION=1.0.0
```

#### Agent Behavior Configuration
```bash
# System Prompt (can also use file-based approach)
AGENT_SYSTEM_PROMPT=You are a helpful AI assistant specialized in...

# Agent Skills Configuration
AGENT_SKILLS_FILE=app/agent/agent_skills.json
```

#### Optional Advanced Settings
```bash
# Model Parameters
MODEL_TEMPERATURE=0.6
MODEL_MAX_TOKENS=1000
MODEL_TOP_P=0.9
MODEL_TOP_K=50

# Claude SDK Options
AGENT_PERMISSION_MODE=acceptEdits
AGENT_MAX_TURNS=10
USE_TOOL_CALLBACK=false
```

### Step 2: Define Agent Capabilities (agent_skills.json)

Create or modify [`app/agent/agent_skills.json`](app/agent/agent_skills.json) to define your agent's capabilities:

```json
[
  {
    "id": "your_agent_skill_id",
    "name": "Your Agent Skill Name",
    "description": "Detailed description of what your agent can do and its purpose",
    "tags": ["tag1", "tag2", "tag3"],
    "examples": [
      "Example request 1 that your agent can handle",
      "Example request 2 showing different capability",
      "Example request 3 demonstrating advanced features"
    ]
  }
]
```

#### Skills Configuration Fields:
- **`id`**: Unique identifier for the skill (used internally)
- **`name`**: Human-readable skill name
- **`description`**: Detailed explanation of capabilities
- **`tags`**: Array of tags for categorization and discovery
- **`examples`**: Sample requests that demonstrate the skill's usage

### Step 3: Create System Prompt

Choose one of two approaches for your agent's system prompt:

#### Option A: File-Based Prompt (Recommended)
Create [`app/prompts/agent_system_prompt.txt`](app/prompts/agent_system_prompt.txt):

```txt
You are the [Your Agent Name].

Your workflow is:
1. [Step 1 of your agent's workflow]
2. [Step 2 of your agent's workflow]
3. [Step 3 of your agent's workflow]

Always return [desired response format].

NOTE: This prompt is loaded from app/prompts/agent_system_prompt.txt (FILE-BASED PROMPT)
```

#### Option B: Environment Variable Prompt
Set the prompt in your `.env` file:

```bash
AGENT_SYSTEM_PROMPT=You are a helpful AI assistant specialized in...
```

**Note**: File-based prompts take precedence over environment variables.

### Step 4: Implement Tools (Optional)

If your agent needs custom tools, create them in the [`app/tools/`](app/tools/) directory:

#### Tool Creation Pattern
```python
# app/tools/tool_your_tool.py
from __future__ import annotations
import logging
from typing import Any
from claude_agent_sdk import tool

logger = logging.getLogger(__name__)

def your_tool_function(param1: str, param2: int) -> str:
    """Core tool implementation."""
    # Your tool logic here
    return f"Processed: {param1} with {param2}"

@tool("your_tool_name", "Description of your tool", {"param1": str, "param2": int})
async def your_tool_mcp(args: dict[str, Any]) -> dict[str, Any]:
    """MCP wrapper for your tool."""
    param1 = args.get("param1", "")
    param2 = args.get("param2", 0)
    
    try:
        result = your_tool_function(param1, param2)
        return {
            "content": [
                {"type": "text", "text": result}
            ]
        }
    except Exception as e:
        error_msg = f"Error: {e}"
        logger.error(error_msg)
        return {"content": [{"type": "text", "text": error_msg}]}

__all__ = ["your_tool_function", "your_tool_mcp"]
```

#### Tool Auto-Discovery
Tools are automatically discovered by the system:
- Tool files must follow pattern: `tool_<name>.py`
- MCP wrapper functions must end with `_mcp`
- Use `@tool()` decorator for proper registration
- Export both functions in `__all__`

### Step 5: Test Your Agent

#### Basic Testing
```bash
# Start the server
python -m app

# Test with curl or any HTTP client
curl -X POST http://localhost:10005 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "send",
    "params": {
      "message": {
        "parts": [{"kind": "text", "text": "Hello, what can you do?"}]
      },
      "contextId": "test-session-123"
    }
  }'

```

Here's a complete example of creating a document processing agent:

#### 1. Environment Configuration
```bash
AGENT_NAME=Document Processing Agent
AGENT_DESCRIPTION=Specializes in document analysis, text extraction, and content summarization
AGENT_SYSTEM_PROMPT=You are a document processing expert that analyzes and summarizes documents.
```

#### 2. Skills Configuration
```json
[
  {
    "id": "document_processing_skill",
    "name": "Document Processing",
    "description": "Analyzes documents, extracts text, and provides summaries",
    "tags": ["documents", "text-processing", "analysis", "summarization"],
    "examples": [
      "Analyze this PDF document and provide a summary",
      "Extract key information from this document",
      "Process and categorize this text content"
    ]
  }
]
```

#### 3. System Prompt
```txt
You are the v3e Organization Access Bot.

Your workflow is:
1. Extract email address from the JIRA description
2. Use add_user_to_v3e tool to add the user to Azure DevOps

STRICT CONSTRAINTS:
- TARGET ORG: 'v3e'
- TARGET PROJECT: 'eee'
- ACCESS LEVEL: 'Basic'
- GROUP: 'Project Contributors'

LOGIC:
- If you find an email address: Call the 'add_user_to_v3e' tool immediately.
- If NO email address is found: Stop and respond exactly with "ERROR: MISSING_EMAIL".
- If the request is not related to access: Stop and respond exactly with "ERROR: INVALID_REQUEST".

DO NOT ask the user for missing information. You are a background worker.
```

#### 4. Tool Implementation
```python
# app/tools/tool_ado_user.py
from __future__ import annotations
import logging
from typing import Any
from claude_agent_sdk import tool
from app.config import AppConfig

logger = logging.getLogger(__name__)

def add_user_to_v3e_tool(email: str) -> str:
    """Add user to Azure DevOps organization."""
    # Your Azure DevOps logic here
    return f"SUCCESS: Added {email} to v3e/eee"

@tool("add_user_to_v3e", "Add a user to the v3e Azure DevOps organization", {"email": str})
async def add_user_to_v3e_mcp(args: dict[str, Any]) -> dict[str, Any]:
    """MCP wrapper for Azure DevOps user management tool."""
    email = args.get("email", "")
    
    try:
        result = add_user_to_v3e_tool(email)
        return {"content": [{"type": "text", "text": result}]}
    except Exception as e:
        error_msg = f"Error adding user: {e}"
        logger.error(error_msg)
        return {"content": [{"type": "text", "text": error_msg}]}

__all__ = ["add_user_to_v3e_tool", "add_user_to_v3e_mcp"]
```

### Agent Creation Best Practices

#### 1. Configuration Management
- Use file-based prompts for better version control
- Keep sensitive data in environment variables
- Test configuration changes in development first

#### 2. Skills Definition
- Be specific in skill descriptions
- Provide comprehensive examples
- Use relevant tags for discoverability

#### 3. Tool Development
- Follow naming conventions consistently
- Include proper error handling
- Add logging for debugging


#### 4. Prompt Engineering
- Be clear and specific about expected behavior
- Include workflow steps when applicable
- Specify response formats for consistency

#### 5. Testing Strategy
- Test individual components first
- Verify tool auto-discovery works
- Test end-to-end agent functionality
- Include edge cases in testing


### Advanced Agent Features

#### Custom Tool Callbacks
Implement security and control over tool usage:

```python
# app/agent/tool_callbacks.py
from claude_agent_sdk import (
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext
)
from app.common.utils import get_logger

logger = get_logger(__name__)

async def security_callback(
    tool_name: str,
    input_data: dict,
    context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    """Security callback - validates tool usage based on tool name and input."""
    
    logger.info(f"Security callback evaluating tool: {tool_name}")
    
    # Always allow read-only operations
    if tool_name in ["Read", "Glob", "Grep", "ListMcpResources", "ReadMcpResource"]:
        return PermissionResultAllow()
    
    # Allow Azure DevOps user management tools
    if tool_name in [
        "mcp__local_tools__add_user_to_v3e"
    ]:
        return PermissionResultAllow()
    
    # Block dangerous operations
    if tool_name == "Bash":
        command = input_data.get("command", "")
        dangerous_patterns = ["rm -rf", "sudo rm", "chmod 777", "dd if="]
        
        for pattern in dangerous_patterns:
            if pattern in command:
                return PermissionResultDeny(message=f"Dangerous command detected: {pattern}")
    
    # Default deny for unknown tools
    return PermissionResultDeny(message="Tool not explicitly allowed")

async def default_callback(
    tool_name: str,
    input_data: dict,
    context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    """Default callback - allows all tools (current behavior)."""
    return PermissionResultAllow()
```

Enable in `.env`:
```bash
USE_TOOL_CALLBACK=true
TOOL_CALLBACK_METHOD=security_callback
```

**Available Callback Methods:**
- `default_callback` - Allows all tools (default behavior)
- `security_callback` - Implements security validation and tool restrictions

#### Session Management
Configure session behavior for conversation continuity:

```bash
# Enable session persistence
AGENT_PERMISSION_MODE=acceptEdits
AGENT_MAX_TURNS=10
```

#### Multi-Model Support
Configure different models for different tiers:

```bash
MODEL_HAIKU=
MODEL_OPUS=
MODEL_SONNET=
```

---

**Built with ❤️ using Claude Agent SDK and A2A Protocol**
