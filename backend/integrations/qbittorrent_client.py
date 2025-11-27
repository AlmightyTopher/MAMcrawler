"""
qBittorrent API Client

Provides async interface to qBittorrent Web API for managing torrent downloads.
Supports adding torrents, monitoring status, and controlling download queue.
"""

import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
import asyncio
from urllib.parse import urljoin

import aiohttp
from aiohttp import ClientTimeout, ClientError, FormData
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)


class QBittorrentError(Exception):
    """Base exception for qBittorrent client errors."""
    pass


class QBittorrentAuthError(QBittorrentError):
    """Authentication failed."""
    pass


class QBittorrentClient:
    """
    Async client for qBittorrent Web API v2.

    Handles authentication, session management, retries, and error handling
    for all qBittorrent operations.

    Args:
        base_url: qBittorrent Web UI URL (e.g., "http://localhost:8080")
        username: Web UI username
        password: Web UI password
        timeout: Request timeout in seconds (default: 30)

    Example:
        >>> async with QBittorrentClient(url, user, password) as client:
        ...     await client.add_torrent(magnet_link, category="audiobooks")
        ...     torrents = await client.get_all_torrents()
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        timeout: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None
        self._authenticated = False

        logger.info(f"Initialized QBittorrentClient for {self.base_url}")

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        await self._login()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self._logout()
            await self.session.close()

    async def _ensure_session(self):
        """Ensure session is initialized and authenticated."""
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        if not self._authenticated:
            await self._login()

    async def _login(self):
        """
        Authenticate with qBittorrent Web UI.

        Raises:
            QBittorrentAuthError: If authentication fails
        """
        logger.info("Authenticating with qBittorrent")
        url = urljoin(self.base_url, "/api/v2/auth/login")

        data = FormData()
        data.add_field("username", self.username)
        data.add_field("password", self.password)

        try:
            async with self.session.post(url, data=data) as response:
                response.raise_for_status()
                result = await response.text()

                if result.strip() == "Ok.":
                    self._authenticated = True
                    logger.info("Successfully authenticated with qBittorrent")
                else:
                    raise QBittorrentAuthError(f"Authentication failed: {result}")

        except aiohttp.ClientError as e:
            logger.error(f"Authentication request failed: {str(e)}")
            raise QBittorrentAuthError(f"Login request failed: {str(e)}")

    async def _logout(self):
        """Logout from qBittorrent."""
        if not self._authenticated:
            return

        logger.info("Logging out from qBittorrent")
        url = urljoin(self.base_url, "/api/v2/auth/logout")

        try:
            async with self.session.post(url) as response:
                response.raise_for_status()
                self._authenticated = False
                logger.info("Successfully logged out")
        except aiohttp.ClientError as e:
            logger.warning(f"Logout failed: {str(e)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ClientError, asyncio.TimeoutError)),
        reraise=True,
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> Any:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint path
            **kwargs: Additional arguments for aiohttp request

        Returns:
            Response (text or JSON depending on endpoint)

        Raises:
            QBittorrentError: On API errors
        """
        await self._ensure_session()
        url = urljoin(self.base_url, endpoint)

        logger.debug(f"{method} {url}")

        try:
            async with self.session.request(method, url, **kwargs) as response:
                response.raise_for_status()

                # Most qBittorrent endpoints return JSON
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    data = await response.json()
                else:
                    data = await response.text()

                logger.debug(f"Response: {response.status}")
                return data

        except aiohttp.ClientResponseError as e:
            # Check if authentication expired
            if e.status == 403:
                logger.warning("Authentication expired, re-authenticating")
                self._authenticated = False
                await self._login()
                # Retry the request after re-authentication
                return await self._request(method, endpoint, **kwargs)

            logger.error(f"API error: {e.status} - {e.message}")
            raise QBittorrentError(f"API request failed: {e.status} {e.message}")

        except aiohttp.ClientError as e:
            logger.error(f"Client error: {str(e)}")
            raise QBittorrentError(f"Request failed: {str(e)}")

        except asyncio.TimeoutError:
            logger.error(f"Request timeout for {url}")
            raise QBittorrentError("Request timeout")

    async def add_torrent(
        self,
        magnet_link: str,
        category: Optional[str] = None,
        save_path: Optional[str] = None,
        paused: bool = False,
    ) -> Dict[str, Any]:
        """
        Add magnet link to download queue.

        Args:
            magnet_link: Magnet URI
            category: Optional category to assign
            save_path: Optional custom download path
            paused: If True, add torrent in paused state

        Returns:
            Dictionary with success status and torrent hash

        Example:
            >>> result = await client.add_torrent(
            ...     "magnet:?xt=urn:btih:...",
            ...     category="audiobooks"
            ... )
            >>> print(f"Added torrent: {result['hash']}")
        """
        logger.info(f"Adding torrent (category={category}, paused={paused})")
        logger.debug(f"Magnet: {magnet_link[:80]}...")

        endpoint = "/api/v2/torrents/add"

        data = FormData()
        data.add_field("urls", magnet_link)

        if category:
            data.add_field("category", category)
        if save_path:
            data.add_field("savepath", save_path)
        if paused:
            data.add_field("paused", "true")

        try:
            result = await self._request("POST", endpoint, data=data)

            if result.strip() == "Ok.":
                logger.info("Torrent added successfully")
                # Get torrent hash by querying recent torrents
                await asyncio.sleep(1)  # Wait for torrent to appear
                torrents = await self.get_all_torrents()

                # Find most recent torrent matching the magnet link
                # Extract info hash from magnet link
                info_hash = None
                if "btih:" in magnet_link:
                    info_hash = magnet_link.split("btih:")[1].split("&")[0].lower()

                if info_hash:
                    for torrent in torrents:
                        if torrent.get("hash", "").lower() == info_hash:
                            return {"success": True, "hash": torrent["hash"]}

                return {"success": True, "hash": None}
            else:
                logger.error(f"Failed to add torrent: {result}")
                return {"success": False, "error": result}

        except QBittorrentError as e:
            logger.error(f"Failed to add torrent: {str(e)}")
            raise

    async def get_torrent_status(self, torrent_hash: str) -> Dict[str, Any]:
        """
        Get download status and progress for specific torrent.

        Args:
            torrent_hash: Torrent info hash

        Returns:
            Torrent status dictionary with progress, speed, state, etc.

        Example:
            >>> status = await client.get_torrent_status(torrent_hash)
            >>> print(f"Progress: {status['progress']*100:.1f}%")
            >>> print(f"State: {status['state']}")
        """
        logger.debug(f"Getting status for torrent: {torrent_hash}")

        endpoint = "/api/v2/torrents/info"
        params = {"hashes": torrent_hash}

        try:
            torrents = await self._request("GET", endpoint, params=params)

            if not torrents:
                raise QBittorrentError(f"Torrent not found: {torrent_hash}")

            status = torrents[0]
            logger.debug(
                f"Torrent '{status.get('name', 'Unknown')}': "
                f"{status.get('progress', 0)*100:.1f}% - {status.get('state', 'unknown')}"
            )
            return status

        except QBittorrentError as e:
            logger.error(f"Failed to get torrent status: {str(e)}")
            raise

    async def get_all_torrents(
        self,
        filter_state: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get list of all torrents.

        Args:
            filter_state: Optional state filter (downloading, completed, paused, etc.)
            category: Optional category filter

        Returns:
            List of torrent status dictionaries

        Example:
            >>> torrents = await client.get_all_torrents(filter_state="downloading")
            >>> for t in torrents:
            ...     print(f"{t['name']}: {t['progress']*100:.1f}%")
        """
        logger.info(f"Getting all torrents (filter={filter_state}, category={category})")

        endpoint = "/api/v2/torrents/info"
        params = {}

        if filter_state:
            params["filter"] = filter_state
        if category:
            params["category"] = category

        try:
            torrents = await self._request("GET", endpoint, params=params)
            logger.info(f"Found {len(torrents)} torrents")
            return torrents

        except QBittorrentError as e:
            logger.error(f"Failed to get torrents: {str(e)}")
            raise

    async def pause_torrent(self, torrent_hash: str) -> bool:
        """
        Pause torrent download.

        Args:
            torrent_hash: Torrent info hash

        Returns:
            True if successful

        Example:
            >>> await client.pause_torrent(torrent_hash)
        """
        logger.info(f"Pausing torrent: {torrent_hash}")

        endpoint = "/api/v2/torrents/pause"
        data = FormData()
        data.add_field("hashes", torrent_hash)

        try:
            result = await self._request("POST", endpoint, data=data)
            logger.info("Torrent paused successfully")
            return True

        except QBittorrentError as e:
            logger.error(f"Failed to pause torrent: {str(e)}")
            raise

    async def resume_torrent(self, torrent_hash: str) -> bool:
        """
        Resume torrent download.

        Args:
            torrent_hash: Torrent info hash

        Returns:
            True if successful

        Example:
            >>> await client.resume_torrent(torrent_hash)
        """
        logger.info(f"Resuming torrent: {torrent_hash}")

        endpoint = "/api/v2/torrents/resume"
        data = FormData()
        data.add_field("hashes", torrent_hash)

        try:
            result = await self._request("POST", endpoint, data=data)
            logger.info("Torrent resumed successfully")
            return True

        except QBittorrentError as e:
            logger.error(f"Failed to resume torrent: {str(e)}")
            raise

    async def delete_torrent(
        self,
        torrent_hash: str,
        delete_files: bool = False,
    ) -> bool:
        """
        Remove torrent from download queue.

        Args:
            torrent_hash: Torrent info hash
            delete_files: If True, also delete downloaded files

        Returns:
            True if successful

        Example:
            >>> await client.delete_torrent(torrent_hash, delete_files=True)
        """
        logger.info(f"Deleting torrent: {torrent_hash} (delete_files={delete_files})")

        endpoint = "/api/v2/torrents/delete"
        data = FormData()
        data.add_field("hashes", torrent_hash)
        data.add_field("deleteFiles", "true" if delete_files else "false")

        try:
            result = await self._request("POST", endpoint, data=data)
            logger.info("Torrent deleted successfully")
            return True

        except QBittorrentError as e:
            logger.error(f"Failed to delete torrent: {str(e)}")
            raise

    async def get_download_path(self, torrent_hash: Optional[str] = None) -> str:
        """
        Get configured downloads folder.

        Args:
            torrent_hash: Optional torrent hash to get specific save path

        Returns:
            Download path as string

        Example:
            >>> path = await client.get_download_path()
            >>> print(f"Downloads folder: {path}")
        """
        if torrent_hash:
            # Get torrent-specific save path
            logger.debug(f"Getting save path for torrent: {torrent_hash}")
            status = await self.get_torrent_status(torrent_hash)
            path = status.get("save_path", "")
            logger.info(f"Torrent save path: {path}")
            return path
        else:
            # Get default save path from preferences
            logger.debug("Getting default save path")
            endpoint = "/api/v2/app/preferences"

            try:
                prefs = await self._request("GET", endpoint)
                path = prefs.get("save_path", "")
                logger.info(f"Default save path: {path}")
                return path

            except QBittorrentError as e:
                logger.error(f"Failed to get preferences: {str(e)}")
                raise

    async def get_server_state(self) -> Dict[str, Any]:
        """
        Get qBittorrent server status.

        Returns:
            Dictionary with server state (download speed, connection status, etc.)

        Example:
            >>> state = await client.get_server_state()
            >>> print(f"Download speed: {state['dl_info_speed']} bytes/s")
            >>> print(f"Connected: {state['connection_status']}")
        """
        logger.debug("Getting server state")

        endpoint = "/api/v2/transfer/info"

        try:
            state = await self._request("GET", endpoint)
            logger.debug(
                f"Server state: DL={state.get('dl_info_speed', 0)} bytes/s, "
                f"UL={state.get('up_info_speed', 0)} bytes/s"
            )
            return state

        except QBittorrentError as e:
            logger.error(f"Failed to get server state: {str(e)}")
            raise

    async def set_category(
        self,
        category_name: str,
        save_path: Optional[str] = None,
    ) -> bool:
        """
        Create or update category.

        Args:
            category_name: Category name
            save_path: Optional custom save path for category

        Returns:
            True if successful

        Example:
            >>> await client.set_category("audiobooks", "/data/audiobooks")
        """
        logger.info(f"Setting category: {category_name}")

        endpoint = "/api/v2/torrents/createCategory"
        data = FormData()
        data.add_field("category", category_name)

        if save_path:
            data.add_field("savePath", save_path)

        try:
            result = await self._request("POST", endpoint, data=data)
            logger.info(f"Category '{category_name}' created/updated")
            return True

        except QBittorrentError as e:
            logger.error(f"Failed to set category: {str(e)}")
            raise

    async def get_categories(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all categories.

        Returns:
            Dictionary mapping category names to their properties

        Example:
            >>> categories = await client.get_categories()
            >>> for name, props in categories.items():
            ...     print(f"{name}: {props['savePath']}")
        """
        logger.debug("Getting categories")

        endpoint = "/api/v2/torrents/categories"

        try:
            categories = await self._request("GET", endpoint)
            logger.info(f"Found {len(categories)} categories")
            return categories

        except QBittorrentError as e:
            logger.error(f"Failed to get categories: {str(e)}")
            raise

    async def close(self):
        """Close client session."""
        if self.session:
            await self._logout()
            await self.session.close()
    # ========================================
    # RSS MANAGEMENT
    # ========================================

    async def add_rss_feed(
        self,
        url: str,
        path: str = "",
    ) -> bool:
        """
        Add RSS feed to qBittorrent.

        Args:
            url: RSS feed URL
            path: Optional path in RSS folder hierarchy

        Returns:
            True if successful

        Example:
            >>> await client.add_rss_feed("https://example.com/rss.xml", "audiobooks")
        """
        logger.info(f"Adding RSS feed: {url}")

        endpoint = "/api/v2/rss/addFeed"
        data = FormData()
        data.add_field("url", url)
        if path:
            data.add_field("path", path)

        try:
            result = await self._request("POST", endpoint, data=data)
            logger.info("RSS feed added successfully")
            return True
        except QBittorrentError as e:
            logger.error(f"Failed to add RSS feed: {str(e)}")
            raise

    async def get_rss_items(self, with_data: bool = False) -> Dict[str, Any]:
        """
        Get RSS items and folders.

        Args:
            with_data: If True, include feed data

        Returns:
            Dictionary of RSS items organized by path

        Example:
            >>> items = await client.get_rss_items()
            >>> for path, item in items.items():
            ...     print(f"{path}: {item.get('title', 'No title')}")
        """
        logger.info("Getting RSS items")

        endpoint = "/api/v2/rss/items"
        params = {"withData": "true" if with_data else "false"}

        try:
            items = await self._request("GET", endpoint, params=params)
            logger.info(f"Retrieved RSS items: {len(items)} top-level items")
            return items
        except QBittorrentError as e:
            logger.error(f"Failed to get RSS items: {str(e)}")
            raise

    async def remove_rss_item(self, path: str) -> bool:
        """
        Remove RSS item (feed or folder).

        Args:
            path: Path to RSS item to remove

        Returns:
            True if successful

        Example:
            >>> await client.remove_rss_item("audiobooks/feed1")
        """
        logger.info(f"Removing RSS item: {path}")

        endpoint = "/api/v2/rss/removeItem"
        data = FormData()
        data.add_field("path", path)

        try:
            result = await self._request("POST", endpoint, data=data)
            logger.info(f"RSS item removed: {path}")
            return True
        except QBittorrentError as e:
            logger.error(f"Failed to remove RSS item: {str(e)}")
            raise

    async def move_rss_item(self, item_path: str, dest_path: str) -> bool:
        """
        Move RSS item to new location.

        Args:
            item_path: Current path of RSS item
            dest_path: New path for RSS item

        Returns:
            True if successful

        Example:
            >>> await client.move_rss_item("feed1", "audiobooks/feed1")
        """
        logger.info(f"Moving RSS item from {item_path} to {dest_path}")

        endpoint = "/api/v2/rss/moveItem"
        data = FormData()
        data.add_field("itemPath", item_path)
        data.add_field("destPath", dest_path)

        try:
            result = await self._request("POST", endpoint, data=data)
            logger.info(f"RSS item moved: {item_path} -> {dest_path}")
            return True
        except QBittorrentError as e:
            logger.error(f"Failed to move RSS item: {str(e)}")
            raise

    async def refresh_rss_item(self, item_path: str) -> bool:
        """
        Refresh RSS item (feed).

        Args:
            item_path: Path to RSS item to refresh

        Returns:
            True if successful

        Example:
            >>> await client.refresh_rss_item("audiobooks/feed1")
        """
        logger.info(f"Refreshing RSS item: {item_path}")

        endpoint = "/api/v2/rss/refreshItem"
        data = FormData()
        data.add_field("itemPath", item_path)

        try:
            result = await self._request("POST", endpoint, data=data)
            logger.info(f"RSS item refreshed: {item_path}")
            return True
        except QBittorrentError as e:
            logger.error(f"Failed to refresh RSS item: {str(e)}")
            raise

    async def set_rss_rule(
        self,
        rule_name: str,
        rule_def: Dict[str, Any],
    ) -> bool:
        """
        Set RSS download rule.

        Args:
            rule_name: Name of the rule
            rule_def: Rule definition dictionary

        Returns:
            True if successful

        Example:
            >>> rule = {
            ...     "enabled": True,
            ...     "mustContain": "audiobook",
            ...     "episodeFilter": "",
            ...     "smartFilter": False,
            ...     "previouslyMatchedEpisodes": [],
            ...     "affectedFeeds": ["audiobooks/feed1"],
            ...     "addPaused": False,
            ...     "assignedCategory": "audiobooks",
            ...     "savePath": "/data/audiobooks"
            ... }
            >>> await client.set_rss_rule("audiobook_rule", rule)
        """
        logger.info(f"Setting RSS rule: {rule_name}")

        endpoint = "/api/v2/rss/setRule"
        data = FormData()
        data.add_field("ruleName", rule_name)
        data.add_field("ruleDef", str(rule_def).replace("'", '"'))  # Convert to JSON string

        try:
            result = await self._request("POST", endpoint, data=data)
            logger.info(f"RSS rule set: {rule_name}")
            return True
        except QBittorrentError as e:
            logger.error(f"Failed to set RSS rule: {str(e)}")
            raise

    async def get_rss_rules(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all RSS download rules.

        Returns:
            Dictionary of RSS rules

        Example:
            >>> rules = await client.get_rss_rules()
            >>> for name, rule in rules.items():
            ...     print(f"{name}: {rule.get('enabled', False)}")
        """
        logger.info("Getting RSS rules")

        endpoint = "/api/v2/rss/rules"

        try:
            rules = await self._request("GET", endpoint)
            logger.info(f"Retrieved {len(rules)} RSS rules")
            return rules
        except QBittorrentError as e:
            logger.error(f"Failed to get RSS rules: {str(e)}")
            raise

    async def remove_rss_rule(self, rule_name: str) -> bool:
        """
        Remove RSS download rule.

        Args:
            rule_name: Name of rule to remove

        Returns:
            True if successful

        Example:
            >>> await client.remove_rss_rule("old_rule")
        """
        logger.info(f"Removing RSS rule: {rule_name}")

        endpoint = "/api/v2/rss/removeRule"
        data = FormData()
        data.add_field("ruleName", rule_name)

        try:
            result = await self._request("POST", endpoint, data=data)
            logger.info(f"RSS rule removed: {rule_name}")
            return True
        except QBittorrentError as e:
            logger.error(f"Failed to remove RSS rule: {str(e)}")
            raise

    async def get_rss_matching_articles(self, rule_name: str) -> List[Dict[str, Any]]:
        """
        Get articles matching RSS rule.

        Args:
            rule_name: Name of RSS rule

        Returns:
            List of matching articles

        Example:
            >>> articles = await client.get_rss_matching_articles("audiobook_rule")
            >>> for article in articles:
            ...     print(f"{article.get('title', 'No title')}")
        """
        logger.info(f"Getting matching articles for rule: {rule_name}")

        endpoint = "/api/v2/rss/matchingArticles"
        params = {"ruleName": rule_name}

        try:
            articles = await self._request("GET", endpoint, params=params)
            logger.info(f"Found {len(articles)} matching articles")
            return articles
        except QBittorrentError as e:
            logger.error(f"Failed to get matching articles: {str(e)}")
            raise

    async def mark_rss_article_as_read(
        self,
        item_path: str,
        article_id: str,
    ) -> bool:
        """
        Mark RSS article as read.

        Args:
            item_path: Path to RSS item
            article_id: Article ID

        Returns:
            True if successful

        Example:
            >>> await client.mark_rss_article_as_read("audiobooks/feed1", "article123")
        """
        logger.info(f"Marking RSS article as read: {item_path}/{article_id}")

        endpoint = "/api/v2/rss/markAsRead"
        data = FormData()
        data.add_field("itemPath", item_path)
        data.add_field("articleId", article_id)

        try:
            result = await self._request("POST", endpoint, data=data)
            logger.info(f"RSS article marked as read: {item_path}/{article_id}")
            return True
        except QBittorrentError as e:
            logger.error(f"Failed to mark RSS article as read: {str(e)}")
            raise

    async def create_rss_folder(self, path: str) -> bool:
        """
        Create RSS folder.

        Args:
            path: Path for new folder

        Returns:
            True if successful

        Example:
            >>> await client.create_rss_folder("audiobooks")
        """
        logger.info(f"Creating RSS folder: {path}")

        # Create folder by adding a dummy feed and then removing it
        # This is a workaround since qBittorrent doesn't have a direct create folder API
        temp_feed_url = "http://example.com/dummy.xml"  # This will fail but create the folder

        try:
            await self.add_rss_feed(temp_feed_url, path)
        except QBittorrentError:
            # Expected to fail, but folder should be created
            pass

        # Try to remove the failed feed
        try:
            await self.remove_rss_item(f"{path}/dummy")
        except QBittorrentError:
            pass  # May not exist

        logger.info(f"RSS folder created: {path}")
        return True

    async def get_rss_feeds_status(self) -> Dict[str, Any]:
        """
        Get RSS feeds status and last update times.

        Returns:
            Dictionary with RSS status information

        Example:
            >>> status = await client.get_rss_feeds_status()
            >>> print(f"RSS enabled: {status.get('isProcessingEnabled', False)}")
        """
        logger.info("Getting RSS feeds status")

        # Get RSS items with data to check status
        try:
            items = await self.get_rss_items(with_data=True)

            # Extract status information
            status_info = {
                "total_feeds": 0,
                "total_folders": 0,
                "feeds_by_status": {},
            }

            def count_items(item_dict, path=""):
                for key, value in item_dict.items():
                    current_path = f"{path}/{key}" if path else key

                    if isinstance(value, dict):
                        if "url" in value:
                            # This is a feed
                            status_info["total_feeds"] += 1
                            last_update = value.get("lastBuildDate", "Never")
                            status_info["feeds_by_status"][current_path] = {
                                "last_update": last_update,
                                "has_error": "error" in value,
                            }
                        else:
                            # This is a folder
                            status_info["total_folders"] += 1
                            count_items(value, current_path)

            count_items(items)
            logger.info(f"RSS status: {status_info['total_feeds']} feeds, {status_info['total_folders']} folders")
            return status_info

        except QBittorrentError as e:
            logger.error(f"Failed to get RSS feeds status: {str(e)}")
            raise

    # ========================================
    # BANDWIDTH MANAGEMENT
    # ========================================

    async def set_global_download_limit(self, limit: int) -> bool:
        """
        Set global download speed limit.

        Args:
            limit: Download limit in bytes/second (0 = unlimited)

        Returns:
            True if successful

        Example:
            >>> await client.set_global_download_limit(1024000)  # 1 MB/s
        """
        logger.info(f"Setting global download limit: {limit} bytes/s")

        endpoint = "/api/v2/transfer/setDownloadLimit"
        data = FormData()
        data.add_field("limit", str(limit))

        try:
            result = await self._request("POST", endpoint, data=data)
            logger.info("Global download limit set successfully")
            return True
        except QBittorrentError as e:
            logger.error(f"Failed to set global download limit: {str(e)}")
            raise

    async def set_global_upload_limit(self, limit: int) -> bool:
        """
        Set global upload speed limit.

        Args:
            limit: Upload limit in bytes/second (0 = unlimited)

        Returns:
            True if successful

        Example:
            >>> await client.set_global_upload_limit(512000)  # 512 KB/s
        """
        logger.info(f"Setting global upload limit: {limit} bytes/s")

        endpoint = "/api/v2/transfer/setUploadLimit"
        data = FormData()
        data.add_field("limit", str(limit))

        try:
            result = await self._request("POST", endpoint, data=data)
            logger.info("Global upload limit set successfully")
            return True
        except QBittorrentError as e:
            logger.error(f"Failed to set global upload limit: {str(e)}")
            raise

    async def get_global_download_limit(self) -> int:
        """
        Get global download speed limit.

        Returns:
            Download limit in bytes/second

        Example:
            >>> limit = await client.get_global_download_limit()
            >>> print(f"Download limit: {limit} bytes/s")
        """
        logger.debug("Getting global download limit")

        endpoint = "/api/v2/transfer/downloadLimit"

        try:
            limit = await self._request("GET", endpoint)
            logger.info(f"Global download limit: {limit} bytes/s")
            return int(limit)
        except QBittorrentError as e:
            logger.error(f"Failed to get global download limit: {str(e)}")
            raise

    async def get_global_upload_limit(self) -> int:
        """
        Get global upload speed limit.

        Returns:
            Upload limit in bytes/second

        Example:
            >>> limit = await client.get_global_upload_limit()
            >>> print(f"Upload limit: {limit} bytes/s")
        """
        logger.debug("Getting global upload limit")

        endpoint = "/api/v2/transfer/uploadLimit"

        try:
            limit = await self._request("GET", endpoint)
            logger.info(f"Global upload limit: {limit} bytes/s")
            return int(limit)
        except QBittorrentError as e:
            logger.error(f"Failed to get global upload limit: {str(e)}")
            raise

    async def set_torrent_download_limit(self, torrent_hash: str, limit: int) -> bool:
        """
        Set download speed limit for specific torrent.

        Args:
            torrent_hash: Torrent info hash
            limit: Download limit in bytes/second (0 = unlimited)

        Returns:
            True if successful

        Example:
            >>> await client.set_torrent_download_limit(torrent_hash, 512000)
        """
        logger.info(f"Setting torrent download limit: {torrent_hash} -> {limit} bytes/s")

        endpoint = "/api/v2/torrents/setDownloadLimit"
        data = FormData()
        data.add_field("hashes", torrent_hash)
        data.add_field("limit", str(limit))

        try:
            result = await self._request("POST", endpoint, data=data)
            logger.info("Torrent download limit set successfully")
            return True
        except QBittorrentError as e:
            logger.error(f"Failed to set torrent download limit: {str(e)}")
            raise

    async def set_torrent_upload_limit(self, torrent_hash: str, limit: int) -> bool:
        """
        Set upload speed limit for specific torrent.

        Args:
            torrent_hash: Torrent info hash
            limit: Upload limit in bytes/second (0 = unlimited)

        Returns:
            True if successful

        Example:
            >>> await client.set_torrent_upload_limit(torrent_hash, 256000)
        """
        logger.info(f"Setting torrent upload limit: {torrent_hash} -> {limit} bytes/s")

        endpoint = "/api/v2/torrents/setUploadLimit"
        data = FormData()
        data.add_field("hashes", torrent_hash)
        data.add_field("limit", str(limit))

        try:
            result = await self._request("POST", endpoint, data=data)
            logger.info("Torrent upload limit set successfully")
            return True
        except QBittorrentError as e:
            logger.error(f"Failed to set torrent upload limit: {str(e)}")
            raise

    async def get_torrent_download_limit(self, torrent_hash: str) -> int:
        """
        Get download speed limit for specific torrent.

        Args:
            torrent_hash: Torrent info hash

        Returns:
            Download limit in bytes/second

        Example:
            >>> limit = await client.get_torrent_download_limit(torrent_hash)
            >>> print(f"Torrent download limit: {limit} bytes/s")
        """
        logger.debug(f"Getting torrent download limit: {torrent_hash}")

        endpoint = "/api/v2/torrents/downloadLimit"
        params = {"hashes": torrent_hash}

        try:
            limits = await self._request("GET", endpoint, params=params)
            limit = limits.get(torrent_hash, 0) if isinstance(limits, dict) else 0
            logger.info(f"Torrent download limit: {limit} bytes/s")
            return int(limit)
        except QBittorrentError as e:
            logger.error(f"Failed to get torrent download limit: {str(e)}")
            raise

    async def get_torrent_upload_limit(self, torrent_hash: str) -> int:
        """
        Get upload speed limit for specific torrent.

        Args:
            torrent_hash: Torrent info hash

        Returns:
            Upload limit in bytes/second

        Example:
            >>> limit = await client.get_torrent_upload_limit(torrent_hash)
            >>> print(f"Torrent upload limit: {limit} bytes/s")
        """
        logger.debug(f"Getting torrent upload limit: {torrent_hash}")

        endpoint = "/api/v2/torrents/uploadLimit"
        params = {"hashes": torrent_hash}

        try:
            limits = await self._request("GET", endpoint, params=params)
            limit = limits.get(torrent_hash, 0) if isinstance(limits, dict) else 0
            logger.info(f"Torrent upload limit: {limit} bytes/s")
            return int(limit)
        except QBittorrentError as e:
            logger.error(f"Failed to get torrent upload limit: {str(e)}")
            raise

    async def set_alternative_speed_limits_mode(self, enabled: bool) -> bool:
        """
        Enable or disable alternative speed limits.

        Args:
            enabled: True to enable alternative limits, False for normal limits

        Returns:
            True if successful

        Example:
            >>> await client.set_alternative_speed_limits_mode(True)
        """
        logger.info(f"Setting alternative speed limits mode: {enabled}")

        endpoint = "/api/v2/transfer/toggleSpeedLimitsMode"

        try:
            result = await self._request("POST", endpoint)
            logger.info(f"Alternative speed limits mode set to: {enabled}")
            return True
        except QBittorrentError as e:
            logger.error(f"Failed to set alternative speed limits mode: {str(e)}")
            raise

    async def get_alternative_speed_limits(self) -> Dict[str, int]:
        """
        Get alternative speed limits.

        Returns:
            Dictionary with alt_dl_limit and alt_up_limit

        Example:
            >>> limits = await client.get_alternative_speed_limits()
            >>> print(f"Alt DL: {limits['alt_dl_limit']} bytes/s")
        """
        logger.debug("Getting alternative speed limits")

        endpoint = "/api/v2/transfer/speedLimitsMode"
        alt_mode_endpoint = "/api/v2/transfer/speedLimitsMode"

        try:
            # Get current mode and limits
            mode_result = await self._request("GET", alt_mode_endpoint)
            alt_mode = mode_result.get("alternative_speed_limits", False)

            # Get the actual limits
            dl_limit = await self.get_global_download_limit()
            up_limit = await self.get_global_upload_limit()

            limits = {
                "alternative_speed_limits_enabled": alt_mode,
                "alt_dl_limit": dl_limit,
                "alt_up_limit": up_limit,
            }

            logger.info(f"Alternative speed limits: {limits}")
            return limits
        except QBittorrentError as e:
            logger.error(f"Failed to get alternative speed limits: {str(e)}")
            raise

    async def set_alternative_speed_limits(
        self,
        dl_limit: int,
        up_limit: int,
    ) -> bool:
        """
        Set alternative speed limits.

        Args:
            dl_limit: Alternative download limit in bytes/second
            up_limit: Alternative upload limit in bytes/second

        Returns:
            True if successful

        Example:
            >>> await client.set_alternative_speed_limits(512000, 256000)
        """
        logger.info(f"Setting alternative speed limits: DL={dl_limit}, UL={up_limit}")

        # First enable alternative speed limits mode
        await self.set_alternative_speed_limits_mode(True)

        # Set the limits
        await self.set_global_download_limit(dl_limit)
        await self.set_global_upload_limit(up_limit)

        logger.info("Alternative speed limits set successfully")
        return True

    async def get_bandwidth_usage_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive bandwidth usage statistics.

        Returns:
            Dictionary with bandwidth statistics

        Example:
            >>> stats = await client.get_bandwidth_usage_stats()
            >>> print(f"Current DL: {stats['current_dl']} bytes/s")
        """
        logger.debug("Getting bandwidth usage stats")

        try:
            # Get transfer info
            transfer_info = await self.get_server_state()

            # Get all torrents for detailed stats
            torrents = await self.get_all_torrents()

            # Calculate totals
            total_dl_speed = sum(t.get("dlspeed", 0) for t in torrents)
            total_ul_speed = sum(t.get("upspeed", 0) for t in torrents)
            total_downloaded = sum(t.get("downloaded", 0) for t in torrents)
            total_uploaded = sum(t.get("uploaded", 0) for t in torrents)

            stats = {
                "server_dl_speed": transfer_info.get("dl_info_speed", 0),
                "server_ul_speed": transfer_info.get("up_info_speed", 0),
                "total_torrent_dl_speed": total_dl_speed,
                "total_torrent_ul_speed": total_ul_speed,
                "total_downloaded": total_downloaded,
                "total_uploaded": total_uploaded,
                "active_torrents": len([t for t in torrents if t.get("state") in ["downloading", "uploading"]]),
                "total_torrents": len(torrents),
            }

            logger.info(f"Bandwidth stats: DL={stats['server_dl_speed']} bytes/s, UL={stats['server_ul_speed']} bytes/s")
            return stats
        except QBittorrentError as e:
            logger.error(f"Failed to get bandwidth usage stats: {str(e)}")
            raise
            self.session = None
