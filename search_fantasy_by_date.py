#!/usr/bin/env python3
"""
Search MyAnonamouse audiobooks by date range
Find top fantasy audiobooks from the current week
Queue missing ones to qBittorrent
"""

import logging
import os
import time
from pathlib import Path
from typing import List, Dict, Set, Tuple
import re
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from qbittorrent_session_client import QBittorrentSessionClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MAMFantasyByDate:
    def __init__(self):
        self.mam_username = os.getenv('MAM_USERNAME')
        self.mam_password = os.getenv('MAM_PASSWORD')
        self.qb_host = os.getenv('QB_HOST', 'http://localhost')
        self.qb_port = os.getenv('QB_PORT', '52095')
        self.qb_user = os.getenv('QB_USERNAME', 'TopherGutbrod')
        self.qb_pass = os.getenv('QB_PASSWORD', '')
        self.library_path = Path("F:\\Audiobookshelf\\Books")

        self.driver = None
        self.qb_client = None
        self.existing_books = set()

        # Fantasy category ID
        self.fantasy_cat = "41"

    def get_library_titles(self) -> Set[str]:
        """Get all book titles from existing library"""
        titles = set()
        if not self.library_path.exists():
            logger.warning(f"Library path not found: {self.library_path}")
            return titles

        for item in self.library_path.iterdir():
            name = item.name
            cleaned = re.sub(r'^(\d+\s+|\[M4B\]\s+|\[.*?\]\s+)', '', name)
            if item.is_file():
                cleaned = Path(cleaned).stem

            titles.add(cleaned.lower().strip())
            # Also add author/title parts
            parts = cleaned.lower().split('-')
            for part in parts:
                titles.add(part.strip())

        logger.info(f"Found {len(titles)} existing books in library")
        return titles

    def initialize_driver(self) -> bool:
        """Initialize Selenium WebDriver"""
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            logger.info("WebDriver initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            return False

    def login_mam(self) -> bool:
        """Login to MyAnonamouse"""
        try:
            logger.info("Logging into MyAnonamouse...")
            self.driver.get("https://www.myanonamouse.net/login.php")
            wait = WebDriverWait(self.driver, 10)

            # Find and fill login form
            email_field = wait.until(EC.presence_of_element_located((By.NAME, "email")))
            password_field = self.driver.find_element(By.NAME, "password")

            email_field.clear()
            email_field.send_keys(self.mam_username)
            password_field.clear()
            password_field.send_keys(self.mam_password)

            # Submit
            submit_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]")
            submit_btn.click()

            time.sleep(5)
            if "login" not in self.driver.current_url.lower():
                logger.info("✓ Logged into MAM")
                return True
            else:
                logger.error("Login failed")
                return False
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    def search_fantasy_by_date(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Search fantasy audiobooks by date range
        Date format: YYYY-MM-DD
        """
        logger.info(f"\nSearching fantasy audiobooks from {start_date} to {end_date}")

        # Build URL
        base_url = "https://www.myanonamouse.net/tor/browse.php"
        url = (
            f"{base_url}?"
            f"&tor[srchIn][title]=true"
            f"&tor[srchIn][author]=true"
            f"&tor[srchIn][narrator]=true"
            f"&tor[searchType]=all"
            f"&tor[searchIn]=torrents&tor[cat][]=41"  # Fantasy category
            f"&tor[browse_lang][]=1"
            f"&tor[browseFlagsHideVsShow]=0"
            f"&tor[startDate]={start_date}"
            f"&tor[endDate]={end_date}"
            f"&tor[sortType]=snatchedDesc"  # Sort by most snatched (popular)
            f"&tor[startNumber]=0"
            f"&thumbnail=true"
        )

        logger.info(f"URL: {url}")

        try:
            self.driver.get(url)
            time.sleep(3)

            # Extract results from table
            results = []
            wait = WebDriverWait(self.driver, 10)

            # Find all torrent rows
            torrent_rows = wait.until(
                EC.presence_of_all_elements_located((By.XPATH, "//table[@class='table']//tr[@class='torrent']"))
            )

            logger.info(f"Found {len(torrent_rows)} results")

            for idx, row in enumerate(torrent_rows[:10]):  # Get top 10
                try:
                    # Get title and link
                    title_elem = row.find_element(By.XPATH, ".//a[contains(@href, '/tor/')]")
                    title = title_elem.text.strip()
                    link = title_elem.get_attribute('href')

                    # Get upload date (look in table cells)
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    upload_date = "Unknown"

                    # Date is typically in one of the later columns
                    for cell in cells:
                        cell_text = cell.text.strip()
                        # Look for date pattern YYYY-MM-DD or similar
                        if re.match(r'\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}', cell_text):
                            upload_date = cell_text
                            break

                    results.append({
                        'title': title,
                        'link': link,
                        'upload_date': upload_date,
                        'position': idx + 1
                    })

                    logger.info(f"[{idx+1}] {title}")
                    logger.info(f"    Date: {upload_date}")
                    logger.info(f"    Link: {link}")

                except Exception as e:
                    logger.warning(f"Error extracting result {idx}: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    def is_book_in_library(self, title: str) -> bool:
        """Check if book is likely in library"""
        title_lower = title.lower()
        matches = 0

        for lib_title in self.existing_books:
            if len(lib_title) > 3 and lib_title in title_lower:
                matches += 1

        return matches >= 2

    def get_magnet_link(self, torrent_url: str) -> str:
        """Navigate to torrent page and extract magnet link"""
        try:
            self.driver.get(torrent_url)
            time.sleep(2)

            # Find magnet link
            magnet_elem = self.driver.find_element(By.XPATH, "//a[contains(@href, 'magnet:')]")
            magnet_link = magnet_elem.get_attribute('href')

            return magnet_link
        except Exception as e:
            logger.warning(f"Could not get magnet link: {e}")
            return None

    def run(self):
        """Main execution"""
        logger.info("="*80)
        logger.info("FANTASY AUDIOBOOKS - WEEKLY DATE RANGE SEARCH")
        logger.info("="*80)

        try:
            # Calculate date range for this week
            today = datetime.now()
            start_of_week = today - timedelta(days=today.weekday())  # Monday
            end_of_week = start_of_week + timedelta(days=6)  # Sunday

            start_date = start_of_week.strftime("%Y-%m-%d")
            end_date = end_of_week.strftime("%Y-%m-%d")

            logger.info(f"\nSearch period: {start_date} to {end_date}")

            # Step 1: Get library
            logger.info("\nStep 1: Scanning library...")
            self.existing_books = self.get_library_titles()

            # Step 2: Initialize driver
            logger.info("\nStep 2: Initializing browser...")
            if not self.initialize_driver():
                return

            # Step 3: Login
            logger.info("\nStep 3: Logging into MAM...")
            if not self.login_mam():
                return

            # Step 4: Search
            logger.info("\nStep 4: Searching fantasy audiobooks...")
            results = self.search_fantasy_by_date(start_date, end_date)

            if not results:
                logger.warning("No results found for this week")
                return

            # Step 5: Compare with library
            logger.info("\n" + "="*80)
            logger.info("COMPARISON: Library vs Search Results")
            logger.info("="*80)

            missing_books = []
            for book in results:
                in_lib = self.is_book_in_library(book['title'])
                status = "✓ IN LIBRARY" if in_lib else "✗ MISSING"
                logger.info(f"[{book['position']}] {status}: {book['title']}")
                logger.info(f"         Date: {book['upload_date']}")

                if not in_lib:
                    missing_books.append(book)

            logger.info(f"\nMissing: {len(missing_books)}/{len(results)}")

            if not missing_books:
                logger.info("✓ All results already in library!")
                return

            # Step 6: Queue to qBittorrent
            logger.info(f"\nStep 5: Queuing {len(missing_books)} missing books...")

            qb_url = f"{self.qb_host}:{self.qb_port}"
            self.qb_client = QBittorrentSessionClient(
                host=qb_url,
                username=self.qb_user,
                password=self.qb_pass
            )

            if not self.qb_client.login():
                logger.error("Failed to connect to qBittorrent")
                return

            queued_count = 0
            for book in missing_books:
                magnet = self.get_magnet_link(book['link'])

                if magnet:
                    success = self.qb_client.torrents_add(
                        urls=magnet,
                        category="audiobooks",
                        tags=["fantasy", "weekly-top"],
                        is_paused=False
                    )

                    if success:
                        logger.info(f"✓ Queued: {book['title']}")
                        queued_count += 1
                    else:
                        logger.warning(f"✗ Failed to queue: {book['title']}")
                else:
                    logger.warning(f"✗ No magnet for: {book['title']}")

                time.sleep(2)

            logger.info("\n" + "="*80)
            logger.info(f"COMPLETE: {queued_count}/{len(missing_books)} books queued")
            logger.info("="*80)

        except Exception as e:
            logger.error(f"Fatal error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            if self.driver:
                logger.info("Closing browser...")
                self.driver.quit()


if __name__ == "__main__":
    finder = MAMFantasyByDate()
    finder.run()
