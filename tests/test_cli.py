"""
Unit tests for cli.py module.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json
import numpy as np

from cli import ask_permission, main


class TestAskPermission(unittest.TestCase):
    """Test ask_permission function."""

    @patch("builtins.input")
    def test_ask_permission_yes(self, mock_input):
        """Test ask_permission with yes response."""
        mock_input.return_value = "yes"
        result = ask_permission()
        self.assertTrue(result)

    @patch("builtins.input")
    def test_ask_permission_no(self, mock_input):
        """Test ask_permission with no response."""
        mock_input.return_value = "no"
        result = ask_permission()
        self.assertFalse(result)

    @patch("builtins.input")
    def test_ask_permission_y(self, mock_input):
        """Test ask_permission with y response."""
        mock_input.return_value = "y"
        result = ask_permission()
        self.assertTrue(result)

    @patch("builtins.input")
    def test_ask_permission_invalid_then_yes(self, mock_input):
        """Test ask_permission with invalid then valid response."""
        mock_input.side_effect = ["maybe", "yes"]
        result = ask_permission()
        self.assertTrue(result)


class TestMain(unittest.TestCase):
    """Test main function."""

    def setUp(self):
        """Set up test fixtures."""
        self.original_argv = sys.argv.copy()

    def tearDown(self):
        """Clean up test fixtures."""
        sys.argv = self.original_argv

    @patch("sys.argv", ["cli.py"])
    @patch("builtins.print")
    def test_main_no_args(self, mock_print):
        """Test main with no arguments."""
        main()
        mock_print.assert_called_with("Usage: python cli.py <query>")

    @patch("os.path.exists")
    @patch("builtins.print")
    def test_main_missing_files(self, mock_print, mock_exists):
        """Test main with missing index or database files."""
        mock_exists.return_value = False
        sys.argv = ["cli.py", "test query"]

        main()

        mock_print.assert_called_with(
            "ERROR: index.faiss or database missing. Run: python ingest.py"
        )

    @patch("os.path.exists")
    @patch("cli.database")
    @patch("cli.EmbeddingService")
    @patch("cli.FAISSIndexManager")
    @patch("builtins.print")
    def test_main_remote_mode_off(
        self, mock_print, mock_index_class, mock_embed_class, mock_db, mock_exists
    ):
        """Test main with REMOTE_MODE='off'."""
        mock_exists.return_value = True
        sys.argv = ["cli.py", "test query"]

        # Mock components
        mock_embed = MagicMock()
        mock_embed.encode_query.return_value = np.array([[1.0, 2.0]], dtype=np.float32)
        mock_embed_class.return_value = mock_embed

        mock_index = MagicMock()
        mock_index.search.return_value = (np.array([[0.1, 0.2]]), np.array([[1, 2]]))
        mock_index_class.return_value = mock_index

        mock_db.get_chunks_by_ids.return_value = [
            ("chunk text 1", "path1", "header1"),
            ("chunk text 2", "path2", "header2"),
        ]

        with patch("cli.REMOTE_MODE", "off"):
            with patch("os.getenv", return_value=None):
                main()

        # Should print local results but not call API
        self.assertTrue(
            any("Local RAG results:" in str(call) for call in mock_print.call_args_list)
        )
        self.assertTrue(
            any("REMOTE_MODE is off" in str(call) for call in mock_print.call_args_list)
        )

    @patch("os.path.exists")
    @patch("cli.database")
    @patch("cli.EmbeddingService")
    @patch("cli.FAISSIndexManager")
    @patch("builtins.print")
    def test_main_remote_mode_ask_no_api_key(
        self, mock_print, mock_index_class, mock_embed_class, mock_db, mock_exists
    ):
        """Test main with REMOTE_MODE='ask' but no API key."""
        mock_exists.return_value = True
        sys.argv = ["cli.py", "test query"]

        # Mock components
        mock_embed = MagicMock()
        mock_embed.encode_query.return_value = np.array([[1.0, 2.0]], dtype=np.float32)
        mock_embed_class.return_value = mock_embed

        mock_index = MagicMock()
        mock_index.search.return_value = (np.array([[0.1, 0.2]]), np.array([[1, 2]]))
        mock_index_class.return_value = mock_index

        mock_db.get_chunks_by_ids.return_value = [
            ("chunk text 1", "path1", "header1"),
            ("chunk text 2", "path2", "header2"),
        ]

        with patch("cli.REMOTE_MODE", "ask"):
            with patch("os.getenv", return_value=None):
                main()

        # Should print local results and no API key message
        self.assertTrue(
            any(
                "No Anthropic API key found" in str(call)
                for call in mock_print.call_args_list
            )
        )

    @patch("os.path.exists")
    @patch("cli.database")
    @patch("cli.EmbeddingService")
    @patch("cli.FAISSIndexManager")
    @patch("cli.ask_permission")
    @patch("builtins.print")
    def test_main_remote_mode_ask_user_declines(
        self,
        mock_print,
        mock_ask,
        mock_index_class,
        mock_embed_class,
        mock_db,
        mock_exists,
    ):
        """Test main with REMOTE_MODE='ask' and user declines."""
        mock_exists.return_value = True
        sys.argv = ["cli.py", "test query"]
        mock_ask.return_value = False

        # Mock components
        mock_embed = MagicMock()
        mock_embed.encode_query.return_value = np.array([[1.0, 2.0]], dtype=np.float32)
        mock_embed_class.return_value = mock_embed

        mock_index = MagicMock()
        mock_index.search.return_value = (np.array([[0.1, 0.2]]), np.array([[1, 2]]))
        mock_index_class.return_value = mock_index

        mock_db.get_chunks_by_ids.return_value = [
            ("chunk text 1", "path1", "header1"),
            ("chunk text 2", "path2", "header2"),
        ]

        with patch("cli.REMOTE_MODE", "ask"):
            with patch("os.getenv", return_value="fake_key"):
                main()

        mock_ask.assert_called_once()
        self.assertTrue(
            any("Skipping cloud API" in str(call) for call in mock_print.call_args_list)
        )

    @patch("os.path.exists")
    @patch("cli.database")
    @patch("cli.EmbeddingService")
    @patch("cli.FAISSIndexManager")
    @patch("cli.ask_permission")
    @patch("cli.anthropic.Anthropic")
    @patch("builtins.print")
    def test_main_remote_mode_ask_user_accepts(
        self,
        mock_print,
        mock_anthropic_class,
        mock_ask,
        mock_index_class,
        mock_embed_class,
        mock_db,
        mock_exists,
    ):
        """Test main with REMOTE_MODE='ask' and user accepts."""
        mock_exists.return_value = True
        sys.argv = ["cli.py", "test query"]
        mock_ask.return_value = True

        # Mock components
        mock_embed = MagicMock()
        mock_embed.encode_query.return_value = np.array([[1.0, 2.0]], dtype=np.float32)
        mock_embed_class.return_value = mock_embed

        mock_index = MagicMock()
        mock_index.search.return_value = (np.array([[0.1, 0.2]]), np.array([[1, 2]]))
        mock_index_class.return_value = mock_index

        mock_db.get_chunks_by_ids.return_value = [
            ("chunk text 1", "path1", "header1"),
            ("chunk text 2", "path2", "header2"),
        ]

        # Mock Anthropic
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "AI response"
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        with patch("cli.REMOTE_MODE", "ask"):
            with patch("os.getenv", return_value="fake_key"):
                main()

        mock_anthropic_class.assert_called_once_with(api_key="fake_key")
        mock_client.messages.create.assert_called_once()
        self.assertTrue(
            any("AI response" in str(call) for call in mock_print.call_args_list)
        )

    @patch("os.path.exists")
    @patch("cli.database")
    @patch("cli.EmbeddingService")
    @patch("cli.FAISSIndexManager")
    @patch("cli.anthropic.Anthropic")
    @patch("builtins.print")
    def test_main_remote_mode_on(
        self,
        mock_print,
        mock_anthropic_class,
        mock_index_class,
        mock_embed_class,
        mock_db,
        mock_exists,
    ):
        """Test main with REMOTE_MODE='on'."""
        mock_exists.return_value = True
        sys.argv = ["cli.py", "test query"]

        # Mock components
        mock_embed = MagicMock()
        mock_embed.encode_query.return_value = np.array([[1.0, 2.0]], dtype=np.float32)
        mock_embed_class.return_value = mock_embed

        mock_index = MagicMock()
        mock_index.search.return_value = (np.array([[0.1, 0.2]]), np.array([[1, 2]]))
        mock_index_class.return_value = mock_index

        mock_db.get_chunks_by_ids.return_value = [
            ("chunk text 1", "path1", "header1"),
            ("chunk text 2", "path2", "header2"),
        ]

        # Mock Anthropic
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "AI response"
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        with patch("cli.REMOTE_MODE", "on"):
            with patch("os.getenv", return_value="fake_key"):
                main()

        # Should not ask permission in 'on' mode
        mock_anthropic_class.assert_called_once_with(api_key="fake_key")
        mock_client.messages.create.assert_called_once()

    @patch("os.path.exists")
    @patch("cli.database")
    @patch("cli.EmbeddingService")
    @patch("cli.FAISSIndexManager")
    @patch("cli.anthropic.Anthropic")
    @patch("builtins.print")
    def test_main_api_error(
        self,
        mock_print,
        mock_anthropic_class,
        mock_index_class,
        mock_embed_class,
        mock_db,
        mock_exists,
    ):
        """Test main with API error."""
        mock_exists.return_value = True
        sys.argv = ["cli.py", "test query"]

        # Mock components
        mock_embed = MagicMock()
        mock_embed.encode_query.return_value = np.array([[1.0, 2.0]], dtype=np.float32)
        mock_embed_class.return_value = mock_embed

        mock_index = MagicMock()
        mock_index.search.return_value = (np.array([[0.1, 0.2]]), np.array([[1, 2]]))
        mock_index_class.return_value = mock_index

        mock_db.get_chunks_by_ids.return_value = [
            ("chunk text 1", "path1", "header1"),
            ("chunk text 2", "path2", "header2"),
        ]

        # Mock Anthropic to raise exception
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API Error")
        mock_anthropic_class.return_value = mock_client

        with patch("cli.REMOTE_MODE", "on"):
            with patch("os.getenv", return_value="fake_key"):
                main()

        self.assertTrue(
            any(
                "Error calling Anthropic API" in str(call)
                for call in mock_print.call_args_list
            )
        )
        self.assertTrue(
            any(
                "Falling back to local-only mode" in str(call)
                for call in mock_print.call_args_list
            )
        )


if __name__ == "__main__":
    unittest.main()
