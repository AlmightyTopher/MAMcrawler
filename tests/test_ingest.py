"""
Unit tests for ingest.py module.
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import os
import hashlib
import numpy as np

from ingest import process_file, main


class TestProcessFile(unittest.TestCase):
    """Test process_file function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test.md")

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    @patch("ingest.os.path.getmtime")
    @patch("ingest.safe_read_markdown")
    @patch("ingest.database")
    @patch("ingest.MarkdownChunker")
    def test_process_file_new_file(
        self, mock_chunker_class, mock_db, mock_read, mock_getmtime
    ):
        """Test processing a new file."""
        content = "# Test\n\nContent"
        mock_read.return_value = content
        mock_getmtime.return_value = 1234567890.0

        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [
            ("embed_text1", "raw_text1", "header1"),
            ("embed_text2", "raw_text2", "header2"),
        ]
        mock_chunker_class.return_value = mock_chunker

        mock_db.get_file_details.return_value = None
        mock_db.insert_or_update_file.return_value = 1
        mock_db.insert_chunk.side_effect = [10, 11]

        chunks, chunk_ids = process_file(self.test_file, mock_chunker)

        mock_read.assert_called_once_with(self.test_file)
        mock_db.get_file_details.assert_called_once_with(self.test_file)
        mock_db.insert_or_update_file.assert_called_once()
        self.assertEqual(mock_db.insert_chunk.call_count, 2)
        self.assertEqual(chunks, ["embed_text1", "embed_text2"])
        self.assertEqual(chunk_ids, [10, 11])

    @patch("ingest.safe_read_markdown")
    @patch("ingest.database")
    @patch("ingest.MarkdownChunker")
    def test_process_file_unchanged_file(self, mock_chunker_class, mock_db, mock_read):
        """Test processing an unchanged file."""
        content = "# Test\n\nContent"
        mock_read.return_value = content

        file_hash = hashlib.sha256(content.encode()).hexdigest()
        mock_db.get_file_details.return_value = (1, file_hash)

        mock_chunker = MagicMock()
        mock_chunker_class.return_value = mock_chunker

        chunks, chunk_ids = process_file(self.test_file, mock_chunker)

        mock_read.assert_called_once_with(self.test_file)
        mock_db.get_file_details.assert_called_once_with(self.test_file)
        mock_chunker.chunk.assert_not_called()
        self.assertEqual(chunks, [])
        self.assertEqual(chunk_ids, [])


class TestMain(unittest.TestCase):
    """Test main function."""

    @patch("ingest.os.walk")
    @patch("ingest.database")
    @patch("ingest.MarkdownChunker")
    @patch("ingest.EmbeddingService")
    @patch("ingest.FAISSIndexManager")
    @patch("ingest.process_file")
    def test_main(
        self,
        mock_process_file,
        mock_index_class,
        mock_embed_class,
        mock_chunker_class,
        mock_db,
        mock_walk,
    ):
        """Test main ingestion function."""
        # Mock directory structure
        mock_walk.return_value = [
            ("/test/dir", [], ["file1.md", "file2.md", "not_md.txt"])
        ]

        # Mock components
        mock_chunker = MagicMock()
        mock_chunker_class.return_value = mock_chunker

        mock_embed = MagicMock()
        mock_embed_class.return_value = mock_embed

        mock_index = MagicMock()
        mock_index.total_vectors = 10
        mock_index_class.return_value = mock_index

        # Mock process_file returns
        mock_process_file.side_effect = [
            (["chunk1"], [1]),  # file1.md
            ([], []),  # file2.md (no changes)
        ]

        # Mock embeddings
        mock_embed.encode.return_value = np.array([[1.0, 2.0]], dtype=np.float32)

        with patch("builtins.print"):
            main("/test/dir")

        mock_db.create_tables.assert_called_once()
        self.assertEqual(mock_process_file.call_count, 2)  # Only .md files
        mock_embed.encode.assert_called_once()
        mock_index.add.assert_called_once()
        mock_index.save.assert_called_once()

    @patch("ingest.os.walk")
    @patch("ingest.database")
    @patch("ingest.MarkdownChunker")
    @patch("ingest.EmbeddingService")
    @patch("ingest.FAISSIndexManager")
    def test_main_no_chunks(
        self, mock_index_class, mock_embed_class, mock_chunker_class, mock_db, mock_walk
    ):
        """Test main with no chunks to process."""
        mock_walk.return_value = [("/test/dir", [], ["file1.md"])]

        mock_chunker = MagicMock()
        mock_chunker_class.return_value = mock_chunker

        mock_embed = MagicMock()
        mock_embed_class.return_value = mock_embed

        mock_index = MagicMock()
        mock_index_class.return_value = mock_index

        with patch("ingest.process_file", return_value=([], [])):
            with patch("builtins.print"):
                main("/test/dir")

        mock_embed.encode.assert_not_called()
        mock_index.add.assert_not_called()
        mock_index.save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
