"""
Series Completion Logic (Section 8).
Identifies and downloads missing books in a series.
"""

import logging
import asyncio
from typing import List, Dict, Optional
from mamcrawler.goodreads import GoodreadsMetadata

logger = logging.getLogger(__name__)

class SeriesCompletion:
    """
    Handles series completion logic.
    """
    
    def __init__(self):
        self.goodreads = GoodreadsMetadata()
    
    async def check_series_completion(self,
                                      book_metadata: Dict,
                                      abs_library: List[Dict]) -> List[Dict]:
        """
        Check if book belongs to a series and identify missing books.
        
        Args:
            book_metadata: Metadata for the current book
            abs_library: Current Audiobookshelf library
            
        Returns:
            List of missing book metadata dicts
        """
        series_name = book_metadata.get('series')
        author = book_metadata.get('author')
        
        if not series_name or not author:
            logger.info("📚 Book is not part of a series or missing author info")
            return []
        
        logger.info(f"📚 Checking series completion: {series_name} by {author}")
        
        # Get all books in series from Goodreads
        series_books = await self.goodreads.get_series_books(series_name, author)
        
        if not series_books:
            logger.warning(f"✗ Could not find series books for: {series_name}")
            return []
        
        logger.info(f"✓ Found {len(series_books)} books in series: {series_name}")
        
        # Identify missing books
        missing_books = self._find_missing_books(series_books, abs_library)
        
        if missing_books:
            logger.info(f"📥 Missing {len(missing_books)} books from series:")
            for book in missing_books:
                logger.info(f"  - {book.get('title')} (#{book.get('series_number')})")
        else:
            logger.info(f"✓ Series complete! All books present in library")
        
        return missing_books
    
    def _find_missing_books(self, 
                           series_books: List[Dict],
                           abs_library: List[Dict]) -> List[Dict]:
        """
        Compare series books against library to find missing ones.
        
        Args:
            series_books: Books in the series from Goodreads
            abs_library: Current Audiobookshelf library
            
        Returns:
            List of missing books
        """
        missing = []
        
        for book in series_books:
            if not self._is_in_library(book, abs_library):
                missing.append(book)
        
        return missing
    
    def _is_in_library(self, book: Dict, library: List[Dict]) -> bool:
        """
        Check if a book is already in the library.
        
        Uses fuzzy matching on title and author.
        """
        book_title = book.get('title', '').lower()
        book_author = book.get('author', '').lower()
        
        for lib_item in library:
            lib_title = lib_item.get('title', '').lower()
            lib_author = lib_item.get('author', '').lower()
            
            # Exact match
            if book_title == lib_title and book_author == lib_author:
                return True
            
            # Fuzzy match (handle subtitle variations)
            if self._fuzzy_title_match(book_title, lib_title) and book_author == lib_author:
                return True
        
        return False
    
    def _fuzzy_title_match(self, title1: str, title2: str, threshold: float = 0.85) -> bool:
        """
        Fuzzy match two titles.
        
        Handles:
        - Subtitle variations ("Title: Subtitle" vs "Title")
        - Punctuation differences
        - Minor spelling variations
        """
        # Remove common subtitle separators
        title1_base = title1.split(':')[0].split('(')[0].strip()
        title2_base = title2.split(':')[0].split('(')[0].strip()
        
        # Simple character-based similarity
        if title1_base == title2_base:
            return True
        
        # Try fuzzywuzzy if available
        try:
            from fuzzywuzzy import fuzz
            score = fuzz.ratio(title1_base, title2_base) / 100.0
            return score >= threshold
        except ImportError:
            # Fallback to exact match
            return title1_base == title2_base
    
    async def download_missing_books(self,
                                     missing_books: List[Dict],
                                     download_callback) -> List[Dict]:
        """
        Download missing books from series.
        
        Args:
            missing_books: List of missing book metadata
            download_callback: Async function to download a book
                             Should accept (title, author, metadata) and return success bool
            
        Returns:
            List of successfully downloaded books
        """
        if not missing_books:
            return []
        
        logger.info(f"📥 Downloading {len(missing_books)} missing books from series...")
        
        downloaded = []
        
        for book in missing_books:
            title = book.get('title')
            author = book.get('author')
            
            logger.info(f"📥 Downloading: {title} by {author}")
            
            try:
                success = await download_callback(title, author, book)
                
                if success:
                    downloaded.append(book)
                    logger.info(f"✓ Downloaded: {title}")
                else:
                    logger.warning(f"✗ Failed to download: {title}")
                
                # Rate limiting between downloads
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"✗ Error downloading {title}: {e}")
        
        logger.info(f"✓ Downloaded {len(downloaded)}/{len(missing_books)} missing books")
        
        return downloaded
    
    def prioritize_missing_books(self, missing_books: List[Dict]) -> List[Dict]:
        """
        Prioritize missing books by series order.
        
        Downloads in series order (lowest series_number first).
        """
        return sorted(missing_books, key=lambda b: float(b.get('series_number', 999) or 999))
