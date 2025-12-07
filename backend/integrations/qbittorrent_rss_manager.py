"""
qBittorrent RSS Feed Management

Manages RSS feeds, rules, and article processing for qBittorrent.
"""

import logging
from typing import Any, Dict, List, Optional
from aiohttp import FormData

logger = logging.getLogger(__name__)


class QBittorrentRSSManager:
    """
    Manager for qBittorrent RSS operations.

    Encapsulates all RSS-related operations including:
    - Feed management (add, remove, refresh)
    - RSS rules (create, update, remove)
    - Article processing
    - Folder management

    Args:
        client: Reference to QBittorrentClient for making requests
    """

    def __init__(self, client):
        """Initialize RSS manager with client reference."""
        self.client = client

    async def add_rss_feed(
        self,
        url: str,
        cookie_filter: Optional[str] = None
    ) -> bool:
        """
        Add RSS feed to qBittorrent.

        Args:
            url: RSS feed URL
            cookie_filter: Optional cookie filter string

        Returns:
            True if successful

        Raises:
            QBittorrentError: On API errors
        """
        data = FormData()
        data.add_field("url", url)
        if cookie_filter:
            data.add_field("cookie", cookie_filter)

        logger.info(f"Adding RSS feed: {url}")
        await self.client._request("POST", "/api/v2/rss/addFeed", data=data)
        return True

    async def get_rss_items(
        self,
        with_data: bool = False
    ) -> Dict[str, Any]:
        """
        Get RSS items.

        Args:
            with_data: If True, include article data

        Returns:
            Dict of RSS items

        Raises:
            QBittorrentError: On API errors
        """
        params = {"withData": "true" if with_data else "false"}

        logger.debug("Fetching RSS items")
        response = await self.client._request(
            "GET",
            "/api/v2/rss/items",
            params=params
        )
        return response

    async def remove_rss_item(self, path: str) -> bool:
        """
        Remove RSS feed or folder.

        Args:
            path: RSS feed/folder path

        Returns:
            True if successful

        Raises:
            QBittorrentError: On API errors
        """
        data = FormData()
        data.add_field("itemPath", path)

        logger.info(f"Removing RSS item: {path}")
        await self.client._request("POST", "/api/v2/rss/removeItem", data=data)
        return True

    async def move_rss_item(self, item_path: str, dest_path: str) -> bool:
        """
        Move RSS item to new folder.

        Args:
            item_path: Current RSS item path
            dest_path: Destination folder path

        Returns:
            True if successful

        Raises:
            QBittorrentError: On API errors
        """
        data = FormData()
        data.add_field("itemPath", item_path)
        data.add_field("destPath", dest_path)

        logger.info(f"Moving RSS item from {item_path} to {dest_path}")
        await self.client._request("POST", "/api/v2/rss/moveItem", data=data)
        return True

    async def refresh_rss_item(self, item_path: str) -> bool:
        """
        Refresh RSS feed or folder.

        Args:
            item_path: RSS feed/folder path

        Returns:
            True if successful

        Raises:
            QBittorrentError: On API errors
        """
        data = FormData()
        data.add_field("itemPath", item_path)

        logger.info(f"Refreshing RSS item: {item_path}")
        await self.client._request("POST", "/api/v2/rss/refreshItem", data=data)
        return True

    async def set_rss_rule(self, rule_name: str, rule_config: Dict[str, Any]) -> bool:
        """
        Create or update RSS rule.

        Args:
            rule_name: Rule name
            rule_config: Rule configuration dict

        Returns:
            True if successful

        Raises:
            QBittorrentError: On API errors
        """
        data = FormData()
        data.add_field("ruleName", rule_name)
        data.add_field("ruleDef", str(rule_config))  # Convert dict to string

        logger.info(f"Setting RSS rule: {rule_name}")
        await self.client._request("POST", "/api/v2/rss/setRule", data=data)
        return True

    async def get_rss_rules(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all RSS rules.

        Returns:
            Dict of RSS rules

        Raises:
            QBittorrentError: On API errors
        """
        logger.debug("Fetching RSS rules")
        response = await self.client._request("GET", "/api/v2/rss/rules")
        return response

    async def remove_rss_rule(self, rule_name: str) -> bool:
        """
        Remove RSS rule.

        Args:
            rule_name: Rule name

        Returns:
            True if successful

        Raises:
            QBittorrentError: On API errors
        """
        data = FormData()
        data.add_field("ruleName", rule_name)

        logger.info(f"Removing RSS rule: {rule_name}")
        await self.client._request("POST", "/api/v2/rss/removeRule", data=data)
        return True

    async def get_rss_matching_articles(
        self,
        rule_name: str
    ) -> List[Dict[str, Any]]:
        """
        Get articles matching RSS rule.

        Args:
            rule_name: Rule name

        Returns:
            List of matching articles

        Raises:
            QBittorrentError: On API errors
        """
        params = {"ruleName": rule_name}

        logger.debug(f"Fetching articles matching rule: {rule_name}")
        response = await self.client._request(
            "GET",
            "/api/v2/rss/matchingArticles",
            params=params
        )
        return response

    async def mark_rss_article_as_read(
        self,
        item_path: str,
        article_id: str
    ) -> bool:
        """
        Mark RSS article as read.

        Args:
            item_path: RSS feed path
            article_id: Article ID

        Returns:
            True if successful

        Raises:
            QBittorrentError: On API errors
        """
        data = FormData()
        data.add_field("itemPath", item_path)
        data.add_field("articleId", article_id)

        logger.debug(f"Marking article {article_id} as read in {item_path}")
        await self.client._request(
            "POST",
            "/api/v2/rss/markAsRead",
            data=data
        )
        return True

    async def create_rss_folder(self, path: str) -> bool:
        """
        Create RSS folder.

        Args:
            path: Folder path

        Returns:
            True if successful

        Raises:
            QBittorrentError: On API errors
        """
        data = FormData()
        data.add_field("folderPath", path)

        logger.info(f"Creating RSS folder: {path}")
        await self.client._request("POST", "/api/v2/rss/createFolder", data=data)
        return True

    async def get_rss_feeds_status(self) -> Dict[str, Any]:
        """
        Get status of all RSS feeds.

        Returns:
            Dict with RSS feed status information

        Raises:
            QBittorrentError: On API errors
        """
        logger.debug("Fetching RSS feeds status")
        response = await self.client._request("GET", "/api/v2/rss/feedsStatus")
        return response
