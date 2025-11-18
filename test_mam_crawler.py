"""
Unit tests for MAM crawler components.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock, mock_open
from datetime import datetime, timedelta
import json

from mam_crawler import MAMPassiveCrawler, MAMDataProcessor


class TestMAMPassiveCrawler:
    """Test cases for MAMPassiveCrawler class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.crawler = MAMPassiveCrawler(username="test@example.com", password="testpass")

    def test_init_with_credentials(self):
        """Test initialization with provided credentials."""
        assert self.crawler.username == "test@example.com"
        assert self.crawler.password == "testpass"
        assert self.crawler.base_url == "https://www.myanonamouse.net"
        assert "/guides/" in self.crawler.allowed_paths
        assert "/f/" in self.crawler.allowed_paths

    def test_init_with_env_vars(self):
        """Test initialization using environment variables."""
        with patch.dict('os.environ', {'MAM_USERNAME': 'env@example.com', 'MAM_PASSWORD': 'envpass'}):
            crawler = MAMPassiveCrawler()
            assert crawler.username == "env@example.com"
            assert crawler.password == "envpass"

    def test_init_missing_credentials(self):
        """Test initialization failure when credentials are missing."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="MAM credentials not provided"):
                MAMPassiveCrawler()

    def test_is_allowed_path(self):
        """Test URL path validation."""
        # Allowed paths
        assert self.crawler._is_allowed_path("https://www.myanonamouse.net/")
        assert self.crawler._is_allowed_path("https://www.myanonamouse.net/tor/browse.php")
        assert self.crawler._is_allowed_path("https://www.myanonamouse.net/guides/")
        assert self.crawler._is_allowed_path("https://www.myanonamouse.net/f/qbittorrent/")

        # Forbidden paths
        assert not self.crawler._is_allowed_path("https://www.myanonamouse.net/user/profile")
        assert not self.crawler._is_allowed_path("https://www.myanonamouse.net/admin/")
        assert not self.crawler._is_allowed_path("https://example.com/")

    @pytest.mark.asyncio
    @patch('mam_crawler.AsyncWebCrawler')
    async def test_login_success(self, mock_crawler_class):
        """Test successful login."""
        mock_crawler = AsyncMock()
        mock_crawler.arun.return_value = Mock(
            success=True,
            markdown="<html>logout my account</html>",
            cookies={'session': 'test'}
        )
        mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

        result = await self.crawler._login()
        assert result is True
        assert self.crawler.session_cookies == {'session': 'test'}
        assert self.crawler.last_login is not None

    @pytest.mark.asyncio
    @patch('mam_crawler.AsyncWebCrawler')
    async def test_login_failure(self, mock_crawler_class):
        """Test login failure."""
        mock_crawler = AsyncMock()
        mock_crawler.arun.return_value = Mock(
            success=True,
            markdown="<html>login failed</html>",
            cookies={}
        )
        mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

        result = await self.crawler._login()
        assert result is False

    @pytest.mark.asyncio
    @patch('mam_crawler.AsyncWebCrawler')
    @patch.object(MAMPassiveCrawler, '_login', return_value=True)
    async def test_crawl_page_allowed_url(self, mock_login, mock_crawler_class):
        """Test crawling an allowed URL."""
        mock_crawler = AsyncMock()
        mock_crawler.arun.return_value = Mock(
            success=True,
            url="https://www.myanonamouse.net/guides/",
            title="Test Guide",
            markdown="# Test Content"
        )
        mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

        result = await self.crawler.crawl_page("https://www.myanonamouse.net/guides/")

        assert result["success"] is True
        assert result["url"] == "https://www.myanonamouse.net/guides/"
        assert result["title"] == "Test Guide"
        assert "crawled_at" in result

    @pytest.mark.asyncio
    async def test_crawl_page_forbidden_url(self):
        """Test crawling a forbidden URL."""
        result = await self.crawler.crawl_page("https://www.myanonamouse.net/user/profile")

        assert result["success"] is False
        assert "not allowed" in result["error"]

    @pytest.mark.asyncio
    @patch('mam_crawler.AsyncWebCrawler')
    @patch.object(MAMPassiveCrawler, '_login', return_value=True)
    async def test_crawl_guides_section(self, mock_login, mock_crawler_class):
        """Test crawling guides section."""
        mock_crawler = AsyncMock()
        mock_crawler.arun.return_value = Mock(
            success=True,
            url="https://www.myanonamouse.net/guides/",
            title="MAM Guides",
            markdown="# Guide Content"
        )
        mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

        results = await self.crawler.crawl_guides_section()

        assert len(results) == 1
        assert results[0]["success"] is True
        assert "guides" in results[0]["url"]

    @pytest.mark.asyncio
    @patch('mam_crawler.AsyncWebCrawler')
    @patch.object(MAMPassiveCrawler, '_login', return_value=True)
    async def test_crawl_qbittorrent_settings(self, mock_login, mock_crawler_class):
        """Test crawling qBittorrent settings."""
        mock_crawler = AsyncMock()
        mock_crawler.arun.return_value = Mock(
            success=True,
            url="https://www.myanonamouse.net/f/qbittorrent/",
            title="qBittorrent Settings",
            markdown="# Settings Content"
        )
        mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

        results = await self.crawler.crawl_qbittorrent_settings()

        assert len(results) == 1
        assert results[0]["success"] is True
        assert "qbittorrent" in results[0]["url"]


class TestMAMDataProcessor:
    """Test cases for MAMDataProcessor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = MAMDataProcessor()

    def test_validate_data_valid(self):
        """Test validation of valid data."""
        valid_data = {
            "success": True,
            "url": "https://example.com",
            "crawled_at": "2023-01-01T00:00:00"
        }
        assert self.processor.validate_data(valid_data) is True

    def test_validate_data_invalid(self):
        """Test validation of invalid data."""
        invalid_data = {
            "success": False,
            "url": "https://example.com"
            # missing crawled_at
        }
        assert self.processor.validate_data(invalid_data) is False

    def test_process_guides_data(self):
        """Test processing guides data into Markdown."""
        guides_data = [
            {
                "success": True,
                "url": "https://www.myanonamouse.net/guides/test",
                "data": {
                    "title": "Test Guide",
                    "description": "A test guide",
                    "author": "Test Author",
                    "timestamp": "2023-01-01",
                    "content": "This is a comprehensive guide with substantial content that exceeds the minimum character threshold required for inclusion in the output. It contains detailed information and instructions."
                }
            }
        ]

        result = self.processor.process_guides_data(guides_data)

        assert "# MAM Guides" in result
        assert "## Test Guide" in result
        assert "Test Author" in result
        assert "comprehensive guide" in result

    def test_process_qbittorrent_data(self):
        """Test processing qBittorrent data into Markdown."""
        qb_data = [
            {
                "success": True,
                "url": "https://www.myanonamouse.net/f/qbittorrent/",
                "data": {
                    "title": "qBittorrent Settings for MAM",
                    "author": "Forum User",
                    "date": "2023-01-01",
                    "content": "Here are the recommended qBittorrent settings for optimal performance on MAM tracker network.",
                    "settings_code": "[BitTorrent]\nSession\\DefaultSavePath=/downloads"
                }
            }
        ]

        result = self.processor.process_qbittorrent_data(qb_data)

        assert "# qBittorrent Settings" in result
        assert "## qBittorrent Settings for MAM" in result
        assert "/downloads" in result
        assert "optimal performance" in result

    @patch('builtins.open', new_callable=mock_open)
    def test_save_markdown_output(self, mock_file):
        """Test saving Markdown output to file."""
        guides_md = "# Guides\n\n## Guide 1\n\nContent"
        qb_md = "# Settings\n\n## Setting 1\n\nValue"

        self.processor.save_markdown_output(guides_md, qb_md, "test.md")

        mock_file.assert_called_once_with("test.md", 'w', encoding='utf-8')
        # Verify the combined content was written
        handle = mock_file()
        handle.write.assert_called()
        written_content = handle.write.call_args[0][0]
        assert "# Guides" in written_content
        assert "# Settings" in written_content


if __name__ == "__main__":
    pytest.main([__file__])