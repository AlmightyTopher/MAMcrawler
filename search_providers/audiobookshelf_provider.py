#!/usr/bin/env python3
"""
Audiobookshelf search provider for the unified search system.
Consolidates Audiobookshelf library search functionality.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any

from search_types import SearchProviderInterface, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class AudiobookshelfSearchProvider(SearchProviderInterface):
    """
    Audiobookshelf library search provider
    """

    PROVIDER_TYPE = "audiobookshelf"
    CAPABILITIES = ["library_search", "metadata_search", "collection_search"]
    RATE_LIMITS = {"requests_per_minute": 60, "delay_seconds": 1}
    CONFIG_REQUIRED = ["base_url", "api_token"]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = self.config.get('base_url')
        self.api_token = self.config.get('api_token')
        self.client = None

    async def __aenter__(self):
        """Context manager entry - initialize client"""
        if not self.base_url or not self.api_token:
            raise ValueError("Audiobookshelf base_url and api_token are required")

        # Import here to avoid circular imports
        try:
            from backend.integrations.abs_client import AudiobookshelfClient
            self.client = AudiobookshelfClient(self.base_url, self.api_token)
            await self.client.__aenter__()
            return self
        except ImportError:
            logger.error("AudiobookshelfClient not available")
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Search Audiobookshelf library

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

            # Search the library
            search_results = await self.client.search_books(
                query=query.query,
                limit=query.limit
            )

            # Convert to unified format
            for item in search_results:
                result = self._convert_to_search_result(item, query.query)
                if result:
                    results.append(result)

            logger.info(f"Audiobookshelf search found {len(results)} results for '{query.query}'")

        except Exception as e:
            logger.error(f"Audiobookshelf search error: {e}")
            return []

        return results

    def _convert_to_search_result(self, abs_item: Dict[str, Any], search_query: str) -> Optional[SearchResult]:
        """Convert Audiobookshelf item to unified SearchResult format"""
        try:
            media = abs_item.get('media', {})
            metadata = media.get('metadata', {})

            title = metadata.get('title', 'Unknown Title')
            authors = metadata.get('authors', [])
            author_names = []

            if isinstance(authors, list):
                for author in authors:
                    if isinstance(author, dict):
                        author_names.append(author.get('name', 'Unknown'))
                    else:
                        author_names.append(str(author))
            else:
                author_names = [str(authors)] if authors else []

            author = ', '.join(author_names) if author_names else 'Unknown'

            # Extract series information
            series_name = metadata.get('seriesName')
            series_position = None
            if series_name:
                # Parse series position from series name (e.g., "Series Name #1")
                import re
                match = re.search(r'#(\d+(?:\.\d+)?)', series_name)
                if match:
                    series_position = match.group(1)

            result = SearchResult(
                provider=self.PROVIDER_TYPE,
                query=search_query,
                title=title,
                author=author,
                series_name=series_name,
                series_position=series_position,
                url=f"{self.base_url}/item/{abs_item.get('id', '')}",
                description=metadata.get('description', ''),
                confidence=1.0,  # High confidence for library items
                metadata={
                    'abs_id': abs_item.get('id'),
                    'library_id': abs_item.get('libraryId'),
                    'duration': media.get('duration'),
                    'size': media.get('size'),
                    'published_year': metadata.get('publishedYear'),
                    'publisher': metadata.get('publisher'),
                    'isbn': metadata.get('isbn'),
                    'asin': metadata.get('asin'),
                    'language': metadata.get('language'),
                    'genres': metadata.get('genres', []),
                    'tags': metadata.get('tags', []),
                    'narrators': [n.get('name', '') if isinstance(n, dict) else str(n)
                                for n in metadata.get('narrators', [])]
                }
            )

            return result

        except Exception as e:
            logger.warning(f"Error converting Audiobookshelf item: {e}")
            return None

    async def get_library_books_by_author(self, author_name: str, limit: int = 50) -> List[SearchResult]:
        """
        Get all books by a specific author from the library

        Args:
            author_name: Name of the author
            limit: Maximum number of results

        Returns:
            List of SearchResult objects
        """
        try:
            # Get all library items
            all_items = await self.client.get_library_items(limit=limit * 2)  # Get more to filter

            results = []
            for item in all_items:
                media = item.get('media', {})
                metadata = media.get('metadata', {})

                # Check if author matches
                authors = metadata.get('authors', [])
                author_matches = False

                for author in authors:
                    author_name_in_lib = author.get('name', '').lower() if isinstance(author, dict) else str(author).lower()
                    if author_name.lower() in author_name_in_lib or author_name_in_lib in author_name.lower():
                        author_matches = True
                        break

                if author_matches:
                    result = self._convert_to_search_result(item, f"author:{author_name}")
                    if result:
                        results.append(result)

                        if len(results) >= limit:
                            break

            logger.info(f"Found {len(results)} books by {author_name} in library")
            return results

        except Exception as e:
            logger.error(f"Error getting library books by author {author_name}: {e}")
            return []

    async def get_missing_books(self, owned_titles: List[str], author_name: Optional[str] = None) -> List[SearchResult]:
        """
        Find books not in the library (useful for comparing with external sources)

        Args:
            owned_titles: List of titles already owned
            author_name: Optional author filter

        Returns:
            List of potentially missing books (this would need external data source)
        """
        # This method would be used in conjunction with external search providers
        # For now, return empty list as it requires external data
        logger.info("get_missing_books requires external data source comparison")
        return []

    async def health_check(self) -> bool:
        """Check if Audiobookshelf is accessible"""
        try:
            if not self.client:
                async with self:
                    libraries = await self.client.get_libraries()
                    return len(libraries) > 0
            else:
                libraries = await self.client.get_libraries()
                return len(libraries) > 0
        except Exception as e:
            logger.error(f"Audiobookshelf health check error: {e}")
            return False