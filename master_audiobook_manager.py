#!/usr/bin/env python3
"""
Master Audiobook Management System
==================================
Comprehensive system for:
1. Full metadata updates across all books and Audiobookshelf
2. Missing book detection (series priority, then author priority)
3. Top 10 audiobook search integration
4. On-demand execution capabilities

Usage:
    python master_audiobook_manager.py --help
    python master_audiobook_manager.py --update-metadata
    python master_audiobook_manager.py --missing-books
    python master_audiobook_manager.py --top-search
    python master_audiobook_manager.py --full-sync
"""

import asyncio
import os
import json
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv

# Force UTF-8 output on Windows with error handling
# Disabled in subprocess to avoid I/O errors
# if sys.platform == 'win32':
#     import io
#     try:
#         if hasattr(sys.stdout, 'buffer') and sys.stdout.isatty():
#             sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
#         if hasattr(sys.stderr, 'buffer') and sys.stderr.isatty():
#             sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
#     except (AttributeError, ValueError, io.UnsupportedOperation):
#         pass

# Import existing components with graceful fallbacks
try:
    from unified_metadata_aggregator import get_metadata
except ImportError:
    get_metadata = None

# Import Core Logic Modules
try:
    from mamcrawler.unified_config import config
    from mamcrawler.mam_categories import MAMCategories
    from mamcrawler.metadata_scanner import MetadataScanner
    from mamcrawler.event_pacing import EventAwarePacing
    from mamcrawler.author_series_completion import AuthorSeriesCompletion
    from mamcrawler.quality import QualityFilter
    from mamcrawler.metadata_maintenance import MetadataMaintenance
    from mamcrawler.qbittorrent_monitor import QBittorrentMonitor
    
    CORE_MODULES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Core modules not available: {e}")
    CORE_MODULES_AVAILABLE = False

# Import Selenium integration (NEW)
try:
    from selenium_integration import run_selenium_top_search, SeleniumIntegrationConfig, get_mam_user_stats
    SELENIUM_AVAILABLE = True
except ImportError as e:
    SELENIUM_AVAILABLE = False
    SeleniumIntegrationConfig = None

load_dotenv()

class MasterAudiobookManager:
    """
    Master controller for audiobook management across all systems.
    Integrates metadata sync, missing book detection, and on-demand search.
    """

    def __init__(self):
        self.setup_logging()
        self.setup_directories()

        # Initialize Core Modules
        if CORE_MODULES_AVAILABLE:
            self.logger.info("Initializing core logic modules...")
            
            # Mocks/Stubs for dependencies not yet fully integrated in this file
            # In a real scenario, we'd pass actual clients here.
            # For now, we'll rely on the modules' internal default initializations 
            # or pass None where they expect clients that we haven't instantiated here yet.
            # Note: Some modules like MetadataScanner need clients. 
            # We will instantiate them lazily or with what we have.
            
            # For this integration, we assume the modules can handle their own client creation 
            # or we need to create them here.
            # Let's create the shared clients first.
            
            # We need to instantiate clients if we want to pass them. 
            # However, the current MasterAudiobookManager uses direct requests/selenium.
            # The new modules use specific client classes (QBittorrentClient, AudiobookshelfClient).
            # We should probably instantiate those if we want to use the new modules fully.
            # But to keep it simple for this step, we will instantiate the logic modules.
            
            # Note: MetadataScanner needs qbt, abs, goodreads clients.
            # We'll instantiate them with None for now and let them fail gracefully or use their internal logic if robust.
            # Actually, looking at the code, they expect clients passed in.
            # We should probably update the legacy code to use the new clients eventually.
            # For now, let's initialize what we can.
            
            self.config = config
            self.categories = MAMCategories()
            self.pacing = EventAwarePacing()
            self.quality = QualityFilter()
            self.completion = AuthorSeriesCompletion()
            
            # These require clients, so we'll initialize them in setup_clients() or similar
            self.scanner = None 
            self.maintenance = None
            self.monitor = None
            
            self.logger.info("✓ Core logic modules initialized")
        else:
            self.logger.warning("⚠ Core logic modules NOT available - using legacy fallback")

        # Check Selenium integration availability
        self.selenium_available = SELENIUM_AVAILABLE and (
            SeleniumIntegrationConfig.validate() if SELENIUM_AVAILABLE else False
        )
        if self.selenium_available:
            self.logger.info("✓ Selenium integration AVAILABLE - will use for real searches")
        else:
            self.logger.warning("⚠ Selenium integration NOT available - searches will be limited")

        # Initialize Service Manager and check dependencies
        try:
            from mamcrawler.service_manager import ServiceManager
            self.service_manager = ServiceManager()
            self.service_manager.ensure_all_services()
        except ImportError:
            self.logger.warning("ServiceManager not available, skipping service checks")
        except Exception as e:
            self.logger.error(f"Error checking services: {e}")

        self.stats = {
            'started_at': datetime.now().isoformat(),
            'metadata_updates': 0,
            'missing_books_found': 0,
            'series_books_missing': 0,
            'author_books_missing': 0,
            'search_results': 0,
            'selenium_queued': 0,
            'selenium_duplicates': 0,
            'errors': []
        }

    def setup_logging(self):
        """Setup comprehensive logging."""
        self.log_file = f"master_manager_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_directories(self):
        """Create necessary directories."""
        self.output_dirs = {
            'metadata': Path("metadata_analysis"),
            'missing': Path("missing_books"),
            'search_results': Path("search_results"),
            'reports': Path("reports")
        }
        
        for dir_path in self.output_dirs.values():
            dir_path.mkdir(exist_ok=True)

    def setup_clients(self):
        """Initialize API clients for core modules."""
        if not CORE_MODULES_AVAILABLE:
            return

        try:
            from backend.integrations.qbittorrent_client import QBittorrentClient
            from backend.integrations.abs_client import AudiobookshelfClient
            from backend.integrations.hardcover_client import HardcoverClient
            
            # Initialize clients
            self.qbt_client = QBittorrentClient()
            self.abs_client = AudiobookshelfClient()
            
            # Initialize Hardcover client
            hardcover_token = os.getenv('HARDCOVER_TOKEN')
            if hardcover_token:
                self.hardcover_client = HardcoverClient(api_token=hardcover_token)
                self.logger.info("✓ Hardcover client initialized")
            else:
                self.logger.warning("⚠ HARDCOVER_TOKEN not set - metadata resolution will be limited")
                self.hardcover_client = None
            
            # Initialize dependent modules
            # Note: MetadataScanner will be updated to accept 'metadata_provider' instead of 'goodreads_client'
            # or we pass hardcover_client as the provider.
            self.scanner = MetadataScanner(
                qbt_client=self.qbt_client,
                abs_client=self.abs_client,
                goodreads_client=self.hardcover_client # Passing Hardcover as the metadata provider
            )
            
            self.maintenance = MetadataMaintenance(
                abs_client=self.abs_client,
                scanner=self.scanner
            )
            
            self.monitor = QBittorrentMonitor(
                qbt_client=self.qbt_client
            )
            
            self.logger.info("✓ API clients and dependent modules initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize clients: {e}")
            self.stats['errors'].append({
                'operation': 'setup_clients',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })

    async def update_all_metadata(self) -> Dict[str, Any]:
        """
        Update all books with comprehensive metadata.
        Runs audiobookshelf sync and additional metadata enrichment.
        """
        self.logger.info("=" * 70)
        self.logger.info("COMPREHENSIVE METADATA UPDATE")
        self.logger.info("=" * 70)

        try:
            # Ensure clients are set up
            if CORE_MODULES_AVAILABLE and self.maintenance is None:
                self.setup_clients()

            if CORE_MODULES_AVAILABLE and self.maintenance:
                # Step 1: Run weekly maintenance scan
                self.logger.info("Step 1: Running metadata maintenance scan...")
                results = await self.maintenance.run_weekly_scan()
                
                self.stats['metadata_updates'] = results.get('updated_count', 0)
                
                # Step 2: Analyze library (using new completion module if possible, or legacy)
                self.logger.info("Step 2: Analyzing library for metadata completeness...")
                # We can use the legacy analysis for now as it provides specific stats we use in reports
                # Or we can upgrade this too. Let's keep legacy analysis for reporting consistency for now.
                library_analysis = await self.analyze_library_metadata()

                # Step 3: Generate metadata report
                await self.generate_metadata_report(library_analysis)

                return {
                    'success': True,
                    'books_updated': self.stats['metadata_updates'],
                    'library_analysis': library_analysis,
                    'maintenance_results': results
                }
            else:
                self.logger.warning("Core modules not available, skipping metadata update")
                return {'success': False, 'error': 'Core modules not available'}

        except Exception as e:
            self.logger.error(f"Metadata update failed: {e}")
            self.stats['errors'].append({
                'operation': 'metadata_update',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            return {'success': False, 'error': str(e)}

    async def analyze_library_metadata(self) -> Dict[str, Any]:
        """Analyze the Audiobookshelf library for metadata completeness."""
        try:
            abs_url = os.getenv('ABS_URL', 'http://localhost:13378')
            abs_token = os.getenv('ABS_TOKEN', '')

            if not abs_token:
                self.logger.warning("ABS_TOKEN not set - analysis limited")
                return {'error': 'ABS_TOKEN not configured'}

            import requests
            headers = {'Authorization': f'Bearer {abs_token}'}

            # Get all libraries
            lib_response = requests.get(f"{abs_url}/api/libraries", headers=headers)
            if lib_response.status_code != 200:
                return {'error': f'Failed to get libraries: {lib_response.status_code}'}

            libraries = lib_response.json()
            if isinstance(libraries, dict) and 'libraries' in libraries:
                libraries = libraries['libraries']

            # Analyze each library
            analysis = {
                'total_libraries': len(libraries),
                'libraries': [],
                'overall_stats': {
                    'total_books': 0,
                    'books_with_series': 0,
                    'books_without_series': 0,
                    'books_with_author': 0,
                    'books_without_author': 0,
                    'books_with_isbn': 0,
                    'books_without_isbn': 0,
                    'books_with_genres': 0,
                    'books_without_genres': 0
                }
            }

            for library in libraries:
                lib_id = library.get('id')
                lib_name = library.get('name', 'Unknown')

                self.logger.info(f"Analyzing library: {lib_name}")

                # Get all items from library
                items_response = requests.get(
                    f"{abs_url}/api/libraries/{lib_id}/items",
                    headers=headers,
                    params={'limit': 10000}
                )

                if items_response.status_code != 200:
                    continue

                items = items_response.json().get('results', [])
                
                # Analyze each book
                lib_stats = {
                    'library_name': lib_name,
                    'library_id': lib_id,
                    'total_books': len(items),
                    'books_with_series': 0,
                    'books_without_series': 0,
                    'books_with_author': 0,
                    'books_without_author': 0,
                    'books_with_isbn': 0,
                    'books_without_isbn': 0,
                    'books_with_genres': 0,
                    'books_without_genres': 0,
                    'books_missing_metadata': []
                }

                for item in items:
                    metadata = item.get('media', {}).get('metadata', {})
                    
                    # Series analysis
                    if metadata.get('series'):
                        lib_stats['books_with_series'] += 1
                        analysis['overall_stats']['books_with_series'] += 1
                    else:
                        lib_stats['books_without_series'] += 1
                        analysis['overall_stats']['books_without_series'] += 1

                    # Author analysis
                    if metadata.get('authorName'):
                        lib_stats['books_with_author'] += 1
                        analysis['overall_stats']['books_with_author'] += 1
                    else:
                        lib_stats['books_without_author'] += 1
                        analysis['overall_stats']['books_without_author'] += 1

                    # ISBN analysis
                    if metadata.get('isbn'):
                        lib_stats['books_with_isbn'] += 1
                        analysis['overall_stats']['books_with_isbn'] += 1
                    else:
                        lib_stats['books_without_isbn'] += 1
                        analysis['overall_stats']['books_without_isbn'] += 1

                    # Genres analysis
                    if metadata.get('genres'):
                        lib_stats['books_with_genres'] += 1
                        analysis['overall_stats']['books_with_genres'] += 1
                    else:
                        lib_stats['books_without_genres'] += 1
                        analysis['overall_stats']['books_without_genres'] += 1

                    # Track books missing critical metadata
                    missing_metadata = []
                    if not metadata.get('series'):
                        missing_metadata.append('series')
                    if not metadata.get('authorName'):
                        missing_metadata.append('author')
                    if not metadata.get('isbn'):
                        missing_metadata.append('isbn')
                    if not metadata.get('genres'):
                        missing_metadata.append('genres')

                    if missing_metadata:
                        lib_stats['books_missing_metadata'].append({
                            'title': metadata.get('title', 'Unknown'),
                            'missing': missing_metadata
                        })

                analysis['overall_stats']['total_books'] += len(items)
                analysis['libraries'].append(lib_stats)

            return analysis

        except Exception as e:
            self.logger.error(f"Library analysis failed: {e}")
            return {'error': str(e)}



    async def get_audiobookshelf_library(self) -> Optional[List[Dict]]:
        """Get complete Audiobookshelf library data."""
        try:
            abs_url = os.getenv('ABS_URL', 'http://localhost:13378')
            abs_token = os.getenv('ABS_TOKEN', '')

            if not abs_token:
                self.logger.warning("ABS_TOKEN not set")
                return None

            import requests
            headers = {'Authorization': f'Bearer {abs_token}'}

            # Get all libraries
            lib_response = requests.get(f"{abs_url}/api/libraries", headers=headers)
            if lib_response.status_code != 200:
                return None

            libraries = lib_response.json()
            if isinstance(libraries, dict) and 'libraries' in libraries:
                libraries = libraries['libraries']

            # Get all books from all libraries
            all_books = []
            for library in libraries:
                lib_id = library.get('id')
                items_response = requests.get(
                    f"{abs_url}/api/libraries/{lib_id}/items",
                    headers=headers,
                    params={'limit': 10000}
                )

                if items_response.status_code == 200:
                    items = items_response.json().get('results', [])
                    all_books.extend(items)

            return all_books

        except Exception as e:
            self.logger.error(f"Failed to get Audiobookshelf library: {e}")
            return None

    async def analyze_series_missing_books(self, library_data: List[Dict]) -> Dict[str, Any]:
        """Analyze missing books in series."""
        # Group books by series
        series_groups = {}
        
        for book in library_data:
            metadata = book.get('media', {}).get('metadata', {})
            series = metadata.get('series', '').strip()
            
            if series:
                if series not in series_groups:
                    series_groups[series] = []
                
                series_book = {
                    'title': metadata.get('title', 'Unknown'),
                    'series_number': metadata.get('seriesSequence', ''),
                    'author': metadata.get('authorName', 'Unknown'),
                    'book_id': book.get('id')
                }
                series_groups[series].append(series_book)

        # Find missing books in each series
        missing_in_series = []
        
        for series_name, books in series_groups.items():
            if len(books) < 3:  # Only analyze series with 3+ books
                continue
                
            self.logger.info(f"Analyzing series: {series_name} ({len(books)} books found)")
            
            # Get current series numbers
            series_numbers = []
            for book in books:
                seq = book.get('series_number', '').strip()
                if seq:
                    try:
                        series_numbers.append(int(seq))
                    except ValueError:
                        pass
            
            if not series_numbers:
                continue
                
            # Find gaps in sequence
            series_numbers.sort()
            min_book = min(series_numbers)
            max_book = max(series_numbers)
            
            missing_numbers = []
            for i in range(min_book, max_book + 1):
                if i not in series_numbers:
                    missing_numbers.append(i)
            
            if missing_numbers:
                missing_in_series.append({
                    'series_name': series_name,
                    'author': books[0].get('author', 'Unknown'),
                    'total_books': max_book,
                    'found_books': len(books),
                    'missing_numbers': missing_numbers,
                    'missing_count': len(missing_numbers),
                    'existing_books': [b['title'] for b in books]
                })

        return {
            'total_series_analyzed': len(series_groups),
            'series_with_missing_books': len(missing_in_series),
            'missing_books': missing_in_series
        }

    async def analyze_author_missing_books(self, library_data: List[Dict]) -> Dict[str, Any]:
        """Analyze missing books by author."""
        # Group books by author
        author_groups = {}
        
        for book in library_data:
            metadata = book.get('media', {}).get('metadata', {})
            author = metadata.get('authorName', '').strip()
            
            if author and author != 'Unknown':
                if author not in author_groups:
                    author_groups[author] = []
                
                author_groups[author].append({
                    'title': metadata.get('title', 'Unknown'),
                    'year': metadata.get('publishedYear', ''),
                    'book_id': book.get('id')
                })

        # Analyze authors with multiple books
        authors_with_missing = []
        
        for author, books in author_groups.items():
            if len(books) < 2:  # Only analyze authors with 2+ books
                continue
                
            self.logger.info(f"Analyzing author: {author} ({len(books)} books found)")
            
            # Check for gaps in book titles (basic approach)
            # In a real implementation, you'd want to check against external sources
            # For now, we'll flag authors with many books as potential candidates
            
            if len(books) >= 5:
                authors_with_missing.append({
                    'author': author,
                    'total_books': len(books),
                    'existing_books': [b['title'] for b in books],
                    'note': 'High-volume author - likely has more books available'
                })

        return {
            'total_authors_analyzed': len(author_groups),
            'authors_with_missing': len(authors_with_missing),
            'missing_books': authors_with_missing
        }

    async def detect_missing_books(self) -> Dict[str, Any]:
        """
        Detect missing books in the library by analyzing series and authors.
        Orchestrates the analysis process.
        """
        self.logger.info("Detecting missing books...")
        
        # 1. Get library data
        library_data = await self.get_audiobookshelf_library()
        if not library_data:
            return {'success': False, 'error': 'Could not fetch library data'}
            
        # 2. Analyze series
        self.logger.info("Analyzing series gaps...")
        series_analysis = await self.analyze_series_missing_books(library_data)
        
        # 3. Analyze authors
        self.logger.info("Analyzing author gaps...")
        author_analysis = await self.analyze_author_missing_books(library_data)
        
        self.stats['missing_books_found'] = (
            series_analysis.get('series_with_missing_books', 0) + 
            author_analysis.get('authors_with_missing', 0)
        )
        self.stats['series_books_missing'] = series_analysis.get('series_with_missing_books', 0)
        self.stats['author_books_missing'] = author_analysis.get('authors_with_missing', 0)
        
        return {
            'success': True,
            'series_analysis': series_analysis,
            'author_analysis': author_analysis
        }

    async def run_top_10_search(self) -> Dict[str, Any]:
        """
        Run top 10 audiobook search using Selenium crawler with real MAM searches.
        Integrates with missing book detection for targeted, intelligent searches.
        PRODUCTION MODE: Actual data, actual downloads, actual metadata.
        """
        self.logger.info("=" * 70)
        self.logger.info("TOP 10 AUDIOBOOK SEARCH (SELENIUM - PRODUCTION MODE)")
        self.logger.info("=" * 70)

        try:
            if not self.selenium_available:
                self.logger.error("❌ Selenium integration not available")
                return {
                    'success': False,
                    'error': 'Selenium not configured',
                    'searched': 0,
                    'found': 0,
                    'queued': 0
                }

            # Check Pacing if available
            if CORE_MODULES_AVAILABLE and self.pacing:
                self.logger.info("Checking event-aware pacing...")
                try:
                    # Fetch real stats from MAM
                    user_stats = await get_mam_user_stats()
                    
                    if user_stats:
                        current_ratio = user_stats.get('ratio', 0.0)
                        bonus_points = user_stats.get('bonus_points', 0.0)
                        self.logger.info(f"MAM Stats: Ratio={current_ratio}, BP={bonus_points}")
                        
                        if not self.pacing.should_download_now(current_ratio):
                            self.logger.warning(f"⚠️ Pacing check failed (Ratio {current_ratio} too low). Aborting search.")
                            return {
                                'success': False,
                                'error': 'Pacing check failed',
                                'searched': 0,
                                'found': 0,
                                'queued': 0
                            }
                    else:
                        self.logger.warning("Could not fetch user stats, using cautious default (1.0)")
                        if not self.pacing.should_download_now(1.0):
                            return {
                                'success': False,
                                'error': 'Pacing check failed (default)',
                                'searched': 0,
                                'found': 0,
                                'queued': 0
                            }
                            
                except Exception as e:
                    self.logger.warning(f"Could not check pacing: {e}")

            # Step 1: Detect missing books to search for
            self.logger.info("Step 1: Detecting missing books in library...")
            missing_analysis = await self.detect_missing_books()

            if not missing_analysis.get('success'):
                self.logger.error("Missing book detection failed")
                return {
                    'success': False,
                    'error': 'Missing book detection failed',
                    'searched': 0,
                    'found': 0,
                    'queued': 0
                }

            # Step 2: Run Selenium search with actual MAM
            self.logger.info("Step 2: Running REAL searches on MyAnonamouse with Selenium...")
            self.logger.info(f"   - Series missing books: {missing_analysis['series_analysis'].get('series_with_missing_books', 0)}")
            self.logger.info(f"   - Authors analyzed: {missing_analysis['author_analysis'].get('total_authors_analyzed', 0)}")

            result = await run_selenium_top_search(missing_analysis=missing_analysis)

            # Update statistics
            self.stats['search_results'] = result.get('queued', 0)
            self.stats['selenium_queued'] = result.get('queued', 0)
            self.stats['selenium_duplicates'] = result.get('duplicates', 0)

            # Step 3: Generate report
            search_report = await self.generate_search_report({
                'searched': result.get('searched', 0),
                'found': result.get('found', 0),
                'queued': result.get('queued', 0),
                'duplicates': result.get('duplicates', 0),
                'mode': 'production'
            })

            self.logger.info("=" * 70)
            self.logger.info("SEARCH RESULTS SUMMARY:")
            self.logger.info(f"  Searched: {result.get('searched', 0)} terms")
            self.logger.info(f"  Found: {result.get('found', 0)} audiobooks")
            self.logger.info(f"  Queued: {result.get('queued', 0)} to qBittorrent")
            self.logger.info(f"  Duplicates skipped: {result.get('duplicates', 0)}")
            self.logger.info(f"  Report: {search_report}")
            self.logger.info("=" * 70)

            return {
                'success': result.get('success', False),
                'searched': result.get('searched', 0),
                'found': result.get('found', 0),
                'queued': result.get('queued', 0),
                'duplicates': result.get('duplicates', 0),
                'missing_analysis': missing_analysis,
                'report': search_report,
                'mode': 'production'
            }

        except Exception as e:
            error_msg = f"Top 10 search failed: {e}"
            self.logger.error(error_msg)
            self.logger.exception(e)
            self.stats['errors'].append({
                'operation': 'top_10_search',
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            })
            return {
                'success': False,
                'error': error_msg,
                'searched': 0,
                'found': 0,
                'queued': 0
            }

    async def collect_search_results(self) -> List[Dict]:
        """Collect all results from search output files."""
        results = []
        search_dir = Path("audiobookshelf_output")
        
        if not search_dir.exists():
            return results
            
        for json_file in search_dir.glob("audiobookshelf_*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    results.extend(data)
            except Exception as e:
                self.logger.warning(f"Could not read {json_file}: {e}")
                
        return results

    def select_top_10_audiobooks(self, results: List[Dict]) -> List[Dict]:
        """Select top 10 most relevant audiobooks."""
        # Sort by relevance factors
        def score_audiobook(audiobook):
            score = 0
            
            # Prefer newer entries (has crawled_at timestamp)
            if audiobook.get('crawled_at'):
                score += 1
                
            # Prefer entries with more complete metadata
            title = audiobook.get('title', '')
            author = audiobook.get('author', '')
            size = audiobook.get('size', '')
            
            if title: score += 2
            if author: score += 2
            if size: score += 1
            
            # Prefer certain keywords
            title_lower = title.lower()
            if any(keyword in title_lower for keyword in ['new', '2024', '2023', 'bestseller']):
                score += 1
                
            return score
        
        # Sort and select top 10
        sorted_results = sorted(results, key=score_audiobook, reverse=True)
        return sorted_results[:10]

    async def generate_reports(self) -> Dict[str, str]:
        """Generate comprehensive reports for all operations."""
        reports = {}
        
        try:
            # Create comprehensive summary report
            summary_report = await self.generate_summary_report()
            reports['summary'] = summary_report
            
            # Create individual operation reports
            if self.stats['metadata_updates'] > 0:
                reports['metadata'] = await self.get_latest_metadata_report()
                
            if self.stats['missing_books_found'] > 0:
                reports['missing_books'] = await self.get_latest_missing_report()
                
            if self.stats['search_results'] > 0:
                reports['search_results'] = await self.get_latest_search_report()
                
        except Exception as e:
            self.logger.error(f"Report generation failed: {e}")
            
        return reports

    async def generate_summary_report(self) -> str:
        """Generate overall summary report."""
        report = f"""
MASTER AUDIOBOOK MANAGEMENT SYSTEM - SUMMARY REPORT
==================================================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

OPERATIONS COMPLETED:
- Metadata Updates: {self.stats['metadata_updates']} books
- Missing Books Found: {self.stats['missing_books_found']} books
  - Series Missing: {self.stats['series_books_missing']} books
  - Author Missing: {self.stats['author_books_missing']} books
- Search Results: {self.stats['search_results']} audiobooks found
- Errors: {len(self.stats['errors'])} errors encountered

STARTED: {self.stats['started_at']}
COMPLETED: {datetime.now().isoformat()}

DETAILS:
"""
        
        if self.stats['errors']:
            report += "\nERRORS:\n"
            for error in self.stats['errors']:
                report += f"- {error['operation']}: {error['error']}\n"
        
        return report

    async def generate_metadata_report(self, analysis: Dict[str, Any]) -> str:
        """Generate metadata analysis report."""
        report_file = self.output_dirs['reports'] / f"metadata_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        report = f"# Metadata Analysis Report\n\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        if 'error' in analysis:
            report += f"**Error:** {analysis['error']}\n"
        else:
            stats = analysis.get('overall_stats', {})
            report += f"## Overall Statistics\n\n"
            report += f"- **Total Books:** {stats.get('total_books', 0)}\n"
            report += f"- **Books with Series:** {stats.get('books_with_series', 0)} ({stats.get('books_with_series', 0) / max(stats.get('total_books', 1), 1) * 100:.1f}%)\n"
            report += f"- **Books with Author:** {stats.get('books_with_author', 0)} ({stats.get('books_with_author', 0) / max(stats.get('total_books', 1), 1) * 100:.1f}%)\n"
            report += f"- **Books with ISBN:** {stats.get('books_with_isbn', 0)} ({stats.get('books_with_isbn', 0) / max(stats.get('total_books', 1), 1) * 100:.1f}%)\n"
            report += f"- **Books with Genres:** {stats.get('books_with_genres', 0)} ({stats.get('books_with_genres', 0) / max(stats.get('total_books', 1), 1) * 100:.1f}%)\n\n"
            
            report += f"## Library Breakdown\n\n"
            for lib in analysis.get('libraries', []):
                report += f"### {lib['library_name']}\n"
                report += f"- Total Books: {lib['total_books']}\n"
                report += f"- Series Coverage: {lib['books_with_series']}/{lib['total_books']}\n"
                report += f"- Author Coverage: {lib['books_with_author']}/{lib['total_books']}\n"
                report += f"- Books Missing Critical Metadata: {len(lib['books_missing_metadata'])}\n\n"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
            
        self.logger.info(f"Metadata report saved: {report_file}")
        return str(report_file)

    async def generate_missing_books_report(self, series_analysis: Dict, author_analysis: Dict) -> Dict[str, Any]:
        """Generate missing books report."""
        report_file = self.output_dirs['missing'] / f"missing_books_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        report = f"# Missing Books Report\n\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Series missing books
        series_missing = series_analysis.get('missing_books', [])
        report += f"## Series Missing Books ({len(series_missing)} series)\n\n"
        
        for series in series_missing[:20]:  # First 20
            report += f"### {series['series_name']}\n"
            report += f"- **Author:** {series['author']}\n"
            report += f"- **Total in Series:** {series['total_books']}\n"
            report += f"- **Found:** {series['found_books']}\n"
            report += f"- **Missing:** {', '.join(map(str, series['missing_numbers']))}\n"
            report += f"- **Existing:** {', '.join(series['existing_books'][:3])}{'...' if len(series['existing_books']) > 3 else ''}\n\n"
        
        # Author missing books  
        author_missing = author_analysis.get('missing_books', [])
        report += f"## Author Missing Books ({len(author_missing)} authors)\n\n"
        
        for author_data in author_missing[:20]:  # First 20
            report += f"### {author_data['author']}\n"
            report += f"- **Books in Library:** {author_data['total_books']}\n"
            report += f"- **Note:** {author_data['note']}\n\n"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
            
        self.logger.info(f"Missing books report saved: {report_file}")
        
        return {
            'report_file': str(report_file),
            'missing_books': series_missing + author_missing
        }

    async def generate_search_report(self, search_data) -> str:
        """Generate search results report - supports both production and legacy formats."""
        report_file = self.output_dirs['search_results'] / f"selenium_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        report = f"# Selenium Crawler Search Results (PRODUCTION)\n\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        # Handle new production format
        if isinstance(search_data, dict) and 'mode' in search_data:
            report += f"## Search Statistics\n\n"
            report += f"- **Books Searched:** {search_data.get('searched', 0)}\n"
            report += f"- **Found:** {search_data.get('found', 0)}\n"
            report += f"- **Queued to qBittorrent:** {search_data.get('queued', 0)}\n"
            report += f"- **Duplicates Skipped:** {search_data.get('duplicates', 0)}\n"
            report += f"- **Success Rate:** {(search_data.get('queued', 0) / max(search_data.get('found', 1), 1) * 100):.1f}%\n"
            report += f"- **Mode:** {search_data.get('mode', 'unknown').upper()}\n\n"

            report += "## Status\n\n"
            if search_data.get('queued', 0) > 0:
                report += f"✓ **ACTIVE**: {search_data.get('queued', 0)} audiobooks queued and downloading in qBittorrent\n\n"
            else:
                report += "⚠ No audiobooks queued (may need broader searches)\n\n"

        # Handle legacy format (list of audiobooks)
        elif isinstance(search_data, list):
            for i, audiobook in enumerate(search_data, 1):
                report += f"## {i}. {audiobook.get('title', 'Unknown Title')}\n"
                report += f"- **Author:** {audiobook.get('author', 'Unknown')}\n"
                report += f"- **Size:** {audiobook.get('size', 'Unknown')}\n"
                report += f"- **Category:** {audiobook.get('category', 'Unknown')}\n"
                report += f"- **Search Term:** {audiobook.get('search_term', 'Unknown')}\n\n"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        self.logger.info(f"Search report saved: {report_file}")
        return str(report_file)

    async def full_sync(self) -> Dict[str, Any]:
        """Run complete synchronization: metadata update + missing book detection + search."""
        self.logger.info("=" * 70)
        self.logger.info("FULL SYNCHRONIZATION")
        self.logger.info("=" * 70)

        results = {
            'metadata_update': None,
            'missing_books': None,
            'top_search': None
        }

        # Step 1: Update all metadata
        self.logger.info("Step 1: Updating metadata...")
        results['metadata_update'] = await self.update_all_metadata()
        await asyncio.sleep(2)  # Brief pause between operations

        # Step 2: Detect missing books
        self.logger.info("Step 2: Detecting missing books...")
        results['missing_books'] = await self.detect_missing_books()
        await asyncio.sleep(2)  # Brief pause between operations

        # Step 3: Run top 10 search
        self.logger.info("Step 3: Running top 10 search...")
        results['top_search'] = await self.run_top_10_search()
        await asyncio.sleep(2)  # Brief pause between operations

        # Step 4: Generate reports
        self.logger.info("Step 4: Generating comprehensive reports...")
        reports = await self.generate_reports()

        # Final summary
        await self.print_final_summary(results, reports)

        return results

    async def print_final_summary(self, results: Dict, reports: Dict):
        """Print final summary of all operations."""
        self.logger.info("\n" + "=" * 70)
        self.logger.info("FULL SYNCHRONIZATION COMPLETE")
        self.logger.info("=" * 70)

        # Results summary
        if results['metadata_update'] and results['metadata_update'].get('success'):
            self.logger.info(f"✓ Metadata Updated: {self.stats['metadata_updates']} books")

        if results['missing_books'] and results['missing_books'].get('success'):
            self.logger.info(f"✓ Missing Books: {self.stats['missing_books_found']} found")
            self.logger.info(f"  - Series Missing: {self.stats['series_books_missing']}")
            self.logger.info(f"  - Author Missing: {self.stats['author_books_missing']}")

        if results['top_search'] and results['top_search'].get('success'):
            self.logger.info(f"✓ Search Results: {self.stats['search_results']} audiobooks")

        # Reports summary
        if reports:
            self.logger.info(f"\n📊 Reports Generated:")
            for report_type, report_path in reports.items():
                self.logger.info(f"  - {report_type.title()}: {report_path}")

        # Errors summary
        if self.stats['errors']:
            self.logger.info(f"\n⚠️  Errors: {len(self.stats['errors'])} errors occurred")
            for error in self.stats['errors'][:3]:  # Show first 3
                self.logger.info(f"  - {error['operation']}: {error['error']}")

        self.logger.info("=" * 70)

    async def get_latest_metadata_report(self) -> str:
        """Get path to latest metadata report."""
        report_dir = self.output_dirs['reports']
        report_files = list(report_dir.glob("metadata_analysis_*.md"))
        if report_files:
            return str(max(report_files, key=os.path.getctime))
        return "No metadata report found"

    async def get_latest_missing_report(self) -> str:
        """Get path to latest missing books report."""
        missing_dir = self.output_dirs['missing']
        report_files = list(missing_dir.glob("missing_books_*.md"))
        if report_files:
            return str(max(report_files, key=os.path.getctime))
        return "No missing books report found"

    async def get_latest_search_report(self) -> str:
        """Get path to latest search report."""
        search_dir = self.output_dirs['search_results']
        report_files = list(search_dir.glob("top_10_search_*.md"))
        if report_files:
            return str(max(report_files, key=os.path.getctime))
        return "No search report found"


async def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Master Audiobook Management System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --update-metadata     # Update all book metadata
  %(prog)s --missing-books        # Detect missing books
  %(prog)s --top-search          # Run top 10 audiobook search
  %(prog)s --full-sync          # Run complete synchronization
  %(prog)s --status             # Show system status
        """
    )
    
    parser.add_argument('--update-metadata', action='store_true',
                       help='Update metadata for all books in Audiobookshelf')
    parser.add_argument('--missing-books', action='store_true',
                       help='Detect missing books (series priority, then author)')
    parser.add_argument('--top-search', action='store_true',
                       help='Run top 10 audiobook search using stealth crawler')
    parser.add_argument('--full-sync', action='store_true',
                       help='Run complete synchronization (all operations)')
    parser.add_argument('--status', action='store_true',
                       help='Show current system status and configuration')
    parser.add_argument('--dry-run', action='store_true',
                       help='Run operations in dry-run mode (no actual changes)')
    
    args = parser.parse_args()
    
    # Show status if requested
    if args.status:
        await show_system_status()
        return
    
    # Initialize manager
    manager = MasterAudiobookManager()
    
    try:
        # Execute requested operations
        if args.update_metadata:
            await manager.update_all_metadata()
        elif args.missing_books:
            await manager.detect_missing_books()
        elif args.top_search:
            await manager.run_top_10_search()
        elif args.full_sync:
            await manager.full_sync()
        else:
            parser.print_help()
            
    except KeyboardInterrupt:
        manager.logger.info("\n⚠️  Operation cancelled by user")
    except Exception as e:
        manager.logger.error(f"❌ Operation failed: {e}")
        import traceback
        traceback.print_exc()


async def show_system_status():
    """Show current system status and configuration."""
    # Use logging instead of print to avoid I/O issues in non-interactive environments
    logger = logging.getLogger(__name__)

    status_lines = [
        "=" * 70,
        "MASTER AUDIOBOOK MANAGER - SYSTEM STATUS",
        "=" * 70,
        "",
        "🔧 Configuration Status:"
    ]

    env_vars = [
        ('ABS_URL', 'Audiobookshelf URL'),
        ('ABS_TOKEN', 'Audiobookshelf Token'),
        ('MAM_USERNAME', 'MyAnonamouse Username'),
        ('MAM_PASSWORD', 'MyAnonamouse Password'),
        ('QB_HOST', 'qBittorrent Host'),
        ('QB_PORT', 'qBittorrent Port')
    ]

    for var, description in env_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'PASSWORD' in var or 'TOKEN' in var:
                display_value = "*" * (len(value) - 4) + value[-4:]
            else:
                display_value = value
            status_lines.append(f"  ✓ {description}: {display_value}")
        else:
            status_lines.append(f"  ❌ {description}: Not set")

    # Check directories
    status_lines.append("")
    status_lines.append("📁 Directory Status:")
    manager = MasterAudiobookManager()
    for dir_name, dir_path in manager.output_dirs.items():
        if dir_path.exists():
            status_lines.append(f"  ✓ {dir_name.title()}: {dir_path}")
        else:
            status_lines.append(f"  ❌ {dir_name.title()}: Not created")

    # Check log file
    status_lines.append("")
    status_lines.append("📋 Logging:")
    if hasattr(manager, 'log_file'):
        status_lines.append(f"  ✓ Log file: {manager.log_file}")

    status_lines.append("")
    status_lines.append("=" * 70)

    # Output all status lines
    for line in status_lines:
        logger.info(line)


if __name__ == "__main__":
    asyncio.run(main())