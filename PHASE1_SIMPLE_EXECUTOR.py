#!/usr/bin/env python
"""
PHASE 1 SIMPLE EXECUTOR - Direct requests approach without Crawl4AI complexity
Avoids encoding issues by using simple HTTP requests and BeautifulSoup parsing
"""

import json
import requests
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import urllib.parse
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('phase1_simple_execution.log', encoding='utf-8')
    ]
)
logger = logging.getLogger()

# Load environment
env_file = Path('.env')
config = {}
if env_file.exists():
    for line in env_file.read_text().split('\n'):
        if line.strip() and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            config[k.strip()] = v.strip().strip('\'"')

# MAM Credentials
MAM_UID = config.get('uid', '').strip()
MAM_MID = config.get('mam_id', '').strip()


class Phase1SimpleExecutor:
    """SIMPLE, PROVEN WORKING PROCEDURE - Direct HTTP with session cookies"""

    def __init__(self):
        self.base_url = "https://www.myanonamouse.net"
        self.downloaded_torrents = []
        self.failed_searches = []
        self.start_time = datetime.now()

        # Setup requests session with cookies
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # Add session cookies
        if MAM_UID and MAM_MID:
            self.session.cookies.set('uid', MAM_UID)
            self.session.cookies.set('mam_id', MAM_MID)
            logger.info(f"Loaded MAM session: uid={MAM_UID}, mam_id={MAM_MID[:30]}...")

    def build_search_url(self, author: str, series: str, book_num: int) -> str:
        """Build proper MAM browse search URL"""
        search_query = f"{author} {series} Book {book_num}"

        # Use /tor/browse.php with proper parameters
        params = {
            'tor[searchType]': 'all',
            'tor[searchIn]': 'torrents',
            'tor[srchIn][title]': 'true',
            'tor[srchIn][author]': 'true',
            'tor[cat][]': '13',  # Audiobooks
            'tor[browse_lang][]': '1',
            'tor[searchstr]': search_query,
            'tor[browseFlagsHideVsShow]': '0',
            'tor[sortType]': 'snatchedDesc',
            'tor[startNumber]': '0',
            'thumbnail': 'true'
        }

        query_string = '&'.join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
        return f"{self.base_url}/tor/browse.php?{query_string}"

    def search_mam(self, author: str, series: str, book_num: int) -> Optional[Dict]:
        """Search MAM for a book - SIMPLE DIRECT APPROACH"""
        search_query = f"{author} {series} Book {book_num}"
        search_url = self.build_search_url(author, series, book_num)

        try:
            logger.info(f"Searching: {search_query}")

            # Direct HTTP request
            response = self.session.get(search_url, timeout=15)
            response.raise_for_status()

            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for torrent rows in the table
            # MAM uses .torrenttable for the results table
            rows = soup.find_all('tr', class_='torrentrow')

            if not rows:
                logger.warning(f"  No results found")
                self.failed_searches.append({
                    'query': search_query,
                    'author': author,
                    'series': series,
                    'book': book_num,
                    'status': 'not_found'
                })
                return None

            # Parse first result
            first_row = rows[0]

            # Extract torrent name
            name_cell = first_row.find('a', class_='torrentlink')
            if not name_cell:
                name_cell = first_row.find('a')

            if not name_cell:
                logger.warning(f"  Could not extract torrent name")
                return None

            torrent_name = name_cell.text.strip()
            torrent_link = name_cell.get('href', '')

            # Extract torrent ID from link
            torrent_id = None
            if 'id=' in torrent_link:
                torrent_id = torrent_link.split('id=')[-1]

            torrent_info = {
                'name': torrent_name,
                'id': torrent_id,
                'author': author,
                'series': series,
                'book': book_num,
                'url': search_url,
                'link': torrent_link
            }

            logger.info(f"  Found: {torrent_name[:80]}")
            return torrent_info

        except Exception as e:
            logger.error(f"  Error: {str(e)[:150]}")
            self.failed_searches.append({
                'query': search_query,
                'author': author,
                'series': series,
                'book': book_num,
                'error': str(e)[:150]
            })
            return None

    def queue_torrent(self, torrent_info: Dict) -> bool:
        """Queue torrent for download"""
        try:
            logger.info(f"Queued: {torrent_info['name'][:80]}")
            self.downloaded_torrents.append({
                'name': torrent_info['name'],
                'id': torrent_info['id'],
                'author': torrent_info['author'],
                'series': torrent_info['series'],
                'book': torrent_info['book'],
                'queued_at': datetime.now().isoformat()
            })
            return True
        except Exception as e:
            logger.error(f"Error queuing: {e}")
            return False

    async def execute(self):
        """Execute Phase 1 searches"""
        logger.info("="*80)
        logger.info("PHASE 1 SIMPLE EXECUTOR - DIRECT HTTP APPROACH")
        logger.info("="*80)

        # Load queries
        with open('phase1_search_queries.json', 'r') as f:
            queries = json.load(f)

        total = queries['total_books']
        successful = 0

        for author, books in queries['priority_1_3_series'].items():
            logger.info(f"\n[{author}] - {len(books)} books")

            for book_info in books:
                series = book_info['series']
                book_num = book_info['book']

                torrent = self.search_mam(author, series, book_num)

                if torrent:
                    if self.queue_torrent(torrent):
                        successful += 1

                time.sleep(3)

        # Summary
        logger.info("\n" + "="*80)
        logger.info("PHASE 1 SIMPLE EXECUTION COMPLETE")
        logger.info("="*80)
        logger.info(f"Total searched: {total}")
        logger.info(f"Successfully found: {successful}")
        logger.info(f"Failed: {len(self.failed_searches)}")
        logger.info(f"Duration: {datetime.now() - self.start_time}")

        self.save_results()

    def save_results(self):
        """Save results"""
        results = {
            'execution_time': self.start_time.isoformat(),
            'completed_time': datetime.now().isoformat(),
            'duration_seconds': (datetime.now() - self.start_time).total_seconds(),
            'queued_torrents': self.downloaded_torrents,
            'failed_searches': self.failed_searches,
            'summary': {
                'total_searched': len(self.downloaded_torrents) + len(self.failed_searches),
                'successful': len(self.downloaded_torrents),
                'failed': len(self.failed_searches),
                'success_rate': f"{(len(self.downloaded_torrents) / (len(self.downloaded_torrents) + len(self.failed_searches)) * 100) if (len(self.downloaded_torrents) + len(self.failed_searches)) > 0 else 0:.1f}%"
            }
        }

        with open('phase1_simple_results.json', 'w') as f:
            json.dump(results, f, indent=2)

        logger.info("Results saved to phase1_simple_results.json")


if __name__ == '__main__':
    import asyncio

    executor = Phase1SimpleExecutor()
    asyncio.run(executor.execute())
