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
from .middleware import (
    IndexConfig,
    SuggestMiddleware,
    TokenUsageLoggingMiddleware,
    ToolSearchFilterMiddleware,
)
from .tools import (
    TOOL_REGISTRY,
    SearchToolsOrSkillsTool,
    create_execute_code_tool,
    discover_mcp_servers,
    enable_tool,
    get_skill,
    get_skill_index,
    get_tool_index,
    load_mcp_tools,
    register_builtin_tools,
    search_skills,
    tool_search,
    tool_search_regex,
)
from .tools.sandbox import is_srt_available

# SRT sandbox settings (project root)
SRT_SETTINGS_PATH = Path(__file__).parent.parent / "srt-settings.json"

# SQLite checkpoint database path
CHECKPOINT_DB_PATH = Path(__file__).parent.parent / "tmp" / "checkpoints.db"

PROGRAMMATIC_SYSTEM_PROMPT = """You are a helpful assistant with programmatic tool calling capabilities.

Available tools:
- tool_search: Search for tools by natural language (e.g., "send messages", "weather").
- tool_search_regex: Search for tools by regex pattern (e.g., "weather_.*", "send|receive").
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

Use tool_search or tool_search_regex to find available tools, then use them to help the user."""


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
    mcp_tools: list[BaseTool] = []
    if discover_mcp_servers():
        exit_stack, mcp_tools = await load_mcp_tools()

    # Build sandbox tools registry (tools callable via tool_call() in execute_code)
    sandbox_tools = {**TOOL_REGISTRY, **{t.name: t for t in mcp_tools}}
    get_tool_index(sandbox_tools)

    # Create execute_code tool with access to sandbox tools
    execute_code = create_execute_code_tool(sandbox_tools, srt_settings=SRT_SETTINGS_PATH)
    # Skill tools are for LLM reference, not for execute_code
    tools: list[BaseTool] = [tool_search, tool_search_regex, enable_tool, execute_code, search_skills, get_skill]

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

    Usage as async context manager:
        async with DirectModeAgentFactory(...) as factory:
            # factory.middleware and factory.checkpointer available
            agent = factory.create_agent()  # lazy creation
            ...
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
        self.hitl_tools = hitl_tools or set()
        self._registered_tools: dict[str, BaseTool] = {}
        self._middleware: ToolSearchFilterMiddleware | None = None
        self._exit_stack: AsyncExitStack | None = None
        self._agent: CompiledStateGraph[Any] | None = None

    async def __aenter__(self) -> "DirectModeAgentFactory":
        """Enter context: initialize resources."""
        await self._initialize()
        return self

    async def __aexit__(self, *exc: object) -> None:
        """Exit context: cleanup resources."""
        if self._exit_stack is not None:
            await self._exit_stack.aclose()
            self._exit_stack = None

    @property
    def tool_filter(self) -> ToolSearchFilterMiddleware:
        """Get the tool filter middleware (must enter context first)."""
        if self._middleware is None:
            raise RuntimeError("Use 'async with' before accessing tool_filter")
        return self._middleware

    async def _initialize(self) -> None:
        """Initialize the factory by registering tools and checkpointer."""
        register_builtin_tools()

        exit_stack = AsyncExitStack()

        # Initialize SQLite checkpointer
        CHECKPOINT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.checkpointer = await exit_stack.enter_async_context(
            AsyncSqliteSaver.from_conn_string(str(CHECKPOINT_DB_PATH))
        )

        # Load MCP tools if servers exist
        mcp_tools: list[BaseTool] = []
        if discover_mcp_servers():
            mcp_stack, mcp_tools = await load_mcp_tools()
            await exit_stack.enter_async_context(mcp_stack)

        # Build combined registry
        self._registered_tools = {**TOOL_REGISTRY, **{t.name: t for t in mcp_tools}}
        self._middleware = ToolSearchFilterMiddleware(self._registered_tools)

        self._exit_stack = exit_stack

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

        if self._middleware is None:
            raise RuntimeError("Use 'async with' before create_agent()")

        # Create indexes (shared between SuggestMiddleware and SearchToolsOrSkillsTool)
        tool_index = get_tool_index(self._registered_tools)
        skill_index = get_skill_index()

        # Create search_tools_or_skills tool with shared indexes
        search_tools_or_skills = SearchToolsOrSkillsTool(
            tool_index=tool_index,
            skill_index=skill_index,
        )

        # Register ALL tools - middleware will filter visibility
        # Skill tools are added directly (not via registry) since they're only for direct mode
        tools: list[BaseTool] = [
            tool_search,
            tool_search_regex,
            enable_tool,
            search_tools_or_skills,
            search_skills,
            get_skill,
        ]
        tools.extend(self._registered_tools.values())

        # Build middleware list
        middlewares: list[AgentMiddleware[Any, Any]] = [
            self._middleware,
            SuggestMiddleware(
                indexes=[
                    IndexConfig(
                        index=tool_index,
                        label="tool",
                        usage_hint="Use enable_tool(name) to enable tools.",
                    ),
                    IndexConfig(
                        index=skill_index,
                        label="skill",
                        usage_hint="Use get_skill(name) to retrieve full skill content.",
                    ),
                ],
                top_k=5,
            ),
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
