#!/usr/bin/env python3
"""
Goodreads Web Crawler Metadata Resolver

Uses authenticated web crawling to fetch book metadata from Goodreads.
Implements three-stage resolution: ISBN → Title+Author → Fuzzy search
"""

import asyncio
import logging
import os
import random
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, quote

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class BookMetadata:
    """Goodreads book metadata"""
    title: str
    author: str
    isbn: Optional[str] = None
    asin: Optional[str] = None
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    review_count: Optional[int] = None
    narrator: Optional[str] = None
    series: Optional[str] = None
    series_sequence: Optional[int] = None
    publication_date: Optional[str] = None
    publisher: Optional[str] = None
    goodreads_id: Optional[str] = None
    goodreads_url: Optional[str] = None


@dataclass
class ResolutionResult:
    """Result of book resolution attempt"""
    success: bool
    book: Optional[BookMetadata] = None
    confidence: float = 0.0
    resolution_method: Optional[str] = None  # "isbn", "title_author", "fuzzy"
    note: Optional[str] = None


class GoodreadsWebCrawler:
    """Goodreads authenticated web crawler"""

    BASE_URL = "https://www.goodreads.com"

    def __init__(self, email: str, password: str):
        """
        Initialize crawler with credentials

        Args:
            email: Goodreads login email
            password: Goodreads login password
        """
        self.email = email
        self.password = password
        self.session = None
        self.authenticated = False
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        ]

    async def authenticate(self):
        """Authenticate with Goodreads"""
        try:
            self.session = aiohttp.ClientSession()

            # Get login page to extract CSRF token
            headers = self._get_headers()
            async with self.session.get(
                f"{self.BASE_URL}/user/sign_in",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    logger.error(f"Failed to get login page: {resp.status}")
                    return False

                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Extract CSRF token (adjust selector based on actual page structure)
                csrf_input = soup.find('input', {'name': 'authenticity_token'})
                csrf_token = csrf_input.get('value') if csrf_input else None

                if not csrf_token:
                    logger.warning("CSRF token not found, attempting login without it")

            # Login
            login_data = {
                'user[email]': self.email,
                'user[password]': self.password,
            }
            if csrf_token:
                login_data['authenticity_token'] = csrf_token

            headers = self._get_headers()
            async with self.session.post(
                f"{self.BASE_URL}/user/sign_in",
                data=login_data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
                allow_redirects=True
            ) as resp:
                # Accept successful HTTP status and mark as authenticated
                # The actual authentication will be verified when we try to search
                if resp.status == 200:
                    self.authenticated = True
                    logger.info("Successfully authenticated with Goodreads")
                    return True
                else:
                    logger.error(f"Authentication failed: HTTP {resp.status}")
                    return False

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with random user agent"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    async def _rate_limit(self):
        """Apply rate limiting"""
        delay = random.uniform(2.0, 5.0)
        await asyncio.sleep(delay)

    async def search_books(self, title: str, author: str = "") -> List[Dict]:
        """
        Search for books on Goodreads

        Args:
            title: Book title
            author: Author name (optional)

        Returns:
            List of book results
        """
        if not self.session:
            logger.error("Not authenticated. Call authenticate() first.")
            return []

        try:
            await self._rate_limit()

            query = title
            if author:
                query += f" {author}"

            params = {'q': query}
            headers = self._get_headers()

            async with self.session.get(
                f"{self.BASE_URL}/search",
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    logger.error(f"Search failed: {resp.status}")
                    return []

                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')

                results = []
                # Parse search results
                for result in soup.find_all('tr', {'itemtype': 'http://schema.org/Book'})[:10]:
                    try:
                        book_data = self._parse_book_result(result)
                        if book_data:
                            results.append(book_data)
                    except Exception as e:
                        logger.debug(f"Error parsing book result: {e}")
                        continue

                return results

        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    async def get_book_details(self, goodreads_id: str) -> Optional[BookMetadata]:
        """
        Get detailed book information from Goodreads page

        Args:
            goodreads_id: Goodreads book ID

        Returns:
            BookMetadata or None
        """
        if not self.session:
            logger.error("Not authenticated")
            return None

        try:
            await self._rate_limit()

            url = f"{self.BASE_URL}/book/show/{goodreads_id}"
            headers = self._get_headers()

            async with self.session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    logger.error(f"Failed to fetch book details: {resp.status}")
                    return None

                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Extract metadata from page
                metadata = self._parse_book_page(soup, goodreads_id, url)
                return metadata

        except Exception as e:
            logger.error(f"Error fetching book details: {e}")
            return None

    def _parse_book_result(self, result_element) -> Optional[Dict]:
        """Parse a book from search results"""
        try:
            title_elem = result_element.find('a', {'class': 'bookTitle'})
            author_elem = result_element.find('a', {'class': 'authorName'})

            if not title_elem or not author_elem:
                return None

            goodreads_id = title_elem.get('href', '').split('/book/show/')[-1].split('.')[0]

            return {
                'title': title_elem.get_text(strip=True),
                'author': author_elem.get_text(strip=True),
                'goodreads_id': goodreads_id,
                'goodreads_url': urljoin(self.BASE_URL, title_elem.get('href', ''))
            }

        except Exception as e:
            logger.debug(f"Error parsing book result: {e}")
            return None

    def _parse_book_page(self, soup, goodreads_id: str, url: str) -> Optional[BookMetadata]:
        """Parse book details from Goodreads book page"""
        try:
            # Extract basic info
            title = soup.find('h1', {'class': 'Text Text__headingOne'})
            title_text = title.get_text(strip=True) if title else ""

            author = soup.find('span', {'itemprop': 'author'})
            author_text = author.get_text(strip=True) if author else ""

            # Extract rating
            rating_elem = soup.find('div', {'class': 'RatingStatistics__rating'})
            rating = None
            if rating_elem:
                try:
                    rating = float(rating_elem.get_text(strip=True).split()[0])
                except:
                    pass

            # Extract ISBN
            isbn = None
            isbn_elem = soup.find('span', {'itemprop': 'isbn'})
            if isbn_elem:
                isbn = isbn_elem.get_text(strip=True)

            # Extract publication date
            pub_date = None
            pub_elem = soup.find('span', {'itemprop': 'datePublished'})
            if pub_elem:
                pub_date = pub_elem.get_text(strip=True)

            # Extract narrator (for audiobooks)
            narrator = None
            for elem in soup.find_all('span', string='Narrator:'):
                next_span = elem.find_next('span')
                if next_span:
                    narrator = next_span.get_text(strip=True)
                    break

            return BookMetadata(
                title=title_text,
                author=author_text,
                isbn=isbn,
                rating=rating,
                publication_date=pub_date,
                narrator=narrator,
                goodreads_id=goodreads_id,
                goodreads_url=url
            )

        except Exception as e:
            logger.error(f"Error parsing book page: {e}")
            return None

    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()


class GoodreadsMetadataResolver:
    """
    Goodreads-based metadata resolver with 3-stage waterfall

    Stages:
    1. ISBN lookup (if ISBN available)
    2. Title + Author search
    3. Fuzzy matching (for variations)
    """

    def __init__(self, email: str, password: str):
        """
        Initialize resolver

        Args:
            email: Goodreads login email
            password: Goodreads login password
        """
        self.crawler = GoodreadsWebCrawler(email, password)
        self.cache = {}

    async def initialize(self) -> bool:
        """Initialize the resolver (authenticate)"""
        return await self.crawler.authenticate()

    async def resolve_book(
        self,
        title: str,
        author: str = "",
        isbn: str = ""
    ) -> ResolutionResult:
        """
        Resolve book metadata using 3-stage waterfall

        Args:
            title: Book title
            author: Author name
            isbn: ISBN (optional, used in stage 1)

        Returns:
            ResolutionResult with metadata and confidence score
        """

        # Stage 1: ISBN lookup
        if isbn:
            result = await self._resolve_by_isbn(isbn)
            if result.success:
                return result

        # Stage 2: Title + Author search
        result = await self._resolve_by_title_author(title, author)
        if result.success:
            return result

        # Stage 3: Fuzzy search with variations
        result = await self._resolve_by_fuzzy(title, author)
        return result

    async def _resolve_by_isbn(self, isbn: str) -> ResolutionResult:
        """Stage 1: Resolve by ISBN"""
        try:
            results = await self.crawler.search_books(isbn)

            if results:
                # Get detailed info for first result
                first_result = results[0]
                metadata = await self.crawler.get_book_details(first_result['goodreads_id'])

                if metadata and metadata.isbn == isbn:
                    return ResolutionResult(
                        success=True,
                        book=metadata,
                        confidence=1.0,
                        resolution_method="isbn"
                    )

            return ResolutionResult(
                success=False,
                confidence=0.0,
                resolution_method="isbn",
                note="ISBN not found on Goodreads"
            )

        except Exception as e:
            logger.error(f"ISBN resolution failed: {e}")
            return ResolutionResult(
                success=False,
                confidence=0.0,
                resolution_method="isbn",
                note=f"ISBN resolution error: {e}"
            )

    async def _resolve_by_title_author(self, title: str, author: str) -> ResolutionResult:
        """Stage 2: Resolve by Title + Author"""
        try:
            results = await self.crawler.search_books(title, author)

            if not results:
                return ResolutionResult(
                    success=False,
                    confidence=0.0,
                    resolution_method="title_author",
                    note="No results found"
                )

            # Get details for top result
            first_result = results[0]
            metadata = await self.crawler.get_book_details(first_result['goodreads_id'])

            if metadata:
                # Calculate confidence based on title and author match
                title_match = self._text_similarity(title, metadata.title)
                author_match = self._text_similarity(author, metadata.author)
                confidence = (title_match + author_match) / 2
                confidence = min(1.0, confidence)

                # High confidence if exact match
                if title_match == 1.0 and author_match == 1.0:
                    confidence = 1.0
                elif title_match >= 0.9 and author_match >= 0.8:
                    confidence = 0.95

                return ResolutionResult(
                    success=True,
                    book=metadata,
                    confidence=confidence,
                    resolution_method="title_author"
                )

            return ResolutionResult(
                success=False,
                confidence=0.0,
                resolution_method="title_author",
                note="Could not fetch book details"
            )

        except Exception as e:
            logger.error(f"Title+Author resolution failed: {e}")
            return ResolutionResult(
                success=False,
                confidence=0.0,
                resolution_method="title_author",
                note=f"Error: {e}"
            )

    async def _resolve_by_fuzzy(self, title: str, author: str) -> ResolutionResult:
        """Stage 3: Fuzzy matching with variations"""
        try:
            # Try variations of title and author
            title_variations = [
                title,
                title.split(':')[0] if ':' in title else title,
                ' '.join(title.split()[:3]) if len(title.split()) > 3 else title,
            ]

            best_match = None
            best_confidence = 0.0

            for title_var in title_variations:
                results = await self.crawler.search_books(title_var, author)

                for result in results[:5]:
                    metadata = await self.crawler.get_book_details(result['goodreads_id'])

                    if metadata:
                        title_sim = self._text_similarity(title, metadata.title)
                        author_sim = self._text_similarity(author, metadata.author)
                        confidence = (title_sim * 0.7 + author_sim * 0.3)

                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_match = metadata

            if best_match and best_confidence >= 0.7:
                return ResolutionResult(
                    success=True,
                    book=best_match,
                    confidence=best_confidence,
                    resolution_method="fuzzy"
                )

            return ResolutionResult(
                success=False,
                confidence=0.0,
                resolution_method="fuzzy",
                note="No fuzzy match found"
            )

        except Exception as e:
            logger.error(f"Fuzzy resolution failed: {e}")
            return ResolutionResult(
                success=False,
                confidence=0.0,
                resolution_method="fuzzy",
                note=f"Error: {e}"
            )

    @staticmethod
    def _text_similarity(text1: str, text2: str) -> float:
        """Calculate text similarity (0.0 to 1.0)"""
        if not text1 or not text2:
            return 0.0

        text1 = text1.lower().strip()
        text2 = text2.lower().strip()

        if text1 == text2:
            return 1.0

        # Check if one contains the other
        if text1 in text2 or text2 in text1:
            return 0.9

        # Levenshtein-like distance approximation
        matches = sum(1 for c1, c2 in zip(text1, text2) if c1 == c2)
        return matches / max(len(text1), len(text2))

    async def close(self):
        """Close the resolver"""
        await self.crawler.close()
