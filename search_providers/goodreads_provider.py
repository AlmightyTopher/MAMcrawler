#!/usr/bin/env python3
"""
Goodreads search provider for the unified search system.
Consolidates Goodreads metadata verification and search functionality.
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Any, Tuple

import aiohttp
from bs4 import BeautifulSoup

from search_types import SearchProviderInterface, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class GoodreadsSearchProvider(SearchProviderInterface):
    """
    Goodreads web scraping provider for metadata verification and search
    """

    PROVIDER_TYPE = "goodreads"
    CAPABILITIES = ["metadata_search", "author_search", "book_verification"]
    RATE_LIMITS = {"requests_per_minute": 30, "delay_seconds": 2}
    CONFIG_REQUIRED = []  # No authentication required for basic search

    BASE_URL = "https://www.goodreads.com"
    SEARCH_URL = f"{BASE_URL}/search"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.session = None

    async def __aenter__(self):
        """Context manager entry"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.session = aiohttp.ClientSession(headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            await self.session.close()

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Search Goodreads for books

        Args:
            query: Search query parameters

        Returns:
            List of search results
        """
        if not self.session:
            # Initialize session if not in context manager
            async with self:
                return await self._perform_search(query)

        return await self._perform_search(query)

    async def _perform_search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform the actual search"""
        results = []

        try:
            if query.author and not query.query:
                # Author-specific search
                results = await self._search_author_books(query.author, query.limit)
            else:
                # General book search
                search_term = query.query or f"{query.author or ''} {query.series or ''}".strip()
                if search_term:
                    results = await self._search_books(search_term, query.limit)

        except Exception as e:
            logger.error(f"Goodreads search error: {e}")
            return []

        return results

    async def _search_books(self, search_term: str, limit: int = 10) -> List[SearchResult]:
        """Search Goodreads for books by title/author"""
        logger.info(f"Searching Goodreads for: {search_term}")

        try:
            # Rate limiting
            await asyncio.sleep(self.RATE_LIMITS["delay_seconds"])

            # Construct search query
            params = {
                'q': search_term,
                'search_type': 'books'
            }

            async with self.session.get(self.SEARCH_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    logger.warning(f"Goodreads search failed with status {resp.status}")
                    return []

                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Find search results
                results = soup.find_all('tr', itemtype='http://schema.org/Book')

                if not results:
                    logger.info(f"No Goodreads results found for: {search_term}")
                    return []

                search_results = []
                for result_div in results[:limit]:
                    book_result = self._extract_book_from_search_result(result_div, search_term)
                    if book_result:
                        search_results.append(book_result)

                logger.info(f"Found {len(search_results)} Goodreads results for '{search_term}'")
                return search_results

        except asyncio.TimeoutError:
            logger.warning(f"Goodreads search timeout for: {search_term}")
            return []
        except Exception as e:
            logger.error(f"Error searching Goodreads: {e}")
            return []

    async def _search_author_books(self, author_name: str, limit: int = 10) -> List[SearchResult]:
        """Search Goodreads for books by a specific author"""
        logger.info(f"Searching Goodreads for author: {author_name}")

        try:
            # Rate limiting
            await asyncio.sleep(self.RATE_LIMITS["delay_seconds"])

            # Search for author first
            author_search_url = f"{self.SEARCH_URL}?q={author_name}&search_type=author"

            async with self.session.get(author_search_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    logger.warning(f"Goodreads author search failed with status {resp.status}")
                    return []

                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Find author link
                author_link = soup.find('a', class_='authorName')
                if not author_link:
                    logger.info(f"No author found for: {author_name}")
                    return []

                author_url = author_link.get('href')
                if author_url:
                    author_url = f"{self.BASE_URL}{author_url}"

                    # Get author's books page
                    books_url = f"{author_url}/books"
                    await asyncio.sleep(self.RATE_LIMITS["delay_seconds"])

                    async with self.session.get(books_url, timeout=aiohttp.ClientTimeout(total=15)) as books_resp:
                        if books_resp.status == 200:
                            books_html = await books_resp.text()
                            books_soup = BeautifulSoup(books_html, 'html.parser')

                            # Extract books from author page
                            book_links = books_soup.find_all('a', class_='bookTitle')
                            results = []

                            for book_link in book_links[:limit]:
                                title = book_link.get_text(strip=True)
                                book_url = book_link.get('href')
                                if book_url:
                                    book_url = f"{self.BASE_URL}{book_url}"

                                # Parse series from title
                                parsed_title, series_name, series_position = self._parse_series_from_title(title)

                                result = SearchResult(
                                    provider=self.PROVIDER_TYPE,
                                    query=author_name,
                                    title=parsed_title,
                                    author=author_name,
                                    series_name=series_name,
                                    series_position=series_position,
                                    url=book_url,
                                    confidence=0.8  # High confidence for author page results
                                )

                                results.append(result)

                            logger.info(f"Found {len(results)} books for author {author_name}")
                            return results

        except Exception as e:
            logger.error(f"Error searching Goodreads for author {author_name}: {e}")
            return []

        return []

    def _extract_book_from_search_result(self, book_div, search_term: str) -> Optional[SearchResult]:
        """Extract book metadata from Goodreads search result HTML"""
        try:
            # Find title link
            title_link = book_div.find('a', class_='bookTitle')
            if not title_link:
                return None

            full_title = title_link.get_text(strip=True)
            book_url = title_link.get('href', '')
            if book_url:
                book_url = f"{self.BASE_URL}{book_url}"

            # Parse series from title
            title, series_name, series_position = self._parse_series_from_title(full_title)

            # Find author
            author_link = book_div.find('a', class_='authorName')
            author = author_link.get_text(strip=True) if author_link else "Unknown"

            # Calculate confidence based on search term match
            confidence = self._calculate_confidence(search_term, title, author)

            return SearchResult(
                provider=self.PROVIDER_TYPE,
                query=search_term,
                title=title,
                author=author,
                series_name=series_name,
                series_position=series_position,
                url=book_url,
                confidence=confidence
            )

        except Exception as e:
            logger.warning(f"Error parsing search result: {e}")
            return None

    def _parse_series_from_title(self, full_title: str) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Parse series information from Goodreads title

        Examples:
        - "The Name of the Wind (The Kingkiller Chronicle, #1)" -> ("The Name of the Wind", "The Kingkiller Chronicle", "1")
        - "Harry Potter and the Sorcerer's Stone (Harry Potter, #1)" -> ("Harry Potter...", "Harry Potter", "1")
        """
        # Pattern: Title (Series Name, #Number)
        match = re.search(r'^(.*?)\s*\((.*?),?\s*#(\d+\.?\d*)\)\s*$', full_title)
        if match:
            title = match.group(1).strip()
            series = match.group(2).strip()
            position = match.group(3).strip()
            return title, series, position

        # Pattern: Title (Series Name #Number)
        match = re.search(r'^(.*?)\s*\((.*?)\s+#(\d+\.?\d*)\)\s*$', full_title)
        if match:
            title = match.group(1).strip()
            series = match.group(2).strip()
            position = match.group(3).strip()
            return title, series, position

        return full_title.strip(), None, None

    def _calculate_confidence(self, search_term: str, title: str, author: str) -> float:
        """Calculate confidence score for search result"""
        confidence = 0.0

        # Normalize search term and result
        search_lower = search_term.lower()
        title_lower = title.lower()
        author_lower = author.lower()

        # Title match (highest weight)
        if search_lower in title_lower:
            confidence += 0.6
        elif any(word in title_lower for word in search_lower.split()):
            confidence += 0.4

        # Author match
        if search_lower in author_lower:
            confidence += 0.3
        elif any(word in author_lower for word in search_lower.split()):
            confidence += 0.2

        # Exact matches get bonus
        if search_lower == title_lower:
            confidence += 0.1
        if search_lower == author_lower:
            confidence += 0.1

        return min(confidence, 1.0)  # Cap at 1.0

    async def health_check(self) -> bool:
        """Check if Goodreads is accessible"""
        try:
            async with self.session.get(self.BASE_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"Goodreads health check error: {e}")
            return False