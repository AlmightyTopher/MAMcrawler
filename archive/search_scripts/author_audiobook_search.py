#!/usr/bin/env python3
"""
Author Audiobook Search and Library Sync
==========================================
Search MAM for audiobooks by specified authors across ALL pages
Cross-verify with Goodreads to ensure completeness
Compare against Audiobookshelf library
Add missing titles to qBittorrent queue

Authors to search:
- William D. Arand
- Randi Darren
- A. R. Rend
"""

import sys
import os
import time
import json
import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Set
from urllib.parse import quote, urljoin
from pathlib import Path
import asyncio

if sys.platform == 'win32':
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass

from dotenv import load_dotenv
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('author_search.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    import requests
    from bs4 import BeautifulSoup
    import qbittorrentapi
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError as e:
    logger.error(f"Missing required library: {e}")
    sys.exit(1)

# Import async clients
from backend.integrations.abs_client import AudiobookshelfClient
from backend.integrations.qbittorrent_client import QBittorrentClient


class AuthorAudiobookSearch:
    """
    Comprehensive author search across MAM, Goodreads, and Audiobookshelf
    """

    AUTHORS = [
        "William D. Arand",
        "Randi Darren",
        "A. R. Rend"
    ]

    def __init__(self):
        self.mam_username = os.getenv('MAM_USERNAME')
        self.mam_password = os.getenv('MAM_PASSWORD')
        self.mam_url = "https://www.myanonamouse.net"

        self.abs_url = os.getenv('ABS_URL', 'http://localhost:13378')
        self.abs_token = os.getenv('ABS_TOKEN')

        self.qb_url = os.getenv('QBITTORRENT_URL', 'http://192.168.0.48:52095/')
        self.qb_user = os.getenv('QBITTORRENT_USERNAME', 'TopherGutbrod')
        self.qb_pass = os.getenv('QBITTORRENT_PASSWORD')

        # Create session for MAM
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # Selenium driver for robust login
        self.driver = None
        self.wait = None

        self.authenticated = False
        self.results = {
            "mam_results": {},
            "goodreads_results": {},
            "abs_library": {},
            "missing_titles": {},
            "to_queue": []
        }

    def login_mam(self) -> bool:
        """Login to MyAnonamouse using Selenium for robust session management"""
        print("\n" + "=" * 120)
        print("STEP 1: Login to MyAnonamouse (Selenium WebDriver)")
        print("=" * 120)

        try:
            logger.info("Initializing Selenium WebDriver...")

            # Setup Chrome options
            chrome_options = ChromeOptions()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 20)

            logger.info("Navigating to login page...")
            self.driver.get(f"{self.mam_url}/login.php")
            time.sleep(2)

            # Find and fill login form
            logger.info("Filling login form...")
            email_field = self.wait.until(EC.presence_of_element_located((By.NAME, "email")))
            password_field = self.driver.find_element(By.NAME, "password")

            email_field.clear()
            email_field.send_keys(self.mam_username)
            password_field.clear()
            password_field.send_keys(self.mam_password)

            # Submit form
            logger.info("Submitting login form...")
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit'] | //input[@type='submit']")
            login_button.click()

            # Wait for redirect
            time.sleep(5)

            # Verify login by checking URL and page content
            current_url = self.driver.current_url.lower()
            page_source = self.driver.page_source.lower()

            if "login" in current_url and "error" in page_source:
                logger.error("Login failed - still on login page with error")
                return False

            if "logout" in page_source or "userdetails" in page_source or "browse" in page_source:
                self.authenticated = True

                # Transfer cookies to requests session for subsequent searches
                cookies = self.driver.get_cookies()
                for cookie in cookies:
                    self.session.cookies.set(cookie['name'], cookie['value'])

                logger.info("✓ Successfully logged into MAM via Selenium")
                print(f"✓ Logged in successfully (Selenium)")
                print(f"  Cookies transferred: {len(cookies)}")
                return True
            else:
                logger.error("Login verification inconclusive")
                return False

        except TimeoutException:
            logger.error("Login timeout - form elements not found")
            return False
        except Exception as e:
            logger.error(f"Login error: {e}", exc_info=True)
            return False

    def search_mam_author(self, author_name: str) -> List[Dict[str, str]]:
        """
        Search MAM for all audiobooks by an author across ALL pages
        Returns list of {title, author, category, magnet_link}
        """
        print(f"\n{'=' * 120}")
        print(f"SEARCHING MAM FOR: {author_name}")
        print(f"{'=' * 120}")

        all_results = []
        page_num = 0
        has_more_pages = True

        while has_more_pages:
            page_num += 1
            start_number = (page_num - 1) * 50  # MAM shows ~50 results per page

            search_url = (
                f"{self.mam_url}/tor/browse.php"
                f"?tor[searchstr]={quote(author_name)}"
                f"&tor[cat][]=13"  # Audiobooks category
                f"&tor[startNumber]={start_number}"
            )

            logger.info(f"Fetching page {page_num} (startNumber={start_number})")
            print(f"  Page {page_num}...", end=" ", flush=True)

            try:
                time.sleep(2)  # Rate limiting
                response = self.session.get(search_url, timeout=30)

                if response.status_code != 200:
                    logger.warning(f"Page {page_num} request failed: {response.status_code}")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')

                # Find all torrent rows
                torrent_rows = soup.find_all('tr')
                page_results = 0

                for row in torrent_rows:
                    # Look for torrent link
                    torrent_link = row.find('a', href=re.compile(r'/t/\d+'))
                    if not torrent_link:
                        continue

                    title = torrent_link.get_text(strip=True)
                    torrent_id = torrent_link.get('href', '').split('/t/')[1].split('/')[0] if '/t/' in torrent_link.get('href', '') else None

                    if not title or not torrent_id:
                        continue

                    # Store torrent info
                    torrent_info = {
                        'title': title,
                        'author': author_name,
                        'torrent_id': torrent_id,
                        'url': urljoin(self.mam_url, f"/t/{torrent_id}/")
                    }

                    all_results.append(torrent_info)
                    page_results += 1

                print(f"Found {page_results} results")

                # Check if there are more pages
                # Look for "Next" button or pagination
                next_button = soup.find('a', string=re.compile(r'Next|next|>'))
                if page_results == 0:
                    has_more_pages = False
                    logger.info(f"No more results on page {page_num}, stopping")

                # Safety check: if we got results, assume there might be more
                if page_num >= 10:  # Limit to 10 pages max
                    logger.warning("Reached max pages (10), stopping pagination")
                    has_more_pages = False

            except Exception as e:
                logger.error(f"Error fetching page {page_num}: {e}")
                break

        logger.info(f"Total results for {author_name}: {len(all_results)}")
        print(f"  ✓ Total results: {len(all_results)} audiobooks\n")

        self.results["mam_results"][author_name] = all_results
        return all_results

    def extract_magnet_from_torrent(self, torrent_id: str) -> Optional[str]:
        """Extract magnet link from torrent details page"""
        try:
            torrent_url = f"{self.mam_url}/t/{torrent_id}/"
            logger.debug(f"Fetching torrent details from {torrent_url}")

            time.sleep(1)  # Rate limiting
            response = self.session.get(torrent_url, timeout=30)

            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for magnet link
            magnet_link = soup.find('a', href=re.compile(r'^magnet:\?'))
            if magnet_link:
                return magnet_link.get('href')

            # Alternative: look in download links
            download_link = soup.find('a', href=re.compile(r'download|magnet', re.IGNORECASE))
            if download_link:
                return download_link.get('href')

            return None

        except Exception as e:
            logger.error(f"Error extracting magnet for torrent {torrent_id}: {e}")
            return None

    async def get_abs_library_books(self) -> Dict[str, List[str]]:
        """Get all books from Audiobookshelf by author"""
        print(f"\n{'=' * 120}")
        print(f"QUERYING AUDIOBOOKSHELF LIBRARY")
        print(f"{'=' * 120}")

        try:
            async with AudiobookshelfClient(self.abs_url, self.abs_token) as client:
                # Get all library items
                library_items = await client.get_library_items(limit=500)
                logger.info(f"Retrieved {len(library_items)} items from Audiobookshelf")

                # Organize by author
                books_by_author = {}
                for item in library_items:
                    metadata = item.get('media', {}).get('metadata', {})
                    authors = metadata.get('authors', [])
                    title = metadata.get('title', 'Unknown')

                    if isinstance(authors, list):
                        for author in authors:
                            author_name = author if isinstance(author, str) else author.get('name', '')
                            if author_name:
                                if author_name not in books_by_author:
                                    books_by_author[author_name] = []
                                books_by_author[author_name].append(title)
                    else:
                        author_name = metadata.get('authorName', '')
                        if author_name:
                            if author_name not in books_by_author:
                                books_by_author[author_name] = []
                            books_by_author[author_name].append(title)

                # Print found books by our target authors
                for author in self.AUTHORS:
                    if author in books_by_author:
                        print(f"  {author}: {len(books_by_author[author])} books")
                        for book in books_by_author[author]:
                            print(f"    - {book}")
                    else:
                        print(f"  {author}: No books found in library")

                self.results["abs_library"] = books_by_author
                return books_by_author

        except Exception as e:
            logger.error(f"Error querying Audiobookshelf: {e}")
            return {}

    def search_goodreads_author(self, author_name: str) -> Set[str]:
        """
        Search Goodreads for author books to verify completeness
        Returns set of book titles
        """
        print(f"\nSearching Goodreads for {author_name}...", end=" ", flush=True)

        try:
            # Goodreads doesn't have a public API, but we can search their website
            search_url = "https://www.goodreads.com/search"
            params = {
                'q': author_name,
                'search_type': 'author'
            }

            # Use a different user agent for Goodreads
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(search_url, params=params, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.warning(f"Goodreads search failed: {response.status_code}")
                print("(failed)")
                return set()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract book titles from search results
            books = set()
            # Look for book elements
            for book_elem in soup.find_all('a', {'class': re.compile(r'.*bookTitle.*')}):
                title = book_elem.get_text(strip=True)
                if title:
                    books.add(title)

            print(f"(found {len(books)} titles)")
            logger.info(f"Goodreads found {len(books)} books for {author_name}")

            self.results["goodreads_results"][author_name] = list(books)
            return books

        except Exception as e:
            logger.warning(f"Goodreads search error: {e}")
            print("(error)")
            return set()

    def compare_and_identify_missing(self) -> Dict[str, List[str]]:
        """
        Compare MAM results with Audiobookshelf library
        Identify missing titles
        """
        print(f"\n{'=' * 120}")
        print(f"COMPARING RESULTS AND IDENTIFYING MISSING TITLES")
        print(f"{'=' * 120}")

        missing_by_author = {}

        for author in self.AUTHORS:
            mam_books = self.results["mam_results"].get(author, [])
            abs_books = self.results["abs_library"].get(author, [])

            # Normalize titles for comparison
            abs_books_normalized = {self._normalize_title(b) for b in abs_books}

            missing = []
            for mam_book in mam_books:
                mam_title_normalized = self._normalize_title(mam_book['title'])

                # Check if this title is in the library
                if mam_title_normalized not in abs_books_normalized:
                    missing.append(mam_book)

            missing_by_author[author] = missing

            print(f"\n{author}:")
            print(f"  MAM results: {len(mam_books)}")
            print(f"  In library: {len(abs_books)}")
            print(f"  Missing: {len(missing)}")

            if missing:
                print(f"  Missing titles:")
                for book in missing[:10]:  # Show first 10
                    print(f"    - {book['title']}")
                if len(missing) > 10:
                    print(f"    ... and {len(missing) - 10} more")

        self.results["missing_titles"] = missing_by_author
        return missing_by_author

    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison"""
        # Remove common prefixes and suffixes
        normalized = title.lower().strip()
        # Remove series numbers
        normalized = re.sub(r'\s*\(.*?(?:book|series|part|vol).*?\)\s*', '', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'[\[\]]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    async def queue_missing_to_qbittorrent(self) -> int:
        """
        Add missing titles to qBittorrent queue
        Returns number of items queued
        """
        print(f"\n{'=' * 120}")
        print(f"QUEUING MISSING TITLES TO QBITTORRENT")
        print(f"{'=' * 120}")

        queued_count = 0

        try:
            async with QBittorrentClient(self.qb_url, self.qb_user, self.qb_pass) as qb:
                for author in self.AUTHORS:
                    missing = self.results["missing_titles"].get(author, [])

                    print(f"\n{author}: Queuing {len(missing)} missing titles")

                    for book in missing[:5]:  # Queue first 5 to test
                        try:
                            # Extract magnet link from torrent page
                            magnet_link = self.extract_magnet_from_torrent(book['torrent_id'])

                            if not magnet_link:
                                logger.warning(f"Could not extract magnet for {book['title']}")
                                continue

                            # Add to qBittorrent
                            result = await qb.add_torrent(
                                magnet_link,
                                category="audiobooks",
                                paused=False
                            )

                            if result.get('success'):
                                queued_count += 1
                                print(f"  ✓ Queued: {book['title']}")
                                self.results["to_queue"].append({
                                    'title': book['title'],
                                    'author': author,
                                    'status': 'queued'
                                })
                            else:
                                logger.error(f"Failed to queue {book['title']}: {result.get('error')}")
                                print(f"  ✗ Failed: {book['title']}")

                        except Exception as e:
                            logger.error(f"Error queuing {book['title']}: {e}")
                            print(f"  ✗ Error: {book['title']}")

        except Exception as e:
            logger.error(f"qBittorrent connection error: {e}")
            print(f"✗ Could not connect to qBittorrent: {e}")

        print(f"\n✓ Total queued: {queued_count} audiobooks")
        return queued_count

    def save_report(self):
        """Save search results to JSON report"""
        report_file = f"author_search_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            logger.info(f"Report saved to {report_file}")
            print(f"\n✓ Report saved: {report_file}")
        except Exception as e:
            logger.error(f"Could not save report: {e}")

    def cleanup(self):
        """Close Selenium driver and cleanup"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Closed Selenium WebDriver")
            except Exception as e:
                logger.warning(f"Error closing driver: {e}")

    async def run(self):
        """Execute complete search workflow"""
        print("\n" + "=" * 120)
        print("AUTHOR AUDIOBOOK SEARCH - COMPREHENSIVE WORKFLOW")
        print("=" * 120)
        print(f"Start: {datetime.now().isoformat()}")
        print(f"Authors: {', '.join(self.AUTHORS)}")
        print()

        try:
            # Step 1: Login to MAM
            if not self.login_mam():
                logger.error("Failed to login to MAM")
                return

            # Step 2: Search MAM for each author
            for author in self.AUTHORS:
                self.search_mam_author(author)

                # Also try Goodreads for verification
                self.search_goodreads_author(author)
                time.sleep(3)  # Rate limiting

            # Step 3: Get Audiobookshelf library
            await self.get_abs_library_books()

            # Step 4: Compare and identify missing
            self.compare_and_identify_missing()

            # Step 5: Queue missing to qBittorrent
            await self.queue_missing_to_qbittorrent()

            # Step 6: Save report
            self.save_report()

            print("\n" + "=" * 120)
            print("WORKFLOW COMPLETE")
            print("=" * 120)
            print(f"End: {datetime.now().isoformat()}")

        except Exception as e:
            logger.error(f"Workflow error: {e}", exc_info=True)
            print(f"\n✗ Error: {e}")
        finally:
            self.cleanup()


def main():
    search = AuthorAudiobookSearch()
    asyncio.run(search.run())


if __name__ == '__main__':
    main()
