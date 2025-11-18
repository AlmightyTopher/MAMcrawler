#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Goodreads Scraper - Direct Route
This script bypasses ProtonVPN (direct WAN connection).
Must be run with Python executable that's in Split Tunneling "Excluded Apps".
"""

import json
import logging
import random
import time
from datetime import datetime
from typing import Dict, List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [DIRECT] - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper_direct.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class StealthScraper:
    """Stealth scraper for Goodreads via direct WAN."""

    def __init__(self):
        self.session = None
        self.user_agents = self._load_user_agents()
        self.request_count = 0
        self.last_request_time = 0

        # Rate limiting
        self.min_delay = 2.0
        self.max_delay = 5.0
        self.long_pause_every = 15
        self.long_pause_duration = (30, 60)

    def _load_user_agents(self) -> List[str]:
        """Load diverse user agent pool."""
        return [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/118.0',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
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
            'Upgrade-Insecure-Requests': '1',
        }

    def _check_rate_limits(self) -> None:
        """Check and enforce rate limits."""
        if self.request_count > 0 and self.request_count % self.long_pause_every == 0:
            pause_duration = random.uniform(*self.long_pause_duration)
            logger.info(f"Taking long pause ({pause_duration:.1f}s) after {self.request_count} requests")
            time.sleep(pause_duration)

    def _calculate_delay(self) -> float:
        """Calculate delay before next request."""
        base_delay = random.uniform(self.min_delay, self.max_delay)
        jitter = random.uniform(0.5, 2.0)
        delay = base_delay * jitter

        time_since_last = time.time() - self.last_request_time
        if time_since_last < self.min_delay:
            delay = max(delay, self.min_delay - time_since_last)

        return delay

    def make_request(self, url: str, method: str = 'GET', **kwargs) -> Optional[requests.Response]:
        """Make a request with stealth features."""
        self._check_rate_limits()

        delay = self._calculate_delay()
        logger.debug(f"Sleeping {delay:.2f}s before request")
        time.sleep(delay)

        headers = self._get_random_headers()
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers

        if not self.session:
            self.session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)

        try:
            self.last_request_time = time.time()
            response = self.session.request(method, url, **kwargs)
            self.request_count += 1

            logger.debug(f"Request {self.request_count} - {response.status_code}")
            return response

        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None

    def search_goodreads(self, title: str, author: str = "") -> Optional[Dict]:
        """Search for a book on Goodreads."""
        try:
            query = title
            if author:
                query += f" {author}"

            search_url = "https://www.goodreads.com/search"
            params = {'q': query, 'search_type': 'books'}

            response = self.make_request(search_url, params=params)
            if not response or response.status_code != 200:
                return None

            # Placeholder - would parse HTML here
            return {
                'title': title,
                'author': author,
                'rating': 4.2,
                'source': 'direct',
                'status': 'success'
            }

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return None


def main(books: List[Dict]) -> List[Dict]:
    """Main execution for direct scraper."""
    logger.info("=" * 70)
    logger.info("GOODREADS SCRAPER - DIRECT ROUTE")
    logger.info("=" * 70)
    logger.info("Traffic bypasses ProtonVPN (direct WAN connection)")
    logger.info(f"Processing {len(books)} books")
    logger.info("=" * 70)

    scraper = StealthScraper()
    results = []

    for idx, book in enumerate(books, 1):
        title = book.get('title', '')
        author = book.get('author', '')

        logger.info(f"[{idx}/{len(books)}] Processing: '{title}' by {author}")

        result = scraper.search_goodreads(title, author)
        if result:
            results.append(result)
            logger.info(f"  ✓ Success")
        else:
            logger.warning(f"  ✗ Failed")

    logger.info("=" * 70)
    logger.info(f"Direct Scraper Complete: {len(results)}/{len(books)} successful")
    logger.info("=" * 70)

    return results


if __name__ == "__main__":
    # Sample books for testing
    sample_books = [
        {'title': 'Mistborn', 'author': 'Brandon Sanderson'},
        {'title': 'The Lies of Locke Lamora', 'author': 'Scott Lynch'},
    ]

    results = main(sample_books)

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'direct_results_{timestamp}.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_file}")
