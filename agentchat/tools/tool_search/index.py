"""Tool index using LanceDB for hybrid search."""

import tempfile
from typing import Any

import lancedb
from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector
from lancedb.rerankers import RRFReranker
from langchain_core.tools import BaseTool


class ToolIndex:
    """In-memory tool index using LanceDB for hybrid search."""

    def __init__(self) -> None:
        self._temp_dir = tempfile.mkdtemp(prefix="lancedb_tools_")
        self.db = lancedb.connect(self._temp_dir)
        self.table: Any = None
        self._tool_schemas: dict[str, dict[str, Any]] = {}

    def build_index(self, tools: dict[str, BaseTool]) -> None:
        """Build the search index from tool registry.

        Args:
            tools: Tool registry mapping names to BaseTool instances.
        """
        if not tools:
            return

        # Prepare tool data
        tool_data: list[dict[str, Any]] = []
        for name, t in tools.items():
            description = t.description or ""

            # Store schema for later retrieval
            if t.args_schema and hasattr(t.args_schema, "model_json_schema"):
                schema = t.args_schema.model_json_schema()
                schema["name"] = name
                schema["description"] = description
                self._tool_schemas[name] = schema
            else:
                self._tool_schemas[name] = {
                    "name": name,
                    "description": description,
                }

            tool_data.append(
                {
                    "name": name,
                    "description": description,
                    "text": f"{name}\n{description}",
                }
            )

        # Get embedding model (same as SkillIndex)
        embeddings = get_registry().get("sentence-transformers").create(
            name="paraphrase-multilingual-MiniLM-L12-v2"
        )

        # Define schema with embedding
        class ToolDocument(LanceModel):  # type: ignore[misc]
            name: str
            description: str
            text: str = embeddings.SourceField()
            vector: Vector(embeddings.ndims()) = embeddings.VectorField()  # type: ignore[valid-type]

        # Create table
        self.table = self.db.create_table("tools", schema=ToolDocument, mode="overwrite")
        self.table.add(data=tool_data)

        # Create FTS index for hybrid search
        self.table.create_fts_index("text")

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search tools using hybrid search (BM25 + vector).

        Args:
            query: Natural language search query.
            top_k: Number of results to return.

        Returns:
            List of tool schemas with scores.
        """
        if self.table is None:
            return []

        reranker = RRFReranker()

        results = (
            self.table.search(query, query_type="hybrid")
            .rerank(reranker=reranker)
            .limit(top_k)
            .to_list()
        )

        # Return full schemas
        return [
            {
                **self._tool_schemas.get(r["name"], {"name": r["name"]}),
                "score": r.get("_relevance_score", 0.0),
            }
            for r in results
        ]


# Singleton instance
_tool_index: ToolIndex | None = None


def get_tool_index() -> ToolIndex:
    """Get or create the global tool index."""
    global _tool_index
    if _tool_index is None:
        _tool_index = ToolIndex()
    return _tool_index


def reset_tool_index() -> None:
    """Reset the global tool index (for rebuilding after tool registration)."""
    global _tool_index
    _tool_index = None
