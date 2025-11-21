#!/usr/bin/env python
"""
PHASE 1 DOWNLOAD - Simple username/password login, no cookie management
Direct approach: Log in, search, download
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('phase1_download.log', encoding='utf-8')
    ]
)
logger = logging.getLogger()

# Load config
env_file = Path('.env')
config = {}
if env_file.exists():
    for line in env_file.read_text().split('\n'):
        if line.strip() and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            config[k.strip()] = v.strip().strip('\'"')

MAM_USERNAME = config.get('MAM_USERNAME', '').strip('\'"')
MAM_PASSWORD = config.get('MAM_PASSWORD', '').strip('\'"')


class Phase1Download:
    """Phase 1 - Simple login with username/password"""

    def __init__(self):
        self.base_url = "https://www.myanonamouse.net"
        self.downloaded_torrents = []
        self.failed_searches = []
        self.start_time = datetime.now()
        self.session = None

    def login(self) -> bool:
        """Login to MAM with credentials"""
        logger.info("Logging in to MAM...")

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        try:
            # Get login page
            response = self.session.get(f'{self.base_url}/login.php', timeout=15)
            if response.status_code != 200:
                logger.error(f"Failed to access login page: {response.status_code}")
                return False

            # Submit credentials
            login_data = {
                'username': MAM_USERNAME,
                'password': MAM_PASSWORD,
                'login': 'Login'
            }

            response = self.session.post(
                f'{self.base_url}/takelogin.php',
                data=login_data,
                timeout=15,
                allow_redirects=True
            )

            if response.status_code != 200:
                logger.error(f"Login failed: {response.status_code}")
                return False

            # Verify authentication
            if self.session.cookies.get('lid'):
                logger.info("Authentication successful! (lid cookie received)")
                return True
            else:
                logger.warning("No session cookie received")
                return False

        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    def search_and_queue(self, author: str, series: str, book_num: int) -> Optional[Dict]:
        """Search for a book and queue it"""
        search_query = f"{author} {series} Book {book_num}"

        try:
            logger.info(f"Searching: {search_query}")

            # Build search URL
            params = {
                'tor[searchType]': 'all',
                'tor[searchIn]': 'torrents',
                'tor[srchIn][title]': 'true',
                'tor[srchIn][author]': 'true',
                'tor[cat][]': '13',
                'tor[browse_lang][]': '1',
                'tor[searchstr]': search_query,
                'tor[browseFlagsHideVsShow]': '0',
                'tor[sortType]': 'snatchedDesc',
                'tor[startNumber]': '0',
                'thumbnail': 'true'
            }

            query_string = '&'.join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
            search_url = f"{self.base_url}/tor/browse.php?{query_string}"

            # Get search results
            response = self.session.get(search_url, timeout=15)

            if response.status_code != 200:
                logger.warning(f"  Search failed: HTTP {response.status_code}")
                self.failed_searches.append({
                    'query': search_query,
                    'error': f'HTTP {response.status_code}'
                })
                return None

            # Parse results
            soup = BeautifulSoup(response.text, 'html.parser')
            rows = soup.find_all('tr')

            # Find torrent link
            found = False
            for row in rows:
                links = row.find_all('a')
                for link in links:
                    href = link.get('href', '')
                    text = link.text.strip()

                    # Check if this looks like a torrent
                    if 'torrent' in href.lower() or ('/t/' in href and len(text) > 10):
                        torrent_name = text
                        torrent_url = href if href.startswith('http') else f"{self.base_url}{href}"

                        logger.info(f"  Found: {torrent_name[:80]}")
                        self.downloaded_torrents.append({
                            'author': author,
                            'series': series,
                            'book': book_num,
                            'name': torrent_name,
                            'url': torrent_url,
                            'queued_at': datetime.now().isoformat()
                        })
                        found = True
                        break

                if found:
                    break

            if not found:
                logger.warning(f"  No results found")
                self.failed_searches.append({
                    'query': search_query,
                    'error': 'No results'
                })
                return None

            return {'name': torrent_name}

        except Exception as e:
            logger.error(f"  Error: {str(e)[:100]}")
            self.failed_searches.append({
                'query': search_query,
                'error': str(e)[:100]
            })
            return None

    def execute_phase1(self):
        """Execute Phase 1"""
        logger.info("="*80)
        logger.info("PHASE 1 DOWNLOAD - LOGIN WITH CREDENTIALS")
        logger.info("="*80)

        # Login
        if not self.login():
            logger.error("Login failed - aborting")
            return

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

                if self.search_and_queue(author, series, book_num):
                    successful += 1

                time.sleep(3)

        # Summary
        logger.info("\n" + "="*80)
        logger.info("PHASE 1 COMPLETE")
        logger.info("="*80)
        logger.info(f"Searched: {total} books")
        logger.info(f"Found: {successful}")
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
                'failed': len(self.failed_searches)
            }
        }

        with open('phase1_download_results.json', 'w') as f:
            json.dump(results, f, indent=2)

        logger.info("Results saved to phase1_download_results.json")


if __name__ == '__main__':
    executor = Phase1Download()
    executor.execute_phase1()
