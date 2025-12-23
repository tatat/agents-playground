"""Shared embeddings module with query caching."""

from functools import lru_cache
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray


class SearchableIndex(Protocol):
    """Protocol for indexes that support hybrid search with encoding."""

    def encode_query(self, query: str) -> NDArray[np.float32]:
        """Encode a query string to a vector.

        Args:
            query: The query string to encode.

        Returns:
            The embedding vector.
        """
        ...

    def search_with_vector(
        self, vector: NDArray[np.float32], query: str, top_k: int = 5
    ) -> list[dict[str, Any]]:
        """Search using pre-computed vector.

        Args:
            vector: Pre-computed query embedding vector.
            query: Original query string (for FTS component).
            top_k: Number of results to return.

        Returns:
            List of results with name, description, and score.
        """
        ...


@lru_cache(maxsize=1)
def get_embeddings() -> Any:
    """Get or create the shared embedding model (singleton).

    Returns:
        SentenceTransformer embedding function from LanceDB.
    """
    from lancedb.embeddings import get_registry

    return (
        get_registry()
        .get("sentence-transformers")
        .create(name="paraphrase-multilingual-MiniLM-L12-v2")
    )


# Simple cache for query embeddings (avoids re-encoding same query)
_query_cache: dict[str, NDArray[np.float32]] = {}
_cache_max_size = 10


def encode_query(query: str) -> NDArray[np.float32]:
    """Encode a query string to a vector, with caching.

    Args:
        query: The query string to encode.

    Returns:
        The embedding vector as numpy array.
    """
    if query in _query_cache:
        return _query_cache[query]

    embeddings = get_embeddings()
    raw = embeddings.compute_query_embeddings(query)[0]
    vector: NDArray[np.float32] = np.array(raw, dtype=np.float32)

    # Simple cache eviction: clear when full
    if len(_query_cache) >= _cache_max_size:
        _query_cache.clear()

    _query_cache[query] = vector
    return vector


def get_embedding_dims() -> int:
    """Get the dimensionality of the embedding model."""
    return int(get_embeddings().ndims())
