"""
Tests for Audiobookshelf API Client

Comprehensive test suite for all Audiobookshelf client methods including
new RSS and bandwidth management features.
"""

import pytest
import asyncio
from backend.integrations.qbittorrent_client import QBittorrentClient, QBittorrentError
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import ClientError, ClientResponseError

from backend.integrations.abs_client import AudiobookshelfClient, AudiobookshelfError


class TestAudiobookshelfClient:
    """Test suite for AudiobookshelfClient."""

    @pytest.fixture
    def client(self):
        """Create test client instance."""
        return AudiobookshelfClient(
            base_url="http://localhost:13378",
            api_token="test-token"
        )

    @pytest.fixture
    def mock_session(self):
        """Mock aiohttp ClientSession."""
        session = AsyncMock()
        response = AsyncMock()
        response.raise_for_status = MagicMock()
        response.json = AsyncMock(return_value={"test": "data"})
        response.text = AsyncMock(return_value="Ok.")
        session.request.return_value.__aenter__.return_value = response
        return session

    @pytest.mark.asyncio
    async def test_initialization(self, client):
        """Test client initialization."""
        assert client.base_url == "http://localhost:13378"
        assert client.api_token == "test-token"
        assert client.timeout.total == 30

    @pytest.mark.asyncio
    async def test_context_manager(self, client, mock_session):
        """Test async context manager."""
        with patch('aiohttp.ClientSession', return_value=mock_session):
            async with client:
                assert client.session is not None
            # Session should be closed
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_library_items_pagination(self, client, mock_session):
        """Test library items pagination."""
        # Mock responses for pagination
        responses = [
            {"results": [{"id": "1", "title": "Book 1"}, {"id": "2", "title": "Book 2"}], "total": 5},
            {"results": [{"id": "3", "title": "Book 3"}, {"id": "4", "title": "Book 4"}], "total": 5},
            {"results": [{"id": "5", "title": "Book 5"}], "total": 5},
        ]

        mock_session.request.return_value.__aenter__.side_effect = [
            AsyncMock(json=AsyncMock(return_value=resp), raise_for_status=MagicMock())
            for resp in responses
        ]

        with patch('aiohttp.ClientSession', return_value=mock_session):
            async with client:
                items = await client.get_library_items(limit=2)

        assert len(items) == 5
        assert items[0]["title"] == "Book 1"
        assert items[4]["title"] == "Book 5"

    @pytest.mark.asyncio
    async def test_get_book_by_id(self, client, mock_session):
        """Test getting single book by ID."""
        book_data = {
            "id": "test123",
            "media": {"metadata": {"title": "Test Book"}}
        }

        mock_session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value=book_data)
        mock_session.request.return_value.__aenter__.return_value.raise_for_status = MagicMock()

        with patch('aiohttp.ClientSession', return_value=mock_session):
            async with client:
                result = await client.get_book_by_id("test123")

        assert result["id"] == "test123"
        assert result["media"]["metadata"]["title"] == "Test Book"

    @pytest.mark.asyncio
    async def test_update_book_metadata(self, client, mock_session):
        """Test updating book metadata."""
        mock_session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value={"success": True})

        with patch('aiohttp.ClientSession', return_value=mock_session):
            async with client:
                result = await client.update_book_metadata("book123", {"title": "New Title"})

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_rss_feed_management(self, client, mock_session):
        """Test RSS feed management methods."""
        # Test add RSS feed
        mock_session.request.return_value.__aenter__.return_value.text = AsyncMock(return_value="Ok.")

        with patch('aiohttp.ClientSession', return_value=mock_session):
            async with client:
                # Test add feed
                result = await client.add_rss_feed("https://example.com/rss.xml", "audiobooks")
                assert result is True

                # Test get RSS items
                mock_session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value={
                    "audiobooks": {"feed1": {"title": "Test Feed"}}
                })
                items = await client.get_rss_items()
                assert "audiobooks" in items

                # Test remove RSS item
                result = await client.remove_rss_item("audiobooks/feed1")
                assert result is True

    @pytest.mark.asyncio
    async def test_rss_rules_management(self, client, mock_session):
        """Test RSS rules management."""
        with patch('aiohttp.ClientSession', return_value=mock_session):
            async with client:
                # Test set RSS rule
                rule_def = {
                    "enabled": True,
                    "mustContain": "audiobook",
                    "assignedCategory": "audiobooks"
                }
                result = await client.set_rss_rule("audiobook_rule", rule_def)
                assert result is True

                # Test get RSS rules
                mock_session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value={
                    "audiobook_rule": rule_def
                })
                rules = await client.get_rss_rules()
                assert "audiobook_rule" in rules

                # Test remove RSS rule
                result = await client.remove_rss_rule("audiobook_rule")
                assert result is True

    @pytest.mark.asyncio
    async def test_bandwidth_management(self, client, mock_session):
        """Test bandwidth management methods."""
        with patch('aiohttp.ClientSession', return_value=mock_session):
            async with client:
                # Test set global download limit
                result = await client.set_global_download_limit(1024000)
                assert result is True

                # Test get global download limit
                mock_session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value="1024000")
                limit = await client.get_global_download_limit()
                assert limit == 1024000

                # Test set torrent download limit
                result = await client.set_torrent_download_limit("hash123", 512000)
                assert result is True

    @pytest.mark.asyncio
    async def test_error_handling(self, client, mock_session):
        """Test error handling."""
        # Mock a client error
        mock_session.request.side_effect = ClientError("Connection failed")

        with patch('aiohttp.ClientSession', return_value=mock_session):
            async with client:
                with pytest.raises(AudiobookshelfError):
                    await client.get_library_items()

    @pytest.mark.asyncio
    async def test_retry_logic(self, client, mock_session):
        """Test retry logic on failures."""
        # Mock authentication failure followed by success
        responses = [
            AsyncMock(status=403, raise_for_status=MagicMock(side_effect=ClientResponseError(None, None, status=403))),
            AsyncMock(json=AsyncMock(return_value={"results": [], "total": 0}))
        ]

        mock_session.request.return_value.__aenter__.side_effect = responses

        with patch('aiohttp.ClientSession', return_value=mock_session):
            async with client:
                # Should retry after auth failure
                result = await client.get_library_items()
                assert result == []

    @pytest.mark.asyncio
    async def test_collection_management(self, client, mock_session):
        """Test collection management methods."""
        with patch('aiohttp.ClientSession', return_value=mock_session):
            async with client:
                # Test create collection
                result = await client.create_collection("My Collection", "Test collection")
                assert result is True

                # Test get collections
                mock_session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value={
                    "results": [{"id": "col1", "name": "My Collection"}]
                })
                collections = await client.get_collections()
                assert len(collections) == 1

                # Test add book to collection
                result = await client.add_book_to_collection("col1", "book1")
                assert result is True

    @pytest.mark.asyncio
    async def test_playlist_management(self, client, mock_session):
        """Test playlist management methods."""
        with patch('aiohttp.ClientSession', return_value=mock_session):
            async with client:
                # Test create playlist
                result = await client.create_playlist("My Playlist", "Test playlist")
                assert result is True

                # Test get playlists
                mock_session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value={
                    "results": [{"id": "pl1", "name": "My Playlist"}]
                })
                playlists = await client.get_playlists()
                assert len(playlists) == 1

                # Test add item to playlist
                result = await client.add_item_to_playlist("pl1", "item1")
                assert result is True

    @pytest.mark.asyncio
    async def test_progress_tracking(self, client, mock_session):
        """Test progress tracking methods."""
        with patch('aiohttp.ClientSession', return_value=mock_session):
            async with client:
                # Test get media progress
                mock_session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value={
                    "progress": 0.75, "currentTime": 1800
                })
                progress = await client.get_media_progress("item1")
                assert progress["progress"] == 0.75

                # Test update media progress
                result = await client.update_media_progress("item1", 0.8, 2000)
                assert result is True

                # Test create bookmark
                result = await client.create_bookmark("item1", "Chapter 5", 1800.0)
                assert result is True

    @pytest.mark.asyncio
    async def test_user_management(self, client, mock_session):
        """Test user management methods."""
        with patch('aiohttp.ClientSession', return_value=mock_session):
            async with client:
                # Test get user profile
                mock_session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value={
                    "username": "testuser", "id": "user1"
                })
                profile = await client.get_user_profile()
                assert profile["username"] == "testuser"

                # Test update user profile
                result = await client.update_user_profile({"username": "newuser"})
                assert result is True

                # Test get user stats
                mock_session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value={
                    "booksCompleted": 42, "totalListeningTime": 86400
                })
                stats = await client.get_user_stats()
                assert stats["booksCompleted"] == 42

    @pytest.mark.asyncio
    async def test_backup_management(self, client, mock_session):
        """Test backup management methods."""
        with patch('aiohttp.ClientSession', return_value=mock_session):
            async with client:
                # Test create backup
                result = await client.create_backup({"name": "Test Backup"})
                assert result is True

                # Test get backups
                mock_session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value={
                    "backups": [{"id": "backup1", "name": "Test Backup"}]
                })
                backups = await client.get_backups()
                assert len(backups) == 1

                # Test run backup
                result = await client.run_backup("backup1")
                assert result is True

    @pytest.mark.asyncio
    async def test_notification_management(self, client, mock_session):
        """Test notification management methods."""
        with patch('aiohttp.ClientSession', return_value=mock_session):
            async with client:
                # Test create notification
                result = await client.create_notification({
                    "title": "Test",
                    "message": "Test message",
                    "type": "info"
                })
                assert result is True

                # Test get notifications
                mock_session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value={
                    "notifications": [{"id": "notif1", "title": "Test"}]
                })
                notifications = await client.get_notifications()
                assert len(notifications) == 1

                # Test mark as read
                result = await client.mark_notification_read("notif1")
                assert result is True

    @pytest.mark.asyncio
    async def test_email_management(self, client, mock_session):
        """Test email management methods."""
        with patch('aiohttp.ClientSession', return_value=mock_session):
            async with client:
                # Test send email
                result = await client.send_email({
                    "to": "test@example.com",
                    "subject": "Test",
                    "body": "Test body"
                })
                assert result is True

                # Test get email settings
                mock_session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value={
                    "smtp_host": "smtp.example.com"
                })
                settings = await client.get_email_settings()
                assert settings["smtp_host"] == "smtp.example.com"

                # Test test email settings
                result = await client.test_email_settings()
                assert result is True


class TestQBittorrentClient:
    """Test suite for QBittorrentClient RSS and bandwidth features."""

    @pytest.fixture
    def qb_client(self):
        """Create test qBittorrent client instance."""
        return QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="password"
        )

    @pytest.fixture
    def mock_qb_session(self):
        """Mock aiohttp ClientSession for qBittorrent."""
        session = AsyncMock()
        response = AsyncMock()
        response.raise_for_status = MagicMock()
        response.json = AsyncMock(return_value={})
        response.text = AsyncMock(return_value="Ok.")
        session.request.return_value.__aenter__.return_value = response
        session.post.return_value.__aenter__.return_value = response
        return session

    @pytest.mark.asyncio
    async def test_rss_feed_operations(self, qb_client, mock_qb_session):
        """Test RSS feed operations."""
        with patch('aiohttp.ClientSession', return_value=mock_qb_session):
            async with qb_client:
                # Test add RSS feed
                result = await qb_client.add_rss_feed("https://example.com/rss.xml", "audiobooks")
                assert result is True

                # Test get RSS items
                mock_qb_session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value={
                    "audiobooks": {"feed1": {"title": "Test Feed"}}
                })
                items = await qb_client.get_rss_items()
                assert "audiobooks" in items

                # Test remove RSS item
                result = await qb_client.remove_rss_item("audiobooks/feed1")
                assert result is True

                # Test move RSS item
                result = await qb_client.move_rss_item("feed1", "audiobooks/feed1")
                assert result is True

                # Test refresh RSS item
                result = await qb_client.refresh_rss_item("audiobooks/feed1")
                assert result is True

    @pytest.mark.asyncio
    async def test_rss_rules_operations(self, qb_client, mock_qb_session):
        """Test RSS rules operations."""
        with patch('aiohttp.ClientSession', return_value=mock_qb_session):
            async with qb_client:
                # Test set RSS rule
                rule_def = {
                    "enabled": True,
                    "mustContain": "audiobook",
                    "assignedCategory": "audiobooks"
                }
                result = await qb_client.set_rss_rule("audiobook_rule", rule_def)
                assert result is True

                # Test get RSS rules
                mock_qb_session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value={
                    "audiobook_rule": rule_def
                })
                rules = await qb_client.get_rss_rules()
                assert "audiobook_rule" in rules

                # Test get matching articles
                mock_qb_session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value=[
                    {"title": "Audiobook 1", "id": "art1"}
                ])
                articles = await qb_client.get_rss_matching_articles("audiobook_rule")
                assert len(articles) == 1

                # Test mark article as read
                result = await qb_client.mark_rss_article_as_read("audiobooks/feed1", "art1")
                assert result is True

                # Test remove RSS rule
                result = await qb_client.remove_rss_rule("audiobook_rule")
                assert result is True

    @pytest.mark.asyncio
    async def test_bandwidth_operations(self, qb_client, mock_qb_session):
        """Test bandwidth control operations."""
        with patch('aiohttp.ClientSession', return_value=mock_qb_session):
            async with qb_client:
                # Test set global download limit
                result = await qb_client.set_global_download_limit(1024000)
                assert result is True

                # Test get global download limit
                mock_qb_session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value="1024000")
                limit = await qb_client.get_global_download_limit()
                assert limit == 1024000

                # Test set global upload limit
                result = await qb_client.set_global_upload_limit(512000)
                assert result is True

                # Test get global upload limit
                mock_qb_session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value="512000")
                limit = await qb_client.get_global_upload_limit()
                assert limit == 512000

                # Test set torrent download limit
                result = await qb_client.set_torrent_download_limit("hash123", 256000)
                assert result is True

                # Test get torrent download limit
                mock_qb_session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value={
                    "hash123": "256000"
                })
                limit = await qb_client.get_torrent_download_limit("hash123")
                assert limit == 256000

                # Test set alternative speed limits
                result = await qb_client.set_alternative_speed_limits(512000, 256000)
                assert result is True

                # Test get bandwidth usage stats
                mock_qb_session.request.return_value.__aenter__.return_value.json = AsyncMock(side_effect=[
                    {"dl_info_speed": 1024000, "up_info_speed": 512000},  # transfer info
                    [{"hash": "t1", "dlspeed": 512000, "upspeed": 256000, "downloaded": 1000000, "uploaded": 500000, "state": "downloading"}]  # torrents
                ])
                stats = await qb_client.get_bandwidth_usage_stats()
                assert stats["server_dl_speed"] == 1024000
                assert stats["total_torrent_dl_speed"] == 512000

    @pytest.mark.asyncio
    async def test_rss_feeds_status(self, qb_client, mock_qb_session):
        """Test RSS feeds status retrieval."""
        with patch('aiohttp.ClientSession', return_value=mock_qb_session):
            async with qb_client:
                mock_qb_session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value={
                    "audiobooks": {
                        "feed1": {
                            "url": "https://example.com/rss.xml",
                            "lastBuildDate": "2023-12-01",
                            "title": "Audiobooks RSS"
                        }
                    }
                })
                status = await qb_client.get_rss_feeds_status()
                assert status["total_feeds"] == 1
                assert status["total_folders"] == 1
                assert "audiobooks/feed1" in status["feeds_by_status"]


if __name__ == "__main__":
    pytest.main([__file__])