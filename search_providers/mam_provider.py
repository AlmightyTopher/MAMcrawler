#!/usr/bin/env python3
"""
MAM (MyAnonamouse) search provider for the unified search system.
Consolidates multiple MAM search scripts into a single provider.
"""

import asyncio
import logging
import re
import time
from typing import Dict, List, Optional, Any
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

from search_types import SearchProviderInterface, SearchQuery, SearchResult, SearchMode

logger = logging.getLogger(__name__)


class MAMSearchProvider(SearchProviderInterface):
    """
    MAM (MyAnonamouse) torrent search provider
    """

    PROVIDER_TYPE = "mam"
    CAPABILITIES = ["torrent_search", "audiobook_search", "author_search", "genre_search"]
    RATE_LIMITS = {"requests_per_minute": 30, "delay_seconds": 2}
    CONFIG_REQUIRED = ["session_id"]

    # MAM category mappings
    CATEGORIES = {
        'audiobooks': 13,  # Main audiobooks category
        'fantasy': 41,     # Audiobooks - Fantasy
        'sci-fi': 47,      # Audiobooks - Science Fiction
        'all_audiobooks': [39, 49, 50, 83, 51, 97, 40, 41, 106, 42, 52, 98, 54, 55, 43, 99, 84, 44, 56, 45, 57, 85, 87, 119, 88, 58, 59, 46, 47, 53, 89, 100, 108, 48, 111]
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = "https://www.myanonamouse.net"
        self.session_id = self.config.get('session_id') or self.config.get('mam_id')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        if self.session_id:
            self.session.cookies.set('mam_id', self.session_id, domain='www.myanonamouse.net', path='/')

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Search MAM for audiobooks

        Args:
            query: Search query parameters

        Returns:
            List of search results
        """
        if not self.session_id:
            logger.warning("MAM session ID not configured")
            return []

        results = []

        try:
            if query.author and not query.query:
                # Author-specific search
                results = await self._search_by_author(query.author, query.limit)
            elif query.genre:
                # Genre-specific search
                results = await self._search_by_genre(query.genre, query.limit)
            else:
                # General search
                results = await self._search_general(query.query, query.limit)

        except Exception as e:
            logger.error(f"MAM search error: {e}")
            return []

        return results

    async def _search_by_author(self, author_name: str, limit: int = 10) -> List[SearchResult]:
        """Search MAM for all audiobooks by an author"""
        logger.info(f"Searching MAM for author: {author_name}")

        all_results = []
        page_num = 0
        has_more = True

        while has_more and len(all_results) < limit:
            page_num += 1
            start_number = (page_num - 1) * 50

            search_url = (
                f"{self.base_url}/tor/browse.php"
                f"?tor[searchstr]={quote(author_name)}"
                f"&tor[cat][]={self.CATEGORIES['audiobooks']}"  # Audiobooks
                f"&tor[searchType]=all"
                f"&tor[searchIn]=torrents"
                f"&tor[startNumber]={start_number}"
            )

            logger.debug(f"Fetching page {page_num} (startNumber={start_number})")

            try:
                # Rate limiting
                await asyncio.sleep(self.RATE_LIMITS["delay_seconds"])

                response = self.session.get(search_url, timeout=30)

                if response.status_code != 200:
                    logger.warning(f"Page {page_num} failed: {response.status_code}")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')
                page_results = self._parse_search_results(soup, author_name)

                if not page_results:
                    has_more = False
                    logger.debug(f"No results on page {page_num}, stopping")
                else:
                    all_results.extend(page_results)

                if page_num >= 15:  # Safety limit
                    logger.warning("Reached page limit (15), stopping")
                    has_more = False

            except Exception as e:
                logger.error(f"Error on page {page_num}: {e}")
                break

        logger.info(f"Found {len(all_results)} results for author {author_name}")
        return all_results[:limit]

    async def _search_by_genre(self, genre: str, limit: int = 10) -> List[SearchResult]:
        """Search MAM for audiobooks in a specific genre"""
        logger.info(f"Searching MAM for genre: {genre}")

        if genre not in self.CATEGORIES:
            logger.warning(f"Unknown genre: {genre}")
            return []

        category_id = self.CATEGORIES[genre]

        # Build search URL for popular audiobooks in genre
        search_url = (
            f"{self.base_url}/tor/browse.php?"
            f"tor[srchIn][title]=true&"
            f"tor[srchIn][author]=true&"
            f"tor[srchIn][narrator]=true&"
            f"tor[searchType]=all&"
            f"tor[searchIn]=torrents&"
            f"tor[cat][]={category_id}&"
            f"tor[browse_lang][]=1&"
            f"tor[browseFlagsHideVsShow]=0&"
            f"tor[sortType]=snatchedDesc&"
            f"tor[startNumber]=0&"
            "thumbnail=true"
        )

        try:
            # Rate limiting
            await asyncio.sleep(self.RATE_LIMITS["delay_seconds"])

            response = self.session.get(search_url, timeout=30)

            if response.status_code != 200:
                logger.error(f"MAM search failed: {response.status_code}")
                return []

            soup = BeautifulSoup(response.text, 'html.parser')
            results = self._parse_search_results(soup, genre=genre)

            logger.info(f"Found {len(results)} results for genre {genre}")
            return results[:limit]

        except Exception as e:
            logger.error(f"Genre search error: {e}")
            return []

    async def _search_general(self, search_term: str, limit: int = 10) -> List[SearchResult]:
        """General MAM search"""
        logger.info(f"Searching MAM for: {search_term}")

        search_url = (
            f"{self.base_url}/tor/browse.php"
            f"?tor[searchstr]={quote(search_term)}"
            f"&tor[cat][]={self.CATEGORIES['audiobooks']}"
            f"&tor[searchType]=all"
            f"&tor[searchIn]=torrents"
            f"&tor[startNumber]=0"
        )

        try:
            # Rate limiting
            await asyncio.sleep(self.RATE_LIMITS["delay_seconds"])

            response = self.session.get(search_url, timeout=30)

            if response.status_code != 200:
                logger.error(f"MAM search failed: {response.status_code}")
                return []

            soup = BeautifulSoup(response.text, 'html.parser')
            results = self._parse_search_results(soup, search_term=search_term)

            logger.info(f"Found {len(results)} results for '{search_term}'")
            return results[:limit]

        except Exception as e:
            logger.error(f"General search error: {e}")
            return []

    def _parse_search_results(self, soup: BeautifulSoup, author: str = None,
                            genre: str = None, search_term: str = None) -> List[SearchResult]:
        """Parse MAM search results HTML"""
        results = []

        # Find all torrent entries
        rows = soup.find_all('tr')

        for row in rows:
            torrent_link = row.find('a', href=re.compile(r'/t/\d+'))
            if not torrent_link:
                continue

            title = torrent_link.get_text(strip=True)
            torrent_id_match = re.search(r'/t/(\d+)', torrent_link.get('href', ''))

            if not title or not torrent_id_match:
                continue

            torrent_id = torrent_id_match.group(1)

            # Extract additional metadata from the row
            size = self._extract_size(row)
            seeders = self._extract_seeders(row)
            snatched = self._extract_snatched(row)

            # Try to extract magnet link
            magnet_link = self._extract_magnet_link(torrent_id)

            result = SearchResult(
                provider=self.PROVIDER_TYPE,
                query=search_term or author or genre or "",
                title=title,
                author=author,
                torrent_id=torrent_id,
                url=urljoin(self.base_url, f"/t/{torrent_id}/"),
                magnet_link=magnet_link,
                size=size,
                seeders=seeders,
                snatched=snatched,
                metadata={
                    'genre': genre,
                    'search_term': search_term
                }
            )

            results.append(result)

        return results

    def _extract_size(self, row) -> Optional[str]:
        """Extract file size from torrent row"""
        try:
            # Look for size in table cells
            cells = row.find_all('td')
            for cell in cells:
                text = cell.get_text(strip=True)
                # Match patterns like "500 MB", "2.3 GB", etc.
                if re.search(r'\d+\.?\d*\s*(MB|GB|KB)', text, re.IGNORECASE):
                    return text
        except:
            pass
        return None

    def _extract_seeders(self, row) -> Optional[int]:
        """Extract seeder count from torrent row"""
        try:
            # Look for seeder numbers
            cells = row.find_all('td')
            for cell in cells:
                text = cell.get_text(strip=True)
                # Look for pure numbers that could be seeders
                if text.isdigit() and len(text) <= 4:  # Reasonable seeder count
                    return int(text)
        except:
            pass
        return None

    def _extract_snatched(self, row) -> Optional[int]:
        """Extract snatched count from torrent row"""
        try:
            # Similar to seeders but look for higher numbers
            cells = row.find_all('td')
            for cell in cells:
                text = cell.get_text(strip=True)
                if text.isdigit() and len(text) >= 2:  # Snatched counts are usually higher
                    return int(text)
        except:
            pass
        return None

    def _extract_magnet_link(self, torrent_id: str) -> Optional[str]:
        """Extract magnet link from torrent details page"""
        try:
            torrent_url = f"{self.base_url}/t/{torrent_id}/"
            time.sleep(1)  # Rate limiting

            response = self.session.get(torrent_url, timeout=30)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')
            magnet_link = soup.find('a', href=re.compile(r'^magnet:\?'))

            if magnet_link:
                return magnet_link.get('href')

        except Exception as e:
            logger.warning(f"Error extracting magnet for {torrent_id}: {e}")

        return None

    async def health_check(self) -> bool:
        """Check if MAM is accessible and authenticated"""
        try:
            # Try to access the browse page
            response = self.session.get(f"{self.base_url}/tor/browse.php", timeout=10)

            if response.status_code == 200:
                # Check if we're logged in (look for user-specific content)
                if "logout" in response.text.lower() or "userdetails" in response.text.lower():
                    return True
                else:
                    logger.warning("MAM accessible but not authenticated")
                    return False
            else:
                logger.error(f"MAM health check failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"MAM health check error: {e}")
            return False