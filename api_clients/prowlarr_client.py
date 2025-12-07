"""
Prowlarr API Client

Provides Prowlarr-specific API client implementation.

Author: Agent 10 - API Client Consolidation Specialist
"""

from .rest_client import RESTAPIClient
from ..api_client_system import APIClientConfig


class ProwlarrAPIClient(RESTAPIClient):
    """Prowlarr API client - extends REST client with service-specific methods."""

    def __init__(self, config: APIClientConfig):
        super().__init__(config)

    # Add Prowlarr-specific methods here
    async def get_indexers(self, **kwargs):
        """Get indexer list."""
        return await self.get("/api/v1/indexer", **kwargs)