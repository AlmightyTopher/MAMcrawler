#!/usr/bin/env python3
"""
Queue popular fantasy audiobooks that are missing from library
Uses existing Selenium crawler infrastructure
"""

import logging
import os
import time
from pathlib import Path
from typing import List, Dict, Set
import re
from mam_selenium_crawler import SeleniumMAMCrawler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_library_titles() -> Set[str]:
    """Get all book titles from library"""
    library_path = Path("F:\\Audiobookshelf\\Books")
    titles = set()

    if not library_path.exists():
        logger.warning(f"Library path not found: {library_path}")
        return titles

    for item in library_path.iterdir():
        name = item.name
        # Normalize: remove prefixes, extensions
        cleaned = re.sub(r'^(\d+\s+|\[M4B\]\s+|\[.*?\]\s+)', '', name)
        if item.is_file():
            cleaned = Path(cleaned).stem

        titles.add(cleaned.lower().strip())

    logger.info(f"Found {len(titles)} items in library")
    return titles


def is_in_library(title: str, library_titles: Set[str]) -> bool:
    """Check if title is likely in library"""
    title_lower = title.lower()
    # Look for author or key words
    for lib_title in library_titles:
        if len(lib_title) > 3 and lib_title in title_lower:
            return True
    return False


def main():
    # Popular fantasy authors - known to have audiobooks on MAM
    popular_authors = [
        "Brandon Sanderson",
        "Robert Jordan",
        "Terry Pratchett",
        "Patrick Rothfuss",
        "Neil Gaiman",
        "J.R.R. Tolkien",
        "George R.R. Martin",
        "Steven Erikson",
        "Robin Hobb",
        "Joe Abercrombie",
    ]

    logger.info("="*80)
    logger.info("QUEUEING POPULAR FANTASY AUDIOBOOKS")
    logger.info("="*80)

    # Get library titles
    logger.info("\nScanning existing library...")
    library_titles = get_library_titles()

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

    logger.info("\n" + "="*80)
    logger.info("SEARCHING FOR POPULAR FANTASY AUTHORS")
    logger.info("="*80)

    queued_count = 0
    not_found_count = 0
    already_have_count = 0

    for author in popular_authors:
        logger.info(f"\nSearching: {author}")

        # Search on MAM
        result = crawler.search_mam(author)

        if not result:
            logger.info(f"  ✗ Not found on MAM")
            not_found_count += 1
            time.sleep(1)
            continue

        title = result.get('title', author)
        torrent_id = result.get('id')

        logger.info(f"  Found: {title}")

        # Check if in library
        if is_in_library(title, library_titles):
            logger.info(f"  ✓ Already in library")
            already_have_count += 1
            time.sleep(1)
            continue

        # Get magnet link and queue
        logger.info(f"  Getting magnet link...")
        magnet = crawler._get_magnet_link(torrent_id) if torrent_id else None

        if magnet:
            logger.info(f"  Queuing to qBittorrent...")
            success = crawler.qb_client.torrents_add(
                urls=magnet,
                category="audiobooks",
                tags=["fantasy", "popular-authors"],
                is_paused=False
            )

            if success:
                logger.info(f"  ✓ Queued: {title}")
                queued_count += 1
            else:
                logger.warning(f"  ✗ Failed to queue")
        else:
            logger.warning(f"  ✗ Could not get magnet link")

        time.sleep(2)

    logger.info("\n" + "="*80)
    logger.info("SUMMARY")
    logger.info("="*80)
    logger.info(f"Queued: {queued_count} audiobooks")
    logger.info(f"Already in library: {already_have_count} audiobooks")
    logger.info(f"Not found on MAM: {not_found_count} audiobooks")
    logger.info("="*80)

    crawler.cleanup()


if __name__ == "__main__":
    main()
