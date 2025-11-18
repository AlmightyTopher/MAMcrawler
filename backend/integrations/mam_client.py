"""
MyAnonamouse (MAM) Client
Async client for interacting with MAM torrent tracker
"""

import asyncio
import logging
import random
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin, quote_plus

import aiohttp
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from backend.config import get_settings

logger = logging.getLogger(__name__)


class MAMError(Exception):
    """Base exception for MAM client errors"""
    pass


class MAMAuthError(MAMError):
    """Authentication error with MAM"""
    pass


class MAMRateLimitError(MAMError):
    """Rate limit exceeded on MAM"""
    pass


class MAMClient:
    """
    Async client for MyAnonamouse operations

    Provides methods for:
        - Authentication with session management
        - Searching for audiobooks
        - Getting torrent details
        - Downloading .torrent files or magnet links

    Usage:
        >>> client = MAMClient()
        >>> await client.login(username, password)
        >>> results = await client.search("Brandon Sanderson Mistborn")
        >>> await client.close()
    """

    BASE_URL = "https://www.myanonamouse.net"

    # User agents for rotation
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.76",
    ]

    def __init__(self):
        """Initialize MAM client"""
        settings = get_settings()

        self.session: Optional[aiohttp.ClientSession] = None
        self.authenticated = False
        self.session_expiry: Optional[datetime] = None
        self.last_request_time: Optional[datetime] = None

        # Configuration
        self.rate_limit_seconds = getattr(settings, 'MAM_RATE_LIMIT_SECONDS', 5.0)
        self.timeout = aiohttp.ClientTimeout(total=getattr(settings, 'MAM_TIMEOUT', 30))
        self.max_retries = getattr(settings, 'MAM_MAX_RETRIES', 3)
        self.session_duration_hours = 2  # MAM sessions typically last 2 hours

        self._user_agent = random.choice(self.USER_AGENTS)

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers=self._get_headers()
            )
        return self.session

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        return {
            "User-Agent": self._user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    async def _rate_limit(self) -> None:
        """Apply rate limiting between requests"""
        if self.last_request_time:
            elapsed = (datetime.now() - self.last_request_time).total_seconds()
            if elapsed < self.rate_limit_seconds:
                # Add random jitter for more natural behavior
                delay = self.rate_limit_seconds - elapsed + random.uniform(0.5, 2.0)
                logger.debug(f"Rate limiting: waiting {delay:.2f}s")
                await asyncio.sleep(delay)

        self.last_request_time = datetime.now()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
    )
    async def _make_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """
        Make HTTP request with rate limiting and retries

        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional arguments for aiohttp

        Returns:
            aiohttp.ClientResponse

        Raises:
            MAMError: If request fails
        """
        await self._rate_limit()

        session = await self._get_session()
        full_url = urljoin(self.BASE_URL, url)

        try:
            async with session.request(method, full_url, **kwargs) as response:
                if response.status == 429:
                    raise MAMRateLimitError("Rate limited by MAM")
                elif response.status == 403:
                    self.authenticated = False
                    raise MAMAuthError("Session expired or invalid")
                elif response.status >= 400:
                    text = await response.text()
                    raise MAMError(f"Request failed: {response.status} - {text[:200]}")

                # Return text content
                return await response.text()

        except aiohttp.ClientError as e:
            logger.error(f"Request error: {e}")
            raise

    async def login(self, username: str, password: str) -> bool:
        """
        Authenticate with MAM

        Args:
            username: MAM username
            password: MAM password

        Returns:
            True if login successful

        Raises:
            MAMAuthError: If login fails
        """
        logger.info(f"Logging in to MAM as {username}")

        try:
            session = await self._get_session()

            # Get login page for any tokens
            await self._rate_limit()
            async with session.get(f"{self.BASE_URL}/login.php") as response:
                if response.status != 200:
                    raise MAMAuthError("Failed to load login page")

            # Perform login
            await self._rate_limit()
            login_data = {
                "username": username,
                "password": password,
            }

            async with session.post(
                f"{self.BASE_URL}/takelogin.php",
                data=login_data,
                allow_redirects=True
            ) as response:
                text = await response.text()

                # Check for successful login indicators
                if "logout" in text.lower() or "my account" in text.lower():
                    self.authenticated = True
                    self.session_expiry = datetime.now() + timedelta(
                        hours=self.session_duration_hours
                    )
                    logger.info("MAM login successful")
                    return True
                else:
                    raise MAMAuthError("Login failed - invalid credentials or captcha required")

        except MAMAuthError:
            raise
        except Exception as e:
            logger.error(f"Login error: {e}")
            raise MAMAuthError(f"Login failed: {e}")

    async def _ensure_authenticated(self) -> None:
        """Ensure session is authenticated and not expired"""
        if not self.authenticated:
            raise MAMAuthError("Not authenticated - call login() first")

        if self.session_expiry and datetime.now() >= self.session_expiry:
            self.authenticated = False
            raise MAMAuthError("Session expired - need to re-authenticate")

    async def search(
        self,
        query: str,
        category: str = "audiobooks",
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search MAM for audiobooks

        Args:
            query: Search query
            category: Category to search (default: audiobooks)
            max_results: Maximum results to return

        Returns:
            List of search results with torrent details

        Raises:
            MAMAuthError: If not authenticated
            MAMError: If search fails
        """
        await self._ensure_authenticated()

        logger.info(f"Searching MAM for: {query}")

        try:
            # Build search URL
            encoded_query = quote_plus(query)
            search_url = f"/tor/browse.php?search={encoded_query}&cat=39"  # 39 = Audiobooks

            html = await self._make_request("GET", search_url)
            soup = BeautifulSoup(html, 'lxml')

            results = []

            # Parse search results table
            rows = soup.select("table#torrentTable tbody tr")

            for row in rows[:max_results]:
                try:
                    result = self._parse_search_result(row)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.warning(f"Error parsing search result: {e}")
                    continue

            logger.info(f"Found {len(results)} results for '{query}'")
            return results

        except MAMError:
            raise
        except Exception as e:
            logger.error(f"Search error: {e}")
            raise MAMError(f"Search failed: {e}")

    def _parse_search_result(self, row) -> Optional[Dict[str, Any]]:
        """
        Parse a single search result row

        Args:
            row: BeautifulSoup element for table row

        Returns:
            Dict with torrent details or None
        """
        try:
            # Extract title and link
            title_elem = row.select_one("td.tName a")
            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)
            torrent_url = title_elem.get("href", "")

            # Extract torrent ID
            torrent_id = None
            if "/t/" in torrent_url:
                match = re.search(r"/t/(\d+)", torrent_url)
                if match:
                    torrent_id = match.group(1)

            # Extract size
            size_elem = row.select_one("td.tSize")
            size = size_elem.get_text(strip=True) if size_elem else "Unknown"

            # Extract seeders/leechers
            seeders_elem = row.select_one("td.tSeeders")
            seeders = int(seeders_elem.get_text(strip=True)) if seeders_elem else 0

            leechers_elem = row.select_one("td.tLeechers")
            leechers = int(leechers_elem.get_text(strip=True)) if leechers_elem else 0

            # Extract author if available
            author_elem = row.select_one("td.tName span.author")
            author = author_elem.get_text(strip=True) if author_elem else None

            return {
                "torrent_id": torrent_id,
                "title": title,
                "author": author,
                "url": torrent_url,
                "size": size,
                "seeders": seeders,
                "leechers": leechers,
            }

        except Exception as e:
            logger.debug(f"Error parsing result: {e}")
            return None

    async def get_torrent_details(self, torrent_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a torrent

        Args:
            torrent_id: MAM torrent ID

        Returns:
            Dict with torrent details

        Raises:
            MAMError: If request fails
        """
        await self._ensure_authenticated()

        logger.info(f"Getting details for torrent: {torrent_id}")

        try:
            html = await self._make_request("GET", f"/t/{torrent_id}")
            soup = BeautifulSoup(html, 'lxml')

            # Extract details
            details = {
                "torrent_id": torrent_id,
                "title": None,
                "author": None,
                "narrator": None,
                "series": None,
                "series_number": None,
                "description": None,
                "download_url": None,
            }

            # Title
            title_elem = soup.select_one("h1.tTitle")
            if title_elem:
                details["title"] = title_elem.get_text(strip=True)

            # Download link
            download_elem = soup.select_one("a[href*='/tor/download.php']")
            if download_elem:
                details["download_url"] = download_elem.get("href")

            # Author (from metadata table)
            for row in soup.select("tr"):
                label = row.select_one("td.rowhead")
                value = row.select_one("td.row1")
                if label and value:
                    label_text = label.get_text(strip=True).lower()
                    value_text = value.get_text(strip=True)

                    if "author" in label_text:
                        details["author"] = value_text
                    elif "narrator" in label_text:
                        details["narrator"] = value_text
                    elif "series" in label_text:
                        details["series"] = value_text

            return details

        except MAMError:
            raise
        except Exception as e:
            logger.error(f"Error getting torrent details: {e}")
            raise MAMError(f"Failed to get torrent details: {e}")

    async def get_download_link(self, torrent_id: str) -> str:
        """
        Get .torrent download URL for a torrent

        Args:
            torrent_id: MAM torrent ID

        Returns:
            Download URL for .torrent file

        Raises:
            MAMError: If request fails
        """
        details = await self.get_torrent_details(torrent_id)
        download_url = details.get("download_url")

        if not download_url:
            raise MAMError(f"No download link found for torrent {torrent_id}")

        return urljoin(self.BASE_URL, download_url)

    async def close(self) -> None:
        """Close the client session"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.debug("MAM client session closed")

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
