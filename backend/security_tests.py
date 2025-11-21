"""
Security Testing Module for MAMcrawler API

This module provides utilities for testing and verifying the security measures
implemented in the MAMcrawler API, including:
- Authentication testing
- Authorization verification
- CORS policy validation
- Security header verification
- Input sanitization testing
- Rate limiting verification
- SQL injection testing
- XSS prevention testing

Author: Audiobook Automation System
Version: 1.0.0
"""

import os
import json
import time
import logging
import secrets
import sys
from typing import Dict, List, Optional, Union, Any, Tuple
from urllib.parse import urljoin

import requests
from requests.auth import HTTPBasicAuth

# Configure logging
logger = logging.getLogger(__name__)

class SecurityTester:
    """Class for testing security measures in the MAMcrawler API"""
    
    def __init__(self, base_url: str, api_key: str = None, username: str = None, password: str = None):
        """
        Initialize the SecurityTester
        
        Args:
            base_url: Base URL of the API
            api_key: API key for authentication
            username: Username for basic authentication
            password: Password for basic authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key or os.getenv("API_KEY")
        self.username = username
        self.password = password
        self.auth = HTTPBasicAuth(username, password) if username and password else None
        
        # Test results
        self.results = {
            "authentication": [],
            "authorization": [],
            "cors": [],
            "security_headers": [],
            "input_sanitization": [],
            "rate_limiting": [],
            "sql_injection": [],
            "xss_prevention": []
        }
    
    def test_api_key_authentication(self) -> bool:
        """
        Test API key authentication
        
        Returns:
            True if authentication tests pass, False otherwise
        """
        test_results = []
        logger.info("Testing API key authentication...")
        
        # Test with valid API key
        if self.api_key:
            try:
                url = urljoin(self.base_url, "/health/detailed")
                headers = {"X-API-Key": self.api_key}
                
                response = requests.get(url, headers=headers)
                
                if response.status_code == 200:
                    test_results.append(("Valid API key", True, "Successfully authenticated with valid API key"))
                else:
                    test_results.append(("Valid API key", False, f"Unexpected status code: {response.status_code}"))
            except Exception as e:
                test_results.append(("Valid API key", False, f"Error: {str(e)}"))
        else:
            test_results.append(("API key", False, "API key not provided for testing"))
        
        # Test with invalid API key
        try:
            invalid_key = "invalid_api_key_" + secrets.token_hex(8)
            url = urljoin(self.base_url, "/health/detailed")
            headers = {"X-API-Key": invalid_key}
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 401:
                test_results.append(("Invalid API key", True, "Successfully rejected invalid API key"))
            else:
                test_results.append(("Invalid API key", False, f"Expected 401, got {response.status_code}"))
        except Exception as e:
            test_results.append(("Invalid API key", False, f"Error: {str(e)}"))
        
        # Test without API key
        try:
            url = urljoin(self.base_url, "/health/detailed")
            response = requests.get(url)
            
            if response.status_code == 401:
                test_results.append(("No API key", True, "Correctly rejected request without API key"))
            else:
                test_results.append(("No API key", False, f"Expected 401, got {response.status_code}"))
        except Exception as e:
            test_results.append(("No API key", False, f"Error: {str(e)}"))
        
        # Update results
        self.results["authentication"] = test_results
        
        # Log results
        for test_name, passed, message in test_results:
            status = "PASS" if passed else "FAIL"
            logger.info(f"[{status}] {test_name}: {message}")
        
        # Return overall result
        return all(result[1] for result in test_results)
    
    def test_cors_policies(self) -> bool:
        """
        Test CORS policies
        
        Returns:
            True if CORS tests pass, False otherwise
        """
        test_results = []
        logger.info("Testing CORS policies...")
        
        try:
            url = urljoin(self.base_url, "/health")
            
            # Test preflight request
            response = requests.options(
                url,
                headers={
                    "Origin": "https://malicious-site.com",
                    "Access-Control-Request-Method": "GET"
                }
            )
            
            # Check for CORS headers
            cors_headers = {
                "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
                "Access-Control-Allow-Credentials": response.headers.get("Access-Control-Allow-Credentials"),
                "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
                "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers")
            }
            
            # Log CORS headers
            logger.info(f"CORS Headers: {json.dumps(cors_headers, indent=2)}")
            
            # Check if CORS is properly configured (not allowing all origins)
            allow_origin = cors_headers["Access-Control-Allow-Origin"]
            
            if allow_origin and allow_origin != "*":
                test_results.append(("CORS Configuration", True, f"CORS is properly configured with specific origins: {allow_origin}"))
            else:
                test_results.append(("CORS Configuration", False, "CORS is configured permissively or allows all origins"))
        except Exception as e:
            test_results.append(("CORS Configuration", False, f"Error testing CORS: {str(e)}"))
        
        # Update results
        self.results["cors"] = test_results
        
        # Log results
        for test_name, passed, message in test_results:
            status = "PASS" if passed else "FAIL"
            logger.info(f"[{status}] {test_name}: {message}")
        
        # Return overall result
        return all(result[1] for result in test_results)
    
    def test_security_headers(self) -> bool:
        """
        Test security headers in responses
        
        Returns:
            True if security header tests pass, False otherwise
        """
        test_results = []
        logger.info("Testing security headers...")
        
        try:
            url = urljoin(self.base_url, "/health")
            response = requests.get(url)
            
            # Check for security headers
            security_headers = {
                "X-Content-Type-Options": response.headers.get("X-Content-Type-Options"),
                "X-Frame-Options": response.headers.get("X-Frame-Options"),
                "X-XSS-Protection": response.headers.get("X-XSS-Protection"),
                "Strict-Transport-Security": response.headers.get("Strict-Transport-Security"),
                "Referrer-Policy": response.headers.get("Referrer-Policy")
            }
            
            # Log security headers
            logger.info(f"Security Headers: {json.dumps(security_headers, indent=2)}")
            
            # Test specific headers
            tests = [
                ("X-Content-Type-Options", security_headers["X-Content-Type-Options"] == "nosniff"),
                ("X-Frame-Options", security_headers["X-Frame-Options"] in ["DENY", "SAMEORIGIN"]),
                ("X-XSS-Protection", security_headers["X-XSS-Protection"] == "1; mode=block"),
                ("Referrer-Policy", security_headers["Referrer-Policy"] is not None),
                ("Server Header", response.headers.get("server") is None)
            ]
            
            for test_name, passed in tests:
                if passed:
                    test_results.append((test_name, True, f"{test_name} header is properly set"))
                else:
                    test_results.append((test_name, False, f"{test_name} header is not properly set or is missing"))
        except Exception as e:
            test_results.append(("Security Headers", False, f"Error testing security headers: {str(e)}"))
        
        # Update results
        self.results["security_headers"] = test_results
        
        # Log results
        for test_name, passed, message in test_results:
            status = "PASS" if passed else "FAIL"
            logger.info(f"[{status}] {test_name}: {message}")
        
        # Return overall result
        return all(result[1] for result in test_results)
    
    def test_input_sanitization(self) -> bool:
        """
        Test input sanitization measures
        
        Returns:
            True if input sanitization tests pass, False otherwise
        """
        test_results = []
        logger.info("Testing input sanitization...")
        
        # Test for XSS prevention
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src='x' onerror='alert(1)'>",
            "javascript:alert('XSS')",
            "<svg onload='alert(1)'>"
        ]
        
        try:
            url = urljoin(self.base_url, "/health/detailed")
            headers = {"X-API-Key": self.api_key} if self.api_key else {}
            
            # Test if XSS payloads are sanitized in error messages
            for payload in xss_payloads:
                response = requests.get(
                    url, 
                    params={"test": payload},
                    headers=headers
                )
                
                # Check if the payload appears unchanged in the response
                if payload in response.text and response.status_code != 400:
                    test_results.append(("XSS Prevention", False, f"XSS payload '{payload}' was not sanitized"))
                else:
                    test_results.append(("XSS Prevention", True, f"XSS payload '{payload}' was properly handled"))
        except Exception as e:
            test_results.append(("XSS Prevention", False, f"Error testing XSS prevention: {str(e)}"))
        
        # Test for path traversal prevention
        path_traversal_payloads = [
            "../../etc/passwd",
            "..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "....//....//....//etc//passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        ]
        
        try:
            for payload in path_traversal_payloads:
                url = urljoin(self.base_url, f"/{payload}")
                response = requests.get(url)
                
                # Check if path traversal payloads are rejected
                if response.status_code != 404 and response.status_code != 400:
                    test_results.append(("Path Traversal Prevention", False, f"Path traversal payload '{payload}' was not properly rejected"))
                else:
                    test_results.append(("Path Traversal Prevention", True, f"Path traversal payload '{payload}' was properly rejected"))
        except Exception as e:
            test_results.append(("Path Traversal Prevention", False, f"Error testing path traversal prevention: {str(e)}"))
        
        # Update results
        self.results["input_sanitization"] = test_results
        
        # Log results
        for test_name, passed, message in test_results:
            status = "PASS" if passed else "FAIL"
            logger.info(f"[{status}] {test_name}: {message}")
        
        # Return overall result
        return all(result[1] for result in test_results)
    
    def test_sql_injection(self) -> bool:
        """
        Test SQL injection prevention measures
        
        Returns:
            True if SQL injection tests pass, False otherwise
        """
        test_results = []
        logger.info("Testing SQL injection prevention...")
        
        # SQL injection payloads
        sql_payloads = [
            "' OR '1'='1",
            "\" OR \"1\"=\"1",
            "') OR ('1'='1",
            "' OR 1=1--",
            "\" OR 1=1--",
            "') OR ('1'='1'--",
            "' UNION SELECT NULL--",
            "\" UNION SELECT NULL--",
            "') UNION SELECT NULL--",
            "admin'--",
            "admin'#",
            "admin'/*",
            "' or '1'='1'#",
            "' or '1'='1'/*",
            "') or '1'='1'#",
            "') or '1'='1'/*"
        ]
        
        try:
            url = urljoin(self.base_url, "/health/detailed")
            headers = {"X-API-Key": self.api_key} if self.api_key else {}
            
            # Test if SQL injection payloads are properly handled
            for payload in sql_payloads:
                response = requests.get(
                    url, 
                    params={"search": payload},
                    headers=headers
                )
                
                # Check for SQL errors in the response
                if any(error in response.text.lower() for error in ["sql", "mysql", "postgresql", "sqlite", "database"]):
                    test_results.append(("SQL Injection Prevention", False, f"SQL injection payload '{payload}' may have caused a database error"))
                else:
                    test_results.append(("SQL Injection Prevention", True, f"SQL injection payload '{payload}' was properly handled"))
        except Exception as e:
            test_results.append(("SQL Injection Prevention", False, f"Error testing SQL injection prevention: {str(e)}"))
        
        # Update results
        self.results["sql_injection"] = test_results
        
        # Log results
        for test_name, passed, message in test_results:
            status = "PASS" if passed else "FAIL"
            logger.info(f"[{status}] {test_name}: {message}")
        
        # Return overall result
        return all(result[1] for result in test_results)
    
    def test_rate_limiting(self, requests_count: int = 10, window_seconds: int = 5) -> bool:
        """
        Test rate limiting measures
        
        Args:
            requests_count: Number of requests to send
            window_seconds: Time window for testing rate limiting
            
        Returns:
            True if rate limiting tests pass, False otherwise
        """
        test_results = []
        logger.info(f"Testing rate limiting ({requests_count} requests in {window_seconds} seconds)...")
        
        try:
            url = urljoin(self.base_url, "/health")
            
            # Track response times
            response_times = []
            status_codes = []
            
            # Send requests
            for i in range(requests_count):
                start_time = time.time()
                response = requests.get(url)
                end_time = time.time()
                
                response_times.append(end_time - start_time)
                status_codes.append(response.status_code)
                
                # Add a small delay to avoid overwhelming the server
                time.sleep(0.1)
            
            # Check for rate limiting indicators
            if 429 in status_codes:
                test_results.append(("Rate Limiting", True, f"Received HTTP 429 (Too Many Requests) indicating rate limiting is active"))
            else:
                # Check for gradual response time increase
                if len(response_times) >= 3:
                    first_third = sum(response_times[:len(response_times)//3]) / (len(response_times)//3)
                    last_third = sum(response_times[-len(response_times)//3:]) / (len(response_times)//3)
                    
                    if last_third > first_third * 2:
                        test_results.append(("Rate Limiting", True, f"Response times increased significantly (from {first_third:.3f}s to {last_third:.3f}s), indicating rate limiting"))
                    else:
                        test_results.append(("Rate Limiting", False, "No clear evidence of rate limiting detected"))
                else:
                    test_results.append(("Rate Limiting", False, "Insufficient data to determine rate limiting effectiveness"))
        except Exception as e:
            test_results.append(("Rate Limiting", False, f"Error testing rate limiting: {str(e)}"))
        
        # Update results
        self.results["rate_limiting"] = test_results
        
        # Log results
        for test_name, passed, message in test_results:
            status = "PASS" if passed else "FAIL"
            logger.info(f"[{status}] {test_name}: {message}")
        
        # Return overall result
        return all(result[1] for result in test_results)
    
    def run_all_tests(self) -> Dict[str, List[Tuple[str, bool, str]]]:
        """
        Run all security tests
        
        Returns:
            Dictionary of test results organized by category
        """
        logger.info("Running all security tests...")
        
        # Run all tests
        self.test_api_key_authentication()
        self.test_cors_policies()
        self.test_security_headers()
        self.test_input_sanitization()
        self.test_sql_injection()
        self.test_rate_limiting()
        
        # Log overall results
        logger.info("Overall security test results:")
        for category, tests in self.results.items():
            passed = sum(1 for _, test_passed, _ in tests if test_passed)
            total = len(tests)
            logger.info(f"{category}: {passed}/{total} tests passed")
        
        return self.results
    
    def generate_report(self) -> str:
        """
        Generate a security test report
        
        Returns:
            Formatted security test report
        """
        report = "# MAMcrawler API Security Test Report\n\n"
        report += f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Summary
        total_tests = 0
        passed_tests = 0
        
        for category, tests in self.results.items():
            total_tests += len(tests)
            passed_tests += sum(1 for _, test_passed, _ in tests if test_passed)
        
        report += f"## Summary\n\n"
        report += f"- Total Tests: {total_tests}\n"
        report += f"- Passed: {passed_tests}\n"
        report += f"- Failed: {total_tests - passed_tests}\n"
        report += f"- Pass Rate: {(passed_tests / total_tests * 100) if total_tests > 0 else 0:.1f}%\n\n"
        
        # Detailed results
        report += "## Detailed Results\n\n"
        
        for category, tests in self.results.items():
            if tests:  # Only include categories with tests
                report += f"### {category.replace('_', ' ').title()}\n\n"
                
                for test_name, passed, message in tests:
                    status = "[PASS]" if passed else "[FAIL]"
                    report += f"- **{test_name}**: {status}\n"
                    report += f"  - {message}\n"
                
                report += "\n"
        
        # Recommendations
        report += "## Recommendations\n\n"
        
        failed_tests = []
        for category, tests in self.results.items():
            for test_name, passed, message in tests:
                if not passed:
                    failed_tests.append((category, test_name, message))
        
        if failed_tests:
            report += "The following security measures need improvement:\n\n"
            
            for category, test_name, message in failed_tests:
                report += f"- **{test_name}** ({category.replace('_', ' ').title()}): {message}\n"
        else:
            report += "All security tests passed! The API appears to be properly secured.\n"
        
        return report

# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    # Set UTF-8 encoding for Windows console
    if sys.platform.startswith('win'):
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    
    # Get API URL and key from environment or command line
    api_url = os.getenv("API_URL", "http://localhost:8000")
    api_key = os.getenv("API_KEY")
    
    # Create tester
    tester = SecurityTester(api_url, api_key=api_key)
    
    # Run tests
    tester.run_all_tests()
    
    # Generate and print report
    report = tester.generate_report()
    print(report)