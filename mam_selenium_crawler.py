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

# if sys.platform == 'win32':
#     import io
#     try:
#         if hasattr(sys.stdout, 'buffer'):
#             sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
#         if hasattr(sys.stderr, 'buffer'):
#             sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
#     except Exception:
#         pass

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
    # Import ConfigSystem for encryption
    from config_system import get_config_system
except ImportError as e:
    print(f"ERROR: Missing required library: {e}")
    print("Install with: pip install selenium webdriver-manager beautifulsoup4 cryptography")
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
        self.cookies_file = 'mam_cookies.enc'
        self.legacy_cookies_file = 'mam_cookies.json'

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
        """Load saved cookies to restore session (Encrypted)"""
        cookies = None
        
        # Try loading encrypted cookies first
        if os.path.exists(self.cookies_file):
            try:
                config_sys = get_config_system()
                with open(self.cookies_file, 'r') as f:
                    encrypted_data = f.read()
                    
                json_data = config_sys.secret_manager.decrypt_secret(encrypted_data)
                cookies = json.loads(json_data)
                logger.info(f"Loaded {len(cookies)} encrypted cookies")
            except Exception as e:
                logger.warning(f"Could not load encrypted cookies: {e}")

        # Fallback to legacy plaintext cookies if no encrypted ones found
        if not cookies and os.path.exists(self.legacy_cookies_file):
            try:
                logger.info("Migrating legacy plaintext cookies to encrypted storage...")
                with open(self.legacy_cookies_file, 'r') as f:
                    cookies = json.load(f)
                # We will save them encrypted on next save
            except Exception as e:
                logger.warning(f"Could not load legacy cookies: {e}")

        if cookies:
            try:
                self.driver.get(self.base_url)
                self.anti_crawl.apply_random_delay(0.5, 1.5)

                for cookie in cookies:
                    try:
                        # Fix for domain mismatch if cookies are old or generic
                        if 'domain' in cookie:
                             # Ensure domain matches current base url domain or remove it to let selenium handle it
                             if 'myanonamouse.net' not in cookie['domain']:
                                 del cookie['domain']
                        
                        self.driver.add_cookie(cookie)
                    except Exception as e:
                        logger.debug(f"Could not add cookie {cookie.get('name')}: {e}")
                return True
            except Exception as e:
                logger.warning(f"Error applying cookies: {e}")

        return False

    def _save_cookies(self):
        """Save cookies for session recovery (Encrypted)"""
        try:
            cookies = self.driver.get_cookies()
            if not cookies:
                return

            config_sys = get_config_system()
            json_data = json.dumps(cookies)
            encrypted_data = config_sys.secret_manager.encrypt_secret(json_data)

            with open(self.cookies_file, 'w') as f:
                f.write(encrypted_data)
                
            logger.info(f"Saved {len(cookies)} encrypted cookies")
            
            # Secure delete legacy file if it exists
            if os.path.exists(self.legacy_cookies_file):
                try:
                    os.remove(self.legacy_cookies_file)
                    logger.info("Removed legacy plaintext cookie file")
                except OSError:
                    pass
                    
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
                try:
                    # Wait for logout link or some element that indicatesloggedIn state
                    logger.info("Waiting for login to complete...")
                    self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='logout.php'], .torTable"))
                    )
                except TimeoutException:
                    logger.warning("Login wait timed out, proceeding to check source...")

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

        return False

    def discover_top_books(self, limit: int = 10) -> List[Dict[str, str]]:
        """
        Discover top trending audiobooks on MAM.
        Navigates to the browse page, filters for audiobooks, sorts by activity.
        """
        print(f"STEP: Discovering Top {limit} Audiobooks")
        print("-" * 120)

        discovered = []
        try:
            if not self.driver:
                if not self.setup():
                    return []
            
            if not self.authenticated:
                if not self.login():
                    return []

            self.anti_crawl.check_rate_limit(2.0)
            
            # Browser URL for Top 10 Audiobooks (Cat 14=Audiobook)
            # sort=7 (Seeders), sort=2 (Date), sort=6 (Leechers)
            # We'll use sort=2 (Date) to see new stuff, or maybe sort by activity.
            # Let's try default browse with Audiobooks category selected.
            # Cat IDs: Audiobooks is typically around 13, 14, or mixed. 
            # Looking at search_mam it uses cat[]=13.
            browse_url = f"{self.base_url}/tor/browse.php?tor[cat][]=14&tor[sort]=seeders&tor[sr]=desc"
            
            logger.info(f"Navigating to: {browse_url}")
            logger.info(f"Navigating to: {browse_url}")
            self.driver.get(browse_url)
            
            # Wait for torrent table
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "torTable"))
                )
            except TimeoutException:
                logger.warning("Timeout waiting for Browse table")
                return []
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find torrent rows
            # Table usually has class 'torTable' or similar
            rows = soup.find_all('tr')
            count = 0
            
            for row in rows:
                if count >= limit:
                    break
                    
                # Find title link
                link = row.find('a', href=re.compile(r'^/t/\d+'))
                if link and not re.search(r'^/f/t/', link['href']):
                    full_title = link.get_text(strip=True)
                    
                    # Heuristic split for Title / Author
                    # MAM titles are often "Author - Title" or "Title - Author" or messy
                    # We'll try to guess.
                    # Common format: "Author - Series - Title" or "Author - Title"
                    
                    if ' - ' in full_title:
                        parts = full_title.split(' - ', 1)
                        author = parts[0].strip()
                        title = parts[1].strip()
                    else:
                        title = full_title
                        author = "Unknown"
                        
                    discovered.append({'title': title, 'author': author})
                    logger.info(f"   -> Found: {title} by {author}")
                    count += 1
            
            print(f"✓ Discovered {len(discovered)} books from Top list")
            return discovered

        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            return []

    def search_mam(self, search_term: str) -> Optional[Dict[str, Any]]:
        """Search MAM and extract best result using QualityFilter."""
        try:
            # Import QualityFilter and Categories here to avoid circular imports if any
            from mamcrawler.quality import QualityFilter
            from mamcrawler.mam_categories import MAMCategories
            
            quality_filter = QualityFilter()
            
            self.anti_crawl.check_rate_limit(2.0)
            self.anti_crawl.apply_random_delay(1.0, 3.0)

            # Use the search form by navigating to browse page first
            logger.info(f"Searching for: {search_term}")
            browse_url = f"{self.base_url}/tor/browse.php"

            # Navigate to browse page
            # Navigate to browse page
            self.driver.get(browse_url)
            
            # Wait for search input
            self.wait.until(EC.presence_of_element_located((By.ID, "ts")))

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
                    f"&tor[cat][]=13" # Force Audiobook category
                )
                self.driver.get(search_url)

            # Wait for results to load
            try:
                # Wait for either results table or "No results" message
                # This is tricky because if no results, we might just get a different page structure.
                # Assuming 'torTable' is present on results.
                self.wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "torTable"))
                )
            except TimeoutException:
                logger.warning("Timeout waiting for search results")
                # Proceed to check page source in case it's just empty
            
            page_source = self.driver.page_source

            # Check for login page
            if 'not logged in' in page_source.lower():
                logger.warning("Session lost, re-authenticating...")
                # Try to re-authenticate
                if self.login():
                    # Retry search
                    self.driver.get(search_url)
                    try:
                         self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "torTable")))
                         page_source = self.driver.page_source
                    except TimeoutException:
                         return None
                else:
                    return None

            # Parse HTML
            soup = BeautifulSoup(page_source, 'html.parser')

            # Look for torrent links
            # We will now score them instead of taking the first one
            candidates = []

            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                # Check if this is a torrent link (/t/\d+) and not a forum thread (/f/t/)
                if re.search(r'^/t/\d+', href) and not re.search(r'^/f/t/', href):
                    title = link.get_text(strip=True)
                    
                    # Basic metadata extraction (best effort without full table parsing)
                    # We assume title contains most info
                    release_data = {
                        'title': title,
                        'size_mb': 0, # Placeholder
                        'seeders': 0, # Placeholder
                        'leechers': 0 # Placeholder
                    }
                    
                    # Score the release
                    score = quality_filter.score_release(release_data)
                    
                    # Check if it passes basic quality checks (e.g. not abridged if we want unabridged)
                    # For now, we trust score_release to penalize bad ones
                    
                    candidates.append({
                        'link': link,
                        'score': score,
                        'title': title,
                        'url': href
                    })

            if not candidates:
                logger.info(f"No torrent links found")
                return None

            # Sort by score descending
            candidates.sort(key=lambda x: x['score'], reverse=True)
            
            best_candidate = candidates[0]
            logger.info(f"Selected best candidate: {best_candidate['title']} (Score: {best_candidate['score']})")
            
            first_link = best_candidate['link']
            result_title = best_candidate['title']
            torrent_url = best_candidate['url']

            if torrent_url.startswith('/'):
                torrent_url = urljoin(self.base_url, torrent_url)

            logger.info(f"Found torrent link: {torrent_url}")

            # Extract torrent ID
            match = re.search(r'/t/(\d+)', torrent_url)
            if not match:
                logger.warning(f"Could not extract torrent ID from {torrent_url}")
                return None

            torrent_id = match.group(1)
            
            # Get magnet link
            logger.info(f"Attempting to get magnet link for torrent {torrent_id}...")
            magnet = self._get_magnet_link(torrent_id)

            if magnet:
                return {
                    'title': result_title,
                    'url': torrent_url,
                    'magnet': magnet,
                    'torrent_id': torrent_id,
                    'score': best_candidate['score']
                }

            logger.warning(f"Failed to get magnet link for {torrent_id}")
            return None

        except Exception as e:
            logger.error(f"Search error: {e}")
            return None



    def _download_from_mam(self, download_url: str, output_file: str) -> bool:
        """Download file from MAM's proprietary download system using authenticated session"""
        try:
            import requests
            from requests.adapters import HTTPAdapter

            logger.info(f"Downloading from MAM: {download_url[:80]}...")

            # Get cookies from Selenium and use them with requests
            session = requests.Session()

            # Copy cookies from Selenium to requests session
            for cookie in self.driver.get_cookies():
                session.cookies.set(cookie['name'], cookie['value'])

            # Download the file
            response = session.get(download_url, timeout=300, stream=True)

            if response.status_code == 200:
                # Write file
                with open(output_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                file_size = os.path.getsize(output_file)
                logger.info(f"File downloaded successfully: {output_file} ({file_size:,} bytes)")
                return True
            else:
                logger.error(f"Download failed with status {response.status_code}: {response.text[:200]}")
                return False

        except Exception as e:
            logger.error(f"Error downloading from MAM: {e}")
            return False

    def _get_magnet_link(self, torrent_id: str) -> Optional[str]:
        """Extract magnet link or download URL from torrent page."""
        try:
            self.anti_crawl.apply_random_delay(0.5, 1.5)

            torrent_url = f"{self.base_url}/t/{torrent_id}"
            logger.debug(f"Fetching download link from {torrent_url}")

            self.driver.get(torrent_url)
            time.sleep(2)

            page_source = self.driver.page_source

            # Save for debugging
            with open(f'mam_torrent_{torrent_id}.html', 'w', encoding='utf-8') as f:
                f.write(page_source)

            # Try to find magnet link first
            magnet_match = re.search(r'(magnet:\?[^"<\s]+)', page_source)
            if magnet_match:
                magnet = magnet_match.group(1)
                logger.info(f"Found magnet for torrent {torrent_id}: {magnet[:80]}...")
                return magnet

            # If no magnet, try to find the direct download link from MAM
            download_match = re.search(r'href="(/tor/download\.php/[^"]+)"', page_source)
            if download_match:
                download_path = download_match.group(1)
                download_url = urljoin(self.base_url, download_path)
                logger.info(f"Found MAM download URL for torrent {torrent_id}: {download_url[:80]}...")
                # IMPORTANT: Return the URL marked as MAM-specific so caller knows to handle differently
                return f"MAM_AUTH:{download_url}"

            logger.warning(f"No magnet or download link found on torrent page {torrent_id}")
            return None

        except Exception as e:
            logger.error(f"Error getting download link for {torrent_id}: {e}")
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

    def get_user_stats(self) -> Optional[Dict[str, Any]]:
        """
        Fetch comprehensive user statistics from MAM.
        Retrieves: Ratio, Bonus Points, Upload/Download, Class, Seeding/Leeching, etc.
        Generates a shorthand status line for easy sharing/logging.
        """
        print("STEP: Fetching User Stats")
        print("-" * 120)
        
        try:
            # Ensure driver is initialized
            if not self.driver:
                if not self.setup():
                    return None

            if not self.authenticated:
                if not self.login():
                    return None
            
            # Navigate to User Details for detailed stats
            # We need to find the profile link first
            if "index.php" not in self.driver.current_url:
                self.driver.get(f"{self.base_url}/index.php")
                time.sleep(2)
                
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Try multiple ways to find profile link
            profile_link = soup.find('a', href=re.compile(r'userdetails\.php\?id=\d+'))
            
            # Fallback: Look for link with text matching username if we knew it, or just "Profile"
            if not profile_link:
                links = soup.find_all('a', href=True)
                for link in links:
                    if 'userdetails.php?id=' in link['href'] or '/u/' in link['href']:
                        # Check if /u/ is followed by digits
                        if '/u/' in link['href']:
                            match = re.search(r'/u/(\d+)', link['href'])
                            if match:
                                profile_link = link
                                break
                        else:
                            profile_link = link
                            break
            
            # Hard fallback for this specific user if dynamic detection fails
            if not profile_link:
                logger.warning("Could not find profile link dynamically. Trying known ID.")
                profile_url = f"{self.base_url}/u/229756"
            else:
                profile_url = urljoin(self.base_url, profile_link['href'])
            
            logger.info(f"Navigating to profile: {profile_url}")
            self.driver.get(profile_url)
            time.sleep(2)
            
            # Parse Profile Page
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            text_content = soup.get_text()
            
            stats = {
                'updated_at': datetime.now().isoformat(),
                'raw_data': {},
                'shorthand': ''
            }
            
            # 1. Extract ALL Data (Key-Value pairs from tables)
            # MAM profile tables usually have cells with labels and values
            for row in soup.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) >= 2:
                    # Try to identify key-value pairs
                    # Often the first col is label, second is value
                    key = cols[0].get_text(strip=True).replace(':', '')
                    val = cols[1].get_text(strip=True)
                    
                    # Filter out empty or extremely long text
                    if key and val and len(key) < 50 and len(val) < 200:
                        # Check if key is already present (avoid duplicates)
                        if key not in stats['raw_data']:
                            stats['raw_data'][key] = val
                            
            # 2. Extract Specific Fields for Shorthand
            def get_val(k):
                for rk, rv in stats['raw_data'].items():
                    if rk.lower() == k.lower():
                        return rv
                return None

            # Fields
            uploaded_str = get_val('Uploaded')
            downloaded_str = get_val('Downloaded')
            ratio_str = get_val('Share ratio')
            class_str = get_val('Class')
            sat_str = get_val('Satisfied')
            unsat_str = get_val('Unsatisfied')
            leech_str = get_val('Leeching')
            
            # Bonus Rate (from text)
            # "Last update had ... worth X per hour"
            bonus_rate_val = 0.0
            bonus_match = re.search(r'worth\s*([\d\.,]+)\s*per hour', text_content)
            if bonus_match:
                bonus_rate_val = float(bonus_match.group(1).replace(',', ''))
                stats['raw_data']['Bonus Rate'] = f"{bonus_rate_val} per hour"

            # 3. Calculate Shorthand
            try:
                # Helper for bytes conversion
                def parse_bytes(s):
                    if not s: return 0.0
                    # Remove "Real" prefix if present (though get_val should hit exact key, 
                    # but sometimes keys are "Real Uploaded")
                    # The user said ignore Real, so we used get_val('Uploaded') which should match "Uploaded" key
                    
                    # Parse "1.23 TiB"
                    match = re.search(r'([\d\.,]+)\s*([TGMK]i?B)', s)
                    if not match: return 0.0
                    
                    val = float(match.group(1).replace(',', ''))
                    unit = match.group(2)
                    
                    multipliers = {
                        'B': 1, 
                        'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4, 'PB': 1024**5,
                        'KiB': 1024, 'MiB': 1024**2, 'GiB': 1024**3, 'TiB': 1024**4, 'PiB': 1024**5
                    }
                    return val * multipliers.get(unit, 1)

                up_bytes = parse_bytes(uploaded_str)
                down_bytes = parse_bytes(downloaded_str)
                
                # Convert to Target Units (TB for Up, GB for Down)
                up_tb = up_bytes / (1024**4)
                down_gb = down_bytes / (1024**3)
                
                # Format Bonus
                if bonus_rate_val >= 1000:
                    bonus_str = f"{bonus_rate_val/1000:.2f}k/hr"
                else:
                    bonus_str = f"{bonus_rate_val:.2f}/hr"
                
                # Counts
                sat_count = sat_str if sat_str else "0"
                unsat_count = unsat_str if unsat_str else "0"
                leech_count = leech_str if leech_str else "0"
                
                # Ratio
                ratio_val = ratio_str.replace(',', '') if ratio_str else "0"
                
                # Construct Line
                # Up X TB | Dn X GB | Ratio X | Class | Bonus/hr | SatCount Sat | UnsatCount Unsat | LeechCount Leech
                shorthand = (
                    f"Up {up_tb:.2f} TB | "
                    f"Dn {down_gb:.2f} GB | "
                    f"Ratio {ratio_val} | "
                    f"{class_str} | "
                    f"{bonus_str} | "
                    f"{sat_count} Sat | "
                    f"{unsat_count} Unsat | "
                    f"{leech_count} Leech"
                )
                
                stats['shorthand'] = shorthand
                print(f"  ✓ Shorthand: {shorthand}")
                
                # Calculate Buffer
                buffer_bytes = up_bytes - down_bytes
                
                def format_bytes(b):
                    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
                        if abs(b) < 1024.0:
                            return f"{b:.2f} {unit}"
                        b /= 1024.0
                    return f"{b:.2f} PB"
                
                stats['buffer'] = format_bytes(buffer_bytes)
                
            except Exception as e:
                logger.error(f"Error calculating shorthand: {e}")
                stats['shorthand'] = "Error generating shorthand"

            # Populate main stats for UI compatibility
            stats['ratio'] = float(ratio_str.replace(',', '')) if ratio_str else 0.0
            stats['uploaded'] = uploaded_str
            stats['downloaded'] = downloaded_str
            stats['class'] = class_str
            stats['seeding'] = int(sat_str) if sat_str and sat_str.isdigit() else 0 # Approx
            stats['leeching'] = int(leech_str) if leech_str and leech_str.isdigit() else 0
            
            # Add Real Stats if available
            stats['real_uploaded'] = get_val('Real Uploaded')
            stats['real_downloaded'] = get_val('Real Downloaded')
            
            # Total Bonus Points
            bp_match = re.search(r'Bonus Points:\s*([\d\.,]+)', text_content)
            if bp_match:
                stats['bonus_points'] = float(bp_match.group(1).replace(',', ''))
            
            return stats
            
        except Exception as e:
            logger.error(f"Error fetching user stats: {e}")
            return None

    def run(self, books: List[Dict[str, str]]) -> bool:
        """Execute workflow."""
        try:
            if not self.setup():
                return False

            # Check if already authenticated with saved cookies
            if not self.authenticated:
                if not self.login():
                    return False
            
            # Fetch and display stats first (integration of mam-exporter features)
            self.get_user_stats()

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
