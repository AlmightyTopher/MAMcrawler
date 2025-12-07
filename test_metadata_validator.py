# test_metadata_validator.py
# Comprehensive validation of the Metadata Validator module

import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from mamcrawler.metadata.metadata_validator import MetadataValidator, get_metadata_validator


def test_required_fields():
    """Test required field validation."""
    print("\n=== Testing Required Fields Validation ===")

    validator = MetadataValidator()

    # Test 1: Valid metadata with all required fields
    print("\n  Test 1: Valid metadata")
    valid_metadata = {
        'title': 'The Great Audiobook',
        'author': 'John Author'
    }

    valid, missing = validator.validate_required_fields(valid_metadata)

    if not valid or missing:
        print(f"    ❌ FAIL: Should be valid, got missing={missing}")
        return False
    print("    ✓ Valid metadata passes")

    # Test 2: Missing title
    print("\n  Test 2: Missing title")
    no_title = {'author': 'John Author'}
    valid2, missing2 = validator.validate_required_fields(no_title)

    if valid2:
        print("    ❌ FAIL: Should be invalid (missing title)")
        return False
    if 'title' not in missing2:
        print(f"    ❌ FAIL: Should report 'title' missing, got {missing2}")
        return False
    print(f"    ✓ Missing title detected: {missing2}")

    # Test 3: Missing author
    print("\n  Test 3: Missing author")
    no_author = {'title': 'The Book'}
    valid3, missing3 = validator.validate_required_fields(no_author)

    if valid3:
        print("    ❌ FAIL: Should be invalid (missing author)")
        return False
    if 'author' not in missing3:
        print(f"    ❌ FAIL: Should report 'author' missing, got {missing3}")
        return False
    print(f"    ✓ Missing author detected: {missing3}")

    # Test 4: Empty string values
    print("\n  Test 4: Empty string values")
    empty_strings = {'title': '   ', 'author': ''}
    valid4, missing4 = validator.validate_required_fields(empty_strings)

    if valid4:
        print("    ❌ FAIL: Empty strings should fail validation")
        return False
    print(f"    ✓ Empty strings rejected: {missing4}")

    # Test 5: Missing both
    print("\n  Test 5: Missing all required fields")
    empty = {}
    valid5, missing5 = validator.validate_required_fields(empty)

    if valid5:
        print("    ❌ FAIL: Should be invalid (all fields missing)")
        return False
    if len(missing5) != 2:
        print(f"    ❌ FAIL: Should report 2 missing fields, got {len(missing5)}")
        return False
    print(f"    ✓ All missing fields detected: {missing5}")

    print("\n  ✓ All required field tests passed")
    return True


def test_format_validation():
    """Test format validation for various fields."""
    print("\n=== Testing Format Validation ===")

    validator = MetadataValidator()

    # Test 1: Valid release year
    print("\n  Test 1: Valid release year")
    valid_year = {'title': 'Book', 'author': 'Author', 'releaseYear': 2020}
    valid, errors = validator.validate_format(valid_year)

    if not valid:
        print(f"    ❌ FAIL: Valid year should pass, errors: {errors}")
        return False
    print("    ✓ Valid year (2020) accepted")

    # Test 2: Year out of range (too old)
    print("\n  Test 2: Year out of range (too old)")
    old_year = {'releaseYear': 999}
    valid2, errors2 = validator.validate_format(old_year)

    if valid2:
        print("    ❌ FAIL: Year 999 should be rejected")
        return False
    if not any('out of range' in e for e in errors2):
        print(f"    ❌ FAIL: Should report 'out of range', got {errors2}")
        return False
    print(f"    ✓ Old year rejected: {errors2}")

    # Test 3: Year out of range (too new)
    print("\n  Test 3: Year out of range (future)")
    future_year = {'releaseYear': 2101}
    valid3, errors3 = validator.validate_format(future_year)

    if valid3:
        print("    ❌ FAIL: Year 2101 should be rejected")
        return False
    print(f"    ✓ Future year rejected: {errors3}")

    # Test 4: Invalid year format
    print("\n  Test 4: Invalid year format (string)")
    string_year = {'releaseYear': 'not-a-year'}
    valid4, errors4 = validator.validate_format(string_year)

    if valid4:
        print("    ❌ FAIL: String year should be rejected")
        return False
    print(f"    ✓ String year rejected: {errors4}")

    # Test 5: Genres must be list
    print("\n  Test 5: Genres format validation")
    invalid_genres = {'genres': 'Fantasy'}  # Should be list
    valid5, errors5 = validator.validate_format(invalid_genres)

    if valid5:
        print("    ❌ FAIL: Genres string should be rejected")
        return False
    if not any('must be a list' in e for e in errors5):
        print(f"    ❌ FAIL: Should report 'must be a list', got {errors5}")
        return False
    print(f"    ✓ Genres string rejected: {errors5}")

    # Test 6: Valid genres list
    print("\n  Test 6: Valid genres list")
    valid_genres = {'genres': ['Fantasy', 'Adventure']}
    valid6, errors6 = validator.validate_format(valid_genres)

    if not valid6:
        print(f"    ❌ FAIL: Valid genres list should pass, errors: {errors6}")
        return False
    print("    ✓ Valid genres list accepted")

    # Test 7: Duration validation
    print("\n  Test 7: Duration validation")
    invalid_duration = {'duration': 'not-a-number'}
    valid7, errors7 = validator.validate_format(invalid_duration)

    if valid7:
        print("    ❌ FAIL: Invalid duration should be rejected")
        return False
    print(f"    ✓ Invalid duration rejected: {errors7}")

    # Test 8: Valid duration
    print("\n  Test 8: Valid duration")
    valid_duration = {'duration': 36000, 'durationMs': 36000000, 'durationSeconds': 3600.5}
    valid8, errors8 = validator.validate_format(valid_duration)

    if not valid8:
        print(f"    ❌ FAIL: Valid durations should pass, errors: {errors8}")
        return False
    print("    ✓ Valid durations accepted")

    # Test 9: Rating out of range
    print("\n  Test 9: Rating validation")
    invalid_rating = {'rating': 6}
    valid9, errors9 = validator.validate_format(invalid_rating)

    if valid9:
        print("    ❌ FAIL: Rating > 5 should be rejected")
        return False
    print(f"    ✓ Rating > 5 rejected: {errors9}")

    # Test 10: Valid rating
    print("\n  Test 10: Valid rating")
    valid_rating = {'rating': 4.5}
    valid10, errors10 = validator.validate_format(valid_rating)

    if not valid10:
        print(f"    ❌ FAIL: Valid rating should pass, errors: {errors10}")
        return False
    print("    ✓ Valid rating accepted")

    print("\n  ✓ All format validation tests passed")
    return True


def test_sanitize_text():
    """Test text field sanitization."""
    print("\n=== Testing Text Sanitization ===")

    validator = MetadataValidator()

    # Test 1: Whitespace normalization
    print("\n  Test 1: Whitespace normalization")
    messy_whitespace = {
        'title': '  The   Great    Book  ',
        'author': 'John    Author'
    }

    cleaned = validator.sanitize_text_fields(messy_whitespace)

    if cleaned['title'] != 'The Great Book':
        print(f"    ❌ FAIL: Expected 'The Great Book', got '{cleaned['title']}'")
        return False
    if cleaned['author'] != 'John Author':
        print(f"    ❌ FAIL: Expected 'John Author', got '{cleaned['author']}'")
        return False
    print("    ✓ Whitespace normalized correctly")

    # Test 2: Invalid character removal
    print("\n  Test 2: Invalid character removal")
    special_chars = {
        'title': 'Book@#$%^&*Title',
        'description': 'Description with €¥£ symbols'
    }

    cleaned2 = validator.sanitize_text_fields(special_chars)

    # Should keep letters/numbers but remove special symbols
    if '@' in cleaned2['title'] or '#' in cleaned2['title']:
        print(f"    ❌ FAIL: Special chars not removed: '{cleaned2['title']}'")
        return False
    print(f"    ✓ Special chars removed: '{cleaned2['title']}'")

    # Test 3: Keep allowed punctuation
    print("\n  Test 3: Allowed punctuation preserved")
    punctuation = {
        'title': "Author's Book: A Story (Part 1)",
        'series': "Book-Series, Vol. 2"
    }

    cleaned3 = validator.sanitize_text_fields(punctuation)

    # Should keep: apostrophes, colons, parentheses, hyphens, commas, periods
    required_chars = ["'", ":", "(", ")", "-", ",", "."]
    for char in required_chars:
        if char not in cleaned3['title'] and char not in cleaned3.get('series', ''):
            print(f"    ❌ FAIL: Lost allowed punctuation: '{char}'")
            return False
    print(f"    ✓ Allowed punctuation preserved")

    # Test 4: Duplicate punctuation removal
    print("\n  Test 4: Duplicate punctuation removal")
    duplicates = {
        'title': 'Book!!! Really!!!',
        'description': 'Amazing... Really... Great...'
    }

    cleaned4 = validator.sanitize_text_fields(duplicates)

    if '!!!' in cleaned4['title'] or '...' in cleaned4.get('description', ''):
        print(f"    ❌ FAIL: Duplicate punctuation not removed")
        return False
    print(f"    ✓ Duplicate punctuation removed: '{cleaned4['title']}'")

    # Test 5: Non-string fields preserved
    print("\n  Test 5: Non-string fields unchanged")
    mixed_types = {
        'title': 'Book',
        'author': 'Author',
        'releaseYear': 2020,
        'rating': 4.5
    }

    cleaned5 = validator.sanitize_text_fields(mixed_types)

    if cleaned5['releaseYear'] != 2020:
        print(f"    ❌ FAIL: Numeric field changed")
        return False
    if cleaned5['rating'] != 4.5:
        print(f"    ❌ FAIL: Float field changed")
        return False
    print("    ✓ Non-string fields preserved")

    print("\n  ✓ All text sanitization tests passed")
    return True


def test_duplicate_detection():
    """Test duplicate detection logic."""
    print("\n=== Testing Duplicate Detection ===")

    validator = MetadataValidator()

    existing = [
        {'title': 'The Great Gatsby', 'author': 'F. Scott Fitzgerald'},
        {'title': '1984', 'author': 'George Orwell'},
        {'title': 'To Kill a Mockingbird', 'author': 'Harper Lee'}
    ]

    # Test 1: Exact match
    print("\n  Test 1: Exact match detection")
    is_dup, details = validator.detect_and_handle_duplicates(
        'The Great Gatsby',
        'F. Scott Fitzgerald',
        existing
    )

    if not is_dup:
        print("    ❌ FAIL: Should detect exact match")
        return False
    if 'Exact match' not in details:
        print(f"    ❌ FAIL: Should report 'Exact match', got '{details}'")
        return False
    print(f"    ✓ Exact match detected: {details}")

    # Test 2: Case insensitive match
    print("\n  Test 2: Case insensitive match")
    is_dup2, details2 = validator.detect_and_handle_duplicates(
        'the great gatsby',
        'f. scott fitzgerald',
        existing
    )

    if not is_dup2:
        print("    ❌ FAIL: Should detect case-insensitive match")
        return False
    print(f"    ✓ Case-insensitive match detected")

    # Test 3: Fuzzy match (high similarity)
    print("\n  Test 3: Fuzzy match detection")
    is_dup3, details3 = validator.detect_and_handle_duplicates(
        'The Great Gatsby ',  # Extra space
        'F Scott Fitzgerald',  # Missing period
        existing
    )

    if not is_dup3:
        print("    ❌ FAIL: Should detect fuzzy match")
        return False
    if 'Fuzzy match' not in details3:
        print(f"    ❌ FAIL: Should report 'Fuzzy match', got '{details3}'")
        return False
    print(f"    ✓ Fuzzy match detected: {details3}")

    # Test 4: No match
    print("\n  Test 4: No duplicate (different book)")
    is_dup4, details4 = validator.detect_and_handle_duplicates(
        'A Different Book',
        'Another Author',
        existing
    )

    if is_dup4:
        print(f"    ❌ FAIL: Should not detect duplicate, got '{details4}'")
        return False
    print("    ✓ No duplicate for different book")

    # Test 5: Empty existing list
    print("\n  Test 5: Empty existing metadata")
    is_dup5, details5 = validator.detect_and_handle_duplicates(
        'Any Book',
        'Any Author',
        []
    )

    if is_dup5:
        print("    ❌ FAIL: Should not detect duplicate with empty list")
        return False
    print("    ✓ No duplicate with empty list")

    # Test 6: Similar but not duplicate (< 95% match)
    print("\n  Test 6: Similar but distinct books")
    is_dup6, details6 = validator.detect_and_handle_duplicates(
        'The Great Adventure',  # Different enough
        'F. Scott Fitzgerald',
        existing
    )

    if is_dup6:
        print(f"    ❌ FAIL: Should not match sufficiently different title")
        return False
    print("    ✓ Sufficiently different titles not matched")

    print("\n  ✓ All duplicate detection tests passed")
    return True


def test_complete_validation():
    """Test complete audiobook validation pipeline."""
    print("\n=== Testing Complete Validation ===")

    validator = MetadataValidator()

    # Test 1: Fully valid audiobook
    print("\n  Test 1: Fully valid audiobook")
    valid_book = {
        'title': '  The Great Book  ',  # Will be cleaned
        'author': 'John Author',
        'narrator': 'Jane Narrator',
        'series': 'The Series',
        'releaseYear': 2020,
        'genres': ['Fantasy', 'Adventure'],
        'rating': 4.5,
        'description': 'A great story'
    }

    result = validator.validate_audiobook(valid_book)

    if not result['valid']:
        print(f"    ❌ FAIL: Should be valid, errors: {result['errors']}")
        return False
    if result['errors']:
        print(f"    ❌ FAIL: Should have no errors, got {result['errors']}")
        return False
    if result['cleaned_metadata']['title'] != 'The Great Book':
        print(f"    ❌ FAIL: Title not cleaned properly")
        return False
    print(f"    ✓ Valid audiobook passes")
    print(f"    ✓ Cleaned metadata returned")

    # Test 2: Missing required fields
    print("\n  Test 2: Missing required fields")
    missing_fields = {
        'narrator': 'Someone'
    }

    result2 = validator.validate_audiobook(missing_fields)

    if result2['valid']:
        print("    ❌ FAIL: Should be invalid (missing required fields)")
        return False
    if len(result2['errors']) < 2:
        print(f"    ❌ FAIL: Should have at least 2 errors, got {len(result2['errors'])}")
        return False
    print(f"    ✓ Missing fields rejected: {len(result2['errors'])} errors")

    # Test 3: Format errors
    print("\n  Test 3: Format validation errors")
    format_errors = {
        'title': 'Book',
        'author': 'Author',
        'releaseYear': 'not-a-year',
        'genres': 'Fantasy',  # Should be list
        'rating': 10  # Out of range
    }

    result3 = validator.validate_audiobook(format_errors)

    if result3['valid']:
        print("    ❌ FAIL: Should be invalid (format errors)")
        return False
    if len(result3['errors']) < 3:
        print(f"    ❌ FAIL: Should have multiple format errors, got {len(result3['errors'])}")
        return False
    print(f"    ✓ Format errors detected: {len(result3['errors'])} errors")

    # Test 4: Warnings for long fields
    print("\n  Test 4: Warnings for long fields")
    long_fields = {
        'title': 'A' * 600,  # >500 chars
        'author': 'Author',
        'description': 'B' * 6000  # >5000 chars
    }

    result4 = validator.validate_audiobook(long_fields)

    if not result4['valid']:
        print(f"    ❌ FAIL: Long fields should still be valid, errors: {result4['errors']}")
        return False
    if len(result4['warnings']) < 2:
        print(f"    ❌ FAIL: Should have 2 warnings, got {len(result4['warnings'])}")
        return False
    print(f"    ✓ Warnings for long fields: {result4['warnings']}")

    # Test 5: Cleaned metadata only returned if valid
    print("\n  Test 5: Cleaned metadata behavior")
    invalid = {'narrator': 'Someone'}
    result5 = validator.validate_audiobook(invalid)

    if result5['valid']:
        print("    ❌ FAIL: Should be invalid")
        return False
    if result5['cleaned_metadata'] != invalid:
        print("    ❌ FAIL: Should return original metadata when invalid")
        return False
    print("    ✓ Original metadata returned when invalid")

    print("\n  ✓ All complete validation tests passed")
    return True


def test_singleton():
    """Test singleton pattern for validator."""
    print("\n=== Testing Singleton Pattern ===")

    # Test 1: Get instance twice
    print("\n  Test 1: Singleton returns same instance")
    validator1 = get_metadata_validator()
    validator2 = get_metadata_validator()

    if validator1 is not validator2:
        print("    ❌ FAIL: Should return same instance")
        return False
    print("    ✓ Same instance returned")

    # Test 2: Instance is MetadataValidator
    print("\n  Test 2: Instance type check")
    if not isinstance(validator1, MetadataValidator):
        print("    ❌ FAIL: Should be MetadataValidator instance")
        return False
    print("    ✓ Correct instance type")

    print("\n  ✓ Singleton pattern tests passed")
    return True


def main():
    """Run all metadata validator tests."""
    print("=" * 60)
    print("Metadata Validator Module Validation")
    print("=" * 60)

    tests = [
        ("Required Fields Validation", test_required_fields),
        ("Format Validation", test_format_validation),
        ("Text Sanitization", test_sanitize_text),
        ("Duplicate Detection", test_duplicate_detection),
        ("Complete Validation", test_complete_validation),
        ("Singleton Pattern", test_singleton),
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
        print("\n🎉 All metadata validator tests passed!")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
