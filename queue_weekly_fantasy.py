#!/usr/bin/env python3
"""
Queue top fantasy audiobooks from the current week
Uses the proven SeleniumMAMCrawler for authentication
Then searches by date range and queues missing books
"""

import logging
import os
import time
from pathlib import Path
from typing import List, Dict, Set
import re
from datetime import datetime, timedelta
from mam_selenium_crawler import SeleniumMAMCrawler
from qbittorrent_session_client import QBittorrentSessionClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_library_titles() -> Set[str]:
    """Get all book titles from existing library"""
    library_path = Path("F:\\Audiobookshelf\\Books")
    titles = set()

    if not library_path.exists():
        logger.warning(f"Library path not found: {library_path}")
        return titles

    for item in library_path.iterdir():
        name = item.name
        cleaned = re.sub(r'^(\d+\s+|\[M4B\]\s+|\[.*?\]\s+)', '', name)
        if item.is_file():
            cleaned = Path(cleaned).stem

        titles.add(cleaned.lower().strip())
        parts = cleaned.lower().split('-')
        for part in parts:
            titles.add(part.strip())

    logger.info(f"Found {len(titles)} existing books in library")
    return titles


def is_book_in_library(title: str, library_titles: Set[str]) -> bool:
    """Check if book is likely in library"""
    title_lower = title.lower()
    matches = 0

    for lib_title in library_titles:
        if len(lib_title) > 3 and lib_title in title_lower:
            matches += 1

    return matches >= 2


def extract_results_from_page(crawler) -> List[Dict]:
    """Extract fantasy audiobook results from current page"""
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        time.sleep(2)

        results = []
        wait = WebDriverWait(crawler.driver, 10)

        # Find all torrent rows
        torrent_rows = wait.until(
            EC.presence_of_all_elements_located((By.XPATH, "//table[@class='table']//tr[@class='torrent']"))
        )

        logger.info(f"Found {len(torrent_rows)} results on page")

        for idx, row in enumerate(torrent_rows[:10]):  # Get top 10
            try:
                # Get title and link
                title_elem = row.find_element(By.XPATH, ".//a[contains(@href, '/tor/')]")
                title = title_elem.text.strip()
                link = title_elem.get_attribute('href')

                # Get upload date from cells
                cells = row.find_elements(By.TAG_NAME, 'td')
                upload_date = "Unknown"

                for cell in cells:
                    cell_text = cell.text.strip()
                    if re.match(r'\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}', cell_text):
                        upload_date = cell_text
                        break

                results.append({
                    'title': title,
                    'link': link,
                    'upload_date': upload_date,
                    'position': idx + 1
                })

                logger.info(f"[{idx+1}] {title}")
                logger.info(f"     Date: {upload_date}")

            except Exception as e:
                logger.warning(f"Error extracting result {idx}: {e}")
                continue

        return results

    except Exception as e:
        logger.error(f"Error extracting results: {e}")
        return []


def main():
    logger.info("="*80)
    logger.info("WEEKLY FANTASY AUDIOBOOKS - QUEUE MISSING")
    logger.info("="*80)

    try:
        # Calculate week dates
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())  # Monday
        end_of_week = start_of_week + timedelta(days=6)  # Sunday

        start_date = start_of_week.strftime("%Y-%m-%d")
        end_date = end_of_week.strftime("%Y-%m-%d")

        logger.info(f"\nSearch period: {start_date} to {end_date}")

        # Step 1: Get existing library
        logger.info("\nStep 1: Scanning library...")
        existing_books = get_library_titles()

        # Step 2: Initialize crawler
        logger.info("\nStep 2: Initializing MAM crawler...")
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

        # Step 3: Build and navigate to date range search URL
        logger.info("\nStep 3: Searching fantasy audiobooks by date range...")

        # Build the date range search URL
        base_url = "https://www.myanonamouse.net/tor/browse.php"
        search_url = (
            f"{base_url}?"
            f"&tor[srchIn][title]=true"
            f"&tor[srchIn][author]=true"
            f"&tor[srchIn][narrator]=true"
            f"&tor[searchType]=all"
            f"&tor[searchIn]=torrents&tor[cat][]=41"  # Fantasy category ID
            f"&tor[browse_lang][]=1"
            f"&tor[browseFlagsHideVsShow]=0"
            f"&tor[startDate]={start_date}"
            f"&tor[endDate]={end_date}"
            f"&tor[sortType]=snatchedDesc"  # Sort by most snatched (popular)
            f"&tor[startNumber]=0"
            f"&thumbnail=true"
        )

        logger.info(f"Search URL:\n{search_url}\n")

        crawler.driver.get(search_url)
        time.sleep(3)

        # Extract results
        results = extract_results_from_page(crawler)

        if not results:
            logger.warning("No fantasy audiobooks found this week")
            crawler.cleanup()
            return

        # Step 4: Compare with library
        logger.info("\n" + "="*80)
        logger.info("COMPARISON: Library vs Weekly Results")
        logger.info("="*80)

        missing_books = []
        for book in results:
            in_lib = is_book_in_library(book['title'], existing_books)
            status = "✓ IN LIBRARY" if in_lib else "✗ MISSING"
            logger.info(f"[{book['position']}] {status}: {book['title']}")
            logger.info(f"           Upload: {book['upload_date']}")

            if not in_lib:
                missing_books.append(book)

        logger.info(f"\nMissing: {len(missing_books)}/{len(results)}")

        if not missing_books:
            logger.info("✓ All weekly fantasy books already in your library!")
            crawler.cleanup()
            return

        # Step 5: Queue missing books
        logger.info(f"\nStep 4: Queuing {len(missing_books)} missing books to qBittorrent...")

        queued_count = 0
        for book in missing_books:
            try:
                # Navigate to torrent page to get magnet
                crawler.driver.get(book['link'])
                time.sleep(1)

                # Extract magnet link
                try:
                    from selenium.webdriver.common.by import By
                    magnet_elem = crawler.driver.find_element(By.XPATH, "//a[contains(@href, 'magnet:')]")
                    magnet_link = magnet_elem.get_attribute('href')

                    # Queue it
                    success = crawler.qb_client.torrents_add(
                        urls=magnet_link,
                        category="audiobooks",
                        tags=["fantasy", "weekly-top"],
                        is_paused=False
                    )

                    if success:
                        logger.info(f"✓ Queued: {book['title']}")
                        queued_count += 1
                    else:
                        logger.warning(f"✗ Failed to queue: {book['title']}")

                except Exception as e:
                    logger.warning(f"✗ Could not get magnet for {book['title']}: {e}")

                time.sleep(2)

            except Exception as e:
                logger.error(f"Error processing {book['title']}: {e}")

        logger.info("\n" + "="*80)
        logger.info(f"COMPLETE: {queued_count}/{len(missing_books)} books queued to qBittorrent")
        logger.info("="*80)

        crawler.cleanup()

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
