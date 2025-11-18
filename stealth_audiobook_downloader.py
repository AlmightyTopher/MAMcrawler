"""
Stealth MAM Audiobook Downloader
Enhanced with Audiobookshelf integration, human-like behavior, and production-ready features.
"""

import asyncio
import os
import sys
import json
import logging
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

# Configure logging (no emojis)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stealth_audiobook_download.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class StealthMAMAudiobookDownloader:
    """Enhanced audiobook downloader with stealth capabilities and Audiobookshelf integration."""

    # Strict whitelist - only Science Fiction and Fantasy
    WHITELISTED_GENRES = {
        'Science Fiction': 'c47',
        'Fantasy': 'c41'
    }

    def __init__(self, config_path: str = "audiobook_auto_config.json"):
        self.config = self.load_config(config_path)
        self.username = os.getenv('MAM_USERNAME')
        self.password = os.getenv('MAM_PASSWORD')

        if not self.username or not self.password:
            raise ValueError("MAM_USERNAME and MAM_PASSWORD must be set in .env")

        self.base_url = "https://www.myanonamouse.net"
        self.session_cookies = None
        self.is_authenticated = False

        # Audiobookshelf integration
        self.abs_url = os.getenv('ABS_URL', 'http://localhost:13378')
        self.abs_token = os.getenv('ABS_TOKEN', '')
        self.abs_library = []
        self.abs_available = False

        # qBittorrent setup
        self.qb_client = None
        self.setup_qbittorrent()

        # Stealth parameters
        self.min_delay = 15
        self.max_delay = 45
        self.scroll_delay = 3
        self.read_delay = 8

        # Viewport randomization
        self.viewports = [
            (1920, 1080), (1366, 768), (1536, 864),
            (1440, 900), (1600, 900), (1280, 720)
        ]

        # User agent rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        ]

        # State management
        self.state_file = Path("stealth_audiobook_state.json")
        self.state = self.load_state()

        # Stats
        self.stats = {
            'started_at': datetime.now().isoformat(),
            'genres_processed': 0,
            'torrents_found': 0,
            'torrents_filtered': 0,
            'duplicates_skipped': 0,
            'torrents_added': 0,
            'errors': [],
            'downloads': []
        }

    def load_config(self, path: str) -> Dict:
        """Load configuration."""
        with open(path, 'r') as f:
            return json.load(f)

    def load_state(self) -> Dict:
        """Load crawler state for resume capability."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                logger.info(f"Loaded state: {len(state.get('completed', []))} torrents already processed")
                state.setdefault('completed', [])
                state.setdefault('failed', [])
                state.setdefault('skipped_duplicates', [])
                state.setdefault('last_run', None)
                return state
            except Exception as e:
                logger.error(f"Failed to load state: {e}")

        return {
            'completed': [],
            'failed': [],
            'skipped_duplicates': [],
            'last_run': None
        }

    def save_state(self):
        """Save current state."""
        self.state['last_run'] = datetime.now().isoformat()
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            logger.debug(f"State saved: {len(self.state['completed'])} completed")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def setup_qbittorrent(self):
        """Setup qBittorrent client."""
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
            logger.error(f"qBittorrent connection failed: {e}")
            self.qb_client = None

    def get_audiobookshelf_library(self) -> List[Dict]:
        """Load Audiobookshelf library for duplicate detection."""
        if not self.abs_token or not self.abs_url:
            logger.warning("Audiobookshelf credentials not configured - skipping duplicate detection")
            return []

        try:
            headers = {'Authorization': f'Bearer {self.abs_token}'}
            response = requests.get(f"{self.abs_url}/api/libraries", headers=headers, timeout=10)
            response.raise_for_status()

            libraries = response.json()
            if not libraries:
                logger.warning("No Audiobookshelf libraries found")
                return []

            # Get the first library (assuming audiobook library)
            lib_id = libraries[0]['id']
            lib_response = requests.get(f"{self.abs_url}/api/libraries/{lib_id}/items", headers=headers, timeout=30)
            lib_response.raise_for_status()

            items = lib_response.json().get('results', [])
            logger.info(f"Loaded {len(items)} items from Audiobookshelf library")
            self.abs_available = True
            return items

        except Exception as e:
            logger.error(f"Failed to load Audiobookshelf library: {e}")
            return []

    def is_duplicate(self, title: str, author: str = "") -> bool:
        """Check if audiobook already exists in Audiobookshelf library."""
        if not self.abs_available or not self.abs_library:
            return False

        # Fuzzy title matching
        title_lower = title.lower().strip()
        author_lower = author.lower().strip()

        for item in self.abs_library:
            item_title = item.get('media', {}).get('metadata', {}).get('title', '').lower().strip()
            item_author = item.get('media', {}).get('metadata', {}).get('authorName', '').lower().strip()

            # Title similarity check (simple contains for now)
            if title_lower in item_title or item_title in title_lower:
                if not author or author_lower in item_author or item_author in author_lower:
                    logger.info(f"Duplicate found: '{title}' matches '{item_title}' by {item_author}")
                    return True

        return False

    def build_mam_url(self, genre_code: str, days_back: int = 0) -> str:
        """Build MAM search URL for genre - production mode with current top torrents."""
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
            "tor[sortType]=snatchedDesc",  # Top snatched torrents
            "tor[startNumber]=0",
            "thumbnail=true"
        ]

        return f"{base}?&{'&'.join(params)}"

    async def human_delay(self, min_seconds: Optional[int] = None, max_seconds: Optional[int] = None):
        """Simulate human-like random delay."""
        min_s = min_seconds or self.min_delay
        max_s = max_seconds or self.max_delay
        delay = random.uniform(min_s, max_s)
        logger.info(f"Waiting {delay:.1f} seconds (human-like delay)...")
        await asyncio.sleep(delay)

    def get_random_viewport(self) -> tuple:
        """Get random viewport size."""
        return random.choice(self.viewports)

    def get_random_user_agent(self) -> str:
        """Get random user agent."""
        return random.choice(self.user_agents)

    def create_browser_config(self) -> BrowserConfig:
        """Create browser config with randomized settings."""
        width, height = self.get_random_viewport()

        if sys.platform == 'win32':
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

        return BrowserConfig(
            headless=False,
            viewport_width=width,
            viewport_height=height,
            verbose=False,
            user_agent=self.get_random_user_agent(),
            ignore_https_errors=False,
            java_script_enabled=True,
            light_mode=False
        )

    def create_stealth_js(self) -> str:
        """Create JavaScript for human-like behavior simulation."""
        return """
        async function simulateHumanBehavior() {
            for (let i = 0; i < 4; i++) {
                const x = Math.floor(Math.random() * window.innerWidth);
                const y = Math.floor(Math.random() * window.innerHeight);

                const event = new MouseEvent('mousemove', {
                    clientX: x,
                    clientY: y,
                    bubbles: true
                });
                document.dispatchEvent(event);

                await new Promise(resolve => setTimeout(resolve, 300 + Math.random() * 500));
            }

            const scrollHeight = document.documentElement.scrollHeight;
            const scrollSteps = 4 + Math.floor(Math.random() * 4);

            for (let i = 0; i < scrollSteps; i++) {
                const scrollTo = (scrollHeight / scrollSteps) * (i + 1);
                window.scrollTo({
                    top: scrollTo,
                    behavior: 'smooth'
                });

                await new Promise(resolve => setTimeout(resolve, 1500 + Math.random() * 3000));
            }

            window.scrollTo({ top: 0, behavior: 'smooth' });
            await new Promise(resolve => setTimeout(resolve, 800));
        }

        await simulateHumanBehavior();
        """

    async def authenticate(self, crawler: AsyncWebCrawler) -> bool:
        """Authenticate with human-like behavior."""
        if self.is_authenticated:
            logger.info("Already authenticated")
            return True

        logger.info("Authenticating with MyAnonamouse (stealth mode)")

        await self.human_delay(5, 10)

        try:
            login_url = f"{self.base_url}/login.php"

            js_login = f"""
            await new Promise(resolve => setTimeout(resolve, {random.randint(2000, 4000)}));

            for (let i = 0; i < 3; i++) {{
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
                session_id="mam_stealth_session",
                cache_mode=CacheMode.BYPASS,
                js_code=js_login,
                wait_for="css:body",
                page_timeout=60000,
                screenshot=True
            )

            result = await crawler.arun(url=login_url, config=config)

            if result.success:
                response_text = (result.markdown or "").lower()
                if any(k in response_text for k in ["logout", "my account", "log out"]):
                    logger.info("Authentication successful")
                    self.is_authenticated = True

                    if getattr(result, 'screenshot', None):
                        import base64
                        screenshot_data = base64.b64decode(result.screenshot) if isinstance(result.screenshot, str) else result.screenshot
                        with open('stealth_login_success.png', 'wb') as f:
                            f.write(screenshot_data)

                    return True
                else:
                    logger.error("Authentication failed")
                    if getattr(result, 'screenshot', None):
                        import base64
                        screenshot_data = base64.b64decode(result.screenshot) if isinstance(result.screenshot, str) else result.screenshot
                        with open('stealth_login_failed.png', 'wb') as f:
                            f.write(screenshot_data)
                    return False
            else:
                logger.error(f"Browser automation failed: {result.error_message}")
                return False

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def crawl_genre_page(self, crawler: AsyncWebCrawler, genre_name: str, genre_code: str) -> List[Dict]:
        """Crawl top audiobooks for a specific genre."""
        logger.info(f"Crawling {genre_name} audiobooks (last 7 days)")

        url = self.build_mam_url(genre_code, days_back=7)
        logger.info(f"Genre URL: {url}")

        await self.human_delay()

        config = CrawlerRunConfig(
            session_id="mam_stealth_session",
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

            # Parse torrent table
            torrent_rows = soup.find_all('tr', class_=lambda x: x and 'torrent' in x)

            for row in torrent_rows[:10]:  # Top 10 only
                try:
                    # Extract torrent info
                    title_link = row.find('a', class_='torrentName')
                    if not title_link:
                        continue

                    title = title_link.get_text(strip=True)
                    torrent_url = title_link.get('href', '')

                    if not title or not torrent_url:
                        continue

                    if torrent_url.startswith('/'):
                        torrent_url = f"{self.base_url}{torrent_url}"

                    # Extract size
                    size_td = row.find('td', class_='torrentSize')
                    size_text = size_td.get_text(strip=True) if size_td else "Unknown"

                    # Extract snatched count
                    snatched_td = row.find('td', class_='torrentSnatched')
                    snatched_text = snatched_td.get_text(strip=True) if snatched_td else "0"

                    # Check for VIP/freeleech indicators
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

    def should_download_torrent(self, torrent: Dict) -> tuple[bool, str]:
        """Determine if torrent should be downloaded based on rules."""
        title = torrent.get('title', '').lower()
        author = ""  # Could extract from title if needed

        # Check duplicate against Audiobookshelf
        if self.is_duplicate(title, author):
            self.stats['duplicates_skipped'] += 1
            return False, "Duplicate in Audiobookshelf library"

        # VIP torrents are always freeleech
        if torrent.get('is_vip', False):
            return True, "VIP torrent (freeleech)"

        # Freeleech torrents
        if torrent.get('is_freeleech', False):
            return True, "Freeleech torrent"

        # Check size for FL wedge usage (non-VIP large torrents)
        size_text = torrent.get('size', '')
        if self.should_use_fl_wedge(size_text):
            return True, f"Large torrent ({size_text}) - using FL wedge"

        return False, "Not VIP, freeleech, or large enough for FL wedge"

    def should_use_fl_wedge(self, size_text: str) -> bool:
        """Check if torrent size warrants FL wedge usage."""
        try:
            # Parse size (e.g., "2.5 GB", "500 MB")
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

            # Use FL wedge for torrents > 1GB (adjustable threshold)
            return gb_size > 1.0

        except (ValueError, IndexError):
            return False

    async def download_torrent(self, torrent: Dict) -> bool:
        """Download torrent using qBittorrent."""
        if not self.qb_client:
            logger.error("qBittorrent not available")
            return False

        try:
            torrent_url = torrent['url']
            category = "Audiobooks"
            tags = [torrent['genre'].lower().replace(' ', '_'), "mam_automated"]

            # Add VIP/freeleech tags
            if torrent.get('is_vip'):
                tags.append("vip")
            if torrent.get('is_freeleech'):
                tags.append("freeleech")

            # Add FL wedge tag if applicable
            if self.should_use_fl_wedge(torrent.get('size', '')) and not torrent.get('is_vip'):
                tags.append("fl_wedge")

            logger.info(f"Adding torrent: {torrent['title']}")
            logger.info(f"Tags: {', '.join(tags)}")

            # Add torrent to qBittorrent
            self.qb_client.torrents_add(
                urls=[torrent_url],
                category=category,
                tags=tags,
                save_path=self.config.get('download_path', '')
            )

            logger.info(f"Successfully added: {torrent['title']}")
            return True

        except Exception as e:
            logger.error(f"Failed to add torrent {torrent.get('title', 'Unknown')}: {e}")
            return False

    async def process_genre(self, crawler: AsyncWebCrawler, genre_name: str, genre_code: str):
        """Process a single genre."""
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing {genre_name}")
        logger.info(f"{'='*60}")

        torrents = await self.crawl_genre_page(crawler, genre_name, genre_code)

        if not torrents:
            logger.warning(f"No torrents found for {genre_name}")
            return

        added_count = 0

        for torrent in torrents:
            self.stats['torrents_found'] += 1

            should_download, reason = self.should_download_torrent(torrent)

            if should_download:
                logger.info(f"Downloading: {torrent['title']} - {reason}")

                if await self.download_torrent(torrent):
                    self.state['completed'].append({
                        'title': torrent['title'],
                        'url': torrent['url'],
                        'genre': genre_name,
                        'reason': reason,
                        'added_at': datetime.now().isoformat()
                    })
                    self.stats['torrents_added'] += 1
                    added_count += 1
                else:
                    self.state['failed'].append({
                        'title': torrent['title'],
                        'url': torrent['url'],
                        'error': 'Download failed',
                        'timestamp': datetime.now().isoformat()
                    })
                    self.stats['errors'].append(f"Failed to download: {torrent['title']}")
            else:
                logger.info(f"Skipping: {torrent['title']} - {reason}")
                self.state['skipped_duplicates'].append({
                    'title': torrent['title'],
                    'reason': reason,
                    'timestamp': datetime.now().isoformat()
                })
                self.stats['torrents_filtered'] += 1

            # Human-like delay between torrent processing
            await self.human_delay(5, 15)

        logger.info(f"Genre {genre_name}: {added_count} torrents added, {len(torrents) - added_count} skipped")
        self.stats['genres_processed'] += 1

    async def run(self):
        """Main execution with stealth and state management."""
        logger.info("=" * 80)
        logger.info("Starting STEALTH MAM Audiobook Downloader")
        logger.info("=" * 80)

        # Load Audiobookshelf library
        self.abs_library = self.get_audiobookshelf_library()

        browser_config = self.create_browser_config()
        logger.info(f"Viewport: {browser_config.viewport_width}x{browser_config.viewport_height}")

        async with AsyncWebCrawler(config=browser_config) as crawler:
            if not await self.authenticate(crawler):
                logger.error("Authentication failed. Exiting.")
                return

            # Process only whitelisted genres
            for genre_name, genre_code in self.WHITELISTED_GENRES.items():
                await self.process_genre(crawler, genre_name, genre_code)
                self.save_state()

                # Longer delay between genres
                await self.human_delay(30, 60)

        # Final stats and summary
        self.save_state()

        logger.info("\n" + "=" * 80)
        logger.info("DOWNLOAD COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Genres processed: {self.stats['genres_processed']}")
        logger.info(f"Total torrents found: {self.stats['torrents_found']}")
        logger.info(f"Torrents filtered: {self.stats['torrents_filtered']}")
        logger.info(f"Duplicates skipped: {self.stats['duplicates_skipped']}")
        logger.info(f"Torrents added: {self.stats['torrents_added']}")
        logger.info(f"Errors: {len(self.stats['errors'])}")
        logger.info("=" * 80)

        # Save final stats
        stats_file = Path("stealth_download_stats.json")
        with open(stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
        logger.info(f"Stats saved to {stats_file}")


async def main():
    """Entry point."""
    try:
        downloader = StealthMAMAudiobookDownloader()
        await downloader.run()
    except KeyboardInterrupt:
        logger.info("\nDownload interrupted by user")
        logger.info("Progress has been saved - run again to resume")
    except Exception as e:
        logger.error(f"Download failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())