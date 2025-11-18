"""
MAM Audiobook Downloader
Downloads top audiobooks from MyAnonamouse by genre using real MAM URLs.
"""

import asyncio
import os
import sys
import json
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
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
        logging.FileHandler('mam_audiobook_download.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class MAMAudiobookDownloader:
    """Download top audiobooks from MAM by genre."""

    # MAM Category codes from MyAnonamouse.md - ALL audiobook genres
    GENRES = {
        'Action/Adventure': 'c39',
        'Art': 'c49',
        'Biographical': 'c50',
        'Business': 'c83',
        'Computer/Internet': 'c51',
        'Crafts': 'c97',
        'Crime/Thriller': 'c40',
        'Fantasy': 'c41',
        'Food': 'c106',
        'General Fiction': 'c42',
        'General Non-Fiction': 'c52',
        'Historical Fiction': 'c98',
        'History': 'c54',
        'Home/Garden': 'c55',
        'Horror': 'c43',
        'Humor': 'c99',
        'Instructional': 'c84',
        'Juvenile': 'c44',
        'Language': 'c56',
        'Literary Classics': 'c45',
        'Math/Science/Tech': 'c57',
        'Medical': 'c85',
        'Mystery': 'c87',
        'Nature': 'c119',
        'Philosophy': 'c88',
        'Politics/Sociology/Religion': 'c58',
        'Recreation': 'c59',
        'Romance': 'c46',
        'Science Fiction': 'c47',
        'Self-Help': 'c53',
        'Travel/Adventure': 'c89',
        'True Crime': 'c100',
        'Urban Fantasy': 'c108',
        'Western': 'c48',
        'Young Adult': 'c111'
    }

    def __init__(self, config_path: str = "audiobook_auto_config.json"):
        self.config = self.load_config(config_path)
        self.username = os.getenv('MAM_USERNAME')
        self.password = os.getenv('MAM_PASSWORD')

        if not self.username or not self.password:
            raise ValueError("MAM_USERNAME and MAM_PASSWORD must be set in .env")

        self.base_url = "https://www.myanonamouse.net"
        self.session_cookies = None

        # qBittorrent setup
        self.qb_client = None
        self.setup_qbittorrent()

        # Stats
        self.stats = {
            'started_at': datetime.now().isoformat(),
            'genres_processed': 0,
            'torrents_found': 0,
            'torrents_added': 0,
            'errors': [],
            'downloads': []
        }

    def load_config(self, path: str) -> Dict:
        """Load configuration."""
        with open(path, 'r') as f:
            return json.load(f)

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
            logger.info(f"✓ Connected to qBittorrent {self.qb_client.app.version}")
        except Exception as e:
            logger.error(f"✗ qBittorrent connection failed: {e}")
            self.qb_client = None

    def build_mam_url(self, genre_code: str, days_back: int = 7) -> str:
        """Build MAM search URL for genre and time range."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        base = "https://www.myanonamouse.net/tor/browse.php"
        params = [
            "tor[srchIn][title]=true",
            "tor[srchIn][author]=true",
            "tor[srchIn][narrator]=true",
            "tor[searchType]=all",
            "tor[searchIn]=torrents",
            f"tor[cat][]={genre_code.replace('c', '')}",  # Remove 'c' prefix
            "tor[browse_lang][]=1",
            "tor[browseFlagsHideVsShow]=0",
            f"tor[startDate]={start_date.strftime('%Y-%m-%d')}",
            f"tor[endDate]={end_date.strftime('%Y-%m-%d')}",
            "tor[sortType]=snatchedDesc",  # Sort by most snatched
            "tor[startNumber]=0",
            "thumbnail=true"
        ]

        return f"{base}?&{'&'.join(params)}"

    async def login(self, crawler: AsyncWebCrawler) -> bool:
        """Login to MAM using aiohttp."""
        logger.info("🔐 Logging into MyAnonamouse...")

        try:
            import aiohttp
            import random

            login_url = f"{self.base_url}/takelogin.php"

            # MAM login requires form submission
            login_data = {
                "username": self.username,
                "password": self.password,
                "login": "Login"
            }

            logger.info(f"Attempting login with username: {self.username[:5]}... (password hidden)")
            logger.info(f"Login data keys: {list(login_data.keys())}")

            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
            ]

            headers = {
                'User-Agent': random.choice(user_agents),
                'Referer': f"{self.base_url}/login.php",
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            async with aiohttp.ClientSession() as session:
                # First visit login page
                async with session.get(f"{self.base_url}/login.php", headers=headers) as resp:
                    await resp.text()

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
                        # Save debug info
                        with open('mam_login_debug.html', 'w', encoding='utf-8') as f:
                            f.write(response_text)
                        logger.info("Debug output saved to mam_login_debug.html")
                        return False

        except Exception as e:
            logger.error(f"✗ Login error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def extract_torrents_from_page(self, html: str, genre_name: str, max_results: int = 10) -> List[Dict]:
        """Extract torrent information from MAM browse page."""
        soup = BeautifulSoup(html, 'lxml')
        torrents = []

        # MAM uses table rows for torrent listings
        # Look for torrent rows (they typically have id="tdr_<torrent_id>")
        torrent_rows = soup.find_all('tr', id=lambda x: x and x.startswith('tdr_'))

        logger.info(f"📊 Found {len(torrent_rows)} torrent rows")

        for row in torrent_rows[:max_results]:
            try:
                # Extract torrent ID from row id (tdr_1234567)
                torrent_id = row.get('id', '').replace('tdr_', '')

                # Find title link
                title_link = row.find('a', href=lambda x: x and '/t/' in x)
                if not title_link:
                    continue

                title = title_link.get_text(strip=True)
                torrent_url = f"{self.base_url}{title_link['href']}"

                # Extract additional info
                author = "Unknown"
                narrator = "Unknown"
                size = "Unknown"
                seeders = 0

                # Try to find author/narrator in the row
                info_cells = row.find_all('td')
                for cell in info_cells:
                    text = cell.get_text(strip=True)
                    if 'by' in text.lower():
                        author = text

                # Find seeders/leechers
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
                logger.info(f"  ✓ [{len(torrents)}] {title}")

            except Exception as e:
                logger.warning(f"  ⚠ Failed to parse torrent row: {e}")
                continue

        return torrents

    async def download_torrent_file(self, crawler: AsyncWebCrawler, torrent_url: str) -> str:
        """Get download URL for torrent."""
        # MAM torrent download URLs are typically /tor/download.php?tid=<id>
        torrent_id = torrent_url.split('/t/')[-1].split('/')[0] if '/t/' in torrent_url else None

        if torrent_id:
            download_url = f"{self.base_url}/tor/download.php?tid={torrent_id}"
            return download_url

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

    async def process_genre(self, crawler: AsyncWebCrawler, genre_name: str, genre_code: str):
        """Process a single genre."""
        logger.info(f"\n{'='*70}")
        logger.info(f"GENRE: {genre_name}")
        logger.info(f"{'='*70}")

        # Build search URL
        days_back = 7  # Last week
        url = self.build_mam_url(genre_code, days_back)

        logger.info(f"🔍 URL: {url}")

        # Crawl the page with authenticated cookies
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            page_timeout=30000,
            wait_for="css:body",
            cookies=list(self.session_cookies.items()) if self.session_cookies else None
        )

        try:
            result = await crawler.arun(url=url, config=config)

            if not result.success:
                logger.error(f"✗ Failed to crawl {genre_name}: {result.error_message}")
                self.stats['errors'].append({
                    'genre': genre_name,
                    'error': result.error_message
                })
                return

            # Extract torrents
            max_results = self.config['query_settings']['top_n_per_genre']
            torrents = await self.extract_torrents_from_page(result.html, genre_name, max_results)

            self.stats['torrents_found'] += len(torrents)
            logger.info(f"✓ Found {len(torrents)} torrents")

            # Add to qBittorrent
            for torrent in torrents:
                download_url = await self.download_torrent_file(crawler, torrent['url'])

                if download_url:
                    if self.add_to_qbittorrent(download_url, torrent['title']):
                        self.stats['torrents_added'] += 1
                        self.stats['downloads'].append({
                            'title': torrent['title'],
                            'genre': genre_name,
                            'url': torrent['url'],
                            'download_url': download_url
                        })

                await asyncio.sleep(1)  # Rate limiting

            self.stats['genres_processed'] += 1

        except Exception as e:
            logger.error(f"✗ Error processing {genre_name}: {e}")
            import traceback
            traceback.print_exc()
            self.stats['errors'].append({
                'genre': genre_name,
                'error': str(e)
            })

    async def run(self):
        """Main execution."""
        logger.info("="*70)
        logger.info("MAM AUDIOBOOK DOWNLOADER")
        logger.info("="*70)

        # Get whitelisted genres from config
        whitelisted = self.config.get('included_genres', ['Science Fiction', 'Fantasy'])
        excluded = self.config.get('excluded_genres', [])

        # Auto-add all non-whitelisted genres to excluded list for visibility
        all_genres = set(self.GENRES.keys())
        whitelisted_set = set(whitelisted)
        auto_excluded = all_genres - whitelisted_set

        logger.info(f"📚 Whitelisted genres ({len(whitelisted)}): {', '.join(sorted(whitelisted))}")
        logger.info(f"🚫 Excluded genres ({len(auto_excluded)}): {', '.join(sorted(auto_excluded))}")

        browser_config = BrowserConfig(
            headless=True,
            viewport_width=1920,
            viewport_height=1080,
            verbose=False
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Login
            if not await self.login(crawler):
                logger.error("✗ Login failed - aborting")
                return

            # Process each whitelisted genre
            for genre_name in whitelisted:
                # Match genre name to code
                genre_code = None
                for key, code in self.GENRES.items():
                    if genre_name.lower() in key.lower() or key.lower() in genre_name.lower():
                        genre_code = code
                        break

                if not genre_code:
                    logger.warning(f"⚠ Unknown genre: {genre_name}")
                    continue

                await self.process_genre(crawler, genre_name, genre_code)
                await asyncio.sleep(5)  # Pause between genres

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print final summary."""
        logger.info("\n" + "="*70)
        logger.info("DOWNLOAD SUMMARY")
        logger.info("="*70)
        logger.info(f"Genres Processed: {self.stats['genres_processed']}")
        logger.info(f"Torrents Found:   {self.stats['torrents_found']}")
        logger.info(f"Torrents Added:   {self.stats['torrents_added']}")
        logger.info(f"Errors:           {len(self.stats['errors'])}")

        if self.stats['downloads']:
            logger.info("\nDOWNLOADS:")
            for dl in self.stats['downloads']:
                logger.info(f"  - [{dl['genre']}] {dl['title']}")

        # Save stats
        stats_file = f"mam_download_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)
        logger.info(f"\n✓ Stats saved to {stats_file}")
        logger.info("="*70)


async def main():
    """Entry point."""
    downloader = MAMAudiobookDownloader()
    await downloader.run()


if __name__ == "__main__":
    asyncio.run(main())
