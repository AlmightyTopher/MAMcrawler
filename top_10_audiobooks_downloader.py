#!/usr/bin/env python3
"""
Top 10 Audiobook Downloader
Downloads the top 10 audiobooks from MyAnonamouse using VPN-protected scraping.
"""

import asyncio
import os
import sys
import json
import logging
import random
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
        logging.FileHandler('top_10_audiobooks_download.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class Top10AudiobookDownloader:
    """Download top 10 audiobooks from multiple popular genres."""

    # Popular audiobook genres with high download rates
    POPULAR_GENRES = {
        'Mystery/Thriller': 'c37',
        'Fantasy': 'c38', 
        'Science Fiction': 'c40',
        'Romance': 'c41',
        'Biography/Memoir': 'c43',
        'Historical Fiction': 'c53',
        'Self-Help': 'c54',
        'Business/Economics': 'c83',
        'True Crime': 'c85',
        'Horror': 'c86'
    }

    def __init__(self):
        self.mam_username = os.getenv('MAM_USERNAME', 'your_username')
        self.mam_password = os.getenv('MAM_PASSWORD', 'your_password')
        self.mam_base_url = os.getenv('MAM_BASE_URL', 'https://myanonamouse.com')
        
        # VPN proxy configuration
        self.vpn_proxy = {
            'http': 'socks5://127.0.0.1:9050',
            'https': 'socks5://127.0.0.1:9050'
        }
        
        # qBittorrent configuration
        self.qbt_host = os.getenv('QBIT_HOST', 'localhost')
        self.qbt_port = int(os.getenv('QBT_PORT', '8080'))
        self.qbt_username = os.getenv('QBT_USERNAME', 'admin')
        self.qbt_password = os.getenv('QBT_PASSWORD', 'adminadmin')
        
        self.qbt_client = None
        self.session = None
        self.crawler = None
        
    async def initialize_services(self):
        """Initialize qBittorrent client and web crawler."""
        try:
            # Initialize qBittorrent client
            self.qbt_client = qbittorrentapi.Client(
                host=self.qbt_host,
                port=self.qbt_port,
                username=self.qbt_username,
                password=self.qbt_password
            )
            self.qbt_client.auth_log_in()
            logger.info("✅ qBittorrent client initialized successfully")
            
            # Initialize browser for web scraping
            self.crawler = AsyncWebCrawler(
                browser_config=BrowserConfig(
                    headless=True,
                    proxy_config={'http': 'socks5://127.0.0.1:9050', 'https': 'socks5://127.0.0.1:9050'}
                ),
                crawler_config=CrawlerRunConfig(
                    cache_mode=CacheMode.DISABLED,
                    delay_before_domid_output=3.0
                )
            )
            await self.crawler.__aenter__()
            logger.info("✅ VPN-protected web crawler initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize services: {e}")
            raise

    async def scrape_genre_top_audiobooks(self, genre: str, category: str) -> List[Dict]:
        """Scrape top audiobooks from a specific genre."""
        logger.info(f"🔍 Scraping top audiobooks from {genre}...")
        
        try:
            # Get top results for the genre
            url = f"{self.mam_base_url}/torrents.php"
            params = {
                'torsearch[search]': '',
                'torsearch[category]': category,
                'torsearch[searchMode]': 'all',
                'torsearch[order]': 'seeders',
                'torsearch[sort]': 'desc',
                'torsearch[type]': 'desc'
            }
            
            async with self.crawler:
                result = await self.crawler.arun(
                    url=url,
                    params=params,
                    wait_for="css:.torrent_name",
                    timeout=30
                )
                
                if not result.success:
                    logger.warning(f"⚠️ Failed to scrape {genre}: {result.error_message}")
                    return []
                
                # Parse the results
                soup = BeautifulSoup(result.html, 'html.parser')
                audiobooks = []
                
                # Find torrent rows
                rows = soup.find_all('tr', class_='b1')
                for row in rows[:2]:  # Get top 2 from each genre for total of 20, then take top 10
                    try:
                        title_elem = row.find('td', class_='torrent_name')
                        if not title_elem:
                            continue
                            
                        title = title_elem.get_text(strip=True)
                        magnet_elem = row.find('a', href=lambda x: x and x.startswith('magnet:'))
                        seeders_elem = row.find('td', string=lambda x: x and x.isdigit())
                        
                        if magnet_elem and seeders_elem:
                            magnet_link = magnet_elem['href']
                            seeders = int(seeders_elem.get_text(strip=True))
                            
                            # Filter for audiobooks with good seed counts
                            if 'audiobook' in title.lower() or 'audio' in title.lower():
                                audiobooks.append({
                                    'title': title,
                                    'magnet': magnet_link,
                                    'seeders': seeders,
                                    'genre': genre,
                                    'category': category
                                })
                                
                    except Exception as e:
                        logger.warning(f"⚠️ Error parsing audiobook row: {e}")
                        continue
                        
            logger.info(f"✅ Found {len(audiobooks)} top audiobooks in {genre}")
            return audiobooks
            
        except Exception as e:
            logger.error(f"❌ Error scraping {genre}: {e}")
            return []

    async def find_top_10_audiobooks(self) -> List[Dict]:
        """Find the top 10 audiobooks across popular genres."""
        logger.info("🚀 Starting top 10 audiobook search...")
        
        all_audiobooks = []
        
        # Scrape each popular genre
        for genre, category in self.POPULAR_GENRES.items():
            audiobooks = await self.scrape_genre_top_audiobooks(genre, category)
            all_audiobooks.extend(audiobooks)
            
            # Random delay to avoid detection
            await asyncio.sleep(random.uniform(3, 7))
        
        # Sort by seeders and get top 10
        top_audiobooks = sorted(all_audiobooks, key=lambda x: x['seeders'], reverse=True)[:10]
        
        logger.info(f"🏆 Selected top {len(top_audiobooks)} audiobooks:")
        for i, book in enumerate(top_audiobooks, 1):
            logger.info(f"   {i}. {book['title'][:60]}... ({book['seeders']} seeders)")
            
        return top_audiobooks

    async def download_audiobooks(self, audiobooks: List[Dict]):
        """Download the selected audiobooks via qBittorrent."""
        logger.info(f"📥 Starting downloads for {len(audiobooks)} audiobooks...")
        
        downloaded = 0
        
        for audiobook in audiobooks:
            try:
                logger.info(f"📥 Adding to qBittorrent: {audiobook['title'][:60]}...")
                
                # Add torrent to qBittorrent
                self.qbt_client.torrents_add(
                    urls=[audiobook['magnet']],
                    save_path="./downloads/audiobooks",
                    category="Audiobooks",
                    tags=[audiobook['genre']]
                )
                
                downloaded += 1
                logger.info(f"✅ Download started for: {audiobook['title'][:60]}...")
                
                # Small delay between additions
                await asyncio.sleep(random.uniform(2, 5))
                
            except Exception as e:
                logger.error(f"❌ Failed to download {audiobook['title'][:60]}: {e}")
        
        logger.info(f"🎉 Successfully started {downloaded} audiobook downloads!")
        return downloaded

    async def monitor_downloads(self):
        """Monitor download progress."""
        logger.info("📊 Monitoring download progress...")
        
        try:
            while True:
                # Get all audiobook torrents
                torrents = self.qbt_client.torrents_info(category="Audiobooks")
                
                if not torrents:
                    logger.info("📋 No audiobook downloads found")
                    break
                
                active_downloads = 0
                completed = 0
                
                for torrent in torrents:
                    if torrent.state_enum.is_downloading:
                        active_downloads += 1
                        progress = int(torrent.progress * 100)
                        logger.info(f"📥 {torrent.name[:50]}... {progress}% ({torrent.num_seeds} seeds)")
                    elif torrent.state_enum.is_complete:
                        completed += 1
                        logger.info(f"✅ {torrent.name[:50]}... COMPLETED")
                
                if completed == len(torrents):
                    logger.info("🎉 All audiobook downloads completed!")
                    break
                
                logger.info(f"📊 Progress: {active_downloads} downloading, {completed} completed of {len(torrents)} total")
                await asyncio.sleep(30)  # Check every 30 seconds
                
        except Exception as e:
            logger.error(f"❌ Error monitoring downloads: {e}")

    async def cleanup(self):
        """Clean up resources."""
        try:
            if self.crawler:
                await self.crawler.__aexit__(None, None, None)
            if self.qbt_client:
                self.qbt_client.auth_log_out()
            logger.info("🧹 Cleanup completed")
        except Exception as e:
            logger.warning(f"⚠️ Cleanup warning: {e}")

    async def run(self):
        """Main execution flow."""
        start_time = datetime.now()
        logger.info("=" * 80)
        logger.info("🎵 TOP 10 AUDIOBOOK DOWNLOADER - STARTED")
        logger.info("=" * 80)
        
        try:
            # Initialize services
            await self.initialize_services()
            
            # Find top audiobooks
            top_audiobooks = await self.find_top_10_audiobooks()
            
            if not top_audiobooks:
                logger.warning("⚠️ No audiobooks found to download")
                return
            
            # Download audiobooks
            downloaded_count = await self.download_audiobooks(top_audiobooks)
            
            # Save results
            results_file = f"top_10_audiobooks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(top_audiobooks, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Results saved to: {results_file}")
            
            # Monitor downloads
            if downloaded_count > 0:
                await self.monitor_downloads()
            
            # Summary
            end_time = datetime.now()
            duration = end_time - start_time
            logger.info("=" * 80)
            logger.info("🎉 TOP 10 AUDIOBOOK DOWNLOADER - COMPLETED")
            logger.info(f"📊 Processed: {len(top_audiobooks)} audiobooks")
            logger.info(f"📥 Downloaded: {downloaded_count} audiobooks")
            logger.info(f"⏱️ Duration: {duration}")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}")
            raise
        finally:
            await self.cleanup()


async def main():
    """Main entry point."""
    try:
        downloader = Top10AudiobookDownloader()
        await downloader.run()
    except KeyboardInterrupt:
        logger.info("🛑 Operation cancelled by user")
    except Exception as e:
        logger.error(f"❌ Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Ensure downloads directory exists
    Path("./downloads/audiobooks").mkdir(parents=True, exist_ok=True)
    
    asyncio.run(main())