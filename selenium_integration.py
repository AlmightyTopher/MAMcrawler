#!/usr/bin/env python3
"""
Selenium Crawler Integration Module
====================================
Provides async-compatible wrappers and integration utilities
for integrating SeleniumMAMCrawler with MasterAudiobookManager

Key Features:
- Async/sync bridge using asyncio executors
- Database integration for storing results
- Duplicate detection and prevention
- Search term generation from missing books
- Result processing and enrichment
"""

import asyncio
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

import sys
# if sys.platform == 'win32':
#     import io
#     try:
#         if hasattr(sys.stdout, 'buffer'):
#             sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
#         if hasattr(sys.stderr, 'buffer'):
#             sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
#     except Exception:
#         pass

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


class SeleniumIntegrationConfig:
    """Configuration for Selenium integration"""

    @staticmethod
    def validate() -> bool:
        """Validate all required environment variables"""
        required = [
            'MAM_USERNAME',
            'MAM_PASSWORD',
            'QB_HOST',
            'QB_USERNAME',
            'QB_PASSWORD'
        ]

        missing = [var for var in required if not os.getenv(var)]

        if missing:
            logger.error(f"SeleniumIntegration: Missing config: {', '.join(missing)}")
            return False

        logger.info("SeleniumIntegration: Configuration validated successfully")
        return True

    @staticmethod
    def get_crawler_params() -> Dict[str, str]:
        """Get parameters for SeleniumMAMCrawler initialization"""
        # Build qB URL from host and port
        qb_host = os.getenv('QB_HOST', 'http://localhost')
        qb_port = os.getenv('QB_PORT', '8080')
        qb_url = f"{qb_host}:{qb_port}" if not qb_host.endswith(qb_port) else qb_host

        return {
            'email': os.getenv('MAM_USERNAME'),
            'password': os.getenv('MAM_PASSWORD'),
            'qb_url': qb_url,
            'qb_user': os.getenv('QB_USERNAME', 'admin'),
            'qb_pass': os.getenv('QB_PASSWORD', ''),
            'headless': os.getenv('MAM_SELENIUM_HEADLESS', 'true').lower() == 'true'
        }


class SeleniumSearchTermGenerator:
    """Generate optimized search terms from missing books analysis"""

    @staticmethod
    def from_series_analysis(series_missing: List[Dict]) -> List[Dict[str, Any]]:
        """Generate search terms from series missing book analysis

        Args:
            series_missing: List of missing series from analyze_series_missing_books()

        Returns:
            List of search term dicts with priority
        """
        search_terms = []

        for series in series_missing:
            series_name = series.get('series_name', '')
            author = series.get('author', 'Unknown')
            missing_numbers = series.get('missing_numbers', [])
            total_books = series.get('total_books', 0)

            for missing_num in missing_numbers:
                # Try exact series number first
                search_terms.append({
                    'title': series_name,
                    'series_number': missing_num,
                    'author': author,
                    'priority': 'high',
                    'search_type': 'series_exact',
                    'context': f"Series {missing_num}/{total_books}"
                })

                # Also try title variant "Series Name Book N"
                search_terms.append({
                    'title': f"{series_name} {missing_num}",
                    'author': author,
                    'priority': 'high',
                    'search_type': 'series_variant',
                    'context': f"Series variant for book {missing_num}"
                })

        logger.info(f"Generated {len(search_terms)} search terms from series analysis")
        return search_terms

    @staticmethod
    def from_author_analysis(author_missing: List[Dict]) -> List[Dict[str, Any]]:
        """Generate search terms from author missing book analysis

        Args:
            author_missing: List of authors with missing books

        Returns:
            List of search term dicts with priority
        """
        search_terms = []

        for author_data in author_missing:
            author = author_data.get('author', 'Unknown')
            # Generate broad author search for high-volume authors
            search_terms.append({
                'author': author,
                'priority': 'medium',
                'search_type': 'author_discovery',
                'context': f"Discover more books by {author}"
            })

        logger.info(f"Generated {len(search_terms)} search terms from author analysis")
        return search_terms

    @staticmethod
    def from_missing_books_list(books: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Generate search terms from simple missing books list

        Args:
            books: List of dicts with 'title', 'author' keys

        Returns:
            List of search term dicts
        """
        search_terms = []

        for book in books:
            title = book.get('title', '')
            author = book.get('author', '')

            if title:
                search_terms.append({
                    'title': title,
                    'author': author if author else None,
                    'priority': 'medium',
                    'search_type': 'direct',
                    'context': 'Direct search for missing book'
                })

        return search_terms


class SeleniumSearchResultProcessor:
    """Process and store Selenium search results"""

    def __init__(self, db_session=None):
        """Initialize processor with optional database session

        Args:
            db_session: SQLAlchemy session for database operations
        """
        self.db_session = db_session
        self.processed = {
            'total_searched': 0,
            'found': 0,
            'queued': 0,
            'duplicates': 0,
            'errors': []
        }

    def check_duplicate(self, title: str, author: str, magnet_link: str) -> bool:
        """Check if download already exists

        Args:
            title: Book title
            author: Author name
            magnet_link: Magnet link

        Returns:
            True if duplicate exists, False otherwise
        """
        if not self.db_session:
            return False

        try:
            # Import here to avoid circular dependency
            from backend.models.download import Download

            existing = self.db_session.query(Download).filter(
                Download.title == title,
                Download.magnet_link == magnet_link
            ).first()

            if existing:
                logger.debug(f"Duplicate detected: {title}")
                return True

        except Exception as e:
            logger.warning(f"Error checking duplicate: {e}")

        return False

    def store_download_record(self, title: str, author: str, magnet_link: str,
                            source: str = "MAM") -> Optional[int]:
        """Store download record in database

        Args:
            title: Book title
            author: Author name
            magnet_link: Magnet link
            source: Download source

        Returns:
            Download record ID or None if failed
        """
        if not self.db_session:
            logger.warning("No database session available for storing download")
            return None

        try:
            from backend.models.download import Download

            download = Download(
                title=title,
                author=author,
                source=source,
                magnet_link=magnet_link,
                status="queued",
                date_queued=datetime.now(),
                import_source="mam_selenium_crawler"
            )

            self.db_session.add(download)
            self.db_session.commit()

            logger.info(f"Stored download record: {title}")
            return download.id

        except Exception as e:
            logger.error(f"Error storing download record: {e}")
            self.db_session.rollback()
            return None

    def process_search_result(self, search_result: Dict[str, Any],
                             search_term: Dict[str, Any]) -> bool:
        """Process single search result

        Args:
            search_result: Result from Selenium crawler
            search_term: Original search term used

        Returns:
            True if successfully processed, False otherwise
        """
        self.processed['total_searched'] += 1

        if not search_result:
            return False

        try:
            title = search_result.get('title', search_term.get('title', 'Unknown'))
            author = search_result.get('author', search_term.get('author', ''))
            magnet_link = search_result.get('magnet_link')

            if not magnet_link:
                logger.warning(f"No magnet link found for {title}")
                return False

            # Check for duplicate
            if self.check_duplicate(title, author, magnet_link):
                self.processed['duplicates'] += 1
                return False

            # Store in database
            download_id = self.store_download_record(title, author, magnet_link)

            if download_id:
                self.processed['found'] += 1
                self.processed['queued'] += 1
                return True

        except Exception as e:
            error_msg = f"Error processing result for {search_term.get('title', 'Unknown')}: {e}"
            logger.error(error_msg)
            self.processed['errors'].append({
                'search_term': search_term,
                'error': str(e)
            })

        return False

    def get_summary(self) -> Dict[str, Any]:
        """Get processing summary"""
        return {
            **self.processed,
            'success': len(self.processed['errors']) == 0,
            'queued_percent': (
                self.processed['queued'] / max(self.processed['total_searched'], 1) * 100
            ) if self.processed['total_searched'] > 0 else 0
        }


class SeleniumAsyncWrapper:
    """Async wrapper for SeleniumMAMCrawler to integrate with async backend"""

    def __init__(self):
        """Initialize wrapper"""
        self.crawler = None
        self.loop = None

    async def initialize(self) -> bool:
        """Initialize Selenium crawler asynchronously

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate configuration
            if not SeleniumIntegrationConfig.validate():
                logger.error("Configuration validation failed")
                return False

            # Import here to avoid issues if selenium not installed
            from mam_selenium_crawler import SeleniumMAMCrawler

            self.loop = asyncio.get_event_loop()

            # Create crawler in thread pool
            params = SeleniumIntegrationConfig.get_crawler_params()
            self.crawler = await self.loop.run_in_executor(
                None,
                lambda: SeleniumMAMCrawler(**params)
            )

            logger.info("Selenium crawler initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Selenium crawler: {e}")
            return False

    async def search_books(self, books: List[Dict[str, str]]) -> Dict[str, Any]:
        """Search for books asynchronously

        Args:
            books: List of book dicts with 'title' and 'author' keys

        Returns:
            Result dict with success status and details
        """
        if not self.crawler:
            await self.initialize()

        if not self.crawler:
            return {
                'success': False,
                'error': 'Crawler initialization failed',
                'searched': 0,
                'found': 0
            }

        try:
            # Run blocking crawler in executor
            result = await self.loop.run_in_executor(
                None,
                self.crawler.run,
                books
            )

            return {
                'success': result,
                'searched': len(books),
                'found': len([b for b in books if b])  # Heuristic
            }

        except Exception as e:
            logger.error(f"Error during search: {e}")
            return {
                'success': False,
                'error': str(e),
                'searched': len(books),
                'found': 0
            }

    async def get_user_stats(self) -> Optional[Dict[str, Any]]:
        """Get user stats asynchronously"""
        if not self.crawler:
            await self.initialize()
        
        if not self.crawler:
            return None
            
        return await self.loop.run_in_executor(
            None,
            self.crawler.get_user_stats
        )

    async def cleanup(self):
        """Clean up resources"""
        if self.crawler:
            try:
                # Close WebDriver in executor if it has cleanup method
                if hasattr(self.crawler, 'driver'):
                    await self.loop.run_in_executor(
                        None,
                        lambda: self.crawler.driver.quit()
                    )
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")


async def run_selenium_top_search(missing_analysis: Optional[Dict] = None,
                                 books: Optional[List[Dict]] = None,
                                 db_session=None) -> Dict[str, Any]:
    """Run top search using Selenium crawler integrated with master manager
    
    This is the main integration point for MasterAudiobookManager.
    
    Args:
        missing_analysis: Optional output from detect_missing_books()
        books: Optional list of books to search
        db_session: Optional SQLAlchemy session for database operations
        
    Returns:
        Result dict with search statistics and status
    """
    logger.info("Starting Selenium top search...")
    
    # Generate search terms from analysis
    search_terms = []
    
    if missing_analysis:
        # Extract search terms from missing books analysis
        series_missing = missing_analysis.get('series_analysis', {}).get('missing_books', [])
        author_missing = missing_analysis.get('author_analysis', {}).get('missing_books', [])
        
        search_terms.extend(SeleniumSearchTermGenerator.from_series_analysis(series_missing))
        search_terms.extend(SeleniumSearchTermGenerator.from_author_analysis(author_missing))
        
    elif books:
        # Use provided books list
        search_terms = SeleniumSearchTermGenerator.from_missing_books_list(books)
    
    if not search_terms:
        logger.warning("No search terms generated")
        return {
            'success': False,
            'error': 'No search terms to process',
            'total_searched': 0,
            'found': 0,
            'queued': 0
        }
    
    # Initialize wrapper
    wrapper = SeleniumAsyncWrapper()
    if not await wrapper.initialize():
        return {
            'success': False,
            'error': 'Crawler initialization failed',
            'total_searched': 0,
            'found': 0,
            'queued': 0
        }
        
    # Fetch user stats (Ratio, BP) - Integration of mam-exporter features
    user_stats = await wrapper.get_user_stats()
    if user_stats:
        logger.info(f"User Stats: Ratio={user_stats.get('ratio')}, BP={user_stats.get('bonus_points')}")
    
    # Initialize result processor
    processor = SeleniumSearchResultProcessor(db_session)
    
    # Run searches
    for search_term in search_terms:
        try:
            # Extract search parameters
            search_query = search_term.get('title', '')
            if search_term.get('author'):
                search_query += f" {search_term['author']}"
            
            # Run search
            result = await wrapper.search_books([{'title': search_query, 'author': search_term.get('author', '')}])
            
            # Process result
            processor.process_search_result(result, search_term)
            
        except Exception as e:
            logger.error(f"Error searching for {search_term.get('title', 'Unknown')}: {e}")
            processor.processed['errors'].append({
                'search_term': search_term,
                'error': str(e)
            })
            
    # Cleanup
    await wrapper.cleanup()
    
    # Return summary
    summary = processor.get_summary()
    summary['success'] = True
    summary['user_stats'] = user_stats
    
    logger.info(f"Selenium search completed: {summary}")
    return summary


async def get_mam_user_stats() -> Optional[Dict[str, Any]]:
    """Fetch MAM user stats (Ratio, Bonus Points)"""
    wrapper = SeleniumAsyncWrapper()
    try:
        if await wrapper.initialize():
            return await wrapper.get_user_stats()
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
    finally:
        await wrapper.cleanup()
    return None


# For direct testing
if __name__ == "__main__":
    import asyncio

    async def test():
        """Test the integration"""
        logger.basicConfig(level=logging.INFO)

        # Test stats fetching
        print("Fetching stats...")
        stats = await get_mam_user_stats()
        print(f"Stats: {stats}")

        # Test with sample books
        books = [
            {'title': 'Mistborn', 'author': 'Brandon Sanderson'},
            {'title': 'The Poppy War', 'author': 'R.F. Kuang'},
        ]

        result = await run_selenium_top_search(books=books)
        print("Integration test result:")
        print(result)

    asyncio.run(test())
