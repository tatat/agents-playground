"""Unified search tool for tools and skills."""

from typing import Any, Literal

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from .embeddings import SearchableIndex


class SearchToolsOrSkillsInput(BaseModel):
    """Input schema for unified search tool."""

    query: str = Field(description="Natural language search query.")
    types: list[Literal["tool", "skill"]] = Field(
        default=["tool", "skill"],
        description="Resource types to search.",
    )
    top_k: int = Field(default=5, description="Maximum results to return.")


class SearchToolsOrSkillsTool(BaseTool):
    """Unified search tool for tools and skills."""

    name: str = "search_tools_or_skills"
    description: str = (
        "Search across both tools and skills by natural language query. "
        "Tools are executable functions; skills are prompts/guides to follow. "
        "Use when you want to discover all available capabilities at once, "
        "or when unsure whether the capability is a tool or skill."
    )
    args_schema: type[BaseModel] = SearchToolsOrSkillsInput

    _tool_index: SearchableIndex
    _skill_index: SearchableIndex

    def __init__(
        self,
        *,
        tool_index: SearchableIndex,
        skill_index: SearchableIndex,
        **kwargs: Any,
    ) -> None:
        """Initialize with indexes."""
        super().__init__(**kwargs)
        self._tool_index = tool_index
        self._skill_index = skill_index

    async def _arun(
        self,
        query: str,
        types: list[Literal["tool", "skill"]] | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Search across tools and skills.

        Args:
            query: Natural language search query.
            types: Resource types to search (default: both).
            top_k: Maximum results to return.

        Returns:
            {"results": [{"type": "tool"|"skill", "name": str, ...}]}
        """
        if types is None:
            types = ["tool", "skill"]

        results: list[dict[str, Any]] = []

        if "tool" in types:
            tool_results = await self._tool_index.search(query, top_k)
            results.extend({"type": "tool", **r} for r in tool_results)

        if "skill" in types:
            skill_results = await self._skill_index.search(query, top_k)
            results.extend({"type": "skill", **r} for r in skill_results)

        # Sort by score (higher is better) and take top_k
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return {"results": results[:top_k]}

    def _run(self, **kwargs: Any) -> Any:
        """Sync run not supported."""
        raise NotImplementedError("Use async")
