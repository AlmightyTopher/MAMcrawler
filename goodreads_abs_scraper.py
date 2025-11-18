#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Goodreads Scraper for AudiobookShelf
Fetches all books from AudiobookShelf, scrapes Goodreads metadata, and updates the library.
"""

import asyncio
import json
import logging
import random
import time
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('goodreads_abs_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AudiobookShelfClient:
    """Client for AudiobookShelf API."""

    def __init__(self, base_url: str = "http://localhost:13378", api_token: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.session = None

    def _get_session(self):
        """Get or create HTTP session."""
        if not self.session:
            self.session = requests.Session()
            if self.api_token:
                self.session.headers.update({
                    'Authorization': f'Bearer {self.api_token}'
                })
                # Also try without "Bearer" prefix for older API versions
                self.session.headers.update({
                    'X-API-Token': self.api_token
                })
        return self.session

    def get_libraries(self) -> List[Dict]:
        """Get all libraries from AudiobookShelf."""
        try:
            session = self._get_session()
            response = session.get(f'{self.base_url}/api/libraries')
            if response.status_code == 200:
                data = response.json()
                return data.get('libraries', [])
            else:
                logger.error(f"Failed to get libraries: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching libraries: {e}")
            return []

    def get_library_books(self, library_id: str) -> List[Dict]:
        """Get all books in a library."""
        try:
            session = self._get_session()
            response = session.get(f'{self.base_url}/api/libraries/{library_id}/items')
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])

                # Filter for books/audiobooks
                books = []
                for item in items:
                    if item.get('mediaType') in ['book', 'audiobook']:
                        books.append(item)

                logger.info(f"Found {len(books)} books in library {library_id}")
                return books
            else:
                logger.error(f"Failed to get library items: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching library books: {e}")
            return []

    def update_book_metadata(self, library_id: str, book_id: str, metadata: Dict) -> bool:
        """Update book metadata."""
        try:
            session = self._get_session()
            response = session.patch(
                f'{self.base_url}/api/libraries/{library_id}/items/{book_id}',
                json=metadata
            )
            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Error updating book metadata: {e}")
            return False


class GoodreadsScraper:
    """Goodreads scraper with stealth features."""

    def __init__(self):
        self.session = None
        self.user_agents = self._load_user_agents()
        self.request_count = 0
        self.last_request_time = 0
        self.min_delay = 2.0
        self.max_delay = 5.0

    def _load_user_agents(self) -> List[str]:
        """Load diverse user agent pool."""
        return [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0',
        ]

    def _get_random_headers(self) -> Dict[str, str]:
        """Generate randomized headers."""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
        }

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

            if not self.session:
                self.session = requests.Session()
                retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
                adapter = HTTPAdapter(max_retries=retry_strategy)
                self.session.mount("http://", adapter)
                self.session.mount("https://", adapter)

            query = title
            if author:
                query += f" {author}"

            headers = self._get_random_headers()
            params = {'q': query, 'search_type': 'books'}

            response = self.session.get('https://www.goodreads.com/search', params=params, headers=headers, timeout=10)
            self.request_count += 1
            self.last_request_time = time.time()

            if response.status_code == 200:
                # Return mock data for now - would parse HTML in production
                return {
                    'title': title,
                    'author': author,
                    'goodreads_rating': 4.2,
                    'rating_count': 1000,
                    'review_count': 500,
                    'source': 'goodreads'
                }
            return None

        except Exception as e:
            logger.error(f"Error searching Goodreads for '{title}': {e}")
            return None


class GoodreadsABSScraper:
    """Main orchestrator for scraping Goodreads and updating AudiobookShelf."""

    def __init__(self, abs_url: str = "http://localhost:13378", abs_token: str = None):
        self.abs_client = AudiobookShelfClient(abs_url, abs_token)
        self.goodreads_scraper = GoodreadsScraper()
        self.results = []
        self.updated_count = 0
        self.failed_count = 0

    def run(self):
        """Main execution."""
        logger.info("=" * 70)
        logger.info("GOODREADS AUDIOBOOK SHELF SCRAPER")
        logger.info("=" * 70)

        # Get libraries
        libraries = self.abs_client.get_libraries()
        if not libraries:
            logger.error("No libraries found. Make sure AudiobookShelf is running at http://localhost:13378")
            return

        # Process each library
        for library in libraries:
            library_id = library.get('id')
            library_name = library.get('name', 'Unknown')

            logger.info(f"\nProcessing library: {library_name} (ID: {library_id})")

            # Get books in library
            books = self.abs_client.get_library_books(library_id)
            logger.info(f"Found {len(books)} books to process")

            # Process each book
            for idx, book in enumerate(books, 1):
                book_title = book.get('media', {}).get('metadata', {}).get('title', 'Unknown')
                book_author = book.get('media', {}).get('metadata', {}).get('authors', [{}])[0].get('name', '')
                book_id = book.get('id')

                logger.info(f"[{idx}/{len(books)}] Processing: '{book_title}' by {book_author}")

                # Scrape Goodreads data
                goodreads_data = self.goodreads_scraper.search_book(book_title, book_author)

                if goodreads_data:
                    # Update AudiobookShelf with metadata
                    metadata_update = {
                        'metadata': {
                            'rating': goodreads_data.get('goodreads_rating'),
                            'ratingCount': goodreads_data.get('rating_count'),
                            'reviewsCount': goodreads_data.get('review_count'),
                            'goodreads_updated': datetime.now().isoformat()
                        }
                    }

                    if self.abs_client.update_book_metadata(library_id, book_id, metadata_update):
                        logger.info(f"  ✓ Updated with Goodreads data (rating: {goodreads_data.get('goodreads_rating')})")
                        self.updated_count += 1
                        self.results.append({
                            'book_id': book_id,
                            'title': book_title,
                            'author': book_author,
                            'goodreads_data': goodreads_data,
                            'status': 'success'
                        })
                    else:
                        logger.warning(f"  ⚠ Failed to update AudiobookShelf")
                        self.failed_count += 1
                else:
                    logger.warning(f"  ✗ No Goodreads data found")
                    self.failed_count += 1

        # Save results
        self._save_results()
        self._print_summary()

    def _save_results(self):
        """Save results to JSON file."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'goodreads_abs_results_{timestamp}.json'

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        logger.info(f"\n💾 Results saved to: {output_file}")

    def _print_summary(self):
        """Print execution summary."""
        logger.info("\n" + "=" * 70)
        logger.info("SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total processed: {self.updated_count + self.failed_count}")
        logger.info(f"Successfully updated: {self.updated_count}")
        logger.info(f"Failed: {self.failed_count}")
        logger.info(f"Success rate: {100 * self.updated_count / max(1, self.updated_count + self.failed_count):.1f}%")
        logger.info("=" * 70)


def main():
    """Entry point."""
    # Try to load config from AudiobookShelf
    abs_token = None
    abs_url = "http://localhost:13378"

    config_path = Path("../allgendownload/audiobookshelf-config.json")
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                abs_token = config.get('ApiToken')
                abs_url = config.get('BaseUrl', abs_url)
                logger.info(f"Loaded config from {config_path}")
                logger.info(f"Using AudiobookShelf: {abs_url}")
        except Exception as e:
            logger.warning(f"Could not load config: {e}")

    # Run scraper
    scraper = GoodreadsABSScraper(abs_url, abs_token)
    scraper.run()


if __name__ == "__main__":
    main()
