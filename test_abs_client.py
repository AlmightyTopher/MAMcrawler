"""
Comprehensive validation test suite for AudiobookshelfClient module.

Tests cover:
1. Initialization and Configuration
2. Session Management
3. Request Handling & Retries
4. Library Operations (with pagination)
5. Book Management
6. Collections Management
7. Playlists Management
8. Progress Tracking
9. User Management
10. Error Handling
11. Context Manager
12. Complete Workflow

Execute with: python test_abs_client.py
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from aiohttp import ClientResponseError, ClientError

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.integrations.abs_client import (
    AudiobookshelfClient,
    AudiobookshelfError,
)


def create_mock_response(status=200, json_data=None):
    """Create a mock aiohttp response."""
    mock_resp = AsyncMock()
    mock_resp.status = status
    mock_resp.json = AsyncMock(return_value=json_data or {})
    mock_resp.raise_for_status = Mock()

    if status >= 400:
        mock_resp.raise_for_status.side_effect = ClientResponseError(
            request_info=Mock(),
            history=(),
            status=status,
            message="Error"
        )

    return mock_resp


class TestAudiobookshelfClient:
    """Test suite for Audiobookshelf client module."""

    def __init__(self):
        self.results = []

    def run_test(self, test_name: str, test_func):
        """Run a single test and record result."""
        try:
            asyncio.run(test_func())
            self.results.append((test_name, True, None))
            print(f"✓ {test_name}")
        except AssertionError as e:
            self.results.append((test_name, False, str(e)))
            print(f"✗ {test_name}: {e}")
        except Exception as e:
            self.results.append((test_name, False, f"Unexpected error: {e}"))
            print(f"✗ {test_name}: Unexpected error: {e}")

    # ========================================
    # 1. INITIALIZATION AND CONFIGURATION
    # ========================================

    async def test_initialization_basic(self):
        """Test basic client initialization."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token_123",
            timeout=30
        )

        assert client.base_url == "http://localhost:13378", "Base URL not set correctly"
        assert client.api_token == "test_token_123", "API token not set correctly"
        assert client.timeout.total == 30, "Timeout not set correctly"
        assert client.headers["Authorization"] == "Bearer test_token_123", "Authorization header not set"
        assert client.headers["Content-Type"] == "application/json", "Content-Type header not set"

    async def test_initialization_base_url_trailing_slash(self):
        """Test base URL trailing slash is stripped."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378/",
            api_token="test_token"
        )

        assert client.base_url == "http://localhost:13378", "Trailing slash should be stripped"

    async def test_initialization_managers(self):
        """Test that all manager modules are initialized."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        # Check all 10 managers are initialized
        assert hasattr(client, 'libraries'), "Libraries manager not initialized"
        assert hasattr(client, 'collections'), "Collections manager not initialized"
        assert hasattr(client, 'playlists'), "Playlists manager not initialized"
        assert hasattr(client, 'progress'), "Progress manager not initialized"
        assert hasattr(client, 'users'), "Users manager not initialized"
        assert hasattr(client, 'backups'), "Backups manager not initialized"
        assert hasattr(client, 'notifications'), "Notifications manager not initialized"
        assert hasattr(client, 'rss'), "RSS manager not initialized"
        assert hasattr(client, 'api_keys'), "API keys manager not initialized"
        assert hasattr(client, 'email'), "Email manager not initialized"

    # ========================================
    # 2. SESSION MANAGEMENT
    # ========================================

    async def test_ensure_session_creates_session(self):
        """Test _ensure_session creates session if not exists."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        assert client.session is None, "Session should be None initially"

        await client._ensure_session()

        assert client.session is not None, "Session should be created"

    async def test_context_manager(self):
        """Test async context manager entry and exit."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        async with client as c:
            assert c is client, "Context manager should return client instance"
            assert client.session is not None, "Session should be created"

        # Session should still exist but we can't easily check if closed without mock

    # ========================================
    # 3. REQUEST HANDLING & RETRIES
    # ========================================

    async def test_request_with_bearer_token(self):
        """Test request includes Bearer token in headers."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token_123"
        )

        # Setup session
        mock_session = Mock()
        client.session = mock_session

        # Mock response
        mock_resp = create_mock_response(status=200, json_data={"status": "ok"})
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = Mock(return_value=mock_resp)

        result = await client._request("GET", "/api/test")

        # Check headers were passed
        assert "Authorization" in client.headers, "Authorization header should exist"
        assert client.headers["Authorization"] == "Bearer test_token_123", "Bearer token not correct"

    async def test_request_204_no_content(self):
        """Test request handles 204 No Content correctly."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        # Setup session
        mock_session = Mock()
        client.session = mock_session

        # Mock 204 response
        mock_resp = create_mock_response(status=204)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = Mock(return_value=mock_resp)

        result = await client._request("DELETE", "/api/test")

        assert result == {}, "204 response should return empty dict"

    async def test_request_json_response(self):
        """Test request handles JSON response correctly."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        # Setup session
        mock_session = Mock()
        client.session = mock_session

        # Mock JSON response
        mock_resp = create_mock_response(status=200, json_data={"books": [{"id": "1", "title": "Test"}]})
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = Mock(return_value=mock_resp)

        result = await client._request("GET", "/api/books")

        assert isinstance(result, dict), "Result should be dict"
        assert "books" in result, "Should contain books key"

    async def test_request_timeout_error(self):
        """Test request handles timeout errors."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        # Setup session
        mock_session = Mock()
        client.session = mock_session

        # Mock timeout error
        class MockTimeoutResponse:
            async def __aenter__(self):
                raise asyncio.TimeoutError()

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        mock_session.request = Mock(return_value=MockTimeoutResponse())

        try:
            await client._request("GET", "/api/test")
            assert False, "Should raise AudiobookshelfError"
        except AudiobookshelfError as e:
            assert "timeout" in str(e).lower(), "Error should mention timeout"

    # ========================================
    # 4. LIBRARY OPERATIONS (WITH PAGINATION)
    # ========================================

    async def test_get_library_items_pagination(self):
        """Test get_library_items with pagination."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        # Track call count for pagination test
        call_count = [0]

        async def mock_request_side_effect(method, endpoint, **kwargs):
            call_count[0] += 1

            # First call: get libraries (exact match)
            if endpoint == "/api/libraries":
                return {
                    "libraries": [{"id": "lib123", "name": "Main"}]
                }
            # Subsequent calls: paginated items
            elif "/items" in endpoint:
                params = kwargs.get('params', {})
                offset = params.get('offset', 0)

                if offset == 0:
                    # First page: 100 items, total 150
                    return {
                        "results": [{"id": f"book{i}"} for i in range(100)],
                        "total": 150
                    }
                else:
                    # Second page: 50 items
                    return {
                        "results": [{"id": f"book{i}"} for i in range(100, 150)],
                        "total": 150
                    }
            else:
                return {}

        with patch.object(client, '_request', side_effect=mock_request_side_effect):
            items = await client.get_library_items(limit=100)

            assert len(items) == 150, f"Should retrieve all 150 items, got {len(items)}"
            assert call_count[0] >= 2, "Should make multiple paginated requests"

    async def test_get_library_items_safety_check(self):
        """Test get_library_items stops at 100k offset safety limit."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        # Mock request that always returns more items
        call_count = [0]

        async def mock_request_always_more(method, endpoint, **kwargs):
            call_count[0] += 1

            if "/api/libraries" in endpoint:
                return {
                    "libraries": [{"id": "lib123"}]
                }
            else:
                # Always return items indicating more exist (infinite pagination trap)
                params = kwargs.get('params', {})
                offset = params.get('offset', 0)
                return {
                    "results": [{"id": f"book{i}"} for i in range(100)],
                    "total": 200000  # Claim 200k total to trigger infinite loop
                }

        with patch.object(client, '_request', side_effect=mock_request_always_more):
            items = await client.get_library_items(limit=100)

            # Should stop before retrieving all due to safety check
            assert len(items) < 200000, "Should stop due to safety check"

    async def test_get_book_by_id(self):
        """Test getting single book by ID."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        mock_book = {
            "id": "book123",
            "media": {
                "metadata": {
                    "title": "Test Book",
                    "author": "Test Author"
                }
            }
        }

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_book)):
            book = await client.get_book_by_id("book123")

            assert book["id"] == "book123", "Should return correct book"
            assert book["media"]["metadata"]["title"] == "Test Book", "Should have metadata"

    async def test_search_books(self):
        """Test searching for books."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        mock_response = {
            "book": [
                {"id": "1", "title": "Foundation"},
                {"id": "2", "title": "Foundation and Empire"}
            ]
        }

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_response)):
            results = await client.search_books("Foundation", limit=20)

            assert len(results) == 2, "Should return 2 results"
            assert results[0]["title"] == "Foundation", "First result correct"

    # ========================================
    # 5. BOOK MANAGEMENT
    # ========================================

    async def test_update_book_metadata_field_transformation(self):
        """Test metadata field transformation (authors list, series)."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        # Mock request to capture what's sent
        captured_payload = {}

        async def capture_request(method, endpoint, **kwargs):
            nonlocal captured_payload
            if 'json' in kwargs:
                captured_payload = kwargs['json']
            return {"success": True}

        with patch.object(client, '_request', side_effect=capture_request):
            await client.update_book_metadata(
                "book123",
                {
                    "authors": ["Isaac Asimov", "Robert Heinlein"],
                    "series": "Foundation",
                    "seriesSequence": "1",
                    "title": "Foundation"
                }
            )

            # Check field transformations
            metadata = captured_payload.get("metadata", {})
            assert metadata["authorName"] == "Isaac Asimov, Robert Heinlein", "Authors should be joined"
            assert metadata["seriesName"] == "Foundation #1", "Series should include sequence"
            assert "seriesSequence" not in metadata, "seriesSequence should not be in final payload"
            assert metadata["title"] == "Foundation", "Title should pass through"

    async def test_scan_library(self):
        """Test triggering library scan."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        # Mock getting libraries and scan
        call_count = [0]

        async def mock_scan_request(method, endpoint, **kwargs):
            call_count[0] += 1
            if "/api/libraries" in endpoint and method == "GET":
                return {
                    "libraries": [{"id": "lib123"}]
                }
            else:
                return {
                    "success": True
                }

        with patch.object(client, '_request', side_effect=mock_scan_request):
            result = await client.scan_library()

            assert result["success"], "Scan should succeed"
            assert call_count[0] >= 2, "Should call get libraries then scan"

    async def test_delete_book(self):
        """Test deleting book with hard delete option."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        with patch.object(client, '_request', new=AsyncMock(return_value={"success": True})) as mock_req:
            # Test soft delete
            result = await client.delete_book("book123", hard_delete=False)
            assert result["success"], "Soft delete should succeed"

            # Test hard delete
            result = await client.delete_book("book456", hard_delete=True)
            assert result["success"], "Hard delete should succeed"

    # ========================================
    # 6. COLLECTIONS MANAGEMENT
    # ========================================

    async def test_create_collection(self):
        """Test creating a collection."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        mock_collection = {"id": "col123", "name": "My Collection"}

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_collection)):
            collection = await client.create_collection("My Collection", "Description")

            assert collection["id"] == "col123", "Should return created collection"
            assert collection["name"] == "My Collection", "Name should match"

    async def test_get_collections(self):
        """Test getting all collections."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        mock_response = {
            "results": [
                {"id": "col1", "name": "Collection 1"},
                {"id": "col2", "name": "Collection 2"}
            ]
        }

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_response)):
            collections = await client.get_collections()

            assert len(collections) == 2, "Should return 2 collections"

    async def test_batch_add_to_collection(self):
        """Test batch adding books to collection."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        with patch.object(client, '_request', new=AsyncMock(return_value={"success": True})):
            result = await client.batch_add_to_collection(
                "col123",
                ["book1", "book2", "book3"]
            )

            assert result["success"], "Batch add should succeed"

    # ========================================
    # 7. PLAYLISTS MANAGEMENT
    # ========================================

    async def test_create_playlist(self):
        """Test creating a playlist."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        mock_playlist = {"id": "pl123", "name": "My Playlist"}

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_playlist)):
            playlist = await client.create_playlist("My Playlist", "Description")

            assert playlist["id"] == "pl123", "Should return created playlist"

    async def test_add_item_to_playlist(self):
        """Test adding item to playlist."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        with patch.object(client, '_request', new=AsyncMock(return_value={"success": True})):
            result = await client.add_item_to_playlist("pl123", "item456")

            assert result["success"], "Add to playlist should succeed"

    async def test_create_playlist_from_collection(self):
        """Test creating playlist from collection."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        mock_playlist = {"id": "pl123", "name": "From Collection"}

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_playlist)):
            playlist = await client.create_playlist_from_collection(
                "col123",
                "From Collection"
            )

            assert playlist["id"] == "pl123", "Should return created playlist"

    # ========================================
    # 8. PROGRESS TRACKING
    # ========================================

    async def test_get_media_progress(self):
        """Test getting media progress."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        mock_progress = {
            "libraryItemId": "item123",
            "progress": 0.75,
            "currentTime": 1800.5
        }

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_progress)):
            progress = await client.get_media_progress("item123")

            assert progress["progress"] == 0.75, "Progress should be 0.75"
            assert progress["currentTime"] == 1800.5, "Current time should match"

    async def test_update_media_progress(self):
        """Test updating media progress."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        with patch.object(client, '_request', new=AsyncMock(return_value={"success": True})):
            result = await client.update_media_progress(
                "item123",
                progress=0.5,
                current_time=900.0,
                is_finished=False
            )

            assert result["success"], "Update progress should succeed"

    async def test_create_bookmark(self):
        """Test creating a bookmark."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        mock_bookmark = {
            "libraryItemId": "item123",
            "title": "Chapter 5",
            "time": 1800.0
        }

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_bookmark)):
            bookmark = await client.create_bookmark("item123", "Chapter 5", 1800.0)

            assert bookmark["title"] == "Chapter 5", "Bookmark title should match"
            assert bookmark["time"] == 1800.0, "Bookmark time should match"

    async def test_get_items_in_progress(self):
        """Test getting items in progress."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        mock_response = {
            "libraryItems": [
                {"id": "item1", "progress": 0.3},
                {"id": "item2", "progress": 0.7}
            ]
        }

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_response)):
            items = await client.get_items_in_progress()

            assert len(items) == 2, "Should return 2 items in progress"

    # ========================================
    # 9. USER MANAGEMENT
    # ========================================

    async def test_get_user_profile(self):
        """Test getting user profile."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        mock_profile = {
            "id": "user123",
            "username": "testuser",
            "email": "test@example.com"
        }

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_profile)):
            profile = await client.get_user_profile()

            assert profile["username"] == "testuser", "Username should match"

    async def test_update_user_settings(self):
        """Test updating user settings."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        with patch.object(client, '_request', new=AsyncMock(return_value={"success": True})):
            result = await client.update_user_settings({"playbackRate": 1.25})

            assert result["success"], "Update settings should succeed"

    async def test_change_password(self):
        """Test changing user password."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        with patch.object(client, '_request', new=AsyncMock(return_value={})):
            result = await client.change_password("oldpass", "newpass")

            assert result is True, "Password change should return True"

    # ========================================
    # 10. ERROR HANDLING
    # ========================================

    async def test_api_error_handling(self):
        """Test handling of API errors."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        # Setup session
        mock_session = Mock()
        client.session = mock_session

        # Mock 404 error
        class MockErrorResponse:
            status = 404

            async def __aenter__(self):
                error = ClientResponseError(
                    request_info=Mock(),
                    history=(),
                    status=404,
                    message="Not Found"
                )
                raise error

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

            def raise_for_status(self):
                pass

        mock_session.request = Mock(return_value=MockErrorResponse())

        try:
            await client._request("GET", "/api/books/nonexistent")
            assert False, "Should raise AudiobookshelfError"
        except AudiobookshelfError as e:
            assert "404" in str(e), "Error should mention 404 status"

    async def test_network_error_handling(self):
        """Test handling of network errors."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        # Setup session
        mock_session = Mock()
        client.session = mock_session

        # Mock network error
        class MockNetworkError:
            async def __aenter__(self):
                raise ClientError("Network error")

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        mock_session.request = Mock(return_value=MockNetworkError())

        try:
            await client._request("GET", "/api/test")
            assert False, "Should raise AudiobookshelfError"
        except AudiobookshelfError as e:
            assert "Request failed" in str(e), "Error message incorrect"

    # ========================================
    # 11. CONTEXT MANAGER
    # ========================================

    async def test_close_method(self):
        """Test close method."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        # Create mock session
        mock_session = AsyncMock()
        client.session = mock_session

        await client.close()

        mock_session.close.assert_called_once()
        assert client.session is None, "Session should be set to None"

    # ========================================
    # 12. COMPLETE WORKFLOW
    # ========================================

    async def test_complete_workflow_library_to_collection(self):
        """Test complete workflow: get library, search, add to collection."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        # Mock sequence of operations
        call_sequence = []

        async def mock_request_workflow(method, endpoint, **kwargs):
            call_sequence.append(endpoint)

            if "/api/libraries" in endpoint:
                return {
                    "libraries": [{"id": "lib123"}]
                }
            elif "/api/search/books" in endpoint:
                return {
                    "book": [{"id": "book123", "title": "Foundation"}]
                }
            elif "/api/collections" in endpoint and method == "POST":
                return {
                    "id": "col123", "name": "Sci-Fi"
                }
            else:
                return {
                    "success": True
                }

        with patch.object(client, '_request', side_effect=mock_request_workflow):
            # Search for book
            results = await client.search_books("Foundation")
            assert len(results) == 1, "Should find 1 book"

            # Create collection
            collection = await client.create_collection("Sci-Fi")
            assert collection["id"] == "col123", "Should create collection"

            # Add book to collection
            await client.add_book_to_collection("col123", "book123")

            assert len(call_sequence) >= 3, "Should make multiple API calls"

    async def test_complete_workflow_progress_tracking(self):
        """Test complete workflow: get progress, update, create bookmark."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        with patch.object(client, '_request', new=AsyncMock()) as mock_req:
            # Get current progress
            mock_req.return_value = {"progress": 0.5, "currentTime": 900.0}
            progress = await client.get_media_progress("item123")
            assert progress["progress"] == 0.5, "Should get current progress"

            # Update progress
            mock_req.return_value = {"success": True}
            await client.update_media_progress("item123", 0.75, 1800.0)

            # Create bookmark
            mock_req.return_value = {"title": "Chapter 10", "time": 1800.0}
            bookmark = await client.create_bookmark("item123", "Chapter 10", 1800.0)
            assert bookmark["title"] == "Chapter 10", "Should create bookmark"

    async def test_complete_workflow_import_and_metadata(self):
        """Test complete workflow: scan library, search, update metadata."""
        client = AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test_token"
        )

        # Mock import book which triggers scan and metadata update
        with patch.object(client, 'scan_library', new=AsyncMock(return_value={"success": True})), \
             patch.object(client, 'search_books', new=AsyncMock(return_value=[{"id": "book123"}])), \
             patch.object(client, 'update_book_metadata', new=AsyncMock(return_value={"success": True})):

            result = await client.import_book(
                "lib123",
                "/audiobooks/test.m4b",
                {"title": "Test Book", "authors": ["Test Author"]}
            )

            assert result["success"], "Import should succeed"
            assert result["book_id"] == "book123", "Should return book ID"

    def run_all_tests(self):
        """Execute all test categories."""
        print("=" * 60)
        print("AudiobookShelf Client Module Validation")
        print("=" * 60)
        print()

        # Category 1: Initialization and Configuration
        print("Category 1: Initialization and Configuration")
        print("-" * 60)
        self.run_test("Initialization - Basic", self.test_initialization_basic)
        self.run_test("Initialization - Base URL trailing slash", self.test_initialization_base_url_trailing_slash)
        self.run_test("Initialization - Managers", self.test_initialization_managers)
        print()

        # Category 2: Session Management
        print("Category 2: Session Management")
        print("-" * 60)
        self.run_test("Ensure session - Creates session", self.test_ensure_session_creates_session)
        self.run_test("Context manager", self.test_context_manager)
        print()

        # Category 3: Request Handling & Retries
        print("Category 3: Request Handling & Retries")
        print("-" * 60)
        self.run_test("Request - Bearer token", self.test_request_with_bearer_token)
        self.run_test("Request - 204 No Content", self.test_request_204_no_content)
        self.run_test("Request - JSON response", self.test_request_json_response)
        self.run_test("Request - Timeout error", self.test_request_timeout_error)
        print()

        # Category 4: Library Operations
        print("Category 4: Library Operations (with Pagination)")
        print("-" * 60)
        self.run_test("Library items - Pagination", self.test_get_library_items_pagination)
        self.run_test("Library items - Safety check (100k limit)", self.test_get_library_items_safety_check)
        self.run_test("Get book by ID", self.test_get_book_by_id)
        self.run_test("Search books", self.test_search_books)
        print()

        # Category 5: Book Management
        print("Category 5: Book Management")
        print("-" * 60)
        self.run_test("Update metadata - Field transformation", self.test_update_book_metadata_field_transformation)
        self.run_test("Scan library", self.test_scan_library)
        self.run_test("Delete book", self.test_delete_book)
        print()

        # Category 6: Collections Management
        print("Category 6: Collections Management")
        print("-" * 60)
        self.run_test("Create collection", self.test_create_collection)
        self.run_test("Get collections", self.test_get_collections)
        self.run_test("Batch add to collection", self.test_batch_add_to_collection)
        print()

        # Category 7: Playlists Management
        print("Category 7: Playlists Management")
        print("-" * 60)
        self.run_test("Create playlist", self.test_create_playlist)
        self.run_test("Add item to playlist", self.test_add_item_to_playlist)
        self.run_test("Create playlist from collection", self.test_create_playlist_from_collection)
        print()

        # Category 8: Progress Tracking
        print("Category 8: Progress Tracking")
        print("-" * 60)
        self.run_test("Get media progress", self.test_get_media_progress)
        self.run_test("Update media progress", self.test_update_media_progress)
        self.run_test("Create bookmark", self.test_create_bookmark)
        self.run_test("Get items in progress", self.test_get_items_in_progress)
        print()

        # Category 9: User Management
        print("Category 9: User Management")
        print("-" * 60)
        self.run_test("Get user profile", self.test_get_user_profile)
        self.run_test("Update user settings", self.test_update_user_settings)
        self.run_test("Change password", self.test_change_password)
        print()

        # Category 10: Error Handling
        print("Category 10: Error Handling")
        print("-" * 60)
        self.run_test("API error handling", self.test_api_error_handling)
        self.run_test("Network error handling", self.test_network_error_handling)
        print()

        # Category 11: Context Manager
        print("Category 11: Context Manager")
        print("-" * 60)
        self.run_test("Close method", self.test_close_method)
        print()

        # Category 12: Complete Workflow
        print("Category 12: Complete Workflow")
        print("-" * 60)
        self.run_test("Workflow - Library to collection", self.test_complete_workflow_library_to_collection)
        self.run_test("Workflow - Progress tracking", self.test_complete_workflow_progress_tracking)
        self.run_test("Workflow - Import and metadata", self.test_complete_workflow_import_and_metadata)
        print()

        # Summary
        print("=" * 60)
        passed = sum(1 for _, success, _ in self.results if success)
        failed = len(self.results) - passed
        print(f"Results: {passed}/{len(self.results)} tests passed")
        print("=" * 60)

        if failed == 0:
            print()
            print("🎉 All AudiobookShelf client tests passed!")
        else:
            print()
            print(f"❌ {failed} test(s) failed:")
            for name, success, error in self.results:
                if not success:
                    print(f"  - {name}: {error}")

        return failed == 0


if __name__ == "__main__":
    tester = TestAudiobookshelfClient()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
