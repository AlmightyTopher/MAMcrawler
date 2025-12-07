#!/usr/bin/env python3
"""
Local search provider for the unified search system.
Provides RAG/vector similarity search using FAISS and SQLite.
"""

import asyncio
import logging
import os
import sys
from typing import Dict, List, Optional, Any

from search_types import SearchProviderInterface, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class LocalSearchProvider(SearchProviderInterface):
    """
    Local RAG search provider using FAISS vector search
    """

    PROVIDER_TYPE = "local"
    CAPABILITIES = ["vector_search", "semantic_search", "local_knowledge"]
    RATE_LIMITS = {"requests_per_minute": 120, "delay_seconds": 0.1}
    CONFIG_REQUIRED = []  # No external config required

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.index_file = self.config.get('index_file', 'index.faiss')
        self.metadata_file = self.config.get('metadata_file', 'metadata.sqlite')
        self.model_name = self.config.get('model_name', 'all-MiniLM-L6-v2')

        # Lazy-loaded components
        self.index = None
        self.model = None
        self.db_connection = None

    def _check_requirements(self) -> bool:
        """Check if required files and libraries are available"""
        if not os.path.exists(self.index_file):
            logger.warning(f"FAISS index file not found: {self.index_file}")
            return False

        if not os.path.exists(self.metadata_file):
            logger.warning(f"Metadata database not found: {self.metadata_file}")
            return False

        try:
            import faiss
            import sqlite3
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            logger.error(f"Missing required libraries: {e}")
            return False

        return True

    def _load_components(self):
        """Load FAISS index, embedding model, and database connection"""
        if not self._check_requirements():
            raise RuntimeError("Local search requirements not met")

        try:
            import faiss
            import sqlite3
            from sentence_transformers import SentenceTransformer

            logger.debug("Loading FAISS index and embedding model...")
            self.index = faiss.read_index(self.index_file)
            self.model = SentenceTransformer(self.model_name)
            self.db_connection = sqlite3.connect(self.metadata_file)

            logger.info("Local search components loaded successfully")

        except Exception as e:
            logger.error(f"Error loading local search components: {e}")
            raise

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Perform vector similarity search

        Args:
            query: Search query parameters

        Returns:
            List of search results
        """
        try:
            # Load components if not already loaded
            if self.index is None:
                self._load_components()

            # Rate limiting
            await asyncio.sleep(self.RATE_LIMITS["delay_seconds"])

            # Embed query
            import numpy as np
            query_vector = self.model.encode([query.query])
            faiss.normalize_L2(query_vector.astype(np.float32))

            # Search FAISS
            D, I = self.index.search(query_vector.astype(np.float32), query.limit)

            if not any(I[0]):
                logger.info(f"No local search results for: {query.query}")
                return []

            # Get text and metadata from SQLite
            chunk_ids = tuple(I[0])
            results_data = self._get_chunks_by_ids(chunk_ids)

            if not results_data:
                logger.warning("No chunks found in database")
                return []

            # Convert to SearchResult format
            results = []
            for i, (text, path, headers) in enumerate(results_data):
                result = SearchResult(
                    provider=self.PROVIDER_TYPE,
                    query=query.query,
                    title=headers or "Local Document",
                    description=text[:500] + "..." if len(text) > 500 else text,
                    url=f"file://{path}",
                    confidence=1 - D[0][i],  # Convert distance to similarity score
                    metadata={
                        'source_file': path,
                        'section': headers,
                        'similarity_score': float(1 - D[0][i]),
                        'chunk_index': int(I[0][i])
                    }
                )
                results.append(result)

            logger.info(f"Local search found {len(results)} results for '{query.query}'")
            return results

        except Exception as e:
            logger.error(f"Local search error: {e}")
            return []

    def _get_chunks_by_ids(self, chunk_ids: tuple) -> List[tuple]:
        """Get chunks from SQLite database by IDs"""
        try:
            cursor = self.db_connection.cursor()
            placeholders = ','.join('?' * len(chunk_ids))
            cursor.execute(f"SELECT text, path, headers FROM chunks WHERE id IN ({placeholders})", chunk_ids)

            results = []
            for row in cursor.fetchall():
                text, path, headers = row
                results.append((text, path, headers))

            return results

        except Exception as e:
            logger.error(f"Error querying database: {e}")
            return []

    async def get_document_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific document

        Args:
            file_path: Path to the document

        Returns:
            Document metadata or None if not found
        """
        try:
            if not self.db_connection:
                self._load_components()

            cursor = self.db_connection.cursor()
            cursor.execute("SELECT COUNT(*), path FROM chunks WHERE path = ? GROUP BY path", (file_path,))

            result = cursor.fetchone()
            if result:
                chunk_count, path = result
                return {
                    'file_path': path,
                    'chunk_count': chunk_count,
                    'indexed': True
                }

        except Exception as e:
            logger.error(f"Error getting document info for {file_path}: {e}")

        return None

    async def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the local index"""
        try:
            if not self.index or not self.db_connection:
                self._load_components()

            # Get total chunks
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM chunks")
            total_chunks = cursor.fetchone()[0]

            # Get unique files
            cursor.execute("SELECT COUNT(DISTINCT path) FROM chunks")
            total_files = cursor.fetchone()[0]

            return {
                'total_chunks': total_chunks,
                'total_files': total_files,
                'index_dimension': self.index.d,
                'index_size': self.index.ntotal,
                'model_name': self.model_name
            }

        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {}

    async def health_check(self) -> bool:
        """Check if local search is available"""
        try:
            if not self._check_requirements():
                return False

            # Try to load components
            if self.index is None:
                self._load_components()

            # Quick test search
            test_results = await self.search(SearchQuery(query="test", limit=1))
            return True  # If we get here without exception, it's working

        except Exception as e:
            logger.error(f"Local search health check error: {e}")
            return False