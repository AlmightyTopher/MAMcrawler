#!/usr/bin/env python3
"""
Test suite for Phase 3 (Audio Processing) and Phase 4 (Metadata Enrichment) modules.
Tests all core functionality without external API calls.
"""

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_imports():
    """Test that all modules can be imported successfully."""
    logger.info("=" * 80)
    logger.info("TEST 1: Testing Module Imports")
    logger.info("=" * 80)

    try:
        # Audio Processing imports
        from mamcrawler.audio_processing import (
            get_audio_normalizer,
            get_audio_merger,
            get_chapter_handler,
            get_file_namer,
            get_audio_processor_orchestrator
        )
        logger.info("✓ Audio Processing modules imported successfully")

        # Metadata Enrichment imports
        from mamcrawler.metadata import (
            get_audible_source,
            get_goodreads_source,
            get_openlibrary_source,
            get_metadata_validator,
            get_metadata_enricher,
            get_cover_art_handler
        )
        logger.info("✓ Metadata Enrichment modules imported successfully")

        return True

    except Exception as e:
        logger.error(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_normalizer():
    """Test Audio Normalizer initialization and methods."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Testing Audio Normalizer")
    logger.info("=" * 80)

    try:
        from mamcrawler.audio_processing import get_audio_normalizer

        normalizer = get_audio_normalizer(target_lufs=-16.0, output_format="m4b")
        logger.info(f"✓ AudioNormalizer initialized")
        logger.info(f"  - Target LUFS: {normalizer.target_lufs}")
        logger.info(f"  - Output format: {normalizer.output_format}")

        # Test dynamic range config
        dr_config = normalizer.preserve_dynamic_range()
        logger.info(f"✓ Dynamic range config retrieved: {dr_config['filter']}")

        return True

    except Exception as e:
        logger.error(f"✗ Normalizer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_merger():
    """Test Audio Merger initialization and pattern detection."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Testing Audio Merger")
    logger.info("=" * 80)

    try:
        from mamcrawler.audio_processing import get_audio_merger

        merger = get_audio_merger()
        logger.info(f"✓ AudioMerger initialized")
        logger.info(f"  - Split patterns supported: {len(merger.split_patterns)}")

        # Test pattern list
        for pattern in merger.split_patterns:
            logger.info(f"    - Pattern: {pattern}")

        return True

    except Exception as e:
        logger.error(f"✗ Merger test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_chapter_handler():
    """Test Chapter Handler initialization."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Testing Chapter Handler")
    logger.info("=" * 80)

    try:
        from mamcrawler.audio_processing import get_chapter_handler

        chapter_handler = get_chapter_handler()
        logger.info(f"✓ ChapterHandler initialized")
        logger.info(f"  - Ready to process audio chapters")

        return True

    except Exception as e:
        logger.error(f"✗ Chapter Handler test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_namer():
    """Test File Namer functionality."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 5: Testing File Namer")
    logger.info("=" * 80)

    try:
        from mamcrawler.audio_processing import get_file_namer

        namer = get_file_namer()
        logger.info(f"✓ FileNamer initialized")
        logger.info(f"  - Base directory: {namer.base_directory}")

        # Test filename generation
        result = namer.generate_filename(
            author="Brandon Sanderson",
            title="The Way of Kings",
            narrator="Michael Kramer",
            year=2009,
            series="Stormlight Archive"
        )

        if result['valid']:
            logger.info(f"✓ Filename generation successful")
            logger.info(f"  - Filename: {result['filename']}")
            logger.info(f"  - Directory: {result['directory']}")
            logger.info(f"  - Full path: {result['full_path']}")
        else:
            logger.error(f"✗ Filename generation failed")
            return False

        # Test sanitization
        sanitized = namer.sanitize_filename("Invalid<>:Filename|?*")
        logger.info(f"✓ Filename sanitization: '{sanitized}'")

        return True

    except Exception as e:
        logger.error(f"✗ File Namer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_processor_orchestrator():
    """Test Audio Processor Orchestrator initialization."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 6: Testing Audio Processor Orchestrator")
    logger.info("=" * 80)

    try:
        from mamcrawler.audio_processing import get_audio_processor_orchestrator

        orchestrator = get_audio_processor_orchestrator(output_format="m4b")
        logger.info(f"✓ AudioProcessorOrchestrator initialized")
        logger.info(f"  - Output format: {orchestrator.output_format}")
        logger.info(f"  - Normalizer available: {orchestrator.normalizer is not None}")
        logger.info(f"  - Merger available: {orchestrator.merger is not None}")
        logger.info(f"  - Chapter handler available: {orchestrator.chapter_handler is not None}")
        logger.info(f"  - File namer available: {orchestrator.file_namer is not None}")

        return True

    except Exception as e:
        logger.error(f"✗ Processor Orchestrator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_audible_source():
    """Test Audible Metadata Source initialization."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 7: Testing Audible Metadata Source")
    logger.info("=" * 80)

    try:
        from mamcrawler.metadata import get_audible_source

        audible = get_audible_source()
        logger.info(f"✓ AudibleMetadataSource initialized")
        logger.info(f"  - Base URL: {audible.base_url}")
        logger.info(f"  - Timeout: {audible.timeout}s")

        return True

    except Exception as e:
        logger.error(f"✗ Audible Source test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_goodreads_source():
    """Test Goodreads Metadata Source initialization."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 8: Testing Goodreads Metadata Source")
    logger.info("=" * 80)

    try:
        from mamcrawler.metadata import get_goodreads_source

        goodreads = get_goodreads_source()
        logger.info(f"✓ GoodreadsMetadataSource initialized")
        logger.info(f"  - Base URL: {goodreads.base_url}")
        logger.info(f"  - Timeout: {goodreads.timeout}s")

        return True

    except Exception as e:
        logger.error(f"✗ Goodreads Source test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_openlibrary_source():
    """Test OpenLibrary Metadata Source initialization."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 9: Testing OpenLibrary Metadata Source")
    logger.info("=" * 80)

    try:
        from mamcrawler.metadata import get_openlibrary_source

        openlibrary = get_openlibrary_source()
        logger.info(f"✓ OpenLibraryMetadataSource initialized")
        logger.info(f"  - Base URL: {openlibrary.base_url}")
        logger.info(f"  - Timeout: {openlibrary.timeout}s")

        return True

    except Exception as e:
        logger.error(f"✗ OpenLibrary Source test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_metadata_validator():
    """Test Metadata Validator functionality."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 10: Testing Metadata Validator")
    logger.info("=" * 80)

    try:
        from mamcrawler.metadata import get_metadata_validator

        validator = get_metadata_validator()
        logger.info(f"✓ MetadataValidator initialized")

        # Test required fields validation
        valid_metadata = {
            'title': 'Test Book',
            'author': 'Test Author'
        }

        is_valid, missing = validator.validate_required_fields(valid_metadata)
        logger.info(f"✓ Required fields check: {is_valid} (missing: {missing})")

        # Test format validation
        test_metadata = {
            'title': 'Test Book',
            'author': 'Test Author',
            'releaseYear': 2023,
            'rating': 4.5,
            'genres': ['fiction', 'adventure']
        }

        format_valid, errors = validator.validate_format(test_metadata)
        logger.info(f"✓ Format validation: {format_valid} (errors: {len(errors)})")

        # Test sanitization
        dirty_metadata = {
            'title': '  Book   Title  ',
            'author': 'Author   Name  ',
            'description': 'Test<>Description'
        }

        cleaned = validator.sanitize_text_fields(dirty_metadata)
        logger.info(f"✓ Text sanitization completed")
        logger.info(f"  - Title: '{cleaned['title']}'")
        logger.info(f"  - Author: '{cleaned['author']}'")

        # Test complete validation
        result = validator.validate_audiobook(test_metadata)
        logger.info(f"✓ Complete validation: {result['valid']}")
        logger.info(f"  - Errors: {len(result['errors'])}")
        logger.info(f"  - Warnings: {len(result['warnings'])}")

        return True

    except Exception as e:
        logger.error(f"✗ Metadata Validator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_metadata_enricher():
    """Test Metadata Enricher initialization."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 11: Testing Metadata Enricher")
    logger.info("=" * 80)

    try:
        from mamcrawler.metadata import get_metadata_enricher

        enricher = get_metadata_enricher()
        logger.info(f"✓ MetadataEnricher initialized")
        logger.info(f"  - Audible source available: {enricher.audible_source is not None}")
        logger.info(f"  - Goodreads source available: {enricher.goodreads_source is not None}")
        logger.info(f"  - OpenLibrary source available: {enricher.openlibrary_source is not None}")
        logger.info(f"  - Validator available: {enricher.validator is not None}")

        # Test metadata merging (local test without API calls)
        base = {'title': 'Book', 'author': 'Author'}
        enrichment = {'narrator': 'Narrator Name', 'genres': ['fiction']}

        merged = enricher._merge_metadata(base, enrichment, 'test')
        logger.info(f"✓ Metadata merging successful")
        logger.info(f"  - Merged fields: {len(merged)}")

        # Test enriched metadata generation
        test_data = {
            'title': 'Book Title',
            'author': 'Author Name',
            'narrator': 'Narrator',
            'series': 'Series Name',
            'genres': ['fiction'],
            'rating': 4.5
        }

        final = enricher.generate_enriched_metadata(test_data)
        logger.info(f"✓ Enriched metadata generation successful")
        logger.info(f"  - Final fields: {len(final)}")

        return True

    except Exception as e:
        logger.error(f"✗ Metadata Enricher test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cover_art_handler():
    """Test Cover Art Handler initialization."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 12: Testing Cover Art Handler")
    logger.info("=" * 80)

    try:
        from mamcrawler.metadata import get_cover_art_handler

        handler = get_cover_art_handler()
        logger.info(f"✓ CoverArtHandler initialized")
        logger.info(f"  - Cache directory: {handler.cache_directory}")
        logger.info(f"  - Cache directory exists: {handler.cache_directory.exists()}")
        logger.info(f"  - Supported formats: {handler.supported_formats}")

        return True

    except Exception as e:
        logger.error(f"✗ Cover Art Handler test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests and report results."""
    logger.info("\n" + "=" * 80)
    logger.info("AUDIOBOOK ARCHIVIST - PHASE 3 & 4 COMPREHENSIVE TEST SUITE")
    logger.info("=" * 80 + "\n")

    tests = [
        ("Module Imports", test_imports),
        ("Audio Normalizer", test_normalizer),
        ("Audio Merger", test_merger),
        ("Chapter Handler", test_chapter_handler),
        ("File Namer", test_file_namer),
        ("Processor Orchestrator", test_processor_orchestrator),
        ("Audible Source", test_audible_source),
        ("Goodreads Source", test_goodreads_source),
        ("OpenLibrary Source", test_openlibrary_source),
        ("Metadata Validator", test_metadata_validator),
        ("Metadata Enricher", test_metadata_enricher),
        ("Cover Art Handler", test_cover_art_handler),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            logger.error(f"Unexpected error in {test_name}: {e}")
            results.append((test_name, False))

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"{status}: {test_name}")

    logger.info("\n" + "=" * 80)
    logger.info(f"TOTAL: {passed}/{total} tests passed")
    logger.info("=" * 80 + "\n")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
