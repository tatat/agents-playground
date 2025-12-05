from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Math")


@mcp.tool(name="math__add")
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@mcp.tool(name="math__multiply")
def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b


if __name__ == "__main__":
    mcp.run(transport="stdio")
