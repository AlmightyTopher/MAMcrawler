#!/usr/bin/env python3
"""
Phase 5: Complete Repair & Replacement System - Real Execution Test Suite

Tests all three components (QualityComparator, RepairOrchestrator, RepairReporter)
with real execution, real logging, and real file operations.
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
    """Test that all Phase 5 modules can be imported successfully."""
    logger.info("=" * 80)
    logger.info("TEST 1: Testing Phase 5 Module Imports")
    logger.info("=" * 80)

    try:
        from mamcrawler.repair.quality_comparator import QualityComparator, get_quality_comparator
        logger.info("✓ QualityComparator imported successfully")

        from mamcrawler.repair.repair_orchestrator import RepairOrchestrator, get_repair_orchestrator
        logger.info("✓ RepairOrchestrator imported successfully")

        from mamcrawler.repair.repair_reporter import RepairReporter, get_repair_reporter
        logger.info("✓ RepairReporter imported successfully")

        return True

    except Exception as e:
        logger.error(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_singleton_instances():
    """Test that singleton instances work correctly."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Testing Singleton Instances")
    logger.info("=" * 80)

    try:
        from mamcrawler.repair import (
            get_quality_comparator,
            get_repair_orchestrator,
            get_repair_reporter
        )

        # Get instances
        comparator1 = get_quality_comparator()
        comparator2 = get_quality_comparator()
        assert comparator1 is comparator2, "QualityComparator should be singleton"
        logger.info("✓ QualityComparator is singleton")

        orchestrator1 = get_repair_orchestrator()
        orchestrator2 = get_repair_orchestrator()
        assert orchestrator1 is orchestrator2, "RepairOrchestrator should be singleton"
        logger.info("✓ RepairOrchestrator is singleton")

        reporter1 = get_repair_reporter()
        reporter2 = get_repair_reporter()
        assert reporter1 is reporter2, "RepairReporter should be singleton"
        logger.info("✓ RepairReporter is singleton")

        return True

    except Exception as e:
        logger.error(f"✗ Singleton test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_quality_comparator_with_real_files():
    """Test QualityComparator with real temporary audio files."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Testing QualityComparator with Real Files")
    logger.info("=" * 80)

    try:
        from mamcrawler.repair import get_quality_comparator

        comparator = get_quality_comparator()

        # Create temporary test files (we'll test with simple files)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create test file 1
            test_file1 = tmpdir / "test1.m4b"
            test_file1.write_bytes(b"test audio data 1")
            logger.info(f"✓ Created test file 1: {test_file1}")

            # Create test file 2
            test_file2 = tmpdir / "test2.m4b"
            test_file2.write_bytes(b"test audio data 2")
            logger.info(f"✓ Created test file 2: {test_file2}")

            # Test with non-existent files (expected behavior)
            result = comparator.compare_quality(
                str(test_file1),
                str(test_file2)
            )

            assert result is not None, "Comparison should return result"
            assert 'original' in result, "Result should have 'original' key"
            assert 'replacement' in result, "Result should have 'replacement' key"
            assert 'comparison' in result, "Result should have 'comparison' key"
            logger.info("✓ Quality comparison returned proper structure")

            # Since these aren't real audio files, properties should be None
            if result['original'] is None and result['replacement'] is None:
                logger.info("✓ Non-audio files properly returned None for properties (expected)")
            else:
                logger.info("⚠ Audio files were processed (unexpected but acceptable)")

            return True

    except Exception as e:
        logger.error(f"✗ QualityComparator real file test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_repair_orchestrator_initialization():
    """Test RepairOrchestrator initialization and configuration."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Testing RepairOrchestrator Initialization")
    logger.info("=" * 80)

    try:
        from mamcrawler.repair import get_repair_orchestrator

        orchestrator = get_repair_orchestrator()

        # Check attributes
        assert hasattr(orchestrator, 'max_replacement_candidates'), "Should have max_replacement_candidates"
        assert hasattr(orchestrator, 'quality_comparator'), "Should have quality_comparator"
        assert hasattr(orchestrator, 'safety_validator'), "Should have safety_validator"
        assert hasattr(orchestrator, 'logger'), "Should have logger"
        logger.info("✓ RepairOrchestrator has all required attributes")

        # Check methods
        assert hasattr(orchestrator, 'evaluate_replacement'), "Should have evaluate_replacement method"
        assert hasattr(orchestrator, 'execute_replacement'), "Should have execute_replacement method"
        assert hasattr(orchestrator, 'batch_evaluate_replacements'), "Should have batch_evaluate_replacements method"
        logger.info("✓ RepairOrchestrator has all required methods")

        logger.info(f"✓ Max replacement candidates: {orchestrator.max_replacement_candidates}")

        return True

    except Exception as e:
        logger.error(f"✗ RepairOrchestrator initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_repair_orchestrator_evaluation():
    """Test RepairOrchestrator evaluation workflow."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 5: Testing RepairOrchestrator Evaluation Workflow")
    logger.info("=" * 80)

    try:
        from mamcrawler.repair import get_repair_orchestrator

        orchestrator = get_repair_orchestrator()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create test files
            original = tmpdir / "original.m4b"
            replacement = tmpdir / "replacement.m4b"
            original.write_bytes(b"original audio")
            replacement.write_bytes(b"replacement audio")

            # Evaluate replacement
            result = orchestrator.evaluate_replacement(
                str(original),
                str(replacement),
                audiobook_title="Test Audiobook",
                author="Test Author"
            )

            # Verify result structure
            assert result is not None, "Evaluation should return result"
            assert 'is_acceptable' in result, "Result should have 'is_acceptable' key"
            assert 'quality_comparison' in result, "Result should have 'quality_comparison' key"
            assert 'decision' in result, "Result should have 'decision' key"
            assert 'reason' in result, "Result should have 'reason' key"
            assert 'audiobook_title' in result, "Result should have 'audiobook_title' key"
            assert 'author' in result, "Result should have 'author' key"
            logger.info("✓ Evaluation returned proper structure")

            # Log decision
            logger.info(f"✓ Decision: {result['decision']}")
            logger.info(f"✓ Reason: {result['reason']}")
            logger.info(f"✓ Is Acceptable: {result['is_acceptable']}")

            return True

    except Exception as e:
        logger.error(f"✗ RepairOrchestrator evaluation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_repair_orchestrator_backup_creation():
    """Test RepairOrchestrator backup creation."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 6: Testing RepairOrchestrator Backup Creation")
    logger.info("=" * 80)

    try:
        from mamcrawler.repair import get_repair_orchestrator

        orchestrator = get_repair_orchestrator()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create test files
            original = tmpdir / "original.m4b"
            replacement = tmpdir / "replacement.m4b"
            original.write_text("original audio content")
            replacement.write_text("replacement audio content")

            # Test backup creation
            backup = orchestrator._create_backup(original)

            if backup:
                assert backup.exists(), "Backup file should exist"
                logger.info(f"✓ Backup created: {backup}")

                # Verify backup content
                backup_content = backup.read_text()
                original_content = original.read_text()
                assert backup_content == original_content, "Backup should have same content"
                logger.info("✓ Backup content matches original")

                return True
            else:
                logger.error("✗ Backup creation returned None")
                return False

    except Exception as e:
        logger.error(f"✗ Backup creation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_repair_reporter_initialization():
    """Test RepairReporter initialization."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 7: Testing RepairReporter Initialization")
    logger.info("=" * 80)

    try:
        from mamcrawler.repair import get_repair_reporter

        reporter = get_repair_reporter()

        # Check attributes
        assert hasattr(reporter, 'report_timestamp'), "Should have report_timestamp"
        logger.info("✓ RepairReporter has report_timestamp attribute")

        # Check methods
        assert hasattr(reporter, 'generate_evaluation_report'), "Should have generate_evaluation_report"
        assert hasattr(reporter, 'generate_execution_report'), "Should have generate_execution_report"
        assert hasattr(reporter, 'generate_batch_report'), "Should have generate_batch_report"
        assert hasattr(reporter, 'generate_summary_report'), "Should have generate_summary_report"
        logger.info("✓ RepairReporter has all report generation methods")

        assert hasattr(reporter, 'format_report_as_json'), "Should have format_report_as_json"
        assert hasattr(reporter, 'format_report_as_markdown'), "Should have format_report_as_markdown"
        logger.info("✓ RepairReporter has all formatting methods")

        return True

    except Exception as e:
        logger.error(f"✗ RepairReporter initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_repair_reporter_report_generation():
    """Test RepairReporter report generation with real data."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 8: Testing RepairReporter Report Generation")
    logger.info("=" * 80)

    try:
        from mamcrawler.repair import get_repair_reporter, get_repair_orchestrator

        reporter = get_repair_reporter()
        orchestrator = get_repair_orchestrator()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create test files
            original = tmpdir / "original.m4b"
            replacement = tmpdir / "replacement.m4b"
            original.write_bytes(b"original audio")
            replacement.write_bytes(b"replacement audio")

            # Create evaluation
            evaluation = orchestrator.evaluate_replacement(
                str(original),
                str(replacement),
                audiobook_title="Test Audiobook",
                author="Test Author"
            )

            # Generate evaluation report
            eval_report = reporter.generate_evaluation_report(evaluation)
            assert eval_report is not None, "Should generate evaluation report"
            assert eval_report['report_type'] == 'EVALUATION', "Report type should be EVALUATION"
            logger.info("✓ Generated evaluation report")

            # Format as JSON
            json_str = reporter.format_report_as_json(eval_report)
            assert json_str is not None, "Should format as JSON"
            json_data = json.loads(json_str)
            assert json_data['report_type'] == 'EVALUATION', "JSON should contain report_type"
            logger.info("✓ Formatted evaluation report as JSON")

            # Format as Markdown
            md_str = reporter.format_report_as_markdown(eval_report)
            assert md_str is not None, "Should format as Markdown"
            assert '# Replacement Evaluation Report' in md_str, "Markdown should have header"
            logger.info("✓ Formatted evaluation report as Markdown")

            # Save report
            report_path = tmpdir / "report"
            success = reporter.save_report(eval_report, str(report_path), format='both')
            assert success, "Should save report"
            assert (tmpdir / "report.json").exists(), "JSON file should exist"
            assert (tmpdir / "report.md").exists(), "Markdown file should exist"
            logger.info("✓ Saved report in both formats")

            return True

    except Exception as e:
        logger.error(f"✗ RepairReporter report generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_batch_evaluation():
    """Test batch evaluation of replacement candidates."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 9: Testing Batch Replacement Evaluation")
    logger.info("=" * 80)

    try:
        from mamcrawler.repair import get_repair_orchestrator

        orchestrator = get_repair_orchestrator()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create original file
            original = tmpdir / "original.m4b"
            original.write_bytes(b"original audio content")

            # Create replacement candidates
            candidates = []
            for i in range(3):
                candidate = tmpdir / f"candidate_{i}.m4b"
                candidate.write_bytes(f"replacement audio content {i}".encode())
                candidates.append(str(candidate))
            logger.info(f"✓ Created {len(candidates)} replacement candidates")

            # Batch evaluate
            result = orchestrator.batch_evaluate_replacements(
                str(original),
                candidates,
                audiobook_title="Test Audiobook",
                author="Test Author"
            )

            assert result is not None, "Should return batch result"
            assert 'audiobook_title' in result, "Should have audiobook_title"
            assert 'candidates_evaluated' in result, "Should have candidates_evaluated"
            assert 'acceptable_candidates' in result, "Should have acceptable_candidates"
            assert result['candidates_evaluated'] == len(candidates), "Should evaluate all candidates"
            logger.info("✓ Batch evaluation completed successfully")
            logger.info(f"✓ Evaluated candidates: {result['candidates_evaluated']}")
            logger.info(f"✓ Acceptable candidates: {result['acceptable_candidates']}")

            return True

    except Exception as e:
        logger.error(f"✗ Batch evaluation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_summary_report():
    """Test summary report generation."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 10: Testing Summary Report Generation")
    logger.info("=" * 80)

    try:
        from mamcrawler.repair import get_repair_reporter

        reporter = get_repair_reporter()

        # Create sample repairs list
        repairs = [
            {
                'report_type': 'EXECUTION',
                'success': True,
                'audiobook': 'Book 1'
            },
            {
                'report_type': 'EXECUTION',
                'success': False,
                'audiobook': 'Book 2'
            },
            {
                'report_type': 'EVALUATION',
                'decision': 'APPROVED',
                'audiobook': 'Book 3'
            },
            {
                'report_type': 'EVALUATION',
                'decision': 'REJECTED',
                'audiobook': 'Book 4'
            }
        ]

        # Generate summary
        summary = reporter.generate_summary_report(repairs)

        assert summary is not None, "Should generate summary"
        assert summary['report_type'] == 'SUMMARY', "Report type should be SUMMARY"
        assert summary['total_operations'] == len(repairs), "Should count all operations"
        assert summary['successful_executions'] == 1, "Should count successful executions"
        assert summary['failed_repairs'] == 1, "Should count failed repairs"
        assert summary['approved_evaluations'] == 1, "Should count approved evaluations"
        logger.info("✓ Summary report generated successfully")
        logger.info(f"✓ Total operations: {summary['total_operations']}")
        logger.info(f"✓ Successful executions: {summary['successful_executions']}")
        logger.info(f"✓ Failed repairs: {summary['failed_repairs']}")
        logger.info(f"✓ Approved evaluations: {summary['approved_evaluations']}")

        # Format as Markdown
        md_str = reporter.format_report_as_markdown(summary)
        assert '# Repair Operations Summary Report' in md_str, "Markdown should have header"
        logger.info("✓ Summary formatted as Markdown")

        return True

    except Exception as e:
        logger.error(f"✗ Summary report test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all Phase 5 tests and report results."""
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 5: COMPLETE REPAIR & REPLACEMENT SYSTEM - TEST SUITE")
    logger.info("=" * 80 + "\n")

    tests = [
        ("Module Imports", test_imports),
        ("Singleton Instances", test_singleton_instances),
        ("QualityComparator with Real Files", test_quality_comparator_with_real_files),
        ("RepairOrchestrator Initialization", test_repair_orchestrator_initialization),
        ("RepairOrchestrator Evaluation Workflow", test_repair_orchestrator_evaluation),
        ("RepairOrchestrator Backup Creation", test_repair_orchestrator_backup_creation),
        ("RepairReporter Initialization", test_repair_reporter_initialization),
        ("RepairReporter Report Generation", test_repair_reporter_report_generation),
        ("Batch Replacement Evaluation", test_batch_evaluation),
        ("Summary Report Generation", test_summary_report),
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
