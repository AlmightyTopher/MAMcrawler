"""
Author & Series Completion (Section 9).
Library-driven expansion - downloads missing titles from existing authors/series.
"""

import logging
import asyncio
from typing import List, Dict, Set, Optional
from mamcrawler.goodreads import GoodreadsMetadata

logger = logging.getLogger(__name__)

class AuthorSeriesCompletion:
    """
    Handles author and series completion logic.
    Downloads missing titles from authors/series already in library.
    """
    
    def __init__(self):
        self.goodreads = GoodreadsMetadata()
        self.wishlist = []
    
    async def gather_library_authors(self, abs_library: List[Dict]) -> Set[str]:
        """
        Gather all unique authors from Audiobookshelf library.
        
        Args:
            abs_library: Current Audiobookshelf library
            
        Returns:
            Set of author names
        """
        authors = set()
        
        for item in abs_library:
            author = item.get('author')
            if author:
                authors.add(author)
        
        logger.info(f"📚 Found {len(authors)} unique authors in library")
        
        return authors
    
    async def gather_library_series(self, abs_library: List[Dict]) -> Set[str]:
        """
        Gather all unique series from Audiobookshelf library.
        
        Args:
            abs_library: Current Audiobookshelf library
            
        Returns:
            Set of series names
        """
        series = set()
        
        for item in abs_library:
            series_name = item.get('series')
            if series_name:
                series.add(series_name)
        
        logger.info(f"📚 Found {len(series)} unique series in library")
        
        return series
    
    async def find_missing_by_author(self,
                                     author: str,
                                     abs_library: List[Dict],
                                     mam_search_callback) -> List[Dict]:
        """
        Find all missing titles by a specific author.
        
        Args:
            author: Author name
            abs_library: Current library
            mam_search_callback: Async function to search MAM for author's books
                                Returns list of book metadata dicts
            
        Returns:
            List of missing book metadata
        """
        logger.info(f"🔍 Finding missing titles by: {author}")
        
        # Search MAM for all books by this author
        mam_books = await mam_search_callback(author)
        
        if not mam_books:
            logger.warning(f"✗ No books found on MAM for: {author}")
            return []
        
        logger.info(f"✓ Found {len(mam_books)} books by {author} on MAM")
        
        # Filter out books already in library
        missing = []
        for book in mam_books:
            if not self._is_in_library(book, abs_library):
                missing.append(book)
        
        if missing:
            logger.info(f"📥 Missing {len(missing)} books by {author}:")
            for book in missing[:5]:  # Show first 5
                logger.info(f"  - {book.get('title')}")
            if len(missing) > 5:
                logger.info(f"  ... and {len(missing) - 5} more")
        
        return missing
    
    async def find_missing_by_series(self,
                                     series_name: str,
                                     author: str,
                                     abs_library: List[Dict]) -> List[Dict]:
        """
        Find all missing books in a series.
        
        Args:
            series_name: Series name
            author: Author name
            abs_library: Current library
            
        Returns:
            List of missing book metadata
        """
        logger.info(f"🔍 Finding missing books in series: {series_name}")
        
        # Get all books in series from Goodreads
        series_books = await self.goodreads.get_series_books(series_name, author)
        
        if not series_books:
            logger.warning(f"✗ Could not find series: {series_name}")
            return []
        
        # Filter out books already in library
        missing = []
        for book in series_books:
            if not self._is_in_library(book, abs_library):
                missing.append(book)
        
        if missing:
            logger.info(f"📥 Missing {len(missing)} books from {series_name}")
        
        return missing
    
    def _is_in_library(self, book: Dict, library: List[Dict]) -> bool:
        """Check if book is in library (fuzzy match)."""
        book_title = book.get('title', '').lower()
        book_author = book.get('author', '').lower()
        
        for lib_item in library:
            lib_title = lib_item.get('title', '').lower()
            lib_author = lib_item.get('author', '').lower()
            
            if self._fuzzy_match(book_title, lib_title) and book_author == lib_author:
                return True
        
        return False
    
    def _fuzzy_match(self, str1: str, str2: str, threshold: float = 0.85) -> bool:
        """Fuzzy string matching."""
        # Remove subtitles
        str1_base = str1.split(':')[0].split('(')[0].strip()
        str2_base = str2.split(':')[0].split('(')[0].strip()
        
        if str1_base == str2_base:
            return True
        
        try:
            from fuzzywuzzy import fuzz
            return fuzz.ratio(str1_base, str2_base) / 100.0 >= threshold
        except ImportError:
            return str1_base == str2_base
    
    async def build_wishlist(self,
                             abs_library: List[Dict],
                             mam_search_callback) -> List[Dict]:
        """
        Build complete wishlist of missing titles.
        
        Args:
            abs_library: Current Audiobookshelf library
            mam_search_callback: Async function to search MAM
            
        Returns:
            Wishlist of missing books
        """
        logger.info("📋 Building wishlist from library authors and series...")
        
        wishlist = []
        
        # Gather authors and series
        authors = await self.gather_library_authors(abs_library)
        series = await self.gather_library_series(abs_library)
        
        # Find missing by author
        for author in authors:
            missing = await self.find_missing_by_author(author, abs_library, mam_search_callback)
            wishlist.extend(missing)
            await asyncio.sleep(2)  # Rate limiting
        
        # Find missing by series
        for series_name in series:
            # Get author for this series from library
            series_author = self._get_series_author(series_name, abs_library)
            if series_author:
                missing = await self.find_missing_by_series(series_name, series_author, abs_library)
                wishlist.extend(missing)
                await asyncio.sleep(2)  # Rate limiting
        
        # Remove duplicates
        wishlist = self._deduplicate_wishlist(wishlist)
        
        logger.info(f"✓ Wishlist complete: {len(wishlist)} missing titles")
        
        self.wishlist = wishlist
        return wishlist
    
    def _get_series_author(self, series_name: str, library: List[Dict]) -> Optional[str]:
        """Get author for a series from library."""
        for item in library:
            if item.get('series') == series_name:
                return item.get('author')
        return None
    
    def _deduplicate_wishlist(self, wishlist: List[Dict]) -> List[Dict]:
        """Remove duplicate books from wishlist."""
        seen = set()
        unique = []
        
        for book in wishlist:
            key = (book.get('title', '').lower(), book.get('author', '').lower())
            if key not in seen:
                seen.add(key)
                unique.append(book)
        
        return unique
    
    def categorize_wishlist(self, wishlist: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Categorize wishlist by download priority.
        
        Categories:
        - immediate: Few missing titles (< 5)
        - gradual: Many missing titles (>= 5)
        
        Returns:
            Dict with 'immediate' and 'gradual' lists
        """
        categorized = {
            'immediate': [],
            'gradual': []
        }
        
        # Group by author
        by_author = {}
        for book in wishlist:
            author = book.get('author', 'Unknown')
            if author not in by_author:
                by_author[author] = []
            by_author[author].append(book)
        
        # Categorize
        for author, books in by_author.items():
            if len(books) < 5:
                categorized['immediate'].extend(books)
            else:
                categorized['gradual'].extend(books)
        
        logger.info(f"📊 Wishlist categorized:")
        logger.info(f"  - Immediate download: {len(categorized['immediate'])} books")
        logger.info(f"  - Gradual download: {len(categorized['gradual'])} books")
        
        return categorized
    
    async def download_wishlist(self,
                                wishlist: List[Dict],
                                download_callback,
                                event_aware: bool = True,
                                max_downloads: Optional[int] = None) -> List[Dict]:
        """
        Download books from wishlist.
        
        Args:
            wishlist: List of books to download
            download_callback: Async function to download a book
            event_aware: If True, respect event-aware pacing
            max_downloads: Maximum number of downloads (None = unlimited)
            
        Returns:
            List of successfully downloaded books
        """
        if not wishlist:
            return []
        
        download_count = min(len(wishlist), max_downloads) if max_downloads else len(wishlist)
        
        logger.info(f"📥 Downloading {download_count} books from wishlist...")
        
        downloaded = []
        
        for i, book in enumerate(wishlist[:download_count]):
            title = book.get('title')
            author = book.get('author')
            
            logger.info(f"📥 [{i+1}/{download_count}] Downloading: {title} by {author}")
            
            try:
                success = await download_callback(title, author, book)
                
                if success:
                    downloaded.append(book)
                    logger.info(f"✓ Downloaded: {title}")
                else:
                    logger.warning(f"✗ Failed to download: {title}")
                
                # Event-aware pacing
                if event_aware:
                    await asyncio.sleep(10)  # Slow pace by default
                else:
                    await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"✗ Error downloading {title}: {e}")
        
        logger.info(f"✓ Downloaded {len(downloaded)}/{download_count} books from wishlist")
        
        return downloaded
