#!/usr/bin/env python3
"""
Find top 10 fantasy audiobooks for the week on MAM
Cross-reference with existing library
Search and queue missing audiobooks to qBittorrent
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
from qbittorrent_session_client import QBittorrentSessionClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FantasyAudiobookFinder:
    def __init__(self):
        self.mam_username = os.getenv('MAM_USERNAME')
        self.mam_password = os.getenv('MAM_PASSWORD')
        self.qb_url = os.getenv('QB_HOST', 'http://localhost')
        self.qb_port = os.getenv('QB_PORT', '52095')
        self.qb_user = os.getenv('QB_USERNAME', 'TopherGutbrod')
        self.qb_pass = os.getenv('QB_PASSWORD', '')
        self.library_path = Path("F:\\Audiobookshelf\\Books")

        self.driver = None
        self.qb_client = None
        self.existing_books = set()
        self.top_fantasy_books = []
        self.missing_books = []

    def get_existing_library_titles(self) -> Set[str]:
        """Get all book titles/authors from the existing library"""
        titles = set()
        if not self.library_path.exists():
            logger.warning(f"Library path not found: {self.library_path}")
            return titles

        for item in self.library_path.iterdir():
            # Get the directory name or file name (without extension)
            name = item.name
            # Remove common prefixes like "01 ", "[M4B] ", etc.
            cleaned = re.sub(r'^(\d+\s+|\[M4B\]\s+|\[.*?\]\s+)', '', name)
            # Remove file extensions
            cleaned = Path(cleaned).stem if item.is_file() else cleaned
            titles.add(cleaned.lower().strip())

        logger.info(f"Found {len(titles)} existing books in library")
        return titles

    def initialize_webdriver(self):
        """Initialize Selenium WebDriver"""
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            logger.info("Selenium WebDriver initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            return False

    def login_mam(self) -> bool:
        """Login to MyAnonamouse"""
        try:
            logger.info("Logging into MyAnonamouse...")
            self.driver.get("https://www.myanonamouse.net/login.php")

            # Wait for login form
            wait = WebDriverWait(self.driver, 10)

            # Try different login form selectors
            try:
                email_field = wait.until(EC.presence_of_element_located((By.NAME, "email")))
                password_field = self.driver.find_element(By.NAME, "password")
            except:
                # Try alternative selectors
                email_field = wait.until(EC.presence_of_element_located((By.ID, "email")))
                password_field = self.driver.find_element(By.ID, "password")

            # Fill in credentials
            email_field.clear()
            email_field.send_keys(self.mam_username)
            password_field.clear()
            password_field.send_keys(self.mam_password)

            # Submit - try different button selectors
            try:
                submit_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]")
            except:
                submit_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'login')]")

            submit_btn.click()

            # Wait for redirect
            time.sleep(5)
            if "login" not in self.driver.current_url.lower():
                logger.info("Successfully logged into MAM")
                return True
            else:
                logger.error("Login failed - still on login page")
                return False
        except Exception as e:
            logger.error(f"Login error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_top_fantasy_for_week(self) -> List[Dict]:
        """Navigate to fantasy section and get top 10 books for the week"""
        try:
            logger.info("Navigating to fantasy section...")
            # Navigate to the audio section with sorting
            self.driver.get("https://www.myanonamouse.net/tor/browse.php?cat=4&sort=seeders&order=DESC&time=7")

            time.sleep(3)

            # Extract torrent table data
            books = []
            wait = WebDriverWait(self.driver, 10)

            # Wait for table to load
            table_rows = wait.until(
                EC.presence_of_all_elements_located((By.XPATH, "//table[@class='table']//tr[@class='torrent']"))
            )

            logger.info(f"Found {len(table_rows)} torrents in fantasy section")

            for idx, row in enumerate(table_rows[:10]):  # Get top 10
                try:
                    # Get title link
                    title_elem = row.find_element(By.XPATH, ".//a[contains(@href, '/tor/')]")
                    title = title_elem.text.strip()
                    torrent_url = title_elem.get_attribute('href')

                    # Get seeders
                    seeders_elem = row.find_elements(By.TAG_NAME, 'td')
                    seeders = "N/A"
                    if len(seeders_elem) > 5:
                        seeders = seeders_elem[5].text.strip()

                    # Get size
                    size = "N/A"
                    if len(seeders_elem) > 4:
                        size = seeders_elem[4].text.strip()

                    books.append({
                        'title': title,
                        'url': torrent_url,
                        'seeders': seeders,
                        'size': size,
                        'position': idx + 1
                    })

                    logger.info(f"[{idx+1}] {title} ({seeders} seeders, {size})")
                except Exception as e:
                    logger.warning(f"Error extracting book {idx}: {e}")
                    continue

            return books
        except Exception as e:
            logger.error(f"Error getting fantasy books: {e}")
            return []

    def find_missing_books(self, top_books: List[Dict]) -> List[Dict]:
        """Compare top books with library and find missing ones"""
        missing = []

        logger.info("\n" + "="*80)
        logger.info("COMPARISON: Library vs Top 10 Fantasy Audiobooks")
        logger.info("="*80)

        for book in top_books:
            title_lower = book['title'].lower()
            # Simple check: see if any part of the title is in existing library
            is_in_library = any(
                book_part in title_lower for book_part in self.existing_books
            ) or any(
                book_part in title_lower.lower() for book_part in self.existing_books
            )

            status = "✓ IN LIBRARY" if is_in_library else "✗ MISSING"
            logger.info(f"[{book['position']}] {status}: {book['title']} ({book['seeders']} seeders)")

            if not is_in_library:
                missing.append(book)

        logger.info(f"\nTotal missing: {len(missing)}/{len(top_books)}")
        return missing

    def search_and_get_magnet(self, book_title: str) -> str:
        """Search for a book on MAM and get the magnet link"""
        try:
            logger.info(f"Searching for: {book_title}")

            # Go to search page
            search_url = f"https://www.myanonamouse.net/tor/search.php?q={book_title.replace(' ', '+')}&cat=4&sort=seeders&order=DESC"
            self.driver.get(search_url)

            time.sleep(2)

            # Get first result
            wait = WebDriverWait(self.driver, 5)
            try:
                first_result = wait.until(
                    EC.presence_of_element_located((By.XPATH, "//table[@class='table']//tr[@class='torrent']//a[contains(@href, '/tor/')]"))
                )
                magnet_url = first_result.get_attribute('href')

                # Navigate to torrent page to get magnet link
                self.driver.get(magnet_url)
                time.sleep(1)

                # Look for magnet link
                magnet_elem = self.driver.find_element(By.XPATH, "//a[contains(@href, 'magnet:')]")
                magnet_link = magnet_elem.get_attribute('href')

                logger.info(f"Found magnet for: {book_title}")
                return magnet_link
            except:
                logger.warning(f"Could not find magnet for: {book_title}")
                return None
        except Exception as e:
            logger.error(f"Search error for {book_title}: {e}")
            return None

    def queue_to_qbittorrent(self, book_title: str, magnet_link: str) -> bool:
        """Add magnet link to qBittorrent"""
        try:
            if not magnet_link:
                logger.warning(f"No magnet link for {book_title}")
                return False

            # Construct full qB URL
            qb_full_url = f"{self.qb_url}:{self.qb_port}"

            success = self.qb_client.torrents_add(
                urls=magnet_link,
                category="audiobooks",
                tags=["fantasy", "auto-added"],
                is_paused=False
            )

            if success:
                logger.info(f"✓ Queued to qBittorrent: {book_title}")
            else:
                logger.warning(f"✗ Failed to queue: {book_title}")

            return success
        except Exception as e:
            logger.error(f"Error queuing {book_title}: {e}")
            return False

    def run(self):
        """Main execution"""
        logger.info("="*80)
        logger.info("FANTASY AUDIOBOOK FINDER - WEEK TOP 10")
        logger.info("="*80)

        try:
            # Get existing library
            logger.info("\nStep 1: Scanning existing library...")
            self.existing_books = self.get_existing_library_titles()

            # Initialize WebDriver
            logger.info("\nStep 2: Initializing browser...")
            if not self.initialize_webdriver():
                return

            # Login to MAM
            logger.info("\nStep 3: Authenticating to MAM...")
            if not self.login_mam():
                return

            # Get top fantasy books for the week
            logger.info("\nStep 4: Fetching top 10 fantasy audiobooks...")
            self.top_fantasy_books = self.get_top_fantasy_for_week()

            if not self.top_fantasy_books:
                logger.error("Failed to get fantasy books")
                return

            # Find missing books
            logger.info("\nStep 5: Comparing with library...")
            self.missing_books = self.find_missing_books(self.top_fantasy_books)

            if not self.missing_books:
                logger.info("✓ All top 10 fantasy books are already in your library!")
                return

            # Initialize qBittorrent client
            logger.info("\nStep 6: Initializing qBittorrent...")
            qb_full_url = f"{self.qb_url}:{self.qb_port}"
            self.qb_client = QBittorrentSessionClient(
                host=qb_full_url,
                username=self.qb_user,
                password=self.qb_pass
            )

            if not self.qb_client.login():
                logger.error("Failed to connect to qBittorrent")
                return

            # Search and queue missing books
            logger.info(f"\nStep 7: Searching and queuing {len(self.missing_books)} missing books...")
            queued_count = 0

            for book in self.missing_books:
                magnet = self.search_and_get_magnet(book['title'])
                if magnet:
                    if self.queue_to_qbittorrent(book['title'], magnet):
                        queued_count += 1
                    time.sleep(2)  # Rate limiting

            logger.info("\n" + "="*80)
            logger.info(f"SUMMARY: {queued_count}/{len(self.missing_books)} books queued to qBittorrent")
            logger.info("="*80)

        except Exception as e:
            logger.error(f"Fatal error: {e}")

        finally:
            if self.driver:
                logger.info("Closing browser...")
                self.driver.quit()


if __name__ == "__main__":
    finder = FantasyAudiobookFinder()
    finder.run()
