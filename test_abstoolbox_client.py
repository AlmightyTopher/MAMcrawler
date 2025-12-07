"""
Test suite for absToolbox Client
Tests batch operations, quality rules, and standardization logic.

Run with: python test_abstoolbox_client.py
"""

import asyncio
import sys
import json
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from aiohttp import ClientError

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.integrations.abstoolbox_client import (
    absToolboxClient,
    OperationType,
    QUALITY_RULES_TEMPLATE
)


def create_mock_response(status=200, json_data=None):
    """Create a mock aiohttp response."""
    mock_resp = AsyncMock()
    mock_resp.status = status
    mock_resp.json = AsyncMock(return_value=json_data or {})
    mock_resp.raise_for_status = Mock()
    return mock_resp


class TestAbsToolboxClient:
    """Test suite for absToolbox client module."""

    def __init__(self):
        self.results = []
        self.test_dir = Path("test_abstoolbox_logs")

    def setup(self):
        """Setup test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir()

    def teardown(self):
        """Cleanup test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

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
        """Test client initialization."""
        client = absToolboxClient(
            abs_url="http://localhost:13378",
            abs_token="test_token"
        )
        
        assert client.abs_url == "http://localhost:13378"
        assert client.abs_token == "test_token"
        assert client.toolbox_url == "https://abstoolbox.vito0912.de"
        
        # Test custom toolbox URL
        client2 = absToolboxClient(
            abs_url="http://localhost:13378",
            abs_token="test_token",
            toolbox_url="http://custom-toolbox.com/"
        )
        assert client2.toolbox_url == "http://custom-toolbox.com"

    # ========================================
    # 2. LIBRARY STATS
    # ========================================

    async def test_get_library_stats(self):
        """Test fetching library statistics."""
        client = absToolboxClient("http://localhost:13378", "token")
        client.session = Mock()
        
        # Mock responses
        async def mock_request(method, endpoint, **kwargs):
            if endpoint == "/api/libraries":
                return {"libraries": [{"id": "lib1", "name": "Audiobooks"}]}
            elif "/items" in endpoint:
                return {"total": 150}
            return {}
            
        with patch.object(client, '_request', side_effect=mock_request):
            stats = await client.get_library_stats()
            
            assert stats["library_id"] == "lib1"
            assert stats["library_name"] == "Audiobooks"
            assert stats["items"] == 150

    # ========================================
    # 3. QUALITY VALIDATION
    # ========================================

    async def test_validate_metadata_quality(self):
        """Test metadata quality validation logic."""
        client = absToolboxClient("http://localhost:13378", "token")
        client.operation_log_dir = self.test_dir
        client.session = Mock()
        
        # Mock data
        mock_items = [
            {
                "id": "item1",
                "media": {
                    "metadata": {
                        "title": "Good Book",
                        "authorName": "John Smith",  # Valid
                        "narrator": "Jane Doe"       # Valid
                    }
                }
            },
            {
                "id": "item2",
                "media": {
                    "metadata": {
                        "title": "Bad Book",
                        "authorName": "J",           # Too short
                        "narrator": ""               # Missing
                    }
                }
            }
        ]
        
        async def mock_request(method, endpoint, **kwargs):
            if endpoint == "/api/libraries":
                return {"libraries": [{"id": "lib1", "name": "Audiobooks"}]}
            elif "/items" in endpoint:
                # Return items for first page, empty for subsequent to stop loop
                offset = kwargs.get('params', {}).get('offset', 0)
                if offset == 0:
                    return {"results": mock_items, "total": 2}
                return {"results": [], "total": 2}
            return {}

        rules = {
            "authorName": {"required": True, "min_length": 2},
            "narrator": {"required": True}
        }

        with patch.object(client, '_request', side_effect=mock_request):
            issues = await client.validate_metadata_quality(rules)
            
            assert issues["total_checked"] == 2
            assert issues["issues_count"] == 1
            
            # Check specific issues
            problem_item = issues["invalid_format"][0]
            assert problem_item["item_id"] == "item2"
            assert any("too short" in i for i in problem_item["issues"])
            assert any("Missing required" in i for i in problem_item["issues"])

    # ========================================
    # 4. STANDARDIZATION
    # ========================================

    async def test_standardize_metadata(self):
        """Test metadata standardization logic."""
        client = absToolboxClient("http://localhost:13378", "token")
        client.operation_log_dir = self.test_dir
        client.session = Mock()
        
        # Mock data with messy metadata
        mock_items = [
            {
                "id": "item1",
                "media": {
                    "metadata": {
                        "title": "Book 1",
                        "authorName": "Smith, John",           # Should become John Smith
                        "narrator": "Narrated by Jane Doe",    # Should become Jane Doe
                        "seriesName": "Series Vol. 1"          # Should become Series 1
                    }
                }
            }
        ]
        
        async def mock_request(method, endpoint, **kwargs):
            if endpoint == "/api/libraries":
                return {"libraries": [{"id": "lib1", "name": "Audiobooks"}]}
            elif "/items" in endpoint:
                offset = kwargs.get('params', {}).get('offset', 0)
                if offset == 0:
                    return {"results": mock_items, "total": 1}
                return {"results": [], "total": 1}
            return {}

        with patch.object(client, '_request', side_effect=mock_request):
            # Test dry run
            results = await client.standardize_metadata({}, dry_run=True)
            
            assert results["items_updated"] == 1, f"Expected 1 item updated, got {results['items_updated']}"
            changes = results["changes"][0]["changes"]
            
            assert changes.get("authorName") == "John Smith", f"Author name mismatch: {changes.get('authorName')}"
            assert changes.get("narrator") == "Jane Doe", f"Narrator mismatch: {changes.get('narrator')}"
            assert changes.get("seriesName") == "Series 1", f"Series name mismatch: {changes.get('seriesName')}"

    async def test_standardize_metadata_apply(self):
        """Test applying standardization changes."""
        client = absToolboxClient("http://localhost:13378", "token")
        client.operation_log_dir = self.test_dir
        client.session = Mock()
        
        mock_items = [{"id": "item1", "media": {"metadata": {"authorName": "Smith, John"}}}]
        
        # Track patch calls
        patch_calls = []
        
        async def mock_request(method, endpoint, **kwargs):
            if method == "PATCH":
                patch_calls.append((endpoint, kwargs.get('json_data')))
                return {}
            elif endpoint == "/api/libraries":
                return {"libraries": [{"id": "lib1", "name": "Audiobooks"}]}
            elif "/items" in endpoint:
                offset = kwargs.get('params', {}).get('offset', 0)
                if offset == 0:
                    return {"results": mock_items, "total": 1}
                return {"results": [], "total": 1}
            return {}

        with patch.object(client, '_request', side_effect=mock_request):
            # Test actual run (dry_run=False)
            await client.standardize_metadata({}, dry_run=False)
            
            assert len(patch_calls) == 1
            endpoint, data = patch_calls[0]
            assert endpoint == "/api/items/item1"
            assert data["media"]["metadata"]["authorName"] == "John Smith"

    # ========================================
    # 5. SERIES COMPLETION
    # ========================================

    async def test_complete_author_series(self):
        """Test series completion analysis."""
        client = absToolboxClient("http://localhost:13378", "token")
        client.operation_log_dir = self.test_dir
        client.session = Mock()
        
        # Mock books by author
        mock_books = [
            {
                "id": "b1",
                "media": {"metadata": {"authorName": "Isaac Asimov", "seriesName": "Foundation"}}
            },
            {
                "id": "b2",
                "media": {"metadata": {"authorName": "Isaac Asimov", "seriesName": "Foundation"}}
            },
            {
                "id": "b3",
                "media": {"metadata": {"authorName": "Isaac Asimov", "seriesName": "Robot"}}
            },
            {
                "id": "b4",
                "media": {"metadata": {"authorName": "Other Author", "seriesName": "Other"}}
            }
        ]
        
        async def mock_request(method, endpoint, **kwargs):
            if endpoint == "/api/libraries":
                return {"libraries": [{"id": "lib1", "name": "Audiobooks"}]}
            elif "/items" in endpoint:
                offset = kwargs.get('params', {}).get('offset', 0)
                if offset == 0:
                    return {"results": mock_books, "total": 4}
                return {"results": [], "total": 4}
            return {}

        with patch.object(client, '_request', side_effect=mock_request):
            result = await client.complete_author_series("Isaac Asimov")
            
            assert result["author"] == "Isaac Asimov"
            assert result["books_in_library"] == 3  # Should filter out Other Author
            assert len(result["series"]) == 2  # Foundation and Robot
            assert len(result["series"]["Foundation"]) == 2
            assert len(result["series"]["Robot"]) == 1


async def main():
    tester = TestAbsToolboxClient()
    
    print("============================================================")
    print("absToolbox Client Module Validation")
    print("============================================================")
    
    await tester.run_test("Initialization", tester.test_initialization)
    await tester.run_test("Get Library Stats", tester.test_get_library_stats)
    await tester.run_test("Validate Metadata Quality", tester.test_validate_metadata_quality)
    await tester.run_test("Standardize Metadata (Dry Run)", tester.test_standardize_metadata)
    await tester.run_test("Standardize Metadata (Apply)", tester.test_standardize_metadata_apply)
    await tester.run_test("Complete Author Series", tester.test_complete_author_series)
    
    print("\n============================================================")
    passed = sum(1 for r in tester.results if r[1])
    total = len(tester.results)
    print(f"Results: {passed}/{total} passed")
    print("============================================================")

if __name__ == "__main__":
    asyncio.run(main())
