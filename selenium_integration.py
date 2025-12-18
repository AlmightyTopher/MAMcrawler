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

from dotenv import load_dotenv
load_dotenv()

try:
    from config_system import get_config_value, get_secret
except ImportError:
    # Fallback if config_system not found
    import sys
    sys.path.append(str(Path(__file__).parent))
    from config_system import get_config_value, get_secret

logger = logging.getLogger(__name__)


class SeleniumIntegrationConfig:
    """Configuration for Selenium integration"""

    @staticmethod
    def validate() -> bool:
        """Validate all required configuration"""
        # Functional check for credentials
        if not get_config_value('api_endpoints.mam_username') or not get_config_value('api_endpoints.mam_password'):
            logger.error("SeleniumIntegration: Missing MAM credentials in config")
            return False
        return True

    @staticmethod
    def get_crawler_params() -> Dict[str, str]:
        """Get parameters for SeleniumMAMCrawler initialization"""
        qb_host = get_config_value('crawler.qb_host') or os.getenv('QB_HOST', 'http://localhost')
        qb_port = get_config_value('crawler.qb_port') or os.getenv('QB_PORT', '8080')
        qb_url = f"{qb_host}:{qb_port}" if not qb_host.endswith(qb_port) else qb_host

        return {
            'email': get_config_value('api_endpoints.mam_username'),
            'password': get_config_value('api_endpoints.mam_password'),
            'qb_url': qb_url,
            'qb_user': get_config_value('crawler.qb_username') or os.getenv('QB_USERNAME', 'admin'),
            'qb_pass': get_config_value('crawler.qb_password') or os.getenv('QB_PASSWORD', ''),
            'headless': get_config_value('crawler.headless', True)
        }


class SeleniumSearchTermGenerator:
    """Generate optimized search terms from missing books analysis"""

    @staticmethod
    def from_series_analysis(series_missing: List[Dict]) -> List[Dict[str, Any]]:
        """Generate search terms from series missing book analysis"""
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
        """Generate search terms from author missing book analysis"""
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
        """Generate search terms from simple missing books list"""
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
        self.db_session = db_session
        self.processed = {
            'total_searched': 0,
            'found': 0,
            'queued': 0,
            'duplicates': 0,
            'errors': []
        }

    def check_duplicate(self, title: str, author: str, magnet_link: str) -> bool:
        if not self.db_session:
            return False

        try:
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

            if self.check_duplicate(title, author, magnet_link):
                self.processed['duplicates'] += 1
                return False

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
        return {
            **self.processed,
            'success': len(self.processed['errors']) == 0,
            'queued_percent': (
                self.processed['queued'] / max(self.processed['total_searched'], 1) * 100
            ) if self.processed['total_searched'] > 0 else 0
        }


_GLOBAL_CRAWLER_INSTANCE = None

class SeleniumAsyncWrapper:
    """Async wrapper for SeleniumMAMCrawler to integrate with async backend"""

    def __init__(self):
        self.loop = None

    async def initialize(self) -> bool:
        global _GLOBAL_CRAWLER_INSTANCE
        
        try:
            if not SeleniumIntegrationConfig.validate():
                logger.error("Configuration validation failed")
                return False

            self.loop = asyncio.get_event_loop()

            if _GLOBAL_CRAWLER_INSTANCE:
                try:
                    await self.loop.run_in_executor(
                        None,
                        lambda: _GLOBAL_CRAWLER_INSTANCE.driver.title
                    )
                    logger.info("Reusing existing Selenium session")
                    return True
                except Exception:
                    logger.warning("Existing Selenium usage failed, restarting...")
                    _GLOBAL_CRAWLER_INSTANCE = None

            from mam_selenium_crawler import SeleniumMAMCrawler

            params = SeleniumIntegrationConfig.get_crawler_params()
            
            new_crawler = await self.loop.run_in_executor(
                None,
                lambda: SeleniumMAMCrawler(**params)
            )
            
            _GLOBAL_CRAWLER_INSTANCE = new_crawler
            logger.info("Selenium crawler initialized successfully (Persistent Session)")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Selenium crawler: {e}")
            return False
            
    @property
    def crawler(self):
        global _GLOBAL_CRAWLER_INSTANCE
        return _GLOBAL_CRAWLER_INSTANCE

    async def search_books(self, books: List[Dict[str, str]]) -> Dict[str, Any]:
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
            result = await self.loop.run_in_executor(
                None,
                self.crawler.run,
                books
            )

            return {
                'success': result,
                'searched': len(books),
                'found': len([b for b in books if b])
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
        if not self.crawler:
            await self.initialize()
        
        if not self.crawler:
            return None
            
        return await self.loop.run_in_executor(
            None,
            self.crawler.get_user_stats
        )

    async def discover_top_books(self, limit: int = 10) -> List[Dict[str, str]]:
        if not self.crawler:
            await self.initialize()

        if not self.crawler:
            return []

        return await self.loop.run_in_executor(
            None,
            lambda: self.crawler.discover_top_books(limit)
        )

    async def cleanup(self):
        if self.crawler:
            try:
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
    """Run top search using Selenium crawler integrated with master manager"""
    logger.info("Starting Selenium top search...")
    
    # Generate search terms from analysis
    search_terms = []
    
    if missing_analysis:
        series_missing = missing_analysis.get('series_analysis', {}).get('missing_books', [])
        author_missing = missing_analysis.get('author_analysis', {}).get('missing_books', [])
        
        search_terms.extend(SeleniumSearchTermGenerator.from_series_analysis(series_missing))
        search_terms.extend(SeleniumSearchTermGenerator.from_author_analysis(author_missing))
        
    elif books:
        search_terms = SeleniumSearchTermGenerator.from_missing_books_list(books)
    
    else:
        # User requested "Top Search" without specific targets -> Auto-Discovery Mode
        logger.info("No targets provided. Initiating Top 10 Discovery Mode for Audiobooks...")
        
        wrapper = SeleniumAsyncWrapper()
        if not await wrapper.initialize():
            return {'success': False, 'error': 'Crawler initialization failed'}
        
        logger.info("Browsing MAM for Top 10 Audiobooks...")
        top_books = await wrapper.discover_top_books()
        
        abs_url = get_config_value('api_endpoints.abs_url')
        abs_token = get_config_value('api_endpoints.abs_token') or get_secret('abs_token')
        existing_titles = set()
        
        if abs_url and abs_token:
            try:
                logger.info("Fetching existing library from Audiobookshelf for deduplication...")
                from backend.integrations.abs_client import AudiobookshelfClient
                async with AudiobookshelfClient(abs_url, abs_token) as abs_client:
                    library_items = await abs_client.get_library_items()
                    for item in library_items:
                        meta = item.get('media', {}).get('metadata', {})
                        title = meta.get('title')
                        if title:
                            existing_titles.add(title.lower().strip())
                logger.info(f"Loaded {len(existing_titles)} existing books from ABS for comparison.")
            except Exception as e:
                logger.error(f"Failed to fetch ABS library: {e}")
        
        books = []
        if top_books:
            logger.info(f"Processing {len(top_books)} discovered trending audiobooks...")
            skipped_count = 0
            for b in top_books:
                title_norm = b['title'].lower().strip()
                if title_norm in existing_titles:
                    logger.info(f"   [SKIP] '{b['title']}' - Already exists in Audiobookshelf library.")
                    skipped_count += 1
                    continue
                books.append({'title': b['title'], 'author': b['author']})
            
            logger.info(f"Queueing {len(books)} new books for Prowlarr search (Skipped {skipped_count} existing).")
            search_terms = SeleniumSearchTermGenerator.from_missing_books_list(books)
        else:
            logger.warning("Failed to discover top books.")
            search_terms = []

    if not search_terms:
        logger.warning("No search terms generated")
        return {
            'success': False,
            'error': 'No search terms to process',
            'total_searched': 0,
            'found': 0,
            'queued': 0
        }
    
    wrapper = SeleniumAsyncWrapper()
    if not await wrapper.initialize():
        return {
            'success': False,
            'error': 'Crawler initialization failed',
            'total_searched': 0,
            'found': 0,
            'queued': 0
        }
        
    user_stats = await wrapper.get_user_stats()
    if user_stats:
        logger.info(f"User Stats: Ratio={user_stats.get('ratio')}, BP={user_stats.get('bonus_points')}")
    
    # Initialize Prowlarr Client with ConfigSystem
    prowlarr_url = get_config_value('api_endpoints.prowlarr_url') or os.getenv('PROWLARR_URL', 'http://localhost:9696')
    prowlarr_api_key = get_config_value('api_endpoints.prowlarr_api_key') or get_secret('prowlarr_api_key') or os.getenv('PROWLARR_API_KEY')
    
    use_prowlarr = False
    if prowlarr_url and prowlarr_api_key:
        from backend.integrations.prowlarr_client import ProwlarrClient
        from mamcrawler.quality import QualityFilter
        use_prowlarr = True
        logger.info(f"✅ PROWLARR ACTIVE (URL: {prowlarr_url})")
    else:
        logger.error("❌ PROWLARR DISABLED (Missing API KEY or URL). Fallback to Selenium.")

    processor = SeleniumSearchResultProcessor(db_session)
    quality_filter = QualityFilter() if use_prowlarr else None
    
    for search_term in search_terms:
        try:
            search_query = search_term.get('title', '')
            if not search_query or len(search_query) < 2:
                logger.warning(f"Skipping empty/invalid title: '{search_query}'")
                continue
            
            logger.info(f"   -> Searching for: '{search_query}' (Context: {search_term.get('context', 'Manual')})...")
            
            found_magnet = None
            found_title = None
            found_author = None
            
            if use_prowlarr:
                logger.info(f"   -> [API] Searching Prowlarr for: '{search_query}'")
                try:
                    async with ProwlarrClient(prowlarr_url, prowlarr_api_key) as client:
                        results = await client.get_search_results(query=search_query, limit=20, min_seeders=1)
                        best_match = None
                        if results:
                            filtered_results = quality_filter.filter_and_sort_prowlarr_results(results, search_query) if quality_filter else results
                            if filtered_results:
                                best_match = filtered_results[0]
                        
                        if best_match:
                            found_magnet = await client.add_to_download_queue(best_match)
                            found_title = best_match.get('title')
                            found_author = search_term.get('author')
                            if found_magnet:
                                logger.info(f"      [API] Found match: {found_title}")
                            else:
                                logger.warning(f"      [API] Match found but no magnet link extracted.")
                        else:
                            logger.info(f"      [API] No results found for '{search_query}'")
                except Exception as e:
                    logger.error(f"      [API] Prowlarr API failed: {e}")
            
            else:
                result = await wrapper.search_books([{'title': search_query, 'author': search_term.get('author', '')}])
                # Selenium result processing is handled better by just using the API if possible
                     
            if found_magnet:
                logger.info(f"      -> Queueing to qBittorrent...")
                try:
                    wrapper.crawler.qb_client.torrents_add(
                        urls=found_magnet,
                        category='audiobooks',
                        tags=['prowlarr', 'mam-crawler', 'auto'],
                        is_paused=False
                    )
                    logger.info("      ✓ SUCCESS: Queued!")
                    
                    processor.process_search_result({
                        'title': found_title,
                        'author': found_author,
                        'magnet_link': found_magnet
                    }, search_term)
                    processor.processed['found'] += 1
                    processor.processed['queued'] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to queue to qB: {e}")
                    processor.processed['errors'].append({'search_term': search_term, 'error': str(e)})

            elif not use_prowlarr and 'result' in locals() and result.get('success'):
                logger.info(f"      [SELENIUM] Found {result.get('found', 0)} results.")
                processor.process_search_result(result, search_term)
            
            elif not use_prowlarr:
                 logger.info(f"      [SELENIUM] No results found.")

        except Exception as e:
            logger.error(f"Error searching for {search_term.get('title', 'Unknown')}: {e}")
            processor.processed['errors'].append({
                'search_term': search_term,
                'error': str(e)
            })
            
    logger.info("Selenium session kept open for future requests.")
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
    return None


if __name__ == "__main__":
    import asyncio
    async def test():
        logging.basicConfig(level=logging.INFO)
        print("Fetching stats...")
        stats = await get_mam_user_stats()
        print(f"Stats: {stats}")
        books = [{'title': 'Mistborn', 'author': 'Brandon Sanderson'}]
        result = await run_selenium_top_search(books=books)
        print("Integration test result:")
        print(result)
    asyncio.run(test())
