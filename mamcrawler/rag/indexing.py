"""
FAISS index management for RAG system.
Unified interface for index operations.
"""

from typing import Tuple, Optional
from pathlib import Path
import numpy as np
import faiss

from ..config import RAGConfig, DEFAULT_RAG_CONFIG


class FAISSIndexManager:
    """
    Manages FAISS index for vector similarity search.

    Uses IndexIDMap to support custom IDs that correspond to database chunk IDs.
    """

    def __init__(self, config: RAGConfig = None, index_path: str = None):
        """
        Initialize the index manager.

        Args:
            config: RAG configuration
            index_path: Optional override for index file path
        """
        self.config = config or DEFAULT_RAG_CONFIG
        self.index_path = Path(index_path or self.config.index_path)
        self.index = self._load_or_create()

    def _load_or_create(self) -> faiss.Index:
        """Load existing index or create new one."""
        if self.index_path.exists():
            print(f"Loading existing index from {self.index_path}")
            return faiss.read_index(str(self.index_path))

        print(f"Creating new FAISS index (dimension={self.config.dimension})")
        base_index = faiss.IndexFlatL2(self.config.dimension)
        return faiss.IndexIDMap(base_index)

    def add(self, embeddings: np.ndarray, ids: np.ndarray):
        """
        Add embeddings with IDs to index.

        Args:
            embeddings: Embedding vectors (must be float32, L2 normalized)
            ids: Corresponding chunk IDs
        """
        if len(embeddings) == 0:
            return

        embeddings = embeddings.astype(np.float32)
        ids = ids.astype(np.int64)
        self.index.add_with_ids(embeddings, ids)

    def remove(self, ids: np.ndarray):
        """
        Remove embeddings by IDs.

        Args:
            ids: Chunk IDs to remove
        """
        if len(ids) == 0:
            return

        ids = np.array(ids, dtype=np.int64)
        self.index.remove_ids(ids)

    def search(self, query_embedding: np.ndarray, k: int = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for similar embeddings.

        Args:
            query_embedding: Query vector (must be float32, L2 normalized)
            k: Number of results to return

        Returns:
            Tuple of (distances, ids) arrays
        """
        k = k or self.config.top_k
        query_embedding = query_embedding.astype(np.float32)

        # Ensure 2D shape
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        distances, ids = self.index.search(query_embedding, k)
        return distances, ids

    def save(self):
        """Persist index to disk."""
        faiss.write_index(self.index, str(self.index_path))
        print(f"Index saved to {self.index_path}")

    @property
    def total_vectors(self) -> int:
        """Get total number of vectors in index."""
        return self.index.ntotal


# Module-level singleton
_manager = None


def get_index_manager(config: RAGConfig = None, index_path: str = None) -> FAISSIndexManager:
    """
    Get the index manager singleton.

    Args:
        config: Optional custom config
        index_path: Optional index file path

    Returns:
        FAISSIndexManager instance
    """
    global _manager
    if _manager is None:
        _manager = FAISSIndexManager(config, index_path)
    return _manager


def reset_manager():
    """Reset the singleton (useful for testing)."""
    global _manager
    _manager = None
