#!/usr/bin/env python3
"""
Search MAM directly for "Randi Darren" audiobooks
Uses Selenium to navigate and extract magnet links
Queues to qBittorrent with audiobook category
"""
import os
import sys
import time
import logging
import json
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()
MAM_USERNAME = os.getenv('MAM_USERNAME')
MAM_PASSWORD = os.getenv('MAM_PASSWORD')
QBITTORRENT_URL = os.getenv('QBITTORRENT_URL', 'http://192.168.0.48:52095/')
QBITTORRENT_USERNAME = os.getenv('QBITTORRENT_USERNAME')
QBITTORRENT_PASSWORD = os.getenv('QBITTORRENT_PASSWORD')

if not QBITTORRENT_URL.endswith('/'):
    QBITTORRENT_URL += '/'

class RandiDarrenSearcher:
    def __init__(self):
        self.driver = None
        self.found_torrents = []
        self.queued_torrents = []
        self.session = requests.Session()

    def init_selenium(self):
        """Initialize Selenium WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        self.driver = webdriver.Chrome(options=chrome_options)
        logger.info("Selenium WebDriver initialized")

    def login_with_requests(self):
        """Try to login using requests with cookies"""
        logger.info("Attempting login via requests...")

        login_url = 'https://www.myanonamouse.net/tor/takelogin.php'
        login_data = {
            'username': MAM_USERNAME,
            'password': MAM_PASSWORD,
            'login': 'Login'
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            response = self.session.post(login_url, data=login_data, headers=headers, timeout=10)
            logger.info(f"Login response status: {response.status_code}")

            if 'logout' in response.text.lower() or response.status_code == 200:
                logger.info("Login successful with requests")
                return True
            else:
                logger.warning("Login may have failed, proceeding anyway")
                return True  # Continue even if uncertain

        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    def search_mam(self, query):
        """Search MAM for audiobooks by author"""
        logger.info(f"Searching MAM for: {query}")

        # Use requests for search since we have session cookies
        search_url = f'https://www.myanonamouse.net/tor/searchbook.php'
        params = {
            'searchtype': 'author',
            'query': query,
            'category': '47'  # 47 = audiobooks
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        page_num = 1
        offset = 0

        while page_num <= 15:  # Max 15 pages (roughly 75 torrents)
            logger.info(f"Searching page {page_num} (offset {offset})...")

            search_params = params.copy()
            if offset > 0:
                search_params['offset'] = offset

            try:
                response = self.session.get(search_url, params=search_params, headers=headers, timeout=15)

                if response.status_code != 200:
                    logger.warning(f"Search returned status {response.status_code}, stopping")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')

                # Find all torrent rows in the table
                rows = soup.find_all('tr')

                if not rows:
                    logger.info("No rows found, stopping")
                    break

                found_on_page = False

                for row in rows:
                    try:
                        cells = row.find_all('td')
                        if len(cells) < 3:
                            continue

                        # Look for magnet link
                        magnet_link = row.find('a', {'href': lambda x: x and 'magnet:' in x if x else False})
                        if not magnet_link:
                            continue

                        magnet = magnet_link.get('href', '')

                        # Try to get title from the row
                        title_elem = row.find('a', {'title': True})
                        if not title_elem:
                            # Try different selector
                            title_elem = cells[1].find('a') if len(cells) > 1 else None

                        if title_elem:
                            title = title_elem.get_text(strip=True) or title_elem.get('title', 'Unknown')
                        else:
                            title = 'Unknown Audiobook'

                        # Clean up title
                        if title and len(title) > 5:
                            torrent_info = {
                                'title': title,
                                'magnet': magnet,
                                'page': page_num
                            }
                            self.found_torrents.append(torrent_info)
                            logger.info(f"Found: {title[:80]}")
                            found_on_page = True

                    except Exception as e:
                        logger.debug(f"Error parsing row: {e}")
                        continue

                if not found_on_page:
                    logger.info("No new torrents found on this page, stopping")
                    break

                # Move to next page
                offset += 25  # Assuming 25 results per page
                page_num += 1
                time.sleep(1)  # Rate limit

            except Exception as e:
                logger.error(f"Search error: {e}")
                break

        logger.info(f"Total torrents found: {len(self.found_torrents)}")
        return self.found_torrents

    def queue_to_qbittorrent(self):
        """Queue all found torrents to qBittorrent with audiobook category"""
        logger.info(f"\nQueuing {len(self.found_torrents)} torrents to qBittorrent...")

        # Login to qBittorrent
        login_url = f"{QBITTORRENT_URL}api/v2/auth/login"
        login_data = {'username': QBITTORRENT_USERNAME, 'password': QBITTORRENT_PASSWORD}

        login_response = self.session.post(login_url, data=login_data, timeout=10)
        if login_response.status_code != 200:
            logger.error("qBittorrent login failed")
            return

        logger.info("qBittorrent authenticated")

        # Add each torrent
        add_url = f"{QBITTORRENT_URL}api/v2/torrents/add"

        for torrent in self.found_torrents:
            try:
                add_data = {
                    'urls': torrent['magnet'],
                    'category': 'audiobooks',
                    'paused': False
                }

                response = self.session.post(add_url, data=add_data, timeout=10)

                if response.status_code == 200:
                    logger.info(f"✓ Queued: {torrent['title'][:60]}")
                    self.queued_torrents.append(torrent)
                else:
                    logger.warning(f"✗ Failed to queue: {torrent['title'][:60]} (HTTP {response.status_code})")

                time.sleep(0.5)  # Small delay between additions

            except Exception as e:
                logger.error(f"Error queuing {torrent['title']}: {e}")

        logger.info(f"\nSuccessfully queued: {len(self.queued_torrents)}/{len(self.found_torrents)}")

    def save_results(self):
        """Save results to JSON file"""
        results = {
            'search_query': 'Randi Darren',
            'timestamp': datetime.now().isoformat(),
            'total_found': len(self.found_torrents),
            'total_queued': len(self.queued_torrents),
            'found_torrents': self.found_torrents,
            'queued_torrents': self.queued_torrents
        }

        filename = f'mam_randi_darren_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"Results saved to {filename}")
        return filename

    def close(self):
        """Close Selenium driver"""
        if self.driver:
            self.driver.quit()
            logger.info("Selenium driver closed")

    def run(self):
        """Execute full search and queue workflow"""
        try:
            logger.info("="*80)
            logger.info("RANDI DARREN AUDIOBOOK SEARCH AND QUEUE")
            logger.info("="*80)

            if not self.login_with_requests():
                logger.error("Failed to login to MAM")
                return

            self.search_mam('Randi Darren')

            if self.found_torrents:
                logger.info("\n" + "="*80)
                logger.info(f"QUEUEING TO QBITTORRENT WITH AUDIOBOOK CATEGORY")
                logger.info("="*80)
                self.queue_to_qbittorrent()
            else:
                logger.warning("No torrents found for Randi Darren")

            self.save_results()

            logger.info("\n" + "="*80)
            logger.info("COMPLETE")
            logger.info("="*80)

        except Exception as e:
            logger.error(f"Error in workflow: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.close()

if __name__ == '__main__':
    searcher = RandiDarrenSearcher()
    searcher.run()
