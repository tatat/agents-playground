"""Agent creation and configuration."""

from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph

from .llm import create_chat_model
from .middleware import DynamicToolMiddleware
from .tools import (
    TOOL_REGISTRY,
    create_execute_code_tool,
    discover_mcp_servers,
    load_mcp_tools_to_registry,
    register_builtin_tools,
    tool_search,
)
from .tools.sandbox import is_srt_available

# SRT sandbox settings (project root)
SRT_SETTINGS_PATH = Path(__file__).parent.parent / "srt-settings.json"

PROGRAMMATIC_SYSTEM_PROMPT = """You are a helpful assistant with programmatic tool calling capabilities.

Available tools:
- tool_search: Search for available tools by regex pattern. Returns tool schemas.
- execute_code: Run Python code in a secure sandbox with tool_call(name, **kwargs).

Workflow:
1. When the user asks about capabilities, use tool_search to discover relevant tools.
2. Use execute_code with tool_call() to invoke multiple tools efficiently in a single batch.
3. Aggregate results and provide a clear summary to the user.

Example execute_code usage:
```python
sales = await tool_call("query_sales", region="west")
weather = await tool_call("get_weather", city="Sydney")
print(f"West region revenue: ${sales['revenue']}")
print(f"Sydney weather: {weather['condition']}, {weather['temp']}°C")
```

Always print() your results in execute_code - only printed output is returned."""

DIRECT_SYSTEM_PROMPT = """You are a helpful assistant.

Use tool_search to find available tools, then use them to help the user."""


async def create_programmatic_agent(
    model_name: str | None = None,
    system_prompt: str | None = None,
    use_mcp: bool = True,
) -> tuple[CompiledStateGraph[Any], AsyncExitStack]:
    """Create a programmatic mode agent with sandbox execution.

    Args:
        model_name: The Claude model to use.
        system_prompt: Custom system prompt (optional).
        use_mcp: Whether to load MCP tools from mcp_servers/ directory.

    Returns:
        Tuple of (agent, exit_stack). Caller must keep exit_stack alive
        for MCP tool usage.

    Raises:
        RuntimeError: If sandbox-runtime is not available.
    """
    if not is_srt_available():
        raise RuntimeError(
            "sandbox-runtime (srt) is required for programmatic tool calling.\n"
            "Install with: npm install -g @anthropic-ai/sandbox-runtime\n"
            "Or ensure Node.js/npx is available."
        )

    # Register built-in tools
    register_builtin_tools()

    # Load MCP tools if enabled and servers exist
    exit_stack = AsyncExitStack()
    if use_mcp and discover_mcp_servers():
        exit_stack, _ = await load_mcp_tools_to_registry()

    # Create execute_code tool with access to registry
    execute_code = create_execute_code_tool(TOOL_REGISTRY, srt_settings=SRT_SETTINGS_PATH)
    tools: list[BaseTool] = [tool_search, execute_code]

    # Create the model
    model = create_chat_model(model_name)

    # Create checkpointer for conversation persistence
    checkpointer = InMemorySaver()

    # Create the agent
    agent: CompiledStateGraph[Any] = create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt or PROGRAMMATIC_SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )

    return agent, exit_stack


class DirectModeAgentFactory:
    """Factory for creating direct mode agents with dynamic tool discovery."""

    def __init__(
        self,
        model_name: str | None = None,
        system_prompt: str | None = None,
        hitl_tools: set[str] | None = None,
    ):
        """Initialize the factory.

        Args:
            model_name: The model to use (defaults to provider default).
            system_prompt: Custom system prompt (optional).
            hitl_tools: Tool names that require human approval before execution.
        """
        self.model = create_chat_model(model_name)
        self.system_prompt = system_prompt or DIRECT_SYSTEM_PROMPT
        self.checkpointer = InMemorySaver()
        self.middleware = DynamicToolMiddleware(TOOL_REGISTRY)
        self.hitl_tools = hitl_tools or set()
        self.mcp_tools: list[BaseTool] = []

    async def initialize(self, use_mcp: bool = True) -> AsyncExitStack:
        """Initialize the factory by registering tools.

        Args:
            use_mcp: Whether to load MCP tools.

        Returns:
            Exit stack for MCP session management.
        """
        register_builtin_tools()

        exit_stack = AsyncExitStack()
        if use_mcp and discover_mcp_servers():
            exit_stack, self.mcp_tools = await load_mcp_tools_to_registry()

        return exit_stack

    def create_agent(self, discovered_tools: set[str] | None = None) -> CompiledStateGraph[Any]:
        """Create an agent with tool_search + discovered tools.

        Args:
            discovered_tools: Set of tool names to include (from registry).

        Returns:
            Compiled agent graph.
        """
        tools: list[BaseTool] = [tool_search]

        if discovered_tools:
            for name in discovered_tools:
                if name in TOOL_REGISTRY:
                    tools.append(TOOL_REGISTRY[name])

        # Add MCP tools if they were discovered
        for mcp_tool in self.mcp_tools:
            if discovered_tools and mcp_tool.name in discovered_tools:
                tools.append(mcp_tool)

        # Build middleware list
        middlewares: list[DynamicToolMiddleware | HumanInTheLoopMiddleware] = [self.middleware]

        # Add HITL middleware for discovered tools that require approval
        if self.hitl_tools and discovered_tools:
            hitl_targets = self.hitl_tools & discovered_tools
            if hitl_targets:
                middlewares.append(HumanInTheLoopMiddleware(interrupt_on={name: True for name in hitl_targets}))

        return create_agent(
            model=self.model,
            tools=tools,
            system_prompt=self.system_prompt,
            middleware=middlewares,
            checkpointer=self.checkpointer,
        )
