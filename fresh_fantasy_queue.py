#!/usr/bin/env python3
"""
Fresh login approach for weekly fantasy audiobooks
Skip loading stale cookies and force fresh login
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
        # Clean up file names
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


def main():
    logger.info("="*80)
    logger.info("FRESH LOGIN - WEEKLY FANTASY AUDIOBOOKS")
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

        # KEY FIX: Delete all cookies to force fresh login
        logger.info("\nStep 3: Clearing cookies and forcing fresh login...")
        crawler.driver.delete_all_cookies()
        time.sleep(1)

        # Delete the saved cookie file
        if os.path.exists(crawler.cookies_file):
            os.remove(crawler.cookies_file)
            logger.info("Removed saved cookie file")

        # Perform fresh login
        if not crawler.login():
            logger.error("Failed to login")
            crawler.cleanup()
            return

        logger.info("✓ Fresh login successful")

        # Step 4: Get fantasy audiobooks
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

        # Check if still logged in
        current_url = crawler.driver.current_url
        if "login" in current_url.lower():
            logger.error("Session expired after login! Redirected to login")
            crawler.cleanup()
            return

        # Save page source for debugging
        page_source = crawler.driver.page_source
        with open("fantasy_search_debug.html", "w", encoding="utf-8") as f:
            f.write(page_source)
        logger.info("Saved page source to fantasy_search_debug.html")

        results = []
        try:
            wait = WebDriverWait(crawler.driver, 10)

            # Try different XPath selectors
            logger.info("Trying to find torrent rows...")

            # Try 1: Rows with id starting with 'tdr-' (data rows)
            try:
                torrent_rows = wait.until(
                    EC.presence_of_all_elements_located((By.XPATH, "//tr[starts-with(@id, 'tdr-')]"))
                )
                logger.info(f"Found {len(torrent_rows)} rows with XPath 1 (id='tdr-*')")
            except:
                logger.info("XPath 1 failed, trying alternative...")
                # Try 2: Any tr with class containing 'torrent'
                try:
                    torrent_rows = wait.until(
                        EC.presence_of_all_elements_located((By.XPATH, "//tr[@class='torrent']"))
                    )
                    logger.info(f"Found {len(torrent_rows)} rows with XPath 2 (class='torrent')")
                except:
                    logger.info("XPath 2 also failed...")
                    # Try 3: All tr except header
                    all_trs = wait.until(
                        EC.presence_of_all_elements_located((By.XPATH, "//table[@class='newTorTable']//tr"))
                    )
                    # Filter out header rows (that don't have td with content, only th)
                    torrent_rows = []
                    for tr in all_trs:
                        tds = tr.find_elements(By.TAG_NAME, 'td')
                        if len(tds) > 0:  # Data rows have td elements
                            torrent_rows.append(tr)
                    logger.info(f"Found {len(torrent_rows)} data rows by filtering (XPath 3)")

            logger.info(f"Found {len(torrent_rows)} results")

            for idx, row in enumerate(torrent_rows[:10]):
                try:
                    # Get title - it's in the "torTitle" class link
                    title_elem = row.find_element(By.XPATH, ".//a[@class='torTitle']")
                    title = title_elem.text.strip()
                    href = title_elem.get_attribute('href')

                    # Build link to torrent page (href is like "/t/1198735")
                    if href.startswith('/'):
                        link = f"https://www.myanonamouse.net{href}"
                    else:
                        link = href if href.startswith('http') else f"https://www.myanonamouse.net/{href}"

                    # Get upload date from the torRowDesc span
                    try:
                        desc_elem = row.find_element(By.XPATH, ".//span[@class='torRowDesc']")
                        desc_text = desc_elem.text
                        # Extract date pattern: "Released 2025-11-10"
                        import re
                        date_match = re.search(r'Released (\d{4}-\d{2}-\d{2})', desc_text)
                        upload_date = date_match.group(1) if date_match else "N/A"
                    except:
                        upload_date = "N/A"

                    results.append({
                        'position': idx + 1,
                        'title': title,
                        'link': link,
                        'upload_date': upload_date
                    })

                    logger.info(f"[{idx+1}] {title}")
                    logger.info(f"     Release: {upload_date}")

                except Exception as e:
                    logger.warning(f"Error extracting row {idx}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

        except Exception as e:
            logger.error(f"Error finding results: {e}")
            results = []

        if not results:
            logger.warning("No fantasy audiobooks found - check authentication")
            crawler.cleanup()
            return

        logger.info(f"\nFound {len(results)} fantasy audiobooks")

        # Step 5: Compare with library
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

        # Step 6: Queue missing books
        logger.info(f"\nStep 5: Queuing {len(missing_books)} missing books to qBittorrent...")

        queued_count = 0
        for book in missing_books:
            try:
                logger.info(f"\nProcessing: {book['title']}")

                # Extract torrent ID from link
                # Link format: https://www.myanonamouse.net/t/1198735
                torrent_id = book['link'].split('/t/')[-1]
                logger.info(f"Torrent ID: {torrent_id}")

                # Navigate to torrent detail page
                crawler.driver.get(book['link'])
                time.sleep(3)

                # Try multiple methods to get magnet link
                magnet_link = None

                # Method 1: Look for magnet link in page
                try:
                    magnet_elem = crawler.driver.find_element(By.XPATH, "//a[contains(@href, 'magnet:')]")
                    magnet_link = magnet_elem.get_attribute('href')
                    logger.info(f"Found magnet link via XPath")
                except:
                    logger.warning("Magnet link not found via XPath")

                # Method 2: Try direct download link (API endpoint)
                if not magnet_link:
                    try:
                        # Try to access the download file directly
                        # This might give us a torrent file or magnet link
                        download_url = f"https://www.myanonamouse.net/t/{torrent_id}"
                        # Some trackers support direct magnet generation
                        # For now, we'll extract from page if JavaScript loaded it
                        page_source = crawler.driver.page_source

                        # Look for magnet in page source
                        if "magnet:" in page_source:
                            import re
                            magnet_match = re.search(r'(magnet:\?[^"\'<>\s]+)', page_source)
                            if magnet_match:
                                magnet_link = magnet_match.group(1)
                                logger.info(f"Found magnet link in page source")
                    except Exception as e:
                        logger.warning(f"Method 2 failed: {e}")

                # Method 3: If no magnet, try to use torrent file download
                if not magnet_link:
                    try:
                        # MAM might support fetching torrent file which we can seed via magnet
                        # For now, queue a message that we'll need the magnet
                        logger.warning(f"Could not extract magnet link - would need manual intervention or alternative method")
                    except Exception as e:
                        logger.warning(f"Method 3 failed: {e}")

                # Queue if we found magnet
                if magnet_link:
                    success = crawler.qb_client.torrents_add(
                        urls=magnet_link,
                        category="audiobooks",
                        tags=["fantasy", "weekly-top"],
                        is_paused=False
                    )

                    if success:
                        logger.info(f"✓ Queued to qBittorrent")
                        queued_count += 1
                    else:
                        logger.warning(f"✗ Failed to queue to qBittorrent")
                else:
                    logger.warning(f"✗ Could not find magnet link for {book['title']}")

                time.sleep(2)

            except Exception as e:
                logger.error(f"Error queuing book: {e}")
                import traceback
                traceback.print_exc()

        # Final report
        logger.info("\n" + "="*80)
        logger.info("COMPLETE")
        logger.info("="*80)
        logger.info(f"Fantasy audiobooks from last week: {len(results)}")
        logger.info(f"Already in library: {len(results) - len(missing_books)}")
        logger.info(f"Successfully queued: {queued_count}/{len(missing_books)}")
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
