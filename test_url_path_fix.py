# test_url_path_fix.py
# Verification test for URL path validation bug fix

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from mamcrawler.core.utils import MAMUtils

def test_url_path_fix():
    """Test that the URL path validation bug is fixed"""
    print("="*60)
    print("URL Path Validation Fix Verification")
    print("="*60)

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
        ("https://www.myanonamouse.net//guides/", False, "Double slash (invalid)"),
        ("https://www.myanonamouse.net/admin/", False, "Admin section (forbidden)"),
        ("https://www.myanonamouse.net/upload.php", False, "Upload page (forbidden)"),
        ("https://www.example.com/", False, "Wrong domain"),
        ("", False, "Empty string"),
        ("not-a-url", False, "Invalid URL"),
    ]

    passed = 0
    failed = 0

    print("\nRunning tests...\n")

    for url, expected, description in test_cases:
        result = MAMUtils.is_allowed_path(url)
        status = "✅ PASS" if result == expected else "❌ FAIL"

        if result == expected:
            passed += 1
        else:
            failed += 1

        # Truncate URL for display if too long
        url_display = url if len(url) <= 50 else url[:47] + "..."

        print(f"{status} | {description}")
        print(f"       URL: {url_display}")
        print(f"       Expected: {expected}, Got: {result}\n")

    print("="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)

    if failed == 0:
        print("\n🎉 All tests passed! Bug fix successful.")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) failed. Bug fix incomplete.")
        return False

if __name__ == "__main__":
    success = test_url_path_fix()
    sys.exit(0 if success else 1)
