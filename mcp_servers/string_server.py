from mcp.server.fastmcp import FastMCP

mcp = FastMCP("String")


@mcp.tool(name="string__uppercase")
def uppercase(text: str) -> dict[str, str]:
    """Convert text to uppercase.

    Args:
        text: Input text to convert.

    Returns: {"result": str} where result is the uppercase version of text.
    """
    return {"result": text.upper()}


@mcp.tool(name="string__reverse")
def reverse(text: str) -> dict[str, str]:
    """Reverse a string.

    Args:
        text: Input text to reverse.

    Returns: {"result": str} where result is the reversed text.
    """
    return {"result": text[::-1]}


if __name__ == "__main__":
    mcp.run(transport="stdio")
