#!/usr/bin/env python3
"""
Unified Search System
=====================

Consolidated search system that provides a single entry point for all search operations.
Supports MAM, Audiobookshelf, Goodreads, Prowlarr, and local search providers.

Usage:
    from search_system import SearchSystem

    async with SearchSystem() as search:
        results = await search.search_audiobooks("Foundation Asimov")
        print(f"Found {len(results)} results")
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

from search_types import SearchQuery, SearchResult, SearchMode
from search_cache.cache_manager import SearchCache

logger = logging.getLogger(__name__)


class SearchProvider(Enum):
    """Available search providers"""
    MAM = "mam"
    AUDIOBOOKSHELF = "audiobookshelf"
    GOODREADS = "goodreads"
    PROWLARR = "prowlarr"
    LOCAL = "local"


@dataclass
class SearchConfig:
    """Configuration for search providers"""
    mam: Optional[Dict[str, Any]] = None
    audiobookshelf: Optional[Dict[str, Any]] = None
    goodreads: Optional[Dict[str, Any]] = None
    prowlarr: Optional[Dict[str, Any]] = None
    local: Optional[Dict[str, Any]] = None
    cache_enabled: bool = True
    cache_ttl: int = 1800  # 30 minutes default


class UnifiedSearchSystem:
    """
    Unified search system that consolidates all search providers into a single interface.

    Provides:
    - Unified search interface across all providers
    - Caching and rate limiting
    - Result aggregation and deduplication
    - Health monitoring
    """

    def __init__(self, config: Optional[SearchConfig] = None):
        """
        Initialize the unified search system

        Args:
            config: Search configuration with provider settings
        """
        self.config = config or SearchConfig()
        self.providers = {}
        self.cache = SearchCache() if self.config.cache_enabled else None
        self._initialized = False

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()

    async def initialize(self):
        """Initialize all configured search providers"""
        if self._initialized:
            return

        logger.info("Initializing unified search system...")

        # Initialize providers based on configuration
        provider_configs = {
            SearchProvider.MAM: (self.config.mam, "search_providers.mam_provider", "MAMSearchProvider"),
            SearchProvider.AUDIOBOOKSHELF: (self.config.audiobookshelf, "search_providers.audiobookshelf_provider", "AudiobookshelfSearchProvider"),
            SearchProvider.GOODREADS: (self.config.goodreads, "search_providers.goodreads_provider", "GoodreadsSearchProvider"),
            SearchProvider.PROWLARR: (self.config.prowlarr, "search_providers.prowlarr_provider", "ProwlarrSearchProvider"),
            SearchProvider.LOCAL: (self.config.local, "search_providers.local_provider", "LocalSearchProvider"),
        }

        for provider_type, (config, module_name, class_name) in provider_configs.items():
            if config is not None:
                try:
                    module = __import__(module_name, fromlist=[class_name])
                    provider_class = getattr(module, class_name)
                    provider = provider_class(config)
                    self.providers[provider_type] = provider
                    logger.info(f"Initialized {provider_type.value} provider")
                except Exception as e:
                    logger.warning(f"Failed to initialize {provider_type.value} provider: {e}")

        self._initialized = True
        logger.info(f"Search system initialized with {len(self.providers)} providers")

    async def cleanup(self):
        """Clean up resources"""
        if self.cache:
            await self.cache.cleanup()
        self._initialized = False

    async def search_audiobooks(
        self,
        query: str,
        providers: Optional[List[SearchProvider]] = None,
        mode: SearchMode = SearchMode.QUICK,
        limit: int = 20,
        **kwargs
    ) -> List[SearchResult]:
        """
        Search for audiobooks across all configured providers

        Args:
            query: Search query string
            providers: List of providers to search (default: all configured)
            mode: Search mode (quick, comprehensive, batch)
            limit: Maximum results per provider
            **kwargs: Additional search parameters

        Returns:
            List of search results
        """
        if not self._initialized:
            await self.initialize()

        # Default to all configured providers
        if providers is None:
            providers = list(self.providers.keys())

        # Create search query
        search_query = SearchQuery(
            query=query,
            mode=mode,
            limit=limit,
            **kwargs
        )

        # Check cache first
        if self.cache:
            cache_key = f"audiobooks:{query}:{mode.value}:{limit}"
            cached_results = await self.cache.get(cache_key)
            if cached_results:
                logger.info(f"Returning cached results for: {query}")
                return cached_results

        all_results = []
        tasks = []

        # Create search tasks for each provider
        for provider_type in providers:
            if provider_type in self.providers:
                provider = self.providers[provider_type]
                task = self._search_provider(provider_type, provider, search_query)
                tasks.append(task)

        # Execute searches concurrently
        if tasks:
            results_lists = await asyncio.gather(*tasks, return_exceptions=True)

            for i, results in enumerate(results_lists):
                provider_type = providers[i]
                if isinstance(results, Exception):
                    logger.error(f"Search failed for {provider_type.value}: {results}")
                else:
                    all_results.extend(results)
                    logger.info(f"{provider_type.value}: {len(results)} results")

        # Sort and deduplicate results
        all_results = self._deduplicate_results(all_results)
        all_results = self._sort_results(all_results, mode)

        # Cache results
        if self.cache:
            await self.cache.set(cache_key, all_results, ttl=self.config.cache_ttl)

        logger.info(f"Total results for '{query}': {len(all_results)}")
        return all_results

    async def _search_provider(
        self,
        provider_type: SearchProvider,
        provider,
        query: SearchQuery
    ) -> List[SearchResult]:
        """Search a specific provider"""
        try:
            async with provider:
                results = await provider.search(query)
                # Add provider info to results
                for result in results:
                    result.provider = provider_type.value
                return results
        except Exception as e:
            logger.error(f"Provider {provider_type.value} search failed: {e}")
            return []

    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicate results based on title and author similarity"""
        if not results:
            return results

        deduplicated = []
        seen = set()

        for result in results:
            # Create a key for deduplication
            key = self._create_deduplication_key(result)

            if key not in seen:
                seen.add(key)
                deduplicated.append(result)

        return deduplicated

    def _create_deduplication_key(self, result: SearchResult) -> str:
        """Create a deduplication key for a result"""
        # Normalize title and author for comparison
        title = result.title.lower().strip() if result.title else ""
        author = result.author.lower().strip() if result.author else ""

        # Remove common suffixes/prefixes
        title = title.replace("audiobook", "").replace("unabridged", "").strip()
        title = " ".join(title.split())  # Normalize whitespace

        return f"{title}|{author}|{result.provider}"

    def _sort_results(self, results: List[SearchResult], mode: SearchMode) -> List[SearchResult]:
        """Sort results by relevance"""
        if mode == SearchMode.QUICK:
            # Sort by confidence, then by provider priority
            provider_priority = {
                "audiobookshelf": 1,  # Library results first
                "mam": 2,             # Direct torrent sources
                "prowlarr": 3,        # Indexer results
                "goodreads": 4,       # Metadata only
                "local": 5            # Local knowledge
            }

            def sort_key(result):
                priority = provider_priority.get(result.provider, 99)
                return (priority, -result.confidence, -getattr(result, 'seeders', 0))

        elif mode == SearchMode.COMPREHENSIVE:
            # Sort by confidence and completeness
            def sort_key(result):
                return (-result.confidence, -getattr(result, 'seeders', 0))

        else:  # BATCH mode
            # Sort by seeders for batch operations
            def sort_key(result):
                return (-getattr(result, 'seeders', 0), -result.confidence)

        return sorted(results, key=sort_key)

    async def search_by_author(
        self,
        author_name: str,
        providers: Optional[List[SearchProvider]] = None,
        limit: int = 50
    ) -> List[SearchResult]:
        """
        Search for all works by a specific author

        Args:
            author_name: Name of the author
            providers: Providers to search
            limit: Maximum results

        Returns:
            List of author's works
        """
        query = SearchQuery(
            query=author_name,
            author=author_name,
            limit=limit
        )

        return await self.search_audiobooks(
            query=author_name,
            providers=providers,
            mode=SearchMode.COMPREHENSIVE,
            limit=limit,
            author=author_name
        )

    async def search_by_genre(
        self,
        genre: str,
        providers: Optional[List[SearchProvider]] = None,
        limit: int = 20
    ) -> List[SearchResult]:
        """
        Search for audiobooks in a specific genre

        Args:
            genre: Genre to search for
            providers: Providers to search
            limit: Maximum results

        Returns:
            List of genre results
        """
        query = SearchQuery(
            query=genre,
            genre=genre,
            limit=limit
        )

        return await self.search_audiobooks(
            query=f"genre:{genre}",
            providers=providers,
            mode=SearchMode.QUICK,
            limit=limit,
            genre=genre
        )

    async def find_missing_books(
        self,
        owned_titles: List[str],
        author_name: Optional[str] = None,
        providers: Optional[List[SearchProvider]] = None
    ) -> List[SearchResult]:
        """
        Find books not in the user's library

        Args:
            owned_titles: List of titles already owned
            author_name: Optional author filter
            providers: Providers to search

        Returns:
            List of potentially missing books
        """
        # This would require comparing against Audiobookshelf library
        # For now, delegate to Audiobookshelf provider if available
        if SearchProvider.AUDIOBOOKSHELF in self.providers:
            provider = self.providers[SearchProvider.AUDIOBOOKSHELF]
            try:
                async with provider:
                    return await provider.get_missing_books(owned_titles, author_name)
            except Exception as e:
                logger.error(f"Error finding missing books: {e}")

        return []

    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of all configured providers

        Returns:
            Dict mapping provider names to health status
        """
        health_status = {}

        for provider_type, provider in self.providers.items():
            try:
                async with provider:
                    healthy = await provider.health_check()
                    health_status[provider_type.value] = healthy
            except Exception as e:
                logger.error(f"Health check failed for {provider_type.value}: {e}")
                health_status[provider_type.value] = False

        return health_status

    async def get_provider_stats(self) -> Dict[str, Any]:
        """
        Get statistics from all providers

        Returns:
            Dict with provider statistics
        """
        stats = {}

        for provider_type, provider in self.providers.items():
            try:
                if hasattr(provider, 'get_indexer_stats'):
                    async with provider:
                        provider_stats = await provider.get_indexer_stats()
                        stats[provider_type.value] = provider_stats
                elif hasattr(provider, 'get_index_stats'):
                    async with provider:
                        provider_stats = await provider.get_index_stats()
                        stats[provider_type.value] = provider_stats
                else:
                    stats[provider_type.value] = {"status": "no_stats_available"}
            except Exception as e:
                logger.error(f"Error getting stats for {provider_type.value}: {e}")
                stats[provider_type.value] = {"error": str(e)}

        return stats

    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return [p.value for p in self.providers.keys()]

    def is_provider_available(self, provider: Union[str, SearchProvider]) -> bool:
        """Check if a provider is available"""
        if isinstance(provider, str):
            provider = SearchProvider(provider)
        return provider in self.providers


# Convenience functions for backward compatibility
async def search_audiobooks(query: str, **kwargs) -> List[SearchResult]:
    """Convenience function for quick audiobook searches"""
    async with UnifiedSearchSystem() as search:
        return await search.search_audiobooks(query, **kwargs)


async def search_by_author(author: str, **kwargs) -> List[SearchResult]:
    """Convenience function for author searches"""
    async with UnifiedSearchSystem() as search:
        return await search.search_by_author(author, **kwargs)


async def search_by_genre(genre: str, **kwargs) -> List[SearchResult]:
    """Convenience function for genre searches"""
    async with UnifiedSearchSystem() as search:
        return await search.search_by_genre(genre, **kwargs)


if __name__ == "__main__":
    # Example usage
    async def main():
        async with UnifiedSearchSystem() as search:
            print("Available providers:", search.get_available_providers())

            # Quick search example
            results = await search.search_audiobooks("Foundation Asimov", limit=5)
            print(f"Found {len(results)} results")

            for i, result in enumerate(results[:3], 1):
                print(f"{i}. {result.title} by {result.author} ({result.provider})")

    asyncio.run(main())