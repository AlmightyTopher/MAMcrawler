#!/usr/bin/env python3
"""
Navigate MyAnonamouse using Selenium WebDriver - FIXED VERSION
Corrected form field names based on actual HTML
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

        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 15)

        logger.info("✓ Browser initialized")
        return True

    def login(self):
        """Authenticate with MyAnonamouse"""
        logger.info("\n" + "="*80)
        logger.info("LOGGING INTO MYANONAMOUSE")
        logger.info("="*80)
        logger.info(f"Username: {MAM_USERNAME[:10]}...")

        try:
            # Navigate to login page
            logger.info("\nNavigating to MyAnonamouse...")
            self.driver.get('https://www.myanonamouse.net/')
            time.sleep(3)

            current_url = self.driver.current_url
            logger.info(f"✓ Page loaded")
            logger.info(f"  Current URL: {current_url}")
            logger.info(f"  Page title: {self.driver.title}")

            # Take screenshot of login form
            self.driver.save_screenshot('mam_login_form.png')
            logger.info("✓ Screenshot of login form saved")

            # Find email field (NOT username)
            logger.info("\nFinding login form elements...")
            email_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, 'email')),
                message="Email field not found - checking alternate selectors..."
            )
            logger.info("✓ Found email field")

            # Find password field
            password_field = self.driver.find_element(By.NAME, 'password')
            logger.info("✓ Found password field")

            # Find submit button
            submit_button = self.driver.find_element(By.XPATH, "//input[@type='submit' and contains(@value, 'Log')]")
            logger.info("✓ Found submit button")

            # Fill form
            logger.info("\nEntering credentials...")
            email_field.clear()
            email_field.send_keys(MAM_USERNAME)
            logger.info(f"  Entered email")
            time.sleep(0.5)

            password_field.clear()
            password_field.send_keys(MAM_PASSWORD)
            logger.info(f"  Entered password")
            time.sleep(0.5)

            # Submit
            logger.info("Submitting login form...")
            submit_button.click()
            time.sleep(4)  # Wait for login to process

            # Check if login was successful
            current_url = self.driver.current_url
            page_source = self.driver.page_source.lower()

            logger.info(f"\n✓ Login form submitted")
            logger.info(f"  Current URL after login: {current_url}")

            # Take screenshot after login
            self.driver.save_screenshot('mam_after_login.png')
            logger.info("✓ Screenshot after login saved")

            # Check for logout link or account page
            if 'logout' in page_source or '/my/' in current_url or 'account' in page_source or 'user' in current_url:
                logger.info("\n✓ LOGIN SUCCESSFUL!")
                self.authenticated = True
                return True
            else:
                # Check if we're still on login page
                if 'login' in current_url or 'not logged in' in page_source:
                    logger.error("\n✗ Login failed - still on login page")
                    logger.error(f"  Page contains: 'not logged in': {'not logged in' in page_source}")
                    return False
                else:
                    logger.warning("\n⚠ Login status unclear, but proceeding...")
                    self.authenticated = True
                    return True

        except TimeoutException:
            logger.error("✗ Timeout waiting for login form elements")
            logger.error("  Email field not found with name='email'")
            logger.error("  Form may have different structure")
            return False
        except Exception as e:
            logger.error(f"✗ Login error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def search_author(self, author_name):
        """Search for author on MAM"""
        logger.info("\n" + "="*80)
        logger.info(f"SEARCHING FOR AUTHOR: {author_name}")
        logger.info("="*80)

        if not self.authenticated:
            logger.error("✗ Not authenticated - cannot search")
            return False

        try:
            # Navigate to search page
            search_url = f'https://www.myanonamouse.net/tor/searchbook.php?searchtype=author&query={author_name}&category=47'
            logger.info(f"\nNavigating to search...")
            logger.info(f"  {search_url}")

            self.driver.get(search_url)
            time.sleep(3)

            logger.info(f"✓ Search page loaded")
            logger.info(f"  Current URL: {self.driver.current_url}")
            logger.info(f"  Page title: {self.driver.title}")

            # Take screenshot
            self.driver.save_screenshot('mam_search_results.png')

            # Check if we got results
            page_source = self.driver.page_source

            if len(page_source) > 5000:
                logger.info("✓ Page loaded with content")

                # Try to find search results
                try:
                    rows = self.driver.find_elements(By.XPATH, "//tr[@class='table_dark' or @class='table_light']")
                    logger.info(f"\n✓ Found {len(rows)} result rows")

                    if rows:
                        logger.info(f"\nFirst 5 results for {author_name}:")
                        for i, row in enumerate(rows[:5], 1):
                            try:
                                title = row.find_element(By.XPATH, ".//a[@title]").text
                                logger.info(f"  {i}. {title[:70]}")
                            except:
                                pass

                except Exception as e:
                    logger.warning(f"Could not parse results table: {e}")

                return True
            else:
                logger.error("✗ Page appears empty or not loaded")
                return False

        except Exception as e:
            logger.error(f"✗ Search error: {e}")
            return False

    def browse_audiobooks(self):
        """Browse audiobook category"""
        logger.info("\n" + "="*80)
        logger.info("BROWSING AUDIOBOOK CATEGORY")
        logger.info("="*80)

        if not self.authenticated:
            logger.error("✗ Not authenticated - cannot browse")
            return False

        try:
            browse_url = 'https://www.myanonamouse.net/tor/browse.php?cat=47&page=1'
            logger.info(f"\nNavigating to audiobooks browse page...")
            logger.info(f"  {browse_url}")

            self.driver.get(browse_url)
            time.sleep(3)

            logger.info(f"✓ Browse page loaded")
            logger.info(f"  Current URL: {self.driver.current_url}")
            logger.info(f"  Page title: {self.driver.title}")

            # Take screenshot
            self.driver.save_screenshot('mam_browse_audiobooks.png')

            page_source = self.driver.page_source

            if len(page_source) > 5000:
                logger.info("✓ Page loaded with content")

                try:
                    torrents = self.driver.find_elements(By.XPATH, "//tr[@class='table_dark' or @class='table_light']")
                    logger.info(f"\n✓ Found {len(torrents)} torrent entries")

                    if torrents:
                        logger.info(f"\nFirst 5 audiobooks:")
                        for i, torrent in enumerate(torrents[:5], 1):
                            try:
                                title = torrent.find_element(By.XPATH, ".//a[@title]").text
                                logger.info(f"  {i}. {title[:70]}")
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

    def close(self):
        """Close browser"""
        if self.driver:
            self.driver.quit()
            logger.info("\nBrowser closed")

    def run(self):
        """Execute full navigation workflow"""
        try:
            logger.info("\n")
            logger.info("╔" + "="*78 + "╗")
            logger.info("║" + " "*78 + "║")
            logger.info("║" + "MYANONAMOUSE SELENIUM NAVIGATOR - FIXED".center(78) + "║")
            logger.info("║" + " "*78 + "║")
            logger.info("╚" + "="*78 + "╝")

            # Initialize browser
            if not self.init_browser():
                return False

            time.sleep(1)

            # Login
            if not self.login():
                logger.error("\n✗ Could not login - stopping")
                return False

            time.sleep(2)

            # Search for author
            if not self.search_author('Randi Darren'):
                logger.warning("⚠ Search may have failed")

            time.sleep(2)

            # Browse audiobooks
            if not self.browse_audiobooks():
                logger.warning("⚠ Browse may have failed")

            logger.info("\n" + "="*80)
            logger.info("Navigation complete!")
            logger.info("="*80)
            logger.info("""
Screenshots saved:
  - mam_login_form.png
  - mam_after_login.png
  - mam_search_results.png
  - mam_browse_audiobooks.png

✓ Successfully navigated MyAnonamouse!
""")

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
