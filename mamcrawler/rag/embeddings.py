"""
Unified embedding service for RAG system.
Singleton pattern to avoid loading the model multiple times.
"""

from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from mamcrawler.config import RAGConfig, DEFAULT_RAG_CONFIG


class EmbeddingService:
    """
    Singleton service for text embeddings.

    Uses SentenceTransformers to generate embeddings with optional L2 normalization
    for FAISS compatibility.
    """

    _instance = None
    _initialized = False

    def __new__(cls, config: RAGConfig = None):
        """Singleton pattern - only create one instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: RAGConfig = None):
        """
        Initialize the embedding service.

        Args:
            config: RAG configuration (uses defaults if not provided)
        """
        if self._initialized:
            return

        self.config = config or DEFAULT_RAG_CONFIG
        print(f"Loading embedding model: {self.config.model_name}")
        self.model = SentenceTransformer(self.config.model_name)
        self._initialized = True

    def encode(self, texts: List[str], normalize: bool = True) -> np.ndarray:
        """
        Encode texts to embeddings.

        Args:
            texts: List of texts to encode
            normalize: Whether to L2 normalize (required for FAISS)

        Returns:
            Numpy array of embeddings (float32)
        """
        if not texts:
            return np.array([], dtype=np.float32).reshape(0, self.dimension)

        embeddings = self.model.encode(texts)
        embeddings = embeddings.astype(np.float32)

        if normalize:
            faiss.normalize_L2(embeddings)

        return embeddings

    def encode_query(self, query: str) -> np.ndarray:
        """
        Encode a single query for search.

        Args:
            query: The query string

        Returns:
            Normalized embedding array with shape (1, dimension)
        """
        return self.encode([query])

    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        return self.config.dimension


# Module-level function for convenience
_service = None


def get_embedding_service(config: RAGConfig = None) -> EmbeddingService:
    """
    Get the embedding service singleton.

    Args:
        config: Optional custom config (only used on first call)

    Returns:
        EmbeddingService instance
    """
    global _service
    if _service is None:
        _service = EmbeddingService(config)
    return _service


def encode_texts(texts: List[str], normalize: bool = True) -> np.ndarray:
    """
    Convenience function to encode texts.

    Args:
        texts: List of texts to encode
        normalize: Whether to L2 normalize

    Returns:
        Numpy array of embeddings
    """
    return get_embedding_service().encode(texts, normalize)
