#!/usr/bin/env python3
"""
Audiobook Gap Analysis & Automated Acquisition System

This module orchestrates the complete workflow for:
1. Detecting missing books in series
2. Detecting missing books by author
3. Searching MAM for missing books
4. Queuing downloads automatically
5. Generating reports

Integrates with:
- Audiobookshelf (library scanning)
- Goodreads (metadata and series info)
- MAM (torrent search)
- qBittorrent (download management)
- PostgreSQL (data persistence)
"""

import asyncio
import aiohttp
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from difflib import SequenceMatcher
from dotenv import load_dotenv

from bs4 import BeautifulSoup
import qbittorrentapi

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('gap_analyzer.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class AudiobookGapAnalyzer:
    """
    Main orchestrator for library gap analysis and automated acquisition.

    Workflow:
    1. Scan Audiobookshelf library
    2. Identify series and authors
    3. Query Goodreads for complete series/author lists
    4. Calculate gaps
    5. Search MAM for missing books
    6. Queue downloads
    7. Generate reports
    """

    def __init__(self):
        # Audiobookshelf settings
        self.abs_url = os.getenv('ABS_URL', 'http://localhost:13378')
        self.abs_token = os.getenv('ABS_TOKEN', '')

        # MAM settings
        self.mam_username = os.getenv('MAM_USERNAME')
        self.mam_password = os.getenv('MAM_PASSWORD')
        self.mam_base_url = "https://www.myanonamouse.net"
        self.mam_session_id = "gap_analyzer_session"
        self.mam_authenticated = False

        # qBittorrent settings
        self.qb_client = None
        self._setup_qbittorrent()

        # Configuration
        self.config = {
            'max_downloads_per_run': int(os.getenv('GAP_MAX_DOWNLOADS', '10')),
            'series_priority': os.getenv('GAP_SERIES_PRIORITY', 'true').lower() == 'true',
            'author_priority': os.getenv('GAP_AUTHOR_PRIORITY', 'true').lower() == 'true',
            'min_seeds': int(os.getenv('MAM_MIN_SEEDS', '1')),
            'title_match_threshold': float(os.getenv('MAM_TITLE_MATCH_THRESHOLD', '0.7')),
            'human_delay_min': 10,
            'human_delay_max': 30,
        }

        # State tracking
        self.state_file = Path("gap_analyzer_state.json")
        self.state = self._load_state()

        # Statistics
        self.stats = {
            'started_at': datetime.now().isoformat(),
            'library_books': 0,
            'series_analyzed': 0,
            'authors_analyzed': 0,
            'gaps_identified': 0,
            'series_gaps': 0,
            'author_gaps': 0,
            'torrents_found': 0,
            'downloads_queued': 0,
            'duplicates_skipped': 0,
            'no_results': 0,
            'errors': []
        }

        # Results
        self.library_books = []
        self.series_map = {}  # {series_name: [books]}
        self.author_map = {}  # {author_name: [books]}
        self.gaps = []  # List of missing books
        self.downloads_queued = []

        logger.info("AudiobookGapAnalyzer initialized")

    def _setup_qbittorrent(self):
        """Setup qBittorrent client connection."""
        try:
            qb_host = os.getenv('QBITTORRENT_URL', 'http://localhost:52095')
            qb_user = os.getenv('QBITTORRENT_USERNAME', 'admin')
            qb_pass = os.getenv('QBITTORRENT_PASSWORD', '')

            self.qb_client = qbittorrentapi.Client(
                host=qb_host,
                username=qb_user,
                password=qb_pass
            )
            self.qb_client.auth_log_in()
            logger.info(f"Connected to qBittorrent {self.qb_client.app.version}")
        except Exception as e:
            logger.warning(f"qBittorrent connection failed: {e}")
            self.qb_client = None

    def _load_state(self) -> Dict:
        """Load analyzer state for resume capability."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load state: {e}")

        return {
            'last_run': None,
            'completed_searches': [],
            'failed_searches': [],
            'queued_downloads': []
        }

    def _save_state(self):
        """Save current state."""
        self.state['last_run'] = datetime.now().isoformat()
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save state: {e}")

    async def run_full_analysis(self, analyze_only: bool = False) -> Dict[str, Any]:
        """
        Execute complete gap analysis and acquisition workflow.

        Args:
            analyze_only: If True, only detect gaps without downloading

        Returns:
            Complete results including stats, gaps, and downloads
        """
        logger.info("=" * 80)
        logger.info("STARTING AUDIOBOOK GAP ANALYSIS")
        logger.info("=" * 80)

        try:
            # Phase 1: Scan library
            logger.info("\n--- PHASE 1: Scanning Library ---")
            await self._scan_audiobookshelf_library()

            if not self.library_books:
                logger.error("No books found in library")
                return self._generate_report(success=False, error="No books in library")

            # Phase 2: Analyze series and authors
            logger.info("\n--- PHASE 2: Analyzing Series & Authors ---")
            await self._analyze_series()
            await self._analyze_authors()

            # Phase 3: Identify gaps
            logger.info("\n--- PHASE 3: Identifying Gaps ---")
            await self._identify_gaps()

            if not self.gaps:
                logger.info("No gaps identified - library appears complete!")
                return self._generate_report(success=True)

            if analyze_only:
                logger.info("Analyze-only mode - skipping download phase")
                return self._generate_report(success=True)

            # Phase 4: Search for missing books
            logger.info("\n--- PHASE 4: Searching MAM ---")
            await self._search_missing_books()

            # Phase 5: Queue downloads
            logger.info("\n--- PHASE 5: Queuing Downloads ---")
            await self._queue_downloads()

            # Save state
            self._save_state()

            return self._generate_report(success=True)

        except Exception as e:
            logger.error(f"Gap analysis failed: {e}", exc_info=True)
            self.stats['errors'].append(str(e))
            return self._generate_report(success=False, error=str(e))

    async def _scan_audiobookshelf_library(self):
        """Scan Audiobookshelf library for all books."""
        logger.info("Scanning Audiobookshelf library...")

        if not self.abs_token:
            logger.error("ABS_TOKEN not configured")
            return

        try:
            headers = {'Authorization': f'Bearer {self.abs_token}'}

            async with aiohttp.ClientSession() as session:
                # Get libraries
                async with session.get(
                    f"{self.abs_url}/api/libraries",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to get libraries: {resp.status}")
                        return

                    libraries_data = await resp.json()
                    libraries = libraries_data.get('libraries', [])

                if not libraries:
                    logger.warning("No libraries found in Audiobookshelf")
                    return

                # Get items from each library
                for library in libraries:
                    lib_id = library.get('id')
                    lib_name = library.get('name', 'Unknown')

                    logger.info(f"Scanning library: {lib_name}")

                    async with session.get(
                        f"{self.abs_url}/api/libraries/{lib_id}/items",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            items = data.get('results', [])

                            for item in items:
                                book = self._extract_book_metadata(item)
                                if book:
                                    self.library_books.append(book)
                        else:
                            logger.warning(f"Failed to get items from {lib_name}: {resp.status}")

            self.stats['library_books'] = len(self.library_books)
            logger.info(f"Found {len(self.library_books)} books in library")

        except Exception as e:
            logger.error(f"Error scanning library: {e}")
            self.stats['errors'].append(f"Library scan error: {str(e)}")

    def _extract_book_metadata(self, item: Dict) -> Optional[Dict]:
        """Extract relevant metadata from an Audiobookshelf item."""
        try:
            media = item.get('media', {})
            metadata = media.get('metadata', {})

            return {
                'abs_id': item.get('id'),
                'title': metadata.get('title', '').strip(),
                'author': metadata.get('authorName', '').strip(),
                'series': metadata.get('seriesName', '').strip() or None,
                'series_sequence': metadata.get('seriesSequence', '').strip() or None,
                'isbn': metadata.get('isbn', ''),
                'asin': metadata.get('asin', ''),
            }
        except Exception as e:
            logger.debug(f"Error extracting metadata: {e}")
            return None

    async def _analyze_series(self):
        """Group library books by series."""
        logger.info("Analyzing series...")

        self.series_map = defaultdict(list)

        for book in self.library_books:
            if book.get('series'):
                series_key = f"{book['series']}|{book['author']}"
                self.series_map[series_key].append(book)

        self.stats['series_analyzed'] = len(self.series_map)
        logger.info(f"Found {len(self.series_map)} unique series in library")

        # Log series with multiple books
        for series_key, books in self.series_map.items():
            if len(books) > 1:
                series_name = series_key.split('|')[0]
                logger.debug(f"  {series_name}: {len(books)} books")

    async def _analyze_authors(self):
        """Group library books by author."""
        logger.info("Analyzing authors...")

        self.author_map = defaultdict(list)

        for book in self.library_books:
            if book.get('author'):
                self.author_map[book['author']].append(book)

        self.stats['authors_analyzed'] = len(self.author_map)
        logger.info(f"Found {len(self.author_map)} unique authors in library")

    async def _identify_gaps(self):
        """Identify gaps in series and author collections."""
        logger.info("Identifying gaps...")

        # Identify series gaps
        if self.config['series_priority']:
            await self._identify_series_gaps()

        # Identify author gaps
        if self.config['author_priority']:
            await self._identify_author_gaps()

        # Sort gaps by priority
        self.gaps.sort(key=lambda x: (x.get('priority', 99), x.get('series_name', '')))

        self.stats['gaps_identified'] = len(self.gaps)
        logger.info(f"Total gaps identified: {len(self.gaps)}")

    async def _identify_series_gaps(self):
        """Identify missing books in series using Goodreads."""
        logger.info("Checking series completeness...")

        async with aiohttp.ClientSession() as session:
            for series_key, books in self.series_map.items():
                series_name, author = series_key.split('|', 1)

                # Get owned sequence numbers
                owned_sequences = set()
                for book in books:
                    seq = book.get('series_sequence')
                    if seq:
                        try:
                            owned_sequences.add(float(seq))
                        except ValueError:
                            pass

                # Query Goodreads for complete series
                total_books, all_books = await self._get_series_from_goodreads(
                    session, series_name, author
                )

                if total_books == 0:
                    logger.debug(f"No Goodreads data for series: {series_name}")
                    continue

                # Find missing books
                missing_count = 0
                for book_info in all_books:
                    seq = book_info.get('sequence')
                    title = book_info.get('title', '')

                    # Skip if we already own this sequence
                    if seq and seq in owned_sequences:
                        continue

                    # Skip if title matches owned book (fuzzy)
                    if self._is_title_owned(title, books):
                        continue

                    # This is a gap
                    gap = {
                        'type': 'series_gap',
                        'title': title,
                        'author': author,
                        'series_name': series_name,
                        'series_sequence': seq,
                        'priority': 1,  # Series gaps are high priority
                        'reason': f"Missing book {seq} in series {series_name}",
                        'search_result': None,
                        'download_status': 'identified'
                    }
                    self.gaps.append(gap)
                    missing_count += 1

                if missing_count > 0:
                    logger.info(f"  {series_name}: {missing_count} missing (owned {len(books)}/{total_books})")
                    self.stats['series_gaps'] += missing_count

                # Rate limiting
                await asyncio.sleep(0.5)

    async def _get_series_from_goodreads(
        self,
        session: aiohttp.ClientSession,
        series_name: str,
        author: str
    ) -> Tuple[int, List[Dict]]:
        """
        Get complete series info from Goodreads.

        Returns:
            (total_books, [{'title': ..., 'sequence': ...}, ...])
        """
        try:
            # Search for series on Goodreads
            search_url = "https://www.goodreads.com/search"
            params = {
                'q': f"{series_name} {author}",
                'search_type': 'books'
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            async with session.get(
                search_url,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    return 0, []

                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Find books in search results
                results = soup.find_all('tr', itemtype='http://schema.org/Book')

                books = []
                for result in results[:20]:  # Check first 20 results
                    title_link = result.find('a', class_='bookTitle')
                    if not title_link:
                        continue

                    full_title = title_link.get_text(strip=True)

                    # Parse series info from title
                    # Pattern: "Book Title (Series Name, #1)"
                    match = re.search(
                        rf'\(.*{re.escape(series_name[:20])}.*,?\s*#([\d.]+)\)',
                        full_title,
                        re.IGNORECASE
                    )

                    if match:
                        seq = float(match.group(1))
                        # Extract clean title
                        title = re.sub(r'\s*\([^)]+\)\s*$', '', full_title).strip()
                        books.append({'title': title, 'sequence': seq})

                return len(books), books

        except Exception as e:
            logger.debug(f"Error getting series from Goodreads: {e}")
            return 0, []

    async def _identify_author_gaps(self):
        """Identify missing books by author using Goodreads."""
        logger.info("Checking author completeness...")

        # For now, we'll skip author gap analysis as it's more complex
        # and would require extensive Goodreads scraping for each author's
        # complete bibliography. This can be implemented in a future version.

        logger.info("  Author gap analysis - feature coming soon")

    def _is_title_owned(self, title: str, owned_books: List[Dict]) -> bool:
        """Check if a title (fuzzy match) is already owned."""
        title_lower = title.lower().strip()

        for book in owned_books:
            owned_title = book.get('title', '').lower().strip()

            # Exact match
            if title_lower == owned_title:
                return True

            # Substring match
            if title_lower in owned_title or owned_title in title_lower:
                return True

            # Fuzzy match
            ratio = SequenceMatcher(None, title_lower, owned_title).ratio()
            if ratio >= 0.85:
                return True

        return False

    async def _search_missing_books(self):
        """Search MAM for missing books."""
        logger.info(f"Searching MAM for {len(self.gaps)} missing books...")

        # Import crawler for MAM search
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

        # Create browser config
        browser_config = BrowserConfig(
            headless=False,
            viewport_width=1920,
            viewport_height=1080,
            verbose=False,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Authenticate with MAM
            if not await self._authenticate_mam(crawler):
                logger.error("MAM authentication failed")
                return

            # Search for each gap (up to max_downloads)
            search_count = 0
            for gap in self.gaps:
                if search_count >= self.config['max_downloads_per_run']:
                    logger.info(f"Reached max downloads per run ({self.config['max_downloads_per_run']})")
                    break

                # Skip if already searched
                search_key = f"{gap['title']}|{gap['author']}"
                if search_key in self.state['completed_searches']:
                    logger.debug(f"Already searched: {gap['title']}")
                    continue

                # Search MAM
                result = await self._search_mam_for_book(
                    crawler,
                    gap['title'],
                    gap['author'],
                    gap.get('series_name')
                )

                if result:
                    gap['search_result'] = result
                    gap['download_status'] = 'found'
                    self.stats['torrents_found'] += 1
                    search_count += 1
                else:
                    gap['download_status'] = 'not_found'
                    self.stats['no_results'] += 1
                    self.state['failed_searches'].append(search_key)

                self.state['completed_searches'].append(search_key)

                # Human-like delay
                delay = self.config['human_delay_min'] + (
                    (self.config['human_delay_max'] - self.config['human_delay_min']) *
                    (search_count / self.config['max_downloads_per_run'])
                )
                await asyncio.sleep(delay)

        logger.info(f"Found {self.stats['torrents_found']} torrents on MAM")

    async def _authenticate_mam(self, crawler) -> bool:
        """Authenticate with MyAnonamouse."""
        if self.mam_authenticated:
            return True

        if not self.mam_username or not self.mam_password:
            logger.error("MAM_USERNAME and MAM_PASSWORD must be set")
            return False

        logger.info("Authenticating with MAM...")

        try:
            from crawl4ai import CrawlerRunConfig, CacheMode
            import random

            login_url = f"{self.mam_base_url}/login.php"

            js_login = f"""
            await new Promise(resolve => setTimeout(resolve, {random.randint(2000, 4000)}));

            const emailInput = document.querySelector('input[name="email"]');
            const passwordInput = document.querySelector('input[name="password"]');

            if (emailInput && passwordInput) {{
                emailInput.focus();
                await new Promise(resolve => setTimeout(resolve, 600));
                emailInput.value = '{self.mam_username}';
                await new Promise(resolve => setTimeout(resolve, 1000));

                passwordInput.focus();
                await new Promise(resolve => setTimeout(resolve, 600));
                passwordInput.value = '{self.mam_password}';
                await new Promise(resolve => setTimeout(resolve, 1200));

                const submitBtn = document.querySelector('input[type="submit"]');
                if (submitBtn) submitBtn.click();

                await new Promise(resolve => setTimeout(resolve, 5000));
            }}
            """

            config = CrawlerRunConfig(
                session_id=self.mam_session_id,
                cache_mode=CacheMode.BYPASS,
                js_code=js_login,
                wait_for="css:body",
                page_timeout=60000
            )

            result = await crawler.arun(url=login_url, config=config)

            if result.success:
                response_text = (result.markdown or "").lower()
                if any(k in response_text for k in ["logout", "my account"]):
                    logger.info("MAM authentication successful")
                    self.mam_authenticated = True
                    return True

            logger.error("MAM authentication failed")
            return False

        except Exception as e:
            logger.error(f"MAM authentication error: {e}")
            return False

    async def _search_mam_for_book(
        self,
        crawler,
        title: str,
        author: str,
        series_name: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Search MAM for a specific book.

        Returns:
            Dict with torrent info or None
        """
        from crawl4ai import CrawlerRunConfig, CacheMode

        logger.info(f"Searching MAM: '{title}' by {author}")

        try:
            # Build search query
            query = f"{title} {author}".replace(' ', '+')
            search_url = f"{self.mam_base_url}/tor/browse.php?tor[text]={query}&tor[srchIn][title]=true&tor[srchIn][author]=true&tor[cat][]=39&tor[cat][]=49&tor[cat][]=50&tor[cat][]=83&tor[cat][]=87&tor[browseFlagsHideVsShow]=0"

            # Stealth JS
            js_code = """
            await new Promise(resolve => setTimeout(resolve, 2000));
            window.scrollTo({ top: 500, behavior: 'smooth' });
            await new Promise(resolve => setTimeout(resolve, 1500));
            """

            config = CrawlerRunConfig(
                session_id=self.mam_session_id,
                cache_mode=CacheMode.BYPASS,
                js_code=js_code,
                wait_for="css:body",
                page_timeout=30000
            )

            result = await crawler.arun(url=search_url, config=config)

            if not result.success or not result.html:
                logger.warning(f"Search failed for: {title}")
                return None

            # Parse results
            soup = BeautifulSoup(result.html, 'lxml')
            torrent_rows = soup.find_all('tr', class_=lambda x: x and 'torrent' in str(x))

            best_match = None
            best_score = 0

            for row in torrent_rows[:10]:  # Check first 10 results
                try:
                    # Extract torrent info
                    title_link = row.find('a', class_='torrentName') or row.find('a', href=lambda h: h and '/t/' in str(h))
                    if not title_link:
                        continue

                    torrent_title = title_link.get_text(strip=True)
                    torrent_url = title_link.get('href', '')

                    if torrent_url.startswith('/'):
                        torrent_url = f"{self.mam_base_url}{torrent_url}"

                    # Calculate match score
                    title_match = SequenceMatcher(None, title.lower(), torrent_title.lower()).ratio()

                    # Check for author in title
                    author_match = 1.0 if author.lower() in torrent_title.lower() else 0.5

                    score = (title_match * 0.7) + (author_match * 0.3)

                    if score > best_score and score >= self.config['title_match_threshold']:
                        # Extract additional info
                        size_td = row.find('td', class_=lambda x: x and 'size' in str(x).lower())
                        size = size_td.get_text(strip=True) if size_td else "Unknown"

                        best_match = {
                            'title': torrent_title,
                            'url': torrent_url,
                            'size': size,
                            'score': score
                        }
                        best_score = score

                except Exception as e:
                    logger.debug(f"Error parsing torrent row: {e}")
                    continue

            if best_match:
                logger.info(f"  Found: {best_match['title']} (score: {best_score:.2f})")
                return best_match
            else:
                logger.info(f"  No matches found for: {title}")
                return None

        except Exception as e:
            logger.error(f"Error searching MAM: {e}")
            return None

    async def _queue_downloads(self):
        """Queue found torrents for download."""
        logger.info("Queuing downloads...")

        queued_count = 0

        for gap in self.gaps:
            if gap.get('download_status') != 'found' or not gap.get('search_result'):
                continue

            torrent = gap['search_result']

            # Check for duplicates in library
            if self._is_duplicate_in_library(gap['title'], gap['author']):
                logger.info(f"Skipping duplicate: {gap['title']}")
                self.stats['duplicates_skipped'] += 1
                gap['download_status'] = 'skipped_duplicate'
                continue

            # Add to qBittorrent
            if self.qb_client:
                try:
                    # Build tags
                    tags = ["gap_filler", "automated"]
                    if gap.get('series_name'):
                        tags.append(gap['series_name'].replace(' ', '_')[:30])

                    # Add torrent
                    self.qb_client.torrents_add(
                        urls=[torrent['url']],
                        category="Audiobooks",
                        tags=tags
                    )

                    logger.info(f"Queued: {gap['title']}")
                    gap['download_status'] = 'queued'
                    queued_count += 1

                    self.downloads_queued.append({
                        'title': gap['title'],
                        'author': gap['author'],
                        'series': gap.get('series_name'),
                        'url': torrent['url'],
                        'queued_at': datetime.now().isoformat()
                    })

                    self.state['queued_downloads'].append(gap['title'])

                except Exception as e:
                    logger.error(f"Failed to queue {gap['title']}: {e}")
                    gap['download_status'] = 'queue_failed'
                    self.stats['errors'].append(f"Queue error: {str(e)}")
            else:
                logger.warning(f"qBittorrent not available - cannot queue: {gap['title']}")
                gap['download_status'] = 'queue_unavailable'

        self.stats['downloads_queued'] = queued_count
        logger.info(f"Queued {queued_count} downloads")

    def _is_duplicate_in_library(self, title: str, author: str) -> bool:
        """Check if a book is already in the library."""
        return self._is_title_owned(title, self.library_books)

    def _generate_report(self, success: bool, error: str = None) -> Dict[str, Any]:
        """Generate final analysis report."""
        self.stats['completed_at'] = datetime.now().isoformat()

        # Calculate duration
        started = datetime.fromisoformat(self.stats['started_at'])
        completed = datetime.fromisoformat(self.stats['completed_at'])
        duration = (completed - started).total_seconds()
        self.stats['duration_seconds'] = duration

        report = {
            'success': success,
            'error': error,
            'stats': self.stats,
            'gaps': [
                {
                    'title': g['title'],
                    'author': g['author'],
                    'series': g.get('series_name'),
                    'type': g['type'],
                    'status': g['download_status']
                }
                for g in self.gaps
            ],
            'downloads_queued': self.downloads_queued
        }

        # Log summary
        logger.info("\n" + "=" * 80)
        logger.info("GAP ANALYSIS COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Duration: {duration:.1f} seconds")
        logger.info(f"Library books: {self.stats['library_books']}")
        logger.info(f"Series analyzed: {self.stats['series_analyzed']}")
        logger.info(f"Authors analyzed: {self.stats['authors_analyzed']}")
        logger.info(f"Gaps identified: {self.stats['gaps_identified']}")
        logger.info(f"  - Series gaps: {self.stats['series_gaps']}")
        logger.info(f"  - Author gaps: {self.stats['author_gaps']}")
        logger.info(f"Torrents found: {self.stats['torrents_found']}")
        logger.info(f"Downloads queued: {self.stats['downloads_queued']}")
        logger.info(f"Duplicates skipped: {self.stats['duplicates_skipped']}")
        logger.info(f"No results: {self.stats['no_results']}")
        logger.info(f"Errors: {len(self.stats['errors'])}")
        logger.info("=" * 80)

        # Save report to file
        report_file = Path("gap_analysis_report.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to {report_file}")

        return report


async def main():
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Audiobook Gap Analyzer')
    parser.add_argument('--analyze-only', action='store_true',
                       help='Only detect gaps, do not download')
    parser.add_argument('--max-downloads', type=int, default=10,
                       help='Maximum downloads to queue per run')
    args = parser.parse_args()

    try:
        analyzer = AudiobookGapAnalyzer()

        if args.max_downloads:
            analyzer.config['max_downloads_per_run'] = args.max_downloads

        result = await analyzer.run_full_analysis(analyze_only=args.analyze_only)

        return 0 if result.get('success') else 1

    except KeyboardInterrupt:
        logger.info("\nAnalysis interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
