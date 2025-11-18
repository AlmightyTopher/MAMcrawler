"""
Unit tests for mamcrawler.rag.embeddings module.
"""

import unittest
from unittest.mock import patch, MagicMock
import numpy as np

from mamcrawler.rag.embeddings import (
    EmbeddingService,
    get_embedding_service,
    encode_texts,
)
from mamcrawler.config import RAGConfig


class TestEmbeddingService(unittest.TestCase):
    """Test EmbeddingService class."""

    def setUp(self):
        """Set up test fixtures."""
        from mamcrawler.rag.embeddings import EmbeddingService

        EmbeddingService._reset_singleton()
        self.config = RAGConfig()

    @patch("mamcrawler.rag.embeddings.SentenceTransformer")
    def test_init(self, mock_transformer):
        """Test initialization."""
        mock_model = MagicMock()
        mock_transformer.return_value = mock_model

        service = EmbeddingService(self.config)

        mock_transformer.assert_called_once_with(self.config.model_name)
        self.assertEqual(service.config, self.config)
        self.assertEqual(service.model, mock_model)

    @patch("mamcrawler.rag.embeddings.SentenceTransformer")
    def test_singleton(self, mock_transformer):
        """Test singleton pattern."""
        mock_model = MagicMock()
        mock_transformer.return_value = mock_model

        service1 = EmbeddingService(self.config)
        service2 = EmbeddingService(self.config)

        self.assertIs(service1, service2)
        mock_transformer.assert_called_once()  # Only called once

    @patch("mamcrawler.rag.embeddings.SentenceTransformer")
    @patch("mamcrawler.rag.embeddings.faiss")
    def test_encode(self, mock_faiss, mock_transformer):
        """Test encode method."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array(
            [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype=np.float32
        )
        mock_transformer.return_value = mock_model

        service = EmbeddingService(self.config)

        texts = ["text1", "text2"]
        embeddings = service.encode(texts)

        mock_model.encode.assert_called_once_with(texts)
        mock_faiss.normalize_L2.assert_called_once()
        self.assertEqual(embeddings.shape, (2, 3))
        self.assertEqual(embeddings.dtype, np.float32)

    @patch("mamcrawler.rag.embeddings.SentenceTransformer")
    def test_encode_empty_texts(self, mock_transformer):
        """Test encode with empty text list."""
        mock_model = MagicMock()
        mock_transformer.return_value = mock_model

        service = EmbeddingService(self.config)

        embeddings = service.encode([])
        self.assertEqual(embeddings.shape, (0, self.config.dimension))

    @patch("mamcrawler.rag.embeddings.SentenceTransformer")
    @patch("mamcrawler.rag.embeddings.faiss")
    def test_encode_no_normalize(self, mock_faiss, mock_transformer):
        """Test encode without normalization."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[1.0, 2.0]], dtype=np.float32)
        mock_transformer.return_value = mock_model

        service = EmbeddingService(self.config)

        service.encode(["text"], normalize=False)

        mock_faiss.normalize_L2.assert_not_called()

    @patch("mamcrawler.rag.embeddings.SentenceTransformer")
    @patch("mamcrawler.rag.embeddings.faiss")
    def test_encode_query(self, mock_faiss, mock_transformer):
        """Test encode_query method."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[1.0, 2.0, 3.0]], dtype=np.float32)
        mock_transformer.return_value = mock_model

        service = EmbeddingService(self.config)

        embedding = service.encode_query("query")

        mock_model.encode.assert_called_once_with(["query"])
        mock_faiss.normalize_L2.assert_called_once()
        self.assertEqual(embedding.shape, (1, 3))

    @patch("mamcrawler.rag.embeddings.SentenceTransformer")
    def test_dimension_property(self, mock_transformer):
        """Test dimension property."""
        mock_model = MagicMock()
        mock_transformer.return_value = mock_model

        service = EmbeddingService(self.config)

        self.assertEqual(service.dimension, self.config.dimension)


class TestGetEmbeddingService(unittest.TestCase):
    """Test get_embedding_service function."""

    def setUp(self):
        """Set up test fixtures."""
        from mamcrawler.rag.embeddings import EmbeddingService

        EmbeddingService._reset_singleton()

    @patch("mamcrawler.rag.embeddings.SentenceTransformer")
    def test_get_embedding_service(self, mock_transformer):
        """Test get_embedding_service function."""
        mock_model = MagicMock()
        mock_transformer.return_value = mock_model

        config = RAGConfig()
        service = get_embedding_service(config)

        self.assertIsInstance(service, EmbeddingService)
        mock_transformer.assert_called_once_with(config.model_name)

    @patch("mamcrawler.rag.embeddings.SentenceTransformer")
    def test_get_embedding_service_singleton(self, mock_transformer):
        """Test get_embedding_service singleton."""
        mock_model = MagicMock()
        mock_transformer.return_value = mock_model

        service1 = get_embedding_service()
        service2 = get_embedding_service()

        self.assertIs(service1, service2)


class TestEncodeTexts(unittest.TestCase):
    """Test encode_texts function."""

    def setUp(self):
        """Set up test fixtures."""
        from mamcrawler.rag.embeddings import EmbeddingService

        EmbeddingService._reset_singleton()

    @patch("mamcrawler.rag.embeddings.get_embedding_service")
    def test_encode_texts(self, mock_get_service):
        """Test encode_texts function."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.encode.return_value = np.array([[1.0, 2.0]], dtype=np.float32)

        texts = ["text1", "text2"]
        result = encode_texts(texts)

        mock_get_service.assert_called_once()
        mock_service.encode.assert_called_once_with(texts, True)
        np.testing.assert_array_equal(result, np.array([[1.0, 2.0]], dtype=np.float32))

    @patch("mamcrawler.rag.embeddings.get_embedding_service")
    def test_encode_texts_no_normalize(self, mock_get_service):
        """Test encode_texts with normalize=False."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        encode_texts(["text"], normalize=False)

        mock_service.encode.assert_called_once_with(["text"], False)


if __name__ == "__main__":
    unittest.main()
