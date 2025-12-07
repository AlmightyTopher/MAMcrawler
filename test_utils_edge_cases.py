# test_utils_edge_cases.py
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from mamcrawler.core.utils import MAMUtils

def test_edge_cases():
    """Test edge cases and boundary conditions"""
    print("="*60)
    print("Edge Case Testing")
    print("="*60)

    # Test 1: Empty/None inputs
    print("\n1. Empty/None Inputs:")
    print(f"  sanitize_filename(''): '{MAMUtils.sanitize_filename('')}'")
    print(f"  anonymize_content(''): '{MAMUtils.anonymize_content('')}'")
    print(f"  is_allowed_path(''): {MAMUtils.is_allowed_path('')}")
    print(f"  clean_text(''): '{MAMUtils.clean_text('')}'")

    # Test 2: Unicode and special characters
    print("\n2. Unicode Characters:")
    unicode_title = "Book: The Café résumé 日本語 🎵"
    print(f"  Original: {unicode_title}")
    print(f"  Sanitized: '{MAMUtils.sanitize_filename(unicode_title)}'")

    # Test 3: Only special characters
    print("\n3. Only Special Characters:")
    special_only = "***///<<<>>>|||"
    print(f"  Original: '{special_only}'")
    print(f"  Sanitized: '{MAMUtils.sanitize_filename(special_only)}'")

    # Test 4: Very long URL
    print("\n4. Path Edge Cases:")
    edge_urls = [
        "https://www.myanonamouse.net",  # No trailing slash
        "https://www.myanonamouse.net/guides",  # No trailing slash
        "https://www.myanonamouse.net//guides/",  # Double slash
        "https://www.myanonamouse.net/f/topic.php?id=123",  # Forum with params
    ]
    for url in edge_urls:
        result = MAMUtils.is_allowed_path(url)
        print(f"  {url}: {result}")

    # Test 5: Duration parsing edge cases
    print("\n5. Duration Parsing Edge Cases:")
    edge_durations = [
        "",
        "0",
        "0:0",
        "0:0:0",
        "invalid",
        "1:2:3:4",  # Too many parts
    ]
    for dur in edge_durations:
        result = MAMUtils.parse_duration(dur)
        print(f"  '{dur}': {result}")

    # Test 6: File size formatting
    print("\n6. File Size Formatting:")
    sizes = [0, 1, 1023, 1024, 1048576, 1073741824, 1099511627776]
    for size in sizes:
        formatted = MAMUtils.format_file_size(size)
        print(f"  {size} bytes: {formatted}")

    # Test 7: Extract numbers
    print("\n7. Extract Numbers:")
    test_texts = [
        "123",
        "The answer is 42",
        "Version 1.2.3 released",
        "No numbers here",
        "3.14159 and 2.71828",
    ]
    for text in test_texts:
        numbers = MAMUtils.extract_numbers(text)
        print(f"  '{text}': {numbers}")

    print("\n" + "="*60)

if __name__ == "__main__":
    test_edge_cases()
