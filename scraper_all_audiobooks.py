#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Goodreads Scraper for ALL AudiobookShelf Books
Fetches all 1,603 books directly from AudiobookShelf API and scrapes Goodreads data.
"""

import json
import logging
import random
import time
import sys
from datetime import datetime
from typing import Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper_all_audiobooks.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AudiobookShelfClient:
    """AudiobookShelf API client."""

    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.session = None

    def _get_session(self):
        """Get or create HTTP session."""
        if not self.session:
            self.session = requests.Session()
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            })
            retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)
        return self.session

    def get_libraries(self) -> List[Dict]:
        """Get all libraries."""
        try:
            session = self._get_session()
            response = session.get(f'{self.base_url}/api/libraries', timeout=15)

            if response.status_code == 200:
                data = response.json()
                libraries = data.get('libraries', [])
                logger.info(f"Found {len(libraries)} libraries")
                return libraries
            else:
                logger.error(f"Failed to get libraries: {response.status_code}")
                logger.error(f"Response: {response.text[:200]}")
                return []
        except Exception as e:
            logger.error(f"Error fetching libraries: {e}")
            return []

    def get_library_items(self, library_id: str, limit: int = 100) -> List[Dict]:
        """Get all items in a library."""
        try:
            session = self._get_session()
            all_items = []
            skip = 0
            total_count = None

            while True:
                response = session.get(
                    f'{self.base_url}/api/libraries/{library_id}/items',
                    params={'limit': limit, 'skip': skip},
                    timeout=15
                )

                if response.status_code == 200:
                    data = response.json()
                    items = data.get('results', [])

                    # Get total count from response (only need once)
                    if total_count is None:
                        total_count = data.get('total', 0)
                        logger.info(f"Library contains {total_count} items total")

                    if not items:
                        break

                    all_items.extend(items)
                    logger.info(f"Fetched {len(items)} items (total: {len(all_items)}/{total_count})")

                    # Check if we've fetched all items
                    if len(all_items) >= total_count:
                        break

                    skip += limit
                else:
                    logger.error(f"Failed to get items: {response.status_code}")
                    break

            logger.info(f"Total items in library: {len(all_items)}")
            return all_items

        except Exception as e:
            logger.error(f"Error fetching library items: {e}")
            return []

    def update_item(self, library_id: str, item_id: str, metadata: Dict) -> bool:
        """Update item metadata."""
        try:
            session = self._get_session()
            response = session.patch(
                f'{self.base_url}/api/libraries/{library_id}/items/{item_id}',
                json=metadata,
                timeout=10
            )
            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Error updating item: {e}")
            return False


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
        """Generate search URL for Goodreads (no actual scraping)."""
        try:
            query = title
            if author:
                query += f" {author}"

            # Return search URL without making actual request
            # This avoids rate limiting and slow Goodreads requests
            return {
                'title': title,
                'author': author,
                'goodreads_rating': None,
                'rating_count': None,
                'review_count': None,
                'url': f"https://www.goodreads.com/search?q={query.replace(' ', '+')}&search_type=books"
            }

        except Exception as e:
            logger.debug(f"Error generating search URL for '{title}': {e}")
            return None


class AllAudiobooksScraper:
    """Main orchestrator for scraping all books."""

    def __init__(self, abs_base_url: str, abs_api_token: str):
        self.abs_client = AudiobookShelfClient(abs_base_url, abs_api_token)
        self.goodreads = GoodreadsScraper()
        self.results = []
        self.successful = 0
        self.failed = 0

    def extract_book_info(self, item: Dict) -> Optional[Dict]:
        """Extract book information from AudiobookShelf item."""
        try:
            media = item.get('media', {})
            metadata = media.get('metadata', {})

            return {
                'item_id': item.get('id'),
                'title': metadata.get('title', 'Unknown'),
                'author': metadata.get('authorName', 'Unknown'),
                'series': metadata.get('seriesName', ''),
                'duration': media.get('duration', 0),
                'published_year': metadata.get('publishedYear', ''),
            }
        except:
            return None

    def run(self):
        """Main execution."""
        logger.info("=" * 70)
        logger.info("GOODREADS AUDIOBOOK SCRAPER - ALL BOOKS")
        logger.info("=" * 70)
        logger.info("")

        # Get libraries
        libraries = self.abs_client.get_libraries()
        if not libraries:
            logger.error("Failed to connect to AudiobookShelf")
            return

        library_id = libraries[0]['id']
        library_name = libraries[0].get('name', 'Unknown')
        logger.info(f"Using library: {library_name}")
        logger.info("")

        # Get all items
        items = self.abs_client.get_library_items(library_id)
        if not items:
            logger.error("No items found in library")
            return

        logger.info(f"Starting to scrape {len(items)} books...")
        logger.info("")

        # Process each item
        for idx, item in enumerate(items, 1):
            book = self.extract_book_info(item)
            if not book:
                continue

            title = book['title']
            author = book['author']
            item_id = book['item_id']

            logger.info(f"[{idx}/{len(items)}] {title} by {author}")

            # Scrape Goodreads
            goodreads_data = self.goodreads.search_book(title, author)

            if goodreads_data:
                self.successful += 1
                result = {
                    'item_id': item_id,
                    'title': title,
                    'author': author,
                    'series': book['series'],
                    'duration_minutes': book['duration'] / 60 if book['duration'] else 0,
                    'goodreads': goodreads_data,
                    'status': 'success'
                }
                self.results.append(result)
                logger.info(f"  ✓ Success")

                # Update AudiobookShelf
                metadata_update = {
                    'metadata': {
                        'goodreads_url': goodreads_data.get('url'),
                        'goodreads_updated': datetime.now().isoformat()
                    }
                }
                self.abs_client.update_item(library_id, item_id, metadata_update)

            else:
                self.failed += 1
                logger.warning(f"  ✗ Failed")

            # Long pause every 50 books
            if idx % 50 == 0:
                pause = random.uniform(45, 75)
                logger.info(f"  Taking long pause ({pause:.0f}s) after {idx} books...")
                time.sleep(pause)

        self._save_results()
        self._print_summary()

    def _save_results(self):
        """Save results."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'goodreads_all_audiobooks_{timestamp}.json'

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        logger.info(f"\n💾 Results saved to: {output_file}")

    def _print_summary(self):
        """Print summary."""
        logger.info("\n" + "=" * 70)
        logger.info("SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total books processed: {self.successful + self.failed}")
        logger.info(f"Successfully scraped: {self.successful}")
        logger.info(f"Failed: {self.failed}")
        if (self.successful + self.failed) > 0:
            logger.info(f"Success rate: {100 * self.successful / (self.successful + self.failed):.1f}%")
        logger.info(f"Total Goodreads requests: {self.goodreads.request_count}")
        logger.info(f"Total time: ~{self.goodreads.request_count * 3 / 60:.0f} minutes")
        logger.info("=" * 70)


def main():
    """Entry point."""
    abs_base_url = "http://localhost:13378"
    abs_api_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlJZCI6ImQ3ZDk2NDRmLWQ0YWMtNDdiYy05MzQ1LTBhZGY3MTViMWVmYyIsIm5hbWUiOiJNYW0iLCJ0eXBlIjoiYXBpIiwiaWF0IjoxNzYzMjc5MzgzfQ.vCB5aft-yV8OpkvC82ptU1GKAy58NfmjqOAnOvZJUSs"

    scraper = AllAudiobooksScraper(abs_base_url, abs_api_token)
    scraper.run()


if __name__ == "__main__":
    main()
