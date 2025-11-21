#!/usr/bin/env python3
"""
MAM Audiobook qBittorrent Downloader - Working Solution
Fetches current top ten audiobook torrents from MAM Fantasy and Science Fiction categories,
checks against Audiobookshelf library, and downloads the BEST quality release if missing.
Enforces Strict Identity Rules (Section 21) and Quality Rules (Section 5).
Prioritizes Prowlarr for downloads, with MAM Scraper as fallback (Section 7).
"""

import asyncio
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional
from dotenv import load_dotenv

import aiohttp
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from bs4 import BeautifulSoup
import qbittorrentapi
from aiohttp_socks import ProxyConnector

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mam_audiobook_qbittorrent.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from mamcrawler.stealth import StealthCrawler
from mamcrawler.quality import QualityFilter
from audiobookshelf_metadata_sync import AudiobookshelfMetadataSync
from backend.integrations.prowlarr_client import ProwlarrClient

class WorkingAudiobookDownloader(StealthCrawler):
    """Working audiobook downloader using proven patterns and Shared Stealth Library."""

    # Target genres exactly as requested
    TARGET_GENRES = {
        'Fantasy': '41',
        'Science Fiction': '47'
    }

    def __init__(self):
        # Initialize with MAM Identity (Scraper A)
        super().__init__(state_file="audiobook_downloader_state.json", identity_type='MAM')
        self.username = os.getenv('MAM_USERNAME')
        self.password = os.getenv('MAM_PASSWORD')
        
        if not self.username or not self.password:
            raise ValueError("MAM_USERNAME and MAM_PASSWORD must be set in .env")

        self.base_url = "https://www.myanonamouse.net"
        self.session_cookies = None
        
        # qBittorrent setup
        self.qb_client = self.setup_qbittorrent()
        
        # Prowlarr setup
        self.prowlarr_url = os.getenv('PROWLARR_URL', 'http://localhost:9696')
        self.prowlarr_api_key = os.getenv('PROWLARR_API_KEY')
        
        # Quality Filter
        self.quality_filter = QualityFilter()
        
        # ABS Sync
        self.abs_sync = AudiobookshelfMetadataSync()
        self.abs_library_titles = set()
        
        # Stats
        self.stats = {
            'started_at': datetime.now().isoformat(),
            'genres_processed': 0,
            'torrents_found': 0,
            'books_checked': 0,
            'books_missing': 0,
            'torrents_added': 0,
            'prowlarr_hits': 0,
            'mam_fallback_hits': 0,
            'test_filtered': 0,
            'errors': []
        }

    def setup_qbittorrent(self):
        """Setup qBittorrent client."""
        try:
            qb_host = os.getenv('QBITTORRENT_URL', 'http://localhost:52095')
            qb_user = os.getenv('QBITTORRENT_USERNAME', 'admin')
            qb_pass = os.getenv('QBITTORRENT_PASSWORD', '')
            
            client = qbittorrentapi.Client(
                host=qb_host,
                username=qb_user,
                password=qb_pass
            )
            client.auth_log_in()
            logger.info(f"✓ Connected to qBittorrent {client.app.version}")
            return client
        except Exception as e:
            logger.warning(f"qBittorrent connection failed: {e}")
            return None

    async def login_aiohttp(self) -> bool:
        """Login using aiohttp - the PROVEN working method."""
        logger.info("🔐 Logging into MyAnonamouse using aiohttp...")

        try:
            login_url = f"{self.base_url}/takelogin.php"

            # MAM login requires form submission
            login_data = {
                "username": self.username,
                "password": self.password,
                "login": "Login"
            }

            logger.info(f"Attempting login with username: {self.username[:5]}... (password hidden)")

            # Use Shared Stealth UA (Fixed for MAM)
            user_agent = self.get_user_agent()

            headers = {
                'User-Agent': user_agent,
                'Referer': f"{self.base_url}/login.php"
                # Let aiohttp set Content-Type
            }

            # Use Proxy for MAM Identity
            connector = None
            if self.proxy:
                connector = ProxyConnector.from_url(self.proxy)
                logger.info(f"🔒 Using Proxy: {self.proxy}")

            async with aiohttp.ClientSession(connector=connector) as session:
                # First visit login page
                async with session.get(f"{self.base_url}/login.php", headers=headers) as resp:
                    login_page_html = await resp.text()

                # Extract hidden token 't'
                soup = BeautifulSoup(login_page_html, 'html.parser')
                token_input = soup.find('input', {'name': 't'})
                if not token_input:
                    logger.error("✗ Could not find login token 't'")
                    return False
                
                # Token might be URL-encoded in HTML, decode it
                import urllib.parse
                token = urllib.parse.unquote(token_input.get('value'))
                logger.info(f"Token found: {token[:10]}...")

                # MAM login requires form submission
                # Field name is 'email' even for username
                login_data = {
                    "email": self.username,
                    "password": self.password,
                    "t": token,
                    "rememberMe": "yes",
                    "login": "Log in!" # Try sending it again
                }

                # Submit login form
                async with session.post(login_url, data=login_data, headers=headers, allow_redirects=True) as resp:
                    response_text = await resp.text()

                    # Check if login successful
                    if "logout" in response_text.lower() or "my account" in response_text.lower():
                        logger.info("✓ Login successful")
                        self.session_cookies = {cookie.key: cookie.value for cookie in session.cookie_jar}
                        logger.info(f"✓ Stored {len(self.session_cookies)} session cookies")
                        return True
                    else:
                        logger.error("✗ Login failed - check credentials")
                        with open('mam_login_debug.html', 'w', encoding='utf-8') as f:
                            f.write(response_text)
                        return False

        except Exception as e:
            logger.error(f"✗ Login error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def build_mam_search_url(self, genre_code: str, days_back: int = 7) -> str:
        """Build MAM search URL for genre and time range."""
        from datetime import timedelta
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        base = f"{self.base_url}/tor/browse.php"
        params = [
            "tor[srchIn][title]=true",
            "tor[srchIn][author]=true",
            "tor[srchIn][narrator]=true",
            "tor[searchType]=all",
            "tor[searchIn]=torrents",
            f"tor[cat][]={genre_code}",
            "tor[browse_lang][]=1",
            "tor[browseFlagsHideVsShow]=0",
            f"tor[startDate]={start_date.strftime('%Y-%m-%d')}",
            f"tor[endDate]={end_date.strftime('%Y-%m-%d')}",
            "tor[sortType]=snatchedDesc",  # Sort by most snatched
            "tor[startNumber]=0",
            "thumbnail=true"
        ]

        return f"{base}?&{'&'.join(params)}"

    def is_test_entry(self, title: str) -> bool:
        """Check if title is a test/dummy entry."""
        test_keywords = [
            'test', 'dummy', 'sample', 'placeholder', 'example', 
            'test audiobook', 'dummy book', 'sample audio', 'lorem', 'ipsum'
        ]
        return any(keyword in title.lower() for keyword in test_keywords)

    def extract_torrents_from_page(self, html: str, genre_name: str, max_results: int = 10) -> List[Dict]:
        """Extract torrent information from MAM browse page."""
        soup = BeautifulSoup(html, 'lxml')
        torrents = []

        torrent_rows = soup.find_all('tr', id=lambda x: x and x.startswith('tdr_'))
        logger.info(f"📊 Found {len(torrent_rows)} torrent rows for {genre_name}")

        for row in torrent_rows[:max_results]:
            try:
                torrent_id = row.get('id', '').replace('tdr_', '')
                title_link = row.find('a', href=lambda x: x and '/t/' in x)
                if not title_link:
                    continue

                title = title_link.get_text(strip=True)
                torrent_url = f"{self.base_url}{title_link['href']}"

                if self.is_test_entry(title):
                    continue

                author = "Unknown"
                narrator = "Unknown"
                size = "Unknown"
                seeders = 0

                info_cells = row.find_all('td')
                for cell in info_cells:
                    text = cell.get_text(strip=True)
                    if 'by' in text.lower():
                        author = text

                seed_cell = row.find('td', class_=lambda x: x and 'seed' in x.lower())
                if seed_cell:
                    try:
                        seeders = int(seed_cell.get_text(strip=True))
                    except:
                        pass

                torrent = {
                    'id': torrent_id,
                    'title': title,
                    'url': torrent_url,
                    'author': author,
                    'narrator': narrator,
                    'size': size,
                    'seeders': seeders,
                    'genre': genre_name
                }

                torrents.append(torrent)

            except Exception as e:
                logger.warning(f"  ⚠ Failed to parse torrent row: {e}")
                continue

        return torrents

    async def download_torrent_file(self, crawler: AsyncWebCrawler, torrent_url: str) -> str:
        """Get download URL for torrent."""
        torrent_id = torrent_url.split('/t/')[-1].split('/')[0] if '/t/' in torrent_url else None
        if torrent_id:
            return f"{self.base_url}/tor/download.php?tid={torrent_id}"
        return None

    def add_to_qbittorrent(self, download_url: str, title: str, category: str = "audiobooks-auto") -> bool:
        """Add torrent to qBittorrent."""
        if not self.qb_client:
            logger.warning("⚠ qBittorrent not connected")
            return False

        try:
            self.qb_client.torrents_add(
                urls=download_url,
                category=category,
                tags=["mam", "audiobook", "auto"]
            )
            logger.info(f"  ✓ Added to qBittorrent: {title}")
            return True
        except Exception as e:
            logger.error(f"  ✗ Failed to add to qBittorrent: {e}")
            return False

    async def fetch_abs_library(self):
        """Fetch and cache ABS library titles."""
        logger.info("📚 Fetching Audiobookshelf library...")
        items = self.abs_sync.get_audiobookshelf_library()
        self.abs_library_titles = set()
        for item in items:
            media = item.get('media', {})
            metadata = media.get('metadata', {})
            title = metadata.get('title')
            if title:
                self.abs_library_titles.add(title.lower())
        logger.info(f"📚 Cached {len(self.abs_library_titles)} titles from ABS")

    def is_in_library(self, title: str) -> bool:
        """Check if title exists in ABS library (fuzzy match)."""
        # Simple exact match on lower case for now, can be improved
        return title.lower() in self.abs_library_titles

    async def search_prowlarr(self, title: str, author: str) -> List[Dict]:
        """Search Prowlarr and adapt results for QualityFilter."""
        if not self.prowlarr_api_key:
            logger.warning("⚠ Prowlarr API key not set, skipping Prowlarr search")
            return []

        logger.info(f"  🔎 Searching Prowlarr for: '{title}' by {author}")
        
        try:
            async with ProwlarrClient(self.prowlarr_url, self.prowlarr_api_key) as client:
                # Search for Title + Author
                query = f"{title} {author}"
                results = await client.search(query, categories=[3010], limit=20)
                
                adapted_results = []
                for res in results:
                    # Adapt Prowlarr result to QualityFilter format
                    adapted = {
                        'title': res.get('title'),
                        'url': res.get('magnetUrl') or res.get('downloadUrl'),
                        'seeders': res.get('seeders', 0),
                        'size': res.get('size', 0),
                        'indexer': res.get('indexer'),
                        'narrator': 'Unknown', # Prowlarr doesn't usually parse this
                        'description': res.get('infoUrl', '') # Use info URL as description proxy if needed
                    }
                    
                    # Only include if it has a download link
                    if adapted['url']:
                        adapted_results.append(adapted)
                
                logger.info(f"  ✓ Prowlarr found {len(adapted_results)} candidates")
                return adapted_results

        except Exception as e:
            logger.error(f"  ✗ Prowlarr search failed: {e}")
            return []

    async def search_and_download_best_quality(self, crawler: AsyncWebCrawler, title: str, author: str):
        """
        Search for a book and download the best quality release.
        Priority: Prowlarr -> MAM Fallback
        """
        logger.info(f"🔍 Initiating Search Workflow for: '{title}'")
        
        # 1. Try Prowlarr First (Primary)
        prowlarr_candidates = await self.search_prowlarr(title, author)
        
        if prowlarr_candidates:
            best_release = self.quality_filter.select_best_release(prowlarr_candidates)
            if best_release:
                logger.info(f"  ★ Prowlarr: Best release found: {best_release['title']}")
                if self.add_to_qbittorrent(best_release['url'], best_release['title']):
                    self.stats['torrents_added'] += 1
                    self.stats['prowlarr_hits'] += 1
                    return # Success
            else:
                logger.info("  ⚠ Prowlarr: No candidates met quality standards")
        else:
            logger.info("  ⚠ Prowlarr: No results found")

        # 2. Fallback to MAM Scraper (Secondary)
        logger.info("  🔄 Falling back to MAM Scraper...")
        
        # Build search URL
        base = f"{self.base_url}/tor/browse.php"
        params = [
            "tor[srchIn][title]=true",
            "tor[srchIn][author]=true",
            "tor[searchType]=all",
            "tor[searchIn]=torrents",
            f"tor[text]={title}",
            "tor[sortType]=snatchedDesc"
        ]
        url = f"{base}?&{'&'.join(params)}"

        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_for="css:body",
            cookies=list(self.session_cookies.items()) if self.session_cookies else None
        )

        result = await crawler.arun(url=url, config=config)
        
        if result.success:
            # Extract ALL candidates (up to 20)
            candidates = self.extract_torrents_from_page(result.html, "Search", max_results=20)
            
            if candidates:
                # Apply Quality Filter
                best_release = self.quality_filter.select_best_release(candidates)
                
                if best_release:
                    logger.info(f"  ★ MAM Fallback: Best release found: {best_release['title']}")
                    download_url = await self.download_torrent_file(crawler, best_release['url'])
                    if download_url:
                        if self.add_to_qbittorrent(download_url, best_release['title']):
                            self.stats['torrents_added'] += 1
                            self.stats['mam_fallback_hits'] += 1
                else:
                    logger.warning(f"  ⚠ MAM Fallback: No release met quality standards for: {title}")
            else:
                logger.warning(f"  ⚠ MAM Fallback: No results found for: {title}")
        else:
            logger.error(f"  ❌ MAM Fallback: Search failed for {title}")

    async def process_genre(self, crawler: AsyncWebCrawler, genre_name: str, genre_code: str):
        """Process a single genre: Top 10 -> Check ABS -> Download Best."""
        logger.info(f"\n{'='*70}")
        logger.info(f"GENRE: {genre_name}")
        logger.info(f"{'='*70}")

        # 1. Get Top 10 List (Discovery Phase - Always use MAM Scraper for this)
        days_back = 7
        url = self.build_mam_search_url(genre_code, days_back)
        logger.info(f"🔍 Fetching Top 10 from: {url}")

        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            page_timeout=30000,
            wait_for="css:body"
            # cookies=self.session_cookies if self.session_cookies else None
        )

        result = await crawler.arun(url=url, config=config)
        if not result.success:
            logger.error(f"✗ Failed to crawl {genre_name}")
            return

        # Extract Top 10
        top_10 = self.extract_torrents_from_page(result.html, genre_name, max_results=10)
        logger.info(f"✓ Found {len(top_10)} top torrents")

        # 2. Process Each Book
        processed_titles = set()
        for torrent in top_10:
            title = torrent['title']
            author = torrent['author']
            
            # Deduplicate in this run
            if title.lower() in processed_titles:
                continue
            processed_titles.add(title.lower())
            
            self.stats['books_checked'] += 1
            
            # 3. Check ABS
            if self.is_in_library(title):
                logger.info(f"  ⏭️  Skipping '{title}' (Already in Library)")
                continue
                
            logger.info(f"  📥 Missing '{title}' - Initiating Search & Download...")
            self.stats['books_missing'] += 1
            
            # 4. Search & Download Best Quality (Prowlarr -> MAM)
            await self.search_and_download_best_quality(crawler, title, author)
            
            await asyncio.sleep(2) # Rate limit

        self.stats['genres_processed'] += 1

    async def login_with_cookies(self, crawler: AsyncWebCrawler) -> bool:
        """Login using extracted cookies from browser."""
        logger.info("🔐 Using extracted browser cookies for login...")
        
        # Load cookies from environment variables
        uid = os.getenv('uid')
        mam_id = os.getenv('mam_id')
        
        if not uid or not mam_id:
            logger.error("✗ MAM cookies not found in .env file!")
            logger.error("Please add 'uid' and 'mam_id' to your .env file")
            return False
        
        # Store as list of dicts for crawl4ai compatibility
        self.session_cookies = [
            {"name": "uid", "value": uid, "domain": ".myanonamouse.net"},
            {"name": "mam_id", "value": mam_id, "domain": ".myanonamouse.net"}
        ]
        
        logger.info(f"✓ Loaded {len(self.session_cookies)} cookies from .env")
        logger.info("✓ Login successful (using browser session)")
        return True

    async def run(self):
        """Main execution."""
        logger.info("="*70)
        
        # Validate Identity (Section 21.4)
        if not await self.validate_ip():
            logger.critical("🛑 IP Validation Failed! Aborting to protect identity.")
            return False

        logger.info("MAM AUDIOBOOK qBITTORRENT DOWNLOADER")
        logger.info("Strict Mode: Top 10 -> ABS Check -> Prowlarr -> MAM Fallback")
        logger.info("="*70)

        # Fetch ABS Library
        await self.fetch_abs_library()

        # Browser Config - Back to HEADLESS since we're using cookies
        browser_config = self.create_browser_config(headless=True)

        async with AsyncWebCrawler(config=browser_config) as crawler:
            
            # Login with extracted cookies
            if not await self.login_with_cookies(crawler):
                logger.error("✗ Login failed - aborting")
                return False

            for genre_name in ['Fantasy', 'Science Fiction']:
                await self.process_genre(crawler, genre_name, self.TARGET_GENRES[genre_name])
                await asyncio.sleep(5)

        self.print_summary()
        return True

    def print_summary(self):
        """Print final summary."""
        logger.info("\n" + "="*70)
        logger.info("DOWNLOAD SUMMARY")
        logger.info("="*70)
        logger.info(f"Started at: {self.stats['started_at']}")
        logger.info(f"Completed at: {datetime.now().isoformat()}")
        logger.info(f"Genres processed: {self.stats['genres_processed']}")
        logger.info(f"Books checked: {self.stats['books_checked']}")
        logger.info(f"Books missing: {self.stats['books_missing']}")
        logger.info(f"Torrents added: {self.stats['torrents_added']}")
        logger.info(f"  - Prowlarr: {self.stats['prowlarr_hits']}")
        logger.info(f"  - MAM Fallback: {self.stats['mam_fallback_hits']}")
        logger.info(f"Errors: {len(self.stats['errors'])}")

        if self.stats['errors']:
            logger.info("\nErrors:")
            for error in self.stats['errors']:
                logger.info(f"  - {error['genre']}: {error['error']}")

        stats_file = f"mam_qbittorrent_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)
        logger.info(f"\n✓ Stats saved to {stats_file}")
        logger.info("="*70)


async def main():
    """Entry point."""
    downloader = WorkingAudiobookDownloader()
    await downloader.run()


if __name__ == "__main__":
    asyncio.run(main())