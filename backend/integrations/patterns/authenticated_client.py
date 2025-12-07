"""
Base class for authenticated async HTTP clients.

Provides common functionality for API clients with authentication, retry logic,
session management, and error handling.

This module serves as a template for creating new API client integrations.
Clients inherit from AuthenticatedAsyncClient to get:
- Session management (async context manager)
- Request retry logic with exponential backoff
- Automatic authentication error handling
- Consistent error handling and logging
- Timeout configuration
"""

import logging
import asyncio
from typing import Any, Dict, Optional
from abc import ABC

import aiohttp
from aiohttp import ClientTimeout, ClientError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class RequestError(Exception):
    """Raised when HTTP request fails."""
    pass


class AuthenticatedAsyncClient(ABC):
    """
    Base class for async HTTP clients with authentication and retry logic.

    Provides standard functionality for:
    - Session management and lifecycle
    - Request execution with retry logic
    - Authentication token management
    - Error handling and logging
    - Timeout configuration

    Subclasses should:
    1. Call super().__init__() in their constructor
    2. Set self.auth_token and self.headers appropriately
    3. Override _build_headers() if custom headers needed
    4. Override _handle_auth_error() if custom auth handling needed
    5. Call _request() for all HTTP operations

    Args:
        base_url: API base URL (e.g., "http://api.example.com")
        timeout: Request timeout in seconds (default: 30)

    Example:
        >>> class MyApiClient(AuthenticatedAsyncClient):
        ...     def __init__(self, base_url: str, token: str):
        ...         super().__init__(base_url, timeout=30)
        ...         self.auth_token = token
        ...         self.headers = self._build_headers()
        ...
        ...     async def get_user(self, user_id: str):
        ...         return await self._request("GET", f"/users/{user_id}")
    """

    def __init__(self, base_url: str, timeout: int = 30):
        """
        Initialize authenticated client.

        Args:
            base_url: Base URL for all API requests
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        self.headers: Dict[str, str] = {}

        logger.info(f"Initialized {self.__class__.__name__} for {self.base_url}")

    async def __aenter__(self):
        """Async context manager entry - initialize session."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close session."""
        await self.close()

    async def _ensure_session(self):
        """
        Ensure aiohttp session is initialized.

        Creates a new session if one doesn't exist.
        """
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers=self.headers,
            )
            logger.debug("Created new aiohttp session")

    async def close(self):
        """Close the session."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.debug("Closed aiohttp session")

    def _build_headers(self) -> Dict[str, str]:
        """
        Build request headers.

        Override this method to customize headers for your API client.

        Returns:
            Dictionary of headers for requests
        """
        headers = {
            "Content-Type": "application/json",
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ClientError, asyncio.TimeoutError)),
        reraise=True,
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic.

        Automatically:
        - Ensures session is initialized
        - Builds full URL from endpoint
        - Retries on client errors and timeouts (3 attempts, exponential backoff)
        - Handles JSON responses
        - Re-authenticates on 403 Forbidden
        - Logs all requests and errors

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            endpoint: API endpoint path (e.g., "/api/users")
            **kwargs: Additional arguments passed to aiohttp.request()
                - json: Request body as dict (auto-serialized)
                - params: Query parameters as dict
                - data: Form data
                - headers: Override headers for this request

        Returns:
            Parsed JSON response as dict

        Raises:
            RequestError: On HTTP errors (except 403)
            AuthenticationError: On 403 Forbidden (auth failed)

        Example:
            >>> result = await client._request("GET", "/api/items", params={"limit": 10})
            >>> result = await client._request("POST", "/api/items", json={"name": "item"})
        """
        await self._ensure_session()
        url = f"{self.base_url}{endpoint}"

        logger.debug(f"{method} {url}")

        try:
            async with self.session.request(method, url, **kwargs) as response:
                # Handle 403 Forbidden - authentication failure
                if response.status == 403:
                    logger.warning(f"Authentication failed (403) for {url}")
                    await self._handle_auth_error()
                    raise AuthenticationError(f"Authentication failed: {url}")

                # Handle 204 No Content
                if response.status == 204:
                    logger.debug(f"Response: {response.status} (no content)")
                    return {}

                # Raise for other HTTP errors
                response.raise_for_status()

                # Parse and return JSON response
                data = await response.json()
                logger.debug(f"Response: {response.status}")
                return data

        except aiohttp.ClientResponseError as e:
            logger.error(f"API error: {e.status} - {e.message}")
            raise RequestError(f"API request failed: {e.status} {e.message}")
        except aiohttp.ClientError as e:
            logger.error(f"Client error: {str(e)}")
            raise RequestError(f"Request failed: {str(e)}")
        except asyncio.TimeoutError:
            logger.error(f"Request timeout for {url}")
            raise RequestError(f"Request timeout: {url}")

    async def _handle_auth_error(self):
        """
        Handle authentication errors (403 Forbidden).

        Override this method to implement custom authentication recovery
        (e.g., token refresh, re-login).

        By default, logs the error and closes the session for a fresh start.
        """
        logger.warning("Authentication error - closing session for retry")
        await self.close()


__all__ = [
    "AuthenticatedAsyncClient",
    "AuthenticationError",
    "RequestError",
]
