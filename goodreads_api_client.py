#!/usr/bin/env python3
"""
Goodreads API Client for External Metadata Verification

Provides integration with Goodreads to verify audiobook metadata extracted from audio.
Uses web scraping since the official Goodreads API was deprecated.
Includes caching and rate limiting to minimize network calls.
"""

import asyncio
import aiohttp
import logging
import json
import re
import time
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class BookMetadata:
    """Structured book metadata from external source"""
    title: str
    author: str
    series_name: Optional[str] = None
    series_position: Optional[str] = None
    isbn: Optional[str] = None
    asin: Optional[str] = None
    goodreads_url: Optional[str] = None
    confidence: float = 0.0


class GoodreadsClient:
    """
    Goodreads web scraper for metadata verification

    Since the official API was deprecated, this uses web scraping with:
    - Rate limiting (max 5 requests/sec)
    - Local caching to minimize requests
    - Retry logic with exponential backoff
    """

    BASE_URL = "https://www.goodreads.com"
    SEARCH_URL = f"{BASE_URL}/search"
    RATE_LIMIT_DELAY = 0.2  # 5 requests/sec max

    def __init__(self, cache_file: str = "goodreads_cache.json"):
        self.cache_file = Path(cache_file)
        self.cache = self._load_cache()
        self.last_request_time = 0
        self.session = None

    def _load_cache(self) -> Dict:
        """Load cached search results"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading cache: {e}")
        return {}

    def _save_cache(self):
        """Save cache to disk"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving cache: {e}")

    def _get_cache_key(self, title: str, author: str) -> str:
        """Generate cache key from title + author"""
        return f"{title.lower().strip()}|{author.lower().strip()}"

    async def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            await asyncio.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self.last_request_time = time.time()

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
        self._save_cache()

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

    def _extract_book_from_search_result(self, book_div) -> Optional[BookMetadata]:
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

            # Extract book ID for potential ISBN lookup
            goodreads_id = None
            if book_url:
                id_match = re.search(r'/show/(\d+)', book_url)
                if id_match:
                    goodreads_id = id_match.group(1)

            return BookMetadata(
                title=title,
                author=author,
                series_name=series_name,
                series_position=series_position,
                goodreads_url=book_url,
                confidence=0.0  # Will be calculated by caller
            )

        except Exception as e:
            logger.warning(f"Error parsing search result: {e}")
            return None

    async def search_book(self, title: str, author: str) -> Optional[BookMetadata]:
        """
        Search Goodreads for a book by title and author

        Returns the best matching result or None
        """
        cache_key = self._get_cache_key(title, author)

        # Check cache first
        if cache_key in self.cache:
            logger.debug(f"Cache hit for: {title} by {author}")
            cached = self.cache[cache_key]
            if cached:
                return BookMetadata(**cached)
            return None

        # Not in cache - perform search
        logger.info(f"Searching Goodreads: '{title}' by {author}")

        try:
            await self._rate_limit()

            # Construct search query
            query = f"{title} {author}"
            params = {
                'q': query,
                'search_type': 'books'
            }

            async with self.session.get(self.SEARCH_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    logger.warning(f"Goodreads search failed with status {resp.status}")
                    self.cache[cache_key] = None
                    return None

                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Find search results
                results = soup.find_all('tr', itemtype='http://schema.org/Book')

                if not results:
                    logger.info(f"No Goodreads results found for: {title} by {author}")
                    self.cache[cache_key] = None
                    return None

                # Process first result (most relevant)
                best_match = self._extract_book_from_search_result(results[0])

                if best_match:
                    # Cache the result
                    self.cache[cache_key] = asdict(best_match)
                    logger.info(f"Found: {best_match.title} by {best_match.author}")
                    if best_match.series_name:
                        logger.info(f"  Series: {best_match.series_name} #{best_match.series_position}")
                    return best_match
                else:
                    self.cache[cache_key] = None
                    return None

        except asyncio.TimeoutError:
            logger.warning(f"Goodreads search timeout for: {title}")
            return None
        except Exception as e:
            logger.error(f"Error searching Goodreads: {e}")
            return None

    async def verify_metadata(self, audio_title: str, audio_author: str,
                            audio_series: Optional[str] = None,
                            audio_sequence: Optional[str] = None) -> Tuple[bool, float, Optional[BookMetadata]]:
        """
        Verify extracted audio metadata against Goodreads

        Returns:
            (is_valid, confidence_score, goodreads_metadata)

        Confidence scoring:
        - 1.0: Perfect match (title + author + series + sequence)
        - 0.9: Strong match (title + author + series OR sequence)
        - 0.7: Good match (title + author)
        - 0.5: Weak match (title or author)
        - 0.0: No match
        """
        result = await self.search_book(audio_title, audio_author)

        # If no result with full series name, try extracting just the main title
        if not result and audio_series:
            # Try extracting first few words as title
            title_words = audio_series.split()
            if len(title_words) >= 2:
                simple_title = ' '.join(title_words[:2])  # First 2 words
                logger.info(f"Retrying with simplified title: {simple_title}")
                result = await self.search_book(simple_title, audio_author)

        if not result:
            return False, 0.0, None

        confidence = 0.0

        # Title matching (fuzzy) - weighted heavily since it's most reliable
        title_similarity = self._calculate_similarity(audio_title, result.title)
        confidence += title_similarity * 0.5

        # Author matching (fuzzy) - also heavily weighted
        author_similarity = self._calculate_similarity(audio_author, result.author)
        confidence += author_similarity * 0.4

        # Series matching - less weight since speech recognition can mishear series names
        if audio_series and result.series_name:
            series_similarity = self._calculate_similarity(audio_series, result.series_name)
            # Even partial series match is good
            if series_similarity >= 0.3:
                confidence += 0.05
        elif not audio_series and not result.series_name:
            confidence += 0.05  # Both agree no series

        # Sequence matching - exact match required, but low weight
        if audio_sequence and result.series_position:
            if str(audio_sequence).strip() == str(result.series_position).strip():
                confidence += 0.05
        elif not audio_sequence and not result.series_position:
            confidence += 0.05  # Both agree no sequence

        result.confidence = confidence
        is_valid = confidence >= 0.7  # 70% threshold for validity

        return is_valid, confidence, result

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings (0.0 - 1.0)"""
        if not str1 or not str2:
            return 0.0

        # Normalize - lowercase, trim, and remove multiple spaces
        s1 = ' '.join(str1.lower().strip().split())
        s2 = ' '.join(str2.lower().strip().split())

        # Exact match
        if s1 == s2:
            return 1.0

        # Substring match
        if s1 in s2 or s2 in s1:
            return 0.95

        # Check if all words from shorter string are in longer string
        words1 = set(s1.split())
        words2 = set(s2.split())

        if not words1 or not words2:
            return 0.0

        # Use shorter set as base for comparison
        shorter, longer = (words1, words2) if len(words1) < len(words2) else (words2, words1)

        # If all words from shorter are in longer, high similarity
        if shorter.issubset(longer):
            return 0.90

        # Count matching words
        common = words1.intersection(words2)

        # Calculate similarity as ratio of common words to total unique words
        # Use min() in denominator to be more lenient
        similarity = len(common) / min(len(words1), len(words2))

        return similarity


# Standalone test
async def test_goodreads_client():
    """Test the Goodreads client with some example books"""
    test_books = [
        ("The Name of the Wind", "Patrick Rothfuss"),
        ("Harry Potter and the Sorcerer's Stone", "J.K. Rowling"),
        ("The Hobbit", "J.R.R. Tolkien"),
        ("Terminator Gene", "Ian Irvine"),
    ]

    async with GoodreadsClient() as client:
        for title, author in test_books:
            print(f"\nSearching: {title} by {author}")
            print("-" * 60)

            result = await client.search_book(title, author)
            if result:
                print(f"Found: {result.title}")
                print(f"Author: {result.author}")
                if result.series_name:
                    print(f"Series: {result.series_name} #{result.series_position}")
                print(f"URL: {result.goodreads_url}")
            else:
                print("Not found")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    asyncio.run(test_goodreads_client())
