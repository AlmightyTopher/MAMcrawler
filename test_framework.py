"""
Unified Testing Framework for MAMcrawler
========================================

Comprehensive testing system that consolidates all testing approaches into a single,
unified framework supporting:

- Unit tests for individual components
- Integration tests for system interactions
- End-to-end workflow tests
- API endpoint testing
- Performance and load testing
- Database testing with fixtures
- Mocking and stubbing for external services

Author: Agent 7 - Unified Testing Framework Specialist
"""

import asyncio
import json
import os
import sys
import time
import tempfile
import unittest
import shutil
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable, Type, TypeVar
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import logging
import subprocess
import psutil
import aiohttp
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Test type definitions
T = TypeVar('T')

@dataclass
class TestResult:
    """Standardized test result structure."""
    test_name: str
    test_type: str  # 'unit', 'integration', 'e2e', 'performance', 'api', 'database'
    status: str  # 'passed', 'failed', 'skipped', 'error'
    duration: float
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    coverage: Optional[float] = None
    artifacts: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class TestSuiteResult:
    """Result of a complete test suite execution."""
    suite_name: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float
    results: List[TestResult] = field(default_factory=list)
    coverage_report: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

class TestEnvironment:
    """Manages test environment setup and teardown."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path.cwd()
        self.temp_dirs: List[Path] = []
        self.mocks: List[Mock] = []
        self.patches: List[patch] = []

    @contextmanager
    def temp_directory(self, prefix: str = "test_"):
        """Create a temporary directory for testing."""
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
        self.temp_dirs.append(temp_dir)
        try:
            yield temp_dir
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            if temp_dir in self.temp_dirs:
                self.temp_dirs.remove(temp_dir)

    def create_mock(self, target: Any, **kwargs) -> Mock:
        """Create and track a mock object."""
        mock = Mock(**kwargs)
        self.mocks.append(mock)
        return mock

    def apply_patch(self, target: str, new: Any = None, **kwargs) -> patch:
        """Apply and track a patch."""
        p = patch(target, new, **kwargs)
        p.start()
        self.patches.append(p)
        return p

    def cleanup(self):
        """Clean up all test environment resources."""
        # Stop all patches
        for p in self.patches:
            try:
                p.stop()
            except RuntimeError:
                pass  # Already stopped

        # Clean up temp directories
        for temp_dir in self.temp_dirs[:]:  # Copy list to avoid modification during iteration
            try:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)
                self.temp_dirs.remove(temp_dir)
            except Exception:
                pass

        # Clear mocks
        self.mocks.clear()
        self.patches.clear()

class MockService:
    """Base class for service mocking."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.mock_objects: Dict[str, Mock] = {}

    def create_http_mock(self, url_pattern: str, response_data: Dict[str, Any],
                        status_code: int = 200) -> Mock:
        """Create HTTP response mock."""
        mock_response = self.create_mock('response')
        mock_response.status_code = status_code
        mock_response.json.return_value = response_data
        mock_response.text = json.dumps(response_data)
        mock_response.headers = {'Content-Type': 'application/json'}

        self.mock_objects[f'http_{url_pattern}'] = mock_response
        return mock_response

    def create_database_mock(self, table_name: str, data: List[Dict[str, Any]]) -> Mock:
        """Create database query mock."""
        mock_cursor = self.create_mock('cursor')
        mock_cursor.fetchall.return_value = data
        mock_cursor.fetchone.return_value = data[0] if data else None

        mock_connection = self.create_mock('connection')
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.execute = mock_cursor.execute

        self.mock_objects[f'db_{table_name}'] = mock_connection
        return mock_connection

    def create_mock(self, name: str, **kwargs) -> Mock:
        """Create a named mock object."""
        mock = Mock(**kwargs)
        self.mock_objects[name] = mock
        return mock

    def get_mock(self, name: str) -> Optional[Mock]:
        """Get a mock object by name."""
        return self.mock_objects.get(name)

class DatabaseTestFixture:
    """Database testing with fixtures."""

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url
        self.fixtures: Dict[str, List[Dict[str, Any]]] = {}
        self.test_db_name = f"test_{int(time.time())}"

    def load_fixture(self, fixture_name: str, fixture_data: List[Dict[str, Any]]):
        """Load test data fixture."""
        self.fixtures[fixture_name] = fixture_data

    def load_fixture_from_file(self, fixture_path: Path):
        """Load fixture from JSON file."""
        with open(fixture_path) as f:
            data = json.load(f)
            if isinstance(data, dict):
                for name, fixture_data in data.items():
                    self.load_fixture(name, fixture_data)
            else:
                self.load_fixture(fixture_path.stem, data)

    async def setup_test_database(self) -> str:
        """Create and populate test database."""
        # This would be implemented based on the actual database system
        # For now, return a mock connection string
        return f"sqlite:///{self.test_db_name}.db"

    async def teardown_test_database(self):
        """Clean up test database."""
        # Implementation would depend on database system
        pass

class PerformanceMonitor:
    """Monitor performance metrics during tests."""

    def __init__(self):
        self.start_time = None
        self.start_memory = None
        self.metrics: Dict[str, Any] = {}

    def start_monitoring(self):
        """Start performance monitoring."""
        self.start_time = time.time()
        self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.metrics = {}

    def record_metric(self, name: str, value: Any):
        """Record a performance metric."""
        self.metrics[name] = value

    def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring and return results."""
        if self.start_time is None:
            return {}

        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        results = {
            'duration': end_time - self.start_time,
            'memory_start_mb': self.start_memory,
            'memory_end_mb': end_memory,
            'memory_delta_mb': end_memory - self.start_memory,
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            **self.metrics
        }

        return results

class BaseTestCase(unittest.TestCase, ABC):
    """Base test case with unified testing utilities."""

    def setUp(self):
        """Set up test environment."""
        self.env = TestEnvironment()
        self.mock_service = MockService(self.__class__.__name__)
        self.db_fixture = DatabaseTestFixture()
        self.perf_monitor = PerformanceMonitor()
        self.test_artifacts: List[str] = []

    def tearDown(self):
        """Clean up test environment."""
        self.env.cleanup()

    def assertPerformance(self, operation: Callable, max_duration: float,
                         max_memory_mb: float = None):
        """Assert that an operation meets performance criteria."""
        self.perf_monitor.start_monitoring()

        start_time = time.time()
        result = operation()
        duration = time.time() - start_time

        metrics = self.perf_monitor.stop_monitoring()

        self.assertLess(duration, max_duration,
                       f"Operation took {duration:.2f}s, max allowed {max_duration}s")

        if max_memory_mb is not None:
            self.assertLess(metrics.get('memory_delta_mb', 0), max_memory_mb,
                           f"Memory usage {metrics.get('memory_delta_mb', 0):.2f}MB exceeded limit {max_memory_mb}MB")

        return result

    async def assertAsyncPerformance(self, operation: Callable, max_duration: float,
                                   max_memory_mb: float = None):
        """Assert that an async operation meets performance criteria."""
        self.perf_monitor.start_monitoring()

        start_time = time.time()
        result = await operation()
        duration = time.time() - start_time

        metrics = self.perf_monitor.stop_monitoring()

        self.assertLess(duration, max_duration,
                       f"Async operation took {duration:.2f}s, max allowed {max_duration}s")

        if max_memory_mb is not None:
            self.assertLess(metrics.get('memory_delta_mb', 0), max_memory_mb,
                           f"Memory usage {metrics.get('memory_delta_mb', 0):.2f}MB exceeded limit {max_memory_mb}MB")

        return result

class UnitTestCase(BaseTestCase):
    """Unit test case for individual component testing."""
    pass

class IntegrationTestCase(BaseTestCase):
    """Integration test case for component interaction testing."""
    pass

class E2ETestCase(BaseTestCase):
    """End-to-end test case for full workflow testing."""

    def setUp(self):
        super().setUp()
        # E2E tests may need real services, so we provide opt-in mocking
        self.use_real_services = os.getenv('E2E_USE_REAL_SERVICES', 'false').lower() == 'true'

class PerformanceTestCase(BaseTestCase):
    """Performance test case for load and stress testing."""

    def setUp(self):
        super().setUp()
        self.iterations = int(os.getenv('PERF_TEST_ITERATIONS', '100'))
        self.concurrency = int(os.getenv('PERF_TEST_CONCURRENCY', '10'))

class APITestCase(BaseTestCase):
    """API endpoint testing."""

    def setUp(self):
        super().setUp()
        self.base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
        self.session = requests.Session()

    def tearDown(self):
        super().tearDown()
        self.session.close()

    def api_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make an API request."""
        url = f"{self.base_url}{endpoint}"
        return self.session.request(method, url, **kwargs)

    def assertAPIResponse(self, response: requests.Response,
                         expected_status: int = 200,
                         expected_content_type: str = None):
        """Assert API response properties."""
        self.assertEqual(response.status_code, expected_status,
                        f"Expected status {expected_status}, got {response.status_code}")

        if expected_content_type:
            self.assertIn(expected_content_type, response.headers.get('Content-Type', ''),
                         f"Expected content type {expected_content_type}")

class DatabaseTestCase(BaseTestCase):
    """Database testing with fixtures."""

    def setUp(self):
        super().setUp()
        self.test_db_url = None

    async def asyncSetUp(self):
        """Async setup for database tests."""
        self.test_db_url = await self.db_fixture.setup_test_database()

    async def asyncTearDown(self):
        """Async teardown for database tests."""
        await self.db_fixture.teardown_test_database()

class TestRunner:
    """Unified test runner with discovery and execution."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path.cwd()
        self.test_suites: Dict[str, List[Type[BaseTestCase]]] = {}
        self.results: List[TestSuiteResult] = []
        self.logger = logging.getLogger(__name__)

    def discover_tests(self, test_dir: str = "tests") -> Dict[str, List[Type[BaseTestCase]]]:
        """Discover test classes in the test directory."""
        test_path = self.base_dir / test_dir
        if not test_path.exists():
            return {}

        # Import test modules and find test classes
        test_classes = {}

        for py_file in test_path.glob("**/*.py"):
            if py_file.name.startswith("test_"):
                module_name = f"tests.{py_file.relative_to(test_path).with_suffix('').as_posix().replace('/', '.')}"

                try:
                    # Import the module
                    if module_name in sys.modules:
                        module = sys.modules[module_name]
                    else:
                        module = __import__(module_name, fromlist=[module_name])

                    # Find test classes
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and
                            issubclass(attr, BaseTestCase) and
                            attr != BaseTestCase):

                            # Determine test type from class hierarchy
                            if issubclass(attr, UnitTestCase):
                                test_type = "unit"
                            elif issubclass(attr, IntegrationTestCase):
                                test_type = "integration"
                            elif issubclass(attr, E2ETestCase):
                                test_type = "e2e"
                            elif issubclass(attr, PerformanceTestCase):
                                test_type = "performance"
                            elif issubclass(attr, APITestCase):
                                test_type = "api"
                            elif issubclass(attr, DatabaseTestCase):
                                test_type = "database"
                            else:
                                test_type = "custom"

                            if test_type not in test_classes:
                                test_classes[test_type] = []
                            test_classes[test_type].append(attr)

                except Exception as e:
                    self.logger.warning(f"Failed to import {module_name}: {e}")

        self.test_suites = test_classes
        return test_classes

    def run_test_suite(self, suite_name: str, test_classes: List[Type[BaseTestCase]],
                      parallel: bool = False) -> TestSuiteResult:
        """Run a test suite."""
        start_time = time.time()
        results = []

        if parallel and len(test_classes) > 1:
            # Run tests in parallel
            with ThreadPoolExecutor(max_workers=min(len(test_classes), 4)) as executor:
                futures = []
                for test_class in test_classes:
                    future = executor.submit(self._run_test_class, test_class)
                    futures.append(future)

                for future in as_completed(futures):
                    results.extend(future.result())
        else:
            # Run tests sequentially
            for test_class in test_classes:
                results.extend(self._run_test_class(test_class))

        duration = time.time() - start_time

        # Calculate summary
        passed = sum(1 for r in results if r.status == 'passed')
        failed = sum(1 for r in results if r.status == 'failed')
        skipped = sum(1 for r in results if r.status == 'skipped')
        errors = sum(1 for r in results if r.status == 'error')

        return TestSuiteResult(
            suite_name=suite_name,
            total_tests=len(results),
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            duration=duration,
            results=results
        )

    def _run_test_class(self, test_class: Type[BaseTestCase]) -> List[TestResult]:
        """Run all tests in a test class."""
        results = []

        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)

        # Run tests and capture results
        for test in suite:
            start_time = time.time()

            try:
                # Set up test environment
                if hasattr(test, 'setUp'):
                    test.setUp()

                # Run the test
                result = unittest.TestResult()
                test.run(result)

                duration = time.time() - start_time

                if result.wasSuccessful():
                    status = 'passed'
                    error_message = None
                elif result.failures:
                    status = 'failed'
                    error_message = str(result.failures[0][1])
                elif result.errors:
                    status = 'error'
                    error_message = str(result.errors[0][1])
                else:
                    status = 'skipped'
                    error_message = None

                # Determine test type
                if issubclass(test_class, UnitTestCase):
                    test_type = 'unit'
                elif issubclass(test_class, IntegrationTestCase):
                    test_type = 'integration'
                elif issubclass(test_class, E2ETestCase):
                    test_type = 'e2e'
                elif issubclass(test_class, PerformanceTestCase):
                    test_type = 'performance'
                elif issubclass(test_class, APITestCase):
                    test_type = 'api'
                elif issubclass(test_class, DatabaseTestCase):
                    test_type = 'database'
                else:
                    test_type = 'custom'

                test_result = TestResult(
                    test_name=f"{test_class.__name__}.{test._testMethodName}",
                    test_type=test_type,
                    status=status,
                    duration=duration,
                    error_message=error_message
                )

                results.append(test_result)

            except Exception as e:
                duration = time.time() - start_time
                results.append(TestResult(
                    test_name=f"{test_class.__name__}.{test._testMethodName}",
                    test_type='unknown',
                    status='error',
                    duration=duration,
                    error_message=str(e)
                ))

            finally:
                # Clean up test environment
                if hasattr(test, 'tearDown'):
                    try:
                        test.tearDown()
                    except Exception:
                        pass  # Ignore cleanup errors

        return results

    def run_all_suites(self, parallel: bool = False) -> Dict[str, TestSuiteResult]:
        """Run all discovered test suites."""
        results = {}

        for suite_name, test_classes in self.test_suites.items():
            self.logger.info(f"Running {suite_name} test suite ({len(test_classes)} classes)")
            suite_result = self.run_test_suite(suite_name, test_classes, parallel)
            results[suite_name] = suite_result
            self.results.append(suite_result)

        return results

    def generate_report(self, output_dir: Path = None) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        if output_dir is None:
            output_dir = self.base_dir / "test_reports"
        output_dir.mkdir(exist_ok=True)

        # Aggregate all results
        total_tests = sum(r.total_tests for r in self.results)
        total_passed = sum(r.passed for r in self.results)
        total_failed = sum(r.failed for r in self.results)
        total_skipped = sum(r.skipped for r in self.results)
        total_errors = sum(r.errors for r in self.results)
        total_duration = sum(r.duration for r in self.results)

        report = {
            'summary': {
                'timestamp': datetime.now().isoformat(),
                'total_suites': len(self.results),
                'total_tests': total_tests,
                'passed': total_passed,
                'failed': total_failed,
                'skipped': total_skipped,
                'errors': total_errors,
                'success_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0,
                'total_duration': total_duration
            },
            'suite_results': [asdict(r) for r in self.results]
        }

        # Save JSON report
        json_path = output_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        # Generate HTML report
        html_path = output_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        self._generate_html_report(report, html_path)

        self.logger.info(f"Test reports generated: {json_path}, {html_path}")

        return report

    def _generate_html_report(self, report: Dict[str, Any], output_path: Path):
        """Generate HTML test report."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>MAMcrawler Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f0f0f0; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .suite {{ margin-bottom: 30px; border: 1px solid #ddd; padding: 15px; }}
        .passed {{ color: green; }}
        .failed {{ color: red; }}
        .skipped {{ color: orange; }}
        .error {{ color: darkred; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>MAMcrawler Unified Test Report</h1>
    <div class="summary">
        <h2>Test Summary</h2>
        <p><strong>Generated:</strong> {report['summary']['timestamp']}</p>
        <p><strong>Total Suites:</strong> {report['summary']['total_suites']}</p>
        <p><strong>Total Tests:</strong> {report['summary']['total_tests']}</p>
        <p><strong>Passed:</strong> <span class="passed">{report['summary']['passed']}</span></p>
        <p><strong>Failed:</strong> <span class="failed">{report['summary']['failed']}</span></p>
        <p><strong>Skipped:</strong> <span class="skipped">{report['summary']['skipped']}</span></p>
        <p><strong>Errors:</strong> <span class="error">{report['summary']['errors']}</span></p>
        <p><strong>Success Rate:</strong> {report['summary']['success_rate']:.1f}%</p>
        <p><strong>Total Duration:</strong> {report['summary']['total_duration']:.2f}s</p>
    </div>

    <h2>Test Suite Results</h2>
"""

        for suite in report['suite_results']:
            status_class = 'passed' if suite['failed'] == 0 and suite['errors'] == 0 else 'failed'
            html += f"""
    <div class="suite">
        <h3 class="{status_class}">{suite['suite_name']} Suite</h3>
        <p>Tests: {suite['total_tests']} | Passed: <span class="passed">{suite['passed']}</span> |
           Failed: <span class="failed">{suite['failed']}</span> |
           Skipped: <span class="skipped">{suite['skipped']}</span> |
           Errors: <span class="error">{suite['errors']}</span> |
           Duration: {suite['duration']:.2f}s</p>

        <table>
            <tr>
                <th>Test Name</th>
                <th>Type</th>
                <th>Status</th>
                <th>Duration</th>
                <th>Error</th>
            </tr>
"""

            for test in suite['results']:
                status_class = test['status']
                error = test.get('error_message', '')[:100] + '...' if test.get('error_message') and len(test.get('error_message', '')) > 100 else test.get('error_message', '')
                html += f"""
            <tr>
                <td>{test['test_name']}</td>
                <td>{test['test_type']}</td>
                <td class="{status_class}">{test['status']}</td>
                <td>{test['duration']:.2f}s</td>
                <td>{error}</td>
            </tr>
"""

            html += """
        </table>
    </div>
"""

        html += """
</body>
</html>
"""

        with open(output_path, 'w') as f:
            f.write(html)

# Global test runner instance
test_runner = TestRunner()

def run_tests(test_types: List[str] = None, parallel: bool = False,
              output_dir: Path = None) -> Dict[str, Any]:
    """
    Main entry point for running tests.

    Args:
        test_types: List of test types to run ('unit', 'integration', 'e2e', etc.)
        parallel: Whether to run tests in parallel
        output_dir: Directory to save test reports

    Returns:
        Test report dictionary
    """
    # Discover tests
    discovered = test_runner.discover_tests()

    if test_types:
        # Filter to requested test types
        test_runner.test_suites = {k: v for k, v in discovered.items() if k in test_types}
    else:
        test_runner.test_suites = discovered

    # Run tests
    results = test_runner.run_all_suites(parallel=parallel)

    # Generate report
    report = test_runner.generate_report(output_dir)

    return report

if __name__ == "__main__":
    # CLI interface
    import argparse

    parser = argparse.ArgumentParser(description="MAMcrawler Unified Test Framework")
    parser.add_argument('--types', nargs='+',
                       choices=['unit', 'integration', 'e2e', 'performance', 'api', 'database'],
                       help='Test types to run')
    parser.add_argument('--parallel', action='store_true',
                       help='Run tests in parallel')
    parser.add_argument('--output-dir', type=Path,
                       help='Output directory for reports')

    args = parser.parse_args()

    report = run_tests(
        test_types=args.types,
        parallel=args.parallel,
        output_dir=args.output_dir
    )

    # Print summary
    summary = report['summary']
    print("
=== Test Results ===")
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Skipped: {summary['skipped']}")
    print(f"Errors: {summary['errors']}")
    print(f"Success Rate: {summary['success_rate']:.1f}%")

    # Exit with appropriate code
    sys.exit(0 if summary['failed'] == 0 and summary['errors'] == 0 else 1)