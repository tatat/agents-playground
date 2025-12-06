"""Dynamic tool middleware for tool discovery pattern."""

from typing import Any

import rich
from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.tools import BaseTool
from langgraph.types import interrupt


class DynamicToolMiddleware(AgentMiddleware[Any, Any]):
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

    def _process_tool_search_result(self, request: Any, result: Any) -> None:
        """Process tool_search results to track discovered tools."""
        tool_name = request.tool.name if hasattr(request.tool, "name") else ""
        if tool_name != "tool_search":
            return

        # Extract tool names from the result
        content = str(result.content) if hasattr(result, "content") else str(result)
        new_discoveries = False
        for name in self.tool_registry:
            if name in content and name not in self.discovered_tools:
                self.discovered_tools.add(name)
                new_discoveries = True
        rich.print(f"[dim]Discovered tools: {self.discovered_tools}[/dim]")

        # Interrupt to allow tools to be added
        if new_discoveries:
            interrupt(
                {
                    "type": self.INTERRUPT_TYPE,
                    "discovered_tools": list(self.discovered_tools),
                }
            )

    def wrap_tool_call(self, request: Any, handler: Any) -> Any:
        """Intercept tool_search results to track discovered tools (sync)."""
        result = handler(request)
        self._process_tool_search_result(request, result)
        return result

    async def awrap_tool_call(self, request: Any, handler: Any) -> Any:
        """Intercept tool_search results to track discovered tools (async)."""
        result = await handler(request)
        self._process_tool_search_result(request, result)
        return result
