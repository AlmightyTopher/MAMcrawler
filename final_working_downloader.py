"""
Final Working Audiobook Downloader - Browser Auth + Multiple Parsing Strategies
This combines the working browser authentication with robust torrent parsing
"""
import asyncio
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any
from dotenv import load_dotenv

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from bs4 import BeautifulSoup
import qbittorrentapi

load_dotenv()

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class FinalAudiobookDownloader:
    """Final working downloader using browser authentication + robust parsing."""

    # MAM Category codes for target genres
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
        
        # qBittorrent setup
        self.qb_client = self.setup_qbittorrent()
        
        # Stats tracking
        self.stats = {
            'started_at': datetime.now().isoformat(),
            'authentication_success': False,
            'parsing_strategies_tested': {},
            'torrents_found': 0,
            'torrents_added': 0,
            'genres_processed': [],
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
            logger.info(f"Connected to qBittorrent {client.app.version}")
            return client
        except Exception as e:
            logger.warning(f"qBittorrent connection failed: {e}")
            return None

    async def browser_login(self, crawler: AsyncWebCrawler) -> bool:
        """Login using browser automation (this method works)."""
        logger.info("Performing browser authentication...")
        
        login_js = """
        // Wait for page load
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Fill login form
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
            return {success: true, authenticated: true};
        }
        return {success: false, error: "Login form not found"};
        """
        
        try:
            result = await crawler.arun(
                url=f"{self.base_url}/login.php",
                config=CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS,
                    js_code=login_js,
                    wait_for="css:body",
                    page_timeout=60000
                )
            )
            
            if result.success:
                logger.info("Browser authentication successful")
                self.stats['authentication_success'] = True
                return True
            else:
                logger.error(f"Browser authentication failed: {result.error_message}")
                return False
                
        except Exception as e:
            logger.error(f"Browser authentication error: {e}")
            return False

    def build_mam_search_url(self, genre_code: str, days_back: int = 7) -> str:
        """Build MAM search URL for genre and time range."""
        import datetime
        from datetime import timedelta
        
        end_date = datetime.datetime.now()
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
            "tor[sortType]=snatchedDesc",
            "tor[startNumber]=0",
            "thumbnail=true"
        ]

        return f"{base}?&{'&'.join(params)}"

    async def extract_torrents_robust(self, html: str, genre_name: str, max_results: int = 10) -> List[Dict]:
        """Extract torrents using multiple strategies - the robust parser."""
        soup = BeautifulSoup(html, 'lxml')
        torrents = []
        
        logger.info(f"Extracting torrents for {genre_name} using robust parser...")
        
        # Strategy 1: Primary - tdr_ pattern (from working script)
        logger.info("Strategy 1: tdr_ pattern...")
        tdr_rows = soup.find_all('tr', id=lambda x: x and x.startswith('tdr_'))
        strategy1_count = 0
        
        for row in tdr_rows:
            torrent = self.parse_torrent_row(row, genre_name)
            if torrent:
                torrents.append(torrent)
                strategy1_count += 1
                if len(torrents) >= max_results:
                    break
        
        self.stats['parsing_strategies_tested']['tdr_pattern'] = strategy1_count
        
        # Strategy 2: Torrent links pattern (if tdr_ didn't work)
        if not torrents:
            logger.info("Strategy 2: Torrent link pattern...")
            torrent_links = soup.find_all('a', href=lambda x: x and '/t/' in x)
            strategy2_count = 0
            
            for link in torrent_links:
                if len(torrents) >= max_results:
                    break
                    
                parent_row = link.find_parent('tr')
                if parent_row:
                    # Extract torrent ID from URL
                    torrent_url = link['href']
                    torrent_id = None
                    if '/t/' in torrent_url:
                        torrent_id = torrent_url.split('/t/')[1].split('/')[0]
                    
                    title = link.get_text(strip=True)
                    if title and not self.is_test_entry(title):
                        torrent = {
                            'id': torrent_id or 'unknown',
                            'title': title,
                            'url': f"{self.base_url}{torrent_url}",
                            'genre': genre_name,
                            'author': 'Unknown',
                            'seeders': 0
                        }
                        torrents.append(torrent)
                        strategy2_count += 1
            
            self.stats['parsing_strategies_tested']['torrent_links'] = strategy2_count
        
        # Strategy 3: Table rows with content (fallback)
        if not torrents:
            logger.info("Strategy 3: Content-based row analysis...")
            all_rows = soup.find_all('tr')
            strategy3_count = 0
            
            for row in all_rows:
                if len(torrents) >= max_results:
                    break
                    
                # Check if row has meaningful content
                text_content = row.get_text(strip=True)
                if (len(text_content) > 20 and 
                    any(keyword in text_content.lower() for keyword in ['mp3', 'm4b', 'audiobook', 'gb', 'mb'])):
                    
                    torrent = self.parse_torrent_row(row, genre_name)
                    if torrent:
                        torrents.append(torrent)
                        strategy3_count += 1
            
            self.stats['parsing_strategies_tested']['content_analysis'] = strategy3_count
        
        logger.info(f"Extracted {len(torrents)} torrents for {genre_name}")
        return torrents[:max_results]

    def parse_torrent_row(self, row, genre_name: str) -> Dict:
        """Parse a single torrent row with robust extraction."""
        try:
            # Get torrent ID from row ID
            torrent_id = row.get('id', '').replace('tdr_', '') if row.get('id') else None
            
            # Find title link
            title_link = row.find('a', href=lambda x: x and '/t/' in x)
            if not title_link:
                return None
                
            title = title_link.get_text(strip=True)
            
            # Skip test/dummy entries
            if self.is_test_entry(title):
                return None
            
            # Extract additional info
            author = "Unknown"
            seeders = 0
            size = "Unknown"
            
            # Parse row content for additional details
            cells = row.find_all('td')
            for cell in cells:
                cell_text = cell.get_text(strip=True)
                
                # Look for author patterns
                if 'by' in cell_text.lower():
                    author = cell_text
                
                # Look for seeders
                if cell_text.isdigit() and int(cell_text) > 0:
                    seeders = int(cell_text)
                
                # Look for size
                if any(unit in cell_text.lower() for unit in ['gb', 'mb', 'mb']):
                    size = cell_text
            
            return {
                'id': torrent_id or 'unknown',
                'title': title,
                'url': f"{self.base_url}{title_link['href']}",
                'author': author,
                'seeders': seeders,
                'size': size,
                'genre': genre_name
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse torrent row: {e}")
            return None

    def is_test_entry(self, title: str) -> bool:
        """Check if title is a test/dummy entry."""
        test_keywords = [
            'test', 'dummy', 'sample', 'placeholder', 'example', 
            'test audiobook', 'dummy book', 'sample audio'
        ]
        
        return any(keyword in title.lower() for keyword in test_keywords)

    async def add_to_qbittorrent(self, torrent: Dict):
        """Add torrent to qBittorrent."""
        if not self.qb_client:
            logger.warning("qBittorrent not connected")
            return
            
        try:
            torrent_id = torrent['id']
            if torrent_id != 'unknown':
                download_url = f"{self.base_url}/tor/download.php?tid={torrent_id}"
                
                self.qb_client.torrents_add(
                    urls=download_url,
                    category="audiobooks-auto",
                    tags=["mam", "audiobook", "auto", torrent['genre'].lower().replace(' ', '_')]
                )
                
                logger.info(f"Added to qBittorrent: {torrent['title']}")
                self.stats['torrents_added'] += 1
            else:
                logger.warning(f"Cannot add torrent - no ID: {torrent['title']}")
                
        except Exception as e:
            logger.error(f"Failed to add torrent: {e}")

    async def process_genre(self, crawler: AsyncWebCrawler, genre_name: str, genre_code: str):
        """Process a single genre with robust extraction."""
        logger.info(f"Processing {genre_name}...")
        
        try:
            # Build search URL
            url = self.build_mam_search_url(genre_code)
            logger.info(f"URL: {url}")
            
            # Crawl the page
            result = await crawler.arun(
                url=url,
                config=CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS,
                    wait_for="css:body",
                    page_timeout=30000
                )
            )
            
            if result.success:
                # Extract torrents using robust parser
                max_results = 10
                torrents = await self.extract_torrents_robust(result.html, genre_name, max_results)
                
                self.stats['torrents_found'] += len(torrents)
                logger.info(f"Found {len(torrents)} torrents in {genre_name}")
                
                # Add to qBittorrent
                for torrent in torrents:
                    await self.add_to_qbittorrent(torrent)
                    await asyncio.sleep(1)  # Rate limiting
                
                self.stats['genres_processed'].append(genre_name)
            else:
                error_msg = f"Failed to crawl {genre_name}: {result.error_message}"
                logger.error(error_msg)
                self.stats['errors'].append(error_msg)
                
        except Exception as e:
            error_msg = f"Error processing {genre_name}: {str(e)}"
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)

    async def run(self):
        """Main execution using working browser authentication."""
        logger.info("Starting Final Working Audiobook Downloader")
        logger.info("=" * 70)
        
        browser_config = BrowserConfig(
            headless=True,
            viewport_width=1920,
            viewport_height=1080,
            verbose=False
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            # First: Login
            if not await self.browser_login(crawler):
                logger.error("Authentication failed - aborting")
                return
            
            # Second: Process each genre
            for genre_name in ['Fantasy', 'Science Fiction']:
                await self.process_genre(crawler, genre_name, self.GENRES[genre_name])
                await asyncio.sleep(5)  # Pause between genres
        
        # Print final summary
        self.print_summary()

    def print_summary(self):
        """Print final execution summary."""
        logger.info("\n" + "=" * 70)
        logger.info("FINAL WORKING DOWNLOADER SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Authentication success: {self.stats['authentication_success']}")
        logger.info(f"Genres processed: {self.stats['genres_processed']}")
        logger.info(f"Torrents found: {self.stats['torrents_found']}")
        logger.info(f"Torrents added: {self.stats['torrents_added']}")
        logger.info(f"Parsing strategies tested: {self.stats['parsing_strategies_tested']}")
        logger.info(f"Errors encountered: {len(self.stats['errors'])}")
        
        if self.stats['errors']:
            logger.info("Errors:")
            for error in self.stats['errors']:
                logger.info(f"  - {error}")
        
        # Save detailed stats
        stats_file = f"final_downloader_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Detailed stats saved to: {stats_file}")
        logger.info("=" * 70)

async def main():
    """Entry point."""
    downloader = FinalAudiobookDownloader()
    await downloader.run()

if __name__ == "__main__":
    asyncio.run(main())