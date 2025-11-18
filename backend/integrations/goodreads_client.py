"""
Goodreads Web Scraper Client

Provides async interface to scrape Goodreads for:
- Series book lists
- Author book lists
- Book metadata

Note: Goodreads has no official API, so this uses web scraping.
Rate limiting is critical to avoid IP bans.
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urljoin

import aiohttp
from aiohttp import ClientTimeout, ClientError
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from backend.config import get_settings

logger = logging.getLogger(__name__)


class GoodreadsError(Exception):
    """Base exception for Goodreads client errors."""
    pass


class GoodreadsClient:
    """
    Async client for scraping Goodreads data.

    Handles rate limiting, retries, and HTML parsing for all
    Goodreads operations.

    Example:
        >>> async with GoodreadsClient() as client:
        ...     books = await client.get_series_books("The Expanse", "James S.A. Corey")
        ...     author_books = await client.get_author_books("Brandon Sanderson")
    """

    BASE_URL = "https://www.goodreads.com"

    def __init__(
        self,
        timeout: int = 30,
        rate_limit_seconds: float = 3.0,
        max_retries: int = 3,
    ):
        """
        Initialize Goodreads client.

        Args:
            timeout: Request timeout in seconds
            rate_limit_seconds: Minimum delay between requests
            max_retries: Maximum retry attempts for failed requests
        """
        settings = get_settings()

        self.timeout = ClientTimeout(total=timeout)
        self.rate_limit_seconds = getattr(
            settings, 'GOODREADS_RATE_LIMIT_SECONDS', rate_limit_seconds
        )
        self.max_retries = max_retries
        self.session: Optional[aiohttp.ClientSession] = None
        self._last_request_time: float = 0

        # Headers to mimic browser
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        logger.info(
            f"GoodreadsClient initialized - rate_limit: {self.rate_limit_seconds}s"
        )

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

    async def _rate_limit(self):
        """Apply rate limiting between requests."""
        import time
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.rate_limit_seconds:
            delay = self.rate_limit_seconds - elapsed
            logger.debug(f"Rate limiting: waiting {delay:.2f}s")
            await asyncio.sleep(delay)
        self._last_request_time = time.time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ClientError, asyncio.TimeoutError)),
        reraise=True,
    )
    async def _make_request(self, url: str) -> str:
        """
        Make rate-limited HTTP request.

        Args:
            url: URL to fetch

        Returns:
            HTML content as string

        Raises:
            GoodreadsError: On request failure
        """
        await self._ensure_session()
        await self._rate_limit()

        logger.debug(f"GET {url}")

        try:
            async with self.session.get(url) as response:
                if response.status == 404:
                    raise GoodreadsError(f"Not found: {url}")
                response.raise_for_status()
                html = await response.text()
                logger.debug(f"Response: {response.status}, {len(html)} bytes")
                return html

        except aiohttp.ClientResponseError as e:
            logger.error(f"Goodreads error: {e.status} - {e.message}")
            raise GoodreadsError(f"Request failed: {e.status} {e.message}")
        except aiohttp.ClientError as e:
            logger.error(f"Client error: {str(e)}")
            raise GoodreadsError(f"Request failed: {str(e)}")
        except asyncio.TimeoutError:
            logger.error(f"Request timeout for {url}")
            raise GoodreadsError("Request timeout")

    async def get_series_books(
        self,
        series_name: str,
        author: str
    ) -> List[Dict[str, Any]]:
        """
        Get all books in a series.

        Args:
            series_name: Name of the series
            author: Author name (for disambiguation)

        Returns:
            List of book dictionaries with keys:
            - title, author, series_number, goodreads_id, goodreads_url
        """
        logger.info(f"Getting series books: {series_name} by {author}")

        # Search for series
        search_query = quote_plus(f"{series_name} {author}")
        search_url = f"{self.BASE_URL}/search?q={search_query}&search_type=series"

        html = await self._make_request(search_url)
        soup = BeautifulSoup(html, 'lxml')

        books = []

        # Find series link from search results
        series_links = soup.select('a.bookTitle, a[href*="/series/"]')

        for link in series_links:
            href = link.get('href', '')
            if '/series/' in href:
                series_url = urljoin(self.BASE_URL, href)
                books = await self._parse_series_page(series_url)
                break

        logger.info(f"Found {len(books)} books in series '{series_name}'")
        return books

    async def _parse_series_page(self, series_url: str) -> List[Dict[str, Any]]:
        """Parse a Goodreads series page for all books."""
        html = await self._make_request(series_url)
        soup = BeautifulSoup(html, 'lxml')

        books = []

        # Find book entries in series
        book_entries = soup.select('.listWithDividers__item, .seriesBookRow')

        for entry in book_entries:
            try:
                title_elem = entry.select_one('.bookTitle, a[href*="/book/show/"]')
                author_elem = entry.select_one('.authorName, a[href*="/author/show/"]')
                number_elem = entry.select_one('.seriesBookNumber, .gr-metaText')

                if not title_elem:
                    continue

                book = {
                    'title': title_elem.get_text(strip=True),
                    'author': author_elem.get_text(strip=True) if author_elem else '',
                    'series_number': '',
                    'goodreads_id': '',
                    'goodreads_url': '',
                }

                # Extract series number
                if number_elem:
                    number_text = number_elem.get_text(strip=True)
                    match = re.search(r'#?(\d+(?:\.\d+)?)', number_text)
                    if match:
                        book['series_number'] = match.group(1)

                # Extract Goodreads ID from URL
                href = title_elem.get('href', '')
                if href:
                    book['goodreads_url'] = urljoin(self.BASE_URL, href)
                    id_match = re.search(r'/book/show/(\d+)', href)
                    if id_match:
                        book['goodreads_id'] = id_match.group(1)

                books.append(book)

            except Exception as e:
                logger.warning(f"Error parsing book entry: {e}")
                continue

        return books

    async def get_author_books(
        self,
        author_name: str,
        audiobooks_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all books by an author.

        Args:
            author_name: Author name to search
            audiobooks_only: If True, filter to audiobooks only

        Returns:
            List of book dictionaries
        """
        logger.info(f"Getting author books: {author_name}")

        # Search for author
        search_query = quote_plus(author_name)
        search_url = f"{self.BASE_URL}/search?q={search_query}&search_type=authors"

        html = await self._make_request(search_url)
        soup = BeautifulSoup(html, 'lxml')

        books = []

        # Find author page link
        author_links = soup.select('a[href*="/author/show/"]')

        for link in author_links:
            href = link.get('href', '')
            if '/author/show/' in href:
                author_url = urljoin(self.BASE_URL, href)
                books = await self._parse_author_page(author_url)
                break

        logger.info(f"Found {len(books)} books by '{author_name}'")
        return books

    async def _parse_author_page(self, author_url: str) -> List[Dict[str, Any]]:
        """Parse a Goodreads author page for all books."""
        html = await self._make_request(author_url)
        soup = BeautifulSoup(html, 'lxml')

        books = []

        # Find book entries
        book_entries = soup.select('.bookRow, tr[itemtype*="Book"]')

        for entry in book_entries:
            try:
                title_elem = entry.select_one('.bookTitle, a[href*="/book/show/"]')

                if not title_elem:
                    continue

                book = {
                    'title': title_elem.get_text(strip=True),
                    'author': '',
                    'goodreads_id': '',
                    'goodreads_url': '',
                }

                # Extract Goodreads ID from URL
                href = title_elem.get('href', '')
                if href:
                    book['goodreads_url'] = urljoin(self.BASE_URL, href)
                    id_match = re.search(r'/book/show/(\d+)', href)
                    if id_match:
                        book['goodreads_id'] = id_match.group(1)

                books.append(book)

            except Exception as e:
                logger.warning(f"Error parsing book entry: {e}")
                continue

        return books

    async def search_book(
        self,
        title: str,
        author: str
    ) -> Optional[Dict[str, Any]]:
        """
        Search for a specific book.

        Args:
            title: Book title
            author: Author name

        Returns:
            Book metadata dict or None if not found
        """
        logger.info(f"Searching book: {title} by {author}")

        search_query = quote_plus(f"{title} {author}")
        search_url = f"{self.BASE_URL}/search?q={search_query}"

        html = await self._make_request(search_url)
        soup = BeautifulSoup(html, 'lxml')

        # Get first result
        first_result = soup.select_one('tr[itemtype*="Book"], .bookRow')

        if not first_result:
            logger.info(f"No results found for '{title}'")
            return None

        title_elem = first_result.select_one('.bookTitle, a[href*="/book/show/"]')

        if not title_elem:
            return None

        return {
            'title': title_elem.get_text(strip=True),
            'goodreads_url': urljoin(self.BASE_URL, title_elem.get('href', '')),
        }

    async def close(self):
        """Close client session."""
        if self.session:
            await self.session.close()
            self.session = None
