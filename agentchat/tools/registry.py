"""Tool registry for managing available tools."""

from langchain_core.tools import BaseTool

# Global tool registry: name -> tool
TOOL_REGISTRY: dict[str, BaseTool] = {}


def register_tool(tool: BaseTool) -> None:
    """Register a tool in the global registry.

    Args:
        tool: The tool to register.
    """
    TOOL_REGISTRY[tool.name] = tool


def get_tool(name: str) -> BaseTool | None:
    """Get a tool by name from the registry.

    Args:
        name: The name of the tool.

    Returns:
        The tool if found, None otherwise.
    """
    return TOOL_REGISTRY.get(name)


def get_all_tools() -> list[BaseTool]:
    """Get all registered tools.

    Returns:
        List of all tools.
    """
    return list(TOOL_REGISTRY.values())
