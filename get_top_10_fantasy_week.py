#!/usr/bin/env python3
"""
Get top 10 fantasy audiobooks from the last week
Uses Mode A: Time/Genre search with date range
"""

import logging
import os
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TopFantasyWeek:
    def __init__(self):
        self.mam_username = os.getenv('MAM_USERNAME')
        self.mam_password = os.getenv('MAM_PASSWORD')
        self.driver = None

    def initialize_driver(self) -> bool:
        """Initialize Selenium WebDriver"""
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            logger.info("WebDriver initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            return False

    def login_mam(self) -> bool:
        """Login to MyAnonamouse"""
        try:
            logger.info("Logging into MyAnonamouse...")
            self.driver.get("https://www.myanonamouse.net/login.php")
            wait = WebDriverWait(self.driver, 10)

            email_field = wait.until(EC.presence_of_element_located((By.NAME, "email")))
            password_field = self.driver.find_element(By.NAME, "password")

            email_field.clear()
            email_field.send_keys(self.mam_username)
            password_field.clear()
            password_field.send_keys(self.mam_password)

            submit_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]")
            submit_btn.click()

            time.sleep(5)
            if "login" not in self.driver.current_url.lower():
                logger.info("✓ Logged into MAM")
                return True
            else:
                logger.error("Login failed")
                return False
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    def get_top_10_fantasy(self) -> list:
        """Get top 10 fantasy audiobooks from last week"""
        # Calculate dates
        today = datetime.now()
        start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

        logger.info(f"\nSearch period: {start_date} to {end_date}")

        # Build search URL
        base_url = "https://www.myanonamouse.net/tor/browse.php"
        search_url = (
            f"{base_url}?"
            f"&tor[srchIn][title]=true"
            f"&tor[srchIn][author]=true"
            f"&tor[srchIn][narrator]=true"
            f"&tor[searchType]=all"
            f"&tor[searchIn]=torrents&tor[cat][]=41"  # Fantasy category
            f"&tor[browse_lang][]=1"
            f"&tor[browseFlagsHideVsShow]=0"
            f"&tor[startDate]={start_date}"
            f"&tor[endDate]={end_date}"
            f"&tor[sortType]=snatchedDesc"  # Sort by most snatched
            f"&tor[startNumber]=0"
            f"&thumbnail=true"
        )

        logger.info(f"\nNavigating to search URL...")
        self.driver.get(search_url)
        time.sleep(4)

        results = []
        try:
            wait = WebDriverWait(self.driver, 10)

            # Try to find torrent rows
            torrent_rows = wait.until(
                EC.presence_of_all_elements_located((By.XPATH, "//tr[@class='torrent']"))
            )

            logger.info(f"Found {len(torrent_rows)} results")

            for idx, row in enumerate(torrent_rows[:10]):
                try:
                    # Extract title and link
                    title_elem = row.find_element(By.XPATH, ".//a[contains(@href, '/tor/')]")
                    title = title_elem.text.strip()
                    link = title_elem.get_attribute('href')

                    # Make absolute URL
                    if link.startswith('/'):
                        link = "https://www.myanonamouse.net" + link

                    # Extract date from table cells
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    upload_date = "N/A"

                    # Date is typically in one of the cells
                    for cell in cells[-3:]:  # Check last 3 cells
                        cell_text = cell.text.strip()
                        if cell_text and any(c.isdigit() for c in cell_text):
                            upload_date = cell_text
                            break

                    results.append({
                        'position': idx + 1,
                        'title': title,
                        'link': link,
                        'upload_date': upload_date
                    })

                    logger.info(f"\n[{idx+1}] {title}")
                    logger.info(f"    Upload date: {upload_date}")
                    logger.info(f"    Link: {link}")

                except Exception as e:
                    logger.warning(f"Error extracting row {idx}: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Error finding results: {e}")
            return []

    def run(self):
        """Main execution"""
        logger.info("="*80)
        logger.info("TOP 10 FANTASY AUDIOBOOKS - LAST WEEK")
        logger.info("="*80)

        try:
            if not self.initialize_driver():
                return

            if not self.login_mam():
                return

            results = self.get_top_10_fantasy()

            if results:
                logger.info("\n" + "="*80)
                logger.info("RESULTS")
                logger.info("="*80)
                for result in results:
                    print(f"\n{result['position']}. {result['title']}")
                    print(f"   {result['link']}")
                    print(f"   Uploaded: {result['upload_date']}")
            else:
                logger.warning("No fantasy audiobooks found in the last week")

        except Exception as e:
            logger.error(f"Fatal error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            if self.driver:
                logger.info("\nClosing browser...")
                self.driver.quit()


if __name__ == "__main__":
    finder = TopFantasyWeek()
    finder.run()
