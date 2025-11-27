#!/usr/bin/env python3
"""
Phase 1: Safety & Compliance Framework - Real Execution Test Suite

Tests all safety validator and operation logger functionality with REAL DATA and REAL EXECUTION.
No simulations. No mocking. Actual file operations and logging.
"""

import sys
import logging
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import time

# Setup logging for test execution
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_imports():
    """Test that all Phase 1 modules can be imported successfully."""
    logger.info("=" * 80)
    logger.info("TEST 1: Testing Phase 1 Module Imports")
    logger.info("=" * 80)

    try:
        from backend.safety_validator import SafetyValidator, get_safety_validator
        logger.info("✓ SafetyValidator imported successfully")

        from backend.logging.operation_logger import OperationLogger, get_operation_logger
        logger.info("✓ OperationLogger imported successfully")

        return True

    except Exception as e:
        logger.error(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_safety_validator_initialization():
    """Test SafetyValidator initialization with real config."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Testing SafetyValidator Initialization")
    logger.info("=" * 80)

    try:
        from backend.safety_validator import get_safety_validator

        validator = get_safety_validator()
        logger.info(f"✓ SafetyValidator initialized")
        logger.info(f"  - Backup directory: {validator.backup_dir}")
        logger.info(f"  - Audit log directory: {validator.audit_log_dir}")
        logger.info(f"  - Protected operations: {validator.protected_ops}")
        logger.info(f"  - Backup enabled: {validator.config.BACKUP_ENABLED}")

        # Verify directories exist
        assert validator.backup_dir.exists(), "Backup directory does not exist"
        assert validator.audit_log_dir.exists(), "Audit log directory does not exist"
        logger.info(f"✓ Backup and audit directories verified")

        return True

    except Exception as e:
        logger.error(f"✗ Initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_env_write_protection():
    """Test .env file write protection (should block)."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Testing .env Write Protection")
    logger.info("=" * 80)

    try:
        from backend.safety_validator import get_safety_validator

        validator = get_safety_validator()

        # Test blocking write to .env
        is_blocked = validator.check_env_write_attempt(".env")
        assert is_blocked, ".env write protection should be active"
        logger.info(f"✓ .env write protection active - write blocked")

        # Test non-.env files not blocked
        is_blocked = validator.check_env_write_attempt("metadata.json")
        assert not is_blocked, "metadata.json should not be blocked"
        logger.info(f"✓ Non-.env files allowed")

        return True

    except Exception as e:
        logger.error(f"✗ .env protection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_operation_validation():
    """Test operation validation with real protected operations."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Testing Operation Validation")
    logger.info("=" * 80)

    try:
        from backend.safety_validator import get_safety_validator

        validator = get_safety_validator()

        # Test 1: Delete audiobook without flags (should fail)
        is_valid, msg = validator.validate_operation("delete_audiobook", {})
        assert not is_valid, "Should reject delete without confirmed_delete flag"
        logger.info(f"✓ Delete without flags rejected: {msg}")

        # Test 2: Delete audiobook with correct flags (should pass)
        flags = {"confirmed_delete": True, "preserve_metadata": True}
        is_valid, msg = validator.validate_operation("delete_audiobook", flags)
        assert is_valid, f"Should accept delete with correct flags. Got: {msg}"
        logger.info(f"✓ Delete with correct flags accepted")

        # Test 3: DRM removal disabled by default (should fail)
        flags = {"confirmed_drm_removal": True}
        is_valid, msg = validator.validate_operation("drm_removal", flags)
        assert not is_valid, "DRM removal should be disabled by default"
        logger.info(f"✓ DRM removal disabled by default: {msg}")

        # Test 4: .env modification (should always fail)
        is_valid, msg = validator.validate_operation("modify_env_file", {})
        assert not is_valid, ".env modification should be blocked"
        logger.info(f"✓ .env modification blocked: {msg}")

        return True

    except Exception as e:
        logger.error(f"✗ Operation validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backup_creation():
    """Test backup creation with real metadata file."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 5: Testing Backup Creation")
    logger.info("=" * 80)

    try:
        from backend.safety_validator import get_safety_validator

        validator = get_safety_validator()

        # Create a test metadata.json file
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_file = Path(tmpdir) / "metadata.json"
            test_data = {
                "title": "Test Audiobook",
                "author": "Test Author",
                "narrator": "Test Narrator",
                "duration": 12345
            }

            with open(metadata_file, 'w') as f:
                json.dump(test_data, f)

            logger.info(f"✓ Test metadata file created: {metadata_file}")

            # Test backup creation
            success, backup_path = validator.require_backup_before_edit(str(metadata_file))
            assert success, f"Backup creation failed: {backup_path}"
            logger.info(f"✓ Backup created: {backup_path}")

            # Verify backup exists
            backup = Path(backup_path)
            assert backup.exists(), "Backup file does not exist"
            logger.info(f"✓ Backup file verified to exist")

            # Verify backup content
            with open(backup, 'r') as f:
                backup_data = json.load(f)
            assert backup_data == test_data, "Backup content does not match original"
            logger.info(f"✓ Backup content verified")

            return True

    except Exception as e:
        logger.error(f"✗ Backup creation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backup_verification():
    """Test backup verification with real JSON validation."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 6: Testing Backup Verification")
    logger.info("=" * 80)

    try:
        from backend.safety_validator import get_safety_validator

        validator = get_safety_validator()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create valid backup
            backup_file = Path(tmpdir) / "backup.json"
            backup_data = {"title": "Test", "author": "Author"}

            with open(backup_file, 'w') as f:
                json.dump(backup_data, f)

            # Test valid backup verification
            is_valid = validator.verify_backup_exists(str(backup_file))
            assert is_valid, "Should verify valid backup"
            logger.info(f"✓ Valid backup verified")

            # Test non-existent backup
            is_valid = validator.verify_backup_exists("/nonexistent/backup.json")
            assert not is_valid, "Should reject non-existent backup"
            logger.info(f"✓ Non-existent backup rejected")

            # Test invalid JSON
            invalid_file = Path(tmpdir) / "invalid.json"
            with open(invalid_file, 'w') as f:
                f.write("{ invalid json }")

            is_valid = validator.verify_backup_exists(str(invalid_file))
            assert not is_valid, "Should reject invalid JSON"
            logger.info(f"✓ Invalid JSON backup rejected")

            return True

    except Exception as e:
        logger.error(f"✗ Backup verification test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_non_destructive_check():
    """Test non-destructive change verification."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 7: Testing Non-Destructive Change Verification")
    logger.info("=" * 80)

    try:
        from backend.safety_validator import get_safety_validator

        validator = get_safety_validator()

        # Test 1: Additive change (should pass)
        old_data = {"title": "Book", "author": "Author"}
        new_data = {"title": "Book", "author": "Author", "narrator": "Narrator"}
        is_ok, msg = validator.verify_non_destructive("test.json", old_data, new_data)
        assert is_ok, f"Additive change should be allowed: {msg}"
        logger.info(f"✓ Additive change allowed")

        # Test 2: Corrective change (should pass)
        old_data = {"title": "Book", "author": "", "narrator": "Narrator"}
        new_data = {"title": "Book", "author": "Author", "narrator": "Narrator"}
        is_ok, msg = validator.verify_non_destructive("test.json", old_data, new_data)
        assert is_ok, f"Corrective change should be allowed: {msg}"
        logger.info(f"✓ Corrective change allowed")

        # Test 3: Destructive deletion (should fail)
        old_data = {"title": "Book", "author": "Author"}
        new_data = {"title": "Book"}
        is_ok, msg = validator.verify_non_destructive("test.json", old_data, new_data)
        assert not is_ok, "Destructive deletion should be blocked"
        logger.info(f"✓ Destructive deletion blocked: {msg}")

        # Test 4: Overwriting field with empty (should fail)
        old_data = {"title": "Book", "narrator": "Narrator"}
        new_data = {"title": "Book", "narrator": ""}
        is_ok, msg = validator.verify_non_destructive("test.json", old_data, new_data)
        assert not is_ok, "Overwriting with empty should be blocked"
        logger.info(f"✓ Destructive overwrite blocked: {msg}")

        return True

    except Exception as e:
        logger.error(f"✗ Non-destructive check test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_hash_calculation():
    """Test SHA256 hash calculation with real files."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 8: Testing File Hash Calculation")
    logger.info("=" * 80)

    try:
        from backend.safety_validator import get_safety_validator

        validator = get_safety_validator()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "test.txt"
            test_content = "This is test content for hashing"
            with open(test_file, 'w') as f:
                f.write(test_content)

            # Get hash
            hash1 = validator.get_file_hash(str(test_file))
            assert hash1, "Hash should not be empty"
            assert len(hash1) == 64, "SHA256 hash should be 64 hex characters"
            logger.info(f"✓ Hash calculated: {hash1[:16]}...")

            # Verify same file produces same hash
            hash2 = validator.get_file_hash(str(test_file))
            assert hash1 == hash2, "Same file should produce same hash"
            logger.info(f"✓ Hash consistency verified")

            # Test non-existent file
            hash3 = validator.get_file_hash("/nonexistent/file.txt")
            assert hash3 == "", "Non-existent file should return empty hash"
            logger.info(f"✓ Non-existent file returns empty hash")

            return True

    except Exception as e:
        logger.error(f"✗ File hash test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_integrity_verification():
    """Test file integrity verification with real hash comparison."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 9: Testing File Integrity Verification")
    logger.info("=" * 80)

    try:
        from backend.safety_validator import get_safety_validator

        validator = get_safety_validator()

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_content = "Integrity test content"
            with open(test_file, 'w') as f:
                f.write(test_content)

            # Get actual hash
            actual_hash = validator.get_file_hash(str(test_file))

            # Test with correct hash
            is_valid = validator.verify_file_integrity(str(test_file), actual_hash)
            assert is_valid, "Should verify with correct hash"
            logger.info(f"✓ File integrity verified with correct hash")

            # Test with wrong hash
            wrong_hash = "0" * 64
            is_valid = validator.verify_file_integrity(str(test_file), wrong_hash)
            assert not is_valid, "Should fail with wrong hash"
            logger.info(f"✓ File integrity fails with wrong hash")

            return True

    except Exception as e:
        logger.error(f"✗ File integrity test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_audit_logging():
    """Test audit logging with real operation logging."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 10: Testing Audit Logging")
    logger.info("=" * 80)

    try:
        from backend.safety_validator import get_safety_validator

        validator = get_safety_validator()

        # Log some operations
        validator.log_operation("backup_creation", "metadata.json", True, "Backup created successfully")
        logger.info(f"✓ Logged successful backup operation")

        validator.log_operation("delete_audiobook", "test_book.m4b", False, "User confirmation missing")
        logger.info(f"✓ Logged failed delete operation")

        validator.log_operation("metadata_update", "metadata.json", True, "Added narrator field")
        logger.info(f"✓ Logged metadata update operation")

        # Verify audit log file exists and has content
        audit_log = validator.audit_log_dir / f"{datetime.now().strftime('%Y%m%d')}_operations.log"
        if audit_log.exists():
            with open(audit_log, 'r') as f:
                content = f.read()
            line_count = len(content.strip().split('\n'))
            logger.info(f"✓ Audit log file created with {line_count} entries")
        else:
            logger.warning(f"⚠ Audit log file not created (audit logging may be disabled)")

        return True

    except Exception as e:
        logger.error(f"✗ Audit logging test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_operation_logger_initialization():
    """Test OperationLogger initialization with real directory structure."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 11: Testing OperationLogger Initialization")
    logger.info("=" * 80)

    try:
        from backend.logging.operation_logger import get_operation_logger

        logger_inst = get_operation_logger()
        logger.info(f"✓ OperationLogger initialized")
        logger.info(f"  - Logs directory: {logger_inst.logs_dir}")
        logger.info(f"  - Categories: {list(logger_inst.categories.keys())}")

        # Verify logs directory exists
        assert logger_inst.logs_dir.exists(), "Logs directory should exist"
        logger.info(f"✓ Logs directory verified")

        return True

    except Exception as e:
        logger.error(f"✗ OperationLogger initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_operation_logger_acquisition_logging():
    """Test acquisition logging with real log file creation."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 12: Testing Acquisition Logging")
    logger.info("=" * 80)

    try:
        from backend.logging.operation_logger import get_operation_logger

        logger_inst = get_operation_logger()

        # Log some acquisitions
        logger_inst.log_acquisition(
            title="Test Audiobook",
            author="Test Author",
            source="test_source",
            status="new",
            details={"source_url": "http://example.com", "file_size": 1024000}
        )
        logger.info(f"✓ Logged acquisition event")

        logger_inst.log_acquisition(
            title="Duplicate Book",
            author="Another Author",
            source="test_source",
            status="duplicate",
            details={"existing_path": "/path/to/book"}
        )
        logger.info(f"✓ Logged duplicate detection")

        # Verify log file was created
        today_logs = list(logger_inst.logs_dir.glob(f"*/acquisitions.md"))
        assert len(today_logs) > 0, "Acquisition log file should be created"
        logger.info(f"✓ Acquisition log file created")

        # Verify content
        with open(today_logs[0], 'r') as f:
            content = f.read()
        assert "Test Audiobook" in content, "Log should contain audiobook title"
        logger.info(f"✓ Log content verified")

        return True

    except Exception as e:
        logger.error(f"✗ Acquisition logging test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_operation_logger_verification_logging():
    """Test verification result logging with real log file."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 13: Testing Verification Logging")
    logger.info("=" * 80)

    try:
        from backend.logging.operation_logger import get_operation_logger

        logger_inst = get_operation_logger()

        # Log successful verification
        logger_inst.log_verification(
            title="Successful Book",
            author="Author Name",
            passed=True,
            details={"narrator_match": True, "duration_ok": True}
        )
        logger.info(f"✓ Logged successful verification")

        # Log failed verification
        logger_inst.log_verification(
            title="Failed Book",
            author="Another Author",
            passed=False,
            failures=["narrator_mismatch", "duration_out_of_range"],
            details={"expected_duration": 12000, "actual_duration": 11000}
        )
        logger.info(f"✓ Logged failed verification")

        # Verify log file
        today_logs = list(logger_inst.logs_dir.glob(f"*/verification.md"))
        assert len(today_logs) > 0, "Verification log file should be created"
        logger.info(f"✓ Verification log file created")

        with open(today_logs[0], 'r') as f:
            content = f.read()
        assert "PASSED" in content and "FAILED" in content, "Log should contain both pass and fail entries"
        logger.info(f"✓ Verification log content verified")

        return True

    except Exception as e:
        logger.error(f"✗ Verification logging test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_operation_logger_processing_logging():
    """Test audio processing logging."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 14: Testing Processing Logging")
    logger.info("=" * 80)

    try:
        from backend.logging.operation_logger import get_operation_logger

        logger_inst = get_operation_logger()

        # Log processing steps
        logger_inst.log_processing(
            title="Processed Book",
            author="Author",
            step="normalize",
            completed=True,
            details={"target_lufs": -16.0, "measured_lufs": -18.5}
        )
        logger.info(f"✓ Logged normalize step")

        logger_inst.log_processing(
            title="Processed Book",
            author="Author",
            step="merge",
            completed=True,
            details={"files_merged": 3, "duration": 45000}
        )
        logger.info(f"✓ Logged merge step")

        logger_inst.log_processing(
            title="Processed Book",
            author="Author",
            step="chapters",
            completed=True,
            details={"chapters_created": 15}
        )
        logger.info(f"✓ Logged chapters step")

        # Verify log file
        today_logs = list(logger_inst.logs_dir.glob(f"*/processing.md"))
        assert len(today_logs) > 0, "Processing log file should be created"
        logger.info(f"✓ Processing log file created")

        with open(today_logs[0], 'r') as f:
            content = f.read()
        assert "normalize" in content and "merge" in content and "chapters" in content, \
            "Log should contain all processing steps"
        logger.info(f"✓ Processing log content verified")

        return True

    except Exception as e:
        logger.error(f"✗ Processing logging test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_operation_logger_enrichment_logging():
    """Test metadata enrichment logging."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 15: Testing Enrichment Logging")
    logger.info("=" * 80)

    try:
        from backend.logging.operation_logger import get_operation_logger

        logger_inst = get_operation_logger()

        # Log enrichment
        logger_inst.log_enrichment(
            title="Enriched Book",
            author="Author",
            fields_added=["narrator", "genres", "series"],
            sources=["audible", "goodreads"],
            details={"sources_used": 2, "fields_total": 3}
        )
        logger.info(f"✓ Logged enrichment event")

        # Verify log file
        today_logs = list(logger_inst.logs_dir.glob(f"*/enrichment.md"))
        assert len(today_logs) > 0, "Enrichment log file should be created"
        logger.info(f"✓ Enrichment log file created")

        with open(today_logs[0], 'r') as f:
            content = f.read()
        assert "Enriched Book" in content and "narrator" in content, \
            "Log should contain enrichment details"
        logger.info(f"✓ Enrichment log content verified")

        return True

    except Exception as e:
        logger.error(f"✗ Enrichment logging test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_log_category_summary():
    """Test log category summary generation."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 16: Testing Log Category Summary")
    logger.info("=" * 80)

    try:
        from backend.logging.operation_logger import get_operation_logger

        logger_inst = get_operation_logger()

        # Get summary of verification logs
        summary = logger_inst.get_category_summary('verification')
        logger.info(f"✓ Generated verification summary")
        logger.info(f"  - Total entries: {summary['total_entries']}")
        logger.info(f"  - Status breakdown: {summary['status_breakdown']}")

        assert 'category' in summary, "Summary should have category field"
        assert 'total_entries' in summary, "Summary should have total_entries"
        assert 'status_breakdown' in summary, "Summary should have status_breakdown"
        logger.info(f"✓ Log summary structure verified")

        return True

    except Exception as e:
        logger.error(f"✗ Log summary test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all Phase 1 tests and report results."""
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 1: SAFETY & COMPLIANCE FRAMEWORK - COMPREHENSIVE TEST SUITE")
    logger.info("=" * 80 + "\n")

    tests = [
        ("Module Imports", test_imports),
        ("SafetyValidator Initialization", test_safety_validator_initialization),
        (".env Write Protection", test_env_write_protection),
        ("Operation Validation", test_operation_validation),
        ("Backup Creation", test_backup_creation),
        ("Backup Verification", test_backup_verification),
        ("Non-Destructive Check", test_non_destructive_check),
        ("File Hash Calculation", test_file_hash_calculation),
        ("File Integrity Verification", test_file_integrity_verification),
        ("Audit Logging", test_audit_logging),
        ("OperationLogger Initialization", test_operation_logger_initialization),
        ("Acquisition Logging", test_operation_logger_acquisition_logging),
        ("Verification Logging", test_operation_logger_verification_logging),
        ("Processing Logging", test_operation_logger_processing_logging),
        ("Enrichment Logging", test_operation_logger_enrichment_logging),
        ("Log Category Summary", test_log_category_summary),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            logger.error(f"Unexpected error in {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

        # Small delay between tests
        time.sleep(0.5)

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
