"""Tool search functionality for dynamic tool discovery."""

import re
from typing import Any

from langchain_core.tools import tool

from .registry import TOOL_REGISTRY


@tool
def tool_search(pattern: str) -> list[dict[str, Any]]:
    """Search for available tools by regex pattern.

    Use this to discover tools before calling them with execute_code.

    Args:
        pattern: Regex pattern to match against tool names and descriptions.

    Returns:
        List of matching tool schemas with name, description, and parameters.
        Empty list if no tools found.

    Example:
        tool_search("weather") -> [{"name": "get_weather", "description": "...", ...}]
        tool_search("sales|email") -> multiple matching tools
    """
    matches: list[dict[str, Any]] = []

    for name, t in TOOL_REGISTRY.items():
        name_match = re.search(pattern, name, re.IGNORECASE)
        desc_match = re.search(pattern, t.description, re.IGNORECASE)

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

    return matches
