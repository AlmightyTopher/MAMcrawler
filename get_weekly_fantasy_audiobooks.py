#!/usr/bin/env python3
"""
Get top 10 fantasy audiobooks from last week and queue missing ones to qBittorrent
Uses proven SeleniumMAMCrawler for authentication
"""

import logging
import os
import time
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Set
from mam_selenium_crawler import SeleniumMAMCrawler
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
        # Clean up file names - remove prefixes like numbers, [M4B], [categories]
        cleaned = re.sub(r'^(\d+\s+|\[M4B\]\s+|\[.*?\]\s+)', '', name)
        if item.is_file():
            cleaned = Path(cleaned).stem

        titles.add(cleaned.lower().strip())
        # Also add individual parts split by dash
        parts = cleaned.lower().split('-')
        for part in parts:
            part_clean = part.strip()
            if len(part_clean) > 2:
                titles.add(part_clean)

    logger.info(f"Found {len(titles)} existing book titles/parts in library")
    return titles


def is_book_in_library(title: str, library_titles: Set[str]) -> bool:
    """Check if book is likely already in library using fuzzy matching"""
    title_lower = title.lower()

    # Direct match
    if title_lower in library_titles:
        return True

    # Check if major parts of title match
    matches = 0
    for lib_title in library_titles:
        if len(lib_title) > 4 and lib_title in title_lower:
            matches += 1

    return matches >= 1


def get_fantasy_audiobooks(crawler) -> List[Dict]:
    """Extract top 10 fantasy audiobooks from last week"""
    try:
        # Calculate dates
        today = datetime.now()
        start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

        logger.info(f"Search period: {start_date} to {end_date}")
        logger.info("Category: Fantasy (ID 41)")
        logger.info("Sort: By most snatched (popularity)")

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

        # Check if we're still logged in
        current_url = crawler.driver.current_url
        if "login" in current_url.lower():
            logger.error("Session expired! Redirected to login")
            return []

        results = []
        try:
            wait = WebDriverWait(crawler.driver, 10)
            # Find torrent rows
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

                    # Try to extract upload date
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

                    logger.info(f"[{idx+1}] {title}")
                    logger.info(f"     Date: {upload_date}")

                except Exception as e:
                    logger.warning(f"Error extracting row {idx}: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Error finding results: {e}")
            return []

    except Exception as e:
        logger.error(f"Error in get_fantasy_audiobooks: {e}")
        return []


def queue_book_to_qbittorrent(crawler, book: Dict) -> bool:
    """Navigate to book page and queue its magnet link"""
    try:
        logger.info(f"\nProcessing: {book['title']}")

        # Navigate to book page
        crawler.driver.get(book['link'])
        time.sleep(2)

        # Find magnet link
        try:
            magnet_elem = crawler.driver.find_element(By.XPATH, "//a[contains(@href, 'magnet:')]")
            magnet_link = magnet_elem.get_attribute('href')

            # Queue to qBittorrent
            success = crawler.qb_client.torrents_add(
                urls=magnet_link,
                category="audiobooks",
                tags=["fantasy", "weekly-top"],
                is_paused=False
            )

            if success:
                logger.info(f"✓ Queued to qBittorrent")
                return True
            else:
                logger.warning(f"✗ Failed to queue to qBittorrent")
                return False

        except Exception as e:
            logger.warning(f"✗ Could not get magnet link: {e}")
            return False

    except Exception as e:
        logger.error(f"Error queuing book: {e}")
        return False


def main():
    logger.info("="*80)
    logger.info("WEEKLY FANTASY AUDIOBOOKS - FIND & QUEUE MISSING")
    logger.info("="*80)

    try:
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

        logger.info("✓ Crawler initialized and authenticated")

        # Step 3: Get fantasy audiobooks
        logger.info("\nStep 3: Fetching top 10 fantasy audiobooks from last week...")
        results = get_fantasy_audiobooks(crawler)

        if not results:
            logger.warning("No fantasy audiobooks found in the last week")
            crawler.cleanup()
            return

        logger.info(f"\nFound {len(results)} fantasy audiobooks")

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
            if queue_book_to_qbittorrent(crawler, book):
                queued_count += 1
            time.sleep(2)

        # Final report
        logger.info("\n" + "="*80)
        logger.info("COMPLETE")
        logger.info("="*80)
        logger.info(f"Fantasy audiobooks from last week: {len(results)}")
        logger.info(f"Already in library: {len(results) - len(missing_books)}")
        logger.info(f"Successfully queued: {queued_count}/{len(missing_books)}")
        logger.info("="*80)

        # Display all books for reference
        logger.info("\nAll Books Found:")
        for result in results:
            in_lib = "✓" if is_book_in_library(result['title'], existing_books) else "✗"
            print(f"{in_lib} [{result['position']}] {result['title']}")
            print(f"     {result['link']}")

        crawler.cleanup()

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
