"""Agent creation and configuration."""

from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware, SummarizationMiddleware
from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.tools import BaseTool
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph

from .llm import create_chat_model
from .middleware import SkillSuggestMiddleware, TokenUsageLoggingMiddleware, ToolSearchFilterMiddleware
from .tools import (
    TOOL_REGISTRY,
    create_execute_code_tool,
    discover_mcp_servers,
    load_mcp_tools_to_registry,
    register_builtin_tools,
    tool_search_regex,
)
from .tools.sandbox import is_srt_available

# SRT sandbox settings (project root)
SRT_SETTINGS_PATH = Path(__file__).parent.parent / "srt-settings.json"

# SQLite checkpoint database path
CHECKPOINT_DB_PATH = Path(__file__).parent.parent / "tmp" / "checkpoints.db"

PROGRAMMATIC_SYSTEM_PROMPT = """You are a helpful assistant with programmatic tool calling capabilities.

Available tools:
- tool_search_regex: Search for tools by regex pattern. Returns tool schemas.
- execute_code: Run Python code in a secure sandbox with tool_call(name, **kwargs).

Workflow:
1. When the user asks about capabilities, use tool_search_regex to discover relevant tools.
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

Use tool_search_regex to find available tools, then use them to help the user."""


async def create_programmatic_agent(
    model_name: str | None = None,
    system_prompt: str | None = None,
) -> tuple[CompiledStateGraph[Any], AsyncSqliteSaver, AsyncExitStack]:
    """Create a programmatic mode agent with sandbox execution.

    Args:
        model_name: The Claude model to use.
        system_prompt: Custom system prompt (optional).

    Returns:
        Tuple of (agent, checkpointer, exit_stack). Caller must keep exit_stack
        alive for MCP tool usage and checkpointer lifecycle.

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

    # Load MCP tools if servers exist
    exit_stack = AsyncExitStack()
    if discover_mcp_servers():
        exit_stack, _ = await load_mcp_tools_to_registry()

    # Create execute_code tool with access to registry
    execute_code = create_execute_code_tool(TOOL_REGISTRY, srt_settings=SRT_SETTINGS_PATH)
    tools: list[BaseTool] = [tool_search_regex, execute_code]

    # Create the model
    model = create_chat_model(model_name)

    # Create checkpointer for conversation persistence
    CHECKPOINT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    checkpointer = await exit_stack.enter_async_context(AsyncSqliteSaver.from_conn_string(str(CHECKPOINT_DB_PATH)))

    # Create the agent
    agent: CompiledStateGraph[Any] = create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt or PROGRAMMATIC_SYSTEM_PROMPT,
        checkpointer=checkpointer,
        middleware=[
            TokenUsageLoggingMiddleware(),
            SummarizationMiddleware(
                model=model,
                trigger=("fraction", 0.7),
                keep=("messages", 20),
            ),
        ],
    )

    return agent, checkpointer, exit_stack


class DirectModeAgentFactory:
    """Factory for creating direct mode agents with dynamic tool filtering.

    Uses filter pattern: all tools registered upfront, middleware filters visibility.
    """

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
        self.checkpointer: AsyncSqliteSaver | None = None
        self.middleware = ToolSearchFilterMiddleware(TOOL_REGISTRY)
        self.hitl_tools = hitl_tools or set()
        self.mcp_tools: list[BaseTool] = []
        self._exit_stack: AsyncExitStack | None = None
        self._agent: CompiledStateGraph[Any] | None = None

    async def initialize(self) -> AsyncExitStack:
        """Initialize the factory by registering tools and checkpointer.

        Returns:
            Exit stack for resource management.
        """
        register_builtin_tools()

        exit_stack = AsyncExitStack()

        # Initialize SQLite checkpointer
        CHECKPOINT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.checkpointer = await exit_stack.enter_async_context(
            AsyncSqliteSaver.from_conn_string(str(CHECKPOINT_DB_PATH))
        )

        # Load MCP tools if servers exist
        if discover_mcp_servers():
            mcp_stack, self.mcp_tools = await load_mcp_tools_to_registry()
            await exit_stack.enter_async_context(mcp_stack)

        self._exit_stack = exit_stack
        return exit_stack

    def create_agent(self) -> CompiledStateGraph[Any]:
        """Create an agent with all tools registered.

        Middleware filters which tools are visible to the LLM based on
        tool_search discoveries.

        Returns:
            Compiled agent graph.
        """
        # Return cached agent if available
        if self._agent is not None:
            return self._agent

        # Register ALL tools - middleware will filter visibility
        tools: list[BaseTool] = [tool_search_regex]
        tools.extend(TOOL_REGISTRY.values())
        tools.extend(self.mcp_tools)

        # Build middleware list
        middlewares: list[AgentMiddleware[Any, Any]] = [
            self.middleware,
            SkillSuggestMiddleware(top_k=3),
            TokenUsageLoggingMiddleware(),
            SummarizationMiddleware(
                model=self.model,
                trigger=("fraction", 0.7),
                keep=("messages", 20),
            ),
        ]

        # Add HITL middleware for tools that require approval
        # Note: HITL applies even before discovery since all tools are registered
        if self.hitl_tools:
            middlewares.append(HumanInTheLoopMiddleware(interrupt_on={name: True for name in self.hitl_tools}))

        self._agent = create_agent(
            model=self.model,
            tools=tools,
            system_prompt=self.system_prompt,
            middleware=middlewares,
            checkpointer=self.checkpointer,
        )

        return self._agent
