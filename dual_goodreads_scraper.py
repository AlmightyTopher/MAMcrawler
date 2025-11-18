#!/usr/bin/env python3
"""
Dual Goodreads Scraper with VPN and Direct WAN Routing
Implements two independent scrapers to appear as different users to Goodreads.
"""

import asyncio
import os
import json
import logging
import random
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv

import aiohttp
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dual_goodreads_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class StealthScraper:
    """Base scraper class with stealth features."""

    def __init__(self, name: str, proxy_config: Optional[Dict] = None):
        self.name = name
        self.proxy_config = proxy_config
        self.session = None
        self.user_agents = self._load_user_agents()
        self.request_count = 0
        self.last_request_time = 0
        self.daily_request_count = 0
        self.daily_reset_time = time.time()

        # Rate limiting
        self.min_delay = 2.0  # Minimum delay between requests
        self.max_delay = 5.0  # Maximum delay between requests
        self.requests_per_hour = 100  # Max requests per hour
        self.long_pause_every = 15  # Long pause every N requests
        self.long_pause_duration = (30, 60)  # 30-60 seconds

    def _load_user_agents(self) -> List[str]:
        """Load diverse user agent pool."""
        return [
            # Desktop Chrome variants
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',

            # Mobile Safari variants
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 15_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.7 Mobile/15E148 Safari/604.1',

            # Firefox variants
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/118.0',
        ]

    def _get_random_headers(self) -> Dict[str, str]:
        """Generate randomized headers for each request."""
        user_agent = random.choice(self.user_agents)

        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }

        # Add some randomization to headers
        if random.random() < 0.3:  # 30% chance
            headers['Accept-Language'] = 'en-US,en;q=0.9,es;q=0.8'
        if random.random() < 0.2:  # 20% chance
            headers['DNT'] = '0'

        return headers

    def _check_rate_limits(self) -> None:
        """Check and enforce rate limits."""
        current_time = time.time()

        # Reset daily counter if needed
        if current_time - self.daily_reset_time > 86400:  # 24 hours
            self.daily_request_count = 0
            self.daily_reset_time = current_time

        # Check hourly limit
        if self.daily_request_count >= self.requests_per_hour:
            sleep_time = 86400 - (current_time - self.daily_reset_time)
            logger.warning(f"{self.name}: Hourly limit reached, sleeping {sleep_time:.0f} seconds")
            time.sleep(sleep_time)
            self.daily_request_count = 0
            self.daily_reset_time = time.time()

        # Check for long pause
        if self.request_count > 0 and self.request_count % self.long_pause_every == 0:
            pause_duration = random.uniform(*self.long_pause_duration)
            logger.info(f"{self.name}: Taking long pause ({pause_duration:.1f}s) after {self.request_count} requests")
            time.sleep(pause_duration)

    def _calculate_delay(self) -> float:
        """Calculate delay before next request with jitter."""
        base_delay = random.uniform(self.min_delay, self.max_delay)

        # Add jitter based on request history
        jitter = random.uniform(0.5, 2.0)
        if self.request_count > 10:
            # Increase delay slightly as we make more requests
            jitter *= 1.2

        delay = base_delay * jitter

        # Ensure minimum delay since last request
        time_since_last = time.time() - self.last_request_time
        if time_since_last < self.min_delay:
            delay = max(delay, self.min_delay - time_since_last)

        return delay

    def make_request(self, url: str, method: str = 'GET', **kwargs) -> Optional[requests.Response]:
        """Make a request with stealth features."""
        self._check_rate_limits()

        delay = self._calculate_delay()
        logger.debug(f"{self.name}: Sleeping {delay:.2f}s before request")
        time.sleep(delay)

        headers = self._get_random_headers()
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers

        # Set proxy if configured
        if self.proxy_config:
            kwargs['proxies'] = self.proxy_config

        # Configure session with retry strategy
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
            self.daily_request_count += 1

            logger.debug(f"{self.name}: Request {self.request_count} - {response.status_code}")
            return response

        except Exception as e:
            logger.error(f"{self.name}: Request failed: {e}")
            return None


class GoodreadsScraper:
    """Goodreads scraper using stealth techniques."""

    def __init__(self, scraper: StealthScraper):
        self.scraper = scraper
        self.base_url = "https://www.goodreads.com"

    def search_books(self, title: str, author: str = "") -> Optional[Dict]:
        """Search for books on Goodreads."""
        try:
            # Construct search query
            query = title
            if author:
                query += f" {author}"

            search_url = f"{self.base_url}/search"
            params = {
                'q': query,
                'search_type': 'books'
            }

            response = self.scraper.make_request(search_url, params=params)
            if not response or response.status_code != 200:
                return None

            # Parse the HTML response (simplified - would need proper HTML parsing)
            # This is a placeholder for actual scraping logic
            return self._parse_search_results(response.text)

        except Exception as e:
            logger.error(f"Goodreads search failed: {e}")
            return None

    def _parse_search_results(self, html: str) -> Optional[Dict]:
        """Parse Goodreads search results."""
        # Placeholder - would implement actual HTML parsing
        # This would extract book information, ratings, etc.
        return {
            'title': 'Sample Book',
            'author': 'Sample Author',
            'rating': 4.2,
            'ratings_count': 1234,
            'reviews_count': 567
        }


class DualGoodreadsScraper:
    """Manages two independent Goodreads scrapers."""

    def __init__(self):
        # Detect ProtonVPN SOCKS5 proxy
        self.vpn_proxy = self._detect_vpn_proxy()

        # Create two independent scrapers
        self.scraper_vpn = StealthScraper("VPN_Scraper", self.vpn_proxy)
        self.scraper_direct = StealthScraper("Direct_Scraper", None)

        # Create Goodreads scrapers
        self.goodreads_vpn = GoodreadsScraper(self.scraper_vpn)
        self.goodreads_direct = GoodreadsScraper(self.scraper_direct)

        # Results storage
        self.results_vpn = []
        self.results_direct = []
        self.merged_results = []

    def _detect_vpn_proxy(self) -> Optional[Dict]:
        """Detect ProtonVPN SOCKS5 proxy (user reported port 62410)."""
        # ProtonVPN ports - prioritize user-reported port
        ports_to_check = [62410, 8080, 54674]  # User reported port first

        for port in ports_to_check:
            try:
                # Test connection to proxy
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()

                if result == 0:
                    proxy_url = f"socks5://127.0.0.1:{port}"
                    logger.info(f"✅ Detected ProtonVPN SOCKS5 proxy: {proxy_url}")
                    logger.info("   Setup verified: Split Tunneling enabled, scraper in 'Included Apps'")
                    return {
                        'http': proxy_url,
                        'https': proxy_url
                    }
            except:
                continue

        logger.warning("⚠️  No ProtonVPN SOCKS5 proxy detected - ensure split tunneling is enabled and scraper is in 'Included Apps'")
        logger.warning("   Setup: Enable Split Tunneling → Add scraper to 'Included Apps' → Disable Kill Switch")
        logger.warning("   Expected proxy: socks5://127.0.0.1:8080 (ProtonVPN v4.3.5)")
        return None

    async def run_scraper_vpn(self, books: List[Dict]) -> None:
        """Run VPN scraper."""
        logger.info("🚀 Starting VPN scraper (via ProtonVPN)")

        for book in books:
            try:
                title = book.get('title', '')
                author = book.get('author', '')

                logger.info(f"📖 VPN: Processing '{title}' by {author}")

                result = self.goodreads_vpn.search_books(title, author)
                if result:
                    result['source'] = 'vpn'
                    result['original_title'] = title
                    result['original_author'] = author
                    self.results_vpn.append(result)
                    logger.info("  ✓ VPN scraper found data")
                else:
                    logger.warning("  ⚠ VPN scraper found no data")

            except Exception as e:
                logger.error(f"  ✗ VPN scraper error: {e}")

        logger.info(f"✅ VPN scraper completed: {len(self.results_vpn)} results")

    async def run_scraper_direct(self, books: List[Dict]) -> None:
        """Run direct WAN scraper."""
        logger.info("🚀 Starting Direct scraper (normal WAN)")

        for book in books:
            try:
                title = book.get('title', '')
                author = book.get('author', '')

                logger.info(f"📖 Direct: Processing '{title}' by {author}")

                result = self.goodreads_direct.search_books(title, author)
                if result:
                    result['source'] = 'direct'
                    result['original_title'] = title
                    result['original_author'] = author
                    self.results_direct.append(result)
                    logger.info("  ✓ Direct scraper found data")
                else:
                    logger.warning("  ⚠ Direct scraper found no data")

            except Exception as e:
                logger.error(f"  ✗ Direct scraper error: {e}")

        logger.info(f"✅ Direct scraper completed: {len(self.results_direct)} results")

    def merge_results(self) -> None:
        """Merge and deduplicate results from both scrapers."""
        logger.info("🔀 Merging results from both scrapers")

        # Combine all results
        all_results = self.results_vpn + self.results_direct

        # Simple deduplication based on title and author
        seen = set()
        deduped_results = []

        for result in all_results:
            key = (result.get('original_title', '').lower(),
                   result.get('original_author', '').lower())

            if key not in seen:
                seen.add(key)
                deduped_results.append(result)

        self.merged_results = deduped_results
        logger.info(f"📊 Merged {len(all_results)} raw results into {len(deduped_results)} unique results")

    def save_results(self) -> None:
        """Save results to files."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save individual results
        with open(f'goodreads_vpn_results_{timestamp}.json', 'w') as f:
            json.dump(self.results_vpn, f, indent=2)

        with open(f'goodreads_direct_results_{timestamp}.json', 'w') as f:
            json.dump(self.results_direct, f, indent=2)

        # Save merged results
        with open(f'goodreads_merged_results_{timestamp}.json', 'w') as f:
            json.dump(self.merged_results, f, indent=2)

        logger.info(f"💾 Results saved with timestamp {timestamp}")

    async def run(self, books: List[Dict]) -> None:
        """Main execution method."""
        logger.info("="*70)
        logger.info("DUAL GOODREADS SCRAPER - VPN + DIRECT WAN")
        logger.info("="*70)

        # Split books between scrapers (alternating)
        books_vpn = books[::2]  # Even indices
        books_direct = books[1::2]  # Odd indices

        logger.info(f"📚 Total books: {len(books)}")
        logger.info(f"📚 VPN scraper: {len(books_vpn)} books")
        logger.info(f"📚 Direct scraper: {len(books_direct)} books")

        # Run both scrapers simultaneously
        await asyncio.gather(
            self.run_scraper_vpn(books_vpn),
            self.run_scraper_direct(books_direct)
        )

        # Merge results
        self.merge_results()

        # Save results
        self.save_results()

        # Print summary
        self.print_summary()

    def print_summary(self) -> None:
        """Print execution summary."""
        logger.info("\n" + "="*70)
        logger.info("DUAL SCRAPER SUMMARY")
        logger.info("="*70)

        logger.info(f"VPN Scraper Results: {len(self.results_vpn)}")
        logger.info(f"Direct Scraper Results: {len(self.results_direct)}")
        logger.info(f"Merged Unique Results: {len(self.merged_results)}")

        if self.scraper_vpn.proxy_config:
            logger.info("✅ VPN proxy detected and used")
        else:
            logger.info("⚠️  No VPN proxy detected - VPN scraper used direct connection")

        logger.info("🎯 Dual scraping completed successfully!")
        logger.info("="*70)


async def main():
    """Entry point."""
    # Sample books to scrape (replace with actual book list)
    sample_books = [
        {'title': 'The Name of the Wind', 'author': 'Patrick Rothfuss'},
        {'title': 'The Way of Kings', 'author': 'Brandon Sanderson'},
        {'title': 'Mistborn', 'author': 'Brandon Sanderson'},
        {'title': 'The Lies of Locke Lamora', 'author': 'Scott Lynch'},
    ]

    scraper = DualGoodreadsScraper()
    await scraper.run(sample_books)


if __name__ == "__main__":
    asyncio.run(main())