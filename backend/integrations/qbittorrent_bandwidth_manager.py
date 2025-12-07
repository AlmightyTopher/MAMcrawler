"""
qBittorrent Bandwidth Management

Manages bandwidth limits and alternative speed limits for qBittorrent downloads.
"""

import logging
from typing import Any, Dict, Optional
from aiohttp import FormData

logger = logging.getLogger(__name__)


class QBittorrentBandwidthManager:
    """
    Manager for qBittorrent bandwidth operations.

    Encapsulates all bandwidth-related operations including:
    - Global download/upload limits
    - Per-torrent download/upload limits
    - Alternative speed limits
    - Bandwidth statistics

    Args:
        client: Reference to QBittorrentClient for making requests
    """

    def __init__(self, client):
        """Initialize bandwidth manager with client reference."""
        self.client = client

    async def set_global_download_limit(self, limit_kb: int) -> bool:
        """
        Set global download limit.

        Args:
            limit_kb: Limit in KB/s (0 = unlimited)

        Returns:
            True if successful

        Raises:
            QBittorrentError: On API errors
        """
        return await self._set_limit("/api/v2/app/setDownloadLimit", limit_kb)

    async def set_global_upload_limit(self, limit_kb: int) -> bool:
        """
        Set global upload limit.

        Args:
            limit_kb: Limit in KB/s (0 = unlimited)

        Returns:
            True if successful

        Raises:
            QBittorrentError: On API errors
        """
        return await self._set_limit("/api/v2/app/setUploadLimit", limit_kb)

    async def get_global_download_limit(self) -> int:
        """
        Get current global download limit.

        Returns:
            Limit in KB/s (0 = unlimited)

        Raises:
            QBittorrentError: On API errors
        """
        return await self._get_limit("/api/v2/app/downloadLimit")

    async def get_global_upload_limit(self) -> int:
        """
        Get current global upload limit.

        Returns:
            Limit in KB/s (0 = unlimited)

        Raises:
            QBittorrentError: On API errors
        """
        return await self._get_limit("/api/v2/app/uploadLimit")

    async def set_torrent_download_limit(self, torrent_hash: str, limit_kb: int) -> bool:
        """
        Set download limit for specific torrent.

        Args:
            torrent_hash: Torrent hash
            limit_kb: Limit in KB/s (0 = unlimited)

        Returns:
            True if successful

        Raises:
            QBittorrentError: On API errors
        """
        data = FormData()
        data.add_field("hashes", torrent_hash)
        data.add_field("limit", str(limit_kb * 1024))  # Convert to bytes/s

        logger.debug(f"Setting download limit {limit_kb}KB/s for torrent {torrent_hash[:8]}")
        result = await self.client._request(
            "POST",
            "/api/v2/torrents/setDownloadLimit",
            data=data
        )
        logger.info(f"Set download limit for torrent {torrent_hash[:8]}")
        return True

    async def set_torrent_upload_limit(self, torrent_hash: str, limit_kb: int) -> bool:
        """
        Set upload limit for specific torrent.

        Args:
            torrent_hash: Torrent hash
            limit_kb: Limit in KB/s (0 = unlimited)

        Returns:
            True if successful

        Raises:
            QBittorrentError: On API errors
        """
        data = FormData()
        data.add_field("hashes", torrent_hash)
        data.add_field("limit", str(limit_kb * 1024))  # Convert to bytes/s

        logger.debug(f"Setting upload limit {limit_kb}KB/s for torrent {torrent_hash[:8]}")
        result = await self.client._request(
            "POST",
            "/api/v2/torrents/setUploadLimit",
            data=data
        )
        logger.info(f"Set upload limit for torrent {torrent_hash[:8]}")
        return True

    async def get_torrent_download_limit(self, torrent_hash: str) -> int:
        """
        Get download limit for specific torrent.

        Args:
            torrent_hash: Torrent hash

        Returns:
            Limit in KB/s (0 = unlimited)

        Raises:
            QBittorrentError: On API errors
        """
        params = {"hashes": torrent_hash}

        logger.debug(f"Getting download limit for torrent {torrent_hash[:8]}")
        response = await self.client._request(
            "GET",
            "/api/v2/torrents/downloadLimit",
            params=params
        )

        # Response is dict with hash as key
        limit_bytes = response.get(torrent_hash, 0)
        limit_kb = limit_bytes // 1024 if limit_bytes else 0
        logger.debug(f"Torrent {torrent_hash[:8]} download limit: {limit_kb}KB/s")
        return limit_kb

    async def get_torrent_upload_limit(self, torrent_hash: str) -> int:
        """
        Get upload limit for specific torrent.

        Args:
            torrent_hash: Torrent hash

        Returns:
            Limit in KB/s (0 = unlimited)

        Raises:
            QBittorrentError: On API errors
        """
        params = {"hashes": torrent_hash}

        logger.debug(f"Getting upload limit for torrent {torrent_hash[:8]}")
        response = await self.client._request(
            "GET",
            "/api/v2/torrents/uploadLimit",
            params=params
        )

        # Response is dict with hash as key
        limit_bytes = response.get(torrent_hash, 0)
        limit_kb = limit_bytes // 1024 if limit_bytes else 0
        logger.debug(f"Torrent {torrent_hash[:8]} upload limit: {limit_kb}KB/s")
        return limit_kb

    async def set_alternative_speed_limits_mode(self, enabled: bool) -> bool:
        """
        Enable/disable alternative speed limits mode.

        Args:
            enabled: True to enable, False to disable

        Returns:
            True if successful

        Raises:
            QBittorrentError: On API errors
        """
        data = FormData()
        data.add_field("enabled", "true" if enabled else "false")

        logger.info(f"Setting alternative speed limits mode: {enabled}")
        await self.client._request(
            "POST",
            "/api/v2/app/setAltSpeedLimitsEnabled",
            data=data
        )
        return True

    async def get_alternative_speed_limits(self) -> Dict[str, int]:
        """
        Get alternative speed limits.

        Returns:
            Dict with 'download' and 'upload' keys (in KB/s)

        Raises:
            QBittorrentError: On API errors
        """
        logger.debug("Getting alternative speed limits")
        response = await self.client._request(
            "GET",
            "/api/v2/app/alternativeSpeedLimitsEnabled"
        )
        return response

    async def set_alternative_speed_limits(
        self,
        download_kb: int,
        upload_kb: int
    ) -> bool:
        """
        Set alternative speed limits.

        Args:
            download_kb: Download limit in KB/s
            upload_kb: Upload limit in KB/s

        Returns:
            True if successful

        Raises:
            QBittorrentError: On API errors
        """
        data = FormData()
        data.add_field("downLimit", str(download_kb * 1024))  # Convert to bytes/s
        data.add_field("upLimit", str(upload_kb * 1024))

        logger.info(f"Setting alternative speed limits: DL={download_kb}KB/s, UL={upload_kb}KB/s")
        await self.client._request(
            "POST",
            "/api/v2/app/setAltSpeedLimit",
            data=data
        )
        return True

    async def get_bandwidth_usage_stats(self) -> Dict[str, Any]:
        """
        Get bandwidth usage statistics.

        Returns:
            Dict with download/upload speeds and limits

        Raises:
            QBittorrentError: On API errors
        """
        logger.debug("Getting bandwidth usage statistics")
        response = await self.client._request("GET", "/api/v2/app/networkInterface")
        return response

    # Helper methods

    async def _set_limit(self, endpoint: str, limit_kb: int) -> bool:
        """
        Generic limit setting helper.

        Args:
            endpoint: API endpoint
            limit_kb: Limit in KB/s

        Returns:
            True if successful

        Raises:
            QBittorrentError: On API errors
        """
        data = FormData()
        data.add_field("limit", str(limit_kb * 1024))  # Convert to bytes/s

        logger.debug(f"Setting limit {limit_kb}KB/s via {endpoint}")
        await self.client._request("POST", endpoint, data=data)
        return True

    async def _get_limit(self, endpoint: str) -> int:
        """
        Generic limit getting helper.

        Args:
            endpoint: API endpoint

        Returns:
            Limit in KB/s

        Raises:
            QBittorrentError: On API errors
        """
        logger.debug(f"Getting limit from {endpoint}")
        limit_bytes = await self.client._request("GET", endpoint)
        limit_kb = limit_bytes // 1024 if limit_bytes else 0
        logger.debug(f"Retrieved limit: {limit_kb}KB/s")
        return limit_kb
