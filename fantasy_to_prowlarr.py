#!/usr/bin/env python3
"""
Get top 10 fantasy audiobooks and send magnet links to Prowlarr
"""

import logging
import os
import time
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Set
import requests

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
        cleaned = re.sub(r'^(\d+\s+|\[M4B\]\s+|\[.*?\]\s+)', '', name)
        if item.is_file():
            cleaned = Path(cleaned).stem

        titles.add(cleaned.lower().strip())
        parts = cleaned.lower().split('-')
        for part in parts:
            part_clean = part.strip()
            if len(part_clean) > 2:
                titles.add(part_clean)

    logger.info(f"Found {len(titles)} existing book titles/parts in library")
    return titles


def is_book_in_library(title: str, library_titles: Set[str]) -> bool:
    """Check if book is likely in library"""
    title_lower = title.lower()

    if title_lower in library_titles:
        return True

    matches = 0
    for lib_title in library_titles:
        if len(lib_title) > 4 and lib_title in title_lower:
            matches += 1

    return matches >= 1


def extract_magnet_links(crawler) -> List[Dict]:
    """Extract fantasy audiobooks with magnet links from search page"""
    results = []

    try:
        wait = WebDriverWait(crawler.driver, 10)

        logger.info("Trying to find torrent rows...")

        # Find rows with id starting with 'tdr-' (data rows)
        try:
            torrent_rows = wait.until(
                EC.presence_of_all_elements_located((By.XPATH, "//tr[starts-with(@id, 'tdr-')]"))
            )
            logger.info(f"Found {len(torrent_rows)} rows")
        except:
            logger.error("Could not find torrent rows")
            return []

        for idx, row in enumerate(torrent_rows[:10]):
            try:
                # Get title
                title_elem = row.find_element(By.XPATH, ".//a[@class='torTitle']")
                title = title_elem.text.strip()
                href = title_elem.get_attribute('href')

                # Build link to torrent page
                if href.startswith('/'):
                    link = f"https://www.myanonamouse.net{href}"
                else:
                    link = href if href.startswith('http') else f"https://www.myanonamouse.net/{href}"

                # Get upload date
                try:
                    desc_elem = row.find_element(By.XPATH, ".//span[@class='torRowDesc']")
                    desc_text = desc_elem.text
                    date_match = re.search(r'Released (\d{4}-\d{2}-\d{2})', desc_text)
                    upload_date = date_match.group(1) if date_match else "N/A"
                except:
                    upload_date = "N/A"

                # Try to find magnet link in the row
                magnet_link = None
                try:
                    # Look for download button or magnet link
                    download_elem = row.find_element(By.XPATH, ".//a[contains(@href, 'magnet:') or contains(@class, 'download')]")
                    magnet_link = download_elem.get_attribute('href')
                    logger.info(f"[{idx+1}] Found magnet: {title}")
                except:
                    # If no direct magnet, we'll need to get it from the torrent page
                    logger.warning(f"[{idx+1}] No magnet in row: {title} - will fetch from page")

                results.append({
                    'position': idx + 1,
                    'title': title,
                    'link': link,
                    'upload_date': upload_date,
                    'magnet': magnet_link
                })

            except Exception as e:
                logger.warning(f"Error extracting row {idx}: {e}")
                continue

        return results

    except Exception as e:
        logger.error(f"Error extracting results: {e}")
        return []


def send_to_prowlarr(download_url: str, title: str) -> bool:
    """Send download link to Prowlarr"""
    try:
        prowlarr_url = os.getenv('PROWLARR_URL', 'http://localhost:9696')
        prowlarr_api_key = os.getenv('PROWLARR_API_KEY', '')

        if not prowlarr_api_key:
            logger.warning("PROWLARR_API_KEY not set - cannot send to Prowlarr")
            return False

        # Prowlarr API endpoint for adding release/grab
        # This creates a manual release in Prowlarr
        url = f"{prowlarr_url}/api/v1/search/grab"

        payload = {
            'title': title,
            'downloadUrl': download_url,
            'indexerId': -1  # Manual release
        }

        headers = {
            'X-Api-Key': prowlarr_api_key,
            'Content-Type': 'application/json'
        }

        response = requests.post(url, json=payload, headers=headers, timeout=10)

        if response.status_code in [200, 201, 204]:
            logger.info(f"✓ Sent to Prowlarr: {title}")
            return True
        else:
            logger.warning(f"✗ Prowlarr response {response.status_code}: {response.text[:200]}")
            return False

    except Exception as e:
        logger.error(f"Error sending to Prowlarr: {e}")
        return False


def main():
    logger.info("="*80)
    logger.info("WEEKLY FANTASY AUDIOBOOKS TO PROWLARR")
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

        # Fresh login
        logger.info("\nStep 3: Fresh login to MAM...")
        crawler.driver.delete_all_cookies()
        time.sleep(1)
        if os.path.exists(crawler.cookies_file):
            os.remove(crawler.cookies_file)

        if not crawler.login():
            logger.error("Failed to login")
            crawler.cleanup()
            return

        logger.info("✓ Fresh login successful")

        # Step 4: Navigate to fantasy search
        logger.info("\nStep 4: Fetching top 10 fantasy audiobooks from last week...")

        today = datetime.now()
        start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

        logger.info(f"Search period: {start_date} to {end_date}")

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
            f"&tor[sortType]=snatchedDesc"
            f"&tor[startNumber]=0"
            f"&thumbnail=true"
        )

        logger.info("Navigating to fantasy search...")
        crawler.driver.get(search_url)
        time.sleep(4)

        # Extract results
        results = extract_magnet_links(crawler)

        if not results:
            logger.warning("No fantasy audiobooks found")
            crawler.cleanup()
            return

        logger.info(f"\nFound {len(results)} fantasy audiobooks")

        # Compare with library
        logger.info("\n" + "="*80)
        logger.info("COMPARISON: Library vs Weekly Results")
        logger.info("="*80)

        missing_books = []
        for book in results:
            in_lib = is_book_in_library(book['title'], existing_books)
            status = "✓ IN LIBRARY" if in_lib else "✗ MISSING"
            logger.info(f"[{book['position']}] {status}: {book['title']}")

            if not in_lib:
                missing_books.append(book)

        logger.info(f"\nMissing: {len(missing_books)}/{len(results)}")

        if not missing_books:
            logger.info("✓ All weekly fantasy books already in your library!")
            crawler.cleanup()
            return

        # Step 5: Send missing books to Prowlarr via torrent links
        logger.info(f"\nStep 5: Sending {len(missing_books)} missing books to Prowlarr...")

        sent_count = 0
        for book in missing_books:
            logger.info(f"\nBook: {book['title']}")
            logger.info(f"Link: {book['link']}")

            # Send the torrent link to Prowlarr - Prowlarr will fetch and convert to magnet
            if send_to_prowlarr(book['link'], book['title']):
                sent_count += 1
            else:
                logger.warning("Failed to send to Prowlarr")

            time.sleep(1)

        # Final report
        logger.info("\n" + "="*80)
        logger.info("COMPLETE")
        logger.info("="*80)
        logger.info(f"Fantasy audiobooks from last week: {len(results)}")
        logger.info(f"Already in library: {len(results) - len(missing_books)}")
        logger.info(f"Sent to Prowlarr: {sent_count}/{len(missing_books)}")
        logger.info("="*80)

        # Display all books
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
