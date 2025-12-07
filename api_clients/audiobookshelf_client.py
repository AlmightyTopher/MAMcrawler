"""
Audiobookshelf API Client

Provides Audiobookshelf-specific API client implementation.

Author: Agent 10 - API Client Consolidation Specialist
"""

from .rest_client import RESTAPIClient
from ..api_client_system import APIClientConfig


class AudiobookshelfAPIClient(RESTAPIClient):
    """Audiobookshelf API client - extends REST client with service-specific methods."""

    def __init__(self, config: APIClientConfig):
        super().__init__(config)

    # Add Audiobookshelf-specific methods here
    async def get_library_items(self, **kwargs):
        """Get library items with pagination."""
        return await self.get("/api/libraries/items", **kwargs)