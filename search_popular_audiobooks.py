#!/usr/bin/env python3
"""
Search for popular audiobooks in Fantasy and Sci-Fi genres on MAM
Uses search with sorting by snatched count to find top audiobooks
"""

import logging
import os
import sys
import time
import json
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import quote, urljoin
import re

if sys.platform == 'win32':
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except:
        pass

from dotenv import load_dotenv
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("=" * 120)
print("MAM POPULAR AUDIOBOOK SEARCHER")
print("=" * 120)
print(f"Start: {datetime.now().isoformat()}")
print()

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
    from webdriver_manager.chrome import ChromeDriverManager
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"ERROR: Missing required library: {e}")
    print("Install with: pip install selenium webdriver-manager beautifulsoup4 python-dotenv")
    sys.exit(1)


class StealthUA:
    """User Agent rotation for stealth mode"""

    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    ]

    @staticmethod
    def random():
        return random.choice(StealthUA.USER_AGENTS)


class AntiCrawlMitigation:
    """Handles anti-crawling detection and evasion"""

    def __init__(self):
        self.request_times = []
        self.failed_attempts = 0
        self.max_consecutive_failures = 3
        self.base_delay = 2  # seconds
        self.max_delay = 30  # seconds

    def add_request(self):
        """Track request timing for rate limiting"""
        self.request_times.append(time.time())
        # Keep only last 10 requests
        if len(self.request_times) > 10:
            self.request_times = self.request_times[-10:]

    def check_rate_limit(self, min_interval: float = 2.0) -> bool:
        """Ensure minimum interval between requests"""
        if not self.request_times:
            return True

        time_since_last = time.time() - self.request_times[-1]
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            logger.info(f"Rate limiting: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
            self.add_request()
            return True

        self.add_request()
        return True

    def get_backoff_delay(self) -> float:
        """Exponential backoff for retries"""
        delay = min(self.base_delay * (2 ** self.failed_attempts), self.max_delay)
        # Add jitter (±20%)
        jitter = delay * random.uniform(0.8, 1.2)
        return jitter

    def record_failure(self):
        """Track failed request"""
        self.failed_attempts += 1
        logger.warning(f"Failed attempt {self.failed_attempts}, backoff: {self.get_backoff_delay():.1f}s")

    def record_success(self):
        """Reset failure counter on success"""
        self.failed_attempts = 0

    def should_give_up(self) -> bool:
        """Determine if we should give up after too many failures"""
        return self.failed_attempts >= self.max_consecutive_failures

    def apply_random_delay(self, min_sec: float = 1.0, max_sec: float = 4.0):
        """Apply random delay to appear more human"""
        delay = random.uniform(min_sec, max_sec)
        logger.debug(f"Human-like delay: {delay:.2f}s")
        time.sleep(delay)


class MAMPopularSearcher:
    """Search for popular audiobooks in specific genres on MAM"""

    def __init__(self, email: str, password: str, headless: bool = True):
        self.email = email
        self.password = password
        self.base_url = "https://www.myanonamouse.net"
        self.driver = None
        self.wait = None
        self.authenticated = False
        self.headless = headless
        self.anti_crawl = AntiCrawlMitigation()

        # Cookie persistence
        self.cookies_file = 'mam_cookies.json'

    def setup(self) -> bool:
        """Initialize Selenium WebDriver"""
        print("SETUP: Initializing components")
        print("-" * 120)

        try:
            # Setup Chrome options for stealth
            chrome_options = ChromeOptions()

            if self.headless:
                chrome_options.add_argument('--headless=new')

            # Stealth arguments
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument(f'user-agent={StealthUA.random()}')

            # Security and privacy
            chrome_options.add_argument('--disable-web-resources')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--no-first-run')
            chrome_options.add_argument('--no-default-browser-check')

            # Performance
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')  # Don't load images (faster)

            # Start driver with automatic ChromeDriver management
            logger.info("Starting Selenium WebDriver (Chrome)")
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 20)

            print(f"✓ Selenium WebDriver initialized (headless={self.headless})")

            # Load cookies if available
            self._load_cookies()

            print()
            return True

        except Exception as e:
            logger.error(f"Setup failed: {e}")
            return False

    def _load_cookies(self):
        """Load saved cookies to restore session"""
        if os.path.exists(self.cookies_file):
            try:
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)

                self.driver.get(self.base_url)
                self.anti_crawl.apply_random_delay(0.5, 1.5)

                for cookie in cookies:
                    try:
                        self.driver.add_cookie(cookie)
                    except Exception as e:
                        logger.debug(f"Could not add cookie {cookie.get('name')}: {e}")

                logger.info(f"Loaded {len(cookies)} saved cookies")
                return True
            except Exception as e:
                logger.warning(f"Could not load cookies: {e}")

        return False

    def _save_cookies(self):
        """Save cookies for session recovery"""
        try:
            cookies = self.driver.get_cookies()
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f)
            logger.info(f"Saved {len(cookies)} cookies")
        except Exception as e:
            logger.warning(f"Could not save cookies: {e}")

    def login(self) -> bool:
        """Login to MAM with email/password."""
        print("STEP 1: Login to MyAnonamouse (email/password)")
        print("-" * 120)

        max_retries = 3
        attempt = 0

        while attempt < max_retries:
            attempt += 1
            logger.info(f"Login attempt {attempt}/{max_retries}")

            try:
                self.anti_crawl.check_rate_limit(2.0)
                self.anti_crawl.apply_random_delay(0.5, 1.5)

                # Navigate to login
                login_url = f"{self.base_url}/login.php"
                logger.info(f"Navigating to {login_url}")
                self.driver.get(login_url)

                # Wait for form to load
                self.wait.until(EC.presence_of_element_located((By.NAME, "email")))
                logger.info("Login form loaded")

                self.anti_crawl.apply_random_delay(0.3, 1.0)

                # Fill email
                email_input = self.driver.find_element(By.NAME, "email")
                email_input.clear()
                email_input.send_keys(self.email)
                logger.debug("Email filled")

                self.anti_crawl.apply_random_delay(0.2, 0.8)

                # Fill password
                password_input = self.driver.find_element(By.NAME, "password")
                password_input.clear()
                password_input.send_keys(self.password)
                logger.debug("Password filled")

                self.anti_crawl.apply_random_delay(0.5, 1.5)

                # Submit form
                submit_btn = self.driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
                submit_btn.click()
                logger.info("Login form submitted")

                # Wait for page to load after login
                time.sleep(5)

                # Check if login was successful
                page_source = self.driver.page_source

                # Save for debugging
                with open('mam_login_response.html', 'w', encoding='utf-8') as f:
                    f.write(page_source)

                if 'not logged in' in page_source.lower() and 'error' in page_source.lower():
                    logger.warning(f"Login failed: 'Not logged in' message detected")
                    self.anti_crawl.record_failure()

                    if self.anti_crawl.should_give_up():
                        print(f"  ✗ Login failed after {max_retries} attempts")
                        return False

                    delay = self.anti_crawl.get_backoff_delay()
                    logger.info(f"Retrying after {delay:.1f}s backoff")
                    time.sleep(delay)
                    continue

                # Positive indicators
                if 'torrent' in page_source.lower() or 'browse' in page_source.lower() or 'logout' in page_source.lower():
                    self.authenticated = True
                    self.anti_crawl.record_success()

                    # Save cookies
                    self._save_cookies()

                    print(f"  ✓ Logged in successfully")
                    print(f"  ✓ Session cookies saved")
                    print()
                    return True

                logger.warning(f"Login verification inconclusive")
                self.anti_crawl.record_failure()

                if self.anti_crawl.should_give_up():
                    print(f"  ✗ Login failed: verification inconclusive")
                    return False

                delay = self.anti_crawl.get_backoff_delay()
                logger.info(f"Retrying after {delay:.1f}s backoff")
                time.sleep(delay)

            except TimeoutException as e:
                logger.error(f"Login timeout: {e}")
                self.anti_crawl.record_failure()

                if self.anti_crawl.should_give_up():
                    print(f"  ✗ Login timeout after {max_retries} attempts")
                    return False

                delay = self.anti_crawl.get_backoff_delay()
                logger.info(f"Retrying after {delay:.1f}s backoff")
                time.sleep(delay)

            except Exception as e:
                logger.error(f"Login error: {e}")
                self.anti_crawl.record_failure()

                if self.anti_crawl.should_give_up():
                    print(f"  ✗ Login failed: {e}")
                    return False

                delay = self.anti_crawl.get_backoff_delay()
                logger.info(f"Retrying after {delay:.1f}s backoff")
                time.sleep(delay)

        return False

    def search_popular_genre(self, genre_name: str, category_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for popular audiobooks in a specific genre"""
        logger.info(f"Searching for top {limit} popular {genre_name} audiobooks")

        try:
            self.anti_crawl.check_rate_limit(3.0)
            self.anti_crawl.apply_random_delay(1.0, 2.0)

            # Build search URL for audiobooks in this category, sorted by most snatched
            search_url = (
                f"{self.base_url}/tor/browse.php?"
                f"&tor[srchIn][title]=true"
                f"&tor[srchIn][author]=true"
                f"&tor[srchIn][narrator]=true"
                f"&tor[searchType]=all"
                f"&tor[searchIn]=torrents"
                f"&tor[cat][]={category_id}"  # Specific category
                f"&tor[browse_lang][]=1"  # English
                f"&tor[browseFlagsHideVsShow]=0"
                f"&tor[sortType]=snatchedDesc"  # Sort by most snatched (popularity)
                f"&tor[startNumber]=0"
                f"&thumbnail=true"
            )

            logger.info(f"Navigating to search URL for {genre_name}")
            self.driver.get(search_url)

            # Wait for results to load
            time.sleep(4)

            page_source = self.driver.page_source

            # Save for debugging
            with open(f'mam_popular_{genre_name.lower()}.html', 'w', encoding='utf-8') as f:
                f.write(page_source)

            # Check for login page
            if 'not logged in' in page_source.lower():
                logger.warning("Session lost, re-authenticating...")
                if self.login():
                    self.driver.get(search_url)
                    time.sleep(3)
                    page_source = self.driver.page_source
                else:
                    return []

            # Parse HTML
            soup = BeautifulSoup(page_source, 'html.parser')

            books = []
            # Look for torrent rows
            torrent_rows = soup.find_all('tr', class_='torrent')

            if not torrent_rows:
                # Try alternative selectors
                torrent_rows = soup.find_all('tr', {'class': lambda x: x and 'torrent' in x})

            logger.info(f"Found {len(torrent_rows)} torrent entries for {genre_name}")

            for idx, row in enumerate(torrent_rows[:limit]):
                try:
                    # Extract title and link
                    title_elem = row.find('a', href=re.compile(r'/t/\d+'))
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    link = title_elem.get('href', '')

                    if link.startswith('/'):
                        link = urljoin(self.base_url, link)

                    # Extract torrent ID
                    match = re.search(r'/t/(\d+)', link)
                    if not match:
                        continue

                    torrent_id = match.group(1)

                    # Try to extract additional info from the row
                    author = "Unknown"
                    size = "Unknown"
                    snatched = "0"
                    seeders = "0"

                    # Look for author in the row
                    author_elem = row.find('a', href=re.compile(r'/u/\d+'))
                    if author_elem:
                        author = author_elem.get_text(strip=True)

                    # Look for size info
                    size_elem = row.find(text=re.compile(r'\d+\.\d+\s*(MB|GB|TB|KB)'))
                    if size_elem:
                        size = size_elem.strip()

                    # Look for snatched count
                    snatched_elem = row.find(text=re.compile(r'Snatched:\s*\d+'))
                    if snatched_elem:
                        snatched_match = re.search(r'Snatched:\s*(\d+)', snatched_elem)
                        if snatched_match:
                            snatched = snatched_match.group(1)

                    # Look for seeders
                    seeders_elem = row.find('td', {'class': 'seeders'})
                    if seeders_elem:
                        seeders = seeders_elem.get_text(strip=True)

                    book_data = {
                        'rank': idx + 1,
                        'title': title,
                        'author': author,
                        'torrent_url': link,
                        'torrent_id': torrent_id,
                        'size': size,
                        'snatched': snatched,
                        'seeders': seeders,
                        'genre': genre_name,
                        'search_popularity': True  # Indicates this came from popularity search
                    }

                    books.append(book_data)
                    logger.info(f"[{idx+1}] {title} by {author} (snatched: {snatched})")

                except Exception as e:
                    logger.warning(f"Error extracting row {idx}: {e}")
                    continue

            return books

        except Exception as e:
            logger.error(f"Error searching popular {genre_name}: {e}")
            return []

    def _get_magnet_link(self, torrent_id: str) -> Optional[str]:
        """Extract magnet link from torrent page."""
        try:
            self.anti_crawl.apply_random_delay(0.5, 1.5)

            torrent_url = f"{self.base_url}/t/{torrent_id}"
            logger.debug(f"Fetching magnet from {torrent_url}")

            self.driver.get(torrent_url)
            time.sleep(2)

            page_source = self.driver.page_source

            # Look for magnet link
            magnet_match = re.search(r'(magnet:\?[^"<\s]+)', page_source)
            if magnet_match:
                return magnet_match.group(1)

            return None

        except Exception as e:
            logger.error(f"Error getting magnet link: {e}")
            return None

    def add_magnet_links(self, books: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add magnet links to book data"""
        logger.info("Fetching magnet links for books...")

        for book in books:
            if 'torrent_id' in book and 'magnet' not in book:
                magnet = self._get_magnet_link(book['torrent_id'])
                if magnet:
                    book['magnet'] = magnet
                    logger.info(f"Got magnet for: {book['title'][:50]}...")
                else:
                    logger.warning(f"No magnet found for: {book['title'][:50]}")

                # Rate limiting between magnet fetches
                time.sleep(1)

        return books

    def search_multiple_genres(self, genres_config: Dict[str, str], limit: int = 10) -> Dict[str, Any]:
        """Search for popular audiobooks across multiple genres"""
        print("STEP 2: Searching for Popular Audiobooks")
        print("-" * 120)

        results = {
            'genres_searched': [],
            'total_books': 0,
            'books_by_genre': {},
            'timestamp': datetime.now().isoformat(),
            'errors': []
        }

        for genre_name, category_id in genres_config.items():
            print(f"\nSearching {genre_name}...")
            try:
                books = self.search_popular_genre(genre_name, category_id, limit)

                if books:
                    results['genres_searched'].append(genre_name)
                    results['books_by_genre'][genre_name] = books
                    results['total_books'] += len(books)
                    print(f"  ✓ Found {len(books)} books")
                else:
                    results['errors'].append(f"No books found for {genre_name}")
                    print(f"  ✗ No books found")

                # Rate limiting between genres
                time.sleep(3)

            except Exception as e:
                error_msg = f"Error searching {genre_name}: {str(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg)
                print(f"  ✗ Error: {str(e)[:60]}")

        # Add magnet links to all books
        if results['total_books'] > 0:
            print("\nFetching magnet links...")
            all_books = []
            for genre_books in results['books_by_genre'].values():
                all_books.extend(genre_books)

            all_books = self.add_magnet_links(all_books)

            # Update the results with magnet links
            book_index = 0
            for genre_name in results['books_by_genre']:
                genre_books = results['books_by_genre'][genre_name]
                for i, book in enumerate(genre_books):
                    if book_index < len(all_books):
                        genre_books[i] = all_books[book_index]
                        book_index += 1

        return results

    def cleanup(self):
        """Close WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")

    def run(self, genres_config: Dict[str, str], limit: int = 10) -> Dict[str, Any]:
        """Execute the search workflow"""
        try:
            if not self.setup():
                return {"error": "Setup failed"}

            if not self.authenticated:
                if not self.login():
                    return {"error": "Login failed"}

            results = self.search_multiple_genres(genres_config, limit)

            # Print summary
            print("\n" + "=" * 120)
            print("SEARCH SUMMARY")
            print("=" * 120)
            print(f"Genres searched: {len(results['genres_searched'])}")
            print(f"Total books found: {results['total_books']}")

            for genre in results['genres_searched']:
                books = results['books_by_genre'].get(genre, [])
                print(f"  {genre}: {len(books)} books")

            if results['errors']:
                print(f"Errors: {len(results['errors'])}")
                for error in results['errors'][:3]:  # Show first 3 errors
                    print(f"  - {error}")

            print()

            return results

        except Exception as e:
            logger.error(f"Fatal error: {e}")
            return {"error": str(e)}

        finally:
            self.cleanup()


def main():
    """Main execution."""

    mam_email = os.getenv('MAM_USERNAME')
    mam_password = os.getenv('MAM_PASSWORD')

    if not all([mam_email, mam_password]):
        print("ERROR: Missing required environment variables")
        print("Required: MAM_USERNAME, MAM_PASSWORD")
        return False

    # Genres to search (category IDs for audiobooks)
    genres_config = {
        'fantasy': '41',    # Fantasy audiobooks
        'sci-fi': '42',     # Science Fiction audiobooks
    }

    # Create searcher (headless=True for production)
    searcher = MAMPopularSearcher(mam_email, mam_password, headless=True)
    results = searcher.run(genres_config, limit=10)

    # Save results
    if 'error' not in results:
        output_file = 'mam_popular_audiobooks.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Results saved to {output_file}")

        # Also save a simplified version for the next steps
        simplified_books = []
        for genre, books in results.get('books_by_genre', {}).items():
            for book in books:
                simplified_books.append({
                    'title': book['title'],
                    'author': book['author'],
                    'genre': genre,
                    'magnet': book.get('magnet', ''),
                    'snatched': book.get('snatched', '0')
                })

        simplified_file = 'audiobooks_to_download.json'
        with open(simplified_file, 'w', encoding='utf-8') as f:
            json.dump(simplified_books, f, indent=2, ensure_ascii=False)
        print(f"Simplified list saved to {simplified_file}")

    return 'error' not in results


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)