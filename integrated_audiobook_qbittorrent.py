#!/usr/bin/env python3
"""
Integrated Stealth Audiobook qBittorrent Downloader
Fetches top 10 audiobook torrents from MAM Fantasy and Science Fiction categories,
filters out test/dummy entries, and adds them to qBittorrent immediately.
"""

import asyncio
import os
import sys
import json
import logging
import re
import random
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

import aiohttp
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from bs4 import BeautifulSoup
import qbittorrentapi

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('integrated_audiobook_qbittorrent.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class TestEntryFilter:
    """Filters out test, dummy, and spam entries from torrent results."""
    
    # Patterns that indicate test/dummy/spam entries
    TEST_PATTERNS = [
        r'\b(test|demo|sample|dummy|test[_\s-]?file|example|sample[_\s-]?file)\b',
        r'\b(test[_\s-]?(audiobook|book|torrent|download)|demo[_\s-]?(audiobook|book|torrent))\b',
        r'\b(lorem|ipsum|placeholder|fake|fake[_\s-]?book|test[_\s-]?content)\b',
        r'\b(test[_\s-]?(series|collection|volume|part)|sample[_\s-]?(collection|series))\b',
        r'\b(automated[_\s-]?test|bot[_\s-]?test|spider[_\s-]?test|crawler[_\s-]?test)\b',
        r'\b(debug[_\s-]?(test|file)|debug[_\s-]?(content|torrent)|dev[_\s-]?test)\b',
        r'\b(check[_\s-]?this|test[_\s-]?upload|upload[_\s-]?test|test[_\s-]?upload)\b',
        r'\b(noise|garbage|spam[_\s-]?(file|content)|random[_\s-]?data)\b',
        r'\b(qa[_\s-]?test|quality[_\s-]?assurance|test[_\s-]?qa|qa[_\s-]?(file|test))\b',
        r'\b(site[_\s-]?test|site[_\s-]?check|test[_\s-]?site|check[_\s-]?site)\b'
    ]
    
    # Suspicious title patterns
    SUSPICIOUS_PATTERNS = [
        r'^[0-9a-f]{32,}$',  # Pure hex hashes
        r'^[0-9]+$',  # Pure numbers
        r'^[^a-zA-Z0-9\s]*$',  # Only special characters
        r'\b\d{8,}\b',  # Very long numbers
        r'\b(test|demo)\s*[0-9]+\b',  # Test + numbers
    ]
    
    # Minimum quality thresholds
    MIN_TITLE_LENGTH = 10
    MAX_TITLE_LENGTH = 200
    MIN_SNATCHED_COUNT = 0  # Allow new torrents
    MIN_FILE_SIZE_MB = 50   # At least 50MB for a meaningful audiobook
    
    def __init__(self):
        self.test_regex = re.compile('|'.join(self.TEST_PATTERNS), re.IGNORECASE)
        self.suspicious_regex = re.compile('|'.join(self.SUSPICIOUS_PATTERNS), re.IGNORECASE)
    
    def is_test_entry(self, title: str, size_text: str = "", snatched_text: str = "") -> tuple[bool, str]:
        """
        Check if a torrent entry is a test/dummy entry.
        
        Returns:
            tuple: (is_test, reason)
        """
        title_lower = title.lower().strip()
        
        # Check against test patterns
        if self.test_regex.search(title_lower):
            return True, "Contains test/demo/dummy patterns"
        
        # Check suspicious patterns
        if self.suspicious_regex.search(title):
            return True, "Suspicious title pattern"
        
        # Title length checks
        if len(title.strip()) < self.MIN_TITLE_LENGTH:
            return True, f"Title too short (min {self.MIN_TITLE_LENGTH} chars)"
        
        if len(title.strip()) > self.MAX_TITLE_LENGTH:
            return True, f"Title too long (max {self.MAX_TITLE_LENGTH} chars)"
        
        # Check for excessive special characters or repeated patterns
        if title.count('!') > 3 or title.count('?') > 3:
            return True, "Excessive punctuation marks"
        
        # Check for excessive whitespace or unusual characters
        if title.count('  ') > 0 or any(ord(c) > 127 for c in title):
            return True, "Unusual whitespace or characters"
        
        # Parse and validate size
        if not self._is_valid_size(size_text):
            return True, "Invalid or suspicious file size"
        
        # Parse and validate snatched count
        if not self._is_valid_snatched_count(snatched_text):
            return True, "Invalid snatched count"
        
        return False, "Genuine entry"
    
    def _is_valid_size(self, size_text: str) -> bool:
        """Validate file size is reasonable for an audiobook."""
        if not size_text or size_text.strip() == "":
            return False
        
        try:
            # Parse size (e.g., "2.5 GB", "500 MB", "1.2 TB")
            size_parts = size_text.strip().split()
            if len(size_parts) != 2:
                return False
            
            value = float(size_parts[0])
            unit = size_parts[1].upper()
            
            # Convert to MB for comparison
            if unit == 'GB':
                mb_size = value * 1024
            elif unit == 'MB':
                mb_size = value
            elif unit == 'TB':
                mb_size = value * 1024 * 1024
            else:
                return False
            
            # Check if size is within reasonable bounds
            if mb_size < self.MIN_FILE_SIZE_MB:
                return False
            
            if mb_size > 50000:  # 50GB seems excessive for audiobooks
                return False
            
            return True
            
        except (ValueError, IndexError):
            return False
    
    def _is_valid_snatched_count(self, snatched_text: str) -> bool:
        """Validate snatched count is reasonable."""
        if not snatched_text or snatched_text.strip() == "":
            return True  # Allow empty snatched counts (new torrents)
        
        try:
            # Remove commas and extract number
            snatched_clean = snatched_text.strip().replace(',', '')
            
            # Handle various formats
            if snatched_clean.lower() == 'n/a' or snatched_clean == '-':
                return True
            
            snatched_count = int(snatched_clean)
            
            # Allow reasonable range (0 to 50000)
            return 0 <= snatched_count <= 50000
            
        except (ValueError, AttributeError):
            return False


class IntegratedAudiobookDownloader:
    """Integrated audiobook downloader with test filtering and qBittorrent integration."""
    
    # Target genres - exactly Fantasy and Science Fiction as requested
    TARGET_GENRES = {
        'Fantasy': 'c41',
        'Science Fiction': 'c47'
    }
    
    def __init__(self, config_path: str = "audiobook_auto_config.json"):
        self.config = self._load_config(config_path)
        self.username = os.getenv('MAM_USERNAME')
        self.password = os.getenv('MAM_PASSWORD')
        self.qb_url = os.getenv('QBITTORRENT_URL', 'http://localhost:52095')
        self.qb_user = os.getenv('QBITTORRENT_USERNAME', 'admin')
        self.qb_pass = os.getenv('QBITTORRENT_PASSWORD', '')

        # Validate required credentials
        if not self.username or not self.password:
            raise ValueError("MAM_USERNAME and MAM_PASSWORD must be set in .env")

        self.base_url = "https://www.myanonamouse.net"
        self.session_cookies = None
        self.is_authenticated = False

        # qBittorrent setup
        self.qb_client = None
        self._setup_qbittorrent()

        # Test entry filter
        self.test_filter = TestEntryFilter()

        # Download statistics
        self.stats = {
            'started_at': datetime.now().isoformat(),
            'genres_processed': 0,
            'total_torrents_found': 0,
            'test_entries_filtered': 0,
            'genuine_torrents': 0,
            'torrents_added_to_qb': 0,
            'errors': []
        }

        # Stealth parameters for human-like behavior
        self.min_delay = 15
        self.max_delay = 45
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        ]

    def _load_config(self, path: str) -> Dict:
        """Load configuration from JSON file."""
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {path} not found, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Get default configuration."""
        return {
            "download_settings": {
                "auto_add_to_qbittorrent": True,
                "category": "Audiobooks",
                "save_path": ""
            },
            "query_settings": {
                "top_n_per_genre": 10
            }
        }

    def _setup_qbittorrent(self):
        """Setup qBittorrent client connection."""
        try:
            # Parse URL if needed
            if not self.qb_url.startswith('http'):
                self.qb_url = f"http://{self.qb_url}"

            self.qb_client = qbittorrentapi.Client(
                host=self.qb_url,
                username=self.qb_user,
                password=self.qb_pass
            )
            self.qb_client.auth_log_in()
            logger.info(f"Connected to qBittorrent {self.qb_client.app.version}")
            
        except Exception as e:
            logger.error(f"qBittorrent connection failed: {e}")
            logger.error("Make sure qBittorrent is running with Web UI enabled")
            self.qb_client = None

    def build_mam_search_url(self, genre_code: str) -> str:
        """Build MAM search URL for current top torrents in a genre."""
        base = "https://www.myanonamouse.net/tor/browse.php"
        params = [
            "tor[srchIn][title]=true",
            "tor[srchIn][author]=true",
            "tor[srchIn][narrator]=true",
            "tor[searchType]=all",
            "tor[searchIn]=torrents",
            f"tor[cat][]={genre_code.replace('c', '')}",
            "tor[browse_lang][]=1",
            "tor[browseFlagsHideVsShow]=0",
            "tor[sortType]=snatchedDesc",  # Top snatched = most popular
            "tor[startNumber]=0",
            "thumbnail=true"
        ]
        return f"{base}?&{'&'.join(params)}"

    async def human_delay(self, min_seconds: Optional[int] = None, max_seconds: Optional[int] = None):
        """Simulate human-like delay between actions."""
        min_s = min_seconds or self.min_delay
        max_s = max_seconds or self.max_delay
        delay = random.uniform(min_s, max_s)
        logger.debug(f"Human-like delay: {delay:.1f} seconds")
        await asyncio.sleep(delay)

    def create_browser_config(self) -> BrowserConfig:
        """Create browser configuration with randomized settings."""
        width, height = random.choice([
            (1920, 1080), (1366, 768), (1536, 864),
            (1440, 900), (1600, 900), (1280, 720)
        ])
        
        if sys.platform == 'win32':
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

        return BrowserConfig(
            headless=True,  # Run headless for automation
            viewport_width=width,
            viewport_height=height,
            verbose=False,
            user_agent=random.choice(self.user_agents),
            ignore_https_errors=False,
            java_script_enabled=True,
            light_mode=False
        )

    def create_stealth_js(self) -> str:
        """Create JavaScript for human-like behavior."""
        return """
        async function simulateHumanBehavior() {
            // Random mouse movements
            for (let i = 0; i < 3; i++) {
                const x = Math.floor(Math.random() * window.innerWidth);
                const y = Math.floor(Math.random() * window.innerHeight);
                const event = new MouseEvent('mousemove', {
                    clientX: x, clientY: y, bubbles: true
                });
                document.dispatchEvent(event);
                await new Promise(resolve => setTimeout(resolve, 200 + Math.random() * 400));
            }
            
            // Gradual scrolling
            const scrollHeight = document.documentElement.scrollHeight;
            const scrollSteps = 3;
            for (let i = 0; i < scrollSteps; i++) {
                const scrollTo = (scrollHeight / scrollSteps) * (i + 1);
                window.scrollTo({ top: scrollTo, behavior: 'smooth' });
                await new Promise(resolve => setTimeout(resolve, 1500 + Math.random() * 2000));
            }
            
            window.scrollTo({ top: 0, behavior: 'smooth' });
            await new Promise(resolve => setTimeout(resolve, 500));
        }
        
        await simulateHumanBehavior();
        """

    async def authenticate(self, crawler: AsyncWebCrawler) -> bool:
        """Authenticate with MAM using stealth behavior."""
        if self.is_authenticated:
            logger.info("Already authenticated with MAM")
            return True

        logger.info("Authenticating with MyAnonamouse (stealth mode)")

        await self.human_delay(5, 10)

        try:
            login_url = f"{self.base_url}/login.php"

            js_login = f"""
            await new Promise(resolve => setTimeout(resolve, {random.randint(2000, 4000)}));

            for (let i = 0; i < 2; i++) {{
                const event = new MouseEvent('mousemove', {{
                    clientX: 300 + Math.random() * 300,
                    clientY: 200 + Math.random() * 150,
                    bubbles: true
                }});
                document.dispatchEvent(event);
                await new Promise(resolve => setTimeout(resolve, {random.randint(400, 800)}));
            }}

            const emailInput = document.querySelector('input[name="email"]');
            const passwordInput = document.querySelector('input[name="password"]');

            if (emailInput && passwordInput) {{
                emailInput.focus();
                await new Promise(resolve => setTimeout(resolve, {random.randint(600, 1200)}));
                emailInput.value = '{self.username}';
                await new Promise(resolve => setTimeout(resolve, {random.randint(1000, 2000)}));

                passwordInput.focus();
                await new Promise(resolve => setTimeout(resolve, {random.randint(600, 1200)}));
                passwordInput.value = '{self.password}';
                await new Promise(resolve => setTimeout(resolve, {random.randint(1200, 2500)}));

                const submitBtn = document.querySelector('input[type="submit"]');
                if (submitBtn) {{
                    submitBtn.click();
                }} else {{
                    const form = document.querySelector('form');
                    if (form) form.submit();
                }}

                await new Promise(resolve => setTimeout(resolve, 5000));
            }}
            """

            config = CrawlerRunConfig(
                session_id="integrated_audiobook_session",
                cache_mode=CacheMode.BYPASS,
                js_code=js_login,
                wait_for="css:body",
                page_timeout=60000
            )

            result = await crawler.arun(url=login_url, config=config)

            if result.success:
                response_text = (result.markdown or "").lower()
                if any(k in response_text for k in ["logout", "my account", "log out"]):
                    logger.info("Authentication successful")
                    self.is_authenticated = True
                    return True
                else:
                    logger.error("Authentication failed")
                    return False
            else:
                logger.error(f"Browser automation failed: {result.error_message}")
                return False

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False

    async def crawl_genre_top_torrents(self, crawler: AsyncWebCrawler, genre_name: str, genre_code: str) -> List[Dict]:
        """Crawl top torrents for a specific genre."""
        logger.info(f"Fetching top 10 {genre_name} audiobooks...")

        url = self.build_mam_search_url(genre_code)
        logger.info(f"Search URL: {url}")

        await self.human_delay()

        config = CrawlerRunConfig(
            session_id="integrated_audiobook_session",
            cache_mode=CacheMode.BYPASS,
            js_code=self.create_stealth_js(),
            wait_for="css:body",
            page_timeout=45000
        )

        try:
            result = await crawler.arun(url=url, config=config)

            if not result.success:
                logger.error(f"Failed to crawl {genre_name}: {result.error_message}")
                return []

            soup = BeautifulSoup(result.html, 'lxml')
            torrents = []

            # Find torrent rows - using WORKING pattern from mam_audiobook_downloader
            torrent_rows = soup.find_all('tr', id=lambda x: x and x.startswith('tdr_'))

            for row in torrent_rows[:10]:  # Top 10 only
                try:
                    # Extract torrent information
                    title_link = row.find('a', class_='torrentName')
                    if not title_link:
                        continue

                    title = title_link.get_text(strip=True)
                    torrent_url = title_link.get('href', '')

                    if not title or not torrent_url:
                        continue

                    # Make URL absolute
                    if torrent_url.startswith('/'):
                        torrent_url = f"{self.base_url}{torrent_url}"

                    # Extract additional info
                    size_td = row.find('td', class_='torrentSize')
                    size_text = size_td.get_text(strip=True) if size_td else ""

                    snatched_td = row.find('td', class_='torrentSnatched')
                    snatched_text = snatched_td.get_text(strip=True) if snatched_td else ""

                    # Check VIP/freeleech status
                    is_vip = 'vip' in row.get('class', []) or row.find('img', alt='VIP') is not None
                    is_freeleech = 'freeleech' in row.get('class', []) or row.find('img', alt='Freeleech') is not None

                    torrent_info = {
                        'title': title,
                        'url': torrent_url,
                        'size': size_text,
                        'snatched': snatched_text,
                        'is_vip': is_vip,
                        'is_freeleech': is_freeleech,
                        'genre': genre_name,
                        'crawled_at': datetime.now().isoformat()
                    }

                    torrents.append(torrent_info)

                except Exception as e:
                    logger.error(f"Error parsing torrent row: {e}")
                    continue

            logger.info(f"Found {len(torrents)} torrents in {genre_name}")
            return torrents

        except Exception as e:
            logger.error(f"Error crawling {genre_name}: {e}")
            return []

    def should_add_torrent(self, torrent: Dict) -> tuple[bool, str]:
        """Determine if torrent should be added to qBittorrent."""
        title = torrent.get('title', '')
        size_text = torrent.get('size', '')
        snatched_text = torrent.get('snatched', '')

        # Test/dummy entry filtering
        is_test, test_reason = self.test_filter.is_test_entry(title, size_text, snatched_text)
        if is_test:
            return False, f"Test/dummy entry: {test_reason}"

        # Check for minimum quality
        if len(title.strip()) < 15:
            return False, "Title too short to be a legitimate audiobook"

        # VIP torrents are always good
        if torrent.get('is_vip', False):
            return True, "VIP torrent"

        # Freeleech torrents
        if torrent.get('is_freeleech', False):
            return True, "Freeleech torrent"

        # Large torrents are generally good content
        if self._is_large_torrent(size_text):
            return True, "Large torrent (likely complete audiobook)"

        return False, "Does not meet minimum criteria"

    def _is_large_torrent(self, size_text: str) -> bool:
        """Check if torrent size indicates a complete audiobook."""
        if not size_text:
            return False
        
        try:
            size_parts = size_text.split()
            if len(size_parts) != 2:
                return False
            
            value = float(size_parts[0])
            unit = size_parts[1].upper()
            
            # Convert to GB
            if unit == 'GB':
                gb_size = value
            elif unit == 'MB':
                gb_size = value / 1024
            elif unit == 'TB':
                gb_size = value * 1024
            else:
                return False
            
            # Audiobooks are typically 200MB to 2GB+ depending on length
            return gb_size >= 0.2  # At least 200MB
            
        except (ValueError, IndexError):
            return False

    async def add_torrent_to_qbittorrent(self, torrent: Dict) -> bool:
        """Add torrent to qBittorrent."""
        if not self.qb_client:
            logger.error("qBittorrent not available")
            return False

        try:
            torrent_url = torrent['url']
            category = self.config['download_settings']['category']
            tags = [torrent['genre'].lower().replace(' ', '_'), "auto_downloaded"]
            
            # Add special tags
            if torrent.get('is_vip'):
                tags.append("vip")
            if torrent.get('is_freeleech'):
                tags.append("freeleech")

            logger.info(f"Adding: {torrent['title']}")
            logger.info(f"Category: {category}, Tags: {', '.join(tags)}")

            # Add to qBittorrent
            self.qb_client.torrents_add(
                urls=[torrent_url],
                category=category,
                tags=tags,
                save_path=self.config['download_settings'].get('save_path', '')
            )

            logger.info(f"Successfully added: {torrent['title']}")
            return True

        except Exception as e:
            logger.error(f"Failed to add torrent {torrent.get('title', 'Unknown')}: {e}")
            return False

    async def process_genre(self, crawler: AsyncWebCrawler, genre_name: str, genre_code: str):
        """Process a single genre: crawl, filter, and add to qBittorrent."""
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing {genre_name}")
        logger.info(f"{'='*60}")

        # Crawl top torrents
        torrents = await self.crawl_genre_top_torrents(crawler, genre_name, genre_code)

        if not torrents:
            logger.warning(f"No torrents found for {genre_name}")
            return

        added_count = 0
        genre_stats = {'total': len(torrents), 'test_filtered': 0, 'added': 0}

        for torrent in torrents:
            self.stats['total_torrents_found'] += 1

            should_add, reason = self.should_add_torrent(torrent)

            if should_add:
                logger.info(f"Adding: {torrent['title']} - {reason}")

                if await self.add_torrent_to_qbittorrent(torrent):
                    added_count += 1
                    genre_stats['added'] += 1
                    self.stats['torrents_added_to_qb'] += 1
                    self.stats['genuine_torrents'] += 1
                else:
                    self.stats['errors'].append(f"Failed to add: {torrent['title']}")
            else:
                logger.info(f"Skipping: {torrent['title']} - {reason}")
                if "test/dummy" in reason.lower():
                    genre_stats['test_filtered'] += 1
                    self.stats['test_entries_filtered'] += 1
                self.stats['errors'].append(f"Skipped: {torrent['title']} - {reason}")

            # Human-like delay between torrents
            await self.human_delay(5, 15)

        logger.info(f"Genre {genre_name}: {genre_stats}")
        logger.info(f"Added {added_count} torrents from {genre_name}")
        self.stats['genres_processed'] += 1

    async def run(self):
        """Main execution function."""
        logger.info("="*80)
        logger.info("INTEGRATED AUDIOBOOK qBITTORRENT DOWNLOADER")
        logger.info("Fetching top 10 from Fantasy and Science Fiction categories")
        logger.info("="*80)

        # Validate qBittorrent connection
        if not self.qb_client:
            logger.error("qBittorrent connection required but not available")
            return False

        try:
            browser_config = self.create_browser_config()

            async with AsyncWebCrawler(config=browser_config) as crawler:
                # Authenticate
                if not await self.authenticate(crawler):
                    logger.error("Authentication failed. Exiting.")
                    return False

                # Process each target genre
                for genre_name, genre_code in self.TARGET_GENRES.items():
                    await self.process_genre(crawler, genre_name, genre_code)
                    
                    # Delay between genres
                    await self.human_delay(30, 60)

            # Print final statistics
            self._print_final_stats()
            return True

        except Exception as e:
            logger.error(f"Download failed: {e}")
            self.stats['errors'].append(f"System error: {e}")
            return False

    def _print_final_stats(self):
        """Print execution statistics."""
        logger.info("\n" + "="*80)
        logger.info("EXECUTION COMPLETE")
        logger.info("="*80)
        logger.info(f"Started at: {self.stats['started_at']}")
        logger.info(f"Completed at: {datetime.now().isoformat()}")
        logger.info(f"Genres processed: {self.stats['genres_processed']}")
        logger.info(f"Total torrents found: {self.stats['total_torrents_found']}")
        logger.info(f"Test/dummy entries filtered: {self.stats['test_entries_filtered']}")
        logger.info(f"Genuine torrents identified: {self.stats['genuine_torrents']}")
        logger.info(f"Torrents added to qBittorrent: {self.stats['torrents_added_to_qb']}")
        logger.info(f"Errors encountered: {len(self.stats['errors'])}")
        
        if self.stats['errors']:
            logger.info("\nError details:")
            for error in self.stats['errors']:
                logger.info(f"  - {error}")
        
        logger.info("="*80)

        # Save statistics
        stats_file = Path("integrated_qbittorrent_stats.json")
        with open(stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
        logger.info(f"Statistics saved to {stats_file}")


async def main():
    """Main entry point."""
    try:
        logger.info("Starting integrated audiobook qBittorrent downloader...")
        downloader = IntegratedAudiobookDownloader()
        
        success = await downloader.run()
        
        if success:
            logger.info("✅ Successfully completed audiobook download and qBittorrent integration")
        else:
            logger.error("❌ Downloader encountered errors")
            
        return 0 if success else 1

    except KeyboardInterrupt:
        logger.info("\nDownload interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)