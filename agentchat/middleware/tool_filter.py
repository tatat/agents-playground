"""Tool filtering middleware for dynamic tool discovery."""

import json
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

import rich
from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command


class ToolSearchFilterMiddleware(AgentMiddleware[AgentState[Any], Any]):
    """Middleware that filters tools based on search tool results.

    - Intercepts tool_search/tool_search_regex/search_tools_or_skills results
    - Filters model requests to only show discovery tools + discovered tools
    - Saves tokens by hiding undiscovered tools from LLM
    """

    # Tools that are always visible (meta-tools for discovery)
    ALWAYS_VISIBLE = {
        "tool_search",
        "tool_search_regex",
        "enable_tool",
        "search_skills",
        "get_skill",
        "search_tools_or_skills",
    }

    def __init__(self, tool_registry: dict[str, BaseTool]):
        """Initialize middleware.

        Args:
            tool_registry: Registry of all available tools.
        """
        self.tool_registry = tool_registry
        self.discovered_tools: set[str] = set()

    def _get_tool_name(self, t: BaseTool | dict[str, Any]) -> str:
        """Get tool name from BaseTool or dict."""
        if isinstance(t, BaseTool):
            return t.name
        return str(t.get("name", "?"))

    def _get_tool_names(self, tools: Sequence[BaseTool | dict[str, Any]]) -> list[str]:
        """Extract tool names from a list of tools."""
        return [self._get_tool_name(t) for t in tools]

    def _filter_tools(self, tools: Sequence[BaseTool | dict[str, Any]]) -> list[BaseTool | dict[str, Any]]:
        """Filter tools to show only always-visible + discovered tools."""
        filtered: list[BaseTool | dict[str, Any]] = []
        for t in tools:
            name = self._get_tool_name(t)
            # Always include meta-tools, plus discovered tools
            if name in self.ALWAYS_VISIBLE or name in self.discovered_tools:
                filtered.append(t)
        return filtered

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Filter tools to only show discovery tools + discovered tools (sync)."""
        filtered = self._filter_tools(request.tools)
        rich.print(f"[dim]Visible tools: {self._get_tool_names(filtered)}[/dim]")
        request = request.override(tools=filtered)
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """Filter tools to only show discovery tools + discovered tools (async)."""
        filtered = self._filter_tools(request.tools)
        rich.print(f"[dim]Visible tools: {self._get_tool_names(filtered)}[/dim]")
        request = request.override(tools=filtered)
        return await handler(request)

    def _process_tool_search_result(self, request: ToolCallRequest, result: Any) -> None:
        """Process tool search results to track discovered tools."""
        tool_name = request.tool.name if request.tool else ""
        if tool_name not in ("tool_search", "tool_search_regex", "enable_tool", "search_tools_or_skills"):
            return

        # Extract tool names from the result
        # result.content may be a dict (native) or JSON string
        content = result.content if hasattr(result, "content") else result

        tool_names: set[str] = set()

        # Parse JSON string if needed
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                pass

        if isinstance(content, dict):
            # Format: {"tools": [...]} for tool_search/tool_search_regex
            tools_list = content.get("tools", [])
            if isinstance(tools_list, list):
                for t in tools_list:
                    if isinstance(t, dict) and isinstance(name := t.get("name"), str):
                        tool_names.add(name)

            # Format: {"results": [...]} for search_tools_or_skills (type="tool" only)
            results_list = content.get("results", [])
            if isinstance(results_list, list):
                for r in results_list:
                    if isinstance(r, dict) and r.get("type") == "tool":
                        if isinstance(name := r.get("name"), str):
                            tool_names.add(name)

        # Track discovered tools (no interrupt)
        for name in tool_names:
            if name in self.tool_registry and name not in self.discovered_tools:
                self.discovered_tools.add(name)
                rich.print(f"[yellow]Discovered: {name}[/yellow]")

    def _check_tool_enabled(self, request: ToolCallRequest) -> ToolMessage | None:
        """Check if tool is enabled. Returns error ToolMessage if not."""
        tool_name = request.tool.name if request.tool else ""
        if tool_name in self.ALWAYS_VISIBLE or tool_name in self.discovered_tools:
            return None
        # Tool not enabled - return error
        rich.print(f"[red]Blocked: {tool_name} (not enabled)[/red]")
        return ToolMessage(
            content=f"Error: Tool '{tool_name}' is not enabled. Use enable_tool('{tool_name}') first.",
            tool_call_id=request.tool_call.get("id", ""),
        )

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        """Intercept search tool results to track discovered tools (sync)."""
        if error := self._check_tool_enabled(request):
            return error
        result = handler(request)
        self._process_tool_search_result(request, result)
        return result

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        """Intercept search tool results to track discovered tools (async)."""
        if error := self._check_tool_enabled(request):
            return error
        result = await handler(request)
        self._process_tool_search_result(request, result)
        return result
