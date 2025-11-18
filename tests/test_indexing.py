"""
Unit tests for mamcrawler.rag.indexing module.
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import os
import numpy as np

from mamcrawler.rag.indexing import FAISSIndexManager, get_index_manager, reset_manager
from mamcrawler.config import RAGConfig


class TestFAISSIndexManager(unittest.TestCase):
    """Test FAISSIndexManager class."""

    def setUp(self):
        """Set up test fixtures."""
        from mamcrawler.rag.indexing import reset_manager

        reset_manager()
        self.config = RAGConfig()
        self.temp_dir = tempfile.mkdtemp()
        self.index_path = os.path.join(self.temp_dir, "test_index.faiss")

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.index_path):
            os.remove(self.index_path)

    @patch("mamcrawler.rag.indexing.faiss")
    def test_init_create_new_index(self, mock_faiss):
        """Test initialization creating new index."""
        mock_index = MagicMock()
        mock_faiss.IndexFlatL2.return_value = mock_index
        mock_faiss.IndexIDMap.return_value = mock_index

        manager = FAISSIndexManager(self.config, self.index_path)

        mock_faiss.IndexFlatL2.assert_called_once_with(self.config.dimension)
        mock_faiss.IndexIDMap.assert_called_once_with(mock_index)
        self.assertEqual(manager.index, mock_index)

    @patch("mamcrawler.rag.indexing.faiss")
    @patch("mamcrawler.rag.indexing.Path")
    def test_init_load_existing_index(self, mock_path, mock_faiss):
        """Test initialization loading existing index."""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        mock_index = MagicMock()
        mock_faiss.read_index.return_value = mock_index

        manager = FAISSIndexManager(self.config, self.index_path)

        mock_faiss.read_index.assert_called_once_with(str(mock_path_instance))
        self.assertEqual(manager.index, mock_index)

    @patch("mamcrawler.rag.indexing.faiss")
    def test_add_embeddings(self, mock_faiss):
        """Test adding embeddings."""
        mock_index = MagicMock()
        mock_faiss.IndexIDMap.return_value = mock_index

        manager = FAISSIndexManager(self.config, self.index_path)

        embeddings = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
        ids = np.array([1, 2], dtype=np.int64)

        manager.add(embeddings, ids)

        mock_index.add_with_ids.assert_called_once()
        args = mock_index.add_with_ids.call_args[0]
        np.testing.assert_array_equal(args[0], embeddings)
        np.testing.assert_array_equal(args[1], ids)

    @patch("mamcrawler.rag.indexing.faiss")
    def test_add_empty_embeddings(self, mock_faiss):
        """Test adding empty embeddings."""
        mock_index = MagicMock()
        mock_faiss.IndexIDMap.return_value = mock_index

        manager = FAISSIndexManager(self.config, self.index_path)

        manager.add(
            np.array([], dtype=np.float32).reshape(0, 2), np.array([], dtype=np.int64)
        )

        mock_index.add_with_ids.assert_not_called()

    @patch("mamcrawler.rag.indexing.faiss")
    def test_remove_ids(self, mock_faiss):
        """Test removing embeddings by IDs."""
        mock_index = MagicMock()
        mock_faiss.IndexIDMap.return_value = mock_index

        manager = FAISSIndexManager(self.config, self.index_path)

        ids = np.array([1, 2], dtype=np.int64)
        manager.remove(ids)

        mock_index.remove_ids.assert_called_once()
        args = mock_index.remove_ids.call_args[0][0]
        np.testing.assert_array_equal(args, ids)

    @patch("mamcrawler.rag.indexing.faiss")
    def test_remove_empty_ids(self, mock_faiss):
        """Test removing empty IDs."""
        mock_index = MagicMock()
        mock_faiss.IndexIDMap.return_value = mock_index

        manager = FAISSIndexManager(self.config, self.index_path)

        manager.remove(np.array([], dtype=np.int64))

        mock_index.remove_ids.assert_not_called()

    @patch("mamcrawler.rag.indexing.faiss")
    def test_search(self, mock_faiss):
        """Test searching for similar embeddings."""
        mock_index = MagicMock()
        mock_index.search.return_value = (np.array([[0.1, 0.2]]), np.array([[1, 2]]))
        mock_faiss.IndexIDMap.return_value = mock_index

        manager = FAISSIndexManager(self.config, self.index_path)

        query = np.array([[1.0, 2.0]], dtype=np.float32)
        distances, ids = manager.search(query, k=2)

        mock_index.search.assert_called_once()
        args = mock_index.search.call_args[0]
        np.testing.assert_array_equal(args[0], query)
        self.assertEqual(args[1], 2)
        np.testing.assert_array_equal(distances, np.array([[0.1, 0.2]]))
        np.testing.assert_array_equal(ids, np.array([[1, 2]]))

    @patch("mamcrawler.rag.indexing.faiss")
    def test_search_1d_query(self, mock_faiss):
        """Test search with 1D query embedding."""
        mock_index = MagicMock()
        mock_index.search.return_value = (np.array([[0.1]]), np.array([[1]]))
        mock_faiss.IndexIDMap.return_value = mock_index

        manager = FAISSIndexManager(self.config, self.index_path)

        query = np.array([1.0, 2.0], dtype=np.float32)
        distances, ids = manager.search(query)

        # Should reshape to 2D
        mock_index.search.assert_called_once()
        call_args = mock_index.search.call_args[0][0]
        self.assertEqual(call_args.shape, (1, 2))

    @patch("mamcrawler.rag.indexing.faiss")
    def test_search_default_k(self, mock_faiss):
        """Test search with default k."""
        mock_index = MagicMock()
        mock_index.search.return_value = (np.array([[0.1]]), np.array([[1]]))
        mock_faiss.IndexIDMap.return_value = mock_index

        manager = FAISSIndexManager(self.config, self.index_path)

        query = np.array([[1.0, 2.0]], dtype=np.float32)
        manager.search(query)

        mock_index.search.assert_called_once()
        args = mock_index.search.call_args[0]
        np.testing.assert_array_equal(args[0], query)
        self.assertEqual(args[1], self.config.top_k)

    @patch("mamcrawler.rag.indexing.faiss")
    def test_save(self, mock_faiss):
        """Test saving index."""
        mock_index = MagicMock()
        mock_faiss.IndexIDMap.return_value = mock_index

        manager = FAISSIndexManager(self.config, self.index_path)

        manager.save()

        mock_faiss.write_index.assert_called_once_with(
            mock_index, str(manager.index_path)
        )

    @patch("mamcrawler.rag.indexing.faiss")
    def test_total_vectors(self, mock_faiss):
        """Test total_vectors property."""
        mock_index = MagicMock()
        mock_index.ntotal = 42
        mock_faiss.IndexIDMap.return_value = mock_index

        manager = FAISSIndexManager(self.config, self.index_path)

        self.assertEqual(manager.total_vectors, 42)


class TestGetIndexManager(unittest.TestCase):
    """Test get_index_manager function."""

    def setUp(self):
        """Set up test fixtures."""
        from mamcrawler.rag.indexing import reset_manager

        reset_manager()

    @patch("mamcrawler.rag.indexing.FAISSIndexManager")
    def test_get_index_manager(self, mock_manager_class):
        """Test get_index_manager function."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        config = RAGConfig()
        manager = get_index_manager(config, "test_path")

        mock_manager_class.assert_called_once_with(config, "test_path")
        self.assertEqual(manager, mock_manager)

    @patch("mamcrawler.rag.indexing.FAISSIndexManager")
    def test_get_index_manager_singleton(self, mock_manager_class):
        """Test get_index_manager singleton."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        manager1 = get_index_manager()
        manager2 = get_index_manager()

        self.assertIs(manager1, manager2)
        mock_manager_class.assert_called_once()


class TestResetManager(unittest.TestCase):
    """Test reset_manager function."""

    @patch("mamcrawler.rag.indexing._manager", "test_manager")
    def test_reset_manager(self):
        """Test reset_manager function."""
        from mamcrawler.rag.indexing import _manager

        _manager = "test_value"
        reset_manager()
        from mamcrawler.rag.indexing import _manager

        self.assertIsNone(_manager)


if __name__ == "__main__":
    unittest.main()
