import sys
import os
sys.path.insert(0, os.path.abspath("."))

from mamcrawler.core.utils import MAMUtils, RateLimiter, RetryPolicy
import asyncio

def test_url_validation():
    """Test URL validation functionality"""
    print("\n=== Testing URL Validation ===")

    # Valid URLs
    valid_urls = [
        "https://www.myanonamouse.net/",
        "https://www.myanonamouse.net/guides/",
        "https://www.myanonamouse.net/t/12345",
        "https://www.myanonamouse.net/tor/browse.php",
    ]

    # Invalid URLs
    invalid_urls = [
        "https://www.myanonamouse.net/admin/",
        "https://www.example.com/",
        "https://www.myanonamouse.net/upload.php",
        "not-a-url",
    ]

    print("Valid URLs (should return True):")
    for url in valid_urls:
        result = MAMUtils.is_allowed_path(url)
        print(f"  {url}: {result}")

    print("\nInvalid URLs (should return False):")
    for url in invalid_urls:
        result = MAMUtils.is_allowed_path(url)
        print(f"  {url}: {result}")

def test_filename_sanitization():
    """Test filename sanitization"""
    print("\n=== Testing Filename Sanitization ===")

    test_cases = [
        "Normal Title",
        "Title: With Colons",
        "Title/With\\Slashes",
        "Title<>With|Invalid*Chars?",
        "   Title   With   Spaces   ",
        "Very Long Title " * 20,
    ]

    for title in test_cases:
        sanitized = MAMUtils.sanitize_filename(title)
        print(f"  Original: '{title[:50]}'")
        print(f"  Sanitized: '{sanitized}'\n")

def test_content_anonymization():
    """Test content anonymization"""
    print("\n=== Testing Content Anonymization ===")

    content = """
    Contact me at user@example.com or admin@test.org
    User user_123 says hello. user-456 also commented.
    Session ID: sid=abc123def456789012345678901234567890
    """

    anonymized = MAMUtils.anonymize_content(content)
    print(f"Original:\n{content}")
    print(f"\nAnonymized:\n{anonymized}")

def test_duration_parsing():
    """Test duration parsing"""
    print("\n=== Testing Duration Parsing ===")

    test_durations = [
        "45",          # 45 seconds
        "1:30",        # 1 minute 30 seconds
        "2:15:30",     # 2 hours 15 minutes 30 seconds
    ]

    for duration in test_durations:
        seconds = MAMUtils.parse_duration(duration)
        formatted = MAMUtils.format_duration(seconds) if seconds else "Invalid"
        print(f"  Input: {duration} -> Seconds: {seconds} -> Formatted: {formatted}")

async def test_rate_limiter():
    """Test rate limiter"""
    print("\n=== Testing Rate Limiter ===")

    limiter = RateLimiter(min_delay=1.0, max_delay=2.0)

    import time
    print("Making 3 requests with rate limiting...")
    for i in range(3):
        start = time.time()
        await limiter.wait()
        elapsed = time.time() - start
        print(f"  Request {i+1}: waited {elapsed:.2f}s")

async def test_retry_policy():
    """Test retry policy"""
    print("\n=== Testing Retry Policy ===")

    policy = RetryPolicy(max_retries=3, base_delay=0.5)

    attempt_count = 0
    async def flaky_operation():
        nonlocal attempt_count
        attempt_count += 1
        print(f"  Attempt {attempt_count}")
        if attempt_count < 3:
            raise Exception("Simulated failure")
        return "Success!"

    try:
        result = await policy.execute_with_retry(flaky_operation)
        print(f"  Result: {result}")
    except Exception as e:
        print(f"  Failed: {e}")

async def main():
    print("=" * 60)
    print("MAMcrawler Utilities Module Validation")
    print("=" * 60)

    test_url_validation()
    test_filename_sanitization()
    test_content_anonymization()
    test_duration_parsing()
    await test_rate_limiter()
    await test_retry_policy()

    print("\n" + "=" * 60)
    print("All tests completed")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
