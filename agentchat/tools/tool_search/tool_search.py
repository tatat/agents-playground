"""Tool search tools for dynamic tool discovery."""

import re
from typing import Any

import rich
from langchain_core.tools import tool

from ..registry import TOOL_REGISTRY
from .index import get_tool_index

PAGE_SIZE = 5


@tool
def tool_search(query: str, top_k: int = 5) -> dict[str, Any]:
    """Search for tools by natural language query.

    Use when tool name is unknown. For known names, use tool_search_regex instead.

    Args:
        query: Natural language search query.
        top_k: Maximum number of results to return (default 5).

    Returns:
        {"tools": [...], "message": "..."} with matching tool schemas.
        {"tools": []} if no tools found or index unavailable.

    Example:
        tool_search("weather") -> tools related to weather
        tool_search("send notifications") -> messaging/notification tools
    """
    try:
        index = get_tool_index()

        # Build index if not yet built
        if index.table is None:
            index.build_index(TOOL_REGISTRY)

        results = index.search(query, top_k)

        if not results:
            return {"tools": [], "message": "No tools found."}

        # Remove score from results (internal detail)
        tools = [{k: v for k, v in r.items() if k != "score"} for r in results]

        return {
            "tools": tools,
            "message": f"Found {len(tools)} tool(s).",
        }

    except Exception as e:  # noqa: BLE001
        rich.print(f"[dim]Tool search error: {e}[/dim]")
        return {"tools": [], "message": "Tool search unavailable."}


@tool
def tool_search_regex(pattern: str, page: int = 1) -> dict[str, Any]:
    """Search for tools by regex pattern.

    Use for precise pattern matching. Prefer this when tool name is known.

    Args:
        pattern: Regex pattern to match against tool names and descriptions.
        page: Page number for pagination (1-indexed, default 1).

    Returns:
        {"tools": [...], "message": "...", "page": N, "total": N}
        {"tools": []} if no tools found.
        {"error": "..."} if the regex pattern is invalid.

    Example:
        tool_search_regex("^get_weather$") -> exact match for get_weather
        tool_search_regex("weather_.*") -> tools starting with weather_
        tool_search_regex("email|calendar") -> tools matching email or calendar
    """
    matches: list[dict[str, Any]] = []

    for name, t in TOOL_REGISTRY.items():
        try:
            name_match = re.search(pattern, name, re.IGNORECASE)
            desc_match = re.search(pattern, t.description, re.IGNORECASE)
        except re.error as e:
            return {"error": f"Invalid regex pattern: {e}"}

        if name_match or desc_match:
            if t.args_schema and hasattr(t.args_schema, "model_json_schema"):
                schema = t.args_schema.model_json_schema()
                schema["name"] = name
                schema["description"] = t.description
                matches.append(schema)
            else:
                matches.append(
                    {
                        "name": name,
                        "description": t.description,
                    }
                )

    total_matches = len(matches)
    total_pages = (total_matches + PAGE_SIZE - 1) // PAGE_SIZE if total_matches else 1

    # Apply pagination (1-indexed)
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    page_matches = matches[start:end]

    if not total_matches:
        message = "No tools found."
    elif total_pages == 1:
        message = f"Found {total_matches} tool(s)."
    else:
        message = f"Page {page} of {total_pages} ({total_matches} total). Use page=N for more."

    return {
        "tools": page_matches,
        "message": message,
        "page": page,
        "total": total_matches,
    }
