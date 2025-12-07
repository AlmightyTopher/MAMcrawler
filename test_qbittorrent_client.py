"""
Comprehensive validation test suite for QBittorrentClient module.

Tests cover:
1. Initialization and Configuration
2. Authentication Flow
3. Session Management
4. Request Handling & Retries
5. Torrent Operations
6. RSS Management
7. Bandwidth Management
8. Category Management
9. Server State & Info
10. Error Handling
11. Context Manager
12. Complete Workflow

Execute with: python test_qbittorrent_client.py
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from aiohttp import ClientResponseError, ClientError
import re


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.integrations.qbittorrent_client import (
    QBittorrentClient,
    QBittorrentError,
    QBittorrentAuthError,
)


def create_mock_response(status=200, text="Ok.", json_data=None, headers=None):
    """Create a mock aiohttp response."""
    mock_resp = AsyncMock()
    mock_resp.status = status
    mock_resp.text = AsyncMock(return_value=text)
    mock_resp.json = AsyncMock(return_value=json_data or {})
    mock_resp.raise_for_status = Mock()
    mock_resp.headers = headers or {}

    if status >= 400:
        mock_resp.raise_for_status.side_effect = ClientResponseError(
            request_info=Mock(),
            history=(),
            status=status,
            message="Error"
        )

    return mock_resp


class TestQBittorrentClient:
    """Test suite for qBittorrent client module."""

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
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass",
            timeout=30
        )

        assert client.base_url == "http://localhost:8080", "Base URL not set correctly"
        assert client.username == "admin", "Username not set correctly"
        assert client.password == "adminpass", "Password not set correctly"
        assert client.timeout.total == 30, "Timeout not set correctly"
        assert not client._authenticated, "Should not be authenticated initially"
        assert client._sid is None, "SID should be None initially"

    async def test_initialization_base_url_trailing_slash(self):
        """Test base URL trailing slash is stripped."""
        client = QBittorrentClient(
            base_url="http://localhost:8080/",  # With trailing slash
            username="admin",
            password="adminpass"
        )

        assert client.base_url == "http://localhost:8080", "Trailing slash should be stripped"

    async def test_initialization_managers(self):
        """Test that managers are initialized."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        assert hasattr(client, 'bandwidth'), "Bandwidth manager not initialized"
        assert hasattr(client, 'rss'), "RSS manager not initialized"
        assert client.bandwidth is not None, "Bandwidth manager is None"
        assert client.rss is not None, "RSS manager is None"

    # ========================================
    # 2. AUTHENTICATION FLOW
    # ========================================

    async def test_login_success(self):
        """Test successful login flow."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        # Mock session
        mock_session = Mock()
        client.session = mock_session

        # Mock successful login response with SID
        mock_resp = create_mock_response(
            status=200,
            text="Ok.",
            headers={"Set-Cookie": "SID=test_session_id; Path=/; HttpOnly; SameSite=Strict"}
        )
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)
        mock_session.post = Mock(return_value=mock_resp)

        await client._login()

        assert client._authenticated, "Should be authenticated after login"
        assert client._sid == "test_session_id", "SID should be extracted from cookie"
        mock_session.post.assert_called_once()

    async def test_login_failure(self):
        """Test login failure handling."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="wrong_pass"
        )

        # Mock session
        mock_session = Mock()
        client.session = mock_session

        # Mock failed login response
        mock_resp = create_mock_response(status=200, text="Fails.")
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)
        mock_session.post = Mock(return_value=mock_resp)

        try:
            await client._login()
            assert False, "Should raise QBittorrentAuthError"
        except QBittorrentAuthError as e:
            assert "Authentication failed" in str(e), "Wrong error message"
            assert not client._authenticated, "Should not be authenticated"

    async def test_logout(self):
        """Test logout flow."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        # Mock session
        mock_session = Mock()
        client.session = mock_session
        client._authenticated = True

        # Mock logout response
        mock_resp = create_mock_response(status=200, text="Ok.")
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)
        mock_session.post = Mock(return_value=mock_resp)

        await client._logout()

        assert not client._authenticated, "Should not be authenticated after logout"
        mock_session.post.assert_called_once()

    # ========================================
    # 3. SESSION MANAGEMENT
    # ========================================

    async def test_ensure_session_creates_session(self):
        """Test _ensure_session creates session if not exists."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        assert client.session is None, "Session should be None initially"

        # Mock login
        with patch.object(client, '_login', new=AsyncMock()):
            await client._ensure_session()

            assert client.session is not None, "Session should be created"

    async def test_ensure_session_authenticates(self):
        """Test _ensure_session authenticates if not authenticated."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        client.session = AsyncMock()
        assert not client._authenticated, "Should not be authenticated initially"

        # Mock login
        with patch.object(client, '_login', new=AsyncMock()) as mock_login:
            await client._ensure_session()

            mock_login.assert_called_once()

    async def test_context_manager(self):
        """Test async context manager entry and exit."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        # Mock login and logout
        with patch.object(client, '_login', new=AsyncMock()) as mock_login, \
             patch.object(client, '_logout', new=AsyncMock()) as mock_logout:

            async with client as c:
                assert c is client, "Context manager should return client instance"
                assert client.session is not None, "Session should be created"
                mock_login.assert_called_once()

            mock_logout.assert_called_once()

    # ========================================
    # 4. REQUEST HANDLING & RETRIES
    # ========================================

    async def test_request_with_sid_cookie(self):
        """Test request includes SID cookie in headers."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        # Setup authenticated session
        mock_session = Mock()
        client.session = mock_session
        client._authenticated = True
        client._sid = "test_session_id"

        # Mock response
        mock_resp = create_mock_response(status=200, json_data={"status": "ok"})
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = Mock(return_value=mock_resp)

        result = await client._request("GET", "/api/v2/test")

        # Check that SID was added to headers
        call_kwargs = mock_session.request.call_args[1]
        assert 'headers' in call_kwargs, "Headers should be in request"
        assert call_kwargs['headers']['Cookie'] == 'SID=test_session_id', "SID cookie not set correctly"

    async def test_request_403_reauthentication(self):
        """Test request re-authenticates on 403 error."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        # Setup authenticated session
        mock_session = Mock()
        client.session = mock_session
        client._authenticated = True
        client._sid = "old_session_id"

        # Track calls for re-authentication test
        call_count = [0]  # Use list to allow modification in nested function

        # Mock _login to restore authentication
        async def mock_login():
            client._authenticated = True
            client._sid = "new_session_id"

        # Mock 403 response first, then success
        def mock_request_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: 403 error
                resp = create_mock_response(status=403)
                resp.__aenter__ = AsyncMock(return_value=resp)
                resp.__aexit__ = AsyncMock(return_value=None)
                return resp
            else:
                # Second call after re-auth: success
                resp = create_mock_response(status=200, json_data={"status": "ok"})
                resp.__aenter__ = AsyncMock(return_value=resp)
                resp.__aexit__ = AsyncMock(return_value=None)
                return resp

        mock_session.request = Mock(side_effect=mock_request_side_effect)

        # Mock login
        with patch.object(client, '_login', new=AsyncMock(side_effect=mock_login)) as mock_login_obj:
            result = await client._request("GET", "/api/v2/test")
            # Should have re-authenticated after 403
            assert mock_login_obj.call_count >= 1, "Login should be called on 403 error"

    async def test_request_json_response(self):
        """Test request handles JSON response correctly."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        # Setup authenticated session
        mock_session = Mock()
        client.session = mock_session
        client._authenticated = True

        # Mock JSON response
        mock_resp = create_mock_response(
            status=200,
            json_data={"torrents": [{"name": "test", "hash": "abc123"}]},
            headers={"Content-Type": "application/json"}
        )
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = Mock(return_value=mock_resp)

        result = await client._request("GET", "/api/v2/torrents/info")

        assert isinstance(result, dict), "Result should be dict for JSON response"
        assert "torrents" in result, "Should contain torrents key"

    async def test_request_text_response(self):
        """Test request handles text response correctly."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        # Setup authenticated session
        mock_session = Mock()
        client.session = mock_session
        client._authenticated = True

        # Mock text response
        mock_resp = create_mock_response(
            status=200,
            text="Ok.",
            headers={"Content-Type": "text/plain"}
        )
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = Mock(return_value=mock_resp)

        result = await client._request("POST", "/api/v2/torrents/add")

        assert isinstance(result, str), "Result should be string for text response"
        assert result == "Ok.", "Text response not correct"

    # ========================================
    # 5. TORRENT OPERATIONS
    # ========================================

    async def test_add_torrent_basic(self):
        """Test adding torrent with magnet link."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        # Mock request
        with patch.object(client, '_request', new=AsyncMock(return_value="Ok.")) as mock_req, \
             patch.object(client, 'get_all_torrents', new=AsyncMock(return_value=[
                 {"hash": "abc123", "name": "test torrent"}
             ])):

            result = await client.add_torrent(
                magnet_link="magnet:?xt=urn:btih:abc123&dn=test",
                category="audiobooks"
            )

            assert result["success"], "Should return success=True"
            assert result["hash"] == "abc123", "Should return correct hash"

    async def test_get_torrent_status(self):
        """Test getting torrent status."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        # Mock request
        mock_torrents = [
            {
                "hash": "abc123",
                "name": "test torrent",
                "progress": 0.5,
                "state": "downloading",
                "dlspeed": 1024000,
            }
        ]

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_torrents)):
            status = await client.get_torrent_status("abc123")

            assert status["hash"] == "abc123", "Hash should match"
            assert status["progress"] == 0.5, "Progress should be 0.5"
            assert status["state"] == "downloading", "State should be downloading"

    async def test_get_all_torrents_with_filter(self):
        """Test getting all torrents with filters."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        # Mock request
        mock_torrents = [
            {"hash": "abc123", "name": "torrent1", "state": "downloading"},
            {"hash": "def456", "name": "torrent2", "state": "downloading"},
        ]

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_torrents)) as mock_req:
            torrents = await client.get_all_torrents(
                filter_state="downloading",
                category="audiobooks"
            )

            assert len(torrents) == 2, "Should return 2 torrents"

            # Check request params
            call_kwargs = mock_req.call_args[1]
            assert call_kwargs['params']['filter'] == "downloading", "Filter not passed correctly"
            assert call_kwargs['params']['category'] == "audiobooks", "Category not passed correctly"

    async def test_pause_resume_torrent(self):
        """Test pausing and resuming torrents."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        with patch.object(client, '_request', new=AsyncMock(return_value="Ok.")):
            # Test pause
            result = await client.pause_torrent("abc123")
            assert result is True, "Pause should return True"

            # Test resume
            result = await client.resume_torrent("abc123")
            assert result is True, "Resume should return True"

    async def test_delete_torrent(self):
        """Test deleting torrent with and without files."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        with patch.object(client, '_request', new=AsyncMock(return_value="Ok.")) as mock_req:
            # Test delete without files
            result = await client.delete_torrent("abc123", delete_files=False)
            assert result is True, "Delete should return True"

            # Test delete with files
            result = await client.delete_torrent("abc123", delete_files=True)
            assert result is True, "Delete should return True"

    # ========================================
    # 6. RSS MANAGEMENT
    # ========================================

    async def test_add_rss_feed(self):
        """Test adding RSS feed."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        with patch.object(client, '_request', new=AsyncMock(return_value="Ok.")):
            result = await client.add_rss_feed(
                url="https://example.com/rss.xml",
                path="audiobooks"
            )

            assert result is True, "Should return True on success"

    async def test_get_rss_items(self):
        """Test getting RSS items."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        mock_items = {
            "audiobooks": {
                "feed1": {"url": "https://example.com/feed1.xml"}
            }
        }

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_items)):
            items = await client.get_rss_items(with_data=True)

            assert "audiobooks" in items, "Should contain audiobooks folder"
            assert "feed1" in items["audiobooks"], "Should contain feed1"

    async def test_rss_rule_management(self):
        """Test RSS rule creation and retrieval."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        rule_def = {
            "enabled": True,
            "mustContain": "audiobook",
            "assignedCategory": "audiobooks",
        }

        with patch.object(client, '_request', new=AsyncMock(return_value="Ok.")):
            # Set rule
            result = await client.set_rss_rule("test_rule", rule_def)
            assert result is True, "Should return True on success"

            # Remove rule
            result = await client.remove_rss_rule("test_rule")
            assert result is True, "Should return True on success"

    # ========================================
    # 7. BANDWIDTH MANAGEMENT
    # ========================================

    async def test_global_download_limit(self):
        """Test setting and getting global download limit."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        with patch.object(client, '_request', new=AsyncMock()) as mock_req:
            # Set limit
            mock_req.return_value = "Ok."
            result = await client.set_global_download_limit(1024000)
            assert result is True, "Should return True on success"

            # Get limit
            mock_req.return_value = "1024000"
            limit = await client.get_global_download_limit()
            assert limit == 1024000, "Should return correct limit"

    async def test_torrent_specific_limits(self):
        """Test setting torrent-specific bandwidth limits."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        with patch.object(client, '_request', new=AsyncMock(return_value="Ok.")):
            # Set download limit
            result = await client.set_torrent_download_limit("abc123", 512000)
            assert result is True, "Should return True on success"

            # Set upload limit
            result = await client.set_torrent_upload_limit("abc123", 256000)
            assert result is True, "Should return True on success"

    async def test_bandwidth_usage_stats(self):
        """Test getting bandwidth usage statistics."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        mock_state = {
            "dl_info_speed": 1024000,
            "up_info_speed": 512000,
        }

        mock_torrents = [
            {"dlspeed": 500000, "upspeed": 250000, "downloaded": 1000000, "uploaded": 500000, "state": "downloading"},
            {"dlspeed": 300000, "upspeed": 150000, "downloaded": 800000, "uploaded": 400000, "state": "uploading"},
        ]

        with patch.object(client, 'get_server_state', new=AsyncMock(return_value=mock_state)), \
             patch.object(client, 'get_all_torrents', new=AsyncMock(return_value=mock_torrents)):

            stats = await client.get_bandwidth_usage_stats()

            assert stats["server_dl_speed"] == 1024000, "Server DL speed incorrect"
            assert stats["total_torrent_dl_speed"] == 800000, "Total torrent DL speed incorrect"
            assert stats["active_torrents"] == 2, "Active torrents count incorrect"
            assert stats["total_torrents"] == 2, "Total torrents count incorrect"

    # ========================================
    # 8. CATEGORY MANAGEMENT
    # ========================================

    async def test_set_category(self):
        """Test creating/updating category."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        with patch.object(client, '_request', new=AsyncMock(return_value="Ok.")):
            result = await client.set_category(
                category_name="audiobooks",
                save_path="/data/audiobooks"
            )

            assert result is True, "Should return True on success"

    async def test_get_categories(self):
        """Test getting all categories."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        mock_categories = {
            "audiobooks": {"savePath": "/data/audiobooks"},
            "ebooks": {"savePath": "/data/ebooks"},
        }

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_categories)):
            categories = await client.get_categories()

            assert len(categories) == 2, "Should return 2 categories"
            assert "audiobooks" in categories, "Should contain audiobooks category"
            assert categories["audiobooks"]["savePath"] == "/data/audiobooks", "Save path incorrect"

    # ========================================
    # 9. SERVER STATE & INFO
    # ========================================

    async def test_get_server_state(self):
        """Test getting server state."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        mock_state = {
            "dl_info_speed": 1024000,
            "up_info_speed": 512000,
            "connection_status": "connected",
        }

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_state)):
            state = await client.get_server_state()

            assert state["dl_info_speed"] == 1024000, "DL speed incorrect"
            assert state["connection_status"] == "connected", "Connection status incorrect"

    async def test_get_download_path(self):
        """Test getting download paths."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        # Test default path
        mock_prefs = {"save_path": "/data/downloads"}
        with patch.object(client, '_request', new=AsyncMock(return_value=mock_prefs)):
            path = await client.get_download_path()
            assert path == "/data/downloads", "Default path incorrect"

        # Test torrent-specific path
        mock_status = {"save_path": "/data/audiobooks"}
        with patch.object(client, 'get_torrent_status', new=AsyncMock(return_value=mock_status)):
            path = await client.get_download_path(torrent_hash="abc123")
            assert path == "/data/audiobooks", "Torrent-specific path incorrect"

    # ========================================
    # 10. ERROR HANDLING
    # ========================================

    async def test_torrent_not_found_error(self):
        """Test handling of torrent not found error."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        # Mock empty response (torrent not found)
        with patch.object(client, '_request', new=AsyncMock(return_value=[])):
            try:
                await client.get_torrent_status("nonexistent")
                assert False, "Should raise QBittorrentError"
            except QBittorrentError as e:
                assert "not found" in str(e).lower(), "Error message should mention 'not found'"

    async def test_network_error_handling(self):
        """Test handling of network errors."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        # Setup authenticated session
        mock_session = Mock()
        client.session = mock_session
        client._authenticated = True

        # Mock network error - use proper async context manager
        class MockErrorResponse:
            async def __aenter__(self):
                raise ClientError("Network error")

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        mock_session.request = Mock(return_value=MockErrorResponse())

        try:
            await client._request("GET", "/api/v2/test")
            assert False, "Should raise QBittorrentError"
        except QBittorrentError as e:
            assert "Request failed" in str(e), "Error message incorrect"

    async def test_timeout_error_handling(self):
        """Test handling of timeout errors."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        # Setup authenticated session
        mock_session = Mock()
        client.session = mock_session
        client._authenticated = True

        # Mock timeout error - use proper async context manager
        class MockTimeoutResponse:
            async def __aenter__(self):
                raise asyncio.TimeoutError()

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        mock_session.request = Mock(return_value=MockTimeoutResponse())

        try:
            await client._request("GET", "/api/v2/test")
            assert False, "Should raise QBittorrentError"
        except QBittorrentError as e:
            assert "timeout" in str(e).lower(), "Error message should mention timeout"

    # ========================================
    # 11. CONTEXT MANAGER
    # ========================================

    async def test_close_method(self):
        """Test close method."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        # Mock session
        mock_session = AsyncMock()
        client.session = mock_session
        client._authenticated = True

        # Mock logout
        with patch.object(client, '_logout', new=AsyncMock()) as mock_logout:
            await client.close()

            mock_logout.assert_called_once()
            mock_session.close.assert_called_once()

    # ========================================
    # 12. COMPLETE WORKFLOW
    # ========================================

    async def test_complete_workflow_add_monitor_delete(self):
        """Test complete workflow: add torrent, monitor, then delete."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        # Mock all operations
        with patch.object(client, '_request', new=AsyncMock()) as mock_req, \
             patch.object(client, 'get_all_torrents', new=AsyncMock(return_value=[
                 {"hash": "abc123", "name": "test"}
             ])):

            # Add torrent
            mock_req.return_value = "Ok."
            result = await client.add_torrent("magnet:?xt=urn:btih:abc123")
            assert result["success"], "Add torrent should succeed"

            # Get status
            mock_req.return_value = [
                {"hash": "abc123", "progress": 0.5, "state": "downloading"}
            ]
            status = await client.get_torrent_status("abc123")
            assert status["progress"] == 0.5, "Progress should be 0.5"

            # Delete torrent
            mock_req.return_value = "Ok."
            result = await client.delete_torrent("abc123", delete_files=True)
            assert result is True, "Delete should succeed"

    async def test_complete_workflow_category_rss(self):
        """Test workflow: create category, add RSS feed, set rule."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        with patch.object(client, '_request', new=AsyncMock(return_value="Ok.")):
            # Create category
            result = await client.set_category("audiobooks", "/data/audiobooks")
            assert result is True, "Category creation should succeed"

            # Add RSS feed
            result = await client.add_rss_feed(
                "https://example.com/rss.xml",
                "audiobooks"
            )
            assert result is True, "RSS feed addition should succeed"

            # Set RSS rule
            rule = {"enabled": True, "mustContain": "audiobook"}
            result = await client.set_rss_rule("audiobook_rule", rule)
            assert result is True, "RSS rule creation should succeed"

    async def test_complete_workflow_bandwidth_management(self):
        """Test workflow: set limits, get stats, adjust limits."""
        client = QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="adminpass"
        )

        with patch.object(client, '_request', new=AsyncMock()) as mock_req, \
             patch.object(client, 'get_server_state', new=AsyncMock(return_value={
                 "dl_info_speed": 1024000, "up_info_speed": 512000
             })), \
             patch.object(client, 'get_all_torrents', new=AsyncMock(return_value=[])):

            # Set global limits
            mock_req.return_value = "Ok."
            result = await client.set_global_download_limit(2048000)
            assert result is True, "Set global DL limit should succeed"

            result = await client.set_global_upload_limit(1024000)
            assert result is True, "Set global UL limit should succeed"

            # Get stats
            stats = await client.get_bandwidth_usage_stats()
            assert "server_dl_speed" in stats, "Stats should contain server_dl_speed"
            assert "total_torrents" in stats, "Stats should contain total_torrents"

    def run_all_tests(self):
        """Execute all test categories."""
        print("=" * 60)
        print("qBittorrent Client Module Validation")
        print("=" * 60)
        print()

        # Category 1: Initialization and Configuration
        print("Category 1: Initialization and Configuration")
        print("-" * 60)
        self.run_test("Initialization - Basic", self.test_initialization_basic)
        self.run_test("Initialization - Base URL trailing slash", self.test_initialization_base_url_trailing_slash)
        self.run_test("Initialization - Managers", self.test_initialization_managers)
        print()

        # Category 2: Authentication Flow
        print("Category 2: Authentication Flow")
        print("-" * 60)
        self.run_test("Login - Success", self.test_login_success)
        self.run_test("Login - Failure", self.test_login_failure)
        self.run_test("Logout", self.test_logout)
        print()

        # Category 3: Session Management
        print("Category 3: Session Management")
        print("-" * 60)
        self.run_test("Ensure session - Creates session", self.test_ensure_session_creates_session)
        self.run_test("Ensure session - Authenticates", self.test_ensure_session_authenticates)
        self.run_test("Context manager", self.test_context_manager)
        print()

        # Category 4: Request Handling & Retries
        print("Category 4: Request Handling & Retries")
        print("-" * 60)
        self.run_test("Request - SID cookie", self.test_request_with_sid_cookie)
        self.run_test("Request - 403 re-authentication", self.test_request_403_reauthentication)
        self.run_test("Request - JSON response", self.test_request_json_response)
        self.run_test("Request - Text response", self.test_request_text_response)
        print()

        # Category 5: Torrent Operations
        print("Category 5: Torrent Operations")
        print("-" * 60)
        self.run_test("Add torrent - Basic", self.test_add_torrent_basic)
        self.run_test("Get torrent status", self.test_get_torrent_status)
        self.run_test("Get all torrents - With filter", self.test_get_all_torrents_with_filter)
        self.run_test("Pause/Resume torrent", self.test_pause_resume_torrent)
        self.run_test("Delete torrent", self.test_delete_torrent)
        print()

        # Category 6: RSS Management
        print("Category 6: RSS Management")
        print("-" * 60)
        self.run_test("Add RSS feed", self.test_add_rss_feed)
        self.run_test("Get RSS items", self.test_get_rss_items)
        self.run_test("RSS rule management", self.test_rss_rule_management)
        print()

        # Category 7: Bandwidth Management
        print("Category 7: Bandwidth Management")
        print("-" * 60)
        self.run_test("Global download limit", self.test_global_download_limit)
        self.run_test("Torrent-specific limits", self.test_torrent_specific_limits)
        self.run_test("Bandwidth usage stats", self.test_bandwidth_usage_stats)
        print()

        # Category 8: Category Management
        print("Category 8: Category Management")
        print("-" * 60)
        self.run_test("Set category", self.test_set_category)
        self.run_test("Get categories", self.test_get_categories)
        print()

        # Category 9: Server State & Info
        print("Category 9: Server State & Info")
        print("-" * 60)
        self.run_test("Get server state", self.test_get_server_state)
        self.run_test("Get download path", self.test_get_download_path)
        print()

        # Category 10: Error Handling
        print("Category 10: Error Handling")
        print("-" * 60)
        self.run_test("Torrent not found error", self.test_torrent_not_found_error)
        self.run_test("Network error handling", self.test_network_error_handling)
        self.run_test("Timeout error handling", self.test_timeout_error_handling)
        print()

        # Category 11: Context Manager
        print("Category 11: Context Manager")
        print("-" * 60)
        self.run_test("Close method", self.test_close_method)
        print()

        # Category 12: Complete Workflow
        print("Category 12: Complete Workflow")
        print("-" * 60)
        self.run_test("Workflow - Add, monitor, delete", self.test_complete_workflow_add_monitor_delete)
        self.run_test("Workflow - Category, RSS", self.test_complete_workflow_category_rss)
        self.run_test("Workflow - Bandwidth management", self.test_complete_workflow_bandwidth_management)
        print()

        # Summary
        print("=" * 60)
        passed = sum(1 for _, success, _ in self.results if success)
        failed = len(self.results) - passed
        print(f"Results: {passed}/{len(self.results)} tests passed")
        print("=" * 60)

        if failed == 0:
            print()
            print("🎉 All qBittorrent client tests passed!")
        else:
            print()
            print(f"❌ {failed} test(s) failed:")
            for name, success, error in self.results:
                if not success:
                    print(f"  - {name}: {error}")

        return failed == 0


if __name__ == "__main__":
    tester = TestQBittorrentClient()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
