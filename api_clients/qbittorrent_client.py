"""
qBittorrent API Client

Provides qBittorrent-specific API client implementation.

Author: Agent 10 - API Client Consolidation Specialist
"""

from .rest_client import RESTAPIClient
from ..api_client_system import APIClientConfig


class QBittorrentAPIClient(RESTAPIClient):
    """qBittorrent API client - extends REST client with service-specific methods."""

    def __init__(self, config: APIClientConfig):
        super().__init__(config)

    # Add qBittorrent-specific methods here
    async def get_torrents(self, **kwargs):
        """Get torrent list."""
        return await self.get("/api/v2/torrents/info", **kwargs)