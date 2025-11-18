"""
Unit tests for mamcrawler.rag.chunking module.
"""

import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os

from mamcrawler.rag.chunking import MarkdownChunker, get_chunker
from mamcrawler.config import RAGConfig


class TestMarkdownChunker(unittest.TestCase):
    """Test MarkdownChunker class."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = RAGConfig()
        self.chunker = MarkdownChunker(self.config)

    def test_init(self):
        """Test initialization with config."""
        self.assertEqual(self.chunker.config, self.config)
        self.assertIsNotNone(self.chunker.splitter)

    def test_init_default_config(self):
        """Test initialization with default config."""
        chunker = MarkdownChunker()
        self.assertIsNotNone(chunker.config)
        self.assertIsNotNone(chunker.splitter)

    def test_chunk_simple_markdown(self):
        """Test chunking simple markdown content."""
        content = """# Header 1

This is content under header 1.

## Header 2

This is content under header 2.

### Header 3

This is content under header 3.
"""

        chunks = self.chunker.chunk(content)

        # Should have 3 chunks
        self.assertEqual(len(chunks), 3)

        # Check structure: (text_to_embed, raw_text, header_context)
        for chunk in chunks:
            self.assertEqual(len(chunk), 3)
            text_to_embed, raw_text, header_context = chunk
            self.assertIn("CONTEXT:", text_to_embed)
            self.assertIn("CONTENT:", text_to_embed)
            self.assertIsInstance(raw_text, str)
            self.assertIsInstance(header_context, str)

    def test_chunk_with_header_context(self):
        """Test that header context is built correctly."""
        content = """# Main Title

Intro content.

## Section 1

Section content.

### Subsection

Sub content.
"""

        chunks = self.chunker.chunk(content)

        # Find the subsection chunk
        subsection_chunk = None
        for chunk in chunks:
            if "Subsection" in chunk[2]:
                subsection_chunk = chunk
                break

        self.assertIsNotNone(subsection_chunk)
        _, _, header_context = subsection_chunk
        self.assertEqual(header_context, "Main Title > Section 1 > Subsection")

    def test_chunk_empty_content(self):
        """Test chunking empty content."""
        chunks = self.chunker.chunk("")
        self.assertEqual(len(chunks), 0)

    def test_chunk_no_headers(self):
        """Test chunking content with no headers."""
        content = "This is just plain text with no headers."
        chunks = self.chunker.chunk(content)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0][2], "")  # Empty header context

    @patch(
        "builtins.open",
        new_callable=unittest.mock.mock_open,
        read_data="# Test\nContent",
    )
    def test_chunk_file(self, mock_file):
        """Test chunking a file."""
        with patch("os.path.exists", return_value=True):
            chunks = self.chunker.chunk_file("test.md")
            self.assertEqual(len(chunks), 1)
            mock_file.assert_called_once_with("test.md", "r", encoding="utf-8")


class TestGetChunker(unittest.TestCase):
    """Test get_chunker function."""

    def test_get_chunker_with_config(self):
        """Test get_chunker with custom config."""
        config = RAGConfig()
        chunker = get_chunker(config)
        self.assertIsInstance(chunker, MarkdownChunker)
        self.assertEqual(chunker.config, config)

    def test_get_chunker_singleton(self):
        """Test get_chunker singleton behavior."""
        chunker1 = get_chunker()
        chunker2 = get_chunker()
        self.assertIs(chunker1, chunker2)


if __name__ == "__main__":
    unittest.main()
