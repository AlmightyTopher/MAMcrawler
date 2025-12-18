"""
Prowlarr API Client

Provides async interface to Prowlarr indexer manager for searching torrents
across multiple indexers.
"""

import logging
from typing import Any, Dict, List, Optional
import asyncio
from datetime import datetime

import aiohttp
from aiohttp import ClientTimeout, ClientError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)


class ProwlarrError(Exception):
    """Base exception for Prowlarr client errors."""
    pass


class ProwlarrClient:
    """
    Async client for Prowlarr API.

    Handles indexer search, result parsing, and magnet link extraction.

    Args:
        base_url: Prowlarr server URL (e.g., "http://localhost:9696")
        api_key: Prowlarr API key
        timeout: Request timeout in seconds (default: 30)

    Example:
        >>> async with ProwlarrClient(url, api_key) as client:
        ...     results = await client.search("Foundation Asimov")
        ...     magnet = results[0]["magnetUrl"]
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None

        # Headers for all requests
        self.headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json",
        }

        logger.info(f"Initialized ProwlarrClient for {self.base_url}")

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            headers=self.headers,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _ensure_session(self):
        """Ensure session is initialized."""
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers=self.headers,
            )

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
            JSON response

        Raises:
            ProwlarrError: On API errors
        """
        await self._ensure_session()
        url = f"{self.base_url}{endpoint}"

        logger.debug(f"{method} {url}")

        try:
            async with self.session.request(method, url, **kwargs) as response:
                response.raise_for_status()

                data = await response.json()
                logger.debug(f"Response: {response.status}")
                return data

        except aiohttp.ClientResponseError as e:
            logger.error(f"API error: {e.status} - {e.message}")
            raise ProwlarrError(f"API request failed: {e.status} {e.message}")

        except aiohttp.ClientError as e:
            logger.error(f"Client error: {str(e)}")
            raise ProwlarrError(f"Request failed: {str(e)}")

        except asyncio.TimeoutError:
            logger.error(f"Request timeout for {url}")
            raise ProwlarrError("Request timeout")

    async def search(
        self,
        query: str,
        indexer_ids: Optional[List[int]] = None,
        categories: Optional[List[int]] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search all configured indexers.

        Args:
            query: Search query string
            indexer_ids: Optional list of specific indexer IDs to search
            categories: Optional list of category IDs (3000=Audio, 3010=Audiobook)
            limit: Maximum results to return (default: 50)

        Returns:
            List of search result dictionaries

        Example:
            >>> results = await client.search("Foundation Asimov")
            >>> for result in results[:5]:
            ...     print(f"{result['title']} - {result['seeders']} seeders")
        """
        logger.info(f"Searching for: {query}")

        endpoint = "/api/v1/search"
        params = {
            "query": query,
            "limit": limit,
            "type": "search",
        }

        if indexer_ids:
            params["indexerIds"] = ",".join(map(str, indexer_ids))

        if categories:
            # 3000 = Audio, 3010 = Audiobook
            params["categories"] = ",".join(map(str, categories))

        try:
            results = await self._request("GET", endpoint, params=params)

            logger.info(f"Found {len(results)} results")

            # Sort by seeders (descending)
            sorted_results = sorted(
                results,
                key=lambda x: x.get("seeders", 0),
                reverse=True,
            )

            return sorted_results

        except ProwlarrError as e:
            logger.error(f"Search failed: {str(e)}")
            raise

    async def search_by_genre(
        self,
        genre: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search by genre.

        Note: Genre search works best when included in the main query.
        This is a convenience wrapper around search().

        Args:
            genre: Genre to search for
            limit: Maximum results to return

        Returns:
            List of search result dictionaries

        Example:
            >>> results = await client.search_by_genre("Science Fiction")
        """
        logger.info(f"Searching by genre: {genre}")

        # Include genre in search query
        query = f"genre:{genre}"

        # Use audiobook category (3010)
        return await self.search(
            query=query,
            categories=[3010],  # Audiobook category
            limit=limit,
        )

    async def get_search_results(
        self,
        query: str,
        limit: int = 50,
        min_seeders: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Get detailed search results with filtering.

        Filters out results with no seeders and enriches data.

        Args:
            query: Search query
            limit: Maximum results to return
            min_seeders: Minimum number of seeders required

        Returns:
            List of enriched search result dictionaries

        Example:
            >>> results = await client.get_search_results(
            ...     "Foundation",
            ...     min_seeders=5
            ... )
            >>> best_result = results[0]
            >>> print(f"Title: {best_result['title']}")
            >>> print(f"Size: {best_result['size_gb']:.2f} GB")
            >>> print(f"Magnet: {best_result['magnetUrl']}")
        """
        logger.info(f"Getting search results for: {query} (min_seeders={min_seeders})")

        # Search all indexers with audiobook category
        results = await self.search(
            query=query,
            categories=[3010],  # Audiobook category
            limit=limit * 2,  # Get more to account for filtering
        )

        # Filter by seeders
        filtered_results = [
            r for r in results
            if r.get("seeders", 0) >= min_seeders
        ]

        logger.info(
            f"Filtered to {len(filtered_results)} results "
            f"(from {len(results)} total)"
        )

        # Enrich results with additional data
        enriched_results = []
        for result in filtered_results[:limit]:
            enriched = self._enrich_result(result)
            enriched_results.append(enriched)

        return enriched_results

    def _enrich_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich search result with computed fields.

        Args:
            result: Raw search result

        Returns:
            Enriched result dictionary
        """
        enriched = result.copy()

        # Add size in GB
        size_bytes = result.get("size", 0)
        enriched["size_gb"] = size_bytes / (1024 ** 3) if size_bytes else 0

        # Add age in days
        publish_date = result.get("publishDate")
        if publish_date:
            try:
                pub_dt = datetime.fromisoformat(publish_date.replace("Z", "+00:00"))
                age = (datetime.now(pub_dt.tzinfo) - pub_dt).days
                enriched["age_days"] = age
            except Exception as e:
                logger.debug(f"Failed to parse publish date: {e}")
                enriched["age_days"] = None

        # Add quality score (seeders * 10 - age_days)
        seeders = result.get("seeders", 0)
        age = enriched.get("age_days", 0) or 0
        enriched["quality_score"] = (seeders * 10) - age

        # Extract indexer name
        enriched["indexer_name"] = result.get("indexer", "Unknown")

        return enriched

    async def add_to_download_queue(
        self,
        result: Dict[str, Any],
    ) -> Optional[str]:
        """
        Extract magnet link from search result.

        Note: Prowlarr doesn't have a download queue - it's a search aggregator.
        This method simply extracts the magnet link for use with a download client.

        Args:
            result: Search result dictionary

        Returns:
            Magnet link URL or None if not found

        Example:
            >>> results = await client.search("Book Title")
            >>> magnet = await client.add_to_download_queue(results[0])
            >>> # Use magnet with qBittorrent, etc.
        """
        # Try different possible magnet link fields
        magnet_fields = ["magnetUrl", "downloadUrl", "link"]

        for field in magnet_fields:
            magnet = result.get(field)
            if magnet and magnet.startswith("magnet:"):
                logger.info(f"Extracted magnet link from field: {field}")
                logger.debug(f"Magnet: {magnet[:80]}...")
                return magnet

        # If no direct magnet, try to get download URL
        download_url = result.get("downloadUrl")
        if download_url:
            logger.warning(
                "No magnet link found, returning download URL. "
                "May require additional processing."
            )
            return download_url

        logger.warning("No magnet link or download URL found in result")
        return None

    async def get_indexers(self) -> List[Dict[str, Any]]:
        """
        Get all configured indexers.

        Returns:
            List of indexer configuration dictionaries

        Example:
            >>> indexers = await client.get_indexers()
            >>> for idx in indexers:
            ...     print(f"{idx['name']}: enabled={idx['enable']}")
        """
        logger.info("Getting indexers")

        endpoint = "/api/v1/indexer"

        try:
            indexers = await self._request("GET", endpoint)
            logger.info(f"Found {len(indexers)} indexers")

            # Log enabled indexers
            enabled = [idx for idx in indexers if idx.get("enable", False)]
            logger.info(f"{len(enabled)} indexers enabled")

            return indexers

        except ProwlarrError as e:
            logger.error(f"Failed to get indexers: {str(e)}")
            raise

    async def get_indexer_stats(self) -> Dict[str, Any]:
        """
        Get indexer statistics.

        Returns:
            Dictionary with indexer stats

        Example:
            >>> stats = await client.get_indexer_stats()
            >>> print(f"Total queries: {stats['totalQueries']}")
        """
        logger.info("Getting indexer stats")

        endpoint = "/api/v1/indexerstats"

        try:
            stats = await self._request("GET", endpoint)
            logger.debug(f"Stats: {stats}")
            return stats

        except ProwlarrError as e:
            logger.error(f"Failed to get indexer stats: {str(e)}")
            raise

    async def test_indexer(self, indexer_id: int) -> Dict[str, Any]:
        """
        Test specific indexer connection.

        Args:
            indexer_id: Indexer ID to test

        Returns:
            Test result dictionary

        Example:
            >>> result = await client.test_indexer(1)
            >>> if result.get("isValid"):
            ...     print("Indexer is working!")
        """
        logger.info(f"Testing indexer: {indexer_id}")

        endpoint = f"/api/v1/indexer/test/{indexer_id}"

        try:
            result = await self._request("POST", endpoint)
            is_valid = result.get("isValid", False)

            if is_valid:
                logger.info(f"Indexer {indexer_id} test passed")
            else:
                logger.warning(
                    f"Indexer {indexer_id} test failed: "
                    f"{result.get('validationFailures', [])}"
                )

            return result

        except ProwlarrError as e:
            logger.error(f"Failed to test indexer: {str(e)}")
            raise

    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get Prowlarr system status.

        Returns:
            System status dictionary

        Example:
            >>> status = await client.get_system_status()
            >>> print(f"Version: {status['version']}")
            >>> print(f"Started: {status['startTime']}")
        """
        logger.info("Getting system status")

        endpoint = "/api/v1/system/status"

        try:
            status = await self._request("GET", endpoint)
            logger.debug(
                f"Prowlarr {status.get('version', 'unknown')} - "
                f"OS: {status.get('osName', 'unknown')}"
            )
            return status

        except ProwlarrError as e:
            logger.error(f"Failed to get system status: {str(e)}")
            raise

    async def search_by_imdb_id(
        self,
        imdb_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search by IMDb ID.

        Args:
            imdb_id: IMDb ID (e.g., "tt1234567")
            limit: Maximum results to return

        Returns:
            List of search result dictionaries

        Example:
            >>> results = await client.search_by_imdb_id("tt0816692")
        """
        logger.info(f"Searching by IMDb ID: {imdb_id}")

        endpoint = "/api/v1/search"
        params = {
            "query": imdb_id,
            "type": "search",
            "limit": limit,
        }

        try:
            results = await self._request("GET", endpoint, params=params)
            logger.info(f"Found {len(results)} results for IMDb ID {imdb_id}")
            return results

        except ProwlarrError as e:
            logger.error(f"Search by IMDb ID failed: {str(e)}")
            raise

    async def add_release(self, title: str, download_url: str, indexer_id: int = -1) -> bool:
        """
        Manually add a release to Prowlarr (e.g. from external source).
        
        Args:
            title: Title of the release
            download_url: URL to download (magnet or http)
            indexer_id: Indexer ID (default -1 for Manual)
            
        Returns:
            True if successful
        """
        logger.info(f"Adding release to Prowlarr: {title}")
        endpoint = "/api/v1/search/grab"
        
        payload = {
            "title": title,
            "downloadUrl": download_url,
            "indexerId": indexer_id
        }
        
        try:
            # Note: /search/grab returns 200 OK on success
            await self._request("POST", endpoint, json=payload)
            logger.info(f"Successfully added release: {title}")
            return True
        except ProwlarrError as e:
            logger.error(f"Failed to add release: {e}")
            return False

    async def close(self):
        """Close client session."""
        if self.session:
            await self.session.close()
            self.session = None
