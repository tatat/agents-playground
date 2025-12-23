"""MCP (Model Context Protocol) tool loading from mcp_servers/ directory."""

from contextlib import AsyncExitStack
from pathlib import Path

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import Connection, StdioConnection
from langchain_mcp_adapters.tools import load_mcp_tools as _load_mcp_tools

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


async def load_mcp_tools(
    servers_dir: Path | None = None,
) -> tuple[AsyncExitStack, list[BaseTool]]:
    """Load MCP tools from servers.

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
    config: dict[str, Connection] = {}
    for name, path in servers.items():
        config[name] = StdioConnection(
            transport="stdio",
            command="python",
            args=[str(path.resolve())],
        )

    client = MultiServerMCPClient(config)
    stack = AsyncExitStack()
    tools: list[BaseTool] = []

    for name in servers:
        session = await stack.enter_async_context(client.session(name))
        server_tools = await _load_mcp_tools(session)
        tools.extend(server_tools)

    return stack, tools
