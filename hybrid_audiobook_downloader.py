"""
Hybrid Audiobook Downloader - Multiple Parsing Strategies
This script combines the best authentication methods with robust parsing strategies
"""
import asyncio
import os
import json
import random
import logging
from datetime import datetime
from typing import Dict, List, Any
from dotenv import load_dotenv

import aiohttp
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from bs4 import BeautifulSoup
import qbittorrentapi

load_dotenv()

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class HybridAudiobookDownloader:
    """Downloader with multiple parsing strategies for robustness."""

    # MAM Category codes
    GENRES = {
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
            'auth_method_used': None,
            'parsing_strategies_tested': {},
            'torrents_found': 0,
            'torrents_added': 0,
            'genres_processed': []
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
            logger.info(f"Connected to qBittorrent {client.app.version}")
            return client
        except Exception as e:
            logger.warning(f"qBittorrent connection failed: {e}")
            return None

    async def browser_auth_login(self, crawler: AsyncWebCrawler) -> bool:
        """Login using browser automation."""
        logger.info("Using browser authentication...")
        
        js_login = """
        // Wait for page load
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Fill form
        const emailInput = document.querySelector('input[name="email"]');
        const passwordInput = document.querySelector('input[name="password"]');
        
        if (emailInput && passwordInput) {
            emailInput.value = '""" + self.username + """';
            passwordInput.value = '""" + self.password + """';
            
            // Click submit
            const submitBtn = document.querySelector('input[type="submit"]');
            if (submitBtn) submitBtn.click();
            
            // Wait for redirect
            await new Promise(resolve => setTimeout(resolve, 5000));
            return {success: true};
        }
        return {success: false, error: "Form elements not found"};
        """
        
        try:
            result = await crawler.arun(
                url=f"{self.base_url}/login.php",
                config=CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS,
                    js_code=js_login,
                    wait_for="css:body",
                    page_timeout=60000
                )
            )
            
            if result.success:
                logger.info("Browser auth successful")
                self.stats['auth_method_used'] = 'browser'
                return True
            else:
                logger.error(f"Browser auth failed: {result.error_message}")
                return False
                
        except Exception as e:
            logger.error(f"Browser auth error: {e}")
            return False

    async def aiohttp_auth_login(self) -> bool:
        """Login using aiohttp (like working script)."""
        logger.info("Using aiohttp authentication...")
        
        try:
            login_url = f"{self.base_url}/takelogin.php"
            
            login_data = {
                "username": self.username,
                "password": self.password,
                "login": "Login"
            }
            
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
                        logger.info("aiohttp auth successful")
                        self.session_cookies = {cookie.key: cookie.value for cookie in session.cookie_jar}
                        self.stats['auth_method_used'] = 'aiohttp'
                        return True
                    else:
                        logger.error("aiohttp auth failed - check credentials")
                        return False
                        
        except Exception as e:
            logger.error(f"aiohttp auth error: {e}")
            return False

    async def extract_torrents_multiple_strategies(self, html: str, genre_name: str, max_results: int = 10) -> List[Dict]:
        """Extract torrents using multiple parsing strategies."""
        soup = BeautifulSoup(html, 'lxml')
        torrents = []
        
        logger.info(f"Extracting torrents using multiple strategies for {genre_name}...")
        
        # Strategy 1: Original tdr_ pattern (from working script)
        logger.info("Strategy 1: Testing tdr_ pattern...")
        tdr_rows = soup.find_all('tr', id=lambda x: x and x.startswith('tdr_'))
        
        if tdr_rows:
            logger.info(f"Strategy 1 success: Found {len(tdr_rows)} tdr_ rows")
            for row in tdr_rows[:max_results]:
                torrent = self.parse_torrent_row(row, genre_name)
                if torrent:
                    torrents.append(torrent)
            self.stats['parsing_strategies_tested']['tdr_pattern'] = len(tdr_rows)
        
        # Strategy 2: Table rows with torrent links
        if not torrents:
            logger.info("Strategy 2: Testing torrent link pattern...")
            torrent_links = soup.find_all('a', href=lambda x: x and '/t/' in x)
            found_torrents = set()
            
            for link in torrent_links:
                # Get parent row
                parent_row = link.find_parent('tr')
                if parent_row and parent_row not in [t['element'] for t in found_torrents]:
                    torrent = self.parse_torrent_row(parent_row, genre_name, link)
                    if torrent and torrent['title'] not in [t['title'] for t in torrents]:
                        torrents.append(torrent)
                        found_torrents.add(torrent)
                        
                        if len(torrents) >= max_results:
                            break
            
            self.stats['parsing_strategies_tested']['torrent_links'] = len(found_torrents)
        
        # Strategy 3: All table rows with content
        if not torrents:
            logger.info("Strategy 3: Testing all table rows...")
            all_rows = soup.find_all('tr')
            content_rows = []
            
            for row in all_rows:
                # Check if row has meaningful content (has links or multiple cells)
                if (len(row.find_all('td')) >= 2 or 
                    row.find('a') or 
                    len(row.get_text(strip=True)) > 20):
                    content_rows.append(row)
            
            for row in content_rows[:max_results * 2]:  # Check more rows
                torrent = self.parse_torrent_row(row, genre_name)
                if torrent and torrent['title'] not in [t['title'] for t in torrents]:
                    torrents.append(torrent)
                    
                    if len(torrents) >= max_results:
                        break
            
            self.stats['parsing_strategies_tested']['content_rows'] = len(content_rows)
        
        # Strategy 4: Text-based search for audiobook indicators
        if not torrents:
            logger.info("Strategy 4: Text-based search...")
            page_text = soup.get_text()
            lines = page_text.split('\n')
            
            for line in lines:
                if any(keyword in line.lower() for keyword in ['audiobook', 'narration', 'mp3', 'm4b']):
                    # This is a fallback - would need more sophisticated parsing
                    logger.info(f"Found potential audiobook text: {line.strip()[:100]}...")
            
            self.stats['parsing_strategies_tested']['text_search'] = len([line for line in lines if any(keyword in line.lower() for keyword in ['audiobook', 'narration', 'mp3', 'm4b'])])
        
        logger.info(f"Total torrents extracted: {len(torrents)}")
        return torrents[:max_results]

    def parse_torrent_row(self, row, genre_name: str, link=None) -> Dict:
        """Parse a single torrent row."""
        try:
            # Extract torrent ID from row id if available
            torrent_id = row.get('id', '').replace('tdr_', '') if row.get('id') else None
            
            # Find title link
            if link:
                title_link = link
            else:
                title_link = row.find('a', href=lambda x: x and '/t/' in x)
            
            if not title_link:
                return None
                
            title = title_link.get_text(strip=True)
            torrent_url = f"{self.base_url}{title_link['href']}"
            
            # Skip test/dummy entries
            if any(keyword in title.lower() for keyword in ['test', 'dummy', 'sample', 'placeholder']):
                return None
            
            # Extract additional info
            author = "Unknown"
            seeders = 0
            
            # Try to find author/narrator
            info_cells = row.find_all('td')
            for cell in info_cells:
                text = cell.get_text(strip=True)
                if 'by' in text.lower():
                    author = text
                # Try to find seeders
                try:
                    if text.isdigit() and int(text) > 0:
                        seeders = int(text)
                except:
                    pass
            
            return {
                'id': torrent_id or 'unknown',
                'title': title,
                'url': torrent_url,
                'author': author,
                'seeders': seeders,
                'genre': genre_name,
                'element': row  # Keep reference for deduplication
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse row: {e}")
            return None

    async def process_genre_hybrid(self, crawler: AsyncWebCrawler, genre_name: str, genre_code: str):
        """Process a genre using hybrid approach."""
        logger.info(f"Processing {genre_name} with hybrid approach...")
        
        # Try aiohttp authentication first (like working script)
        if await self.aiohttp_auth_login():
            # Use browser to crawl the authenticated page
            url = self.build_search_url(genre_code)
            
            try:
                result = await crawler.arun(
                    url=url,
                    config=CrawlerRunConfig(
                        cache_mode=CacheMode.BYPASS,
                        page_timeout=30000,
                        wait_for="css:body",
                        cookies=list(self.session_cookies.items()) if self.session_cookies else None
                    )
                )
                
                if result.success:
                    torrents = await self.extract_torrents_multiple_strategies(result.html, genre_name)
                    
                    logger.info(f"Found {len(torrents)} torrents in {genre_name}")
                    self.stats['torrents_found'] += len(torrents)
                    
                    # Add to qBittorrent
                    for torrent in torrents:
                        await self.add_to_qbittorrent(torrent)
                    
                    self.stats['genres_processed'].append(genre_name)
                else:
                    logger.error(f"Failed to crawl {genre_name}: {result.error_message}")
                    
            except Exception as e:
                logger.error(f"Error processing {genre_name}: {e}")
        else:
            logger.error(f"Authentication failed for {genre_name}")

    def build_search_url(self, genre_code: str) -> str:
        """Build MAM search URL."""
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
            "tor[sortType]=snatchedDesc",
            "tor[startNumber]=0",
            "thumbnail=true"
        ]
        
        return f"{base}?&{'&'.join(params)}"

    async def add_to_qbittorrent(self, torrent: Dict):
        """Add torrent to qBittorrent."""
        if not self.qb_client:
            logger.warning("qBittorrent not connected")
            return
            
        try:
            # Get torrent download URL
            torrent_id = torrent['id']
            if torrent_id != 'unknown':
                download_url = f"{self.base_url}/tor/download.php?tid={torrent_id}"
                
                self.qb_client.torrents_add(
                    urls=download_url,
                    category="audiobooks-auto",
                    tags=["mam", "audiobook", "auto"]
                )
                
                logger.info(f"Added: {torrent['title']}")
                self.stats['torrents_added'] += 1
                
        except Exception as e:
            logger.error(f"Failed to add torrent: {e}")

    async def run(self):
        """Main execution with hybrid approach."""
        logger.info("Starting Hybrid Audiobook Downloader")
        logger.info("=" * 60)
        
        browser_config = BrowserConfig(
            headless=True,
            viewport_width=1920,
            viewport_height=1080,
            verbose=False
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Process target genres
            for genre_name in ['Fantasy', 'Science Fiction']:
                await self.process_genre_hybrid(crawler, genre_name, self.GENRES[genre_name])
                await asyncio.sleep(3)
        
        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print execution summary."""
        logger.info("\n" + "=" * 60)
        logger.info("HYBRID DOWNLOADER SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Authentication method: {self.stats['auth_method_used']}")
        logger.info(f"Parsing strategies tested: {list(self.stats['parsing_strategies_tested'].keys())}")
        logger.info(f"Results per strategy: {self.stats['parsing_strategies_tested']}")
        logger.info(f"Total torrents found: {self.stats['torrents_found']}")
        logger.info(f"Total torrents added: {self.stats['torrents_added']}")
        logger.info(f"Genres processed: {self.stats['genres_processed']}")
        
        # Save detailed stats
        stats_file = f"hybrid_downloader_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Detailed stats saved to: {stats_file}")
        logger.info("=" * 60)

async def main():
    """Entry point."""
    downloader = HybridAudiobookDownloader()
    await downloader.run()

if __name__ == "__main__":
    asyncio.run(main())