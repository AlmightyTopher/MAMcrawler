#!/usr/bin/env python3
"""
Get top 10 fantasy audiobooks from last week - FIXED VERSION
Forces fresh login instead of using stale cookies
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


def login_fresh(driver) -> bool:
    """Fresh login - bypass any stale cookies"""
    try:
        logger.info("Performing fresh login to MAM...")

        # Clear all cookies first
        driver.delete_all_cookies()
        time.sleep(1)

        # Navigate to login
        driver.get("https://www.myanonamouse.net/login.php")
        time.sleep(2)

        # Find and fill form
        wait = WebDriverWait(driver, 10)
        email_field = wait.until(EC.presence_of_element_located((By.NAME, "email")))
        password_field = driver.find_element(By.NAME, "password")

        email = os.getenv('MAM_USERNAME')
        password = os.getenv('MAM_PASSWORD')

        logger.info(f"Logging in as: {email}")

        email_field.clear()
        email_field.send_keys(email)
        password_field.clear()
        password_field.send_keys(password)

        # Find and click login button
        submit_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]")
        submit_btn.click()

        logger.info("Login form submitted, waiting for redirect...")
        time.sleep(6)

        # Verify login
        current_url = driver.current_url
        logger.info(f"Current URL: {current_url}")

        if "login" in current_url.lower():
            logger.error("Still on login page - login failed!")
            return False

        logger.info("✓ Successfully logged in")
        return True

    except Exception as e:
        logger.error(f"Login error: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_fantasy_books(driver) -> list:
    """Extract fantasy books from page"""
    results = []

    try:
        logger.info("\nExtracting results...")

        # Wait for page content
        wait = WebDriverWait(driver, 10)
        time.sleep(2)

        # Try to find title links (all audio books have these)
        title_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/tor/')]")
        logger.info(f"Found {len(title_links)} title links on page")

        # Extract first 10
        for idx, link in enumerate(title_links[:10]):
            try:
                title = link.text.strip()
                href = link.get_attribute('href')

                if not href.startswith('http'):
                    href = "https://www.myanonamouse.net" + href

                results.append({
                    'position': idx + 1,
                    'title': title,
                    'link': href
                })

                logger.info(f"[{idx+1}] {title}")

            except Exception as e:
                logger.warning(f"Error extracting link {idx}: {e}")
                continue

        return results

    except Exception as e:
        logger.error(f"Error extracting results: {e}")
        return []


def main():
    logger.info("="*80)
    logger.info("TOP 10 FANTASY AUDIOBOOKS - LAST WEEK (FIXED)")
    logger.info("="*80)

    # Initialize driver
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    try:
        # Fresh login
        if not login_fresh(driver):
            logger.error("Failed to login")
            return

        # Calculate dates
        today = datetime.now()
        start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

        logger.info(f"\nDate range: {start_date} to {end_date}")

        # Build URL for fantasy category, sorted by popularity
        search_url = (
            f"https://www.myanonamouse.net/tor/browse.php?"
            f"&tor[srchIn][title]=true"
            f"&tor[srchIn][author]=true"
            f"&tor[srchIn][narrator]=true"
            f"&tor[searchType]=all"
            f"&tor[searchIn]=torrents&tor[cat][]=41"  # Fantasy
            f"&tor[browse_lang][]=1"
            f"&tor[browseFlagsHideVsShow]=0"
            f"&tor[startDate]={start_date}"
            f"&tor[endDate]={end_date}"
            f"&tor[sortType]=snatchedDesc"
            f"&tor[startNumber]=0"
            f"&thumbnail=true"
        )

        logger.info(f"\nNavigating to fantasy search...")
        driver.get(search_url)
        time.sleep(5)

        # Check if we're still logged in
        current_url = driver.current_url
        if "login" in current_url.lower():
            logger.error("Session expired! Redirected to login")
            return

        # Extract results
        results = get_fantasy_books(driver)

        logger.info("\n" + "="*80)
        logger.info("RESULTS")
        logger.info("="*80)

        if results:
            for result in results:
                print(f"\n{result['position']}. {result['title']}")
                print(f"   {result['link']}")

            logger.info(f"\n✓ Found {len(results)} fantasy audiobooks")
        else:
            logger.warning("No fantasy audiobooks found")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        logger.info("\nClosing browser...")
        driver.quit()


if __name__ == "__main__":
    main()
