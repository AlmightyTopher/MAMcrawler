"""
Audiobookshelf RSS Feed Management

Manages RSS feed creation, updates, and deletion.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class RSSManager:
    """
    Manager for Audiobookshelf RSS feed operations.

    Encapsulates all RSS feed-related operations including:
    - RSS feed creation and deletion
    - RSS feed retrieval and updates

    Args:
        client: Reference to AudiobookshelfClient for making requests
    """

    def __init__(self, client):
        """Initialize RSS manager with client reference."""
        self.client = client

    async def create_rss_feed(self, feed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new RSS feed.

        Args:
            feed_data: RSS feed configuration data

        Returns:
            Created RSS feed data

        Example:
            >>> feed = await client.rss.create_rss_feed({
            ...     "title": "My Feed",
            ...     "url": "https://example.com/feed.xml"
            ... })
        """
        logger.info("Creating RSS feed")

        try:
            result = await self.client._request("POST", "/api/feeds", json=feed_data)
            logger.info("Successfully created RSS feed")
            return result
        except Exception as e:
            logger.error(f"Failed to create RSS feed: {str(e)}")
            raise

    async def get_rss_feeds(self) -> List[Dict[str, Any]]:
        """
        Get all RSS feeds.

        Returns:
            List of RSS feed data

        Example:
            >>> feeds = await client.rss.get_rss_feeds()
            >>> print(f"Found {len(feeds)} RSS feeds")
        """
        logger.info("Getting RSS feeds")

        try:
            response = await self.client._request("GET", "/api/feeds")
            feeds = response.get("feeds", [])
            logger.info(f"Found {len(feeds)} RSS feeds")
            return feeds
        except Exception as e:
            logger.error(f"Failed to get RSS feeds: {str(e)}")
            raise

    async def update_rss_feed(self, feed_id: str, feed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an RSS feed.

        Args:
            feed_id: RSS feed ID
            feed_data: Updated feed data

        Returns:
            Updated RSS feed data

        Example:
            >>> await client.rss.update_rss_feed("feed123", {"title": "New Title"})
        """
        logger.info(f"Updating RSS feed: {feed_id}")

        try:
            result = await self.client._request("PATCH", f"/api/feeds/{feed_id}", json=feed_data)
            logger.info(f"Successfully updated RSS feed {feed_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to update RSS feed {feed_id}: {str(e)}")
            raise

    async def delete_rss_feed(self, feed_id: str) -> bool:
        """
        Delete an RSS feed.

        Args:
            feed_id: RSS feed ID to delete

        Returns:
            True if successful

        Example:
            >>> await client.rss.delete_rss_feed("feed123")
        """
        logger.info(f"Deleting RSS feed: {feed_id}")

        try:
            await self.client._request("DELETE", f"/api/feeds/{feed_id}")
            logger.info(f"Successfully deleted RSS feed {feed_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete RSS feed {feed_id}: {str(e)}")
            raise
