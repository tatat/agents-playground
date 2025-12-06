"""Tool search functionality for dynamic tool discovery."""

import re
from typing import Any

from langchain_core.tools import tool

from .registry import TOOL_REGISTRY

PAGE_SIZE = 5


@tool
def tool_search(pattern: str, page: int = 1) -> dict[str, Any]:
    """Search for available tools by regex pattern.

    Use this to discover tools before calling them with execute_code.
    Use specific patterns to minimize results and save tokens.

    Args:
        pattern: Regex pattern to match against tool names and descriptions.
            Use specific patterns like "weather" or "email" instead of broad ones like ".*".
        page: Page number for pagination (1-indexed, default 1).

    Returns:
        {"tools": [...], "message": "...", "page": N, "total": N}
        {"tools": []} if no tools found.
        {"error": "..."} if the regex pattern is invalid.

    Example:
        tool_search("weather") -> {"tools": [{"name": "get_weather", ...}], ...}
        tool_search("email|calendar") -> tools matching email or calendar
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
