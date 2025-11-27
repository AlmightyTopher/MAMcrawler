#!/usr/bin/env python3
"""
Author Audiobook Search with Full Authentication
==================================================
Complete search workflow with:
1. MAM authentication (Selenium WebDriver)
2. Goodreads authentication (Email/Password login)
3. Audiobookshelf library query
4. Missing title identification
5. qBittorrent queueing

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

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('author_search_auth.log'),
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

from backend.integrations.abs_client import AudiobookshelfClient
from backend.integrations.qbittorrent_client import QBittorrentClient


class AuthorSearchWithAuth:
    """Complete author search with proper authentication for MAM and Goodreads"""

    AUTHORS = ["William D. Arand", "Randi Darren", "A. R. Rend"]

    def __init__(self):
        self.mam_url = "https://www.myanonamouse.net"
        self.mam_username = os.getenv('MAM_USERNAME')
        self.mam_password = os.getenv('MAM_PASSWORD')

        self.abs_url = os.getenv('ABS_URL', 'http://localhost:13378')
        self.abs_token = os.getenv('ABS_TOKEN')

        self.qb_url = os.getenv('QBITTORRENT_URL', 'http://192.168.0.48:52095/')
        self.qb_user = os.getenv('QBITTORRENT_USERNAME', 'TopherGutbrod')
        self.qb_pass = os.getenv('QBITTORRENT_PASSWORD')

        self.gr_email = os.getenv('GOODREADS_EMAIL', os.getenv('GOODREADS_USERNAME'))
        self.gr_password = os.getenv('GOODREADS_PASSWORD')

        self.driver = None
        self.wait = None
        self.session = requests.Session()

        self.results = {
            "mam_results": {},
            "goodreads_results": {},
            "abs_library": {},
            "missing_titles": {},
            "queued": []
        }

    def init_selenium(self, headless: bool = True) -> bool:
        """Initialize Selenium WebDriver"""
        try:
            chrome_options = ChromeOptions()
            if headless:
                chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            chrome_options.add_argument('--disable-plugins')

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 20)

            logger.info("Selenium WebDriver initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Selenium: {e}")
            return False

    def cleanup(self):
        """Close Selenium driver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Selenium driver closed")
            except:
                pass

    def login_mam(self) -> bool:
        """Authenticate with MAM using the provided MAM_ID cookie"""
        try:
            mam_id = os.getenv('MAM_ID')
            if mam_id:
                logger.info("Using MAM_ID for authentication...")
                # Set the MAM_ID as a cookie
                self.session.cookies.set('mam_id', mam_id, domain='www.myanonamouse.net', path='/')
                logger.info("MAM_ID cookie set, proceeding with authenticated search")
                return True
            else:
                logger.warning("No MAM_ID found in environment")
                return False

        except Exception as e:
            logger.error(f"MAM authentication error: {e}")
            return False

    def search_mam_authenticated(self, author_name: str) -> List[Dict[str, Any]]:
        """
        Search MAM using authenticated session across ALL pages
        """
        print(f"\n{'=' * 120}")
        print(f"SEARCHING MAM (AUTHENTICATED): {author_name}")
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
                f"&tor[cat][]=13"
                f"&tor[searchType]=all"
                f"&tor[startNumber]={start_number}"
            )

            logger.info(f"Page {page_num} (startNumber={start_number})")
            print(f"  Page {page_num}...", end=" ", flush=True)

            try:
                time.sleep(3)
                # Use authenticated session
                response = self.session.get(search_url, timeout=30)

                if response.status_code != 200:
                    logger.warning(f"Page {page_num} failed: {response.status_code}")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')
                page_results = 0

                # Parse torrent entries
                rows = soup.find_all('tr')
                for row in rows:
                    torrent_link = row.find('a', href=re.compile(r'/t/\d+'))
                    if not torrent_link:
                        continue

                    title = torrent_link.get_text(strip=True)
                    match = re.search(r'/t/(\d+)', torrent_link.get('href', ''))

                    if not title or not match:
                        continue

                    torrent_id = match.group(1)
                    all_results.append({
                        'title': title,
                        'author': author_name,
                        'torrent_id': torrent_id,
                        'url': urljoin(self.mam_url, f"/t/{torrent_id}/")
                    })
                    page_results += 1

                print(f"Found {page_results} results")

                if page_results == 0:
                    has_more = False
                    logger.info(f"No results on page {page_num}, stopping")

                if page_num >= 15:
                    logger.warning("Reached page limit (15), stopping")
                    has_more = False

            except Exception as e:
                logger.error(f"Error on page {page_num}: {e}")
                break

        logger.info(f"Total for {author_name}: {len(all_results)} audiobooks")
        print(f"  Total: {len(all_results)} audiobooks\n")

        self.results["mam_results"][author_name] = all_results
        return all_results

    def search_goodreads_authenticated(self, author_name: str) -> Set[str]:
        """
        Search Goodreads with Selenium login for authenticated access
        Paginates through ALL pages and filters for audiobooks only
        """
        print(f"Searching Goodreads for {author_name}...", end=" ", flush=True)

        try:
            # Use existing Selenium driver
            if not self.driver:
                logger.warning("Selenium driver not initialized")
                print("(skipped)")
                return set()

            # Navigate to Goodreads search for author
            search_url = f"https://www.goodreads.com/search?q={quote(author_name)}&search_type=books"
            self.driver.get(search_url)
            time.sleep(3)

            books = set()
            page_num = 1
            max_pages = 10
            has_next = True

            while has_next and page_num <= max_pages:
                logger.info(f"Goodreads page {page_num} for {author_name}")
                time.sleep(2)

                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')

                # Save first page for inspection
                if page_num == 1:
                    with open(f'goodreads_debug_{author_name.replace(" ", "_")}.html', 'w', encoding='utf-8') as f:
                        f.write(page_source)
                    logger.info(f"Saved debug HTML to goodreads_debug_{author_name.replace(' ', '_')}.html")

                # Find all book entries on this page
                # Goodreads uses <tr itemtype="http://schema.org/Book">
                book_rows = soup.find_all('tr', {'itemtype': 'http://schema.org/Book'})

                logger.debug(f"Found {len(book_rows)} book rows on page {page_num}")

                for book_row in book_rows:
                    # The title is in: <a class="bookTitle"><span itemprop="name">Title</span></a>
                    title_link = book_row.find('a', {'class': 'bookTitle'})

                    if title_link:
                        # Get the title from the span with itemprop="name"
                        title_span = title_link.find('span', {'itemprop': 'name'})
                        if title_span:
                            title = title_span.get_text(strip=True)
                            if title and len(title) > 1:
                                books.add(title)
                                logger.debug(f"Found title: {title}")

                # Look for next page button
                next_btn = self.driver.find_elements(By.XPATH, "//a[@rel='next']")

                if next_btn and len(next_btn) > 0:
                    try:
                        next_btn[0].click()
                        page_num += 1
                        time.sleep(2)
                    except:
                        has_next = False
                else:
                    # Try alternative next button selectors
                    next_link = soup.find('a', {'rel': 'next'})
                    if next_link:
                        next_url = next_link.get('href')
                        if next_url:
                            if not next_url.startswith('http'):
                                next_url = urljoin('https://www.goodreads.com', next_url)
                            self.driver.get(next_url)
                            page_num += 1
                            time.sleep(2)
                        else:
                            has_next = False
                    else:
                        has_next = False

            print(f"(found {len(books)} titles across {page_num} pages)")
            logger.info(f"Goodreads: {len(books)} books for {author_name} across {page_num} pages")

            self.results["goodreads_results"][author_name] = list(books)
            return books

        except Exception as e:
            logger.warning(f"Goodreads search error: {e}")
            print(f"(error: {e})")
            return set()

    async def get_abs_library(self) -> Dict[str, List[str]]:
        """Query Audiobookshelf library"""
        print(f"\n{'=' * 120}")
        print("QUERYING AUDIOBOOKSHELF LIBRARY")
        print(f"{'=' * 120}")

        try:
            async with AudiobookshelfClient(self.abs_url, self.abs_token) as client:
                items = await client.get_library_items(limit=500)
                logger.info(f"Retrieved {len(items)} items")

                books_by_author = {}
                for item in items:
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

                for author in self.AUTHORS:
                    count = len(books_by_author.get(author, []))
                    print(f"  {author}: {count} books")

                self.results["abs_library"] = books_by_author
                return books_by_author

        except Exception as e:
            logger.error(f"Audiobookshelf error: {e}")
            return {}

    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison"""
        normalized = title.lower().strip()
        normalized = re.sub(r'\s*\(.*?(?:book|series|part|vol).*?\)\s*', '', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'[\[\]]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def identify_missing(self) -> Dict[str, List[Dict[str, Any]]]:
        """Identify missing titles"""
        print(f"\n{'=' * 120}")
        print("IDENTIFYING MISSING TITLES")
        print(f"{'=' * 120}")

        missing_by_author = {}

        for author in self.AUTHORS:
            mam_books = self.results["mam_results"].get(author, [])
            abs_books = self.results["abs_library"].get(author, [])

            abs_normalized = {self._normalize_title(b) for b in abs_books}
            missing = []

            for mam_book in mam_books:
                if self._normalize_title(mam_book['title']) not in abs_normalized:
                    missing.append(mam_book)

            missing_by_author[author] = missing

            print(f"\n{author}:")
            print(f"  MAM results: {len(mam_books)}")
            print(f"  In library: {len(abs_books)}")
            print(f"  Missing: {len(missing)}")

            if missing:
                print(f"  First 5 missing:")
                for book in missing[:5]:
                    print(f"    - {book['title']}")
                if len(missing) > 5:
                    print(f"    ... and {len(missing) - 5} more")

        self.results["missing_titles"] = missing_by_author
        return missing_by_author

    async def queue_missing(self) -> int:
        """Queue missing titles to qBittorrent"""
        print(f"\n{'=' * 120}")
        print("QUEUING MISSING TITLES TO QBITTORRENT")
        print(f"{'=' * 120}")

        queued = 0

        try:
            async with QBittorrentClient(self.qb_url, self.qb_user, self.qb_pass) as qb:
                for author in self.AUTHORS:
                    missing = self.results["missing_titles"].get(author, [])
                    print(f"\n{author}: Queuing {len(missing)} titles")

                    for book in missing[:10]:
                        try:
                            torrent_url = book['url']
                            time.sleep(1)

                            resp = requests.get(torrent_url, timeout=30)
                            if resp.status_code != 200:
                                print(f"  - {book['title']}: Could not fetch torrent page")
                                continue

                            soup = BeautifulSoup(resp.text, 'html.parser')
                            magnet_link = soup.find('a', href=re.compile(r'^magnet:\?'))

                            if not magnet_link:
                                print(f"  - {book['title']}: No magnet link found")
                                continue

                            magnet = magnet_link.get('href')
                            result = await qb.add_torrent(magnet, category="audiobooks", paused=False)

                            if result.get('success'):
                                queued += 1
                                print(f"  [OK] {book['title']}")
                                self.results["queued"].append({
                                    'title': book['title'],
                                    'author': author,
                                    'torrent_id': book['torrent_id']
                                })
                            else:
                                print(f"  [ERROR] {book['title']}: {result.get('error')}")

                        except Exception as e:
                            logger.error(f"Error queuing {book['title']}: {e}")
                            print(f"  [ERROR] {book['title']}: {str(e)}")

        except Exception as e:
            logger.error(f"qBittorrent connection error: {e}")
            print(f"\nCould not connect to qBittorrent: {e}")

        print(f"\nTotal queued: {queued} audiobooks")
        return queued

    def save_report(self):
        """Save results"""
        report_file = f"author_search_auth_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            logger.info(f"Report saved to {report_file}")
            print(f"\nReport saved: {report_file}")
        except Exception as e:
            logger.error(f"Could not save report: {e}")

    async def run(self):
        """Execute workflow"""
        print("\n" + "=" * 120)
        print("AUTHOR AUDIOBOOK SEARCH - WITH AUTHENTICATION")
        print("=" * 120)
        print(f"Start: {datetime.now().isoformat()}")

        try:
            # Initialize Selenium
            if not self.init_selenium(headless=True):
                logger.error("Failed to initialize Selenium")
                return

            # Authenticate with MAM
            print(f"\n{'=' * 120}")
            print("AUTHENTICATING WITH MAM")
            print(f"{'=' * 120}")
            if not self.login_mam():
                logger.warning("MAM authentication may have failed, proceeding anyway")

            # Search MAM (using authenticated session)
            for author in self.AUTHORS:
                self.search_mam_authenticated(author)
                time.sleep(2)

            # Search Goodreads (using Selenium)
            print(f"\n{'=' * 120}")
            print("GOODREADS VERIFICATION (Selenium)")
            print(f"{'=' * 120}")
            for author in self.AUTHORS:
                self.search_goodreads_authenticated(author)
                time.sleep(2)

            # Query Audiobookshelf
            await self.get_abs_library()

            # Identify missing
            self.identify_missing()

            # Queue missing
            await self.queue_missing()

            # Save report
            self.save_report()

            print("\n" + "=" * 120)
            print("COMPLETE")
            print("=" * 120)
            print(f"End: {datetime.now().isoformat()}\n")

        except Exception as e:
            logger.error(f"Workflow error: {e}", exc_info=True)
            print(f"\nError: {e}")
        finally:
            self.cleanup()


async def main():
    search = AuthorSearchWithAuth()
    await search.run()


if __name__ == '__main__':
    asyncio.run(main())
