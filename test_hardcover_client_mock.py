"""
Mock-based Test Suite for Hardcover Client
Validates logic without external API calls.

Run with: python test_hardcover_client_mock.py
"""

import asyncio
import sys
import json
import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from dataclasses import asdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.integrations.hardcover_client import (
    HardcoverClient,
    ResolutionResult,
    HardcoverBook,
    Author,
    SeriesBook,
    Edition
)

# Mock Data
MOCK_BOOK_DATA = {
    "id": 101,
    "title": "Project Hail Mary",
    "slug": "project-hail-mary",
    "description": "A lone astronaut...",
    "original_publication_date": "2021-05-04",
    "featured_book_series_id": 1,
    "featured_book_series": {"id": 1, "name": "Standalone"},
    "authors": [{"id": 1, "name": "Andy Weir", "slug": "andy-weir", "role": "Author"}],
    "series_books": [],
    "editions": [
        {"id": 1, "format": "Audio", "isbn_13": "9780593135204", "publisher": "Audible"}
    ]
}

class TestHardcoverClientMock:
    """Test suite for Hardcover client using mocks."""

    def __init__(self):
        self.results = []
        self.temp_files = []

    def setup(self):
        """Setup test environment."""
        import uuid
        self.test_db = f"test_hardcover_{uuid.uuid4().hex}.db"
        self.temp_files.append(self.test_db)

    def teardown(self):
        """Cleanup test environment."""
        # We'll try to clean up, but won't fail if we can't immediately
        import os
        try:
            if Path(self.test_db).exists():
                Path(self.test_db).unlink()
        except Exception:
            pass  # Ignore cleanup errors on Windows

    async def run_test(self, test_name: str, test_func):
        """Run a single test and record result."""
        try:
            self.setup()
            await test_func()
            self.results.append((test_name, True, None))
            print(f"✓ {test_name}")
        except AssertionError as e:
            self.results.append((test_name, False, str(e)))
            print(f"✗ {test_name}: {e}")
        except Exception as e:
            self.results.append((test_name, False, f"Unexpected error: {e}"))
            print(f"✗ {test_name}: Unexpected error: {e}")
        finally:
            self.teardown()

    # ========================================
    # 1. INITIALIZATION
    # ========================================

    async def test_initialization(self):
        """Test client initialization and cache setup."""
        client = HardcoverClient("fake_token", cache_db_path=self.test_db)
        
        assert client.api_token == "fake_token"
        assert Path(self.test_db).exists(), "Cache DB should be created"
        
        # Verify schema
        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hardcover_cache'")
            assert cursor.fetchone() is not None, "Cache table should exist"

    # ========================================
    # 2. ISBN RESOLUTION
    # ========================================

    async def test_resolve_by_isbn(self):
        """Test ISBN resolution logic."""
        client = HardcoverClient("fake_token", cache_db_path=self.test_db)
        
        # Mock GraphQL response
        mock_response = {"data": {"books": [MOCK_BOOK_DATA]}}
        
        # Mock session
        mock_session = MagicMock()
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = mock_response
        mock_session.post.return_value.__aenter__.return_value = mock_resp
        client.session = mock_session

        # Run test
        result = await client.resolve_by_isbn("978-0593135204")
        
        assert result.success
        assert result.book.title == "Project Hail Mary"
        assert result.book.authors[0].name == "Andy Weir"
        assert result.confidence == 1.0
        assert result.resolution_method == "isbn"

    async def test_resolve_by_isbn_not_found(self):
        """Test ISBN resolution when not found."""
        client = HardcoverClient("fake_token", cache_db_path=self.test_db)
        
        # Mock empty response
        mock_response = {"data": {"books": []}}
        
        mock_session = MagicMock()
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = mock_response
        mock_session.post.return_value.__aenter__.return_value = mock_resp
        client.session = mock_session

        result = await client.resolve_by_isbn("0000000000")
        
        assert not result.success
        assert result.book is None

    # ========================================
    # 3. TITLE/AUTHOR RESOLUTION
    # ========================================

    async def test_resolve_by_title_author(self):
        """Test Title/Author resolution logic."""
        client = HardcoverClient("fake_token", cache_db_path=self.test_db)
        
        mock_response = {"data": {"books": [MOCK_BOOK_DATA]}}
        
        mock_session = MagicMock()
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = mock_response
        mock_session.post.return_value.__aenter__.return_value = mock_resp
        client.session = mock_session

        result = await client.resolve_by_title_author("Project Hail Mary", "Andy Weir")
        
        assert result.success
        assert result.book.title == "Project Hail Mary"
        assert result.confidence >= 0.95

    # ========================================
    # 4. WATERFALL LOGIC
    # ========================================

    async def test_waterfall_resolution(self):
        """Test waterfall logic (ISBN -> Title/Author -> Fuzzy)."""
        client = HardcoverClient("fake_token", cache_db_path=self.test_db)
        
        # Mock responses for different calls
        # 1. ISBN call -> Empty (Fail)
        # 2. Title/Author call -> Success
        
        def mock_post(*args, **kwargs):
            payload = kwargs.get('json', {})
            query = payload.get('query', '')
            
            # Create a fresh mock response for this call
            mock_resp = AsyncMock()
            mock_resp.status = 200
            
            if "ResolveByISBN" in query:
                mock_resp.json.return_value = {"data": {"books": []}}
            elif "ResolveByTitleAuthor" in query:
                mock_resp.json.return_value = {"data": {"books": [MOCK_BOOK_DATA]}}
            else:
                mock_resp.json.return_value = {"data": {"books": []}}
            
            # Create a context manager mock that returns our response
            cm = AsyncMock()
            cm.__aenter__.return_value = mock_resp
            cm.__aexit__.return_value = None
            return cm

        mock_session = MagicMock()
        mock_session.post.side_effect = mock_post
        client.session = mock_session

        # Should fail ISBN but succeed on Title/Author
        result = await client.resolve_book(
            title="Project Hail Mary",
            author="Andy Weir",
            isbn="0000000000"
        )
        
        assert result.success
        assert result.resolution_method == "title_author"
        assert result.book.title == "Project Hail Mary"

    # ========================================
    # 5. CACHING
    # ========================================

    async def test_caching_mechanism(self):
        """Test that results are cached and retrieved."""
        client = HardcoverClient("fake_token", cache_db_path=self.test_db)
        
        # 1. First call (Network)
        mock_response = {"data": {"books": [MOCK_BOOK_DATA]}}
        mock_session = MagicMock()
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = mock_response
        mock_session.post.return_value.__aenter__.return_value = mock_resp
        client.session = mock_session

        await client.resolve_by_isbn("9780593135204")
        
        # 2. Verify it's in DB
        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.execute("SELECT count(*) FROM hardcover_cache")
            count = cursor.fetchone()[0]
            assert count == 1, "Should have 1 cached item"

        # 3. Second call (Cache Hit) - Should NOT call network
        # Reset mock to ensure it's not called
        client.session.post.reset_mock()
        
        result = await client.resolve_by_isbn("9780593135204")
        
        assert result.success
        assert result.book.title == "Project Hail Mary"
        client.session.post.assert_not_called()

    # ========================================
    # 6. ERROR HANDLING
    # ========================================

    async def test_api_error_handling(self):
        """Test handling of API errors."""
        client = HardcoverClient("fake_token", cache_db_path=self.test_db)
        
        # Mock 500 error
        mock_session = MagicMock()
        mock_resp = AsyncMock()
        mock_resp.status = 500
        mock_session.post.return_value.__aenter__.return_value = mock_resp
        client.session = mock_session

        result = await client.resolve_by_isbn("9780593135204")
        
        assert not result.success
        assert "Error" in result.note


async def main():
    tester = TestHardcoverClientMock()
    
    print("============================================================")
    print("Hardcover Client Mock Validation")
    print("============================================================")
    
    await tester.run_test("Initialization", tester.test_initialization)
    await tester.run_test("ISBN Resolution", tester.test_resolve_by_isbn)
    await tester.run_test("ISBN Not Found", tester.test_resolve_by_isbn_not_found)
    await tester.run_test("Title/Author Resolution", tester.test_resolve_by_title_author)
    await tester.run_test("Waterfall Logic", tester.test_waterfall_resolution)
    await tester.run_test("Caching Mechanism", tester.test_caching_mechanism)
    await tester.run_test("API Error Handling", tester.test_api_error_handling)
    
    print("\n============================================================")
    passed = sum(1 for r in tester.results if r[1])
    total = len(tester.results)
    print(f"Results: {passed}/{total} passed")
    print("============================================================")

if __name__ == "__main__":
    asyncio.run(main())
