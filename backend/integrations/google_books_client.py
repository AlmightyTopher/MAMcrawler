"""
Google Books API Client

Provides async interface to Google Books API for metadata enrichment.
Includes rate limiting and caching to stay within free tier limits.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import asyncio

import aiohttp
from aiohttp import ClientTimeout, ClientError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)


class GoogleBooksError(Exception):
    """Base exception for Google Books client errors."""
    pass


class GoogleBooksRateLimitError(GoogleBooksError):
    """Rate limit exceeded."""
    pass


class GoogleBooksClient:
    """
    Async client for Google Books API.

    Handles search, metadata extraction, rate limiting, and caching.

    Free tier limits:
    - 1000 requests per day
    - 100 requests per 100 seconds

    Args:
        api_key: Google Books API key (optional, increases rate limits)
        timeout: Request timeout in seconds (default: 30)
        max_requests_per_day: Maximum daily requests (default: 900 to stay safe)

    Example:
        >>> async with GoogleBooksClient(api_key) as client:
        ...     results = await client.search("Foundation", author="Asimov")
        ...     metadata = await client.get_book_details(results[0]["id"])
    """

    BASE_URL = "https://www.googleapis.com/books/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_requests_per_day: int = 900,
    ):
        self.api_key = api_key
        self.timeout = ClientTimeout(total=timeout)
        self.max_requests_per_day = max_requests_per_day
        self.session: Optional[aiohttp.ClientSession] = None

        # Rate limiting tracking
        self._request_count = 0
        self._request_reset_time = datetime.now() + timedelta(days=1)
        self._last_request_time = datetime.now()
        self._min_request_interval = timedelta(seconds=1)  # 1 request per second

        # Simple in-memory cache
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = timedelta(hours=24)

        logger.info(
            f"Initialized GoogleBooksClient "
            f"(api_key={'set' if api_key else 'not set'}, "
            f"max_requests={max_requests_per_day})"
        )

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _ensure_session(self):
        """Ensure session is initialized."""
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

    def _check_rate_limit(self):
        """
        Check if rate limit allows request.

        Raises:
            GoogleBooksRateLimitError: If rate limit exceeded
        """
        now = datetime.now()

        # Reset daily counter if needed
        if now >= self._request_reset_time:
            logger.info("Resetting daily request counter")
            self._request_count = 0
            self._request_reset_time = now + timedelta(days=1)

        # Check daily limit
        if self._request_count >= self.max_requests_per_day:
            reset_in = self._request_reset_time - now
            logger.error(
                f"Daily rate limit exceeded ({self.max_requests_per_day} requests). "
                f"Resets in {reset_in}"
            )
            raise GoogleBooksRateLimitError(
                f"Daily rate limit exceeded. Resets in {reset_in}"
            )

        # Check minimum interval between requests
        time_since_last = now - self._last_request_time
        if time_since_last < self._min_request_interval:
            sleep_time = (self._min_request_interval - time_since_last).total_seconds()
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            return sleep_time

        return 0

    async def _rate_limited_sleep(self):
        """Sleep if needed to respect rate limits."""
        sleep_time = self._check_rate_limit()
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)

    def _increment_request_count(self):
        """Increment request counter and update last request time."""
        self._request_count += 1
        self._last_request_time = datetime.now()

        logger.debug(
            f"Request count: {self._request_count}/{self.max_requests_per_day} "
            f"(resets in {self._request_reset_time - datetime.now()})"
        )

    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get data from cache if not expired.

        Args:
            cache_key: Cache key

        Returns:
            Cached data or None if not found/expired
        """
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            age = datetime.now() - cached_time

            if age < self._cache_ttl:
                logger.debug(f"Cache hit: {cache_key} (age: {age})")
                return cached_data
            else:
                logger.debug(f"Cache expired: {cache_key} (age: {age})")
                del self._cache[cache_key]

        return None

    def _add_to_cache(self, cache_key: str, data: Dict[str, Any]):
        """
        Add data to cache.

        Args:
            cache_key: Cache key
            data: Data to cache
        """
        self._cache[cache_key] = (data, datetime.now())
        logger.debug(f"Cached: {cache_key}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ClientError, asyncio.TimeoutError)),
        reraise=True,
    )
    async def _request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            JSON response

        Raises:
            GoogleBooksError: On API errors
            GoogleBooksRateLimitError: On rate limit errors
        """
        await self._ensure_session()
        await self._rate_limited_sleep()

        url = f"{self.BASE_URL}{endpoint}"

        # Add API key if available
        if params is None:
            params = {}
        if self.api_key:
            params["key"] = self.api_key

        logger.debug(f"GET {url} - params: {params}")

        try:
            async with self.session.get(url, params=params) as response:
                # Increment counter before checking status
                self._increment_request_count()

                # Check for rate limit errors
                if response.status == 429:
                    logger.error("API rate limit exceeded (429)")
                    raise GoogleBooksRateLimitError("API rate limit exceeded")

                response.raise_for_status()

                data = await response.json()
                logger.debug(f"Response: {response.status}")
                return data

        except aiohttp.ClientResponseError as e:
            if e.status == 429:
                raise GoogleBooksRateLimitError("API rate limit exceeded")

            logger.error(f"API error: {e.status} - {e.message}")
            raise GoogleBooksError(f"API request failed: {e.status} {e.message}")

        except aiohttp.ClientError as e:
            logger.error(f"Client error: {str(e)}")
            raise GoogleBooksError(f"Request failed: {str(e)}")

        except asyncio.TimeoutError:
            logger.error(f"Request timeout for {url}")
            raise GoogleBooksError("Request timeout")

    async def search(
        self,
        title: str,
        author: Optional[str] = None,
        isbn: Optional[str] = None,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for books.

        Args:
            title: Book title
            author: Author name (optional)
            isbn: ISBN (optional, more accurate than title search)
            max_results: Maximum results to return (max 40)

        Returns:
            List of book result dictionaries

        Example:
            >>> results = await client.search("Foundation", author="Asimov")
            >>> for book in results:
            ...     print(f"{book['volumeInfo']['title']} by {book['volumeInfo']['authors']}")
        """
        # Check cache first
        cache_key = f"search:{title}:{author}:{isbn}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        # Build query
        query_parts = []

        if isbn:
            # ISBN search is most accurate
            query_parts.append(f"isbn:{isbn}")
            logger.info(f"Searching by ISBN: {isbn}")
        else:
            # Text search
            if title:
                query_parts.append(f'intitle:"{title}"')
            if author:
                query_parts.append(f'inauthor:"{author}"')

            logger.info(f"Searching for: {title}" + (f" by {author}" if author else ""))

        query = " ".join(query_parts)

        endpoint = "/volumes"
        params = {
            "q": query,
            "maxResults": min(max_results, 40),  # API max is 40
            "printType": "books",
        }

        try:
            response = await self._request(endpoint, params=params)
            items = response.get("items", [])

            logger.info(f"Found {len(items)} results")

            # Cache results
            self._add_to_cache(cache_key, items)

            return items

        except GoogleBooksError as e:
            logger.error(f"Search failed: {str(e)}")
            raise

    async def get_book_details(self, book_id: str) -> Dict[str, Any]:
        """
        Get full book details by ID.

        Args:
            book_id: Google Books volume ID

        Returns:
            Book details dictionary

        Example:
            >>> details = await client.get_book_details("abc123")
            >>> info = details["volumeInfo"]
            >>> print(f"Title: {info['title']}")
            >>> print(f"Published: {info['publishedDate']}")
        """
        # Check cache first
        cache_key = f"details:{book_id}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        logger.info(f"Getting details for book: {book_id}")

        endpoint = f"/volumes/{book_id}"

        try:
            details = await self._request(endpoint)
            logger.debug(f"Got details for: {details.get('volumeInfo', {}).get('title', 'Unknown')}")

            # Cache details
            self._add_to_cache(cache_key, details)

            return details

        except GoogleBooksError as e:
            logger.error(f"Failed to get book details: {str(e)}")
            raise

    def extract_metadata(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and normalize metadata from Google Books result.

        Args:
            result: Google Books API result

        Returns:
            Normalized metadata dictionary

        Example:
            >>> results = await client.search("Foundation")
            >>> metadata = client.extract_metadata(results[0])
            >>> print(metadata["title"])
            >>> print(metadata["authors"])
            >>> print(metadata["description"])
        """
        volume_info = result.get("volumeInfo", {})

        # Extract basic fields
        metadata = {
            "google_books_id": result.get("id"),
            "title": volume_info.get("title"),
            "subtitle": volume_info.get("subtitle"),
            "authors": volume_info.get("authors", []),
            "publisher": volume_info.get("publisher"),
            "published_date": volume_info.get("publishedDate"),
            "description": volume_info.get("description"),
            "isbn_10": None,
            "isbn_13": None,
            "page_count": volume_info.get("pageCount"),
            "categories": volume_info.get("categories", []),
            "language": volume_info.get("language"),
            "preview_link": volume_info.get("previewLink"),
            "info_link": volume_info.get("infoLink"),
            "thumbnail": None,
        }

        # Extract ISBNs
        identifiers = volume_info.get("industryIdentifiers", [])
        for identifier in identifiers:
            id_type = identifier.get("type")
            if id_type == "ISBN_10":
                metadata["isbn_10"] = identifier.get("identifier")
            elif id_type == "ISBN_13":
                metadata["isbn_13"] = identifier.get("identifier")

        # Extract best quality thumbnail
        image_links = volume_info.get("imageLinks", {})
        if image_links:
            # Try to get highest quality image
            for size in ["extraLarge", "large", "medium", "small", "thumbnail"]:
                if size in image_links:
                    metadata["thumbnail"] = image_links[size]
                    break

        # Format authors as comma-separated string
        if metadata["authors"]:
            metadata["authors_string"] = ", ".join(metadata["authors"])
        else:
            metadata["authors_string"] = None

        # Format categories as comma-separated string
        if metadata["categories"]:
            metadata["categories_string"] = ", ".join(metadata["categories"])
        else:
            metadata["categories_string"] = None

        logger.debug(
            f"Extracted metadata: {metadata['title']} "
            f"by {metadata.get('authors_string', 'Unknown')}"
        )

        return metadata

    async def search_and_extract(
        self,
        title: str,
        author: Optional[str] = None,
        isbn: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Search and extract metadata from best match.

        Convenience method that searches and returns extracted metadata
        from the first result.

        Args:
            title: Book title
            author: Author name (optional)
            isbn: ISBN (optional)

        Returns:
            Extracted metadata dictionary or None if no results

        Example:
            >>> metadata = await client.search_and_extract(
            ...     "Foundation",
            ...     author="Isaac Asimov"
            ... )
            >>> if metadata:
            ...     print(f"Found: {metadata['title']}")
        """
        logger.info(f"Search and extract: {title}" + (f" by {author}" if author else ""))

        try:
            results = await self.search(title=title, author=author, isbn=isbn, max_results=1)

            if not results:
                logger.warning("No results found")
                return None

            metadata = self.extract_metadata(results[0])
            return metadata

        except GoogleBooksError as e:
            logger.error(f"Search and extract failed: {str(e)}")
            return None

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get current rate limit status.

        Returns:
            Dictionary with rate limit info

        Example:
            >>> status = client.get_rate_limit_status()
            >>> print(f"Requests used: {status['requests_used']}/{status['max_requests']}")
            >>> print(f"Resets in: {status['reset_in']}")
        """
        now = datetime.now()
        reset_in = self._request_reset_time - now

        return {
            "requests_used": self._request_count,
            "max_requests": self.max_requests_per_day,
            "requests_remaining": self.max_requests_per_day - self._request_count,
            "reset_time": self._request_reset_time.isoformat(),
            "reset_in": str(reset_in),
        }

    def clear_cache(self):
        """Clear the in-memory cache."""
        logger.info(f"Clearing cache ({len(self._cache)} entries)")
        self._cache.clear()

    async def close(self):
        """Close client session."""
        if self.session:
            await self.session.close()
            self.session = None
