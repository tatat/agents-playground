"""Tool search functionality for dynamic tool discovery."""

import re
from typing import Any

from langchain_core.tools import tool

from .registry import TOOL_REGISTRY


@tool
def tool_search(pattern: str) -> dict[str, Any]:
    """Search for available tools by regex pattern.

    Use this to discover tools before calling them with execute_code.

    Args:
        pattern: Regex pattern to match against tool names and descriptions.

    Returns:
        {"tools": [...]} with matching tool schemas (name, description, parameters).
        {"tools": []} if no tools found.
        {"error": "..."} if the regex pattern is invalid.

    Example:
        tool_search("weather") -> {"tools": [{"name": "get_weather", ...}]}
        tool_search("sales|email") -> {"tools": [...multiple tools...]}
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

    return {"tools": matches}
