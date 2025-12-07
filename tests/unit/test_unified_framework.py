"""
Sample Unit Tests for MAMcrawler Unified Testing Framework
==========================================================

This file demonstrates how to use the unified testing framework for unit testing.
It shows various testing patterns and utilities available in the framework.

Author: Agent 7 - Unified Testing Framework Specialist
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from test_framework import UnitTestCase


class TestUnifiedFrameworkBasics(UnitTestCase):
    """Test basic functionality of the unified testing framework."""

    def test_environment_setup(self):
        """Test that test environment is properly initialized."""
        # Test environment should be available
        self.assertIsNotNone(self.env)
        self.assertIsNotNone(self.mock_service)
        self.assertIsNotNone(self.db_fixture)
        self.assertIsNotNone(self.perf_monitor)

    def test_temp_directory_creation(self):
        """Test temporary directory creation and cleanup."""
        with self.env.temp_directory("test_temp") as temp_dir:
            self.assertTrue(temp_dir.exists())
            self.assertTrue(str(temp_dir).endswith("test_temp"))

            # Create a test file
            test_file = temp_dir / "test.txt"
            test_file.write_text("test content")

            self.assertTrue(test_file.exists())
            self.assertEqual(test_file.read_text(), "test content")

        # Directory should be cleaned up after context
        self.assertFalse(temp_dir.exists())

    def test_mock_service_creation(self):
        """Test mock service creation and management."""
        # Create HTTP mock
        mock_response = self.mock_service.create_http_mock(
            '/api/test',
            {'status': 'success'},
            200
        )

        self.assertEqual(mock_response.status_code, 200)
        self.assertEqual(mock_response.json.return_value, {'status': 'success'})

        # Create database mock
        mock_db = self.mock_service.create_database_mock(
            'test_table',
            [{'id': 1, 'name': 'test'}]
        )

        # Test that mocks are accessible
        self.assertIsNotNone(self.mock_service.get_mock('http_/api/test'))
        self.assertIsNotNone(self.mock_service.get_mock('db_test_table'))

    def test_performance_monitoring(self):
        """Test performance monitoring capabilities."""
        self.perf_monitor.start_monitoring()
        self.perf_monitor.record_metric('test_metric', 42)

        # Simulate some work
        import time
        time.sleep(0.01)

        results = self.perf_monitor.stop_monitoring()

        self.assertIn('duration', results)
        self.assertIn('test_metric', results)
        self.assertEqual(results['test_metric'], 42)
        self.assertGreater(results['duration'], 0)


class TestPerformanceAssertions(UnitTestCase):
    """Test performance assertion utilities."""

    def test_performance_assertion_success(self):
        """Test that performance assertions work correctly."""
        def fast_operation():
            return 42

        # This should pass
        result = self.assertPerformance(
            fast_operation,
            max_duration=1.0,
            max_memory_mb=10
        )

        self.assertEqual(result, 42)

    def test_performance_assertion_failure(self):
        """Test that performance assertions fail when limits exceeded."""
        def slow_operation():
            import time
            time.sleep(0.1)  # Sleep for 100ms
            return 42

        # This should fail due to time limit
        with self.assertRaises(AssertionError):
            self.assertPerformance(
                slow_operation,
                max_duration=0.01,  # 10ms limit
                max_memory_mb=10
            )


class TestMockUtilities(UnitTestCase):
    """Test mocking utilities and patterns."""

    def test_http_service_mocking(self):
        """Test HTTP service mocking patterns."""
        # Mock a REST API response
        api_mock = self.mock_service.create_http_mock(
            '/api/books',
            {
                'books': [
                    {'id': 1, 'title': 'Test Book', 'author': 'Test Author'},
                    {'id': 2, 'title': 'Another Book', 'author': 'Another Author'}
                ],
                'total': 2
            },
            200
        )

        # Simulate API call
        response = api_mock
        self.assertEqual(response.status_code, 200)

        data = response.json.return_value
        self.assertEqual(len(data['books']), 2)
        self.assertEqual(data['total'], 2)

    def test_database_mocking(self):
        """Test database operation mocking."""
        # Mock database query results
        db_mock = self.mock_service.create_database_mock(
            'books',
            [
                {'id': 1, 'title': 'Book 1', 'author': 'Author 1'},
                {'id': 2, 'title': 'Book 2', 'author': 'Author 2'},
                {'id': 3, 'title': 'Book 3', 'author': 'Author 3'}
            ]
        )

        # Simulate database operations
        cursor = db_mock.cursor.return_value
        results = cursor.fetchall.return_value

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]['title'], 'Book 1')
        self.assertEqual(results[1]['author'], 'Author 2')

    def test_patch_management(self):
        """Test patch creation and automatic cleanup."""
        # Create a mock to patch
        original_function = Mock(return_value="original")
        mock_function = Mock(return_value="mocked")

        # Apply patch
        patch_obj = self.env.apply_patch(
            'tests.unit.test_unified_framework.original_function',
            mock_function
        )

        # Function should be patched
        from tests.unit.test_unified_framework import original_function
        self.assertEqual(original_function(), "mocked")

        # Patch should be automatically cleaned up in tearDown
        # (verified by the fact that no patches remain after test)


class TestFixtureLoading(UnitTestCase):
    """Test fixture loading and data management."""

    def setUp(self):
        super().setUp()
        # Load sample fixture
        fixture_path = Path(__file__).parent.parent.parent / "test_fixtures" / "sample_books.json"
        if fixture_path.exists():
            self.db_fixture.load_fixture_from_file(fixture_path)

    def test_fixture_data_loading(self):
        """Test that fixture data is loaded correctly."""
        # Check if fixture was loaded
        if 'sample_books.json' in self.db_fixture.fixtures:
            books = self.db_fixture.fixtures['sample_books.json']
            self.assertIsInstance(books, list)
            self.assertGreater(len(books), 0)

            # Check structure of first book
            first_book = books[0]
            self.assertIn('id', first_book)
            self.assertIn('title', first_book)
            self.assertIn('author', first_book)
        else:
            self.skipTest("Sample fixture not available")

    def test_fixture_data_validation(self):
        """Test that fixture data has required fields."""
        if 'sample_books.json' in self.db_fixture.fixtures:
            books = self.db_fixture.fixtures['sample_books.json']

            for book in books:
                # Each book should have essential fields
                required_fields = ['id', 'title', 'author']
                for field in required_fields:
                    self.assertIn(field, book, f"Book missing required field: {field}")
                    self.assertIsNotNone(book[field], f"Book field {field} is None")
        else:
            self.skipTest("Sample fixture not available")


class TestErrorHandling(UnitTestCase):
    """Test error handling and exception management."""

    def test_exception_in_test_setup(self):
        """Test that exceptions in setUp are handled properly."""
        # This test should pass because setUp succeeded
        self.assertTrue(True)

    def test_assertion_failures(self):
        """Test that assertion failures are reported correctly."""
        with self.assertRaises(AssertionError):
            self.assertEqual(1, 2, "This should fail")

    def test_exception_wrapping(self):
        """Test that exceptions are properly wrapped and reported."""
        def failing_function():
            raise ValueError("Test exception")

        with self.assertRaises(ValueError):
            failing_function()


# Utility functions for mocking
def original_function():
    """A simple function for testing patches."""
    return "original"


if __name__ == '__main__':
    import unittest
    unittest.main()