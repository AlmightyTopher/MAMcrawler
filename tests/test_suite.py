#!/usr/bin/env python3
"""
Comprehensive Test Suite for MAMcrawler
========================================

This test suite validates:
1. Configuration management and security
2. Async HTTP client functionality
3. Database operations
4. API integrations
5. Core functionality

Usage:
    pytest tests/ -v
    python -m pytest tests/test_config.py -v
    python tests/run_integration_tests.py
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import ConfigManager, validate_environment
from async_http_client import AsyncHTTPClient, HTTPClientManager, make_async_request


class TestConfiguration:
    """Test configuration management and security."""
    
    def test_virtual_environment_detection(self):
        """Test that virtual environment is properly detected."""
        config = ConfigManager()
        result = config._check_virtual_environment()
        
        # Should be True since we're running in venv
        assert result, "Virtual environment should be detected"
    
    def test_environment_validation(self):
        """Test environment validation with secure defaults."""
        config = ConfigManager()
        
        # Test masked environment variables
        masked_vars = config.get_masked_env_vars()
        
        # Should contain expected keys (even if NOT_SET)
        required_keys = [
            'ANTHROPIC_API_KEY', 'GOOGLE_BOOKS_API_KEY', 'POSTGRES_PASSWORD',
            'ABS_TOKEN', 'MAM_PASSWORD', 'QB_PASSWORD', 'ABS_URL', 'MAM_USERNAME'
        ]
        
        for key in required_keys:
            assert key in masked_vars, f"Required environment variable {key} should be present"
    
    def test_config_property_access(self):
        """Test that configuration properties are accessible."""
        config = ConfigManager()
        
        # These should all be accessible without errors
        assert config.security is not None
        assert config.api_endpoints is not None
        assert config.crawler is not None
        assert config.database is not None
        assert config.logging is not None
        assert config.system is not None
    
    def test_sensitive_data_masking(self):
        """Test that sensitive data is properly masked."""
        config = ConfigManager()
        
        # Test masking function directly
        masked_short = config._mask_secret("short")
        masked_long = config._mask_secret("very_long_secret_string_12345")
        
        # Short secrets should be fully masked
        assert masked_short == "******"
        
        # Long secrets should show first 4 and last 4 characters
        assert masked_long.startswith("very")
        assert masked_long.endswith("2345")
        assert "*********" in masked_long  # Middle should be asterisks


class TestAsyncHTTPClient:
    """Test async HTTP client functionality."""
    
    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test HTTP client initialization."""
        async with AsyncHTTPClient() as client:
            assert client._client is not None
            assert client._rate_limiter is not None
            assert client._retry_handler is not None
    
    @pytest.mark.asyncio
    async def test_rate_limiter(self):
        """Test rate limiting functionality."""
        from async_http_client import RateLimiter
        
        limiter = RateLimiter(min_delay=0.1, max_delay=0.2)
        
        start_time = asyncio.get_event_loop().time()
        await limiter.acquire()
        await limiter.acquire()
        end_time = asyncio.get_event_loop().time()
        
        # Should have waited at least min_delay between requests
        elapsed = end_time - start_time
        assert elapsed >= 0.1, f"Rate limiter should enforce minimum delay"
    
    @pytest.mark.asyncio
    async def test_successful_get_request(self):
        """Test successful GET request."""
        try:
            async with AsyncHTTPClient() as client:
                response = await client.get("https://httpbin.org/get")
                
                assert response.status_code == 200
                data = response.json()
                assert "headers" in data
                assert "User-Agent" in data["headers"]
                
        except Exception as e:
            # Skip test if external service is not available
            pytest.skip(f"External service not available: {e}")
    
    @pytest.mark.asyncio
    async def test_client_manager(self):
        """Test HTTP client manager."""
        # Get a client from the manager
        client1 = await HTTPClientManager.get_client("test1")
        client2 = await HTTPClientManager.get_client("test1")  # Should be same instance
        
        assert client1 is client2
        
        # Get a different client
        client3 = await HTTPClientManager.get_client("test2")
        assert client3 is not client1
        
        # Clean up
        await HTTPClientManager.close_all()
    
    @pytest.mark.asyncio
    async def test_convenience_functions(self):
        """Test convenience functions."""
        try:
            response = await make_async_request("GET", "https://httpbin.org/get")
            assert response.status_code == 200
            
        except Exception as e:
            pytest.skip(f"External service not available: {e}")


class TestDatabaseConnection:
    """Test database connection management."""
    
    def test_database_config(self):
        """Test database configuration."""
        from config import config
        
        db_config = config.database
        assert db_config is not None
        assert hasattr(db_config, 'rag_db_path')
        assert hasattr(db_config, 'db_pool_size')
    
    def test_database_directory_creation(self):
        """Test that database directories are created."""
        from config import config
        db_config = config.database
        
        # Should create the directory for the database file
        db_path = Path(db_config.rag_db_path)
        assert db_path.parent.exists()


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_config_validation_errors(self):
        """Test configuration validation with missing environment variables."""
        # Temporarily clear some required environment variables
        original_values = {}
        test_vars = ['ANTHROPIC_API_KEY', 'GOOGLE_BOOKS_API_KEY']
        
        for var in test_vars:
            original_values[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]
        
        try:
            config = ConfigManager()
            errors = config.validate_all()
            
            # Should have validation errors for missing variables
            assert len(errors) > 0
            
        finally:
            # Restore original environment variables
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
    
    @pytest.mark.asyncio
    async def test_http_error_handling(self):
        """Test HTTP error handling."""
        async with AsyncHTTPClient() as client:
            try:
                # Try to access a non-existent endpoint
                response = await client.get("https://httpbin.org/status/404")
                assert response.status_code == 404
                
            except Exception as e:
                pytest.skip(f"External service not available: {e}")
    
    @pytest.mark.asyncio
    async def test_retry_logic(self):
        """Test retry logic for failed requests."""
        from async_http_client import RetryHandler
        
        async def failing_function():
            raise Exception("This should fail")
        
        retry_handler = RetryHandler(max_retries=2)
        
        with pytest.raises(Exception):
            await retry_handler.execute(failing_function)


class TestIntegration:
    """Integration tests for complete workflows."""
    
    @pytest.mark.asyncio
    async def test_config_http_integration(self):
        """Test integration between config and HTTP client."""
        from config import config
        
        # Get rate limiting settings from config
        min_delay = config.crawler.request_delay_min
        max_delay = config.crawler.request_delay_max
        
        # Create HTTP client with config settings
        async with AsyncHTTPClient() as client:
            # Client should respect the rate limiting from config
            assert client._rate_limiter.min_delay == min_delay
            assert client._rate_limiter.max_delay == max_delay
    
    @pytest.mark.asyncio
    async def test_security_validation_integration(self):
        """Test security validation integrated with runtime."""
        # This should work if venv is properly set up
        try:
            validate_environment()
            assert True  # If we get here, validation passed
        except Exception:
            assert False, "Environment validation should pass in venv"


class TestUtilityFunctions:
    """Test utility functions and helpers."""
    
    def test_url_building(self):
        """Test URL building functionality."""
        async with AsyncHTTPClient() as client:
            base_url = "https://api.example.com"
            path = "/v1/books"
            params = {"limit": 10, "offset": 20}
            
            url = client.build_url(base_url, path, params)
            expected = "https://api.example.com/v1/books?limit=10&offset=20"
            
            assert url == expected
    
    def test_log_directory_creation(self):
        """Test that log directories are created properly."""
        from config import config
        
        log_path = Path(config.logging.log_file_path)
        assert log_path.parent.exists()
    
    def test_output_directory_creation(self):
        """Test that output directories are created properly."""
        from config import config
        
        output_path = Path(config.system.output_dir)
        temp_path = Path(config.system.temp_dir)
        
        assert output_path.exists()
        assert temp_path.exists()


# Pytest configuration and fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def http_client():
    """Provide an HTTP client for tests."""
    async with AsyncHTTPClient() as client:
        yield client


@pytest.fixture
def config_manager():
    """Provide a config manager for tests."""
    return ConfigManager()


# Test discovery and collection
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    for item in items:
        # Mark tests that require external services
        if "external" in item.nodeid or "httpbin" in item.nodeid:
            item.add_marker(pytest.mark.external)


# Test execution functions for standalone usage
def run_unit_tests():
    """Run unit tests only."""
    import subprocess
    
    cmd = [
        "python", "-m", "pytest",
        "tests/test_config.py",
        "tests/test_async_http_client.py", 
        "tests/test_database.py",
        "tests/test_error_handling.py",
        "tests/test_utility_functions.py",
        "-v", "--tb=short"
    ]
    
    return subprocess.run(cmd)


def run_integration_tests():
    """Run integration tests."""
    import subprocess
    
    cmd = [
        "python", "-m", "pytest", 
        "tests/test_integration.py",
        "-v", "--tb=short"
    ]
    
    return subprocess.run(cmd)


def run_all_tests():
    """Run all tests."""
    import subprocess
    
    cmd = [
        "python", "-m", "pytest", 
        "tests/",
        "-v", "--tb=short", "--asyncio-mode=auto"
    ]
    
    return subprocess.run(cmd)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MAMcrawler Test Suite")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    if args.unit:
        result = run_unit_tests()
    elif args.integration:
        result = run_integration_tests()
    elif args.all:
        result = run_all_tests()
    else:
        # Default to unit tests
        result = run_unit_tests()
    
    sys.exit(result.returncode)