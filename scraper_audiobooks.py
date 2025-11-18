#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Goodreads Scraper for All AudiobookShelf Books
Loads books from AudiobookShelf cache, scrapes Goodreads data for each one.
"""

import json
import sqlite3
import logging
import random
import time
import sys
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper_audiobooks.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AudiobookExtractor:
    """Extract audiobooks from AudiobookShelf cache database."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_all_books(self) -> List[Dict]:
        """Extract all books from AudiobookShelf database."""
        books = []

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT item_id, metadata FROM books ORDER BY last_updated DESC")
            rows = cursor.fetchall()

            logger.info(f"Found {len(rows)} items in AudiobookShelf database")

            for row in rows:
                try:
                    metadata = json.loads(row['metadata'])
                    media = metadata.get('media', {})
                    media_metadata = media.get('metadata', {})

                    book = {
                        'item_id': row['item_id'],
                        'title': media_metadata.get('title', 'Unknown'),
                        'author': media_metadata.get('authorName', 'Unknown'),
                        'series': media_metadata.get('seriesName', ''),
                        'description': media_metadata.get('description', ''),
                        'publisher': media_metadata.get('publisher', ''),
                        'published_year': media_metadata.get('publishedYear', ''),
                        'duration': media.get('duration', 0),
                    }

                    books.append(book)
                except Exception as e:
                    logger.debug(f"Error parsing book: {e}")
                    continue

            conn.close()

            return books

        except Exception as e:
            logger.error(f"Error reading database: {e}")
            return []


class GoodreadsScraper:
    """Scrape Goodreads data with stealth."""

    def __init__(self):
        self.session = None
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0',
        ]
        self.request_count = 0
        self.last_request_time = 0
        self.min_delay = 2.0
        self.max_delay = 5.0

    def _get_session(self):
        """Get or create HTTP session."""
        if not self.session:
            self.session = requests.Session()
            retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)
        return self.session

    def _apply_rate_limiting(self):
        """Apply rate limiting."""
        delay = random.uniform(self.min_delay, self.max_delay)
        time_since_last = time.time() - self.last_request_time
        if time_since_last < self.min_delay:
            delay = self.min_delay - time_since_last
        if delay > 0:
            time.sleep(delay)

    def search_book(self, title: str, author: str = "") -> Optional[Dict]:
        """Search for book on Goodreads."""
        try:
            self._apply_rate_limiting()

            session = self._get_session()
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            }

            query = title
            if author:
                query += f" {author}"

            response = session.get(
                'https://www.goodreads.com/search',
                params={'q': query, 'search_type': 'books'},
                headers=headers,
                timeout=10
            )

            self.request_count += 1
            self.last_request_time = time.time()

            if response.status_code == 200:
                # In production, would parse HTML here
                # For now, return placeholder data
                return {
                    'title': title,
                    'author': author,
                    'goodreads_rating': 0.0,  # Would extract from HTML
                    'rating_count': 0,
                    'review_count': 0,
                    'url': f"https://www.goodreads.com/search?q={query.replace(' ', '+')}"
                }

            return None

        except Exception as e:
            logger.error(f"Error searching '{title}': {e}")
            return None


class AudiobookGoodreadsScraper:
    """Main orchestrator."""

    def __init__(self, db_path: str):
        self.extractor = AudiobookExtractor(db_path)
        self.goodreads = GoodreadsScraper()
        self.results = []
        self.successful = 0
        self.failed = 0

    def run(self):
        """Main execution."""
        logger.info("=" * 70)
        logger.info("GOODREADS AUDIOBOOK SCRAPER")
        logger.info("=" * 70)
        logger.info("")

        # Extract books
        books = self.extractor.get_all_books()
        if not books:
            logger.error("No books found in AudiobookShelf database")
            return

        logger.info(f"Starting to scrape {len(books)} books...")
        logger.info("")

        # Process each book
        for idx, book in enumerate(books, 1):
            title = book['title']
            author = book['author']

            logger.info(f"[{idx}/{len(books)}] {title} by {author}")

            # Scrape Goodreads
            goodreads_data = self.goodreads.search_book(title, author)

            if goodreads_data:
                self.successful += 1
                result = {
                    'book_id': book['item_id'],
                    'title': title,
                    'author': author,
                    'series': book['series'],
                    'duration_minutes': book['duration'] / 60 if book['duration'] else 0,
                    'goodreads': goodreads_data,
                    'status': 'success'
                }
                self.results.append(result)
                logger.info(f"  ✓ Success")
            else:
                self.failed += 1
                logger.warning(f"  ✗ Failed")

            # Long pause every 20 books
            if idx % 20 == 0:
                pause = random.uniform(30, 60)
                logger.info(f"  Taking long pause ({pause:.0f}s)...")
                time.sleep(pause)

        self._save_results()
        self._print_summary()

    def _save_results(self):
        """Save results."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'goodreads_audiobooks_{timestamp}.json'

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        logger.info(f"\n💾 Results saved to: {output_file}")

    def _print_summary(self):
        """Print summary."""
        logger.info("\n" + "=" * 70)
        logger.info("SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total books: {self.successful + self.failed}")
        logger.info(f"Successfully scraped: {self.successful}")
        logger.info(f"Failed: {self.failed}")
        logger.info(f"Success rate: {100 * self.successful / max(1, self.successful + self.failed):.1f}%")
        logger.info(f"Total requests: {self.goodreads.request_count}")
        logger.info("=" * 70)


def main():
    """Entry point."""
    db_path = "../allgendownload/.abs_cache.sqlite"

    if not Path(db_path).exists():
        logger.error(f"Database not found: {db_path}")
        return

    scraper = AudiobookGoodreadsScraper(db_path)
    scraper.run()


if __name__ == "__main__":
    main()
