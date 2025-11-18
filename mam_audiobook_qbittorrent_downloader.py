#!/usr/bin/env python3
"""
MAM Audiobook qBittorrent Downloader - Working Solution
Fetches current top ten audiobook torrents from MAM Fantasy and Science Fiction categories,
removes test/dummy entries, and adds to qBittorrent.
Uses proven authentication and parsing patterns from working script.
"""

import asyncio
import os
import json
import logging
from datetime import datetime
from typing import Dict, List
from dotenv import load_dotenv

import aiohttp
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from bs4 import BeautifulSoup
import qbittorrentapi

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

class WorkingAudiobookDownloader:
    """Working audiobook downloader using proven patterns."""

    # Target genres exactly as requested
    TARGET_GENRES = {
        'Fantasy': '41',
        'Science Fiction': '47'
    }

    def __init__(self):
        self.username = os.getenv('MAM_USERNAME')
        self.password = os.getenv('MAM_PASSWORD')
        
        if not self.username or not self.password:
            raise ValueError("MAM_USERNAME and MAM_PASSWORD must be set in .env")

        self.base_url = "https://www.myanonamouse.net"
        self.session_cookies = None
        
        # qBittorrent setup
        self.qb_client = self.setup_qbittorrent()
        
        # Stats
        self.stats = {
            'started_at': datetime.now().isoformat(),
            'genres_processed': 0,
            'torrents_found': 0,
            'torrents_added': 0,
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
            import random

            login_url = f"{self.base_url}/takelogin.php"

            # MAM login requires form submission - use exact format from working script
            login_data = {
                "username": self.username,
                "password": self.password,
                "login": "Login"
            }

            logger.info(f"Attempting login with username: {self.username[:5]}... (password hidden)")

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
        """Extract torrent information from MAM browse page using PROVEN method."""
        soup = BeautifulSoup(html, 'lxml')
        torrents = []

        # PROVEN method: Look for torrent rows (they typically have id="tdr_<torrent_id>")
        torrent_rows = soup.find_all('tr', id=lambda x: x and x.startswith('tdr_'))

        logger.info(f"📊 Found {len(torrent_rows)} torrent rows for {genre_name}")

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

                # Skip test/dummy entries
                if self.is_test_entry(title):
                    logger.debug(f"Filtered test entry: {title}")
                    self.stats['test_filtered'] += 1
                    continue

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
        url = self.build_mam_search_url(genre_code, days_back)

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

            # Extract torrents using proven method
            max_results = 10  # Top 10 per genre as requested
            torrents = self.extract_torrents_from_page(result.html, genre_name, max_results)

            self.stats['torrents_found'] += len(torrents)
            logger.info(f"✓ Found {len(torrents)} genuine torrents (test entries filtered)")

            # Add to qBittorrent
            for torrent in torrents:
                download_url = await self.download_torrent_file(crawler, torrent['url'])

                if download_url:
                    if self.add_to_qbittorrent(download_url, torrent['title']):
                        self.stats['torrents_added'] += 1

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
        logger.info("MAM AUDIOBOOK qBITTORRENT DOWNLOADER")
        logger.info("Fetching top 10 from Fantasy and Science Fiction")
        logger.info("Removing test/dummy entries")
        logger.info("="*70)

        # Login with proven aiohttp method
        if not await self.login_aiohttp():
            logger.error("✗ Login failed - aborting")
            return False

        browser_config = BrowserConfig(
            headless=True,
            viewport_width=1920,
            viewport_height=1080,
            verbose=False
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Process each target genre
            for genre_name in ['Fantasy', 'Science Fiction']:
                await self.process_genre(crawler, genre_name, self.TARGET_GENRES[genre_name])
                await asyncio.sleep(5)  # Pause between genres

        # Print summary
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
        logger.info(f"Torrents found: {self.stats['torrents_found']}")
        logger.info(f"Test/dummy entries filtered: {self.stats['test_filtered']}")
        logger.info(f"Torrents added to qBittorrent: {self.stats['torrents_added']}")
        logger.info(f"Errors: {len(self.stats['errors'])}")

        if self.stats['errors']:
            logger.info("\nErrors:")
            for error in self.stats['errors']:
                logger.info(f"  - {error['genre']}: {error['error']}")

        # Save stats
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