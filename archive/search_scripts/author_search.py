#!/usr/bin/env python3
"""
Unified Author Audiobook Search Tool
=====================================
Search MAM for audiobooks by specified authors with multiple modes:
- basic: Simple search without authentication
- auth: Authenticated search with MAM_ID cookie (default, recommended)
- webdriver: Full Selenium WebDriver with login automation

Cross-verify with Goodreads, compare against Audiobookshelf library,
and add missing titles to qBittorrent queue.

Usage:
    python author_search.py --mode=basic
    python author_search.py --mode=auth          # Default
    python author_search.py --mode=webdriver
    python author_search.py --mode=auth --authors="Author Name" --skip-queue
"""

import sys
import os
import time
import json
import logging
import re
import argparse
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

try:
    import requests
    from bs4 import BeautifulSoup
    import qbittorrentapi
except ImportError as e:
    print(f"ERROR: Missing required library: {e}")
    print("Install dependencies: pip install requests beautifulsoup4 qbittorrentapi")
    sys.exit(1)

# Optional Selenium imports (only needed for webdriver mode)
SELENIUM_AVAILABLE = True
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    SELENIUM_AVAILABLE = False

# Import async clients
try:
    from backend.integrations.abs_client import AudiobookshelfClient
    from backend.integrations.qbittorrent_client import QBittorrentClient
except ImportError as e:
    print(f"ERROR: Missing backend integration: {e}")
    print("Ensure backend/integrations modules are available")
    sys.exit(1)


class UnifiedAuthorSearch:
    """
    Unified author search supporting multiple authentication modes
    """

    DEFAULT_AUTHORS = [
        "William D. Arand",
        "Randi Darren",
        "A. R. Rend"
    ]

    def __init__(self, mode: str = "auth", authors: List[str] = None, headless: bool = True):
        """
        Initialize search with specified mode

        Args:
            mode: Search mode ('basic', 'auth', 'webdriver')
            authors: List of author names to search (default: DEFAULT_AUTHORS)
            headless: Run browser in headless mode (webdriver mode only)
        """
        self.mode = mode
        self.authors = authors or self.DEFAULT_AUTHORS
        self.headless = headless

        # Setup logging
        log_file = f'author_search_{mode}.log'
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        # Configuration
        self.mam_url = "https://www.myanonamouse.net"
        self.mam_username = os.getenv('MAM_USERNAME')
        self.mam_password = os.getenv('MAM_PASSWORD')
        self.mam_id = os.getenv('MAM_ID')

        self.abs_url = os.getenv('ABS_URL', 'http://localhost:13378')
        self.abs_token = os.getenv('ABS_TOKEN')

        self.qb_url = os.getenv('QBITTORRENT_URL', 'http://192.168.0.48:52095/')
        self.qb_user = os.getenv('QBITTORRENT_USERNAME', 'TopherGutbrod')
        self.qb_pass = os.getenv('QBITTORRENT_PASSWORD')

        self.gr_email = os.getenv('GOODREADS_EMAIL', os.getenv('GOODREADS_USERNAME'))
        self.gr_password = os.getenv('GOODREADS_PASSWORD')

        # Session for HTTP requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # Selenium driver (only for webdriver mode)
        self.driver = None
        self.wait = None

        # Results storage
        self.results = {
            "mode": mode,
            "mam_results": {},
            "goodreads_results": {},
            "abs_library": {},
            "missing_titles": {},
            "queued": []
        }

    def init_selenium(self) -> bool:
        """Initialize Selenium WebDriver (webdriver mode only)"""
        if self.mode != "webdriver":
            return False

        if not SELENIUM_AVAILABLE:
            self.logger.error("Selenium not installed. Install: pip install selenium webdriver-manager")
            return False

        try:
            chrome_options = ChromeOptions()
            if self.headless:
                chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 20)

            self.logger.info("Selenium WebDriver initialized")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize Selenium: {e}")
            return False

    def cleanup(self):
        """Close Selenium driver if active"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Selenium driver closed")
            except:
                pass

    def login_mam_basic(self) -> bool:
        """Basic mode: No authentication (public access only)"""
        self.logger.info("Running in BASIC mode (no authentication)")
        print("\nMode: BASIC (Public access only)")
        return True

    def login_mam_auth(self) -> bool:
        """Auth mode: Use MAM_ID cookie for authentication"""
        print("\n" + "=" * 120)
        print("AUTHENTICATING WITH MAM (Cookie-based)")
        print("=" * 120)

        if not self.mam_id:
            self.logger.warning("MAM_ID not found in environment")
            print("WARNING: MAM_ID not set. Set MAM_ID environment variable for authenticated access.")
            print("Proceeding with unauthenticated search (limited results)")
            return False

        try:
            self.session.cookies.set('mam_id', self.mam_id, domain='www.myanonamouse.net', path='/')
            self.logger.info("MAM_ID cookie set successfully")
            print("Authenticated with MAM_ID cookie")
            return True
        except Exception as e:
            self.logger.error(f"MAM authentication error: {e}")
            return False

    def login_mam_webdriver(self) -> bool:
        """WebDriver mode: Full Selenium login automation"""
        print("\n" + "=" * 120)
        print("AUTHENTICATING WITH MAM (Selenium WebDriver)")
        print("=" * 120)

        if not self.driver:
            if not self.init_selenium():
                return False

        try:
            self.logger.info("Navigating to login page...")
            self.driver.get(f"{self.mam_url}/login.php")
            time.sleep(2)

            # Fill login form
            self.logger.info("Filling login form...")
            email_field = self.wait.until(EC.presence_of_element_located((By.NAME, "email")))
            password_field = self.driver.find_element(By.NAME, "password")

            email_field.clear()
            email_field.send_keys(self.mam_username)
            password_field.clear()
            password_field.send_keys(self.mam_password)

            # Submit
            self.logger.info("Submitting login...")
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit'] | //input[@type='submit']")
            login_button.click()
            time.sleep(5)

            # Verify login
            page_source = self.driver.page_source.lower()
            if "logout" in page_source or "userdetails" in page_source:
                # Transfer cookies to requests session
                cookies = self.driver.get_cookies()
                for cookie in cookies:
                    self.session.cookies.set(cookie['name'], cookie['value'])

                self.logger.info("Successfully logged in via Selenium")
                print(f"Logged in successfully (Selenium)")
                print(f"Cookies transferred: {len(cookies)}")
                return True
            else:
                self.logger.error("Login verification failed")
                return False

        except Exception as e:
            self.logger.error(f"WebDriver login error: {e}", exc_info=True)
            return False

    def authenticate(self) -> bool:
        """Authenticate based on selected mode"""
        if self.mode == "basic":
            return self.login_mam_basic()
        elif self.mode == "auth":
            return self.login_mam_auth()
        elif self.mode == "webdriver":
            return self.login_mam_webdriver()
        else:
            self.logger.error(f"Unknown mode: {self.mode}")
            return False

    def search_mam_by_author(self, author_name: str) -> List[Dict[str, Any]]:
        """
        Search MAM for all audiobooks by an author across ALL pages
        Works in all modes (basic, auth, webdriver)
        """
        print(f"\n{'=' * 120}")
        print(f"SEARCHING MAM FOR: {author_name}")
        print(f"{'=' * 120}")

        all_results = []
        page_num = 0
        has_more = True

        while has_more:
            page_num += 1
            start_number = (page_num - 1) * 50

            search_url = (
                f"{self.mam_url}/tor/browse.php"
                f"?tor[searchstr]={quote(author_name)}"
                f"&tor[cat][]=13"  # Audiobooks
                f"&tor[searchType]=all"
                f"&tor[searchIn]=torrents"
                f"&tor[startNumber]={start_number}"
            )

            self.logger.info(f"Fetching page {page_num} (startNumber={start_number})")
            print(f"  Page {page_num}...", end=" ", flush=True)

            try:
                time.sleep(3)  # Rate limiting
                response = self.session.get(search_url, timeout=30)

                if response.status_code != 200:
                    self.logger.warning(f"Page {page_num} failed: {response.status_code}")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')
                page_results = 0

                # Find all torrent entries
                rows = soup.find_all('tr')
                for row in rows:
                    torrent_link = row.find('a', href=re.compile(r'/t/\d+'))
                    if not torrent_link:
                        continue

                    title = torrent_link.get_text(strip=True)
                    torrent_id_match = re.search(r'/t/(\d+)', torrent_link.get('href', ''))

                    if not title or not torrent_id_match:
                        continue

                    torrent_id = torrent_id_match.group(1)
                    torrent_info = {
                        'title': title,
                        'author': author_name,
                        'torrent_id': torrent_id,
                        'url': urljoin(self.mam_url, f"/t/{torrent_id}/")
                    }

                    all_results.append(torrent_info)
                    page_results += 1

                print(f"Found {page_results} results")

                if page_results == 0:
                    has_more = False
                    self.logger.info(f"No results on page {page_num}, stopping")

                if page_num >= 15:
                    self.logger.warning("Reached page limit (15), stopping")
                    has_more = False

            except Exception as e:
                self.logger.error(f"Error on page {page_num}: {e}")
                break

        self.logger.info(f"Total results for {author_name}: {len(all_results)}")
        print(f"  Total: {len(all_results)} audiobooks\n")

        self.results["mam_results"][author_name] = all_results
        return all_results

    def search_goodreads_author(self, author_name: str) -> Set[str]:
        """Search Goodreads for author to verify completeness"""
        print(f"Searching Goodreads for {author_name}...", end=" ", flush=True)

        try:
            # For webdriver mode, use Selenium; otherwise use requests
            if self.mode == "webdriver" and self.driver:
                return self._search_goodreads_selenium(author_name)
            else:
                return self._search_goodreads_requests(author_name)

        except Exception as e:
            self.logger.warning(f"Goodreads error: {e}")
            print("(error)")
            return set()

    def _search_goodreads_requests(self, author_name: str) -> Set[str]:
        """Search Goodreads using requests library"""
        search_url = "https://www.goodreads.com/search"
        params = {
            'q': author_name,
            'search_type': 'author'
        }

        response = requests.get(search_url, params=params, timeout=30)

        if response.status_code != 200:
            self.logger.warning(f"Goodreads search failed: {response.status_code}")
            print("(failed)")
            return set()

        soup = BeautifulSoup(response.text, 'html.parser')
        books = set()

        for book_link in soup.find_all('a', {'class': re.compile(r'.*bookTitle.*')}):
            title = book_link.get_text(strip=True)
            if title:
                books.add(title)

        print(f"(found {len(books)} titles)")
        self.logger.info(f"Goodreads: {len(books)} books for {author_name}")

        self.results["goodreads_results"][author_name] = list(books)
        return books

    def _search_goodreads_selenium(self, author_name: str) -> Set[str]:
        """Search Goodreads using Selenium (webdriver mode)"""
        search_url = f"https://www.goodreads.com/search?q={quote(author_name)}&search_type=books"
        self.driver.get(search_url)
        time.sleep(3)

        books = set()
        page_num = 1
        max_pages = 10

        for _ in range(max_pages):
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            book_rows = soup.find_all('tr', {'itemtype': 'http://schema.org/Book'})

            for book_row in book_rows:
                title_link = book_row.find('a', {'class': 'bookTitle'})
                if title_link:
                    title_span = title_link.find('span', {'itemprop': 'name'})
                    if title_span:
                        title = title_span.get_text(strip=True)
                        if title:
                            books.add(title)

            # Check for next page
            try:
                next_btn = self.driver.find_elements(By.XPATH, "//a[@rel='next']")
                if next_btn:
                    next_btn[0].click()
                    time.sleep(2)
                    page_num += 1
                else:
                    break
            except:
                break

        print(f"(found {len(books)} titles across {page_num} pages)")
        self.logger.info(f"Goodreads: {len(books)} books for {author_name}")

        self.results["goodreads_results"][author_name] = list(books)
        return books

    async def get_abs_library_books(self) -> Dict[str, List[str]]:
        """Get all books from Audiobookshelf by author"""
        print(f"\n{'=' * 120}")
        print("QUERYING AUDIOBOOKSHELF LIBRARY")
        print(f"{'=' * 120}")

        try:
            async with AudiobookshelfClient(self.abs_url, self.abs_token) as client:
                library_items = await client.get_library_items(limit=500)
                self.logger.info(f"Retrieved {len(library_items)} items")

                books_by_author = {}
                for item in library_items:
                    metadata = item.get('media', {}).get('metadata', {})
                    title = metadata.get('title', 'Unknown')
                    authors = metadata.get('authors', [])

                    if not authors:
                        author_name = metadata.get('authorName', '')
                        if author_name:
                            authors = [author_name]

                    for author in authors:
                        author_name = author if isinstance(author, str) else author.get('name', '')
                        if author_name:
                            if author_name not in books_by_author:
                                books_by_author[author_name] = []
                            books_by_author[author_name].append(title)

                for author in self.authors:
                    count = len(books_by_author.get(author, []))
                    print(f"  {author}: {count} books")

                self.results["abs_library"] = books_by_author
                return books_by_author

        except Exception as e:
            self.logger.error(f"Audiobookshelf error: {e}")
            return {}

    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison"""
        normalized = title.lower().strip()
        normalized = re.sub(r'\s*\(.*?(?:book|series|part|vol).*?\)\s*', '', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'[\[\]]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def identify_missing_titles(self) -> Dict[str, List[Dict[str, Any]]]:
        """Compare MAM results with Audiobookshelf library"""
        print(f"\n{'=' * 120}")
        print("IDENTIFYING MISSING TITLES")
        print(f"{'=' * 120}")

        missing_by_author = {}

        for author in self.authors:
            mam_books = self.results["mam_results"].get(author, [])
            abs_books = self.results["abs_library"].get(author, [])

            abs_normalized = {self._normalize_title(b) for b in abs_books}
            missing = []

            for mam_book in mam_books:
                mam_normalized = self._normalize_title(mam_book['title'])
                if mam_normalized not in abs_normalized:
                    missing.append(mam_book)

            missing_by_author[author] = missing

            print(f"\n{author}:")
            print(f"  MAM results: {len(mam_books)}")
            print(f"  In library: {len(abs_books)}")
            print(f"  Missing: {len(missing)}")

            if missing:
                print(f"  First 5 missing titles:")
                for book in missing[:5]:
                    print(f"    - {book['title']}")
                if len(missing) > 5:
                    print(f"    ... and {len(missing) - 5} more")

        self.results["missing_titles"] = missing_by_author
        return missing_by_author

    def extract_magnet_from_torrent_page(self, torrent_id: str) -> Optional[str]:
        """Extract magnet link from torrent details page"""
        try:
            torrent_url = f"{self.mam_url}/t/{torrent_id}/"
            time.sleep(1)

            response = self.session.get(torrent_url, timeout=30)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')
            magnet_link = soup.find('a', href=re.compile(r'^magnet:\?'))

            if magnet_link:
                return magnet_link.get('href')

            return None

        except Exception as e:
            self.logger.error(f"Error extracting magnet for {torrent_id}: {e}")
            return None

    async def queue_missing_to_qbittorrent(self) -> int:
        """Queue missing titles to qBittorrent"""
        print(f"\n{'=' * 120}")
        print("QUEUING MISSING TITLES TO QBITTORRENT")
        print(f"{'=' * 120}")

        queued_count = 0

        try:
            async with QBittorrentClient(self.qb_url, self.qb_user, self.qb_pass) as qb:
                for author in self.authors:
                    missing = self.results["missing_titles"].get(author, [])
                    print(f"\n{author}: Attempting to queue {len(missing)} missing titles")

                    for book in missing[:10]:  # Queue up to 10 per author
                        try:
                            magnet_link = self.extract_magnet_from_torrent_page(book['torrent_id'])

                            if not magnet_link:
                                self.logger.warning(f"No magnet for {book['title']}")
                                print(f"  - {book['title']}: No magnet link found")
                                continue

                            result = await qb.add_torrent(
                                magnet_link,
                                category="audiobooks",
                                paused=False
                            )

                            if result.get('success'):
                                queued_count += 1
                                print(f"  [OK] {book['title']}")
                                self.results["queued"].append({
                                    'title': book['title'],
                                    'author': author,
                                    'torrent_id': book['torrent_id']
                                })
                            else:
                                self.logger.error(f"Failed to queue {book['title']}")
                                print(f"  [ERROR] {book['title']}: {result.get('error')}")

                        except Exception as e:
                            self.logger.error(f"Error queuing {book['title']}: {e}")
                            print(f"  [ERROR] {book['title']}: {str(e)}")

        except Exception as e:
            self.logger.error(f"qBittorrent connection error: {e}")
            print(f"\nWARNING: Could not connect to qBittorrent: {e}")
            print("You can manually queue the titles listed above.")

        print(f"\nTotal queued: {queued_count} audiobooks")
        return queued_count

    def save_report(self):
        """Save results to JSON"""
        report_file = f"author_search_report_{self.mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Report saved to {report_file}")
            print(f"\nReport saved: {report_file}")
        except Exception as e:
            self.logger.error(f"Could not save report: {e}")

    async def run(self, skip_queue: bool = False):
        """Execute complete workflow"""
        print("\n" + "=" * 120)
        print(f"UNIFIED AUTHOR AUDIOBOOK SEARCH - MODE: {self.mode.upper()}")
        print("=" * 120)
        print(f"Start: {datetime.now().isoformat()}")
        print(f"Authors: {', '.join(self.authors)}")

        try:
            # Step 1: Authenticate
            if not self.authenticate():
                self.logger.warning("Authentication may have failed, proceeding anyway")

            # Step 2: Search MAM for all authors
            for author in self.authors:
                self.search_mam_by_author(author)
                time.sleep(3)

            # Step 3: Verify with Goodreads
            print(f"\n{'=' * 120}")
            print("GOODREADS VERIFICATION")
            print(f"{'=' * 120}")
            for author in self.authors:
                self.search_goodreads_author(author)
                time.sleep(2)

            # Step 4: Get Audiobookshelf library
            await self.get_abs_library_books()

            # Step 5: Identify missing
            self.identify_missing_titles()

            # Step 6: Queue missing (if not skipped)
            if not skip_queue:
                await self.queue_missing_to_qbittorrent()
            else:
                print("\n[SKIPPED] qBittorrent queuing (--skip-queue flag set)")

            # Step 7: Save report
            self.save_report()

            print("\n" + "=" * 120)
            print("WORKFLOW COMPLETE")
            print("=" * 120)
            print(f"End: {datetime.now().isoformat()}\n")

        except Exception as e:
            self.logger.error(f"Workflow error: {e}", exc_info=True)
            print(f"\nError: {e}")
        finally:
            self.cleanup()


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Unified Author Audiobook Search Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --mode=basic
  %(prog)s --mode=auth          # Default, recommended
  %(prog)s --mode=webdriver
  %(prog)s --mode=auth --authors="Author Name" --skip-queue
  %(prog)s --mode=webdriver --no-headless

Modes:
  basic      - Simple search without authentication (public access only)
  auth       - Authenticated search with MAM_ID cookie (default, recommended)
  webdriver  - Full Selenium WebDriver with login automation

Environment Variables:
  MAM_USERNAME, MAM_PASSWORD  - MAM credentials (for webdriver mode)
  MAM_ID                      - MAM session cookie (for auth mode)
  ABS_URL, ABS_TOKEN          - Audiobookshelf server details
  QBITTORRENT_URL             - qBittorrent server URL
  QBITTORRENT_USERNAME        - qBittorrent username
  QBITTORRENT_PASSWORD        - qBittorrent password
        """
    )

    parser.add_argument(
        '--mode',
        choices=['basic', 'auth', 'webdriver'],
        default='auth',
        help='Search mode (default: auth)'
    )

    parser.add_argument(
        '--authors',
        type=str,
        help='Comma-separated list of authors to search (default: William D. Arand, Randi Darren, A. R. Rend)'
    )

    parser.add_argument(
        '--skip-queue',
        action='store_true',
        help='Skip qBittorrent queuing step'
    )

    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Run browser in non-headless mode (webdriver mode only, for debugging)'
    )

    return parser.parse_args()


async def main():
    args = parse_args()

    # Parse authors list if provided
    authors = None
    if args.authors:
        authors = [a.strip() for a in args.authors.split(',')]

    # Create search instance
    search = UnifiedAuthorSearch(
        mode=args.mode,
        authors=authors,
        headless=not args.no_headless
    )

    # Run workflow
    await search.run(skip_queue=args.skip_queue)


if __name__ == '__main__':
    asyncio.run(main())
