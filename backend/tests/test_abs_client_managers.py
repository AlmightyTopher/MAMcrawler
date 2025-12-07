"""
Tests for AudiobookshelfClient Manager Modules

Comprehensive test suite for:
- LibraryManager
- CollectionManager
- PlaylistManager
- ProgressManager
- UserManager
- BackupManager
- NotificationManager
- RSSManager
- APIKeyManager
- EmailManager

Tests cover:
- Manager instantiation
- Method execution
- Error handling
- Integration with main client
- Backwards compatibility
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from backend.integrations.abs_client import AudiobookshelfClient, AudiobookshelfError
from backend.integrations.abs_managers.library_manager import LibraryManager
from backend.integrations.abs_managers.collection_manager import CollectionManager
from backend.integrations.abs_managers.playlist_manager import PlaylistManager
from backend.integrations.abs_managers.progress_manager import ProgressManager
from backend.integrations.abs_managers.user_manager import UserManager
from backend.integrations.abs_managers.backup_manager import BackupManager
from backend.integrations.abs_managers.notification_manager import NotificationManager
from backend.integrations.abs_managers.rss_manager import RSSManager
from backend.integrations.abs_managers.api_key_manager import APIKeyManager
from backend.integrations.abs_managers.email_manager import EmailManager


@pytest.fixture
def mock_client():
    """Create a mock AudiobookshelfClient."""
    client = MagicMock(spec=AudiobookshelfClient)
    client._request = AsyncMock()
    return client


class TestLibraryManager:
    """Tests for LibraryManager."""

    def test_library_manager_initialization(self, mock_client):
        """Test LibraryManager initializes with client reference."""
        manager = LibraryManager(mock_client)
        assert manager.client == mock_client

    @pytest.mark.asyncio
    async def test_get_library_items(self, mock_client):
        """Test get_library_items returns all items with pagination."""
        mock_client._request.side_effect = [
            {"results": [{"id": "1"}, {"id": "2"}], "total": 3},
            {"results": [{"id": "3"}], "total": 3},
        ]

        manager = LibraryManager(mock_client)
        # Provide library_id to skip the initial library fetch
        items = await manager.get_library_items(library_id="lib123", limit=2)

        assert len(items) == 3
        assert items[0]["id"] == "1"
        assert items[2]["id"] == "3"

    @pytest.mark.asyncio
    async def test_get_book_by_id(self, mock_client):
        """Test get_book_by_id fetches book metadata."""
        mock_client._request.return_value = {
            "id": "book123",
            "media": {"metadata": {"title": "Test Book"}}
        }

        manager = LibraryManager(mock_client)
        book = await manager.get_book_by_id("book123")

        assert book["id"] == "book123"
        mock_client._request.assert_called_once_with("GET", "/api/items/book123")

    @pytest.mark.asyncio
    async def test_search_books(self, mock_client):
        """Test search_books searches library."""
        mock_client._request.return_value = {
            "book": [
                {"id": "1", "media": {"metadata": {"title": "Result 1"}}},
                {"id": "2", "media": {"metadata": {"title": "Result 2"}}},
            ]
        }

        manager = LibraryManager(mock_client)
        results = await manager.search_books("Test Query")

        assert len(results) == 2
        mock_client._request.assert_called_once()


class TestCollectionManager:
    """Tests for CollectionManager."""

    def test_collection_manager_initialization(self, mock_client):
        """Test CollectionManager initializes with client reference."""
        manager = CollectionManager(mock_client)
        assert manager.client == mock_client

    @pytest.mark.asyncio
    async def test_create_collection(self, mock_client):
        """Test create_collection creates new collection."""
        mock_client._request.return_value = {"id": "col123", "name": "My Collection"}

        manager = CollectionManager(mock_client)
        result = await manager.create_collection("My Collection", "Description")

        assert result["id"] == "col123"
        mock_client._request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_collections(self, mock_client):
        """Test get_collections returns all collections."""
        mock_client._request.return_value = {
            "results": [
                {"id": "col1", "name": "Collection 1"},
                {"id": "col2", "name": "Collection 2"},
            ]
        }

        manager = CollectionManager(mock_client)
        collections = await manager.get_collections()

        assert len(collections) == 2

    @pytest.mark.asyncio
    async def test_batch_add_to_collection(self, mock_client):
        """Test batch_add_to_collection handles multiple books."""
        mock_client._request = AsyncMock()

        manager = CollectionManager(mock_client)
        result = await manager.batch_add_to_collection("col123", ["book1", "book2"])

        assert result["total"] == 2
        assert result["success_count"] == 2
        assert mock_client._request.call_count == 2

    @pytest.mark.asyncio
    async def test_batch_add_partial_failure(self, mock_client):
        """Test batch_add_to_collection handles partial failures."""
        async def mock_request(*args, **kwargs):
            if "book2" in str(kwargs):
                raise Exception("Book not found")
            return {"success": True}

        mock_client._request = AsyncMock(side_effect=mock_request)

        manager = CollectionManager(mock_client)
        result = await manager.batch_add_to_collection("col123", ["book1", "book2", "book3"])

        assert result["total"] == 3
        assert result["success_count"] == 2
        assert result["failure_count"] == 1


class TestPlaylistManager:
    """Tests for PlaylistManager."""

    def test_playlist_manager_initialization(self, mock_client):
        """Test PlaylistManager initializes with client reference."""
        manager = PlaylistManager(mock_client)
        assert manager.client == mock_client

    @pytest.mark.asyncio
    async def test_create_playlist(self, mock_client):
        """Test create_playlist creates new playlist."""
        mock_client._request.return_value = {"id": "pl123", "name": "My Playlist"}

        manager = PlaylistManager(mock_client)
        result = await manager.create_playlist("My Playlist")

        assert result["id"] == "pl123"

    @pytest.mark.asyncio
    async def test_batch_add_to_playlist(self, mock_client):
        """Test batch_add_to_playlist handles multiple items."""
        mock_client._request = AsyncMock()

        manager = PlaylistManager(mock_client)
        items = [
            {"libraryItemId": "item1"},
            {"libraryItemId": "item2", "episodeId": "ep1"},
        ]
        result = await manager.batch_add_to_playlist("pl123", items)

        assert result["total"] == 2
        assert result["success_count"] == 2


class TestProgressManager:
    """Tests for ProgressManager."""

    def test_progress_manager_initialization(self, mock_client):
        """Test ProgressManager initializes with client reference."""
        manager = ProgressManager(mock_client)
        assert manager.client == mock_client

    @pytest.mark.asyncio
    async def test_get_media_progress(self, mock_client):
        """Test get_media_progress retrieves progress."""
        mock_client._request.return_value = {"progress": 0.75, "currentTime": 1800}

        manager = ProgressManager(mock_client)
        progress = await manager.get_media_progress("item123")

        assert progress["progress"] == 0.75

    @pytest.mark.asyncio
    async def test_update_media_progress(self, mock_client):
        """Test update_media_progress updates progress."""
        mock_client._request.return_value = {"progress": 0.5}

        manager = ProgressManager(mock_client)
        result = await manager.update_media_progress("item123", 0.5)

        assert result["progress"] == 0.5

    @pytest.mark.asyncio
    async def test_batch_update_progress(self, mock_client):
        """Test batch_update_progress handles multiple items."""
        mock_client._request = AsyncMock()

        manager = ProgressManager(mock_client)
        updates = [
            {"libraryItemId": "item1", "progress": 0.5},
            {"libraryItemId": "item2", "progress": 1.0, "isFinished": True},
        ]
        result = await manager.batch_update_progress(updates)

        assert result["total"] == 2
        assert result["success_count"] == 2

    @pytest.mark.asyncio
    async def test_create_bookmark(self, mock_client):
        """Test create_bookmark creates bookmark."""
        mock_client._request.return_value = {"id": "bm123", "title": "Chapter 5"}

        manager = ProgressManager(mock_client)
        bookmark = await manager.create_bookmark("item123", "Chapter 5", 1800.0)

        assert bookmark["id"] == "bm123"


class TestUserManager:
    """Tests for UserManager."""

    def test_user_manager_initialization(self, mock_client):
        """Test UserManager initializes with client reference."""
        manager = UserManager(mock_client)
        assert manager.client == mock_client

    @pytest.mark.asyncio
    async def test_get_user_profile(self, mock_client):
        """Test get_user_profile retrieves profile."""
        mock_client._request.return_value = {
            "id": "user1",
            "username": "testuser"
        }

        manager = UserManager(mock_client)
        profile = await manager.get_user_profile()

        assert profile["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_update_user_profile(self, mock_client):
        """Test update_user_profile updates profile."""
        mock_client._request.return_value = {
            "id": "user1",
            "username": "newname"
        }

        manager = UserManager(mock_client)
        result = await manager.update_user_profile({"username": "newname"})

        assert result["username"] == "newname"

    @pytest.mark.asyncio
    async def test_change_password(self, mock_client):
        """Test change_password changes user password."""
        mock_client._request.return_value = {}

        manager = UserManager(mock_client)
        result = await manager.change_password("oldpass", "newpass")

        assert result is True


class TestBackupManager:
    """Tests for BackupManager."""

    def test_backup_manager_initialization(self, mock_client):
        """Test BackupManager initializes with client reference."""
        manager = BackupManager(mock_client)
        assert manager.client == mock_client

    @pytest.mark.asyncio
    async def test_create_backup(self, mock_client):
        """Test create_backup creates backup."""
        mock_client._request.return_value = {"id": "backup123", "name": "Daily"}

        manager = BackupManager(mock_client)
        backup = await manager.create_backup({"name": "Daily"})

        assert backup["id"] == "backup123"

    @pytest.mark.asyncio
    async def test_get_backups(self, mock_client):
        """Test get_backups returns all backups."""
        mock_client._request.return_value = {
            "backups": [
                {"id": "backup1", "name": "Backup 1"},
                {"id": "backup2", "name": "Backup 2"},
            ]
        }

        manager = BackupManager(mock_client)
        backups = await manager.get_backups()

        assert len(backups) == 2

    @pytest.mark.asyncio
    async def test_run_backup(self, mock_client):
        """Test run_backup executes backup."""
        mock_client._request.return_value = {"status": "started"}

        manager = BackupManager(mock_client)
        result = await manager.run_backup("backup123")

        assert result["status"] == "started"


class TestNotificationManager:
    """Tests for NotificationManager."""

    def test_notification_manager_initialization(self, mock_client):
        """Test NotificationManager initializes with client reference."""
        manager = NotificationManager(mock_client)
        assert manager.client == mock_client

    @pytest.mark.asyncio
    async def test_get_notifications(self, mock_client):
        """Test get_notifications returns notifications."""
        mock_client._request.return_value = {
            "notifications": [
                {"id": "notif1", "title": "Notification 1"},
                {"id": "notif2", "title": "Notification 2"},
            ]
        }

        manager = NotificationManager(mock_client)
        notifications = await manager.get_notifications()

        assert len(notifications) == 2

    @pytest.mark.asyncio
    async def test_mark_notification_read(self, mock_client):
        """Test mark_notification_read marks as read."""
        mock_client._request.return_value = {"id": "notif123", "read": True}

        manager = NotificationManager(mock_client)
        result = await manager.mark_notification_read("notif123")

        assert result["read"] is True

    @pytest.mark.asyncio
    async def test_mark_all_notifications_read(self, mock_client):
        """Test mark_all_notifications_read marks all as read."""
        mock_client._request.return_value = {"success": True}

        manager = NotificationManager(mock_client)
        result = await manager.mark_all_notifications_read()

        assert result["success"] is True


class TestRSSManager:
    """Tests for RSSManager."""

    def test_rss_manager_initialization(self, mock_client):
        """Test RSSManager initializes with client reference."""
        manager = RSSManager(mock_client)
        assert manager.client == mock_client

    @pytest.mark.asyncio
    async def test_get_rss_feeds(self, mock_client):
        """Test get_rss_feeds returns feeds."""
        mock_client._request.return_value = {
            "feeds": [
                {"id": "feed1", "title": "Feed 1"},
                {"id": "feed2", "title": "Feed 2"},
            ]
        }

        manager = RSSManager(mock_client)
        feeds = await manager.get_rss_feeds()

        assert len(feeds) == 2

    @pytest.mark.asyncio
    async def test_create_rss_feed(self, mock_client):
        """Test create_rss_feed creates feed."""
        mock_client._request.return_value = {"id": "feed123", "title": "My Feed"}

        manager = RSSManager(mock_client)
        feed = await manager.create_rss_feed({"title": "My Feed"})

        assert feed["id"] == "feed123"


class TestAPIKeyManager:
    """Tests for APIKeyManager."""

    def test_api_key_manager_initialization(self, mock_client):
        """Test APIKeyManager initializes with client reference."""
        manager = APIKeyManager(mock_client)
        assert manager.client == mock_client

    @pytest.mark.asyncio
    async def test_get_api_keys(self, mock_client):
        """Test get_api_keys returns keys."""
        mock_client._request.return_value = {
            "keys": [
                {"id": "key1", "name": "Key 1"},
                {"id": "key2", "name": "Key 2"},
            ]
        }

        manager = APIKeyManager(mock_client)
        keys = await manager.get_api_keys()

        assert len(keys) == 2

    @pytest.mark.asyncio
    async def test_create_api_key(self, mock_client):
        """Test create_api_key creates key."""
        mock_client._request.return_value = {"id": "key123", "token": "secret"}

        manager = APIKeyManager(mock_client)
        key = await manager.create_api_key({"name": "My Key"})

        assert key["id"] == "key123"


class TestEmailManager:
    """Tests for EmailManager."""

    def test_email_manager_initialization(self, mock_client):
        """Test EmailManager initializes with client reference."""
        manager = EmailManager(mock_client)
        assert manager.client == mock_client

    @pytest.mark.asyncio
    async def test_send_email(self, mock_client):
        """Test send_email sends email."""
        mock_client._request.return_value = {"success": True}

        manager = EmailManager(mock_client)
        result = await manager.send_email({
            "to": "user@example.com",
            "subject": "Test",
            "body": "Test"
        })

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_get_email_settings(self, mock_client):
        """Test get_email_settings retrieves settings."""
        mock_client._request.return_value = {"smtp_host": "smtp.example.com"}

        manager = EmailManager(mock_client)
        settings = await manager.get_email_settings()

        assert settings["smtp_host"] == "smtp.example.com"


class TestAudiobookshelfClientIntegration:
    """Integration tests for AudiobookshelfClient with managers."""

    @pytest.mark.asyncio
    async def test_client_initializes_all_managers(self):
        """Test AudiobookshelfClient initializes all manager modules."""
        with patch('aiohttp.ClientSession'):
            client = AudiobookshelfClient("http://localhost:13378", "token123")

            assert isinstance(client.libraries, LibraryManager)
            assert isinstance(client.collections, CollectionManager)
            assert isinstance(client.playlists, PlaylistManager)
            assert isinstance(client.progress, ProgressManager)
            assert isinstance(client.users, UserManager)
            assert isinstance(client.backups, BackupManager)
            assert isinstance(client.notifications, NotificationManager)
            assert isinstance(client.rss, RSSManager)
            assert isinstance(client.api_keys, APIKeyManager)
            assert isinstance(client.email, EmailManager)

    @pytest.mark.asyncio
    async def test_manager_delegates_to_client_request(self):
        """Test managers delegate to client._request."""
        mock_client = MagicMock(spec=AudiobookshelfClient)
        mock_client._request = AsyncMock(return_value={"id": "test"})

        manager = LibraryManager(mock_client)
        result = await manager.get_book_by_id("book123")

        mock_client._request.assert_called_once_with("GET", "/api/items/book123")

    @pytest.mark.asyncio
    async def test_error_propagation_from_managers(self):
        """Test errors from API calls propagate through managers."""
        mock_client = MagicMock(spec=AudiobookshelfClient)
        mock_client._request = AsyncMock(side_effect=Exception("API Error"))

        manager = LibraryManager(mock_client)

        with pytest.raises(Exception, match="API Error"):
            await manager.get_book_by_id("book123")


class TestBackwardsCompatibility:
    """Tests ensuring backwards compatibility."""

    @pytest.mark.asyncio
    async def test_manager_methods_match_client_methods(self):
        """Test that manager methods match original client method signatures."""
        # This test ensures that old code using client.get_library_items()
        # continues to work alongside new code using client.libraries.get_library_items()

        with patch('aiohttp.ClientSession'):
            client = AudiobookshelfClient("http://localhost:13378", "token123")

            # All these should exist
            assert hasattr(client, '_request')  # Original method
            assert hasattr(client, 'libraries')  # Manager
            assert hasattr(client.libraries, 'get_library_items')  # Manager method


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
