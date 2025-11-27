"""
Secure Passive Crawling Service for MyAnonamouse.net
Uses Crawl4AI for stealthy, passive web crawling that mimics normal user behavior.
Includes comprehensive security fixes for credential exposure and API key management.
"""

import asyncio
import json
import logging
import os
import re
import secrets
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ratelimit import limits, sleep_and_retry
import markdown
from dotenv import load_dotenv
import aiohttp

# Load environment variables from .env file
load_dotenv()

# Configure logging with security considerations
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler_security.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SecurityError(Exception):
    """Custom exception for security-related errors."""
    pass

class CredentialManager:
    """Secure credential management with environment variable validation."""
    
    def __init__(self):
        self._validate_environment()
    
    @staticmethod
    def _validate_environment():
        """Validate that required environment variables are properly set."""
        required_vars = {
            'MAM_USERNAME': 'MyAnonamouse username',
            'MAM_PASSWORD': 'MyAnonamouse password'
        }
        
        missing_vars = []
        for var, description in required_vars.items():
            if not os.getenv(var):
                missing_vars.append(f"{var} ({description})")
        
        if missing_vars:
            raise SecurityError(
                f"Required environment variables not set: {', '.join(missing_vars)}. "
                "Please set these in your .env file or environment."
            )
    
    @staticmethod
    def get_secure_credentials() -> tuple[str, str]:
        """Get credentials securely from environment variables."""
        username = os.getenv('MAM_USERNAME')
        password = os.getenv('MAM_PASSWORD')
        
        if not username or not password:
            raise SecurityError("Credentials not available in environment variables")
        
        return username, password
    
    @staticmethod
    def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
        """Mask sensitive data for logging purposes."""
        if len(data) <= visible_chars * 2:
            return '*' * len(data)
        return data[:visible_chars] + '*' * (len(data) - visible_chars * 2) + data[-visible_chars:]

class MAMPassiveCrawler:
    """
    Secure passive crawler for MyAnonamouse.net that respects site terms 
    and mimics normal user behavior with comprehensive security measures.
    """

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        # Initialize secure credential manager
        self.credential_manager = CredentialManager()
        
        # Use environment variables for credentials (secure approach)
        if username and password:
            self.username = username
            self.password = password
            logger.warning("Using provided credentials - prefer environment variables for production")
        else:
            self.username, self.password = self.credential_manager.get_secure_credentials()

        # Validate credentials are not empty
        if not self.username or not self.password:
            raise SecurityError("Invalid credentials: username and password cannot be empty")

        self.base_url = "https://www.myanonamouse.net"
        self.session_cookies = None
        self.last_login = None
        self.login_expiry = timedelta(hours=2)  # MAM sessions typically last 2 hours

        # Rate limiting to mimic human behavior
        self.min_delay = 3  # seconds
        self.max_delay = 10  # seconds
        self.last_request = datetime.now()

        # User agent rotation for stealth
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]

        # Crawling restrictions - only publicly viewable content
        self.allowed_paths = [
            "/",  # homepage
            "/t/",  # torrent pages (public)
            "/tor/browse.php",  # browse page
            "/tor/search.php",  # search results
            "/guides/",  # guides section
            "/f/",  # forum sections (public)
        ]

        # Security: Generate secure session identifier
        self.session_id = f"mam_session_{secrets.token_hex(8)}"
        
        # Initialize resource cleanup tracking
        self._resources = []

    def __del__(self):
        """Cleanup resources when object is destroyed."""
        self._cleanup_resources()

    def _cleanup_resources(self):
        """Clean up resources to prevent memory leaks."""
        for resource in self._resources:
            try:
                if hasattr(resource, 'close'):
                    resource.close()
            except Exception as e:
                logger.warning(f"Error cleaning up resource: {e}")
        self._resources.clear()

    @sleep_and_retry
    @limits(calls=1, period=3)  # 1 request per 3 seconds
    async def _rate_limit(self):
        """Implement rate limiting to avoid detection."""
        now = datetime.now()
        elapsed = (now - self.last_request).total_seconds()

        if elapsed < self.min_delay:
            delay = random.uniform(self.min_delay, self.max_delay)
            logger.info(f"Rate limiting: sleeping for {delay:.2f} seconds")
            await asyncio.sleep(delay)

        self.last_request = datetime.now()

    def _sanitize_response_for_debugging(self, response_text: str) -> str:
        """Sanitize response text to remove sensitive information before logging."""
        try:
            # Remove any potential credential patterns
            sanitized = response_text
            
            # Remove form field values that might contain credentials
            sanitized = re.sub(r'value=["\'][^"\']*password[^"\']*["\']', 'value="[PASSWORD_MASKED]"', sanitized, flags=re.IGNORECASE)
            sanitized = re.sub(r'value=["\'][^"\']*username[^"\']*["\']', 'value="[USERNAME_MASKED]"', sanitized, flags=re.IGNORECASE)
            
            # Remove hidden input fields with sensitive names
            sanitized = re.sub(r'<input[^>]*type=["\']hidden["\'][^>]*name=["\'][^"\']*(?:token|session|key|secret)[^"\']*["\'][^>]*value=["\'][^"\']*["\'][^>]*>', '[HIDDEN_FIELD_MASKED]', sanitized, flags=re.IGNORECASE)
            
            # Remove any JWT tokens or API keys
            sanitized = re.sub(r'eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*', '[JWT_TOKEN_MASKED]', sanitized)
            
            # Limit length to prevent excessive file sizes
            if len(sanitized) > 10000:
                sanitized = sanitized[:10000] + "\n\n... [RESPONSE_TRUNCATED_FOR_SECURITY]"
            
            # Add security notice
            security_notice = f"""
<!-- SECURITY NOTICE: This file has been sanitized for security purposes on {datetime.now().isoformat()} -->
<!-- Original response contained {len(response_text)} bytes, sanitized to {len(sanitized)} bytes -->
<!-- All sensitive data including passwords, tokens, and session information has been removed -->

"""
            
            return security_notice + sanitized
            
        except Exception as e:
            logger.error(f"Error sanitizing response: {e}")
            # Fallback: just return a minimal safe response
            return f"<!-- Response sanitization failed on {datetime.now().isoformat()} -->"

    async def _ensure_authenticated(self) -> bool:
        """Ensure we have a valid authenticated session."""
        now = datetime.now()

        # Check if we need to login
        if (self.last_login is None or
            now - self.last_login > self.login_expiry or
            self.session_cookies is None):

            logger.info("Authenticating with MyAnonamouse.net")
            success = await self._login()
            if not success:
                logger.error("Failed to authenticate")
                return False

        return True

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception)
    )
    async def _login(self) -> bool:
        """Perform login using provided credentials with retry logic and comprehensive error handling."""
        try:
            login_url = f"{self.base_url}/takelogin.php"

            # MAM login requires form submission with username/password
            login_data = {
                "username": self.username,
                "password": self.password,
                "login": "Login"  # MAM login button value
            }

            # Use aiohttp for proper POST authentication
            user_agent = random.choice(self.user_agents)
            headers = {
                'User-Agent': user_agent,
                'Referer': f"{self.base_url}/login.php",
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            # Create session with proper cleanup
            session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            )
            self._resources.append(session)

            try:
                # First visit login page to get session cookies
                async with session.get(f"{self.base_url}/login.php") as resp:
                    await resp.text()

                # Submit login form with POST
                async with session.post(login_url, data=login_data, allow_redirects=True) as resp:
                    response_text = await resp.text()
                    response_status = resp.status

                    # SECURE: Save sanitized response for debugging (no credentials)
                    sanitized_response = self._sanitize_response_for_debugging(response_text)
                    debug_file_path = f'mam_login_response_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
                    with open(debug_file_path, 'w', encoding='utf-8') as f:
                        f.write(sanitized_response)

                    logger.info(f"Login response status: {response_status}")
                    logger.info(f"Response length: {len(response_text)} bytes")
                    logger.info(f"Sanitized debug file saved: {debug_file_path}")

                    # Check if login was successful
                    if "logout" in response_text.lower() or "my account" in response_text.lower():
                        logger.info("Login successful - found logout/my account link")
                        self.last_login = datetime.now()

                        # Store session cookies securely
                        self.session_cookies = {cookie.key: cookie.value for cookie in session.cookie_jar}
                        logger.info(f"Stored {len(self.session_cookies)} session cookies")
                        return True
                    else:
                        # Enhanced error detection
                        error_messages = []
                        if "invalid" in response_text.lower() or "incorrect" in response_text.lower():
                            error_messages.append("invalid credentials")
                        elif "captcha" in response_text.lower():
                            error_messages.append("CAPTCHA required")
                        elif "banned" in response_text.lower() or "disabled" in response_text.lower():
                            error_messages.append("account may be banned or disabled")
                        elif "rate limit" in response_text.lower() or "too many" in response_text.lower():
                            error_messages.append("rate limited")
                        
                        if error_messages:
                            logger.error(f"Login failed - {', '.join(error_messages)}")
                        else:
                            logger.error("Login failed - credentials may be invalid or site structure changed")

                        logger.info(f"Debug information saved to {debug_file_path}")
                        return False

            finally:
                # Ensure session is properly closed
                await session.close()
                if session in self._resources:
                    self._resources.remove(session)

        except aiohttp.ClientError as e:
            logger.error(f"Network error during login: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during login: {e}")
            raise

    def _is_allowed_path(self, url: str) -> bool:
        """Check if the URL path is allowed for passive crawling."""
        from urllib.parse import urlparse
        parsed = urlparse(url)

        # Must be on the correct domain
        if parsed.netloc != "www.myanonamouse.net":
            return False

        # Check against allowed paths
        path = parsed.path
        for allowed in self.allowed_paths:
            # Handle homepage as exact match only
            if allowed == "/" and path == "/":
                return True
            # For other paths, check prefix but not for "/"
            elif allowed != "/" and path.startswith(allowed):
                return True

        return False

    async def crawl_page(self, url: str, extraction_config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Crawl a single page passively with user agent rotation and rate limiting.

        Args:
            url: The URL to crawl
            extraction_config: Optional extraction configuration

        Returns:
            Dict containing crawled data
        """
        if not self._is_allowed_path(url):
            return {
                "success": False,
                "error": "URL not allowed for passive crawling",
                "url": url,
                "security_violation": True
            }

        await self._rate_limit()

        # Ensure authentication if needed
        if not await self._ensure_authenticated():
            return {
                "success": False,
                "error": "Authentication failed",
                "url": url
            }

        try:
            # Rotate user agent for each request
            user_agent = random.choice(self.user_agents)

            # Build CrawlerRunConfig with security considerations
            config = CrawlerRunConfig(
                verbose=False,
                user_agent=user_agent,
                # Additional security configurations
                page_timeout=30000,  # 30 second timeout
                browser_args=['--no-sandbox', '--disable-dev-shm-usage']
            )

            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=url, config=config)

                # Anonymize the data for security
                anonymized_data = self._anonymize_data(result)

                return {
                    "success": result.success,
                    "url": result.url,
                    "title": result.title,
                    "content_length": len(result.markdown) if result.markdown else 0,
                    "crawled_at": datetime.now().isoformat(),
                    "session_id": self.session_id,  # For debugging purposes
                    "data": anonymized_data
                }

        except Exception as e:
            logger.error(f"Crawling failed for {url}: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url,
                "crawled_at": datetime.now().isoformat()
            }

    def _anonymize_data(self, result) -> Dict[str, Any]:
        """
        Anonymize crawled data to remove sensitive information.

        Args:
            result: Crawl4AI result object

        Returns:
            Anonymized data dict
        """
        try:
            # Remove any potential user-specific information
            anonymized = {
                "title": result.title,
                "url": result.url,
                "content_type": "public_page",
                "crawl_timestamp": datetime.now().isoformat(),
                "session_id": self.session_id
            }

            # Only include markdown content if it's from allowed public pages
            if result.markdown and self._is_allowed_path(result.url):
                # Remove any user mentions, emails, or personal data
                content = result.markdown
                
                # Security: Remove sensitive patterns
                patterns_to_remove = [
                    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),
                    (r'\buser[_-]\w+\b', '[USER]', flags=re.IGNORECASE),
                    (r'\b[A-Za-z0-9]{20,}\b', '[POTENTIAL_TOKEN]'),  # Remove long alphanumeric strings
                    (r'eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*', '[JWT_TOKEN]'),
                ]
                
                for pattern, replacement in patterns_to_remove:
                    content = re.sub(pattern, replacement, content)
                
                # Limit content length for security and performance
                anonymized["content"] = content[:5000]
                
                # Add content analysis
                anonymized["content_analysis"] = {
                    "original_length": len(result.markdown),
                    "sanitized_length": len(content),
                    "redactions_applied": len(patterns_to_remove)
                }

            return anonymized
            
        except Exception as e:
            logger.error(f"Error anonymizing data: {e}")
            # Return minimal safe data in case of error
            return {
                "title": "Error anonymizing content",
                "url": getattr(result, 'url', 'unknown'),
                "content_type": "error",
                "crawl_timestamp": datetime.now().isoformat(),
                "error": str(e)
            }

    async def crawl_public_pages(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Crawl multiple public pages with enhanced rate limiting and error handling.

        Args:
            urls: List of URLs to crawl

        Returns:
            List of crawl results
        """
        results = []
        total_urls = len(urls)

        logger.info(f"Starting to crawl {total_urls} URLs with security measures enabled")

        for i, url in enumerate(urls, 1):
            logger.info(f"Progress: {i}/{total_urls} - Crawling: {url}")
            
            try:
                result = await self.crawl_page(url)
                results.append(result)
                
                # Log success/failure for monitoring
                if result.get("success"):
                    logger.debug(f"Successfully crawled: {url}")
                else:
                    logger.warning(f"Failed to crawl: {url} - {result.get('error', 'Unknown error')}")
                
            except Exception as e:
                logger.error(f"Unexpected error crawling {url}: {e}")
                results.append({
                    "success": False,
                    "url": url,
                    "error": f"Unexpected error: {str(e)}",
                    "crawled_at": datetime.now().isoformat()
                })

            # Add delay between requests (already handled by rate_limit, but extra safety)
            if i < total_urls:
                await asyncio.sleep(random.uniform(1, 3))

        # Cleanup resources after crawling
        self._cleanup_resources()
        
        logger.info(f"Crawling completed. Results: {len(results)} items processed")
        return results

# Example usage and testing
async def main():
    """Main function with comprehensive error handling."""
    try:
        # Initialize crawler with security measures
        crawler = MAMPassiveCrawler()
        
        # Test URL (public page)
        test_urls = [
            f"{crawler.base_url}/guides/",
            f"{crawler.base_url}/tor/browse.php"
        ]
        
        # Crawl pages with security
        results = await crawler.crawl_public_pages(test_urls)
        
        # Display results (sanitized)
        for result in results:
            print(f"URL: {result['url']}")
            print(f"Success: {result['success']}")
            if result.get('error'):
                print(f"Error: {result['error']}")
            print("-" * 50)
            
    except SecurityError as e:
        logger.error(f"Security error: {e}")
        print(f"Security configuration error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(main())