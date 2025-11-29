"""
Test suite for Hardcover client
Tests all resolution stages and error handling

Run with: python test_hardcover_client.py
"""

import asyncio
import os
import logging
from backend.integrations.hardcover_client import (
    HardcoverClient,
    ResolutionResult,
    HardcoverBook
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestHardcoverClient:
    """Test suite for Hardcover client"""

    def __init__(self):
        self.api_token = os.getenv("HARDCOVER_TOKEN")
        if not self.api_token:
            raise ValueError("HARDCOVER_TOKEN environment variable not set")

        self.test_results = []

    async def run_all_tests(self):
        """Run all tests"""
        logger.info("Starting Hardcover client tests...")
        logger.info(f"Using token: {self.api_token[:10]}...")

        async with HardcoverClient(self.api_token) as client:
            # Stage 1 tests
            await self.test_isbn_resolution(client)
            await self.test_isbn_not_found(client)

            # Stage 2 tests
            await self.test_title_author_resolution(client)
            await self.test_title_author_not_found(client)

            # Stage 3 tests
            await self.test_fuzzy_search(client)

            # Waterfall test
            await self.test_waterfall_resolution(client)

            # Series test
            await self.test_series_retrieval(client)

            # Caching test
            await self.test_caching(client)

        self.print_summary()

    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "[PASS]" if passed else "[FAIL]"
        msg = f"{status} {test_name}"
        if details:
            msg += f" - {details}"

        logger.info(msg)
        self.test_results.append({
            'name': test_name,
            'passed': passed,
            'details': details
        })

    # ========================================================================
    # Stage 1: ISBN Tests
    # ========================================================================

    async def test_isbn_resolution(self, client: HardcoverClient):
        """Test 1: ISBN resolution (Stage 1)"""
        test_name = "ISBN Resolution"

        try:
            # Use a well-known book ISBN
            result = await client.resolve_by_isbn("9780593135204")  # Project Hail Mary

            if result.success:
                self.log_test(
                    test_name,
                    True,
                    f"Resolved to: {result.book.title}"
                )
                return

        except Exception as e:
            pass

        # If API token invalid or network down, skip
        self.log_test(test_name, False, "Unable to test (API unavailable)")

    async def test_isbn_not_found(self, client: HardcoverClient):
        """Test 2: ISBN not found (graceful failure)"""
        test_name = "ISBN Not Found"

        try:
            # Use invalid ISBN
            result = await client.resolve_by_isbn("9999999999999")

            if not result.success:
                self.log_test(
                    test_name,
                    True,
                    f"Correctly returned failure: {result.note}"
                )
                return

        except Exception as e:
            pass

        self.log_test(test_name, False, "Test inconclusive")

    # ========================================================================
    # Stage 2: Title + Author Tests
    # ========================================================================

    async def test_title_author_resolution(self, client: HardcoverClient):
        """Test 3: Title + Author resolution (Stage 2)"""
        test_name = "Title+Author Resolution"

        try:
            result = await client.resolve_by_title_author(
                "The Way of Kings",
                "Brandon Sanderson"
            )

            if result.success:
                self.log_test(
                    test_name,
                    True,
                    f"Resolved to: {result.book.title}"
                )
                return

        except Exception as e:
            pass

        self.log_test(test_name, False, "Unable to test (API unavailable)")

    async def test_title_author_not_found(self, client: HardcoverClient):
        """Test 4: Title+Author not found (graceful failure)"""
        test_name = "Title+Author Not Found"

        try:
            result = await client.resolve_by_title_author(
                "This Book Definitely Does Not Exist Blah Blah",
                "Nonexistent Author Xyz"
            )

            if not result.success:
                self.log_test(
                    test_name,
                    True,
                    f"Correctly returned failure"
                )
                return

        except Exception as e:
            pass

        self.log_test(test_name, False, "Test inconclusive")

    # ========================================================================
    # Stage 3: Fuzzy Search Tests
    # ========================================================================

    async def test_fuzzy_search(self, client: HardcoverClient):
        """Test 5: Fuzzy search (Stage 3)"""
        test_name = "Fuzzy Search"

        try:
            # Search with partial info
            result = await client.resolve_by_search("Dune Frank Herbert")

            if result.success:
                self.log_test(
                    test_name,
                    True,
                    f"Found: {result.book.title}"
                )
                return

        except Exception as e:
            pass

        self.log_test(test_name, False, "Unable to test")

    # ========================================================================
    # Waterfall Tests
    # ========================================================================

    async def test_waterfall_resolution(self, client: HardcoverClient):
        """Test 6: Complete waterfall resolution"""
        test_name = "Waterfall Resolution"

        try:
            # Should use Stage 2 (title+author)
            result = await client.resolve_book(
                title="The Name of the Wind",
                author="Patrick Rothfuss"
            )

            if result.success:
                self.log_test(
                    test_name,
                    True,
                    f"Method: {result.resolution_method}, Confidence: {result.confidence}"
                )
                return

        except Exception as e:
            pass

        self.log_test(test_name, False, "Unable to test")

    # ========================================================================
    # Series Tests
    # ========================================================================

    async def test_series_retrieval(self, client: HardcoverClient):
        """Test 7: Retrieve books in a series"""
        test_name = "Series Retrieval"

        try:
            # First, resolve a book we know is in a series
            result = await client.resolve_book(
                title="The Way of Kings",
                author="Brandon Sanderson"
            )

            if result.success:
                primary_series = result.book.get_primary_series()
                if primary_series:
                    self.log_test(
                        test_name,
                        True,
                        f"Series: {primary_series[0]} (position {primary_series[1]})"
                    )
                    return

        except Exception as e:
            pass

        self.log_test(test_name, False, "Unable to test")

    # ========================================================================
    # Caching Tests
    # ========================================================================

    async def test_caching(self, client: HardcoverClient):
        """Test 8: Caching (second call should be instant)"""
        test_name = "Caching"

        try:
            import time

            # First call (cache miss)
            start = time.time()
            result1 = await client.resolve_by_title_author(
                "The Martian",
                "Andy Weir"
            )
            time1 = time.time() - start

            # Second call (cache hit)
            start = time.time()
            result2 = await client.resolve_by_title_author(
                "The Martian",
                "Andy Weir"
            )
            time2 = time.time() - start

            # Cache hit should be significantly faster
            if time2 < time1 * 0.5:  # At least 2x faster
                self.log_test(
                    test_name,
                    True,
                    f"Cache miss: {time1*1000:.0f}ms, Cache hit: {time2*1000:.0f}ms"
                )
                return
            else:
                self.log_test(
                    test_name,
                    False,
                    f"Cache not significantly faster: {time1*1000:.0f}ms vs {time2*1000:.0f}ms"
                )
                return

        except Exception as e:
            pass

        self.log_test(test_name, False, "Unable to test")

    # ========================================================================
    # Results
    # ========================================================================

    def print_summary(self):
        """Print test summary"""
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)

        passed = sum(1 for r in self.test_results if r['passed'])
        total = len(self.test_results)

        for result in self.test_results:
            status = "[PASS]" if result['passed'] else "[FAIL]"
            msg = f"{status} {result['name']}"
            if result['details']:
                msg += f" - {result['details']}"
            logger.info(msg)

        logger.info("="*80)
        logger.info(f"Results: {passed}/{total} passed")
        logger.info("="*80)

        if passed == total:
            logger.info("All tests passed!")
            return True
        else:
            logger.warning(f"{total - passed} tests failed")
            return False


async def main():
    """Run test suite"""
    try:
        tester = TestHardcoverClient()
        await tester.run_all_tests()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please set HARDCOVER_TOKEN environment variable")


if __name__ == "__main__":
    asyncio.run(main())
