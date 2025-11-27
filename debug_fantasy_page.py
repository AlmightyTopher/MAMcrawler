#!/usr/bin/env python3
"""
Debug the fantasy page structure to understand what's actually there
"""

import logging
import os
import time
from datetime import datetime, timedelta
from mam_selenium_crawler import SeleniumMAMCrawler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    logger.info("="*80)
    logger.info("DEBUGGING FANTASY PAGE STRUCTURE")
    logger.info("="*80)

    try:
        # Initialize crawler
        logger.info("\nInitializing MAM crawler...")
        crawler = SeleniumMAMCrawler(
            email=os.getenv('MAM_USERNAME'),
            password=os.getenv('MAM_PASSWORD'),
            qb_url=f"{os.getenv('QB_HOST', 'http://localhost')}:{os.getenv('QB_PORT', '52095')}",
            qb_user=os.getenv('QB_USERNAME', 'TopherGutbrod'),
            qb_pass=os.getenv('QB_PASSWORD', ''),
            headless=False
        )

        if not crawler.setup():
            logger.error("Failed to setup crawler")
            return

        # Navigate to fantasy browse page (simpler, no date filter)
        logger.info("\nNavigating to fantasy browse page...")
        fantasy_url = "https://www.myanonamouse.net/tor/browse.php?tor[cat][]=41&tor[sortType]=snatchedDesc"

        crawler.driver.get(fantasy_url)
        time.sleep(4)

        # Get page source and save it
        page_source = crawler.driver.page_source

        with open("fantasy_page_debug.html", "w", encoding="utf-8") as f:
            f.write(page_source)

        logger.info("Saved page source to fantasy_page_debug.html")

        # Try different XPath selectors
        logger.info("\nTrying different XPath selectors:")

        from selenium.webdriver.common.by import By

        # Try 1: Original XPath
        try:
            rows = crawler.driver.find_elements(By.XPATH, "//tr[@class='torrent']")
            logger.info(f"XPath 1 (tr[@class='torrent']): Found {len(rows)} rows")
        except:
            logger.info("XPath 1 (tr[@class='torrent']): FAILED")

        # Try 2: Any tr with class containing torrent
        try:
            rows = crawler.driver.find_elements(By.XPATH, "//tr[contains(@class, 'torrent')]")
            logger.info(f"XPath 2 (tr[contains(@class, 'torrent')]): Found {len(rows)} rows")
        except:
            logger.info("XPath 2 (tr[contains(@class, 'torrent')]): FAILED")

        # Try 3: All tr elements
        try:
            rows = crawler.driver.find_elements(By.TAG_NAME, "tr")
            logger.info(f"XPath 3 (all tr): Found {len(rows)} rows")

            # Count rows with more than 3 cells (likely data rows)
            data_rows = 0
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) > 3:
                    data_rows += 1
            logger.info(f"  Data rows (>3 cells): {data_rows}")
        except:
            logger.info("XPath 3 (all tr): FAILED")

        # Try 4: Look for table structure
        try:
            tables = crawler.driver.find_elements(By.TAG_NAME, "table")
            logger.info(f"Tables found: {len(tables)}")

            for idx, table in enumerate(tables):
                try:
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    logger.info(f"  Table {idx}: {len(rows)} rows")
                except:
                    pass
        except:
            logger.info("XPath 4 (tables): FAILED")

        # Try 5: Look for specific elements with title
        try:
            title_links = crawler.driver.find_elements(By.XPATH, "//a[contains(@href, '/tor/')]")
            logger.info(f"Title links found: {len(title_links)}")

            if len(title_links) > 0:
                logger.info("First 5 title links:")
                for i, link in enumerate(title_links[:5]):
                    text = link.text.strip()
                    href = link.get_attribute('href')
                    logger.info(f"  {i+1}. {text[:60]}... -> {href}")
        except Exception as e:
            logger.info(f"XPath 5 (title links): FAILED - {e}")

        # Get current URL
        logger.info(f"\nCurrent URL: {crawler.driver.current_url}")

        # Check page title
        logger.info(f"Page title: {crawler.driver.title}")

        crawler.cleanup()

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
