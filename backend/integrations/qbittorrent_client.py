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
            self.session = None
