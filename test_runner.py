#!/usr/bin/env python3
"""
MAMcrawler Unified Test Runner
===============================

Main entry point for running all tests in the unified testing framework.

Features:
- Test discovery and execution
- Parallel test execution
- Comprehensive reporting (JSON, HTML, coverage)
- CI/CD integration
- Test type filtering
- Performance monitoring

Usage:
    python test_runner.py                    # Run all tests
    python test_runner.py --types unit integration  # Run specific test types
    python test_runner.py --parallel         # Run tests in parallel
    python test_runner.py --coverage         # Generate coverage reports
    python test_runner.py --ci               # CI mode with JUnit output

Author: Agent 7 - Unified Testing Framework Specialist
"""

import asyncio
import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import subprocess
import coverage
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from test_framework import TestRunner, run_tests

class UnifiedTestRunner:
    """Enhanced test runner with CI/CD and advanced reporting features."""

    def __init__(self):
        self.base_dir = Path.cwd()
        self.test_dir = self.base_dir / "tests"
        self.reports_dir = self.base_dir / "test_reports"
        self.fixtures_dir = self.base_dir / "test_fixtures"

        # Create directories
        for dir_path in [self.reports_dir, self.fixtures_dir]:
            dir_path.mkdir(exist_ok=True)

        # Setup logging
        self._setup_logging()

    def _setup_logging(self):
        """Setup comprehensive logging."""
        self.logger = logging.getLogger('test_runner')
        self.logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)

        # File handler
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = self.reports_dir / f"test_run_{timestamp}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)

        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

        self.logger.info("Unified Test Runner initialized")
        self.logger.info(f"Test directory: {self.test_dir}")
        self.logger.info(f"Reports directory: {self.reports_dir}")
        self.logger.info(f"Fixtures directory: {self.fixtures_dir}")

    def discover_test_files(self) -> Dict[str, List[Path]]:
        """Discover test files organized by type."""
        if not self.test_dir.exists():
            self.logger.warning(f"Test directory {self.test_dir} does not exist")
            return {}

        test_files = {}

        # Find test files
        for py_file in self.test_dir.rglob("test_*.py"):
            # Determine test type from file path or content
            test_type = self._determine_test_type(py_file)
            if test_type not in test_files:
                test_files[test_type] = []
            test_files[test_type].append(py_file)

        self.logger.info(f"Discovered test files: {sum(len(files) for files in test_files.values())} total")
        for test_type, files in test_files.items():
            self.logger.info(f"  {test_type}: {len(files)} files")

        return test_files

    def _determine_test_type(self, test_file: Path) -> str:
        """Determine test type from file path and content."""
        # Check file path patterns
        path_str = str(test_file).lower()

        if 'unit' in path_str or 'test_unit' in path_str:
            return 'unit'
        elif 'integration' in path_str or 'test_integration' in path_str:
            return 'integration'
        elif 'e2e' in path_str or 'end_to_end' in path_str:
            return 'e2e'
        elif 'performance' in path_str or 'perf' in path_str:
            return 'performance'
        elif 'api' in path_str:
            return 'api'
        elif 'database' in path_str or 'db' in path_str:
            return 'database'

        # Check file content for test class inheritance
        try:
            with open(test_file, 'r') as f:
                content = f.read()

            if 'UnitTestCase' in content:
                return 'unit'
            elif 'IntegrationTestCase' in content:
                return 'integration'
            elif 'E2ETestCase' in content:
                return 'e2e'
            elif 'PerformanceTestCase' in content:
                return 'performance'
            elif 'APITestCase' in content:
                return 'api'
            elif 'DatabaseTestCase' in content:
                return 'database'
        except Exception:
            pass

        return 'custom'

    def run_unified_tests(self, test_types: List[str] = None, parallel: bool = False,
                         coverage_enabled: bool = True, ci_mode: bool = False) -> Dict[str, Any]:
        """Run tests using the unified framework."""
        self.logger.info("Running unified test framework...")

        # Use the unified test framework
        report = run_tests(
            test_types=test_types,
            parallel=parallel,
            output_dir=self.reports_dir
        )

        # Generate additional reports if needed
        if coverage_enabled:
            self._generate_coverage_report()

        if ci_mode:
            self._generate_junit_report(report)

        return report

    def run_pytest_tests(self, test_types: List[str] = None, parallel: bool = False,
                        coverage_enabled: bool = True, ci_mode: bool = False) -> Dict[str, Any]:
        """Run tests using pytest for compatibility."""
        self.logger.info("Running pytest tests...")

        # Build pytest command
        cmd = [sys.executable, '-m', 'pytest']

        # Add test type filtering
        if test_types:
            # Map test types to pytest markers
            markers = []
            for test_type in test_types:
                if test_type == 'unit':
                    markers.append('unit')
                elif test_type == 'integration':
                    markers.append('integration')
                elif test_type == 'e2e':
                    markers.append('e2e')
                elif test_type == 'performance':
                    markers.append('performance')
                elif test_type == 'api':
                    markers.append('api')
                elif test_type == 'database':
                    markers.append('database')

            if markers:
                cmd.extend(['-m', ' or '.join(markers)])

        # Add parallel execution
        if parallel:
            try:
                import pytest_xdist
                cmd.extend(['-n', 'auto'])
            except ImportError:
                self.logger.warning("pytest-xdist not available, running sequentially")

        # Add coverage
        if coverage_enabled:
            cmd.extend([
                '--cov=.',
                '--cov-report=html',
                '--cov-report=json',
                '--cov-report=term-missing'
            ])

        # Add JUnit output for CI
        if ci_mode:
            junit_file = self.reports_dir / f"junit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
            cmd.extend(['--junitxml', str(junit_file)])

        # Add output directory
        cmd.extend([
            '--tb=short',
            '--strict-markers',
            '-v',
            str(self.test_dir)
        ])

        self.logger.info(f"Running command: {' '.join(cmd)}")

        # Run pytest
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = time.time() - start_time

        # Parse results
        report = self._parse_pytest_output(result, duration)

        # Save detailed results
        result_file = self.reports_dir / f"pytest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(result_file, 'w') as f:
            json.dump({
                'command': cmd,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'report': report
            }, f, indent=2)

        return report

    def _parse_pytest_output(self, result: subprocess.CompletedProcess, duration: float) -> Dict[str, Any]:
        """Parse pytest output to extract test results."""
        stdout = result.stdout
        stderr = result.stderr

        # Extract test counts from output
        import re

        # Look for patterns like "5 passed, 2 failed, 1 skipped"
        match = re.search(r'(\d+)\s+passed(?:,\s*(\d+)\s+failed)?(?:,\s*(\d+)\s+skipped)?(?:,\s*(\d+)\s+errors?)?(?:,\s*(\d+)\s+warnings?)?', stdout)

        passed = int(match.group(1)) if match and match.group(1) else 0
        failed = int(match.group(2)) if match and match.group(2) else 0
        skipped = int(match.group(3)) if match and match.group(3) else 0
        errors = int(match.group(4)) if match and match.group(4) else 0

        total_tests = passed + failed + skipped + errors

        return {
            'summary': {
                'timestamp': datetime.now().isoformat(),
                'total_tests': total_tests,
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
                'errors': errors,
                'success_rate': (passed / total_tests * 100) if total_tests > 0 else 0,
                'total_duration': duration,
                'returncode': result.returncode
            },
            'output': {
                'stdout': stdout,
                'stderr': stderr
            }
        }

    def _generate_coverage_report(self):
        """Generate coverage report."""
        try:
            self.logger.info("Generating coverage report...")

            # Run coverage combine and report
            cov = coverage.Coverage()
            cov.load()
            cov.report()

            # Generate HTML report
            cov.html_report(directory=str(self.reports_dir / "coverage_html"))

            self.logger.info("Coverage report generated")

        except Exception as e:
            self.logger.warning(f"Failed to generate coverage report: {e}")

    def _generate_junit_report(self, report: Dict[str, Any]):
        """Generate JUnit XML report for CI systems."""
        try:
            # This would generate a proper JUnit XML format
            # For now, just log that it would be generated
            self.logger.info("JUnit report generation would be implemented here")
        except Exception as e:
            self.logger.warning(f"Failed to generate JUnit report: {e}")

    def run_all_tests(self, test_types: List[str] = None, parallel: bool = False,
                     coverage_enabled: bool = True, ci_mode: bool = False,
                     framework: str = 'unified') -> Dict[str, Any]:
        """Run all tests using specified framework."""

        self.logger.info("=" * 70)
        self.logger.info("MAMCRAWLER UNIFIED TEST SUITE")
        self.logger.info("=" * 70)

        if test_types:
            self.logger.info(f"Test types: {', '.join(test_types)}")
        else:
            self.logger.info("Running all test types")

        self.logger.info(f"Parallel execution: {parallel}")
        self.logger.info(f"Coverage enabled: {coverage_enabled}")
        self.logger.info(f"CI mode: {ci_mode}")
        self.logger.info(f"Framework: {framework}")
        self.logger.info("")

        start_time = time.time()

        try:
            if framework == 'unified':
                report = self.run_unified_tests(test_types, parallel, coverage_enabled, ci_mode)
            elif framework == 'pytest':
                report = self.run_pytest_tests(test_types, parallel, coverage_enabled, ci_mode)
            else:
                raise ValueError(f"Unknown framework: {framework}")

            total_duration = time.time() - start_time

            # Print final summary
            self._print_final_summary(report, total_duration)

            return report

        except Exception as e:
            self.logger.error(f"Test execution failed: {e}")
            raise

    def _print_final_summary(self, report: Dict[str, Any], total_duration: float):
        """Print final test summary."""
        summary = report.get('summary', {})

        self.logger.info("\n" + "=" * 70)
        self.logger.info("TEST EXECUTION SUMMARY")
        self.logger.info("=" * 70)
        self.logger.info(f"Total Tests: {summary.get('total_tests', 0)}")
        self.logger.info(f"Passed: {summary.get('passed', 0)}")
        self.logger.info(f"Failed: {summary.get('failed', 0)}")
        self.logger.info(f"Skipped: {summary.get('skipped', 0)}")
        self.logger.info(f"Errors: {summary.get('errors', 0)}")
        self.logger.info(f"Success Rate: {summary.get('success_rate', 0):.1f}%")
        self.logger.info(f"Total Duration: {total_duration:.2f}s")
        self.logger.info("=" * 70)

        # Determine exit code
        failed = summary.get('failed', 0)
        errors = summary.get('errors', 0)

        if failed == 0 and errors == 0:
            self.logger.info("🎉 ALL TESTS PASSED!")
        else:
            self.logger.error(f"⚠️  {failed + errors} TESTS FAILED OR HAD ERRORS")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="MAMcrawler Unified Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_runner.py                          # Run all tests
  python test_runner.py --types unit integration # Run specific test types
  python test_runner.py --parallel               # Run tests in parallel
  python test_runner.py --coverage               # Generate coverage reports
  python test_runner.py --ci                     # CI mode with JUnit output
  python test_runner.py --framework pytest       # Use pytest instead of unified framework
        """
    )

    parser.add_argument(
        '--types', '-t',
        nargs='+',
        choices=['unit', 'integration', 'e2e', 'performance', 'api', 'database'],
        help='Test types to run (default: all)'
    )

    parser.add_argument(
        '--parallel', '-p',
        action='store_true',
        help='Run tests in parallel'
    )

    parser.add_argument(
        '--coverage', '-c',
        action='store_true',
        default=True,
        help='Generate coverage reports (default: enabled)'
    )

    parser.add_argument(
        '--no-coverage',
        action='store_true',
        help='Disable coverage reports'
    )

    parser.add_argument(
        '--ci',
        action='store_true',
        help='CI mode with JUnit XML output'
    )

    parser.add_argument(
        '--framework', '-f',
        choices=['unified', 'pytest'],
        default='unified',
        help='Test framework to use (default: unified)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create test runner
    runner = UnifiedTestRunner()

    try:
        # Run tests
        report = runner.run_all_tests(
            test_types=args.types,
            parallel=args.parallel,
            coverage_enabled=args.coverage and not args.no_coverage,
            ci_mode=args.ci,
            framework=args.framework
        )

        # Determine exit code
        summary = report.get('summary', {})
        failed = summary.get('failed', 0)
        errors = summary.get('errors', 0)

        sys.exit(0 if failed == 0 and errors == 0 else 1)

    except Exception as e:
        runner.logger.error(f"Test runner failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()