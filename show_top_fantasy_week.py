#!/usr/bin/env python3
"""
Display top 10 fantasy audiobooks from the last week
Uses authenticated SeleniumMAMCrawler to navigate and extract
"""

import logging
import os
import time
from datetime import datetime, timedelta
from mam_selenium_crawler import SeleniumMAMCrawler
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    logger.info("="*80)
    logger.info("TOP 10 FANTASY AUDIOBOOKS - LAST WEEK")
    logger.info("="*80)

    try:
        # Calculate dates
        today = datetime.now()
        start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

        logger.info(f"\nSearch period: {start_date} to {end_date}")
        logger.info("Category: Fantasy (ID 41)")
        logger.info("Sort: By most snatched (popularity)")

        # Initialize crawler (uses proven authentication)
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

        # Build search URL
        base_url = "https://www.myanonamouse.net/tor/browse.php"
        search_url = (
            f"{base_url}?"
            f"&tor[srchIn][title]=true"
            f"&tor[srchIn][author]=true"
            f"&tor[srchIn][narrator]=true"
            f"&tor[searchType]=all"
            f"&tor[searchIn]=torrents&tor[cat][]=41"  # Fantasy
            f"&tor[browse_lang][]=1"
            f"&tor[browseFlagsHideVsShow]=0"
            f"&tor[startDate]={start_date}"
            f"&tor[endDate]={end_date}"
            f"&tor[sortType]=snatchedDesc"  # Most snatched
            f"&tor[startNumber]=0"
            f"&thumbnail=true"
        )

        logger.info(f"\nNavigating to fantasy search...")
        crawler.driver.get(search_url)
        time.sleep(4)

        # Extract results
        logger.info("Extracting results...")
        results = []

        try:
            wait = WebDriverWait(crawler.driver, 10)
            torrent_rows = wait.until(
                EC.presence_of_all_elements_located((By.XPATH, "//tr[@class='torrent']"))
            )

            logger.info(f"Found {len(torrent_rows)} results\n")

            for idx, row in enumerate(torrent_rows[:10]):
                try:
                    # Title and link
                    title_elem = row.find_element(By.XPATH, ".//a[contains(@href, '/tor/')]")
                    title = title_elem.text.strip()
                    link = title_elem.get_attribute('href')

                    if link.startswith('/'):
                        link = "https://www.myanonamouse.net" + link

                    # Date
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    upload_date = "N/A"

                    for cell in cells[-3:]:
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

                except Exception as e:
                    logger.warning(f"Error extracting row {idx}: {e}")
                    continue

        except Exception as e:
            logger.warning(f"No results found: {e}")
            results = []

        # Display results
        logger.info("="*80)
        logger.info("RESULTS")
        logger.info("="*80)

        if results:
            for result in results:
                print(f"\n{result['position']}. {result['title']}")
                print(f"   {result['link']}")
                print(f"   Uploaded: {result['upload_date']}")

            logger.info("\n" + "="*80)
            logger.info(f"Total: {len(results)} fantasy audiobooks found in last week")
            logger.info("="*80)
        else:
            logger.warning("\nNo fantasy audiobooks found in the last week")

        crawler.cleanup()

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
