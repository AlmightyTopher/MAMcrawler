# test_utils_sanitization.py
# Comprehensive validation of utils/sanitization module

import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.abspath('.'))

from mamcrawler.utils.sanitize import sanitize_filename, anonymize_content, clean_whitespace
from mamcrawler.utils import safe_read_markdown


def test_sanitize_filename():
    """Test filename sanitization with comprehensive cases."""
    print("\n=== Testing sanitize_filename() ===")

    test_cases = [
        # (Input, Expected Contains/Pattern, Description)
        ("Normal Title", "Normal_Title", "Basic sanitization"),
        ("Title: With Colon", "Title_With_Colon", "Colon removal"),
        ("Path/With\\Slashes", "PathWithSlashes", "Slash removal"),
        ("File<With>Brackets", "FileWithBrackets", "Bracket removal"),
        ('Quote"Marks"Here', "QuoteMarksHere", "Quote removal"),
        ("Pipe|Character", "PipeCharacter", "Pipe removal"),
        ("Question?Mark", "QuestionMark", "Question mark removal"),
        ("Asterisk*Here", "AsteriskHere", "Asterisk removal"),
        ("Multiple   Spaces", "Multiple_Spaces", "Multiple spaces to single underscore"),
        ("  Leading And Trailing  ", "Leading_And_Trailing", "Trim and convert"),
        ("Tab\tCharacter", "Tab_Character", "Tab to underscore"),
        ("Newline\nCharacter", "Newline_Character", "Newline to underscore"),
        ("", "", "Empty string"),
        ("日本語タイトル", "日本語タイトル", "Unicode preserved"),
        ("Émojis 🎵 Here", "Émojis_🎵_Here", "Emoji preserved"),
    ]

    passed = 0
    failed = 0

    print("\n  Running sanitization tests:")
    for input_str, expected, description in test_cases:
        result = sanitize_filename(input_str)

        # Check if forbidden characters are removed
        forbidden = r'<>:"/\|?*'
        has_forbidden = any(char in result for char in forbidden)

        # For exact match expectations
        if expected and result != expected:
            print(f"    ❌ FAIL | {description}")
            print(f"         Input: '{input_str}'")
            print(f"         Expected: '{expected}'")
            print(f"         Got: '{result}'")
            failed += 1
        elif has_forbidden:
            print(f"    ❌ FAIL | {description} - Contains forbidden chars")
            print(f"         Result: '{result}'")
            failed += 1
        else:
            print(f"    ✅ PASS | {description}")
            passed += 1

    # Test max_length parameter
    print("\n  Testing max_length parameter:")
    long_title = "A" * 200
    result_default = sanitize_filename(long_title)
    result_custom = sanitize_filename(long_title, max_length=50)

    if len(result_default) != 100:
        print(f"    ❌ FAIL: Default max_length should be 100, got {len(result_default)}")
        failed += 1
    else:
        print(f"    ✅ PASS | Default max_length=100: {len(result_default)} chars")
        passed += 1

    if len(result_custom) != 50:
        print(f"    ❌ FAIL: Custom max_length should be 50, got {len(result_custom)}")
        failed += 1
    else:
        print(f"    ✅ PASS | Custom max_length=50: {len(result_custom)} chars")
        passed += 1

    print(f"\n  Results: {passed} passed, {failed} failed")

    if failed > 0:
        print("  ❌ sanitize_filename() has issues")
        return False

    print("  ✓ All sanitize_filename() tests passed")
    return True


def test_anonymize_content():
    """Test content anonymization."""
    print("\n=== Testing anonymize_content() ===")

    # Test 1: Email removal
    print("\n  Test 1: Email address removal")
    test_cases = [
        ("Contact: user@example.com", "[EMAIL]"),
        ("Multiple: user@test.com and admin@site.org", "[EMAIL]"),
        ("Complex: john.doe+tag@sub.example.co.uk", "[EMAIL]"),
        ("No email here", None),  # Should remain unchanged
    ]

    for content, should_contain in test_cases:
        result = anonymize_content(content)

        if should_contain:
            if should_contain not in result:
                print(f"    ❌ FAIL: Should contain '{should_contain}'")
                print(f"         Input: '{content}'")
                print(f"         Result: '{result}'")
                return False
            if "@" in result and should_contain == "[EMAIL]":
                print(f"    ❌ FAIL: Email not fully removed")
                print(f"         Result: '{result}'")
                return False

    print("    ✓ All email patterns handled correctly")

    # Test 2: Username removal
    print("\n  Test 2: Username pattern removal")
    username_tests = [
        ("Posted by user_john123", "[USER]"),
        ("Author: user-admin456", "[USER]"),
        ("USER_CAPS should match", "[USER]"),
        ("useralone doesn't match", "useralone"),  # Needs underscore/hyphen
    ]

    for content, expected_pattern in username_tests:
        result = anonymize_content(content)

        if expected_pattern not in result:
            print(f"    ❌ FAIL: Expected pattern '{expected_pattern}' not found")
            print(f"         Input: '{content}'")
            print(f"         Result: '{result}'")
            return False

    print("    ✓ All username patterns handled correctly")

    # Test 3: Length limiting
    print("\n  Test 3: Length limiting")
    long_content = "A" * 10000

    result_default = anonymize_content(long_content)
    if len(result_default) != 5000:
        print(f"    ❌ FAIL: Default max_length should be 5000, got {len(result_default)}")
        return False
    print(f"    ✓ Default max_length=5000: {len(result_default)} chars")

    result_custom = anonymize_content(long_content, max_length=1000)
    if len(result_custom) != 1000:
        print(f"    ❌ FAIL: Custom max_length should be 1000, got {len(result_custom)}")
        return False
    print(f"    ✓ Custom max_length=1000: {len(result_custom)} chars")

    result_none = anonymize_content(long_content, max_length=None)
    if len(result_none) != 10000:
        print(f"    ❌ FAIL: max_length=None should preserve full length")
        return False
    print(f"    ✓ max_length=None preserves full content: {len(result_none)} chars")

    # Test 4: Empty/None handling
    print("\n  Test 4: Edge cases")
    empty_result = anonymize_content("")
    if empty_result != "":
        print(f"    ❌ FAIL: Empty string should return empty")
        return False
    print("    ✓ Empty string handled")

    # Test 5: Combined patterns
    print("\n  Test 5: Combined anonymization")
    combined = "user_john emailed admin@test.com about the issue"
    result = anonymize_content(combined)

    if "[USER]" not in result or "[EMAIL]" not in result:
        print(f"    ❌ FAIL: Both patterns should be replaced")
        print(f"         Result: '{result}'")
        return False
    print(f"    ✓ Multiple patterns replaced: '{result}'")

    print("\n  ✓ All anonymize_content() tests passed")
    return True


def test_clean_whitespace():
    """Test whitespace cleaning."""
    print("\n=== Testing clean_whitespace() ===")

    test_cases = [
        # (Input, Expected, Description)
        ("Normal text", "Normal text", "No change needed"),
        ("Text\n\nDouble newline", "Text\n\nDouble newline", "Double newline preserved"),
        ("Text\n\n\nTriple newline", "Text\n\nTriple newline", "Triple → Double"),
        ("Text\n\n\n\nQuad newline", "Text\n\nQuad newline", "Quad → Double"),
        ("Text\n \n \nSpaces between", "Text\n\nSpaces between", "Whitespace-only lines removed"),
        ("  Leading spaces", "Leading spaces", "Leading spaces trimmed"),
        ("Trailing spaces  ", "Trailing spaces", "Trailing spaces trimmed"),
        ("  Both sides  ", "Both sides", "Both sides trimmed"),
        ("", "", "Empty string"),
        ("   ", "", "Whitespace-only string"),
    ]

    passed = 0
    failed = 0

    print("\n  Running whitespace cleaning tests:")
    for input_str, expected, description in test_cases:
        result = clean_whitespace(input_str)

        if result != expected:
            print(f"    ❌ FAIL | {description}")
            print(f"         Input: {repr(input_str)}")
            print(f"         Expected: {repr(expected)}")
            print(f"         Got: {repr(result)}")
            failed += 1
        else:
            print(f"    ✅ PASS | {description}")
            passed += 1

    # Test complex case
    print("\n  Testing complex whitespace:")
    complex_input = """

    Paragraph 1


    Paragraph 2



    Paragraph 3

    """

    result = clean_whitespace(complex_input)

    # Should have no more than double newlines
    if "\n\n\n" in result:
        print(f"    ❌ FAIL: Still contains triple newlines")
        print(f"         Result: {repr(result)}")
        failed += 1
    else:
        print(f"    ✅ PASS | Complex whitespace normalized")
        passed += 1

    # Should be trimmed
    if result.startswith("\n") or result.endswith("\n"):
        print(f"    ❌ FAIL: Not properly trimmed")
        print(f"         Result: {repr(result)}")
        failed += 1
    else:
        print(f"    ✅ PASS | Leading/trailing whitespace removed")
        passed += 1

    print(f"\n  Results: {passed} passed, {failed} failed")

    if failed > 0:
        print("  ❌ clean_whitespace() has issues")
        return False

    print("  ✓ All clean_whitespace() tests passed")
    return True


def test_safe_read_markdown():
    """Test safe markdown file reading with various encodings."""
    print("\n=== Testing safe_read_markdown() ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir)

        # Test 1: UTF-8 without BOM
        print("\n  Test 1: UTF-8 without BOM")
        utf8_file = base_path / "utf8.md"
        test_content = "Hello World! 日本語 🎵"
        utf8_file.write_text(test_content, encoding="utf-8")

        result = safe_read_markdown(str(utf8_file))
        if result != test_content:
            print(f"    ❌ FAIL: Content mismatch")
            print(f"         Expected: {repr(test_content)}")
            print(f"         Got: {repr(result)}")
            return False
        print("    ✓ UTF-8 without BOM read correctly")

        # Test 2: UTF-8 with BOM
        print("\n  Test 2: UTF-8 with BOM")
        utf8_bom_file = base_path / "utf8_bom.md"
        with open(utf8_bom_file, "wb") as f:
            f.write(b"\xef\xbb\xbf" + test_content.encode("utf-8"))

        result2 = safe_read_markdown(str(utf8_bom_file))
        if result2 != test_content:
            print(f"    ❌ FAIL: BOM not properly removed")
            print(f"         Got: {repr(result2)}")
            return False
        print("    ✓ UTF-8 BOM detected and removed")

        # Test 3: UTF-16 LE with BOM
        print("\n  Test 3: UTF-16 LE with BOM")
        utf16le_file = base_path / "utf16le.md"
        with open(utf16le_file, "wb") as f:
            f.write(b"\xff\xfe" + test_content.encode("utf-16-le"))

        result3 = safe_read_markdown(str(utf16le_file))
        if result3 != test_content:
            print(f"    ❌ FAIL: UTF-16 LE not decoded correctly")
            print(f"         Got: {repr(result3)}")
            return False
        print("    ✓ UTF-16 LE with BOM read correctly")

        # Test 4: UTF-16 BE with BOM
        print("\n  Test 4: UTF-16 BE with BOM")
        utf16be_file = base_path / "utf16be.md"
        with open(utf16be_file, "wb") as f:
            f.write(b"\xfe\xff" + test_content.encode("utf-16-be"))

        result4 = safe_read_markdown(str(utf16be_file))
        if result4 != test_content:
            print(f"    ❌ FAIL: UTF-16 BE not decoded correctly")
            print(f"         Got: {repr(result4)}")
            return False
        print("    ✓ UTF-16 BE with BOM read correctly")

        # Test 5: Fallback handling
        print("\n  Test 5: Graceful fallback for corrupted data")
        corrupted_file = base_path / "corrupted.md"
        with open(corrupted_file, "wb") as f:
            # Write invalid UTF-8 sequence
            f.write(b"Valid start \xff\xfe invalid bytes")

        # Should not crash, use errors='replace'
        try:
            result5 = safe_read_markdown(str(corrupted_file))
            print(f"    ✓ Corrupted data handled gracefully")
            print(f"    ✓ Result length: {len(result5)} chars (with replacement chars)")
        except Exception as e:
            print(f"    ❌ FAIL: Should handle corrupted data gracefully")
            print(f"         Exception: {e}")
            return False

        # Test 6: Empty file
        print("\n  Test 6: Empty file")
        empty_file = base_path / "empty.md"
        empty_file.write_text("", encoding="utf-8")

        result6 = safe_read_markdown(str(empty_file))
        if result6 != "":
            print(f"    ❌ FAIL: Empty file should return empty string")
            return False
        print("    ✓ Empty file handled correctly")

    print("\n  ✓ All safe_read_markdown() tests passed")
    return True


def main():
    """Run all utils/sanitization tests."""
    print("=" * 60)
    print("Utils/Sanitization Module Validation")
    print("=" * 60)

    tests = [
        ("sanitize_filename()", test_sanitize_filename),
        ("anonymize_content()", test_anonymize_content),
        ("clean_whitespace()", test_clean_whitespace),
        ("safe_read_markdown()", test_safe_read_markdown),
    ]

    results = []
    for name, test_func in tests:
        try:
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
        print("\n🎉 All utils/sanitization tests passed!")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
