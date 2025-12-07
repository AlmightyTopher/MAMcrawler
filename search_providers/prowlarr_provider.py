#!/usr/bin/env python3
"""
Prowlarr search provider for the unified search system.
Consolidates Prowlarr indexer search functionality.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any

from search_types import SearchProviderInterface, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class ProwlarrSearchProvider(SearchProviderInterface):
    """
    Prowlarr indexer search provider
    """

    PROVIDER_TYPE = "prowlarr"
    CAPABILITIES = ["torrent_search", "indexer_search", "magnet_extraction"]
    RATE_LIMITS = {"requests_per_minute": 30, "delay_seconds": 2}
    CONFIG_REQUIRED = ["base_url", "api_key"]

    # Prowlarr categories for audiobooks
    AUDIOBOOK_CATEGORIES = [3000, 3010]  # Audio, Audiobook

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = self.config.get('base_url')
        self.api_key = self.config.get('api_key')
        self.client = None

    async def __aenter__(self):
        """Context manager entry - initialize client"""
        if not self.base_url or not self.api_key:
            raise ValueError("Prowlarr base_url and api_key are required")

        # Import here to avoid circular imports
        try:
            from backend.integrations.prowlarr_client import ProwlarrClient
            self.client = ProwlarrClient(self.base_url, self.api_key)
            await self.client.__aenter__()
            return self
        except ImportError:
            logger.error("ProwlarrClient not available")
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Search Prowlarr indexers for torrents

        Args:
            query: Search query parameters

        Returns:
            List of search results
        """
        if not self.client:
            # Initialize client if not in context manager
            async with self:
                return await self._perform_search(query)

        return await self._perform_search(query)

    async def _perform_search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform the actual search"""
        results = []

        try:
            # Rate limiting
            await asyncio.sleep(self.RATE_LIMITS["delay_seconds"])

            # Search with audiobook categories
            search_results = await self.client.search(
                query=query.query,
                categories=self.AUDIOBOOK_CATEGORIES,
                limit=query.limit
            )

            # Convert to unified format
            for item in search_results:
                result = self._convert_to_search_result(item, query.query)
                if result:
                    results.append(result)

            logger.info(f"Prowlarr search found {len(results)} results for '{query.query}'")

        except Exception as e:
            logger.error(f"Prowlarr search error: {e}")
            return []

        return results

    def _convert_to_search_result(self, prowlarr_item: Dict[str, Any], search_query: str) -> Optional[SearchResult]:
        """Convert Prowlarr item to unified SearchResult format"""
        try:
            title = prowlarr_item.get('title', 'Unknown Title')
            guid = prowlarr_item.get('guid', '')

            # Extract magnet link
            magnet_link = self._extract_magnet_link(prowlarr_item)

            # Calculate size in bytes
            size_bytes = prowlarr_item.get('size', 0)

            # Extract seeders/leechers
            seeders = prowlarr_item.get('seeders', 0)
            leechers = prowlarr_item.get('leechers', 0)

            # Extract publish date
            publish_date = prowlarr_item.get('publishDate')

            # Extract indexer info
            indexer = prowlarr_item.get('indexer', 'Unknown')

            result = SearchResult(
                provider=self.PROVIDER_TYPE,
                query=search_query,
                title=title,
                magnet_link=magnet_link,
                size=size_bytes,
                seeders=seeders,
                leechers=leechers,
                url=guid,
                confidence=self._calculate_confidence(prowlarr_item),
                metadata={
                    'indexer': indexer,
                    'publish_date': publish_date,
                    'categories': prowlarr_item.get('categories', []),
                    'info_hash': prowlarr_item.get('infoHash'),
                    'minimum_ratio': prowlarr_item.get('minimumRatio'),
                    'minimum_seed_time': prowlarr_item.get('minimumSeedTime'),
                    'download_volume_factor': prowlarr_item.get('downloadVolumeFactor'),
                    'upload_volume_factor': prowlarr_item.get('uploadVolumeFactor'),
                    'guid': guid
                }
            )

            return result

        except Exception as e:
            logger.warning(f"Error converting Prowlarr item: {e}")
            return None

    def _extract_magnet_link(self, item: Dict[str, Any]) -> Optional[str]:
        """Extract magnet link from Prowlarr result"""
        # Try different possible magnet link fields
        magnet_fields = ['magnetUrl', 'downloadUrl', 'link']

        for field in magnet_fields:
            magnet = item.get(field)
            if magnet and isinstance(magnet, str):
                if magnet.startswith('magnet:'):
                    return magnet
                # Some indexers might return download URLs that need conversion
                # For now, we'll return them as-is and let the download client handle it

        return None

    def _calculate_confidence(self, item: Dict[str, Any]) -> float:
        """Calculate confidence score for Prowlarr result"""
        confidence = 0.5  # Base confidence

        # Higher confidence for more seeders
        seeders = item.get('seeders', 0)
        if seeders > 10:
            confidence += 0.2
        elif seeders > 5:
            confidence += 0.1
        elif seeders == 0:
            confidence -= 0.3  # Penalize no seeders

        # Higher confidence for larger files (likely complete audiobooks)
        size = item.get('size', 0)
        if size > 100 * 1024 * 1024:  # > 100MB
            confidence += 0.1
        elif size < 10 * 1024 * 1024:  # < 10MB
            confidence -= 0.2  # Penalize very small files

        # Higher confidence for known good indexers
        indexer = item.get('indexer', '').lower()
        if any(good_indexer in indexer for good_indexer in ['mam', 'audiobook', 'private']):
            confidence += 0.1

        return min(max(confidence, 0.0), 1.0)  # Clamp between 0 and 1

    async def get_indexer_stats(self) -> Dict[str, Any]:
        """Get statistics about configured indexers"""
        try:
            if not self.client:
                async with self:
                    return await self.client.get_indexer_stats()

            return await self.client.get_indexer_stats()

        except Exception as e:
            logger.error(f"Error getting indexer stats: {e}")
            return {}

    async def get_enabled_indexers(self) -> List[Dict[str, Any]]:
        """Get list of enabled indexers"""
        try:
            if not self.client:
                async with self:
                    indexers = await self.client.get_indexers()
            else:
                indexers = await self.client.get_indexers()

            # Filter to enabled indexers
            enabled = [idx for idx in indexers if idx.get('enable', False)]
            return enabled

        except Exception as e:
            logger.error(f"Error getting enabled indexers: {e}")
            return []

    async def test_indexer(self, indexer_id: int) -> bool:
        """Test a specific indexer"""
        try:
            if not self.client:
                async with self:
                    result = await self.client.test_indexer(indexer_id)
            else:
                result = await self.client.test_indexer(indexer_id)

            return result.get('isValid', False)

        except Exception as e:
            logger.error(f"Error testing indexer {indexer_id}: {e}")
            return False

    async def health_check(self) -> bool:
        """Check if Prowlarr is accessible"""
        try:
            if not self.client:
                async with self:
                    status = await self.client.get_system_status()
            else:
                status = await self.client.get_system_status()

            return bool(status.get('version'))

        except Exception as e:
            logger.error(f"Prowlarr health check error: {e}")
            return False