"""Tool index using LanceDB for hybrid search."""

import tempfile
from typing import Any

import lancedb
import rich
from lancedb.pydantic import LanceModel, Vector
from lancedb.rerankers import RRFReranker
from langchain_core.tools import BaseTool

from ..embeddings import encode_query, get_embeddings


class ToolIndex:
    """In-memory tool index using LanceDB for hybrid search.

    Supports lazy loading: index is built automatically on first search
    using the registry provided via get_tool_index(registry=...).
    """

    def __init__(self) -> None:
        self._temp_dir = tempfile.mkdtemp(prefix="lancedb_tools_")
        self.db = lancedb.connect(self._temp_dir)
        self.table: Any = None
        self._tool_schemas: dict[str, dict[str, Any]] = {}
        self._registry: dict[str, BaseTool] | None = None
        self._warned_no_registry = False

    def set_registry(self, registry: dict[str, BaseTool]) -> None:
        """Set the tool registry for lazy index building."""
        self._registry = registry

    @property
    def registry(self) -> dict[str, BaseTool]:
        """Get the tool registry."""
        return self._registry or {}

    def _ensure_index(self) -> None:
        """Build index lazily if not already built."""
        if self.table is not None:
            return

        if self._registry is None:
            if not self._warned_no_registry:
                rich.print(
                    "[yellow]Warning: ToolIndex has no registry. Call get_tool_index(registry=...) first.[/yellow]"
                )
                self._warned_no_registry = True
            return

        self.build_index(self._registry)

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

        # Get shared embedding model
        embeddings = get_embeddings()

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

    async def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search tools using hybrid search (BM25 + vector).

        Args:
            query: Natural language search query.
            top_k: Number of results to return.

        Returns:
            List of tool schemas with scores.
        """
        self._ensure_index()
        if self.table is None:
            return []

        vector = encode_query(query)
        reranker = RRFReranker()

        results = (
            self.table.search(query_type="hybrid")
            .text(query)
            .vector(vector)
            .rerank(reranker=reranker)
            .limit(top_k)
            .to_list()
        )

        return self._format_results(results)

    def _format_results(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Format search results with full schemas."""
        return [
            {
                **self._tool_schemas.get(r["name"], {"name": r["name"]}),
                "score": r.get("_relevance_score", 0.0),
            }
            for r in results
        ]


# Singleton instance
_tool_index: ToolIndex | None = None


def get_tool_index(registry: dict[str, BaseTool] | None = None) -> ToolIndex:
    """Get or create the global tool index.

    Args:
        registry: Tool registry for lazy index building. Required on first call,
                  optional on subsequent calls (uses previously set registry).

    Returns:
        The global ToolIndex instance.
    """
    global _tool_index
    if _tool_index is None:
        _tool_index = ToolIndex()

    if registry is not None:
        _tool_index.set_registry(registry)

    return _tool_index


def reset_tool_index() -> None:
    """Reset the global tool index (for rebuilding after tool registration)."""
    global _tool_index
    _tool_index = None
