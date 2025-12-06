"""Custom middleware for agent functionality."""

import json
from collections.abc import Awaitable, Callable
from typing import Any

import rich
from langchain.agents.middleware.types import AgentMiddleware, AgentState
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command, interrupt


class DynamicToolMiddleware(AgentMiddleware[AgentState[Any], Any]):
    """Middleware that dynamically adds tools based on tool_search results.

    Uses interrupt to pause after tool discovery, allowing agent to be
    recreated with the new tools.
    """

    INTERRUPT_TYPE = "tool_discovery"

    def __init__(self, tool_registry: dict[str, BaseTool]):
        """Initialize middleware.

        Args:
            tool_registry: Registry of all available tools.
        """
        self.tool_registry = tool_registry
        self.discovered_tools: set[str] = set()

    def _process_tool_search_result(self, request: ToolCallRequest, result: Any) -> None:
        """Process tool_search results to track discovered tools."""
        tool_name = request.tool.name if request.tool else ""
        if tool_name != "tool_search":
            return

        # Extract tool names from the result
        # result.content may be a dict (native) or JSON string
        # Format: {"tools": [...]} or {"error": "..."}
        content = result.content if hasattr(result, "content") else result

        tool_names: set[str] = set()

        # Parse JSON string if needed
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                pass

        # Extract tools from {"tools": [...]} format
        if isinstance(content, dict):
            tools_list = content.get("tools", [])
            if isinstance(tools_list, list):
                for t in tools_list:
                    if isinstance(t, dict) and isinstance(name := t.get("name"), str):
                        tool_names.add(name)

        new_discoveries = False
        for name in tool_names:
            if name in self.tool_registry and name not in self.discovered_tools:
                self.discovered_tools.add(name)
                new_discoveries = True

        # Interrupt to allow tools to be added
        if new_discoveries:
            interrupt(
                {
                    "type": self.INTERRUPT_TYPE,
                    "discovered_tools": list(self.discovered_tools),
                }
            )

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        """Intercept tool_search results to track discovered tools (sync)."""
        result = handler(request)
        self._process_tool_search_result(request, result)
        return result

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        """Intercept tool_search results to track discovered tools (async)."""
        result = await handler(request)
        self._process_tool_search_result(request, result)
        return result


class TokenUsageLoggingMiddleware(AgentMiddleware[AgentState[Any], Any]):
    """Middleware that logs token usage for each model call."""

    def after_model(self, state: AgentState[Any], runtime: Any) -> dict[str, Any] | None:  # noqa: ARG002
        """Log token usage after model call."""
        # Get the last message from state which contains usage metadata
        messages = state.get("messages", [])
        if messages:
            last_msg = messages[-1]
            usage = getattr(last_msg, "usage_metadata", None)
            if usage is not None:
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)

                # Check for cache usage
                input_details = usage.get("input_token_details", {})
                cache_read = input_details.get("cache_read", 0)

                if cache_read:
                    rich.print(f"\n[dim]Tokens: {input_tokens} in (cache: {cache_read}) / {output_tokens} out[/dim]")
                else:
                    rich.print(f"\n[dim]Tokens: {input_tokens} in / {output_tokens} out[/dim]")

        return None
