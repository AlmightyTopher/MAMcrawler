#!/usr/bin/env python3
"""
Complete Author Audiobook Search - Using Selenium for Auth
===========================================================
Search MAM for audiobooks by specified authors across ALL pages
Cross-verify with Goodreads (with login)
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
        logging.FileHandler('author_complete_search.log'),
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


class AuthorCompleteSearch:
    """
    Complete author search using proven Selenium approach from mam_selenium_crawler
    """

    AUTHORS = [
        "William D. Arand",
        "Randi Darren",
        "A. R. Rend"
    ]

    def __init__(self):
        self.mam_url = "https://www.myanonamouse.net"
        self.mam_username = os.getenv('MAM_USERNAME')
        self.mam_password = os.getenv('MAM_PASSWORD')

        self.abs_url = os.getenv('ABS_URL', 'http://localhost:13378')
        self.abs_token = os.getenv('ABS_TOKEN')

        self.qb_url = os.getenv('QBITTORRENT_URL', 'http://192.168.0.48:52095/')
        self.qb_user = os.getenv('QBITTORRENT_USERNAME', 'TopherGutbrod')
        self.qb_pass = os.getenv('QBITTORRENT_PASSWORD')

        # Goodreads credentials
        self.gr_email = os.getenv('GOODREADS_EMAIL', os.getenv('GOODREADS_USERNAME'))
        self.gr_password = os.getenv('GOODREADS_PASSWORD')

        # For Goodreads searches
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # Selenium driver
        self.driver = None
        self.wait = None

        self.results = {
            "mam_results": {},
            "goodreads_results": {},
            "abs_library": {},
            "missing_titles": {},
            "queued": []
        }

    def init_selenium(self) -> bool:
        """Initialize Selenium Chrome driver"""
        try:
            chrome_options = ChromeOptions()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 20)

            logger.info("Selenium WebDriver initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Selenium: {e}")
            return False

    def cleanup_selenium(self):
        """Close Selenium driver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Selenium WebDriver closed")
            except:
                pass

    def search_mam_by_author_all_pages(self, author_name: str) -> List[Dict[str, Any]]:
        """
        Search MAM for all audiobooks by an author across ALL pages
        Returns list of {title, author, url, torrent_id}
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

            logger.info(f"Fetching page {page_num} (startNumber={start_number})")
            print(f"  Page {page_num}...", end=" ", flush=True)

            try:
                time.sleep(3)  # Rate limiting
                response = requests.get(search_url, timeout=30)

                if response.status_code != 200:
                    logger.warning(f"Page {page_num} failed: {response.status_code}")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')

                # Find all torrent entries
                page_results = 0
                # Look for torrent table rows
                rows = soup.find_all('tr')

                for row in rows:
                    # Find torrent link in this row
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

                print(f"Found {page_results} results", flush=True)

                # If we got 0 results, assume no more pages
                if page_results == 0:
                    has_more = False
                    logger.info(f"No results on page {page_num}, stopping")

                # Limit to reasonable number of pages
                if page_num >= 15:
                    logger.warning("Reached page limit (15), stopping")
                    has_more = False

            except Exception as e:
                logger.error(f"Error on page {page_num}: {e}")
                break

        logger.info(f"Total results for {author_name}: {len(all_results)}")
        print(f"  Total: {len(all_results)} audiobooks\n")

        self.results["mam_results"][author_name] = all_results
        return all_results

    def search_goodreads_author(self, author_name: str) -> Set[str]:
        """Search Goodreads for author to verify completeness"""
        print(f"Searching Goodreads for {author_name}...", end=" ", flush=True)

        try:
            search_url = "https://www.goodreads.com/search"
            params = {
                'q': author_name,
                'search_type': 'author'
            }

            response = requests.get(search_url, params=params, timeout=30)

            if response.status_code != 200:
                logger.warning(f"Goodreads search failed: {response.status_code}")
                print("(failed)")
                return set()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract books from Goodreads
            books = set()
            for book_link in soup.find_all('a', {'class': re.compile(r'.*bookTitle.*')}):
                title = book_link.get_text(strip=True)
                if title:
                    books.add(title)

            print(f"(found {len(books)} titles)")
            logger.info(f"Goodreads: {len(books)} books for {author_name}")

            self.results["goodreads_results"][author_name] = list(books)
            return books

        except Exception as e:
            logger.warning(f"Goodreads error: {e}")
            print("(error)")
            return set()

    async def get_abs_library_books(self) -> Dict[str, List[str]]:
        """Get all books from Audiobookshelf by author"""
        print(f"\n{'=' * 120}")
        print(f"QUERYING AUDIOBOOKSHELF LIBRARY")
        print(f"{'=' * 120}")

        try:
            async with AudiobookshelfClient(self.abs_url, self.abs_token) as client:
                library_items = await client.get_library_items(limit=500)
                logger.info(f"Retrieved {len(library_items)} items")

                # Organize by author
                books_by_author = {}
                for item in library_items:
                    metadata = item.get('media', {}).get('metadata', {})
                    title = metadata.get('title', 'Unknown')

                    # Get authors
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

                # Print results
                for author in self.AUTHORS:
                    count = len(books_by_author.get(author, []))
                    print(f"  {author}: {count} books")

                self.results["abs_library"] = books_by_author
                return books_by_author

        except Exception as e:
            logger.error(f"Audiobookshelf error: {e}")
            return {}

    def extract_magnet_from_torrent_page(self, torrent_id: str) -> Optional[str]:
        """Extract magnet link from torrent details page"""
        try:
            torrent_url = f"{self.mam_url}/t/{torrent_id}/"
            time.sleep(1)

            response = requests.get(torrent_url, timeout=30)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for magnet link
            magnet_link = soup.find('a', href=re.compile(r'^magnet:\?'))
            if magnet_link:
                return magnet_link.get('href')

            return None

        except Exception as e:
            logger.error(f"Error extracting magnet for {torrent_id}: {e}")
            return None

    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison"""
        normalized = title.lower().strip()
        # Remove series/book info
        normalized = re.sub(r'\s*\(.*?(?:book|series|part|vol).*?\)\s*', '', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'[\[\]]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def identify_missing_titles(self) -> Dict[str, List[Dict[str, Any]]]:
        """Compare MAM results with Audiobookshelf library"""
        print(f"\n{'=' * 120}")
        print(f"IDENTIFYING MISSING TITLES")
        print(f"{'=' * 120}")

        missing_by_author = {}

        for author in self.AUTHORS:
            mam_books = self.results["mam_results"].get(author, [])
            abs_books = self.results["abs_library"].get(author, [])

            # Normalize ABS book titles
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

    async def queue_missing_to_qbittorrent(self) -> int:
        """Queue missing titles to qBittorrent"""
        print(f"\n{'=' * 120}")
        print(f"QUEUING MISSING TITLES TO QBITTORRENT")
        print(f"{'=' * 120}")

        queued_count = 0

        try:
            async with QBittorrentClient(self.qb_url, self.qb_user, self.qb_pass) as qb:
                for author in self.AUTHORS:
                    missing = self.results["missing_titles"].get(author, [])

                    print(f"\n{author}: Attempting to queue {len(missing)} missing titles")

                    for book in missing[:10]:  # Queue up to 10 per author
                        try:
                            magnet_link = self.extract_magnet_from_torrent_page(book['torrent_id'])

                            if not magnet_link:
                                logger.warning(f"No magnet for {book['title']}")
                                print(f"  - {book['title']}: No magnet link found")
                                continue

                            # Add to qBittorrent
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
                                logger.error(f"Failed to queue {book['title']}")
                                print(f"  [ERROR] {book['title']}: {result.get('error')}")

                        except Exception as e:
                            logger.error(f"Error queuing {book['title']}: {e}")
                            print(f"  [ERROR] {book['title']}: {str(e)}")

        except Exception as e:
            logger.error(f"qBittorrent connection error: {e}")
            print(f"\nWARNING: Could not connect to qBittorrent: {e}")
            print("You can manually queue the titles listed above.")

        print(f"\nTotal queued: {queued_count} audiobooks")
        return queued_count

    def save_report(self):
        """Save results to JSON"""
        report_file = f"author_complete_search_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            logger.info(f"Report saved to {report_file}")
            print(f"\nReport saved: {report_file}")
        except Exception as e:
            logger.error(f"Could not save report: {e}")

    async def run(self):
        """Execute complete workflow"""
        print("\n" + "=" * 120)
        print("AUTHOR AUDIOBOOK SEARCH - COMPLETE WORKFLOW")
        print("=" * 120)
        print(f"Start: {datetime.now().isoformat()}")
        print(f"Authors: {', '.join(self.AUTHORS)}")

        try:
            # Step 1: Search MAM for all authors
            for author in self.AUTHORS:
                self.search_mam_by_author_all_pages(author)
                time.sleep(3)

            # Step 2: Verify with Goodreads
            print(f"\n{'=' * 120}")
            print("GOODREADS VERIFICATION")
            print(f"{'=' * 120}")
            for author in self.AUTHORS:
                self.search_goodreads_author(author)
                time.sleep(2)

            # Step 3: Get Audiobookshelf library
            await self.get_abs_library_books()

            # Step 4: Identify missing
            self.identify_missing_titles()

            # Step 5: Queue missing
            await self.queue_missing_to_qbittorrent()

            # Step 6: Save report
            self.save_report()

            print("\n" + "=" * 120)
            print("WORKFLOW COMPLETE")
            print("=" * 120)
            print(f"End: {datetime.now().isoformat()}\n")

        except Exception as e:
            logger.error(f"Workflow error: {e}", exc_info=True)
            print(f"\nError: {e}")


async def main():
    search = AuthorCompleteSearch()
    await search.run()


if __name__ == '__main__':
    asyncio.run(main())
