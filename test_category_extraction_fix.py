# test_category_extraction_fix.py
# Comprehensive verification of category extraction logic

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


def test_category_extraction():
    """Comprehensive category extraction test."""
    print("=" * 70)
    print("Category Extraction Comprehensive Test")
    print("=" * 70)

    crawler = TestCrawler()

    test_cases = [
        # (URL, Expected Category, Description)

        # Homepage patterns
        ("https://www.myanonamouse.net", "General", "Homepage without trailing slash"),
        ("https://www.myanonamouse.net/", "General", "Homepage with trailing slash"),

        # Guide patterns (with gid query param)
        ("https://www.myanonamouse.net/guides/?gid=123", "Guide", "Guide with gid param"),
        ("https://www.myanonamouse.net/guides?gid=456", "Guide", "Guide with gid (no trailing slash)"),

        # Guides section (without gid)
        ("https://www.myanonamouse.net/guides/", "Guide", "Guides section with trailing slash"),
        ("https://www.myanonamouse.net/guides", "Guide", "Guides section without trailing slash"),

        # Torrent page patterns: /t/<category>/<id>
        ("https://www.myanonamouse.net/t/audiobooks/12345", "Audiobooks", "Torrent audiobooks with ID"),
        ("https://www.myanonamouse.net/t/ebooks/67890", "Ebooks", "Torrent ebooks with ID"),
        ("https://www.myanonamouse.net/t/music/11111", "Music", "Torrent music with ID"),
        ("https://www.myanonamouse.net/t/fiction-audiobooks/22222", "Fiction Audiobooks", "Multi-word category with hyphen"),
        ("https://www.myanonamouse.net/t/non_fiction/33333", "Non Fiction", "Category with underscore"),

        # Forum patterns: /f/<category>/...
        ("https://www.myanonamouse.net/f/mam-help/", "Mam Help", "Forum mam-help with trailing slash"),
        ("https://www.myanonamouse.net/f/mam-help", "Mam Help", "Forum mam-help without trailing slash"),
        ("https://www.myanonamouse.net/f/general-discussion/topic/123", "General Discussion", "Forum with topic path"),
        ("https://www.myanonamouse.net/f/announcements/", "Announcements", "Forum announcements"),
        ("https://www.myanonamouse.net/f/tech_support/thread/456", "Tech Support", "Forum with underscore"),
        
        # Torrent browse/search patterns
        ("https://www.myanonamouse.net/tor/browse.php", "Torrent", "Browse page"),
        ("https://www.myanonamouse.net/tor/search.php", "Torrent", "Search page"),
        ("https://www.myanonamouse.net/tor/browse.php?cat=13", "Torrent", "Browse with query params"),

        # Other patterns (default to first segment)
        ("https://www.myanonamouse.net/some-section/page", "Some Section", "Custom section with hyphen"),
        ("https://www.myanonamouse.net/user_profile/123", "User Profile", "User profile with underscore"),
        ("https://www.myanonamouse.net/wiki/article", "Wiki", "Wiki section"),
    ]

    passed = 0
    failed = 0
    failures = []

    print("\nRunning category extraction tests:\n")

    for url, expected, description in test_cases:
        result = crawler.extract_category_from_url(url)
        status = "✅ PASS" if result == expected else "❌ FAIL"

        if result == expected:
            passed += 1
        else:
            failed += 1
            failures.append((url, expected, result, description))

        # Truncate URL for display
        url_display = url if len(url) <= 55 else url[:52] + "..."
        print(f"{status} | {description}")
        print(f"       URL: {url_display}")
    print(f"       Result: '{result}' " + ("✓" if result == expected else f"(expected: '{expected}')"))

    # Summary
    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed > 0:
        print("\nFailed Test Details:")
        print("-" * 70)
        for url, expected, got, desc in failures:
            print(f"\n  {desc}")
            print(f"  URL: {url}")
            print(f"  Expected: '{expected}'")
            print(f"  Got: '{got}'")

    if failed == 0:
        print("\n✅ All category extraction tests passed!")
        print("\nVerified patterns:")
        print("  ✓ Homepage → 'General'")
        print("  ✓ /guides/?gid=X → 'Guide'")
        print("  ✓ /guides/ → 'Guide'")
        print("  ✓ /t/<category>/<id> → category (normalized)")
        print("  ✓ /f/<category>/... → category (normalized)")
        print("  ✓ /tor/browse.php → 'Torrent'")
        print("  ✓ Hyphen/underscore normalization → spaces + title case")
        return True
    else:
        print(f"\n❌ {failed} test(s) failed - category extraction needs fixes")
        return False


if __name__ == "__main__":
    success = test_category_extraction()
    sys.exit(0 if success else 1)
