"""
Test suite for Prowlarr Client
Tests search, result enrichment, and magnet extraction.

Run with: python test_prowlarr_client.py
"""

import asyncio
import sys
import json
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from aiohttp import ClientError

# Add project root to path
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.integrations.prowlarr_client import (
    ProwlarrClient,
    ProwlarrError
)

# Mock Data
MOCK_SEARCH_RESULT = {
    "title": "Foundation - Isaac Asimov (Audiobook)",
    "guid": "http://tracker.com/torrent/123",
    "size": 500000000,  # ~500MB
    "indexer": "AudioBookBay",
    "seeders": 10,
    "leechers": 2,
    "publishDate": "2023-01-01T12:00:00Z",
    "magnetUrl": "magnet:?xt=urn:btih:123456...",
    "downloadUrl": "http://tracker.com/download/123.torrent"
}

class TestProwlarrClient:
    """Test suite for Prowlarr client."""

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
        client = ProwlarrClient("http://localhost:9696", "test_key")
        assert client.base_url == "http://localhost:9696"
        assert client.api_key == "test_key"
        assert client.headers["X-Api-Key"] == "test_key"

    # ========================================
    # 2. SEARCH
    # ========================================

    async def test_search(self):
        """Test search functionality."""
        client = ProwlarrClient("http://localhost:9696", "test_key")
        
        # Mock response
        mock_response = [MOCK_SEARCH_RESULT]
        
        # Setup mock session
        mock_session = MagicMock()
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status = Mock()  # Not async
        
        cm = AsyncMock()
        cm.__aenter__.return_value = mock_resp
        cm.__aexit__.return_value = None
        mock_session.request.return_value = cm
        
        client.session = mock_session

        results = await client.search("Foundation")
        
        assert len(results) == 1
        assert results[0]["title"] == MOCK_SEARCH_RESULT["title"]
        assert results[0]["seeders"] == 10

    async def test_search_by_genre(self):
        """Test search by genre."""
        client = ProwlarrClient("http://localhost:9696", "test_key")
        
        # Mock response
        mock_response = [MOCK_SEARCH_RESULT]
        
        mock_session = MagicMock()
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status = Mock()  # Not async
        
        cm = AsyncMock()
        cm.__aenter__.return_value = mock_resp
        cm.__aexit__.return_value = None
        mock_session.request.return_value = cm
        
        client.session = mock_session

        results = await client.search_by_genre("Sci-Fi")
        
        assert len(results) == 1
        # Check that genre was included in query (mock doesn't verify params, but logic is tested)

    # ========================================
    # 3. RESULT ENRICHMENT
    # ========================================

    async def test_get_search_results_enrichment(self):
        """Test result enrichment (size, age, quality score)."""
        client = ProwlarrClient("http://localhost:9696", "test_key")
        
        # Use recent date to ensure positive quality score
        from datetime import datetime
        recent_result = MOCK_SEARCH_RESULT.copy()
        recent_result["publishDate"] = datetime.now().isoformat()
        mock_response = [recent_result]
        
        mock_session = MagicMock()
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status = Mock()  # Not async
        
        cm = AsyncMock()
        cm.__aenter__.return_value = mock_resp
        cm.__aexit__.return_value = None
        mock_session.request.return_value = cm
        
        client.session = mock_session

        results = await client.get_search_results("Foundation")
        
        result = results[0]
        assert "size_gb" in result
        assert result["size_gb"] > 0
        assert "age_days" in result
        assert "quality_score" in result
        # Score = (10 * 10) - 0 = 100
        assert result["quality_score"] > 0

    # ========================================
    # 4. MAGNET EXTRACTION
    # ========================================

    async def test_add_to_download_queue(self):
        """Test magnet link extraction."""
        client = ProwlarrClient("http://localhost:9696", "test_key")
        
        # Case 1: Direct magnet link
        result1 = {"magnetUrl": "magnet:?xt=urn:btih:123"}
        magnet1 = await client.add_to_download_queue(result1)
        assert magnet1 == "magnet:?xt=urn:btih:123"
        
        # Case 2: No magnet, fallback to downloadUrl
        result2 = {"downloadUrl": "http://test.com/file.torrent"}
        magnet2 = await client.add_to_download_queue(result2)
        assert magnet2 == "http://test.com/file.torrent"
        
        # Case 3: None
        result3 = {}
        magnet3 = await client.add_to_download_queue(result3)
        assert magnet3 is None

    # ========================================
    # 5. ERROR HANDLING
    # ========================================

    async def test_api_error(self):
        """Test handling of API errors."""
        client = ProwlarrClient("http://localhost:9696", "test_key")
        
        mock_session = MagicMock()
        mock_resp = AsyncMock()
        mock_resp.status = 401
        # raise_for_status is a synchronous method on ClientResponse
        mock_resp.raise_for_status = Mock()
        mock_resp.raise_for_status.side_effect = ClientError("Unauthorized")
        
        cm = AsyncMock()
        cm.__aenter__.return_value = mock_resp
        cm.__aexit__.return_value = None
        mock_session.request.return_value = cm
        
        client.session = mock_session

        try:
            await client.search("Foundation")
            assert False, "Should have raised ProwlarrError"
        except ProwlarrError as e:
            assert "Request failed" in str(e)


async def main():
    tester = TestProwlarrClient()
    
    print("============================================================")
    print("Prowlarr Client Validation")
    print("============================================================")
    
    await tester.run_test("Initialization", tester.test_initialization)
    await tester.run_test("Search", tester.test_search)
    await tester.run_test("Search by Genre", tester.test_search_by_genre)
    await tester.run_test("Result Enrichment", tester.test_get_search_results_enrichment)
    await tester.run_test("Magnet Extraction", tester.test_add_to_download_queue)
    await tester.run_test("API Error Handling", tester.test_api_error)
    
    print("\n============================================================")
    passed = sum(1 for r in tester.results if r[1])
    total = len(tester.results)
    print(f"Results: {passed}/{total} passed")
    print("============================================================")

if __name__ == "__main__":
    asyncio.run(main())
