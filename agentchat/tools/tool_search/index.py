"""Tool index using LanceDB for hybrid search."""

import tempfile
from typing import Any

import lancedb
import numpy as np
from lancedb.pydantic import LanceModel, Vector
from lancedb.rerankers import RRFReranker
from langchain_core.tools import BaseTool
from numpy.typing import NDArray

from ..embeddings import encode_query as _encode_query
from ..embeddings import get_embeddings


class ToolIndex:
    """In-memory tool index using LanceDB for hybrid search."""

    def __init__(self) -> None:
        self._temp_dir = tempfile.mkdtemp(prefix="lancedb_tools_")
        self.db = lancedb.connect(self._temp_dir)
        self.table: Any = None
        self._tool_schemas: dict[str, dict[str, Any]] = {}

    def encode_query(self, query: str) -> NDArray[np.float32]:
        """Encode a query string to a vector, using shared cache.

        Args:
            query: The query string to encode.

        Returns:
            The embedding vector as numpy array.
        """
        return _encode_query(query)

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

        results = self.table.search(query, query_type="hybrid").rerank(reranker=reranker).limit(top_k).to_list()

        return self._format_results(results)

    def search_with_vector(
        self, vector: NDArray[np.float32], query: str, top_k: int = 5
    ) -> list[dict[str, Any]]:
        """Search tools using pre-computed vector for hybrid search.

        Args:
            vector: Pre-computed query embedding vector.
            query: Original query string (for FTS component of hybrid search).
            top_k: Number of results to return.

        Returns:
            List of tool schemas with scores.
        """
        if self.table is None:
            return []

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
