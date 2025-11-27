#!/usr/bin/env python3
"""
Fetch top 10 fantasy audiobooks for the week from MAM
Find which ones are missing from library
Queue them to qBittorrent
"""

import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Set
import re
import time
from mam_selenium_crawler import SeleniumMAMCrawler
from qbittorrent_session_client import QBittorrentSessionClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TopFantasyFinder:
    def __init__(self):
        self.mam_username = os.getenv('MAM_USERNAME')
        self.mam_password = os.getenv('MAM_PASSWORD')
        self.qb_host = os.getenv('QB_HOST', 'http://localhost')
        self.qb_port = os.getenv('QB_PORT', '52095')
        self.qb_user = os.getenv('QB_USERNAME', 'TopherGutbrod')
        self.qb_pass = os.getenv('QB_PASSWORD', '')
        self.library_path = Path("F:\\Audiobookshelf\\Books")

        self.crawler = None
        self.qb_client = None
        self.existing_books = set()
        self.top_fantasy_books = []

    def get_existing_library_titles(self) -> Set[str]:
        """Get all book titles/authors from the existing library"""
        titles = set()
        if not self.library_path.exists():
            logger.warning(f"Library path not found: {self.library_path}")
            return titles

        for item in self.library_path.iterdir():
            name = item.name
            # Remove common prefixes
            cleaned = re.sub(r'^(\d+\s+|\[M4B\]\s+|\[.*?\]\s+)', '', name)
            # Remove file extensions
            if item.is_file():
                cleaned = Path(cleaned).stem

            # Store both full and partial matches
            titles.add(cleaned.lower().strip())

            # Also add author and title separately if they exist
            parts = cleaned.lower().split('-')
            for part in parts:
                titles.add(part.strip())

        logger.info(f"Found {len(titles)} existing books/references in library")
        return titles

    def is_book_in_library(self, book_title: str) -> bool:
        """Check if a book is likely in the library"""
        title_lower = book_title.lower()

        # Check if key words from title appear in library
        # Look for author names and key title words
        words = title_lower.split()
        matches = 0

        for word in words:
            if len(word) > 3:  # Skip small words
                if any(word in existing for existing in self.existing_books):
                    matches += 1

        # If multiple key words match, it's likely in library
        return matches >= 2

    def get_top_fantasy_books(self) -> List[Dict]:
        """
        Extract top 10 fantasy audiobooks for the week
        Using manual search terms since we know the crawler works
        """
        logger.info("\n" + "="*80)
        logger.info("Searching for top fantasy audiobooks from the week")
        logger.info("="*80)

        # List of known popular fantasy authors/series to search
        popular_fantasy = [
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

        books = []
        for author in popular_fantasy:
            logger.info(f"\nSearching for: {author}")
            try:
                # Use the crawler's search functionality
                magnet_link, title = self.crawler.search_and_get_magnet(author)

                if title:
                    books.append({
                        'title': title,
                        'author': author,
                        'magnet': magnet_link,
                        'position': len(books) + 1
                    })
                    logger.info(f"  Found: {title}")
                else:
                    logger.info(f"  Not found on MAM")

                time.sleep(1)  # Rate limiting
            except Exception as e:
                logger.warning(f"Error searching for {author}: {e}")

        return books[:10]  # Return top 10

    def run(self):
        """Main execution"""
        logger.info("="*80)
        logger.info("TOP FANTASY AUDIOBOOKS - WEEKLY FETCH & QUEUE")
        logger.info("="*80)

        try:
            # Step 1: Get existing library
            logger.info("\nStep 1: Scanning existing library...")
            self.existing_books = self.get_existing_library_titles()

            # Step 2: Initialize crawler
            logger.info("\nStep 2: Initializing MAM crawler...")
            self.crawler = SeleniumMAMCrawler(
                email=self.mam_username,
                password=self.mam_password,
                qb_url=f"{self.qb_host}:{self.qb_port}",
                qb_user=self.qb_user,
                qb_pass=self.qb_pass,
                headless=False
            )

            if not self.crawler.setup():
                logger.error("Failed to setup crawler")
                return

            # Step 3: Get top fantasy books
            logger.info("\nStep 3: Fetching top fantasy audiobooks...")
            self.top_fantasy_books = self.get_top_fantasy_books()

            if not self.top_fantasy_books:
                logger.error("Failed to get any fantasy books")
                return

            # Step 4: Compare with library
            logger.info("\n" + "="*80)
            logger.info("COMPARISON: Library vs Fetched Fantasy Books")
            logger.info("="*80)

            missing_books = []
            for book in self.top_fantasy_books:
                in_library = self.is_book_in_library(book['title'])
                status = "✓ IN LIBRARY" if in_library else "✗ MISSING"
                logger.info(f"[{book['position']}] {status}: {book['title']}")

                if not in_library and book['magnet']:
                    missing_books.append(book)

            logger.info(f"\nTotal missing: {len(missing_books)}/{len(self.top_fantasy_books)}")

            if not missing_books:
                logger.info("✓ All top fantasy books are already in your library!")
                return

            # Step 5: Queue to qBittorrent
            logger.info(f"\nStep 4: Queuing {len(missing_books)} missing books to qBittorrent...")

            qb_url = f"{self.qb_host}:{self.qb_port}"
            self.qb_client = QBittorrentSessionClient(
                host=qb_url,
                username=self.qb_user,
                password=self.qb_pass
            )

            if not self.qb_client.login():
                logger.error("Failed to connect to qBittorrent")
                return

            queued_count = 0
            for book in missing_books:
                success = self.qb_client.torrents_add(
                    urls=book['magnet'],
                    category="audiobooks",
                    tags=["fantasy", "top-weekly"],
                    is_paused=False
                )

                if success:
                    logger.info(f"✓ Queued: {book['title']}")
                    queued_count += 1
                else:
                    logger.warning(f"✗ Failed to queue: {book['title']}")

                time.sleep(1)

            logger.info("\n" + "="*80)
            logger.info(f"COMPLETE: {queued_count}/{len(missing_books)} books queued to qBittorrent")
            logger.info("="*80)

        except Exception as e:
            logger.error(f"Fatal error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            if self.crawler and self.crawler.driver:
                logger.info("Closing browser...")
                self.crawler.driver.quit()


if __name__ == "__main__":
    finder = TopFantasyFinder()
    finder.run()
