"""Skill search and retrieval tools."""

from typing import Any

from langchain_core.tools import tool

from .index import SKILLS_DIR, get_skill_index


@tool
async def search_skills(query: str, top_k: int = 5) -> dict[str, Any]:
    """Search for skills matching a query using hybrid search.

    Skills are prompts and guides that provide instructions on how to accomplish tasks.
    Unlike tools, skills are not executed directly but followed as guidance.

    Args:
        query: Search query for skill names/descriptions.
        top_k: Number of results to return (default: 5).

    Returns:
        {"query": str, "results": [{"name": str, "description": str, "score": float}, ...]}
    """
    index = get_skill_index()
    results = await index.search(query, top_k)
    return {"query": query, "results": results}


@tool
def get_skill(name: str, path: str | None = None) -> dict[str, Any]:
    """Get detailed information about a skill.

    Args:
        name: Skill name.
        path: Optional path to a specific file within the skill directory.

    Returns:
        {"name": str, "path": str, "content": str, "other_files": [str]}
        Error: {"error": str} if skill not found.
    """
    index = get_skill_index()
    skill = index.get(name)

    if skill is None:
        return {"error": f"Skill not found: {name}"}

    # If path is specified, read that specific file (relative to skill dir)
    if path is not None:
        dir_name = skill["dir_name"]
        file_path = SKILLS_DIR / dir_name / path
        if not file_path.exists():
            return {"error": f"File not found: {path}"}
        if not file_path.is_relative_to(SKILLS_DIR / dir_name):
            return {"error": "Path must be within skill directory"}
        return {
            "name": name,
            "path": path,
            "content": file_path.read_text(encoding="utf-8"),
            "other_files": skill["other_files"],
        }

    return skill
