from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Math")


@mcp.tool(name="math__add")
def add(a: int, b: int) -> dict[str, int]:
    """Add two numbers.

    Args:
        a: First number.
        b: Second number.

    Returns: {"result": int} where result is the sum of a and b.
    """
    return {"result": a + b}


@mcp.tool(name="math__multiply")
def multiply(a: int, b: int) -> dict[str, int]:
    """Multiply two numbers.

    Args:
        a: First number.
        b: Second number.

    Returns: {"result": int} where result is the product of a and b.
    """
    return {"result": a * b}


if __name__ == "__main__":
    mcp.run(transport="stdio")
