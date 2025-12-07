"""
Test suite for Google Books Client
Tests search, metadata extraction, rate limiting, and caching.

Run with: python test_google_books_client.py
"""

import asyncio
import sys
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from aiohttp import ClientError

# Add project root to path
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.integrations.google_books_client import (
    GoogleBooksClient,
    GoogleBooksError,
    GoogleBooksRateLimitError
)

# Mock Data
MOCK_BOOK_RESULT = {
    "id": "vol123",
    "volumeInfo": {
        "title": "Foundation",
        "subtitle": "Book 1",
        "authors": ["Isaac Asimov"],
        "publisher": "Gnome Press",
        "publishedDate": "1951",
        "description": "The first novel in the Foundation Series.",
        "pageCount": 255,
        "categories": ["Science Fiction"],
        "industryIdentifiers": [
            {"type": "ISBN_10", "identifier": "0553293354"},
            {"type": "ISBN_13", "identifier": "9780553293357"}
        ],
        "imageLinks": {
            "thumbnail": "http://example.com/thumb.jpg",
            "large": "http://example.com/large.jpg"
        },
        "language": "en",
        "previewLink": "http://example.com/preview",
        "infoLink": "http://example.com/info"
    }
}

class TestGoogleBooksClient:
    """Test suite for Google Books client."""

    def __init__(self):
        self.results = []

    async def run_test(self, test_name: str, test_func):
        """Run a single test and record result."""
        try:
            await test_func()
            self.results.append((test_name, True, None))
            print(f"✓ {test_name}")
        except AssertionError as e:
            self.results.append((test_name, False, str(e)))
            print(f"✗ {test_name}: {e}")
        except Exception as e:
            self.results.append((test_name, False, f"Unexpected error: {e}"))
            print(f"✗ {test_name}: Unexpected error: {e}")

    # ========================================
    # 1. INITIALIZATION
    # ========================================

    async def test_initialization(self):
        """Test client initialization."""
        client = GoogleBooksClient(api_key="test_key", timeout=10)
        assert client.api_key == "test_key"
        assert client.timeout.total == 10
        assert client.max_requests_per_day == 900

    # ========================================
    # 2. SEARCH & EXTRACTION
    # ========================================

    async def test_search_and_extract(self):
        """Test searching and metadata extraction."""
        client = GoogleBooksClient()
        
        # Mock response
        mock_response = {"items": [MOCK_BOOK_RESULT]}
        
        # Setup mock session
        mock_session = MagicMock()
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = mock_response
        
        # Setup context manager
        cm = AsyncMock()
        cm.__aenter__.return_value = mock_resp
        cm.__aexit__.return_value = None
        mock_session.get.return_value = cm
        
        client.session = mock_session

        # Run search
        metadata = await client.search_and_extract("Foundation", author="Asimov")
        
        assert metadata is not None
        assert metadata["title"] == "Foundation"
        assert metadata["authors"] == ["Isaac Asimov"]
        assert metadata["isbn_13"] == "9780553293357"
        assert metadata["thumbnail"] == "http://example.com/large.jpg"  # Should pick best quality

    async def test_search_no_results(self):
        """Test search with no results."""
        client = GoogleBooksClient()
        
        mock_response = {"items": []}
        
        mock_session = MagicMock()
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = mock_response
        
        cm = AsyncMock()
        cm.__aenter__.return_value = mock_resp
        cm.__aexit__.return_value = None
        mock_session.get.return_value = cm
        
        client.session = mock_session

        metadata = await client.search_and_extract("NonexistentBook12345")
        assert metadata is None

    # ========================================
    # 3. RATE LIMITING
    # ========================================

    async def test_rate_limiting_daily(self):
        """Test daily rate limit enforcement."""
        client = GoogleBooksClient(max_requests_per_day=2)
        
        # Mock successful response
        mock_response = {"items": []}
        mock_session = MagicMock()
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = mock_response
        
        cm = AsyncMock()
        cm.__aenter__.return_value = mock_resp
        cm.__aexit__.return_value = None
        mock_session.get.return_value = cm
        client.session = mock_session

        # 1st request - OK
        await client.search("Book 1")
        
        # 2nd request - OK
        await client.search("Book 2")
        
        # 3rd request - Should fail
        try:
            await client.search("Book 3")
            assert False, "Should have raised rate limit error"
        except GoogleBooksRateLimitError:
            pass  # Expected

    async def test_rate_limiting_api_429(self):
        """Test handling of API 429 responses."""
        client = GoogleBooksClient()
        
        mock_session = MagicMock()
        mock_resp = AsyncMock()
        mock_resp.status = 429
        
        cm = AsyncMock()
        cm.__aenter__.return_value = mock_resp
        cm.__aexit__.return_value = None
        mock_session.get.return_value = cm
        client.session = mock_session

        try:
            await client.search("Book")
            assert False, "Should have raised rate limit error"
        except GoogleBooksRateLimitError:
            pass  # Expected

    # ========================================
    # 4. CACHING
    # ========================================

    async def test_caching(self):
        """Test in-memory caching."""
        client = GoogleBooksClient()
        
        # Mock response
        mock_response = {"items": [MOCK_BOOK_RESULT]}
        
        mock_session = MagicMock()
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = mock_response
        
        cm = AsyncMock()
        cm.__aenter__.return_value = mock_resp
        cm.__aexit__.return_value = None
        mock_session.get.return_value = cm
        client.session = mock_session

        # 1. First call (Network)
        await client.search("Foundation")
        assert client.session.get.call_count == 1
        
        # 2. Second call (Cache)
        await client.search("Foundation")
        assert client.session.get.call_count == 1  # Should not increment

    # ========================================
    # 5. ERROR HANDLING
    # ========================================

    async def test_network_error(self):
        """Test handling of network errors."""
        client = GoogleBooksClient()
        
        mock_session = MagicMock()
        # Simulate network error
        mock_session.get.side_effect = ClientError("Network down")
        client.session = mock_session

        try:
            await client.search("Foundation")
            assert False, "Should have raised GoogleBooksError"
        except GoogleBooksError as e:
            assert "Request failed" in str(e)


async def main():
    tester = TestGoogleBooksClient()
    
    print("============================================================")
    print("Google Books Client Validation")
    print("============================================================")
    
    await tester.run_test("Initialization", tester.test_initialization)
    await tester.run_test("Search & Extraction", tester.test_search_and_extract)
    await tester.run_test("Search No Results", tester.test_search_no_results)
    await tester.run_test("Rate Limiting (Daily)", tester.test_rate_limiting_daily)
    await tester.run_test("Rate Limiting (API 429)", tester.test_rate_limiting_api_429)
    await tester.run_test("Caching", tester.test_caching)
    await tester.run_test("Network Error", tester.test_network_error)
    
    print("\n============================================================")
    passed = sum(1 for r in tester.results if r[1])
    total = len(tester.results)
    print(f"Results: {passed}/{total} passed")
    print("============================================================")

if __name__ == "__main__":
    asyncio.run(main())
