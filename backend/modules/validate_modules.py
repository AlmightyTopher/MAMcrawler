"""
Module Validation Script
Checks all backend modules for import errors and basic functionality
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_imports():
    """Validate all module imports"""
    print("=" * 70)
    print("BACKEND MODULES VALIDATION")
    print("=" * 70)
    print()

    errors = []

    # Test 1: Import main package
    print("Test 1: Importing backend.modules package...")
    try:
        import backend.modules
        print("[PASS] Package imported successfully")
        print(f"  Version: {backend.modules.__version__}")
        print(f"  Exported functions: {len(backend.modules.__all__)}")
    except Exception as e:
        print(f"[FAIL] Package import failed: {e}")
        errors.append(f"Package import: {e}")
    print()

    # Test 2: Import MAM crawler
    print("Test 2: Importing mam_crawler module...")
    try:
        from backend.modules import crawl_mam_guides, get_crawler_status, reset_crawler_state
        print("[PASS] MAM crawler functions imported")
        print(f"  - crawl_mam_guides: {callable(crawl_mam_guides)}")
        print(f"  - get_crawler_status: {callable(get_crawler_status)}")
        print(f"  - reset_crawler_state: {callable(reset_crawler_state)}")
    except Exception as e:
        print(f"[FAIL] MAM crawler import failed: {e}")
        errors.append(f"MAM crawler: {e}")
    print()

    # Test 3: Import metadata correction
    print("Test 3: Importing metadata_correction module...")
    try:
        from backend.modules import correct_book_metadata, correct_all_books
        print("[PASS] Metadata correction functions imported")
        print(f"  - correct_book_metadata: {callable(correct_book_metadata)}")
        print(f"  - correct_all_books: {callable(correct_all_books)}")
    except Exception as e:
        print(f"[FAIL] Metadata correction import failed: {e}")
        errors.append(f"Metadata correction: {e}")
    print()

    # Test 4: Import series completion
    print("Test 4: Importing series_completion module...")
    try:
        from backend.modules import (
            find_missing_series_books,
            download_missing_series_books,
            import_and_correct_series
        )
        print("[PASS] Series completion functions imported")
        print(f"  - find_missing_series_books: {callable(find_missing_series_books)}")
        print(f"  - download_missing_series_books: {callable(download_missing_series_books)}")
        print(f"  - import_and_correct_series: {callable(import_and_correct_series)}")
    except Exception as e:
        print(f"[FAIL] Series completion import failed: {e}")
        errors.append(f"Series completion: {e}")
    print()

    # Test 5: Import author completion
    print("Test 5: Importing author_completion module...")
    try:
        from backend.modules import (
            find_missing_author_books,
            download_missing_author_books,
            import_and_correct_authors
        )
        print("[PASS] Author completion functions imported")
        print(f"  - find_missing_author_books: {callable(find_missing_author_books)}")
        print(f"  - download_missing_author_books: {callable(download_missing_author_books)}")
        print(f"  - import_and_correct_authors: {callable(import_and_correct_authors)}")
    except Exception as e:
        print(f"[FAIL] Author completion import failed: {e}")
        errors.append(f"Author completion: {e}")
    print()

    # Test 6: Import top10 discovery
    print("Test 6: Importing top10_discovery module...")
    try:
        from backend.modules import (
            scrape_mam_top10,
            queue_top10_downloads,
            get_available_genres
        )
        print("[PASS] Top10 discovery functions imported")
        print(f"  - scrape_mam_top10: {callable(scrape_mam_top10)}")
        print(f"  - queue_top10_downloads: {callable(queue_top10_downloads)}")
        print(f"  - get_available_genres: {callable(get_available_genres)}")
    except Exception as e:
        print(f"[FAIL] Top10 discovery import failed: {e}")
        errors.append(f"Top10 discovery: {e}")
    print()

    # Test 7: Check module structure
    print("Test 7: Validating module structure...")
    try:
        modules_dir = Path(__file__).parent
        required_files = [
            "__init__.py",
            "mam_crawler.py",
            "metadata_correction.py",
            "series_completion.py",
            "author_completion.py",
            "top10_discovery.py",
            "README.md"
        ]

        missing = []
        for filename in required_files:
            filepath = modules_dir / filename
            if not filepath.exists():
                missing.append(filename)

        if missing:
            print(f"[FAIL] Missing files: {', '.join(missing)}")
            errors.append(f"Missing files: {missing}")
        else:
            print("[PASS] All required files present")
            for filename in required_files:
                filepath = modules_dir / filename
                size = filepath.stat().st_size
                print(f"  - {filename}: {size:,} bytes")
    except Exception as e:
        print(f"[FAIL] Structure validation failed: {e}")
        errors.append(f"Structure: {e}")
    print()

    # Summary
    print("=" * 70)
    if errors:
        print(f"VALIDATION FAILED - {len(errors)} error(s)")
        print("=" * 70)
        for i, error in enumerate(errors, 1):
            print(f"{i}. {error}")
        return False
    else:
        print("VALIDATION SUCCESSFUL - All modules ready!")
        print("=" * 70)
        return True


if __name__ == "__main__":
    success = validate_imports()
    sys.exit(0 if success else 1)
