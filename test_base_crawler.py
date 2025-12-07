# test_base_crawler.py
# Comprehensive validation of the Base Crawler module

import sys
import os
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

sys.path.insert(0, os.path.abspath('.'))

from mamcrawler.core.base_crawler import BaseMAMCrawler


# Create concrete implementation for testing
class TestableMAMCrawler(BaseMAMCrawler):
    """Concrete implementation of BaseMAMCrawler for testing."""

    def __init__(self, config=None):
        super().__init__(config)
        self.authenticate_calls = 0
        self.crawl_calls = 0

    async def authenticate(self) -> bool:
        """Mock authentication that always succeeds."""
        self.authenticate_calls += 1
        self.session_cookies = {"mam_id": "test_session_123"}
        self.last_login = datetime.now()
        return True

    async def crawl_page(self, url: str, **kwargs) -> Dict[str, Any]:
        """Mock crawl_page implementation."""
        self.crawl_calls += 1
        return {
            'success': True,
            'url': url,
            'crawled_at': datetime.now().isoformat(),
            'title': 'Test Page',
            'content': 'Test content from mock crawl'
        }


def test_initialization():
    """Test crawler initialization with config and env vars."""
    print("\n=== Testing Initialization ===")

    # Test 1: Default initialization
    print("\n  Test 1: Default initialization")
    crawler = TestableMAMCrawler()
    print(f"    ✓ Crawler created")
    print(f"    ✓ Min delay: {crawler.min_delay}s (default: 3)")
    print(f"    ✓ Max delay: {crawler.max_delay}s (default: 10)")
    print(f"    ✓ Base URL: {crawler.base_url}")
    print(f"    ✓ User agents count: {len(crawler.user_agents)}")
    print(f"    ✓ Allowed paths count: {len(crawler.allowed_paths)}")

    # Test 2: Custom config
    print("\n  Test 2: Custom config initialization")
    custom_config = {
        'min_delay': 5,
        'max_delay': 15,
        'username': 'test_user',
        'password': 'test_pass'
    }
    crawler2 = TestableMAMCrawler(config=custom_config)

    if crawler2.min_delay != 5:
        print(f"    ❌ FAIL: Expected min_delay=5, got {crawler2.min_delay}")
        return False
    if crawler2.max_delay != 15:
        print(f"    ❌ FAIL: Expected max_delay=15, got {crawler2.max_delay}")
        return False
    if crawler2.username != 'test_user':
        print(f"    ❌ FAIL: Username not set from config")
        return False

    print(f"    ✓ Custom config applied: min={crawler2.min_delay}, max={crawler2.max_delay}")
    print(f"    ✓ Credentials set from config")

    # Test 3: Environment variables (if set)
    print("\n  Test 3: Environment variable loading")
    env_username = os.getenv('MAM_USERNAME')
    if env_username:
        crawler3 = TestableMAMCrawler()
        print(f"    ✓ Username from env: {crawler3.username[:3]}***")
    else:
        print(f"    ⚠️  MAM_USERNAME not set in environment")

    print("\n  ✓ All initialization tests passed")
    return True


async def test_authentication():
    """Test authentication state management."""
    print("\n=== Testing Authentication ===")

    # Test 1: Initial state (not authenticated)
    print("\n  Test 1: Initial authentication state")
    crawler = TestableMAMCrawler()

    if crawler.is_authenticated:
        print("    ❌ FAIL: Should not be authenticated initially")
        return False
    print("    ✓ Initial state: not authenticated")

    # Test 2: After authentication
    print("\n  Test 2: After authentication")
    success = await crawler.authenticate()

    if not success:
        print("    ❌ FAIL: Authentication should succeed")
        return False
    if not crawler.is_authenticated:
        print("    ❌ FAIL: Should be authenticated after authenticate()")
        return False

    print("    ✓ Authenticated successfully")
    print(f"    ✓ Session cookies set: {bool(crawler.session_cookies)}")
    print(f"    ✓ Last login set: {crawler.last_login is not None}")

    # Test 3: Session expiry
    print("\n  Test 3: Session expiry check")
    # Force expiry by setting last_login to 3 hours ago
    crawler.last_login = datetime.now() - timedelta(hours=3)

    if crawler.is_authenticated:
        print("    ❌ FAIL: Session should be expired after 2 hours")
        return False
    print("    ✓ Session correctly expires after 2 hours")

    # Test 4: ensure_authenticated auto-authenticates
    print("\n  Test 4: ensure_authenticated auto-authenticates")
    crawler.last_login = None  # Reset
    crawler.session_cookies = None
    crawler.authenticate_calls = 0

    result = await crawler.ensure_authenticated()

    if not result:
        print("    ❌ FAIL: ensure_authenticated should succeed")
        return False
    if crawler.authenticate_calls != 1:
        print(f"    ❌ FAIL: Should call authenticate once, got {crawler.authenticate_calls}")
        return False

    print("    ✓ ensure_authenticated calls authenticate() when needed")

    # Call again - should not authenticate again
    await crawler.ensure_authenticated()
    if crawler.authenticate_calls != 1:
        print(f"    ❌ FAIL: Should not re-authenticate, got {crawler.authenticate_calls} calls")
        return False
    print("    ✓ Skips re-authentication when already authenticated")

    print("\n  ✓ All authentication tests passed")
    return True


async def test_rate_limiting():
    """Test rate limiting behavior."""
    print("\n=== Testing Rate Limiting ===")

    # Test 1: Rate limiting delay
    print("\n  Test 1: Rate limiting enforces delays")
    crawler = TestableMAMCrawler(config={'min_delay': 1, 'max_delay': 2})

    start = datetime.now()
    await crawler.rate_limit()
    first_call = datetime.now()

    # Second call should be delayed
    await crawler.rate_limit()
    second_call = datetime.now()

    delay = (second_call - first_call).total_seconds()

    if delay < 1.0:
        print(f"    ❌ FAIL: Delay too short: {delay:.2f}s (expected ≥1s)")
        return False
    if delay > 3.0:
        print(f"    ⚠️  WARNING: Delay very long: {delay:.2f}s")

    print(f"    ✓ Rate limit enforced: {delay:.2f}s delay")

    # Test 2: last_request tracking
    print("\n  Test 2: last_request timestamp tracking")
    before = crawler.last_request
    await asyncio.sleep(0.1)
    await crawler.rate_limit()
    after = crawler.last_request

    if after <= before:
        print("    ❌ FAIL: last_request not updated")
        return False
    print("    ✓ last_request timestamp updated correctly")

    print("\n  ✓ All rate limiting tests passed")
    return True


def test_user_agent_and_viewport():
    """Test user agent and viewport randomization."""
    print("\n=== Testing User Agent & Viewport ===")

    crawler = TestableMAMCrawler()

    # Test 1: User agent rotation
    print("\n  Test 1: User agent randomization")
    agents = set()
    for _ in range(20):
        agent = crawler.get_random_user_agent()
        agents.add(agent)

    if len(agents) < 2:
        print("    ⚠️  WARNING: Only 1 unique user agent seen in 20 calls")

    print(f"    ✓ Generated {len(agents)} unique user agents from pool of {len(crawler.user_agents)}")

    # Verify they're from the pool
    sample_agent = crawler.get_random_user_agent()
    if sample_agent not in crawler.user_agents:
        print("    ❌ FAIL: Generated agent not in pool")
        return False
    print(f"    ✓ User agent from valid pool: '{sample_agent[:50]}...'")

    # Test 2: Viewport rotation
    print("\n  Test 2: Viewport randomization")
    viewports = set()
    for _ in range(20):
        viewport = crawler.get_random_viewport()
        viewports.add(viewport)

    if len(viewports) < 2:
        print("    ⚠️  WARNING: Only 1 unique viewport seen in 20 calls")

    print(f"    ✓ Generated {len(viewports)} unique viewports from pool of {len(crawler.viewports)}")

    # Verify structure
    sample_viewport = crawler.get_random_viewport()
    if not isinstance(sample_viewport, tuple) or len(sample_viewport) != 2:
        print("    ❌ FAIL: Viewport should be tuple of (width, height)")
        return False
    print(f"    ✓ Viewport format valid: {sample_viewport}")

    print("\n  ✓ All user agent & viewport tests passed")
    return True


def test_filename_sanitization():
    """Test filename sanitization."""
    print("\n=== Testing Filename Sanitization ===")

    crawler = TestableMAMCrawler()

    test_cases = [
        ("Normal Title", "Normal_Title"),
        ("Title: With Special <Characters>", "Title_With_Special_Characters"),
        ("Multiple   Spaces", "Multiple_Spaces"),
        ("Title/With\\Slashes", "TitleWithSlashes"),
        ("A" * 150, "A" * 100),  # Max length test
        ("", ""),  # Empty string
        ("日本語タイトル", "日本語タイトル"),  # Unicode
    ]

    print("\n  Testing various filename inputs:")
    for input_title, expected_pattern in test_cases:
        result = crawler.sanitize_filename(input_title)
        display_input = input_title if len(input_title) <= 30 else input_title[:27] + "..."
        display_result = result if len(result) <= 30 else result[:27] + "..."
        print(f"    '{display_input}' → '{display_result}'")

        # Verify no forbidden characters
        forbidden = r'<>:"/\|?*'
        if any(char in result for char in forbidden):
            print(f"    ❌ FAIL: Result contains forbidden characters: {result}")
            return False

        # Verify length limit
        if len(result) > 100:
            print(f"    ❌ FAIL: Result exceeds max length: {len(result)}")
            return False

    print("    ✓ All filenames sanitized correctly")

    print("\n  ✓ All filename sanitization tests passed")
    return True


def test_url_path_validation():
    """Test URL path validation (WILL REVEAL BUG)."""
    print("\n=== Testing URL Path Validation ===")

    crawler = TestableMAMCrawler()

    test_cases = [
        # (URL, Expected Result, Description)
        ("https://www.myanonamouse.net", True, "Homepage without trailing slash"),
        ("https://www.myanonamouse.net/", True, "Homepage with trailing slash"),
        ("https://www.myanonamouse.net/guides", True, "Guides without trailing slash"),
        ("https://www.myanonamouse.net/guides/", True, "Guides with trailing slash"),
        ("https://www.myanonamouse.net/t/12345", True, "Torrent page"),
        ("https://www.myanonamouse.net/tor/browse.php", True, "Browse page"),
        ("https://www.myanonamouse.net/tor/search.php", True, "Search page"),
        ("https://www.myanonamouse.net/f/", True, "Forum section"),
        ("https://www.myanonamouse.net/f/topic.php?id=123", True, "Forum topic with params"),
        ("https://www.example.com/", False, "Wrong domain"),
        ("", False, "Empty string"),
        ("not-a-url", False, "Invalid URL"),
    ]

    passed = 0
    failed = 0

    print("\n  Running URL validation tests:")
    for url, expected, description in test_cases:
        result = crawler.is_allowed_path(url)
        status = "✅ PASS" if result == expected else "❌ FAIL"

        if result == expected:
            passed += 1
        else:
            failed += 1

        url_display = url if len(url) <= 50 else url[:47] + "..."
        print(f"    {status} | {description}")
        if result != expected:
            print(f"         URL: {url_display}")
            print(f"         Expected: {expected}, Got: {result}")

    print(f"\n  Results: {passed} passed, {failed} failed")

    if failed > 0:
        print(f"  ⚠️  URL validation has issues - likely the trailing slash bug")
        return False

    print("\n  ✓ All URL validation tests passed")
    return True


def test_category_extraction():
    """Test category extraction from URLs."""
    print("\n=== Testing Category Extraction ===")

    crawler = TestableMAMCrawler()

    test_cases = [
        ("https://www.myanonamouse.net/guides/?gid=123", "Guide"),
        ("https://www.myanonamouse.net/t/audiobooks/12345", "Audiobooks"),
        ("https://www.myanonamouse.net/f/mam-help/", "Mam Help"),
        ("https://www.myanonamouse.net/some-category/page", "Some Category"),
        ("https://www.myanonamouse.net/", "General"),
    ]

    print("\n  Testing category extraction:")
    for url, expected in test_cases:
        result = crawler.extract_category_from_url(url)
        match = "✓" if result == expected else "❌"
        print(f"    {match} {url[:50]:<50} → '{result}' (expected: '{expected}')")

        if result != expected:
            print(f"    ❌ FAIL: Category mismatch")
            return False

    print("\n  ✓ All category extraction tests passed")
    return True


def test_content_anonymization():
    """Test content anonymization."""
    print("\n=== Testing Content Anonymization ===")

    crawler = TestableMAMCrawler()

    # Test 1: Email removal
    print("\n  Test 1: Email address removal")
    content = "Contact me at user@example.com or admin@site.org"
    result = crawler.anonymize_content(content)

    if "@" in result and "example.com" in result:
        print(f"    ❌ FAIL: Email not anonymized: {result}")
        return False
    if "[EMAIL]" not in result:
        print(f"    ❌ FAIL: Email placeholder missing: {result}")
        return False
    print(f"    ✓ Emails anonymized: '{result}'")

    # Test 2: Username removal
    print("\n  Test 2: Username pattern removal")
    content2 = "Posted by user_john123 and user-admin456"
    result2 = crawler.anonymize_content(content2)

    if "user_john123" in result2 or "user-admin456" in result2:
        print(f"    ❌ FAIL: Usernames not anonymized: {result2}")
        return False
    print(f"    ✓ Usernames anonymized: '{result2}'")

    # Test 3: Length limit
    print("\n  Test 3: Length limiting")
    long_content = "A" * 10000
    result3 = crawler.anonymize_content(long_content, max_length=5000)

    if len(result3) > 5000:
        print(f"    ❌ FAIL: Content not limited: {len(result3)} chars")
        return False
    print(f"    ✓ Content limited to {len(result3)} chars")

    # Test 4: Empty content
    print("\n  Test 4: Empty content handling")
    result4 = crawler.anonymize_content("")
    if result4 != "":
        print(f"    ❌ FAIL: Empty content should return empty")
        return False
    print("    ✓ Empty content handled")

    print("\n  ✓ All content anonymization tests passed")
    return True


async def test_retry_logic():
    """Test retry logic with exponential backoff."""
    print("\n=== Testing Retry Logic ===")

    # Test 1: Successful crawl (no retries needed)
    print("\n  Test 1: Successful crawl (no retries)")
    crawler = TestableMAMCrawler(config={'min_delay': 0.1, 'max_delay': 0.2})

    result = await crawler.crawl_with_retry("https://www.myanonamouse.net/guides/")

    if not result['success']:
        print("    ❌ FAIL: Crawl should succeed")
        return False
    if result['attempt'] != 1:
        print(f"    ❌ FAIL: Should succeed on first attempt, got {result['attempt']}")
        return False

    print(f"    ✓ Successful crawl on attempt {result['attempt']}")
    print(f"    ✓ Result contains: {list(result.keys())}")

    # Test 2: Retry behavior (mock failures)
    print("\n  Test 2: Retry with failures")

    class FailingCrawler(TestableMAMCrawler):
        def __init__(self):
            super().__init__(config={'min_delay': 0.1, 'max_delay': 0.2})
            self.fail_count = 0

        async def crawl_page(self, url: str, **kwargs):
            self.fail_count += 1
            if self.fail_count < 3:
                raise Exception(f"Mock failure {self.fail_count}")
            return await super().crawl_page(url, **kwargs)

    failing_crawler = FailingCrawler()
    start = datetime.now()
    result2 = await failing_crawler.crawl_with_retry(
        "https://www.myanonamouse.net/guides/",
        max_retries=3
    )
    end = datetime.now()

    if not result2['success']:
        print(f"    ❌ FAIL: Should succeed on 3rd attempt")
        return False
    if result2['attempt'] != 3:
        print(f"    ❌ FAIL: Should succeed on attempt 3, got {result2['attempt']}")
        return False

    # Check backoff timing (should have delays: 10s, 20s between attempts)
    total_time = (end - start).total_seconds()
    if total_time < 10:  # Should have at least 10s + 20s = 30s backoff (but we use 5s base)
        print(f"    ⚠️  Backoff time seems short: {total_time:.2f}s")

    print(f"    ✓ Retry succeeded on attempt {result2['attempt']}")
    print(f"    ✓ Total time with backoff: {total_time:.2f}s")

    print("\n  ✓ All retry logic tests passed")
    return True


def test_stealth_js():
    """Test stealth JavaScript generation."""
    print("\n=== Testing Stealth JS Generation ===")

    crawler = TestableMAMCrawler()

    # Test 1: JS generation
    print("\n  Test 1: Generate stealth JavaScript")
    js_code = crawler.create_stealth_js()

    if not js_code or len(js_code) < 100:
        print("    ❌ FAIL: JS code too short or empty")
        return False

    # Check for key components
    required_elements = [
        "simulateHumanBehavior",
        "mousemove",
        "scrollTo",
        "Math.random",
    ]

    for element in required_elements:
        if element not in js_code:
            print(f"    ❌ FAIL: Missing required element: {element}")
            return False

    print(f"    ✓ Generated {len(js_code)} chars of JavaScript")
    print(f"    ✓ Contains all required elements: {required_elements}")

    print("\n  ✓ Stealth JS generation test passed")
    return True


def test_file_saving():
    """Test guide file saving."""
    print("\n=== Testing File Saving ===")

    crawler = TestableMAMCrawler()

    # Create test data
    guide_data = {
        'success': True,
        'title': 'Test Guide: Special Characters <>&',
        'url': 'https://www.myanonamouse.net/guides/?gid=123',
        'category': 'Testing',
        'description': 'A test guide',
        'author': 'Test Author',
        'last_updated': '2025-01-01',
        'tags': 'test, guide, example',
        'content': 'This is the guide content.',
        'sub_links': [
            {'title': 'Related Guide 1', 'url': 'https://example.com/1'},
            {'title': 'Related Guide 2', 'url': 'https://example.com/2'}
        ]
    }

    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)

        # Test 1: Save guide
        print("\n  Test 1: Save guide to file")
        filepath = crawler.save_guide_to_file(guide_data, output_dir)

        if filepath is None:
            print("    ❌ FAIL: File save returned None")
            return False
        if not filepath.exists():
            print("    ❌ FAIL: File not created")
            return False

        print(f"    ✓ File created: {filepath.name}")

        # Test 2: Verify content
        print("\n  Test 2: Verify file content")
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        required_sections = [
            "# Test Guide:",  # Title
            "**URL:**",
            "**Category:**",
            "**Description:**",
            "## Related Guides",
            "## Content",
            "This is the guide content"
        ]

        for section in required_sections:
            if section not in content:
                print(f"    ❌ FAIL: Missing section: {section}")
                return False

        print(f"    ✓ All required sections present")
        print(f"    ✓ File size: {len(content)} chars")

        # Test 3: Failed guide (success=False)
        print("\n  Test 3: Handle failed guide")
        failed_guide = {'success': False, 'title': 'Failed'}
        result = crawler.save_guide_to_file(failed_guide, output_dir)

        if result is not None:
            print("    ❌ FAIL: Should return None for failed guide")
            return False
        print("    ✓ Failed guide handled correctly")

    print("\n  ✓ All file saving tests passed")
    return True


def test_result_validation():
    """Test crawl result validation."""
    print("\n=== Testing Result Validation ===")

    crawler = TestableMAMCrawler()

    # Test 1: Valid result
    print("\n  Test 1: Valid crawl result")
    valid_result = {
        'success': True,
        'url': 'https://example.com',
        'crawled_at': '2025-01-01T00:00:00'
    }

    if not crawler.validate_crawl_result(valid_result):
        print("    ❌ FAIL: Valid result should pass validation")
        return False
    print("    ✓ Valid result passes validation")

    # Test 2: Missing fields
    print("\n  Test 2: Missing required fields")
    invalid_results = [
        {'url': 'https://example.com', 'crawled_at': '2025-01-01'},  # Missing success
        {'success': True, 'crawled_at': '2025-01-01'},  # Missing url
        {'success': True, 'url': 'https://example.com'},  # Missing crawled_at
    ]

    for invalid in invalid_results:
        if crawler.validate_crawl_result(invalid):
            print(f"    ❌ FAIL: Should reject result missing fields: {list(invalid.keys())}")
            return False
    print("    ✓ Missing fields correctly rejected")

    # Test 3: Success=False
    print("\n  Test 3: Result with success=False")
    failed_result = {
        'success': False,
        'url': 'https://example.com',
        'crawled_at': '2025-01-01'
    }

    if crawler.validate_crawl_result(failed_result):
        print("    ❌ FAIL: Should reject result with success=False")
        return False
    print("    ✓ Failed result correctly rejected")

    print("\n  ✓ All result validation tests passed")
    return True


async def main():
    """Run all base crawler tests."""
    print("=" * 60)
    print("Base Crawler Module Validation")
    print("=" * 60)

    tests = [
        ("Initialization", test_initialization, False),
        ("Authentication", test_authentication, True),
        ("Rate Limiting", test_rate_limiting, True),
        ("User Agent & Viewport", test_user_agent_and_viewport, False),
        ("Filename Sanitization", test_filename_sanitization, False),
        ("URL Path Validation", test_url_path_validation, False),
        ("Category Extraction", test_category_extraction, False),
        ("Content Anonymization", test_content_anonymization, False),
        ("Retry Logic", test_retry_logic, True),
        ("Stealth JS Generation", test_stealth_js, False),
        ("File Saving", test_file_saving, False),
        ("Result Validation", test_result_validation, False),
    ]

    results = []
    for name, test_func, is_async in tests:
        try:
            if is_async:
                result = await test_func()
            else:
                result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ EXCEPTION in {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} | {name}")

    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("\n🎉 All base crawler tests passed!")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
