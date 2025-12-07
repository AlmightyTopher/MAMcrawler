# MAMcrawler Unified Testing Framework

## Overview

The MAMcrawler project now uses a unified testing framework that consolidates all testing approaches into a single, comprehensive system. This framework supports unit tests, integration tests, end-to-end tests, performance tests, API tests, and database tests with fixtures.

## Quick Start

### Single Entry Point
Use `test_system.py` as the main entry point for all testing:

```bash
# Run all tests
python test_system.py

# Run specific test types
python test_system.py unit integration

# Run with parallel execution
python test_system.py --parallel

# Run with coverage reporting
python test_system.py --coverage

# CI mode with detailed reporting
python test_system.py --ci
```

### Alternative: Direct Runner
You can also use the test runner directly:

```bash
# Using unified framework
python test_runner.py --types unit integration --parallel

# Using pytest (for compatibility)
python test_runner.py --framework pytest --types unit
```

## Test Types

### 1. Unit Tests (`unit`)
Test individual components in isolation.

```python
from test_framework import UnitTestCase

class TestMyComponent(UnitTestCase):
    def test_my_function(self):
        result = my_function(42)
        self.assertEqual(result, 84)
```

### 2. Integration Tests (`integration`)
Test component interactions.

```python
from test_framework import IntegrationTestCase

class TestComponentInteraction(IntegrationTestCase):
    def test_components_work_together(self):
        component1 = Component1()
        component2 = Component2()
        result = component1.process(component2.get_data())
        self.assertIsNotNone(result)
```

### 3. End-to-End Tests (`e2e`)
Test complete workflows from start to finish.

```python
from test_framework import E2ETestCase

class TestFullWorkflow(E2ETestCase):
    def test_complete_user_journey(self):
        # Test real network calls and file I/O
        workflow = CompleteWorkflow()
        result = workflow.execute()
        self.assertTrue(result.success)
```

### 4. Performance Tests (`performance`)
Test performance and load handling.

```python
from test_framework import PerformanceTestCase

class TestPerformance(PerformanceTestCase):
    def test_operation_under_load(self):
        # Test must complete within 1 second
        result = self.assertPerformance(
            lambda: expensive_operation(),
            max_duration=1.0,
            max_memory_mb=100
        )
```

### 5. API Tests (`api`)
Test API endpoints.

```python
from test_framework import APITestCase

class TestAPIEndpoints(APITestCase):
    def test_get_books_endpoint(self):
        response = self.api_request('GET', '/api/books')
        self.assertAPIResponse(response, 200, 'application/json')
        self.assertIn('books', response.json())
```

### 6. Database Tests (`database`)
Test database operations with fixtures.

```python
from test_framework import DatabaseTestCase

class TestDatabaseOperations(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.db_fixture.load_fixture_from_file('test_fixtures/sample_books.json')

    async def asyncSetUp(self):
        await super().asyncSetUp()
        # Database is now populated with test data

    def test_query_books(self):
        books = self.db.query_books()
        self.assertGreater(len(books), 0)
```

## Test Organization

### Directory Structure
```
tests/
├── unit/
│   ├── test_quality_filter.py
│   ├── test_narrator_detector.py
│   └── ...
├── integration/
│   ├── test_crawler_integration.py
│   └── ...
├── e2e/
│   ├── test_full_workflow.py
│   └── ...
├── performance/
│   ├── test_load_handling.py
│   └── ...
├── api/
│   ├── test_endpoints.py
│   └── ...
└── database/
    ├── test_db_operations.py
    └── ...
```

### Test Fixtures
Test data is stored in `test_fixtures/`:

```json
// test_fixtures/sample_books.json
{
  "books": [
    {
      "id": "test_book_1",
      "title": "The Great Test Book",
      "author": "Test Author",
      // ... more fields
    }
  ]
}
```

### Test Reports
Generated reports are saved in `test_reports/`:
- JSON reports with detailed results
- HTML reports for easy viewing
- Coverage reports
- JUnit XML for CI systems

## Mocking and Stubbing

### HTTP Service Mocking
```python
mock_service = self.mock_service
mock_service.create_http_mock(
    '/api/books',
    {'books': [{'id': 1, 'title': 'Test Book'}]},
    200
)
```

### Database Mocking
```python
mock_db = self.mock_service.create_database_mock(
    'books_table',
    [{'id': 1, 'title': 'Test Book'}]
)
```

## Performance Assertions

```python
# Assert operation completes within time limit
result = self.assertPerformance(
    lambda: my_operation(),
    max_duration=2.0,  # seconds
    max_memory_mb=50   # MB
)

# Assert async operation
result = await self.assertAsyncPerformance(
    async_operation,
    max_duration=1.0,
    max_memory_mb=25
)
```

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run Tests
  run: python test_system.py --ci --coverage

- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./test_reports/coverage.json
```

### Jenkins Pipeline
```groovy
stage('Test') {
    steps {
        sh 'python test_system.py --ci --parallel'
        junit 'test_reports/junit_*.xml'
        publishHTML(target: [reportDir: 'test_reports', reportFiles: 'test_report_*.html'])
    }
}
```

## Configuration

### pytest.ini
The `pytest.ini` file contains all pytest configuration including:
- Test discovery patterns
- Markers for test types
- Coverage settings
- Logging configuration

### Environment Variables
- `E2E_USE_REAL_SERVICES`: Set to 'true' to use real services in E2E tests
- `PERF_TEST_ITERATIONS`: Number of iterations for performance tests
- `PERF_TEST_CONCURRENCY`: Concurrency level for performance tests
- `API_BASE_URL`: Base URL for API tests

## Best Practices

### 1. Test Isolation
Each test should be independent and not rely on other tests.

### 2. Use Appropriate Test Types
- **Unit tests**: Fast, isolated component testing
- **Integration tests**: Component interaction testing
- **E2E tests**: Full workflow validation (use sparingly)
- **Performance tests**: Load and performance validation

### 3. Fixture Usage
Use fixtures for test data to ensure consistency:

```python
def test_with_fixture(self):
    self.db_fixture.load_fixture('sample_books')
    # Test logic here
```

### 4. Mock External Dependencies
Always mock external services in unit and integration tests:

```python
def setUp(self):
    self.mock_service.create_http_mock('/api/external', {'status': 'ok'})
```

### 5. Performance Baselines
Set realistic performance expectations:

```python
# Good: Allow reasonable time for I/O operations
self.assertPerformance(operation, max_duration=5.0)

# Bad: Unrealistic expectations
self.assertPerformance(operation, max_duration=0.001)
```

## Migration from Old Frameworks

### Archiving Old Tests
Old testing frameworks have been moved to `archive/tests/`:
- `comprehensive_testing_framework.py` → `archive/tests/`
- `e2e_test_framework.py` → `archive/tests/`
- `test_suite.py` → `archive/tests/`

### Converting Tests
To convert old tests to the new framework:

1. **Identify test type** (unit, integration, e2e, etc.)
2. **Inherit from appropriate base class**
3. **Use new assertion methods**
4. **Add proper fixtures**

Example conversion:
```python
# Old
class TestOld(unittest.TestCase):
    def test_something(self):
        # test code

# New
from test_framework import UnitTestCase

class TestNew(UnitTestCase):
    def test_something(self):
        # test code with enhanced assertions
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `PYTHONPATH` includes project root
2. **Fixture Not Found**: Check `test_fixtures/` directory exists
3. **Coverage Not Working**: Install `pytest-cov` and `coverage`
4. **Parallel Tests Failing**: Check for shared state issues

### Debug Mode
Run with verbose logging:
```bash
python test_system.py --verbose
```

### Test Isolation
If tests interfere with each other, use:
```python
# In test class
def setUp(self):
    # Ensure clean state
    self.env.cleanup()
```

## Contributing

When adding new tests:

1. Follow the directory structure
2. Use appropriate base classes
3. Add comprehensive docstrings
4. Include fixtures for data-driven tests
5. Add performance assertions where relevant
6. Update this documentation

## Support

For questions about the testing framework:
- Check this documentation first
- Review existing test examples
- Run `python test_system.py --help` for CLI options
- Check test reports in `test_reports/` for failures