#!/usr/bin/env python3
"""
qBittorrent Authentication Fix - Multiple Strategies

This script attempts to resolve qBittorrent 403 Forbidden errors by:
1. Using the proper QBittorrentClient with session persistence
2. Attempting browser-based login via Selenium
3. Checking and reporting IP whitelist/permission issues
4. Validating API credentials against multiple endpoints
"""

import os
import sys
import asyncio
import aiohttp
import json
from pathlib import Path
from dotenv import load_dotenv
import logging
from datetime import datetime

# Try to import Selenium for browser-based login
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("WARNING: Selenium not installed. Browser-based login unavailable.")

# Import the QBittorrentClient
sys.path.insert(0, str(Path(__file__).parent / 'backend' / 'integrations'))
try:
    from qbittorrent_client import QBittorrentClient, QBittorrentAuthError
    QBITTORRENT_CLIENT_AVAILABLE = True
except ImportError:
    QBITTORRENT_CLIENT_AVAILABLE = False
    print("WARNING: QBittorrentClient not available.")

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class QBittorrentAuthFix:
    """Multiple authentication strategies for qBittorrent"""

    def __init__(self):
        self.qb_url = os.getenv('QBITTORRENT_URL', 'http://192.168.0.48:52095/').rstrip('/')
        self.qb_user = os.getenv('QBITTORRENT_USERNAME', 'TopherGutbrod')
        self.qb_pass = os.getenv('QBITTORRENT_PASSWORD', 'Tesl@ismy#1')
        self.results = {}
        self.log_file = Path("qbittorrent_auth_fix.log")

    def log(self, message: str, level: str = "INFO"):
        """Log message"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] [{level:5}] {message}"
        print(formatted)
        with open(self.log_file, 'a') as f:
            f.write(formatted + "\n")

    # ========================================
    # STRATEGY 1: Using QBittorrentClient
    # ========================================

    async def test_qbittorrent_client(self) -> bool:
        """Test authentication using QBittorrentClient"""
        self.log("=" * 80)
        self.log("STRATEGY 1: QBittorrentClient (Async HTTP with Session Persistence)", "TEST")
        self.log("=" * 80)

        if not QBITTORRENT_CLIENT_AVAILABLE:
            self.log("QBittorrentClient not available - skipping this strategy", "WARN")
            return False

        try:
            async with QBittorrentClient(
                self.qb_url,
                self.qb_user,
                self.qb_pass,
                timeout=30
            ) as client:
                # Try to get server state to verify authentication
                try:
                    state = await client.get_server_state()
                    self.log(f"Successfully authenticated! Server state retrieved.", "OK")
                    self.log(f"  Download speed: {state.get('dl_info_speed', 0)} bytes/s", "OK")
                    self.log(f"  Upload speed: {state.get('up_info_speed', 0)} bytes/s", "OK")
                    self.log(f"  Connection status: {state.get('connection_status', 'unknown')}", "OK")
                    self.results['qbittorrent_client'] = True
                    return True

                except Exception as e:
                    self.log(f"Failed to get server state: {e}", "FAIL")
                    self.results['qbittorrent_client'] = False
                    return False

        except QBittorrentAuthError as e:
            self.log(f"Authentication failed: {e}", "FAIL")
            self.results['qbittorrent_client'] = False
            return False

        except Exception as e:
            self.log(f"Unexpected error: {e}", "FAIL")
            self.results['qbittorrent_client'] = False
            return False

    # ========================================
    # STRATEGY 2: Direct HTTP with Session
    # ========================================

    async def test_direct_http_session(self) -> bool:
        """Test direct HTTP with proper session persistence"""
        self.log("=" * 80)
        self.log("STRATEGY 2: Direct HTTP with Session Persistence", "TEST")
        self.log("=" * 80)

        try:
            connector = aiohttp.TCPConnector(ssl=False, limit=10)
            timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=15)

            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                # Step 1: Login with proper headers
                login_url = f'{self.qb_url}/api/v2/auth/login'
                login_data = aiohttp.FormData()
                login_data.add_field('username', self.qb_user)
                login_data.add_field('password', self.qb_pass)

                self.log(f"Logging in to {login_url}", "DEBUG")

                async with session.post(login_url, data=login_data, ssl=False) as resp:
                    login_text = await resp.text()
                    self.log(f"Login response: HTTP {resp.status} - {login_text[:100]}", "DEBUG")

                    if resp.status != 200:
                        self.log(f"Login failed: HTTP {resp.status}", "FAIL")
                        self.results['direct_http_session'] = False
                        return False

                    if login_text.strip() != 'Ok.':
                        self.log(f"Login response not 'Ok.': {login_text}", "FAIL")
                        self.results['direct_http_session'] = False
                        return False

                # Step 2: Try API call to verify session
                self.log("Verifying authentication with API call", "DEBUG")
                api_url = f'{self.qb_url}/api/v2/app/preferences'

                async with session.get(api_url, ssl=False) as resp:
                    if resp.status == 200:
                        prefs = await resp.json()
                        self.log(f"Successfully retrieved preferences", "OK")
                        self.log(f"  Save path: {prefs.get('save_path', 'N/A')}", "OK")
                        self.log(f"  DHT enabled: {prefs.get('dht', False)}", "OK")
                        self.results['direct_http_session'] = True
                        return True
                    else:
                        self.log(f"API call failed: HTTP {resp.status}", "FAIL")
                        self.results['direct_http_session'] = False
                        return False

        except Exception as e:
            self.log(f"Connection error: {e}", "FAIL")
            self.results['direct_http_session'] = False
            return False

    # ========================================
    # STRATEGY 3: Selenium Browser-Based Login
    # ========================================

    def test_selenium_browser_login(self) -> bool:
        """Test browser-based login using Selenium"""
        self.log("=" * 80)
        self.log("STRATEGY 3: Selenium Browser-Based Login", "TEST")
        self.log("=" * 80)

        if not SELENIUM_AVAILABLE:
            self.log("Selenium not installed - skipping browser login", "WARN")
            self.results['selenium_browser'] = False
            return False

        driver = None
        try:
            # Setup Chrome options
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            # Uncomment to run headless:
            # chrome_options.add_argument("--headless")

            self.log(f"Opening browser to {self.qb_url}", "DEBUG")

            # Launch browser
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(self.qb_url)

            # Wait for login form
            self.log("Waiting for login form...", "DEBUG")
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )

            # Fill in credentials
            self.log(f"Entering credentials for user: {self.qb_user}", "DEBUG")
            username_field = driver.find_element(By.NAME, "username")
            password_field = driver.find_element(By.NAME, "password")
            login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")

            username_field.send_keys(self.qb_user)
            password_field.send_keys(self.qb_pass)
            login_button.click()

            # Wait for successful login (page should load)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "mainwindow"))
            )

            self.log("Successfully logged in via browser!", "OK")
            self.log("  qBittorrent Web UI is accessible", "OK")
            self.log("  Credentials are correct", "OK")
            self.log("  IP whitelisting (if any) allows browser access", "OK")

            # Get page title
            title = driver.title
            self.log(f"  Page title: {title}", "OK")

            self.results['selenium_browser'] = True
            return True

        except Exception as e:
            self.log(f"Browser login failed: {e}", "FAIL")
            self.results['selenium_browser'] = False
            return False

        finally:
            if driver:
                driver.quit()

    # ========================================
    # STRATEGY 4: Prowlarr Indexer (Indirect)
    # ========================================

    async def test_prowlarr_indexer(self) -> bool:
        """Test if we can use Prowlarr to add to qBittorrent"""
        self.log("=" * 80)
        self.log("STRATEGY 4: Prowlarr Indexer Integration", "TEST")
        self.log("=" * 80)

        try:
            prowlarr_url = os.getenv('PROWLARR_URL', 'http://localhost:9696')
            prowlarr_key = os.getenv('PROWLARR_API_KEY')

            if not prowlarr_key:
                self.log("Prowlarr API key not configured", "WARN")
                self.results['prowlarr_indexer'] = False
                return False

            # Test Prowlarr health
            self.log(f"Testing Prowlarr at {prowlarr_url}", "DEBUG")

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{prowlarr_url}/api/v1/health",
                    headers={"X-Api-Key": prowlarr_key},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        health = await resp.json()
                        self.log(f"Prowlarr health check passed", "OK")
                        self.log(f"  Status: {health.get('status', 'ok')}", "OK")
                        self.results['prowlarr_indexer'] = True
                        return True
                    else:
                        self.log(f"Prowlarr health check failed: HTTP {resp.status}", "FAIL")
                        self.results['prowlarr_indexer'] = False
                        return False

        except Exception as e:
            self.log(f"Prowlarr test failed: {e}", "FAIL")
            self.results['prowlarr_indexer'] = False
            return False

    # ========================================
    # DIAGNOSTICS & REPORTING
    # ========================================

    async def diagnose_connectivity(self) -> None:
        """Test basic connectivity to qBittorrent"""
        self.log("=" * 80)
        self.log("CONNECTIVITY DIAGNOSTICS", "DIAG")
        self.log("=" * 80)

        try:
            async with aiohttp.ClientSession() as session:
                # Test 1: Basic connectivity
                self.log(f"Testing basic connectivity to {self.qb_url}...", "DEBUG")
                async with session.head(self.qb_url, ssl=False, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    self.log(f"  HTTP {resp.status} - Server is responding", "OK")

                # Test 2: API endpoint
                api_url = f'{self.qb_url}/api/v2/app/version'
                self.log(f"Testing API endpoint...", "DEBUG")
                async with session.get(api_url, ssl=False, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    self.log(f"  HTTP {resp.status}", "OK")
                    version = await resp.text()
                    self.log(f"  qBittorrent version: {version}", "OK")

        except Exception as e:
            self.log(f"Connectivity test failed: {e}", "FAIL")

    def diagnose_ip_whitelist(self) -> None:
        """Check if IP whitelisting might be the issue"""
        self.log("=" * 80)
        self.log("IP WHITELIST DIAGNOSTICS", "DIAG")
        self.log("=" * 80)

        self.log("403 Forbidden errors typically indicate one of:", "INFO")
        self.log("  1. IP is not in qBittorrent whitelist", "INFO")
        self.log("  2. API access disabled for this user", "INFO")
        self.log("  3. API session/token expired", "INFO")
        self.log("  4. CORS restrictions (if remote qBittorrent)", "INFO")
        self.log("", "INFO")
        self.log("To fix:", "INFO")
        self.log("  1. Open qBittorrent Web UI: http://192.168.0.48:52095/", "INFO")
        self.log("  2. Go to Tools > Options > Web UI", "INFO")
        self.log("  3. Check 'Enable Web User Interface'", "INFO")
        self.log("  4. Look for 'IP whitelist' or 'Bypass authentication' settings", "INFO")
        self.log("  5. Verify user 'TopherGutbrod' has API access enabled", "INFO")

    async def run_all_tests(self) -> None:
        """Run all authentication strategies"""
        self.log("")
        self.log("=" * 100)
        self.log("qBITTORRENT AUTHENTICATION FIX - MULTIPLE STRATEGIES")
        self.log("=" * 100)
        self.log("")

        # Diagnostics first
        await self.diagnose_connectivity()
        self.diagnose_ip_whitelist()

        # Test strategies
        test_results = {}

        # Strategy 1: QBittorrentClient
        if QBITTORRENT_CLIENT_AVAILABLE:
            test_results['QBittorrentClient'] = await self.test_qbittorrent_client()
        else:
            self.log("QBittorrentClient not available", "WARN")

        # Strategy 2: Direct HTTP
        test_results['Direct HTTP Session'] = await self.test_direct_http_session()

        # Strategy 3: Selenium (non-async, run after async tests)
        if SELENIUM_AVAILABLE:
            test_results['Selenium Browser'] = self.test_selenium_browser_login()
        else:
            self.log("Selenium not available", "WARN")

        # Strategy 4: Prowlarr
        test_results['Prowlarr Indexer'] = await self.test_prowlarr_indexer()

        # Summary
        self.log("")
        self.log("=" * 100)
        self.log("SUMMARY", "SUMMARY")
        self.log("=" * 100)
        for strategy, result in test_results.items():
            status = "SUCCESS" if result else "FAILED"
            self.log(f"  {strategy}: {status}", "SUMMARY")

        # Recommendations
        self.log("")
        self.log("NEXT STEPS:", "SUMMARY")
        if any(test_results.values()):
            self.log("  One or more authentication methods succeeded!", "OK")
            self.log("  Update execute_full_workflow.py to use the working method", "OK")
        else:
            self.log("  All authentication methods failed - see diagnostics above", "FAIL")
            self.log("  Most likely: IP whitelist issue in qBittorrent settings", "FAIL")
            self.log("  Try opening qBittorrent Web UI and adjusting security settings", "FAIL")

        # Save results
        with open('qbittorrent_auth_results.json', 'w') as f:
            json.dump(test_results, f, indent=2)
        self.log("")
        self.log(f"Results saved to: qbittorrent_auth_results.json", "OK")


async def main():
    fixer = QBittorrentAuthFix()
    await fixer.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
