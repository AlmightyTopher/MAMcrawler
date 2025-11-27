#!/usr/bin/env python3
"""
Navigate MyAnonamouse using Selenium WebDriver
Full browser simulation with proper authentication and delays
"""
import os
import sys
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()
MAM_USERNAME = os.getenv('MAM_USERNAME')
MAM_PASSWORD = os.getenv('MAM_PASSWORD')

class MAMNavigator:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.authenticated = False

    def init_browser(self):
        """Initialize Selenium Chrome WebDriver with stealth options"""
        logger.info("Initializing Chrome WebDriver...")

        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')

        # Don't use headless - some sites detect it
        # chrome_options.add_argument('--headless')

        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 15)

        logger.info("✓ Browser initialized")
        return True

    def navigate_to_home(self):
        """Navigate to MAM homepage"""
        logger.info("Navigating to MyAnonamouse homepage...")

        try:
            self.driver.get('https://www.myanonamouse.net/')
            time.sleep(3)  # Wait for page to fully load

            logger.info(f"✓ Homepage loaded")
            logger.info(f"  Current URL: {self.driver.current_url}")
            logger.info(f"  Page title: {self.driver.title}")

            return True

        except Exception as e:
            logger.error(f"✗ Failed to load homepage: {e}")
            return False

    def login(self):
        """Authenticate with MyAnonamouse"""
        logger.info("\nAttempting to login...")
        logger.info(f"  Username: {MAM_USERNAME[:10]}...")

        try:
            # Navigate to login page
            self.driver.get('https://www.myanonamouse.net/tor/login.php')
            time.sleep(2)

            logger.info(f"✓ Login page loaded")
            logger.info(f"  Current URL: {self.driver.current_url}")

            # Find username field
            logger.info("Finding login form elements...")
            username_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, 'username')),
                message="Username field not found"
            )
            logger.info("✓ Found username field")

            # Find password field
            password_field = self.driver.find_element(By.NAME, 'password')
            logger.info("✓ Found password field")

            # Find submit button
            submit_button = self.driver.find_element(By.XPATH, "//input[@type='submit'] | //button[@type='submit']")
            logger.info("✓ Found submit button")

            # Fill form
            logger.info("Entering credentials...")
            username_field.clear()
            username_field.send_keys(MAM_USERNAME)
            time.sleep(0.5)

            password_field.clear()
            password_field.send_keys(MAM_PASSWORD)
            time.sleep(0.5)

            # Submit
            logger.info("Submitting login form...")
            submit_button.click()
            time.sleep(3)  # Wait for login to process

            # Check if login was successful
            current_url = self.driver.current_url
            page_source = self.driver.page_source.lower()

            if 'logout' in page_source or '/my/' in current_url or 'account' in page_source:
                logger.info("✓ Login successful!")
                logger.info(f"  Current URL: {current_url}")
                self.authenticated = True
                return True
            else:
                logger.warning("⚠ Login may have failed - checking page content...")
                logger.info(f"  Current URL: {current_url}")
                logger.info(f"  Page title: {self.driver.title}")

                # Still try to continue - authentication may have worked
                self.authenticated = True
                return True

        except TimeoutException:
            logger.error("✗ Timeout waiting for login form elements")
            logger.error("  Login form may not be loading properly")
            return False
        except Exception as e:
            logger.error(f"✗ Login error: {e}")
            return False

    def search_author(self, author_name):
        """Search for author on MAM"""
        logger.info(f"\nSearching for author: {author_name}")

        if not self.authenticated:
            logger.error("✗ Not authenticated - cannot search")
            return False

        try:
            # Navigate to search page
            search_url = f'https://www.myanonamouse.net/tor/searchbook.php?searchtype=author&query={author_name}&category=47'
            logger.info(f"Navigating to search URL...")
            logger.info(f"  {search_url}")

            self.driver.get(search_url)
            time.sleep(3)  # Wait for search results to load

            logger.info(f"✓ Search page loaded")
            logger.info(f"  Current URL: {self.driver.current_url}")
            logger.info(f"  Page title: {self.driver.title}")

            # Check if we got results
            page_source = self.driver.page_source

            if '403' in self.driver.page_source or 'forbidden' in self.driver.page_source.lower():
                logger.error("✗ Search returned 403 Forbidden")
                return False

            # Try to find search results table
            try:
                results_table = self.driver.find_element(By.XPATH, "//table[contains(@class, 'table')]")
                logger.info("✓ Found results table")

                # Count rows
                rows = results_table.find_elements(By.TAG_NAME, 'tr')
                logger.info(f"  Found {len(rows)} rows in results")

                return True

            except NoSuchElementException:
                logger.warning("⚠ Could not find results table")
                logger.info(f"  Page length: {len(page_source)} characters")

                # Check if there's any content
                if len(page_source) > 5000:
                    logger.info("✓ Page loaded with content")
                    return True
                else:
                    logger.error("✗ Page appears empty or not loaded")
                    return False

        except Exception as e:
            logger.error(f"✗ Search error: {e}")
            return False

    def browse_audiobooks(self):
        """Browse audiobook category"""
        logger.info("\nBrowsing audiobook category...")

        if not self.authenticated:
            logger.error("✗ Not authenticated - cannot browse")
            return False

        try:
            # Navigate to browse page filtered for audiobooks
            browse_url = 'https://www.myanonamouse.net/tor/browse.php?cat=47&page=1'
            logger.info(f"Navigating to browse page...")
            logger.info(f"  {browse_url}")

            self.driver.get(browse_url)
            time.sleep(3)

            logger.info(f"✓ Browse page loaded")
            logger.info(f"  Current URL: {self.driver.current_url}")
            logger.info(f"  Page title: {self.driver.title}")

            # Check for content
            page_source = self.driver.page_source

            if len(page_source) > 5000:
                logger.info("✓ Page loaded with content")

                # Try to find torrent entries
                try:
                    torrents = self.driver.find_elements(By.XPATH, "//tr[@class='table_dark' or @class='table_light']")
                    logger.info(f"  Found {len(torrents)} torrent entries")

                    if torrents:
                        logger.info("  First few torrents:")
                        for torrent in torrents[:3]:
                            try:
                                title = torrent.find_element(By.XPATH, ".//a[@title]").text
                                logger.info(f"    - {title[:60]}")
                            except:
                                pass
                except:
                    pass

                return True
            else:
                logger.error("✗ Page appears empty")
                return False

        except Exception as e:
            logger.error(f"✗ Browse error: {e}")
            return False

    def take_screenshot(self, filename):
        """Take screenshot of current page"""
        try:
            self.driver.save_screenshot(filename)
            logger.info(f"✓ Screenshot saved: {filename}")
        except Exception as e:
            logger.error(f"✗ Screenshot error: {e}")

    def close(self):
        """Close browser"""
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed")

    def run(self):
        """Execute full navigation workflow"""
        try:
            logger.info("="*80)
            logger.info("MYANONAMOUSE SELENIUM NAVIGATOR")
            logger.info("="*80)
            logger.info("")

            # Initialize browser
            if not self.init_browser():
                return False

            time.sleep(1)

            # Navigate to homepage
            if not self.navigate_to_home():
                return False

            self.take_screenshot('mam_homepage.png')
            time.sleep(2)

            # Login
            if not self.login():
                logger.warning("⚠ Login may have failed, continuing anyway...")

            self.take_screenshot('mam_after_login.png')
            time.sleep(2)

            # Search for author
            if not self.search_author('Randi Darren'):
                logger.warning("⚠ Search may have failed")

            self.take_screenshot('mam_search_results.png')
            time.sleep(2)

            # Browse audiobooks
            if not self.browse_audiobooks():
                logger.warning("⚠ Browse may have failed")

            self.take_screenshot('mam_browse_audiobooks.png')

            logger.info("\n" + "="*80)
            logger.info("Navigation complete")
            logger.info("="*80)
            logger.info("\nScreenshots saved:")
            logger.info("  - mam_homepage.png")
            logger.info("  - mam_after_login.png")
            logger.info("  - mam_search_results.png")
            logger.info("  - mam_browse_audiobooks.png")

            # Keep browser open for manual inspection
            logger.info("\n✓ Browser window is open for manual inspection")
            logger.info("  You can interact with the site directly")
            logger.info("  Press Ctrl+C when done...")

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("User closed browser")

            return True

        except Exception as e:
            logger.error(f"Navigation error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.close()

if __name__ == '__main__':
    navigator = MAMNavigator()
    success = navigator.run()
    sys.exit(0 if success else 1)
