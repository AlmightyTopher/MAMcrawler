"""
Unified markdown chunking for RAG system.
Single implementation to eliminate duplication between ingest.py and watcher.py.
"""

from typing import List, Tuple
from langchain_text_splitters.markdown import MarkdownHeaderTextSplitter

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from mamcrawler.config import RAGConfig, DEFAULT_RAG_CONFIG


class MarkdownChunker:
    """
    Chunks markdown content by headers for RAG indexing.

    Uses the "Embed the Headers" pattern where header context is prepended
    to chunk content for better semantic search.
    """

    def __init__(self, config: RAGConfig = None):
        """
        Initialize the chunker.

        Args:
            config: RAG configuration (uses defaults if not provided)
        """
        self.config = config or DEFAULT_RAG_CONFIG
        self.splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.config.headers_to_split,
            strip_headers=False
        )

    def chunk(self, content: str) -> List[Tuple[str, str, str]]:
        """
        Chunk markdown content by headers.

        Args:
            content: Markdown content to chunk

        Returns:
            List of (text_to_embed, raw_text, header_context) tuples
            - text_to_embed: The full text including context prefix for embedding
            - raw_text: The original chunk text (for storage)
            - header_context: The header breadcrumb (e.g., "H1 > H2 > H3")
        """
        splits = self.splitter.split_text(content)
        results = []

        for split in splits:
            # Build header breadcrumb
            header_context = " > ".join(split.metadata.values())

            # Create embedding text with context prefix
            text_to_embed = f"CONTEXT: {header_context}\n\nCONTENT:\n{split.page_content}"

            results.append((text_to_embed, split.page_content, header_context))

        return results

    def chunk_file(self, filepath: str) -> List[Tuple[str, str, str]]:
        """
        Chunk a markdown file.

        Args:
            filepath: Path to the markdown file

        Returns:
            List of (text_to_embed, raw_text, header_context) tuples
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return self.chunk(content)


# Singleton instance for convenience
_default_chunker = None


def get_chunker(config: RAGConfig = None) -> MarkdownChunker:
    """
    Get a chunker instance (singleton for default config).

    Args:
        config: Optional custom config

    Returns:
        MarkdownChunker instance
    """
    global _default_chunker
    if config:
        return MarkdownChunker(config)
    if _default_chunker is None:
        _default_chunker = MarkdownChunker()
    return _default_chunker
