from mcp.server.fastmcp import FastMCP

mcp = FastMCP("String")


@mcp.tool(name="string__uppercase")
def uppercase(text: str) -> str:
    """Convert text to uppercase."""
    return text.upper()


@mcp.tool(name="string__reverse")
def reverse(text: str) -> str:
    """Reverse a string."""
    return text[::-1]


if __name__ == "__main__":
    mcp.run(transport="stdio")
