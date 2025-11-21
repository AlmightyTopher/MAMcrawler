#!/usr/bin/env python3
"""
Async HTTP Client for MAMcrawler
================================

Provides proper async HTTP client with connection pooling,
rate limiting, retry logic, and comprehensive error handling.
"""

import asyncio
import time
import logging
from typing import Optional, Dict, Any, List, Union
from urllib.parse import urljoin, urlparse
import json

import httpx
import async_timeout
from config import config


class AsyncHTTPClient:
    """Production-ready async HTTP client with advanced features."""
    
    def __init__(self):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limiter = RateLimiter(
            min_delay=config.crawler.request_delay_min,
            max_delay=config.crawler.request_delay_max
        )
        self._retry_handler = RetryHandler(max_retries=3)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._initialize_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _initialize_client(self):
        """Initialize HTTP client with proper configuration."""
        if self._client is None:
            # Build headers with proper user agent
            headers = {
                "User-Agent": self.config.crawler.browser_user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            # Configure proxies if available
            proxies = {}
            if self.config.crawler.http_proxy:
                proxies["http://"] = self.config.crawler.http_proxy
            if self.config.crawler.https_proxy:
                proxies["https://"] = self.config.crawler.https_proxy
            
            # Create client with connection pooling
            limits = httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20
            )
            
            timeout = httpx.Timeout(
                connect=10.0,
                read=self.config.system.request_timeout,
                write=10.0,
                pool=5.0
            )
            
            self._client = httpx.AsyncClient(
                headers=headers,
                limits=limits,
                timeout=timeout,
                proxies=proxies if proxies else None,
                follow_redirects=True,
                max_redirects=5
            )
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def get(
        self, 
        url: str, 
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> httpx.Response:
        """Async GET request with rate limiting and retry logic."""
        await self._rate_limiter.acquire()
        
        try:
            response = await self._retry_handler.execute(
                self._client.get,
                url,
                params=params,
                headers=headers,
                **kwargs
            )
            
            self.logger.debug(f"GET {url} - Status: {response.status_code}")
            return response
            
        except Exception as e:
            self.logger.error(f"GET {url} failed: {e}")
            raise
    
    async def post(
        self,
        url: str,
        data: Optional[Union[Dict[str, Any], str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> httpx.Response:
        """Async POST request with rate limiting and retry logic."""
        await self._rate_limiter.acquire()
        
        try:
            response = await self._retry_handler.execute(
                self._client.post,
                url,
                data=data,
                json=json_data,
                files=files,
                headers=headers,
                **kwargs
            )
            
            self.logger.debug(f"POST {url} - Status: {response.status_code}")
            return response
            
        except Exception as e:
            self.logger.error(f"POST {url} failed: {e}")
            raise
    
    async def put(
        self,
        url: str,
        data: Optional[Union[Dict[str, Any], str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> httpx.Response:
        """Async PUT request with rate limiting and retry logic."""
        await self._rate_limiter.acquire()
        
        try:
            response = await self._retry_handler.execute(
                self._client.put,
                url,
                data=data,
                json=json_data,
                headers=headers,
                **kwargs
            )
            
            self.logger.debug(f"PUT {url} - Status: {response.status_code}")
            return response
            
        except Exception as e:
            self.logger.error(f"PUT {url} failed: {e}")
            raise
    
    async def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> httpx.Response:
        """Async DELETE request with rate limiting and retry logic."""
        await self._rate_limiter.acquire()
        
        try:
            response = await self._retry_handler.execute(
                self._client.delete,
                url,
                headers=headers,
                **kwargs
            )
            
            self.logger.debug(f"DELETE {url} - Status: {response.status_code}")
            return response
            
        except Exception as e:
            self.logger.error(f"DELETE {url} failed: {e}")
            raise
    
    async def download_file(
        self,
        url: str,
        file_path: str,
        chunk_size: int = 8192,
        **kwargs
    ) -> bool:
        """Download a file asynchronously with progress tracking."""
        await self._rate_limiter.acquire()
        
        try:
            async with self._client.stream("GET", url, **kwargs) as response:
                response.raise_for_status()
                
                with open(file_path, 'wb') as f:
                    async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                        f.write(chunk)
                
                self.logger.info(f"Downloaded {url} to {file_path}")
                return True
                
        except Exception as e:
            self.logger.error(f"Download {url} failed: {e}")
            return False
    
    def build_url(self, base_url: str, path: str, params: Optional[Dict] = None) -> str:
        """Build a complete URL from base URL, path and parameters."""
        url = urljoin(base_url, path)
        if params:
            query_string = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{query_string}"
        return url


class RateLimiter:
    """Rate limiter for HTTP requests with configurable delays."""
    
    def __init__(self, min_delay: float = 1.0, max_delay: float = 3.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._last_request_time = 0.0
    
    async def acquire(self):
        """Acquire permission to make a request (rate limiting)."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last
            await asyncio.sleep(sleep_time)
        
        self._last_request_time = time.time()


class RetryHandler:
    """Retry handler with exponential backoff for failed requests."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    async def execute(self, func, *args, **kwargs):
        """Execute function with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            
            except (httpx.RequestError, httpx.ConnectError) as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    break
                
                # Exponential backoff with jitter
                delay = self.base_delay * (2 ** attempt)
                jitter = delay * 0.1 * (time.time() % 1)  # Add jitter
                await asyncio.sleep(delay + jitter)
                
                logging.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}")
        
        raise last_exception


class APIError(Exception):
    """Custom exception for API-related errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class BaseAPI:
    """Base class for API clients with common functionality."""
    
    def __init__(self, base_url: str, client: AsyncHTTPClient):
        self.base_url = base_url.rstrip('/')
        self.client = client
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def get(self, endpoint: str, params: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Make a GET request to the API endpoint."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        response = await self.client.get(url, params=params, **kwargs)
        
        if response.status_code >= 400:
            raise APIError(
                f"API request failed: {response.status_code}",
                status_code=response.status_code,
                response_text=response.text[:500]
            )
        
        # Try to parse as JSON, fall back to text
        try:
            return response.json()
        except json.JSONDecodeError:
            return {"text": response.text}
    
    async def post(self, endpoint: str, json_data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Make a POST request to the API endpoint."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        response = await self.client.post(url, json_data=json_data, **kwargs)
        
        if response.status_code >= 400:
            raise APIError(
                f"API request failed: {response.status_code}",
                status_code=response.status_code,
                response_text=response.text[:500]
            )
        
        try:
            return response.json()
        except json.JSONDecodeError:
            return {"text": response.text}


class HTTPClientManager:
    """Manager for HTTP client instances."""
    
    _instances: Dict[str, AsyncHTTPClient] = {}
    
    @classmethod
    async def get_client(cls, name: str = "default") -> AsyncHTTPClient:
        """Get or create an HTTP client instance."""
        if name not in cls._instances:
            cls._instances[name] = AsyncHTTPClient()
            await cls._instances[name]._initialize_client()
        
        return cls._instances[name]
    
    @classmethod
    async def close_all(cls):
        """Close all HTTP client instances."""
        for client in cls._instances.values():
            await client.close()
        cls._instances.clear()


# Convenience functions for common use cases
async def make_async_request(
    method: str,
    url: str,
    **kwargs
) -> httpx.Response:
    """Make an async HTTP request with proper client management."""
    async with AsyncHTTPClient() as client:
        if method.upper() == "GET":
            return await client.get(url, **kwargs)
        elif method.upper() == "POST":
            return await client.post(url, **kwargs)
        elif method.upper() == "PUT":
            return await client.put(url, **kwargs)
        elif method.upper() == "DELETE":
            return await client.delete(url, **kwargs)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")


async def fetch_json(url: str, **kwargs) -> Dict[str, Any]:
    """Fetch JSON data from a URL."""
    async with AsyncHTTPClient() as client:
        response = await client.get(url, **kwargs)
        response.raise_for_status()
        return response.json()


async def fetch_text(url: str, **kwargs) -> str:
    """Fetch text data from a URL."""
    async with AsyncHTTPClient() as client:
        response = await client.get(url, **kwargs)
        response.raise_for_status()
        return response.text


# Initialize logging for this module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    # Simple test
    async def test_client():
        async with AsyncHTTPClient() as client:
            try:
                response = await client.get("https://httpbin.org/get")
                print(f"Status: {response.status_code}")
                print(f"Response: {response.json()}")
            except Exception as e:
                print(f"Error: {e}")
    
    asyncio.run(test_client())