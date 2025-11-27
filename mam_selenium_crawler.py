#!/usr/bin/env python3
"""
MAM Selenium WebDriver Crawler - Production Ready
==================================================
Complete rewrite using Selenium for reliable browser automation
- Robust session management with proper JavaScript execution
- Anti-crawling detection and evasion
- Stealth mode: headers rotation, user agent randomization, delays
- Cookie persistence and recovery
- Rate limiting and exponential backoff
- Comprehensive error handling and retry logic
- Full logging for debugging
"""

import sys
import os
import time
import json
import logging
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from urllib.parse import quote, urljoin
import re

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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("=" * 120)
print("MAM SELENIUM CRAWLER - PRODUCTION READY")
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
    print("Install with: pip install selenium webdriver-manager beautifulsoup4")
    sys.exit(1)

# Import our session-based qBittorrent client
try:
    from qbittorrent_session_client import QBittorrentSessionClient
except ImportError:
    logger.warning("qbittorrent_session_client not found, will try qbittorrentapi")
    try:
        import qbittorrentapi
        QBittorrentSessionClient = None
    except ImportError:
        logger.error("No qBittorrent client available")
        QBittorrentSessionClient = None


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


class SeleniumMAMCrawler:
    """MAM crawler using Selenium WebDriver with comprehensive anti-crawling handling"""

    def __init__(self, email: str, password: str, qb_url: str, qb_user: str, qb_pass: str, headless: bool = True):
        self.email = email
        self.password = password
        self.base_url = "https://www.myanonamouse.net"

        self.qb_url = qb_url
        self.qb_user = qb_user
        self.qb_pass = qb_pass
        self.qb_client = None

        self.driver = None
        self.wait = None
        self.authenticated = False
        self.headless = headless
        self.anti_crawl = AntiCrawlMitigation()

        self.results = {"searched": 0, "found": 0, "queued": 0, "failed": 0}

        # Cookie persistence
        self.cookies_file = 'mam_cookies.json'

    def setup(self) -> bool:
        """Initialize Selenium WebDriver and qBittorrent."""
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

            # Setup qBittorrent using session-based client
            try:
                if QBittorrentSessionClient:
                    # Use our new session-based client
                    self.qb_client = QBittorrentSessionClient(
                        host=self.qb_url,
                        username=self.qb_user,
                        password=self.qb_pass
                    )
                    if not self.qb_client.login():
                        logger.error("Failed to login to qBittorrent")
                        return False
                else:
                    # Fallback to qbittorrentapi if available
                    import qbittorrentapi
                    self.qb_client = qbittorrentapi.Client(
                        host=self.qb_url,
                        username=self.qb_user,
                        password=self.qb_pass,
                        RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=False
                    )
                    self.qb_client.auth_log_in()

                print(f"✓ qBittorrent connected: {self.qb_url}")
            except Exception as e:
                logger.error(f"qBittorrent connection failed: {e}")
                return False

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
                with open('mam_selenium_login_response.html', 'w', encoding='utf-8') as f:
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

    def search_mam(self, search_term: str) -> Optional[Dict[str, Any]]:
        """Search MAM and extract first result."""
        try:
            self.anti_crawl.check_rate_limit(2.0)
            self.anti_crawl.apply_random_delay(1.0, 3.0)

            # Use the search form by navigating to browse page first
            logger.info(f"Searching for: {search_term}")
            browse_url = f"{self.base_url}/tor/browse.php"

            # Navigate to browse page
            self.driver.get(browse_url)
            time.sleep(2)

            # Find and fill the search input
            try:
                search_input = self.wait.until(
                    EC.presence_of_element_located((By.ID, "ts"))
                )
                search_input.clear()
                search_input.send_keys(search_term)
                logger.debug(f"Search term '{search_term}' entered")

                self.anti_crawl.apply_random_delay(0.5, 1.5)

                # Submit search form
                search_form = self.driver.find_element(By.ID, "mainSearch")
                search_form.submit()
                logger.debug("Search form submitted")

            except TimeoutException:
                logger.warning("Search form not found, trying direct URL")
                search_url = (
                    f"{self.base_url}/tor/browse.php"
                    f"?tor[searchstr]={quote(search_term)}"
                    f"&tor[cat][]=13"
                )
                self.driver.get(search_url)

            # Wait for results to load
            time.sleep(3)

            page_source = self.driver.page_source

            # Save for debugging
            with open(f'mam_selenium_search_{search_term.replace(" ", "_")}.html', 'w', encoding='utf-8') as f:
                f.write(page_source)

            # Check for login page
            if 'not logged in' in page_source.lower():
                logger.warning("Session lost, re-authenticating...")
                # Try to re-authenticate
                if self.login():
                    # Retry search
                    self.driver.get(search_url)
                    time.sleep(3)
                    page_source = self.driver.page_source
                else:
                    return None

            # Parse HTML
            soup = BeautifulSoup(page_source, 'html.parser')

            # Look for torrent links
            torrent_links = []

            for link in soup.find_all('a', href=re.compile(r'/t/\d+')):
                torrent_links.append(link)

            if not torrent_links:
                logger.info(f"No torrent links found")
                return None

            # Get first result
            first_link = torrent_links[0]
            result_title = first_link.get_text(strip=True)
            torrent_url = first_link.get('href', '')

            if torrent_url.startswith('/'):
                torrent_url = urljoin(self.base_url, torrent_url)

            # Extract torrent ID
            match = re.search(r'/t/(\d+)', torrent_url)
            if not match:
                return None

            torrent_id = match.group(1)
            logger.info(f"Found: {result_title[:60]}")

            # Get magnet link
            magnet = self._get_magnet_link(torrent_id)

            if magnet:
                logger.info(f"Magnet: {magnet[:60]}...")
                return {
                    'title': result_title,
                    'url': torrent_url,
                    'magnet': magnet,
                    'torrent_id': torrent_id
                }

            return None

        except Exception as e:
            logger.error(f"Search error: {e}")
            return None

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

    def search_and_queue(self, books: List[Dict[str, str]]):
        """Search for books and queue to qBittorrent."""
        print("STEP 2: Search MAM and Queue to qBittorrent")
        print("-" * 120)
        print()

        for i, book in enumerate(books, 1):
            title = book.get('title', 'Unknown')
            series = book.get('series', '')

            print(f"  [{i}/{len(books)}] Searching for: {title}")
            self.results['searched'] += 1

            # Search
            search_result = self.search_mam(title)

            if not search_result:
                print(f"      ✗ Not found on MAM")
                self.results['failed'] += 1
                time.sleep(2)
                continue

            magnet = search_result.get('magnet')
            if not magnet:
                print(f"      ✗ No magnet link")
                self.results['failed'] += 1
                time.sleep(2)
                continue

            # Queue to qBittorrent
            try:
                self.qb_client.torrents_add(
                    urls=magnet,
                    category='audiobooks',
                    tags=['mam', 'auto', series] if series else ['mam', 'auto'],
                    is_paused=False
                )
                print(f"      ✓ QUEUED TO QBITTORRENT")
                self.results['queued'] += 1
                self.results['found'] += 1

            except Exception as e:
                logger.error(f"Queue failed: {e}")
                print(f"      ✗ Queue failed: {str(e)[:60]}")
                self.results['failed'] += 1

            print()
            time.sleep(2)

    def show_queue(self):
        """Display qBittorrent queue."""
        print("STEP 3: Current qBittorrent Queue")
        print("-" * 120)

        torrents = self.qb_client.torrents_info()
        if torrents:
            print(f"Total torrents in queue: {len(torrents)}")
            print("\nLast 10 torrents:")
            for t in torrents[-10:]:
                # Handle both dict and object types
                name = t.get('name') if isinstance(t, dict) else getattr(t, 'name', 'Unknown')
                state = t.get('state') if isinstance(t, dict) else getattr(t, 'state', 'unknown')
                progress = (t.get('progress', 0) if isinstance(t, dict) else getattr(t, 'progress', 0)) * 100
                seeds = t.get('num_seeds') if isinstance(t, dict) else getattr(t, 'num_seeds', 0)
                print(f"  {name}")
                print(f"    State: {state} | Progress: {progress:.1f}% | Seeds: {seeds}")
        else:
            print("  (No torrents)")
        print()

    def summary(self):
        """Print summary."""
        print("=" * 120)
        print("EXECUTION SUMMARY")
        print("=" * 120)
        print(f"  Searched: {self.results['searched']}")
        print(f"  Found: {self.results['found']}")
        print(f"  Queued to qBittorrent: {self.results['queued']}")
        print(f"  Failed: {self.results['failed']}")
        print()
        if self.results['queued'] > 0:
            print("✓ SUCCESS: Books queued to qBittorrent!")
        else:
            print("✗ No books successfully queued")
        print()

    def cleanup(self):
        """Close WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")

    def run(self, books: List[Dict[str, str]]) -> bool:
        """Execute workflow."""
        try:
            if not self.setup():
                return False

            # Check if already authenticated with saved cookies
            if not self.authenticated:
                if not self.login():
                    return False

            self.search_and_queue(books)
            self.show_queue()
            self.summary()

            return self.results['queued'] > 0

        except Exception as e:
            logger.error(f"Fatal error: {e}")
            return False

        finally:
            self.cleanup()


def main():
    """Main execution."""

    mam_email = os.getenv('MAM_USERNAME')
    mam_password = os.getenv('MAM_PASSWORD')
    qb_url = os.getenv('QBITTORRENT_URL')
    qb_user = os.getenv('QBITTORRENT_USERNAME')
    qb_pass = os.getenv('QBITTORRENT_PASSWORD')

    if not all([mam_email, mam_password, qb_url, qb_user, qb_pass]):
        print("ERROR: Missing required environment variables")
        print("Required: MAM_USERNAME, MAM_PASSWORD, QBITTORRENT_URL, QBITTORRENT_USERNAME, QBITTORRENT_PASSWORD")
        return False

    # Audiobooks to search
    audiobooks_to_find = [
        {'title': 'Save State Hero Book 3', 'series': 'Save State Hero'},
        {'title': 'Save State Hero Book 2', 'series': 'Save State Hero'},
        {'title': 'Save State Hero Book 1', 'series': 'Save State Hero'},
        {'title': 'Save State Hero Book 4', 'series': 'Save State Hero'},
        {'title': 'Save State Hero Book 5', 'series': 'Save State Hero'},
    ]

    # Create crawler (headless=False to see what's happening, set to True for production)
    crawler = SeleniumMAMCrawler(mam_email, mam_password, qb_url, qb_user, qb_pass, headless=False)
    success = crawler.run(audiobooks_to_find)

    return success


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
