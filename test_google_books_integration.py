#!/usr/bin/env python3
"""
Test Google Books API Integration with Rate Limiting Validation.

Tests the Google Books client to ensure:
1. API key authentication works
2. Rate limiting is properly enforced
3. Caching prevents unnecessary requests
4. Quota tracking is accurate
5. Error handling works correctly

Rate Limit Summary (Google Books API v1):
- Default: 1,000 requests per day (API key)
- Per-minute: 100 requests per 100 seconds (1 req/sec min)
- Per-second: 1 request per second recommended
- Error response: HTTP 429 (Too Many Requests)

Usage Strategy:
- Keep 1 second minimum between requests
- Aim for max 900 requests/day (10% buffer below 1000 limit)
- Use caching (24hr TTL) to avoid duplicate requests
- Monitor quota via rate_limit_status()
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from backend.integrations.google_books_client import (
    GoogleBooksClient,
    GoogleBooksError,
    GoogleBooksRateLimitError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('google_books_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GoogleBooksIntegrationTest:
    """Test suite for Google Books API integration."""

    def __init__(self, api_key: str = None):
        """Initialize test suite."""
        self.api_key = api_key or os.getenv('GOOGLE_BOOKS_API_KEY')
        if not self.api_key:
            logger.error("GOOGLE_BOOKS_API_KEY not found in environment")
            raise ValueError("API key required")

        logger.info(f"Initialized test with API key: {self.api_key[:10]}...")
        self.client = None
        self.test_books = [
            ("Project Hail Mary", "Andy Weir"),
            ("The Martian", "Andy Weir"),
            ("Foundation", "Isaac Asimov"),
            ("Dune", "Frank Herbert"),
            ("Ender's Game", "Orson Scott Card"),
            ("Harry Potter and the Sorcerer's Stone", "J.K. Rowling"),
            ("The Lord of the Rings", "J.R.R. Tolkien"),
            ("Neuromancer", "William Gibson"),
            ("Snow Crash", "Neal Stephenson"),
            ("Ready Player One", "Ernest Cline"),
        ]

    async def test_basic_search(self):
        """Test 1: Basic search functionality."""
        logger.info("=" * 70)
        logger.info("TEST 1: Basic Search Functionality")
        logger.info("=" * 70)

        try:
            async with GoogleBooksClient(api_key=self.api_key, max_requests_per_day=900) as client:
                title, author = self.test_books[0]
                logger.info(f"Searching for: '{title}' by {author}")

                results = await client.search(title=title, author=author, max_results=5)

                if results:
                    logger.info(f"✓ Found {len(results)} results")
                    first = results[0].get('volumeInfo', {})
                    logger.info(f"  Top result: {first.get('title')} by {', '.join(first.get('authors', []))}")
                    return True
                else:
                    logger.warning("✗ No results found")
                    return False

        except GoogleBooksRateLimitError as e:
            logger.error(f"✗ Rate limit error: {e}")
            return False
        except Exception as e:
            logger.error(f"✗ Search failed: {e}")
            return False

    async def test_cache_effectiveness(self):
        """Test 2: Caching reduces API calls."""
        logger.info("=" * 70)
        logger.info("TEST 2: Cache Effectiveness")
        logger.info("=" * 70)

        try:
            async with GoogleBooksClient(api_key=self.api_key, max_requests_per_day=900) as client:
                title, author = self.test_books[1]

                # First search - should hit API
                logger.info(f"First search for '{title}'...")
                status_before = client.get_rate_limit_status()
                results1 = await client.search(title=title, author=author, max_results=3)
                status_after_api = client.get_rate_limit_status()

                api_calls_first = status_after_api['requests_used'] - status_before['requests_used']
                logger.info(f"  API calls: {api_calls_first}")

                # Second search - should use cache
                logger.info(f"Second search for '{title}' (should be cached)...")
                results2 = await client.search(title=title, author=author, max_results=3)
                status_after_cache = client.get_rate_limit_status()

                api_calls_second = status_after_cache['requests_used'] - status_after_api['requests_used']
                logger.info(f"  API calls: {api_calls_second}")

                if api_calls_second == 0:
                    logger.info("✓ Cache working correctly (zero API calls on second search)")
                    return True
                else:
                    logger.warning(f"✗ Cache not working (made {api_calls_second} API calls)")
                    return False

        except Exception as e:
            logger.error(f"✗ Cache test failed: {e}")
            return False

    async def test_rate_limiting(self):
        """Test 3: Rate limiting between requests."""
        logger.info("=" * 70)
        logger.info("TEST 3: Rate Limiting Between Requests")
        logger.info("=" * 70)

        try:
            async with GoogleBooksClient(api_key=self.api_key, max_requests_per_day=900) as client:
                start_time = datetime.now()
                logger.info(f"Starting rapid requests at {start_time.isoformat()}")

                # Make 3 requests rapidly (should be rate limited)
                for i, (title, author) in enumerate(self.test_books[2:5], 1):
                    req_start = datetime.now()
                    results = await client.search(title=title, author=author, max_results=1)
                    req_end = datetime.now()

                    elapsed = (req_end - req_start).total_seconds()
                    logger.info(f"  Request {i}: {elapsed:.2f}s (expected ~1s minimum)")

                    if elapsed < 0.9:  # Allow some tolerance
                        logger.warning(f"    ⚠ Request {i} was too fast ({elapsed:.2f}s)")

                total_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"Total time for 3 requests: {total_time:.2f}s (expected ~3s)")

                # Should take at least ~2-3 seconds with rate limiting
                if total_time >= 2.0:
                    logger.info("✓ Rate limiting is enforced")
                    return True
                else:
                    logger.warning("✗ Rate limiting may not be working")
                    return False

        except Exception as e:
            logger.error(f"✗ Rate limiting test failed: {e}")
            return False

    async def test_quota_tracking(self):
        """Test 4: Quota tracking accuracy."""
        logger.info("=" * 70)
        logger.info("TEST 4: Quota Tracking")
        logger.info("=" * 70)

        try:
            async with GoogleBooksClient(api_key=self.api_key, max_requests_per_day=900) as client:
                # Get initial status
                status = client.get_rate_limit_status()
                logger.info(f"Initial quota status:")
                logger.info(f"  Requests used: {status['requests_used']}")
                logger.info(f"  Max requests: {status['max_requests']}")
                logger.info(f"  Requests remaining: {status['requests_remaining']}")
                logger.info(f"  Reset in: {status['reset_in']}")

                # Make a request
                logger.info(f"Making test request...")
                results = await client.search(title="Test", max_results=1)

                # Check updated status
                status_after = client.get_rate_limit_status()
                logger.info(f"After request:")
                logger.info(f"  Requests used: {status_after['requests_used']}")
                logger.info(f"  Requests remaining: {status_after['requests_remaining']}")

                # Verify counter incremented
                if status_after['requests_used'] > status['requests_used']:
                    logger.info("✓ Quota tracking is accurate")
                    return True
                else:
                    logger.warning("✗ Quota tracking not incrementing")
                    return False

        except Exception as e:
            logger.error(f"✗ Quota tracking test failed: {e}")
            return False

    async def test_metadata_extraction(self):
        """Test 5: Metadata extraction correctness."""
        logger.info("=" * 70)
        logger.info("TEST 5: Metadata Extraction")
        logger.info("=" * 70)

        try:
            async with GoogleBooksClient(api_key=self.api_key, max_requests_per_day=900) as client:
                title, author = self.test_books[0]
                logger.info(f"Searching and extracting metadata for '{title}'...")

                metadata = await client.search_and_extract(title=title, author=author)

                if not metadata:
                    logger.warning("✗ No metadata returned")
                    return False

                # Check required fields
                required_fields = ['title', 'authors', 'description', 'google_books_id']
                missing_fields = [f for f in required_fields if not metadata.get(f)]

                if missing_fields:
                    logger.warning(f"✗ Missing fields: {missing_fields}")
                    return False

                logger.info("✓ Metadata extracted successfully:")
                logger.info(f"  Title: {metadata.get('title')}")
                logger.info(f"  Authors: {metadata.get('authors_string')}")
                logger.info(f"  Published: {metadata.get('published_date')}")
                logger.info(f"  ISBN-13: {metadata.get('isbn_13')}")
                logger.info(f"  Categories: {metadata.get('categories_string')}")

                return True

        except Exception as e:
            logger.error(f"✗ Metadata extraction test failed: {e}")
            return False

    async def test_error_handling(self):
        """Test 6: Error handling for invalid queries."""
        logger.info("=" * 70)
        logger.info("TEST 6: Error Handling")
        logger.info("=" * 70)

        try:
            async with GoogleBooksClient(api_key=self.api_key, max_requests_per_day=900) as client:
                # Try searching for non-existent book
                logger.info("Searching for non-existent book...")
                results = await client.search(
                    title="XYZ_DEFINITELY_NONEXISTENT_12345",
                    author="FAKE_AUTHOR_XYZ"
                )

                if results:
                    logger.warning(f"✗ Found unexpected results: {len(results)}")
                    return False
                else:
                    logger.info("✓ Correctly returned no results for invalid query")

                # Try with ISBN
                logger.info("Searching by ISBN...")
                results_isbn = await client.search(isbn="9780451524935")  # 1984

                if results_isbn:
                    logger.info(f"✓ ISBN search returned {len(results_isbn)} results")
                    return True
                else:
                    logger.warning("✗ ISBN search failed")
                    return False

        except Exception as e:
            logger.error(f"✗ Error handling test failed: {e}")
            return False

    async def test_batch_processing(self):
        """Test 7: Batch processing with quota awareness."""
        logger.info("=" * 70)
        logger.info("TEST 7: Batch Processing")
        logger.info("=" * 70)

        try:
            async with GoogleBooksClient(api_key=self.api_key, max_requests_per_day=900) as client:
                logger.info(f"Processing {len(self.test_books)} books...")

                successful = 0
                failed = 0
                start_time = datetime.now()

                for i, (title, author) in enumerate(self.test_books, 1):
                    try:
                        metadata = await client.search_and_extract(title=title, author=author)
                        if metadata:
                            successful += 1
                            logger.info(f"  [{i}/{len(self.test_books)}] ✓ {title}")
                        else:
                            failed += 1
                            logger.warning(f"  [{i}/{len(self.test_books)}] ✗ {title} (no metadata)")
                    except GoogleBooksRateLimitError:
                        logger.error(f"  [{i}/{len(self.test_books)}] ✗ Rate limit exceeded")
                        break
                    except Exception as e:
                        failed += 1
                        logger.warning(f"  [{i}/{len(self.test_books)}] ✗ {title}: {e}")

                elapsed = (datetime.now() - start_time).total_seconds()
                logger.info(f"\nBatch Results:")
                logger.info(f"  Successful: {successful}")
                logger.info(f"  Failed: {failed}")
                logger.info(f"  Total time: {elapsed:.1f}s")
                logger.info(f"  Avg time per book: {elapsed/len(self.test_books):.1f}s")

                # Check quota status
                status = client.get_rate_limit_status()
                logger.info(f"  Quota used: {status['requests_used']}/{status['max_requests']}")

                return successful >= 7  # At least 70% success rate

        except Exception as e:
            logger.error(f"✗ Batch processing test failed: {e}")
            return False

    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests and return results."""
        logger.info("\n" + "=" * 70)
        logger.info("GOOGLE BOOKS API INTEGRATION TEST SUITE")
        logger.info("=" * 70 + "\n")

        logger.info("Rate Limit Specifications:")
        logger.info("  - Daily quota: 1,000 requests (using 900 as safe limit)")
        logger.info("  - Per-second: 1 request minimum")
        logger.info("  - Cache TTL: 24 hours")
        logger.info("  - Error response: HTTP 429")
        logger.info("")

        results = {
            "basic_search": await self.test_basic_search(),
            "cache_effectiveness": await self.test_cache_effectiveness(),
            "rate_limiting": await self.test_rate_limiting(),
            "quota_tracking": await self.test_quota_tracking(),
            "metadata_extraction": await self.test_metadata_extraction(),
            "error_handling": await self.test_error_handling(),
            "batch_processing": await self.test_batch_processing(),
        }

        # Print summary
        logger.info("\n" + "=" * 70)
        logger.info("TEST SUMMARY")
        logger.info("=" * 70)

        passed = sum(1 for v in results.values() if v)
        total = len(results)

        for test_name, passed_test in results.items():
            status = "PASSED" if passed_test else "FAILED"
            logger.info(f"  {test_name}: {status}")

        logger.info(f"\nTotal: {passed}/{total} passed")
        logger.info("=" * 70 + "\n")

        return results


async def main():
    """Main test execution."""
    try:
        tester = GoogleBooksIntegrationTest()
        results = await tester.run_all_tests()

        # Exit with appropriate code
        exit_code = 0 if all(results.values()) else 1
        sys.exit(exit_code)

    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        sys.exit(2)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
