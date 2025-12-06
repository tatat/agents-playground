"""MCP (Model Context Protocol) tool loading from mcp_servers/ directory."""

from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient  # type: ignore[import-untyped]
from langchain_mcp_adapters.tools import load_mcp_tools  # type: ignore[import-untyped]

from .registry import register_tool

# Default path for MCP servers
MCP_SERVERS_DIR = Path(__file__).parent.parent.parent / "mcp_servers"


def discover_mcp_servers(servers_dir: Path | None = None) -> dict[str, Path]:
    """Discover MCP server files in the directory.

    Args:
        servers_dir: Directory containing MCP server Python files.
                    Defaults to mcp_servers/ in project root.

    Returns:
        Dict mapping server name (without _server suffix) to file path.
    """
    if servers_dir is None:
        servers_dir = MCP_SERVERS_DIR

    if not servers_dir.exists():
        return {}

    servers: dict[str, Path] = {}
    for path in servers_dir.glob("*_server.py"):
        # Extract name: math_server.py -> math
        name = path.stem.removesuffix("_server")
        servers[name] = path

    return servers


async def load_mcp_tools_to_registry(
    servers_dir: Path | None = None,
) -> tuple[AsyncExitStack, list[BaseTool]]:
    """Load MCP tools from servers and register them.

    Args:
        servers_dir: Directory containing MCP server Python files.

    Returns:
        Tuple of (exit_stack, tools). Caller must keep exit_stack alive
        for the duration of tool usage.
    """
    servers = discover_mcp_servers(servers_dir)
    if not servers:
        return AsyncExitStack(), []

    # Build MCP client config
    config: dict[str, dict[str, Any]] = {}
    for name, path in servers.items():
        config[name] = {
            "command": "python",
            "args": [str(path.resolve())],
            "transport": "stdio",
        }

    client = MultiServerMCPClient(config)
    stack = AsyncExitStack()
    tools: list[BaseTool] = []

    for name in servers:
        session = await stack.enter_async_context(client.session(name))
        server_tools = await load_mcp_tools(session)
        tools.extend(server_tools)

        # Register each tool
        for tool in server_tools:
            register_tool(tool)

    return stack, tools
