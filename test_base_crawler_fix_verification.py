# test_base_crawler_fix_verification.py
# Verification test for base_crawler.py bug fixes

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from mamcrawler.core.base_crawler import BaseMAMCrawler
from typing import Dict, Any


class TestCrawler(BaseMAMCrawler):
    """Minimal concrete implementation for testing."""

    async def authenticate(self) -> bool:
        return True

    async def crawl_page(self, url: str, **kwargs) -> Dict[str, Any]:
        return {'success': True, 'url': url}


def test_url_path_validation_fix():
    """Verify URL path validation bug is fixed."""
    print("=" * 60)
    print("URL Path Validation Fix Verification")
    print("=" * 60)

    crawler = TestCrawler()

    test_cases = [
        # (URL, Expected, Description)
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
    ]

    passed = 0
    failed = 0

    print("\nRunning URL validation tests:\n")

    for url, expected, description in test_cases:
        result = crawler.is_allowed_path(url)
        status = "✅ PASS" if result == expected else "❌ FAIL"

        if result == expected:
            passed += 1
        else:
            failed += 1

        url_display = url if len(url) <= 50 else url[:47] + "..."
        print(f"{status} | {description}")
        if result != expected:
            print(f"       URL: {url_display}")
            print(f"       Expected: {expected}, Got: {result}")

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("\n✅ All URL validation tests passed! Bug fix successful.")
        return True
    else:
        print(f"\n❌ {failed} test(s) failed. Bug fix incomplete.")
        return False


def test_category_extraction_fix():
    """Verify category extraction bug is fixed."""
    print("\n" + "=" * 60)
    print("Category Extraction Fix Verification")
    print("=" * 60)

    crawler = TestCrawler()

    test_cases = [
        ("https://www.myanonamouse.net/guides/?gid=123", "Guide"),
        ("https://www.myanonamouse.net/t/audiobooks/12345", "Audiobooks"),
        ("https://www.myanonamouse.net/f/mam-help/", "Mam Help"),
        ("https://www.myanonamouse.net/f/mam-help", "Mam Help"),
        ("https://www.myanonamouse.net/some-category/page", "Some Category"),
        ("https://www.myanonamouse.net/", "General"),
    ]

    passed = 0
    failed = 0

    print("\nRunning category extraction tests:\n")

    for url, expected in test_cases:
        result = crawler.extract_category_from_url(url)
        status = "✅ PASS" if result == expected else "❌ FAIL"

        if result == expected:
            passed += 1
        else:
            failed += 1

        url_display = url if len(url) <= 45 else url[:42] + "..."
        print(f"{status} | {url_display:<45} → '{result}' (expected: '{expected}')")

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("\n✅ All category extraction tests passed! Bug fix successful.")
        return True
    else:
        print(f"\n❌ {failed} test(s) failed. Bug fix incomplete.")
        return False


def main():
    """Run both verification tests."""
    print("\n" + "=" * 60)
    print("Base Crawler Bug Fix Verification Suite")
    print("=" * 60)

    test1 = test_url_path_validation_fix()
    test2 = test_category_extraction_fix()

    print("\n" + "=" * 60)
    print("Final Summary")
    print("=" * 60)

    if test1 and test2:
        print("\n🎉 All bug fixes verified successfully!")
        print("\nFixed Issues:")
        print("  1. ✅ URL path validation now handles URLs without trailing slashes")
        print("  2. ✅ Category extraction correctly parses URL path segments")
        return True
    else:
        print("\n⚠️  Some bug fixes failed verification")
        if not test1:
            print("  ❌ URL path validation still has issues")
        if not test2:
            print("  ❌ Category extraction still has issues")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
