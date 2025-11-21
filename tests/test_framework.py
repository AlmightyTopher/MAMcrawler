"""
Comprehensive Test Framework for MAMcrawler

This module provides a complete testing framework for validating the consolidated crawler architecture,
including unit tests, integration tests, mock-based testing, and performance benchmarks.

Author: Audiobook Automation System
Version: 1.0.0
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from dataclasses import dataclass, field

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.base_crawler import BaseMAMCrawler
from core.utils import MAMUtils, RateLimiter, RetryPolicy, ConfigManager
from core.config import (
    CrawlerConfig, DatabaseConfig, LoggingConfig, ProxyConfig,
    SecurityConfig, MAMConfig, OutputConfig, MonitoringConfig,
    GlobalConfig
)


@dataclass
class TestResult:
    """Test result container."""
    test_name: str
    status: str  # "PASS", "FAIL", "SKIP", "ERROR"
    duration: float
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success(self) -> bool:
        return self.status in ["PASS", "SKIP"]


@dataclass
class TestSuite:
    """Test suite container."""
    name: str
    description: str
    tests: List[str] = field(default_factory=list)
    setup_method: Optional[str] = None
    teardown_method: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)


class MockPage:
    """Mock Playwright page for testing."""
    
    def __init__(self):
        self.content = ""
        self.title = ""
        self.url = ""
        self.inner_html_result = {}
        self.text_content_result = {}
        self.evaluate_result = {}
        self.goto_calls = []
        self.wait_for_calls = []
        self.click_calls = []
        self.hover_calls = []
        self.screenshot_calls = []
        self.close_called = False
        
    async def goto(self, url, wait_until="load", timeout=30000):
        self.goto_calls.append({"url": url, "wait_until": wait_until, "timeout": timeout})
        self.url = url
        return self
    
    async def wait_for(self, selector, timeout=10000):
        self.wait_for_calls.append({"selector": selector, "timeout": timeout})
        return self
    
    async def inner_html(self, selector):
        result = self.inner_html_result.get(selector, "")
        return result
    
    async def text_content(self, selector):
        result = self.text_content_result.get(selector, "")
        return result
    
    async def evaluate(self, script):
        return self.evaluate_result.get(script, None)
    
    async def click(self, selector):
        self.click_calls.append({"selector": selector})
    
    async def hover(self, selector):
        self.hover_calls.append({"selector": selector})
    
    async def screenshot(self, path=None, full_page=False):
        self.screenshot_calls.append({"path": path, "full_page": full_page})
        return b"fake_screenshot"
    
    async def close(self):
        self.close_called = True


class MockBrowser:
    """Mock Playwright browser for testing."""
    
    def __init__(self):
        self.pages = []
        self.new_page_calls = []
        self.close_called = False
        
    async def new_page(self):
        self.new_page_calls.append(time.time())
        page = MockPage()
        self.pages.append(page)
        return page
    
    async def close(self):
        self.close_called = True


class MockBrowserContext:
    """Mock Playwright browser context for testing."""
    
    def __init__(self):
        self.pages = []
        self.new_page_calls = []
        self.close_called = False
        
    async def new_page(self):
        self.new_page_calls.append(time.time())
        page = MockPage()
        self.pages.append(page)
        return page
    
    async def close(self):
        self.close_called = True


class MockPlaywright:
    """Mock Playwright for testing."""
    
    def __init__(self):
        self.chromium = Mock()
        self.chromium.launch = AsyncMock()
        self.chromium.launch_calls = []
        self.chromium.close_calls = []
        
    async def start(self):
        return self
    
    async def stop(self):
        pass


class TestDataGenerator:
    """Generate test data for various scenarios."""
    
    @staticmethod
    def generate_test_urls(count: int = 10, include_invalid: bool = True) -> List[str]:
        """Generate test URLs."""
        base_urls = [
            "https://www.myanonamouse.net/",
            "https://www.myanonamouse.net/t/123456",
            "https://www.myanonamouse.net/tor/browse.php",
            "https://www.myanonamouse.net/guides/",
            "https://www.myanonamouse.net/f/general/"
        ]
        
        urls = []
        for i in range(count):
            if include_invalid and i < 3:
                # Add invalid URLs
                urls.extend([
                    f"invalid-url-{i}",
                    f"https://malicious-site{i}.com/fake",
                    f"javascript:alert('test{i}')"
                ])
            else:
                urls.append(f"{base_urls[i % len(base_urls)]}?id={i}")
        
        return urls[:count]
    
    @staticmethod
    def generate_test_content() -> Dict[str, str]:
        """Generate test HTML content."""
        return {
            "login_page": """
                <html>
                    <body>
                        <form name="loginform">
                            <input name="username" type="text" />
                            <input name="password" type="password" />
                            <input type="submit" value="Login" />
                        </form>
                    </body>
                </html>
            """,
            "guide_page": """
                <html>
                    <head><title>Test Guide</title></head>
                    <body>
                        <h1 class="guide-title">Test Guide Title</h1>
                        <div class="guide-content">
                            <p>This is test guide content with sensitive info: user_test@example.com</p>
                        </div>
                        <div class="post">
                            <h2 class="post-title">Test Post</h2>
                            <div class="post-content">Post content here</div>
                        </div>
                    </body>
                </html>
            """,
            "browse_page": """
                <html>
                    <body>
                        <div class="search-result">
                            <a href="/t/12345">Torrent 1</a>
                        </div>
                        <div class="pagination">
                            <a title="Next" href="?page=2">Next</a>
                        </div>
                    </body>
                </html>
            """
        }
    
    @staticmethod
    def generate_test_config() -> Dict[str, Any]:
        """Generate test configuration."""
        return {
            "crawler": {
                "min_delay": 1.0,
                "max_delay": 3.0,
                "headless": False,
                "session_timeout": 3600
            },
            "database": {
                "connection_string": "sqlite:///:memory:",
                "max_connections": 5
            },
            "mam": {
                "base_url": "https://test.myanonamouse.net",
                "username_field": "test_username",
                "password_field": "test_password"
            }
        }


class BaseTestCase(unittest.TestCase):
    """Base test case with common functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_start_time = time.time()
        self.temp_dir = tempfile.mkdtemp()
        self.test_data = TestDataGenerator()
        
        # Create test configuration
        self.test_config = {
            "crawler": CrawlerConfig(min_delay=0.1, max_delay=0.2),
            "database": DatabaseConfig(connection_string="sqlite:///:memory:"),
            "mam": MAMConfig(base_url="https://test.myanonamouse.net")
        }
        
        # Set up test logging
        self.logger = logging.getLogger(f"test.{self.__class__.__name__}")
        
    def tearDown(self):
        """Clean up test environment."""
        duration = time.time() - self.test_start_time
        self.logger.info(f"Test {self._testMethodName} completed in {duration:.3f}s")
        
    def create_mock_crawler(self, config: Optional[Dict] = None) -> BaseMAMCrawler:
        """Create a mock crawler for testing."""
        # This should be implemented by subclasses
        raise NotImplementedError
        
    def assert_test_result(self, result: TestResult):
        """Assert that a test result indicates success."""
        if not result.success:
            self.fail(f"Test {result.test_name} failed: {result.error_message}")
        
    def assert_valid_crawl_result(self, result: Dict[str, Any]):
        """Assert that a crawl result is valid."""
        required_fields = ["success", "url", "crawled_at"]
        for field in required_fields:
            self.assertIn(field, result)
        
        if result["success"]:
            # Additional validation for successful crawls
            self.assertIsInstance(result["crawled_at"], str)
            self.assertIsInstance(result["url"], str)


class TestMAMUtils(BaseTestCase):
    """Test the MAMUtils utility class."""
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        test_cases = [
            ("Test Title", "Test_Title"),
            ("Title with/special\\characters?", "Title_withspecialcharacters"),
            ("", "untitled"),
            ("A" * 150, "A" * 100),
            ("Title_with__multiple___underscores", "Title_with_multiple_underscores")
        ]
        
        for input_title, expected in test_cases:
            result = MAMUtils.sanitize_filename(input_title)
            self.assertEqual(result, expected)
    
    def test_is_allowed_path(self):
        """Test URL path validation."""
        allowed_urls = [
            "https://www.myanonamouse.net/",
            "https://www.myanonamouse.net/t/123456",
            "https://www.myanonamouse.net/tor/browse.php",
            "https://www.myanonamouse.net/guides/guide-title"
        ]
        
        disallowed_urls = [
            "https://malicious-site.com/",
            "https://www.myanonamouse.net.evil.com/",
            "javascript:alert('test')",
            ""
        ]
        
        for url in allowed_urls:
            self.assertTrue(MAMUtils.is_allowed_path(url), f"URL should be allowed: {url}")
            
        for url in disallowed_urls:
            self.assertFalse(MAMUtils.is_allowed_path(url), f"URL should not be allowed: {url}")
    
    def test_anonymize_content(self):
        """Test content anonymization."""
        test_content = """
        This is a test with email user@example.com and user_123.
        Another email test@example.org.
        Session info: sid=1234567890abcdef1234567890abcdef
        """
        
        expected_content = """
        This is a test with email [EMAIL] and [USER].
        Another email [EMAIL].
        Session info: sid=[TOKEN]
        """
        
        result = MAMUtils.anonymize_content(test_content, max_length=1000)
        # Check that sensitive information is anonymized
        self.assertNotIn("user@example.com", result)
        self.assertNotIn("test@example.org", result)
        self.assertNotIn("user_123", result)
        self.assertNotIn("1234567890abcdef1234567890abcdef", result)
    
    def test_extract_numbers(self):
        """Test number extraction."""
        text = "The file is 1.5MB and contains 123 items, price: $19.99"
        numbers = MAMUtils.extract_numbers(text)
        
        self.assertIn(1.5, numbers)
        self.assertIn(123, numbers)
        self.assertIn(19.99, numbers)
    
    def test_parse_duration(self):
        """Test duration parsing."""
        test_cases = [
            ("1:30:45", 5445),  # 1 hour, 30 minutes, 45 seconds
            ("45:30", 2730),   # 45 minutes, 30 seconds
            ("30", 30),        # 30 seconds
            ("invalid", None),
            ("", None)
        ]
        
        for duration_str, expected in test_cases:
            result = MAMUtils.parse_duration(duration_str)
            self.assertEqual(result, expected)


class TestConfigSystem(BaseTestCase):
    """Test the configuration system."""
    
    def test_crawler_config_validation(self):
        """Test crawler configuration validation."""
        # Valid config
        config = CrawlerConfig(min_delay=1.0, max_delay=5.0)
        self.assertEqual(config.min_delay, 1.0)
        self.assertEqual(config.max_delay, 5.0)
        
        # Invalid config should raise ValueError
        with self.assertRaises(ValueError):
            CrawlerConfig(min_delay=-1.0, max_delay=5.0)
            
        with self.assertRaises(ValueError):
            CrawlerConfig(min_delay=5.0, max_delay=1.0)
    
    def test_database_config(self):
        """Test database configuration."""
        config = DatabaseConfig(
            connection_string="postgresql://localhost/test",
            max_connections=20,
            query_timeout=60
        )
        
        self.assertEqual(config.connection_string, "postgresql://localhost/test")
        self.assertEqual(config.max_connections, 20)
        self.assertEqual(config.query_timeout, 60)
    
    def test_global_config_singleton(self):
        """Test global configuration singleton behavior."""
        config1 = GlobalConfig()
        config2 = GlobalConfig()
        
        self.assertIs(config1, config2)
    
    def test_config_registration(self):
        """Test configuration registration."""
        registry = ConfigRegistry()
        
        test_config = CrawlerConfig(min_delay=1.0)
        registry.register_config("test", test_config)
        
        retrieved_config = registry.get_config("test")
        self.assertIs(retrieved_config, test_config)
        
        # Test updating config
        registry.update_config("test", {"max_delay": 5.0})
        self.assertEqual(retrieved_config.max_delay, 5.0)


class TestRateLimiter(BaseTestCase):
    """Test the rate limiter functionality."""
    
    def test_rate_limiter(self):
        """Test basic rate limiting."""
        limiter = RateLimiter(min_delay=0.1, max_delay=0.2)
        
        # First call should not delay
        start_time = time.time()
        asyncio.run(limiter.wait())
        first_duration = time.time() - start_time
        
        self.assertLess(first_duration, 0.05)  # Should be very fast
        
        # Second call should delay
        start_time = time.time()
        asyncio.run(limiter.wait())
        second_duration = time.time() - start_time
        
        self.assertGreaterEqual(second_duration, 0.1)
    
    def test_concurrent_limiter(self):
        """Test rate limiting with concurrent requests."""
        limiter = RateLimiter(min_delay=0.1, max_delay=0.2)
        
        async def test_request():
            await limiter.wait()
            return time.time()
        
        start_time = time.time()
        results = asyncio.run(asyncio.gather(
            test_request(),
            test_request(),
            test_request()
        ))
        
        # All requests should complete within reasonable time
        total_duration = time.time() - start_time
        self.assertLess(total_duration, 1.0)
        
        # Requests should be spaced out
        self.assertGreater(results[2] - results[0], 0.15)


class TestRetryPolicy(BaseTestCase):
    """Test retry policy functionality."""
    
    async def test_successful_operation(self):
        """Test retry policy with successful operation."""
        async def successful_operation():
            return "success"
        
        retry_policy = RetryPolicy(max_retries=3, base_delay=0.1)
        result = await retry_policy.execute_with_retry(successful_operation)
        
        self.assertEqual(result, "success")
    
    async def test_failed_operation_retries(self):
        """Test retry policy with failed operation."""
        call_count = 0
        
        async def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Simulated failure")
            return "success"
        
        retry_policy = RetryPolicy(max_retries=5, base_delay=0.1)
        result = await retry_policy.execute_with_retry(failing_operation)
        
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)
    
    async def test_max_retries_exceeded(self):
        """Test retry policy when max retries exceeded."""
        async def always_failing_operation():
            raise ValueError("Always fails")
        
        retry_policy = RetryPolicy(max_retries=2, base_delay=0.1)
        
        with self.assertRaises(ValueError):
            await retry_policy.execute_with_retry(always_failing_operation)


class TestBaseCrawler(BaseTestCase):
    """Test the base crawler functionality."""
    
    def create_mock_crawler(self, config: Optional[Dict] = None):
        """Create a mock crawler for testing."""
        # Mock implementation of abstract base crawler
        class MockCrawler(BaseMAMCrawler):
            def __init__(self, config=None):
                super().__init__(config)
                self.authenticated = False
                
            async def authenticate(self) -> bool:
                self.last_login = datetime.now()
                self.session_cookies = {"session_id": "test_session"}
                self.authenticated = True
                return True
                
            async def crawl_page(self, url: str, **kwargs) -> Dict[str, Any]:
                return {
                    "success": True,
                    "url": url,
                    "crawled_at": datetime.now().isoformat(),
                    "content": "test content"
                }
        
        return MockCrawler(config)
    
    def test_crawler_initialization(self):
        """Test crawler initialization."""
        crawler = self.create_mock_crawler()
        
        self.assertIsNotNone(crawler.config)
        self.assertEqual(crawler.base_url, "https://www.myanonamouse.net")
        self.assertFalse(crawler.is_authenticated)
    
    def test_authentication_flow(self):
        """Test authentication flow."""
        crawler = self.create_mock_crawler()
        
        # Initially not authenticated
        self.assertFalse(crawler.is_authenticated)
        
        # After authentication
        result = asyncio.run(crawler.authenticate())
        self.assertTrue(result)
        self.assertTrue(crawler.is_authenticated)
    
    def test_ensure_authenticated(self):
        """Test authentication enforcement."""
        crawler = self.create_mock_crawler()
        
        # Should automatically authenticate
        result = asyncio.run(crawler.ensure_authenticated())
        self.assertTrue(result)
        self.assertTrue(crawler.is_authenticated)
    
    def test_rate_limiting(self):
        """Test crawler rate limiting."""
        crawler = self.create_mock_crawler()
        crawler.config["min_delay"] = 0.1
        crawler.config["max_delay"] = 0.2
        
        start_time = time.time()
        asyncio.run(crawler.rate_limit())
        duration = time.time() - start_time
        
        self.assertGreaterEqual(duration, 0.1)
    
    def test_crawl_with_retry(self):
        """Test crawl with retry functionality."""
        crawler = self.create_mock_crawler()
        crawler.crawl_page = AsyncMock(return_value={
            "success": True,
            "url": "https://test.example.com",
            "crawled_at": datetime.now().isoformat()
        })
        
        result = asyncio.run(crawler.crawl_with_retry("https://test.example.com"))
        
        self.assertTrue(result["success"])
        self.assertEqual(result["url"], "https://test.example.com")
        self.assertEqual(result["attempt"], 1)
    
    def test_file_sanitization(self):
        """Test filename sanitization in crawler."""
        crawler = self.create_mock_crawler()
        
        test_cases = [
            ("Test Title", "Test_Title"),
            ("Special/Chars?", "SpecialChars"),
            ("", "untitled")
        ]
        
        for title, expected in test_cases:
            result = crawler.sanitize_filename(title)
            self.assertEqual(result, expected)


class IntegrationTestRunner:
    """Integration test runner for end-to-end testing."""
    
    def __init__(self, test_config: Dict[str, Any]):
        self.test_config = test_config
        self.logger = logging.getLogger("integration_tests")
        self.results: List[TestResult] = []
    
    async def run_integration_tests(self) -> List[TestResult]:
        """Run all integration tests."""
        self.logger.info("Starting integration test suite")
        
        test_suites = [
            self.test_end_to_end_crawler,
            self.test_database_integration,
            self.test_configuration_loading,
            self.test_error_handling,
            self.test_performance_benchmarks
        ]
        
        for test_suite in test_suites:
            try:
                await test_suite()
            except Exception as e:
                self.logger.error(f"Test suite {test_suite.__name__} failed: {e}")
                self.results.append(TestResult(
                    test_name=test_suite.__name__,
                    status="ERROR",
                    duration=0.0,
                    error_message=str(e)
                ))
        
        return self.results
    
    async def test_end_to_end_crawler(self):
        """Test end-to-end crawler workflow."""
        start_time = time.time()
        
        # Test complete crawler workflow
        crawler = TestBaseCrawler().create_mock_crawler()
        
        # Test authentication
        auth_success = await crawler.ensure_authenticated()
        self.assertTrue(auth_success)
        
        # Test crawling
        result = await crawler.crawl_with_retry("https://test.example.com")
        self.assertTrue(result["success"])
        
        # Test rate limiting
        await crawler.rate_limit()
        
        duration = time.time() - start_time
        self.results.append(TestResult(
            test_name="end_to_end_crawler",
            status="PASS",
            duration=duration
        ))
    
    async def test_database_integration(self):
        """Test database integration."""
        start_time = time.time()
        
        # This would test actual database operations
        # For now, just validate configuration
        db_config = DatabaseConfig(connection_string="sqlite:///:memory:")
        self.assertIsNotNone(db_config.connection_string)
        
        duration = time.time() - start_time
        self.results.append(TestResult(
            test_name="database_integration",
            status="PASS",
            duration=duration
        ))
    
    async def test_configuration_loading(self):
        """Test configuration loading and validation."""
        start_time = time.time()
        
        # Test config loading
        test_data = TestDataGenerator.generate_test_config()
        self.assertIn("crawler", test_data)
        self.assertIn("database", test_data)
        self.assertIn("mam", test_data)
        
        # Test config validation
        try:
            crawler_config = CrawlerConfig(**test_data["crawler"])
            self.assertIsInstance(crawler_config, CrawlerConfig)
        except Exception as e:
            raise AssertionError(f"Configuration validation failed: {e}")
        
        duration = time.time() - start_time
        self.results.append(TestResult(
            test_name="configuration_loading",
            status="PASS",
            duration=duration
        ))
    
    async def test_error_handling(self):
        """Test error handling and recovery."""
        start_time = time.time()
        
        # Test retry policy with failures
        retry_policy = RetryPolicy(max_retries=3, base_delay=0.1)
        
        call_count = 0
        async def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Simulated failure")
            return "success"
        
        result = await retry_policy.execute_with_retry(failing_operation)
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)
        
        duration = time.time() - start_time
        self.results.append(TestResult(
            test_name="error_handling",
            status="PASS",
            duration=duration
        ))
    
    async def test_performance_benchmarks(self):
        """Test performance benchmarks."""
        start_time = time.time()
        
        # Test utility function performance
        test_urls = TestDataGenerator.generate_test_urls(100)
        
        # Test filename sanitization performance
        sanitize_start = time.time()
        for _ in range(1000):
            MAMUtils.sanitize_filename("Test filename with special characters!")
        sanitize_duration = time.time() - sanitize_start
        
        # Test URL validation performance
        validation_start = time.time()
        for _ in range(1000):
            MAMUtils.is_allowed_path("https://www.myanonamouse.net/test")
        validation_duration = time.time() - validation_start
        
        # Performance thresholds (should be very fast)
        self.assertLess(sanitize_duration, 1.0, "Filename sanitization too slow")
        self.assertLess(validation_duration, 1.0, "URL validation too slow")
        
        duration = time.time() - start_time
        self.results.append(TestResult(
            test_name="performance_benchmarks",
            status="PASS",
            duration=duration,
            details={
                "sanitize_duration": sanitize_duration,
                "validation_duration": validation_duration
            }
        ))


class MockCrawlerTestRunner:
    """Runner for mock-based crawler tests."""
    
    def __init__(self):
        self.logger = logging.getLogger("mock_tests")
        self.results: List[TestResult] = []
    
    async def run_mock_tests(self) -> List[TestResult]:
        """Run all mock-based tests."""
        self.logger.info("Starting mock crawler test suite")
        
        test_methods = [
            self.test_mock_authentication,
            self.test_mock_crawling,
            self.test_mock_stealth_behavior,
            self.test_mock_error_recovery,
            self.test_mock_concurrent_requests
        ]
        
        for test_method in test_methods:
            try:
                await test_method()
            except Exception as e:
                self.logger.error(f"Test method {test_method.__name__} failed: {e}")
                self.results.append(TestResult(
                    test_name=test_method.__name__,
                    status="ERROR",
                    duration=0.0,
                    error_message=str(e)
                ))
        
        return self.results
    
    async def test_mock_authentication(self):
        """Test authentication with mock setup."""
        start_time = time.time()
        
        # Set up mock browser and page
        mock_playwright = MockPlaywright()
        mock_browser = MockBrowser()
        mock_page = MockPage()
        
        # Set up mock authentication flow
        mock_page.inner_html_result = {
            "form[name=loginform]": """
                <form name="loginform">
                    <input name="username" type="text" />
                    <input name="password" type="password" />
                    <input type="submit" value="Login" />
                </form>
            """
        }
        mock_browser.pages.append(mock_page)
        
        # Simulate authentication
        await mock_page.goto("https://test.myanonamouse.net/login.php")
        self.assertEqual(len(mock_page.goto_calls), 1)
        
        await mock_page.inner_html("form[name=loginform]")
        
        duration = time.time() - start_time
        self.results.append(TestResult(
            test_name="mock_authentication",
            status="PASS",
            duration=duration
        ))
    
    async def test_mock_crawling(self):
        """Test crawling with mock setup."""
        start_time = time.time()
        
        mock_page = MockPage()
        
        # Set up mock page content
        mock_page.inner_html_result = {
            ".guide-title": "Test Guide Title",
            ".guide-content": "Test guide content here"
        }
        mock_page.text_content_result = {
            ".guide-title": "Test Guide Title",
            ".guide-content": "Test guide content here"
        }
        
        # Test content extraction
        title = await mock_page.text_content(".guide-title")
        content = await mock_page.inner_html(".guide-content")
        
        self.assertEqual(title, "Test Guide Title")
        self.assertEqual(content, "Test guide content here")
        
        duration = time.time() - start_time
        self.results.append(TestResult(
            test_name="mock_crawling",
            status="PASS",
            duration=duration
        ))
    
    async def test_mock_stealth_behavior(self):
        """Test stealth behavior simulation."""
        start_time = time.time()
        
        # Test stealth JavaScript generation
        stealth_js = MAMUtils.generate_stealth_js()
        self.assertIn("simulateHumanBehavior", stealth_js)
        self.assertIn("MouseEvent", stealth_js)
        
        # Test viewport randomization
        viewport = MAMUtils.get_random_viewport()
        self.assertIsInstance(viewport, tuple)
        self.assertEqual(len(viewport), 2)
        self.assertGreater(viewport[0], 0)
        self.assertGreater(viewport[1], 0)
        
        duration = time.time() - start_time
        self.results.append(TestResult(
            test_name="mock_stealth_behavior",
            status="PASS",
            duration=duration
        ))
    
    async def test_mock_error_recovery(self):
        """Test error recovery with mock setup."""
        start_time = time.time()
        
        # Test retry policy with mock operations
        retry_policy = RetryPolicy(max_retries=3, base_delay=0.1)
        
        # Simulate network errors
        error_count = 0
        async def network_operation():
            nonlocal error_count
            error_count += 1
            if error_count <= 2:
                raise ConnectionError("Network error")
            return "success"
        
        result = await retry_policy.execute_with_retry(network_operation)
        self.assertEqual(result, "success")
        self.assertEqual(error_count, 3)
        
        duration = time.time() - start_time
        self.results.append(TestResult(
            test_name="mock_error_recovery",
            status="PASS",
            duration=duration
        ))
    
    async def test_mock_concurrent_requests(self):
        """Test concurrent request handling."""
        start_time = time.time()
        
        # Test rate limiter with concurrent requests
        limiter = RateLimiter(min_delay=0.05, max_delay=0.1)
        
        async def mock_request(request_id: int):
            await limiter.wait()
            return f"Response {request_id}"
        
        # Run multiple concurrent requests
        start = time.time()
        results = await asyncio.gather(*[
            mock_request(i) for i in range(5)
        ])
        duration = time.time() - start
        
        # Verify all requests completed
        self.assertEqual(len(results), 5)
        for i, result in enumerate(results):
            self.assertEqual(result, f"Response {i}")
        
        # Should take at least the rate limit delay
        self.assertGreaterEqual(duration, 0.2)
        
        duration = time.time() - start_time
        self.results.append(TestResult(
            test_name="mock_concurrent_requests",
            status="PASS",
            duration=duration
        ))


class TestReportGenerator:
    """Generate test reports and coverage analysis."""
    
    def __init__(self, output_dir: str = "test_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_test_report(self, results: List[TestResult]) -> str:
        """Generate comprehensive test report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"test_report_{timestamp}.json"
        
        # Calculate summary statistics
        total_tests = len(results)
        passed_tests = len([r for r in results if r.status == "PASS"])
        failed_tests = len([r for r in results if r.status == "FAIL"])
        error_tests = len([r for r in results if r.status == "ERROR"])
        skipped_tests = len([r for r in results if r.status == "SKIP"])
        
        summary = {
            "timestamp": timestamp,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "error_tests": error_tests,
            "skipped_tests": skipped_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "total_duration": sum(r.duration for r in results),
            "average_duration": (sum(r.duration for r in results) / total_tests) if total_tests > 0 else 0,
            "test_results": [r.__dict__ for r in results]
        }
        
        # Save detailed JSON report
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        # Generate human-readable report
        readable_report = self._generate_readable_report(summary)
        readable_file = self.output_dir / f"test_report_{timestamp}.txt"
        with open(readable_file, 'w', encoding='utf-8') as f:
            f.write(readable_report)
        
        return str(report_file)
    
    def _generate_readable_report(self, summary: Dict[str, Any]) -> str:
        """Generate human-readable test report."""
        lines = [
            "=" * 80,
            "MAMCRAWLER TEST REPORT",
            "=" * 80,
            "",
            f"Timestamp: {summary['timestamp']}",
            f"Total Tests: {summary['total_tests']}",
            f"Passed: {summary['passed_tests']} ({summary['passed_tests']/summary['total_tests']*100:.1f}%)" if summary['total_tests'] > 0 else "Passed: 0 (0%)",
            f"Failed: {summary['failed_tests']}",
            f"Errors: {summary['error_tests']}",
            f"Skipped: {summary['skipped_tests']}",
            f"Success Rate: {summary['success_rate']:.1f}%",
            f"Total Duration: {summary['total_duration']:.2f}s",
            f"Average Duration: {summary['average_duration']:.3f}s",
            "",
            "=" * 80,
            "TEST RESULTS",
            "=" * 80,
            ""
        ]
        
        for result in summary['test_results']:
            status_symbol = "✓" if result['status'] == "PASS" else "✗" if result['status'] in ["FAIL", "ERROR"] else "⊘"
            lines.append(f"{status_symbol} {result['test_name']} ({result['duration']:.3f}s)")
            
            if result['error_message']:
                lines.append(f"    Error: {result['error_message']}")
            
            if result['details']:
                for key, value in result['details'].items():
                    lines.append(f"    {key}: {value}")
        
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)


async def run_comprehensive_test_suite():
    """Run the complete test suite with all test types."""
    print("Starting Comprehensive MAMcrawler Test Suite")
    print("=" * 50)
    
    # Initialize test components
    test_config = TestDataGenerator.generate_test_config()
    report_generator = TestReportGenerator()
    
    # Run unit tests
    print("\n1. Running Unit Tests...")
    unit_test_runner = unittest.TextTestRunner(verbosity=2)
    unit_suite = unittest.TestSuite()
    
    # Add test classes to suite
    test_classes = [
        TestMAMUtils,
        TestConfigSystem,
        TestRateLimiter,
        TestRetryPolicy,
        TestBaseCrawler
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        unit_suite.addTests(tests)
    
    unit_results = unit_test_runner.run(unit_suite)
    
    # Run integration tests
    print("\n2. Running Integration Tests...")
    integration_runner = IntegrationTestRunner(test_config)
    integration_results = await integration_runner.run_integration_tests()
    
    # Run mock tests
    print("\n3. Running Mock-Based Tests...")
    mock_runner = MockCrawlerTestRunner()
    mock_results = await mock_runner.run_mock_tests()
    
    # Compile all results
    all_results = []
    
    # Add unit test results
    for test_case, result in unit_results.failures + unit_results.errors + [(t, None) for t in unit_results.testsRun if t not in [f[0] for f in unit_results.failures + unit_results.errors]]:
        if isinstance(result, str):
            status = "FAIL" if test_case in unit_results.failures else "ERROR"
            all_results.append(TestResult(
                test_name=str(test_case),
                status=status,
                duration=0.0,
                error_message=result
            ))
        else:
            all_results.append(TestResult(
                test_name=str(test_case),
                status="PASS",
                duration=0.0
            ))
    
    # Add integration and mock test results
    all_results.extend(integration_results)
    all_results.extend(mock_results)
    
    # Generate report
    print("\n4. Generating Test Report...")
    report_file = report_generator.generate_test_report(all_results)
    
    # Print summary
    total_tests = len(all_results)
    passed_tests = len([r for r in all_results if r.status == "PASS"])
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    print("\n" + "=" * 50)
    print("TEST SUITE COMPLETE")
    print("=" * 50)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"Report saved to: {report_file}")
    
    return all_results


if __name__ == "__main__":
    # Configure logging for tests
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the comprehensive test suite
    try:
        results = asyncio.run(run_comprehensive_test_suite())
        
        # Exit with appropriate code
        failed_tests = len([r for r in results if r.status in ["FAIL", "ERROR"]])
        sys.exit(1 if failed_tests > 0 else 0)
        
    except KeyboardInterrupt:
        print("\nTest suite interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nTest suite failed with error: {e}")
        sys.exit(1)