"""
Unit tests for watcher.py module.
"""

import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os
import numpy as np

from watcher import MarkdownHandler, main


class TestMarkdownHandler(unittest.TestCase):
    """Test MarkdownHandler class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        with (
            patch("watcher.MarkdownChunker") as mock_chunker_class,
            patch("watcher.EmbeddingService") as mock_embed_class,
            patch("watcher.FAISSIndexManager") as mock_index_class,
        ):
            self.mock_chunker = MagicMock()
            self.mock_embed = MagicMock()
            self.mock_index = MagicMock()
            mock_chunker_class.return_value = self.mock_chunker
            mock_embed_class.return_value = self.mock_embed
            mock_index_class.return_value = self.mock_index
            self.handler = MarkdownHandler(self.temp_dir)

    @patch("watcher.MarkdownChunker")
    @patch("watcher.EmbeddingService")
    @patch("watcher.FAISSIndexManager")
    def test_init(self, mock_index_class, mock_embed_class, mock_chunker_class):
        """Test initialization."""
        mock_chunker = MagicMock()
        mock_chunker_class.return_value = mock_chunker

        mock_embed = MagicMock()
        mock_embed_class.return_value = mock_embed

        mock_index = MagicMock()
        mock_index_class.return_value = mock_index

        handler = MarkdownHandler(self.temp_dir)

        self.assertEqual(handler.target_dir, self.temp_dir)
        mock_chunker_class.assert_called_once()
        mock_embed_class.assert_called_once()
        mock_index_class.assert_called_once()

    def test_on_created_non_md_file(self):
        """Test on_created with non-markdown file."""
        mock_event = MagicMock()
        mock_event.is_directory = False
        mock_event.src_path = "test.txt"

        self.handler.on_created(mock_event)
        # Should not process non-md files

    def test_on_created_directory(self):
        """Test on_created with directory."""
        mock_event = MagicMock()
        mock_event.is_directory = True
        mock_event.src_path = "test_dir"

        self.handler.on_created(mock_event)
        # Should not process directories

    @patch("watcher.MarkdownHandler._process_file")
    def test_on_created_md_file(self, mock_process):
        """Test on_created with markdown file."""
        mock_event = MagicMock()
        mock_event.is_directory = False
        mock_event.src_path = "test.md"

        self.handler.on_created(mock_event)

        mock_process.assert_called_once_with("test.md")

    def test_on_modified_non_md_file(self):
        """Test on_modified with non-markdown file."""
        mock_event = MagicMock()
        mock_event.is_directory = False
        mock_event.src_path = "test.txt"

        self.handler.on_modified(mock_event)
        # Should not process

    @patch("watcher.MarkdownHandler._update_file")
    def test_on_modified_md_file(self, mock_update):
        """Test on_modified with markdown file."""
        mock_event = MagicMock()
        mock_event.is_directory = False
        mock_event.src_path = "test.md"

        self.handler.on_modified(mock_event)

        mock_update.assert_called_once_with("test.md")

    def test_on_deleted_non_md_file(self):
        """Test on_deleted with non-markdown file."""
        mock_event = MagicMock()
        mock_event.is_directory = False
        mock_event.src_path = "test.txt"

        self.handler.on_deleted(mock_event)
        # Should not process

    @patch("watcher.MarkdownHandler._delete_file")
    def test_on_deleted_md_file(self, mock_delete):
        """Test on_deleted with markdown file."""
        mock_event = MagicMock()
        mock_event.is_directory = False
        mock_event.src_path = "test.md"

        self.handler.on_deleted(mock_event)

        mock_delete.assert_called_once_with("test.md")

    @patch("watcher.os.path.getmtime")
    @patch("watcher.database")
    @patch("watcher.safe_read_markdown")
    def test_chunk_file(self, mock_read, mock_db, mock_getmtime):
        """Test _chunk_file method."""
        content = "# Test\n\nContent"
        mock_read.return_value = content
        mock_getmtime.return_value = 1234567890.0

        mock_db.insert_or_update_file.return_value = 1
        mock_db.insert_chunk.side_effect = [10, 11]

        # Mock chunker.chunk
        self.mock_chunker.chunk.return_value = [
            ("embed1", "raw1", "header1"),
            ("embed2", "raw2", "header2"),
        ]

        chunks, chunk_ids = self.handler._chunk_file("test.md")

        mock_read.assert_called_once_with("test.md")
        self.mock_chunker.chunk.assert_called_once_with(content)
        self.assertEqual(mock_db.insert_or_update_file.call_count, 1)
        self.assertEqual(mock_db.insert_chunk.call_count, 2)
        self.assertEqual(chunks, ["embed1", "embed2"])
        self.assertEqual(chunk_ids, [10, 11])

    @patch("watcher.MarkdownHandler._chunk_file")
    def test_process_file(self, mock_chunk):
        """Test _process_file method."""
        mock_chunk.return_value = (["chunk1", "chunk2"], [1, 2])

        self.mock_embed.encode.return_value = np.array([[1.0], [2.0]], dtype=np.float32)

        self.handler._process_file("test.md")

        self.mock_embed.encode.assert_called_once_with(["chunk1", "chunk2"])
        self.mock_index.add.assert_called_once()
        self.mock_index.save.assert_called_once()

    @patch("watcher.database")
    @patch("watcher.safe_read_markdown")
    def test_update_file_new_file(self, mock_read, mock_db):
        """Test _update_file with new file."""
        mock_db.get_file_details.return_value = None

        with patch.object(self.handler, "_process_file") as mock_process:
            self.handler._update_file("test.md")

            mock_process.assert_called_once_with("test.md")

    @patch("watcher.database")
    @patch("watcher.safe_read_markdown")
    @patch("watcher.hashlib")
    def test_update_file_unchanged(self, mock_hashlib, mock_read, mock_db):
        """Test _update_file with unchanged file."""
        content = "content"
        mock_read.return_value = content

        mock_hash = MagicMock()
        mock_hash.hexdigest.return_value = "hash123"
        mock_hashlib.sha256.return_value = mock_hash

        mock_db.get_file_details.return_value = (1, "hash123")

        with patch.object(self.handler, "_process_file") as mock_process:
            with patch.object(self.mock_index, "remove") as mock_remove:
                self.handler._update_file("test.md")

                mock_process.assert_not_called()
                mock_remove.assert_not_called()

    @patch("watcher.database")
    @patch("watcher.safe_read_markdown")
    @patch("watcher.hashlib")
    def test_update_file_changed(self, mock_hashlib, mock_read, mock_db):
        """Test _update_file with changed file."""
        content = "new content"
        mock_read.return_value = content

        mock_new_hash = MagicMock()
        mock_new_hash.hexdigest.return_value = "new_hash"
        mock_hashlib.sha256.return_value = mock_new_hash

        mock_db.get_file_details.return_value = (1, "old_hash")
        mock_db.get_chunk_ids_for_file.return_value = [10, 11]

        with patch.object(self.handler, "_process_file") as mock_process:
            self.handler._update_file("test.md")

            self.mock_index.remove.assert_called_once()
            mock_db.delete_file_records.assert_called_once_with(1)
            mock_process.assert_called_once_with("test.md")

    @patch("watcher.database")
    def test_delete_file(self, mock_db):
        """Test _delete_file method."""
        mock_db.get_file_details.return_value = (1, "hash")
        mock_db.get_chunk_ids_for_file.return_value = [10, 11]

        self.handler._delete_file("test.md")

        mock_db.get_file_details.assert_called_once_with("test.md")
        mock_db.get_chunk_ids_for_file.assert_called_once_with(1)
        self.mock_index.remove.assert_called_once()
        mock_db.delete_file_records.assert_called_once_with(1)
        self.mock_index.save.assert_called_once()

    @patch("watcher.database")
    def test_delete_file_no_existing(self, mock_db):
        """Test _delete_file with no existing file."""
        mock_db.get_file_details.return_value = None

        self.handler._delete_file("test.md")

        mock_db.get_chunk_ids_for_file.assert_not_called()
        self.mock_index.remove.assert_not_called()


class TestMain(unittest.TestCase):
    """Test main function."""

    @patch("watcher.os.path.exists")
    @patch("watcher.os.makedirs")
    @patch("watcher.database")
    @patch("watcher.Observer")
    def test_main(self, mock_observer_class, mock_db, mock_makedirs, mock_exists):
        """Test main function."""
        mock_exists.return_value = False

        mock_observer = MagicMock()
        mock_observer_class.return_value = mock_observer

        with patch("watcher.MarkdownHandler") as mock_handler_class:
            with patch("builtins.print"):
                with patch("time.sleep", side_effect=KeyboardInterrupt):
                    main()

        mock_db.create_tables.assert_called_once()
        mock_exists.assert_called_once_with("guides_output")
        mock_makedirs.assert_called_once_with("guides_output")
        mock_handler_class.assert_called_once_with("guides_output")
        mock_observer_class.assert_called_once()
        mock_observer.schedule.assert_called_once()
        mock_observer.start.assert_called_once()
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()


if __name__ == "__main__":
    unittest.main()
