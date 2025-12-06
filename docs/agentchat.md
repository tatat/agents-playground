# agentchat

Demo CLI chat application exploring LangChain/LangGraph patterns:

- **Tool Search**: Dynamic tool discovery via regex
- **Programmatic Tool Calling**: Sandboxed batch execution
- **HITL**: Human-in-the-loop approval with auto-approve

This is an experimental implementation for learning and prototyping.

## Setup

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
```

## LLM Provider

Supports Anthropic direct API (default) and AWS Bedrock.

### Anthropic (default)

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
```

### AWS Bedrock

```bash
# .env
LLM_PROVIDER=bedrock
AWS_REGION=us-east-1

# AWS credentials via standard chain (env vars, profile, IAM role)
```

### Model Override

```bash
# Anthropic
MODEL_ID=claude-sonnet-4-5-20250929

# Bedrock (Cross-Region Inference)
MODEL_ID=us.anthropic.claude-sonnet-4-5-20250929-v1:0
```

## Modes

### Direct Mode

Tools are called directly by the agent. Supports dynamic tool discovery and HITL approval.

```bash
uv run agentchat-direct
```

### Programmatic Mode

Agent generates Python code that calls multiple tools in a sandbox (via `srt`).

```bash
uv run agentchat-programmatic
```

Requires Node.js for `npx @anthropic-ai/sandbox-runtime`.

## Architecture

```
agentchat/
├── __init__.py          # Entry points (main_direct, main_programmatic)
├── agent.py             # Agent factory (DirectModeAgentFactory, create_programmatic_agent)
├── middleware.py        # DynamicToolMiddleware for tool discovery
├── ui.py                # Rich console output
├── chat/
│   ├── direct.py        # Direct mode chat loop, HITL handling
│   ├── programmatic.py  # Programmatic mode chat loop
│   └── common.py        # Shared utilities (key bindings, stream processing)
└── tools/
    ├── registry.py      # TOOL_REGISTRY, register_tool()
    ├── search.py        # tool_search() for discovering tools
    ├── sandbox.py       # create_execute_code_tool() for sandboxed execution
    ├── builtin.py       # Sample tools (weather, sales, email, calendar)
    └── mcp.py           # MCP tool loading
```

## Features

### Tool Search

Agent discovers tools dynamically using `tool_search(pattern)`:

```python
# Agent can search for tools by regex
tool_search("email|calendar")  # Returns matching tool schemas
```

### HITL (Human-in-the-Loop)

Direct mode supports approval for sensitive tools:

```python
# agentchat/chat/direct.py
class HITLToolConfig(TypedDict):
    auto_approve: NotRequired[tuple[str, ...]]

HITL_TOOLS: dict[str, HITLToolConfig] = {
    "send_email": {"auto_approve": ("to",)},     # Auto-approve same recipient
    "create_calendar_event": {},                  # Always require approval
}
```

- First call: User prompted for approval
- Subsequent calls: Auto-approved if key args match (configurable per tool)

### MCP Tools

Place MCP server Python files in `mcp_servers/*_server.py`:

```python
# mcp_servers/example_server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("example")

@mcp.tool()
def hello(name: str) -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run()
```

Tools are automatically loaded and available via `tool_search`.

## Persistence

Conversation state is persisted to SQLite using LangGraph's `AsyncSqliteSaver`.

- **Database**: `tmp/checkpoints.db`
- **Format**: msgpack-serialized checkpoints

### Dump Checkpoints

```bash
# Latest checkpoint (JSON)
uv run python scripts/dump_checkpoints.py

# List all threads
uv run python scripts/dump_checkpoints.py -l

# Multiple checkpoints
uv run python scripts/dump_checkpoints.py -n 3

# Filter by thread
uv run python scripts/dump_checkpoints.py -t <thread_id>

# With jq
uv run python scripts/dump_checkpoints.py | jq '.[0].messages'
```

## Key Bindings

- `Ctrl+J` or `Alt+Enter`: Send message
- `Enter`: New line
- `Ctrl+C` / `Ctrl+D`: Exit
- `/exit`: Exit command
