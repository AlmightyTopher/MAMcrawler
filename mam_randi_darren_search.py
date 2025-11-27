#!/usr/bin/env python3
"""
Search MAM directly for "Randi Darren" audiobooks
Uses Selenium to handle JavaScript-heavy MAM interface
Extracts magnet links and queues to qBittorrent with audiobook category
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

    def init_selenium(self):
        """Initialize Selenium WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        self.driver = webdriver.Chrome(options=chrome_options)
        logger.info("Selenium WebDriver initialized")

    def login_mam(self):
        """Login to MAM using credentials"""
        logger.info("Navigating to MAM login page...")
        self.driver.get('https://www.myanonamouse.net/tor/login.php')
        time.sleep(2)

        try:
            # Find and fill login form
            username_field = self.driver.find_element(By.NAME, 'username')
            password_field = self.driver.find_element(By.NAME, 'password')
            login_button = self.driver.find_element(By.XPATH, "//input[@type='submit' or @value='Login']")

            username_field.clear()
            username_field.send_keys(MAM_USERNAME)
            password_field.clear()
            password_field.send_keys(MAM_PASSWORD)

            logger.info("Submitting login form...")
            login_button.click()
            time.sleep(3)

            # Check if login was successful
            page_source = self.driver.page_source.lower()
            if 'logout' in page_source or 'my account' in page_source:
                logger.info("MAM login successful")
                return True
            else:
                logger.warning("MAM login may have failed")
                return False

        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    def search_mam(self, query):
        """Search MAM for audiobooks by author"""
        logger.info(f"Searching MAM for: {query}")

        # Navigate to search page
        search_url = f'https://www.myanonamouse.net/tor/searchbook.php?searchtype=author&query={query}&category=47'
        self.driver.get(search_url)
        time.sleep(2)

        page_num = 1
        while page_num <= 10:  # Max 10 pages
            logger.info(f"Processing page {page_num}...")

            try:
                # Wait for table to load
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//table//tr[@class='table_dark' or @class='table_light']"))
                )
            except:
                logger.info("No more results or table not found")
                break

            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # Find all torrent rows
            rows = soup.find_all('tr', {'class': lambda x: x and ('table_dark' in x or 'table_light' in x)})

            if not rows:
                logger.info("No rows found on this page, stopping")
                break

            logger.info(f"Found {len(rows)} rows on page {page_num}")

            for row in rows:
                try:
                    # Extract torrent info
                    cells = row.find_all('td')
                    if len(cells) < 2:
                        continue

                    # Get title (usually in first cell or second cell)
                    title_elem = row.find('a', {'class': lambda x: x and 'title' in x.lower()})
                    if not title_elem:
                        # Try alternate selector
                        title_elem = cells[1].find('a') if len(cells) > 1 else None

                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)

                    # Get magnet link
                    magnet_elem = row.find('a', {'href': lambda x: x and 'magnet:' in x})
                    if not magnet_elem:
                        continue

                    magnet = magnet_elem.get('href', '')

                    if title and magnet:
                        torrent_info = {
                            'title': title,
                            'magnet': magnet,
                            'page': page_num
                        }
                        self.found_torrents.append(torrent_info)
                        logger.info(f"Found: {title}")

                except Exception as e:
                    logger.debug(f"Error parsing row: {e}")
                    continue

            # Try to go to next page
            try:
                next_button = self.driver.find_element(By.XPATH, "//a[@class='navright' or contains(text(), 'Next')]")
                next_button.click()
                time.sleep(2)
                page_num += 1
            except:
                logger.info("No next page button found, stopping")
                break

        logger.info(f"Total torrents found: {len(self.found_torrents)}")
        return self.found_torrents

    def queue_to_qbittorrent(self):
        """Queue all found torrents to qBittorrent with audiobook category"""
        logger.info(f"\nQueuing {len(self.found_torrents)} torrents to qBittorrent...")

        session = requests.Session()

        # Login to qBittorrent
        login_url = f"{QBITTORRENT_URL}api/v2/auth/login"
        login_data = {'username': QBITTORRENT_USERNAME, 'password': QBITTORRENT_PASSWORD}

        login_response = session.post(login_url, data=login_data, timeout=10)
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

                response = session.post(add_url, data=add_data, timeout=10)

                if response.status_code == 200:
                    logger.info(f"✓ Queued: {torrent['title']}")
                    self.queued_torrents.append(torrent)
                else:
                    logger.warning(f"✗ Failed to queue: {torrent['title']} (HTTP {response.status_code})")

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
            self.init_selenium()

            if not self.login_mam():
                logger.error("Failed to login to MAM")
                return

            self.search_mam('Randi Darren')

            if self.found_torrents:
                self.queue_to_qbittorrent()
            else:
                logger.warning("No torrents found for Randi Darren")

            self.save_results()

        except Exception as e:
            logger.error(f"Error in workflow: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.close()

if __name__ == '__main__':
    searcher = RandiDarrenSearcher()
    searcher.run()
