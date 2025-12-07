# test_file_namer.py
# Comprehensive validation of the File Namer module

import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.abspath('.'))

from mamcrawler.audio_processing.file_namer import FileNamer, get_file_namer


def test_initialization():
    """Test FileNamer initialization."""
    print("\n=== Testing Initialization ===")

    # Test 1: Default initialization
    print("\n  Test 1: Default initialization")
    namer = FileNamer()

    if not namer.base_directory:
        print("    ❌ FAIL: base_directory should be set")
        return False
    print(f"    ✓ Base directory set: {namer.base_directory}")
    print(f"    ✓ Max filename length: {namer.max_filename_length}")

    # Test 2: Custom base directory
    print("\n  Test 2: Custom base directory")
    with tempfile.TemporaryDirectory() as temp_dir:
        custom_namer = FileNamer(base_directory=temp_dir)

        if str(custom_namer.base_directory) != temp_dir:
            print(f"    ❌ FAIL: Expected {temp_dir}, got {custom_namer.base_directory}")
            return False
        print(f"    ✓ Custom base directory: {custom_namer.base_directory}")

    print("\n  ✓ All initialization tests passed")
    return True


def test_generate_filename():
    """Test filename generation."""
    print("\n=== Testing Filename Generation ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        namer = FileNamer(base_directory=temp_dir)

        # Test 1: Basic filename
        print("\n  Test 1: Basic filename (author + title)")
        result = namer.generate_filename(
            author="Brandon Sanderson",
            title="The Way of Kings"
        )

        if not result['valid']:
            print(f"    ❌ FAIL: Should be valid")
            return False
        if result['filename'] != "The Way of Kings.m4b":
            print(f"    ❌ FAIL: Expected 'The Way of Kings.m4b', got '{result['filename']}'")
            return False
        print(f"    ✓ Filename: {result['filename']}")

        # Test 2: With narrator
        print("\n  Test 2: With narrator")
        result2 = namer.generate_filename(
            author="Brandon Sanderson",
            title="The Way of Kings",
            narrator="Michael Kramer"
        )

        if result2['filename'] != "The Way of Kings - Michael Kramer.m4b":
            print(f"    ❌ FAIL: Expected 'The Way of Kings - Michael Kramer.m4b', got '{result2['filename']}'")
            return False
        print(f"    ✓ Filename with narrator: {result2['filename']}")

        # Test 3: With year
        print("\n  Test 3: With year")
        result3 = namer.generate_filename(
            author="Brandon Sanderson",
            title="The Way of Kings",
            narrator="Michael Kramer",
            year=2010
        )

        if result3['filename'] != "The Way of Kings - Michael Kramer (2010).m4b":
            print(f"    ❌ FAIL: Expected year in filename, got '{result3['filename']}'")
            return False
        print(f"    ✓ Filename with year: {result3['filename']}")

        # Test 4: With series (directory structure)
        print("\n  Test 4: With series (directory structure)")
        result4 = namer.generate_filename(
            author="Brandon Sanderson",
            title="The Way of Kings",
            series="Stormlight Archive"
        )

        if "Stormlight Archive" not in result4['directory']:
            print(f"    ❌ FAIL: Series not in directory: {result4['directory']}")
            return False
        if "Brandon Sanderson" not in result4['directory']:
            print(f"    ❌ FAIL: Author not in directory: {result4['directory']}")
            return False
        print(f"    ✓ Directory: {result4['directory']}")

        # Test 5: Different file extension
        print("\n  Test 5: Different file extension")
        result5 = namer.generate_filename(
            author="Author",
            title="Title",
            file_extension="mp3"
        )

        if not result5['filename'].endswith('.mp3'):
            print(f"    ❌ FAIL: Expected .mp3 extension, got '{result5['filename']}'")
            return False
        print(f"    ✓ Custom extension: {result5['filename']}")

        # Test 6: Missing required fields
        print("\n  Test 6: Missing author")
        result6 = namer.generate_filename(
            author="",
            title="Title"
        )

        if result6['valid']:
            print("    ❌ FAIL: Should be invalid (missing author)")
            return False
        print("    ✓ Missing author rejected")

        # Test 7: Missing title
        print("\n  Test 7: Missing title")
        result7 = namer.generate_filename(
            author="Author",
            title=""
        )

        if result7['valid']:
            print("    ❌ FAIL: Should be invalid (missing title)")
            return False
        print("    ✓ Missing title rejected")

        # Test 8: Long filename truncation
        print("\n  Test 8: Long filename truncation")
        long_title = "A" * 250  # Exceeds max_filename_length
        result8 = namer.generate_filename(
            author="Author",
            title=long_title,
            narrator="Narrator",
            year=2020
        )

        if len(result8['filename']) > namer.max_filename_length:
            print(f"    ❌ FAIL: Filename too long: {len(result8['filename'])} chars")
            return False
        if " - Narrator" not in result8['filename']:
            print("    ❌ FAIL: Narrator should be preserved after truncation")
            return False
        if "(2020)" not in result8['filename']:
            print("    ❌ FAIL: Year should be preserved after truncation")
            return False
        print(f"    ✓ Long filename truncated: {len(result8['filename'])} chars")

    print("\n  ✓ All filename generation tests passed")
    return True


def test_sanitization():
    """Test filename sanitization."""
    print("\n=== Testing Filename Sanitization ===")

    namer = FileNamer()

    test_cases = [
        # (Input, Expected Pattern, Description)
        ("Normal Title", "Normal Title", "Normal text unchanged"),
        ("Title: With Colon", "Title With Colon", "Colon removed"),
        ("Path/With\\Slashes", "PathWithSlashes", "Slashes removed"),
        ("File<With>Brackets", "FileWithBrackets", "Brackets removed"),
        ('Quote"Marks"Here', "QuoteMarksHere", "Quotes removed"),
        ("Pipe|Character", "PipeCharacter", "Pipe removed"),
        ("Question?Mark", "QuestionMark", "Question mark removed"),
        ("Asterisk*Here", "AsteriskHere", "Asterisk removed"),
        ("Multiple   Spaces", "Multiple Spaces", "Multiple spaces normalized"),
        ("  Leading And Trailing  ", "Leading And Trailing", "Whitespace trimmed"),
        ("...Leading Dots", "Leading Dots", "Leading dots trimmed"),
        ("Trailing Dots...", "Trailing Dots", "Trailing dots trimmed"),
        ("Multiple...Dots", "Multiple.Dots", "Consecutive dots reduced"),
        ("", "Unknown", "Empty string becomes Unknown"),
        ("   ", "Unknown", "Whitespace-only becomes Unknown"),
        ("日本語タイトル", "日本語タイトル", "Unicode preserved"),
    ]

    passed = 0
    failed = 0

    print("\n  Running sanitization tests:")
    for input_str, expected, description in test_cases:
        result = namer.sanitize_filename(input_str)

        if result != expected:
            print(f"    ❌ FAIL | {description}")
            print(f"         Input: '{input_str}'")
            print(f"         Expected: '{expected}'")
            print(f"         Got: '{result}'")
            failed += 1
        else:
            print(f"    ✅ PASS | {description}")
            passed += 1

    print(f"\n  Results: {passed} passed, {failed} failed")

    if failed > 0:
        print("  ❌ Sanitization has issues")
        return False

    print("  ✓ All sanitization tests passed")
    return True


def test_handle_duplicates():
    """Test duplicate file handling."""
    print("\n=== Testing Duplicate Handling ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir)

        # Create test file
        test_file = base_path / "test.m4b"
        test_file.touch()

        namer = FileNamer(base_directory=temp_dir)

        # Test 1: Non-duplicate file
        print("\n  Test 1: Non-duplicate file")
        non_dup = base_path / "unique.m4b"
        result = namer.handle_duplicates(str(non_dup))

        if result['is_duplicate']:
            print("    ❌ FAIL: Should not be duplicate")
            return False
        if result['counter'] != 0:
            print(f"    ❌ FAIL: Counter should be 0, got {result['counter']}")
            return False
        print("    ✓ Non-duplicate file detected")

        # Test 2: Duplicate file
        print("\n  Test 2: Duplicate file (first rename)")
        result2 = namer.handle_duplicates(str(test_file))

        if not result2['is_duplicate']:
            print("    ❌ FAIL: Should detect duplicate")
            return False
        if result2['counter'] != 1:
            print(f"    ❌ FAIL: Counter should be 1, got {result2['counter']}")
            return False
        if "test (1).m4b" not in result2['final_path']:
            print(f"    ❌ FAIL: Expected 'test (1).m4b' in path, got {result2['final_path']}")
            return False
        print(f"    ✓ Duplicate renamed: {Path(result2['final_path']).name}")

        # Test 3: Multiple duplicates
        print("\n  Test 3: Multiple duplicates")
        (base_path / "test (1).m4b").touch()
        result3 = namer.handle_duplicates(str(test_file))

        if result3['counter'] != 2:
            print(f"    ❌ FAIL: Counter should be 2, got {result3['counter']}")
            return False
        if "test (2).m4b" not in result3['final_path']:
            print(f"    ❌ FAIL: Expected 'test (2).m4b' in path, got {result3['final_path']}")
            return False
        print(f"    ✓ Second duplicate renamed: {Path(result3['final_path']).name}")

        # Test 4: Preserves extension
        print("\n  Test 4: Extension preservation")
        mp3_file = base_path / "audio.mp3"
        mp3_file.touch()
        result4 = namer.handle_duplicates(str(mp3_file))

        if not result4['final_path'].endswith('.mp3'):
            print(f"    ❌ FAIL: Extension not preserved: {result4['final_path']}")
            return False
        print(f"    ✓ Extension preserved: {Path(result4['final_path']).suffix}")

    print("\n  ✓ All duplicate handling tests passed")
    return True


def test_path_validation():
    """Test path structure validation."""
    print("\n=== Testing Path Validation ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        namer = FileNamer(base_directory=temp_dir)

        # Test 1: Valid path (author/file)
        print("\n  Test 1: Valid path (author/file)")
        valid_path = Path(temp_dir) / "Author" / "Book.m4b"
        result = namer.validate_path_structure(str(valid_path))

        if not result['valid']:
            print(f"    ❌ FAIL: Should be valid, issues: {result['issues']}")
            return False
        if result['path_components']['author'] != "Author":
            print(f"    ❌ FAIL: Author should be 'Author', got {result['path_components']['author']}")
            return False
        print(f"    ✓ Valid path structure")

        # Test 2: Valid path with series
        print("\n  Test 2: Valid path with series")
        series_path = Path(temp_dir) / "Author" / "Series" / "Book.m4b"
        result2 = namer.validate_path_structure(str(series_path))

        if not result2['valid']:
            print(f"    ❌ FAIL: Should be valid, issues: {result2['issues']}")
            return False
        if result2['path_components']['series'] != "Series":
            print(f"    ❌ FAIL: Series should be 'Series', got {result2['path_components']['series']}")
            return False
        print(f"    ✓ Valid path with series")

        # Test 3: Invalid extension
        print("\n  Test 3: Invalid file extension")
        invalid_ext = Path(temp_dir) / "Author" / "Book.txt"
        result3 = namer.validate_path_structure(str(invalid_ext))

        if result3['valid']:
            print("    ❌ FAIL: Should be invalid (wrong extension)")
            return False
        if not any('Invalid file extension' in issue for issue in result3['issues']):
            print(f"    ❌ FAIL: Should report extension issue, got {result3['issues']}")
            return False
        print(f"    ✓ Invalid extension detected")

        # Test 4: Too shallow path
        print("\n  Test 4: Too shallow path structure")
        shallow = Path(temp_dir) / "Book.m4b"
        result4 = namer.validate_path_structure(str(shallow))

        if result4['valid']:
            print("    ❌ FAIL: Should be invalid (missing author)")
            return False
        print(f"    ✓ Shallow path rejected")

        # Test 5: Path outside base directory
        print("\n  Test 5: Path outside base directory")
        with tempfile.TemporaryDirectory() as other_dir:
            outside_path = Path(other_dir) / "Author" / "Book.m4b"
            result5 = namer.validate_path_structure(str(outside_path))

            if result5['valid']:
                print("    ❌ FAIL: Should be invalid (outside base dir)")
                return False
            print(f"    ✓ Outside path rejected")

        # Test 6: Invalid characters in path
        print("\n  Test 6: Invalid characters in path")
        invalid_chars = Path(temp_dir) / "Author<>" / "Book.m4b"
        result6 = namer.validate_path_structure(str(invalid_chars))

        if result6['valid']:
            print("    ❌ FAIL: Should be invalid (special chars)")
            return False
        print(f"    ✓ Invalid characters detected")

    print("\n  ✓ All path validation tests passed")
    return True


def test_directory_creation():
    """Test directory structure creation."""
    print("\n=== Testing Directory Creation ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        namer = FileNamer(base_directory=temp_dir)

        # Test 1: Create new directory
        print("\n  Test 1: Create new directory")
        new_path = Path(temp_dir) / "Author" / "Series" / "book.m4b"
        result = namer.create_directory_structure(str(new_path))

        if not result['success']:
            print(f"    ❌ FAIL: Should succeed, got {result['details']}")
            return False
        if result['existed']:
            print("    ❌ FAIL: Directory should not have existed")
            return False
        if not Path(result['directory_created']).exists():
            print(f"    ❌ FAIL: Directory not created: {result['directory_created']}")
            return False
        print(f"    ✓ Directory created: {result['directory_created']}")

        # Test 2: Already existing directory
        print("\n  Test 2: Already existing directory")
        result2 = namer.create_directory_structure(str(new_path))

        if not result2['success']:
            print(f"    ❌ FAIL: Should succeed for existing dir")
            return False
        if not result2['existed']:
            print("    ❌ FAIL: Should report directory existed")
            return False
        print(f"    ✓ Existing directory detected")

        # Test 3: Nested directory creation
        print("\n  Test 3: Nested directory creation (parents=True)")
        deep_path = Path(temp_dir) / "A" / "B" / "C" / "D" / "book.m4b"
        result3 = namer.create_directory_structure(str(deep_path))

        if not result3['success']:
            print(f"    ❌ FAIL: Should create nested dirs, got {result3['details']}")
            return False
        if not (Path(temp_dir) / "A" / "B" / "C" / "D").exists():
            print("    ❌ FAIL: Nested directories not created")
            return False
        print(f"    ✓ Nested directories created")

    print("\n  ✓ All directory creation tests passed")
    return True


def test_singleton():
    """Test singleton pattern."""
    print("\n=== Testing Singleton Pattern ===")

    # Test 1: Default singleton
    print("\n  Test 1: Default singleton")
    namer1 = get_file_namer()
    namer2 = get_file_namer()

    if namer1 is not namer2:
        print("    ❌ FAIL: Should return same instance")
        return False
    print("    ✓ Same instance returned")

    # Test 2: Instance type
    print("\n  Test 2: Instance type check")
    if not isinstance(namer1, FileNamer):
        print("    ❌ FAIL: Should be FileNamer instance")
        return False
    print("    ✓ Correct instance type")

    print("\n  ✓ Singleton pattern tests passed")
    return True


def test_full_workflow():
    """Test complete workflow."""
    print("\n=== Testing Complete Workflow ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        namer = FileNamer(base_directory=temp_dir)

        # Generate filename
        print("\n  Test 1: Generate filename")
        result = namer.generate_filename(
            author="Brandon Sanderson",
            title="The Way of Kings",
            narrator="Michael Kramer",
            year=2010,
            series="Stormlight Archive"
        )

        if not result['valid']:
            print(f"    ❌ FAIL: Generation failed")
            return False
        print(f"    ✓ Generated: {result['filename']}")
        print(f"    ✓ Directory: {result['directory']}")

        # Validate path structure
        print("\n  Test 2: Validate path structure")
        validation = namer.validate_path_structure(result['full_path'])

        if not validation['valid']:
            print(f"    ❌ FAIL: Path validation failed: {validation['issues']}")
            return False
        print(f"    ✓ Path structure valid")

        # Create directory
        print("\n  Test 3: Create directory structure")
        creation = namer.create_directory_structure(result['full_path'])

        if not creation['success']:
            print(f"    ❌ FAIL: Directory creation failed: {creation['details']}")
            return False
        print(f"    ✓ Directory created")

        # Check duplicate handling
        print("\n  Test 4: Duplicate handling")
        Path(result['full_path']).touch()  # Create the file
        dup_result = namer.handle_duplicates(result['full_path'])

        if not dup_result['is_duplicate']:
            print("    ❌ FAIL: Should detect duplicate")
            return False
        print(f"    ✓ Duplicate detected and renamed")

    print("\n  ✓ Complete workflow test passed")
    return True


def main():
    """Run all file namer tests."""
    print("=" * 60)
    print("File Namer Module Validation")
    print("=" * 60)

    tests = [
        ("Initialization", test_initialization),
        ("Filename Generation", test_generate_filename),
        ("Filename Sanitization", test_sanitization),
        ("Duplicate Handling", test_handle_duplicates),
        ("Path Validation", test_path_validation),
        ("Directory Creation", test_directory_creation),
        ("Singleton Pattern", test_singleton),
        ("Complete Workflow", test_full_workflow),
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
        print("\n🎉 All file namer tests passed!")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
