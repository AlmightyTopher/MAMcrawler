#!/usr/bin/env python3
"""
Unified API Client System for MAMcrawler
========================================

Provides a comprehensive, unified API client framework that supports:
- REST API clients with automatic retry and rate limiting
- GraphQL API clients
- WebSocket clients for real-time communication
- Authentication handling (API keys, OAuth, JWT)
- Request/response interceptors and middleware
- Connection pooling and performance optimization
- Error handling and circuit breaker patterns
- API versioning and backward compatibility

Author: Agent 10 - API Client Consolidation Specialist
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Type, Union, Callable
from pathlib import Path
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import time

from config import config

logger = logging.getLogger(__name__)


@dataclass
class APIClientConfig:
    """Configuration for API clients."""
    base_url: str
    timeout: int = 30
    retry_attempts: int = 3
    retry_backoff: float = 1.0
    rate_limit_requests: int = 60
    rate_limit_period: int = 60
    connection_pool_size: int = 10
    max_keepalive: int = 10
    headers: Dict[str, str] = field(default_factory=dict)
    auth_config: Optional[Dict[str, Any]] = None
    enable_metrics: bool = True
    enable_circuit_breaker: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60


@dataclass
class APIRequest:
    """Represents an API request."""
    method: str
    endpoint: str
    params: Optional[Dict[str, Any]] = None
    data: Optional[Union[Dict[str, Any], str]] = None
    json_data: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    timeout: Optional[int] = None


@dataclass
class APIResponse:
    """Represents an API response."""
    status_code: int
    headers: Dict[str, str]
    data: Any
    request_time: float
    success: bool
    error_message: Optional[str] = None


class APIClientError(Exception):
    """Base exception for API client errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class AuthenticationError(APIClientError):
    """Authentication failed."""
    pass


class RateLimitError(APIClientError):
    """Rate limit exceeded."""
    pass


class CircuitBreakerError(APIClientError):
    """Circuit breaker is open."""
    pass


class APIClientMetrics:
    """Metrics collection for API clients."""

    def __init__(self):
        self.requests_total = 0
        self.requests_success = 0
        self.requests_error = 0
        self.request_duration_total = 0.0
        self.rate_limit_hits = 0
        self.circuit_breaker_trips = 0
        self.retry_attempts = 0

    def record_request(self, duration: float, success: bool):
        """Record a request."""
        self.requests_total += 1
        self.request_duration_total += duration
        if success:
            self.requests_success += 1
        else:
            self.requests_error += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get metrics statistics."""
        avg_duration = self.request_duration_total / max(self.requests_total, 1)
        success_rate = self.requests_success / max(self.requests_total, 1)

        return {
            "requests_total": self.requests_total,
            "requests_success": self.requests_success,
            "requests_error": self.requests_error,
            "avg_request_duration": avg_duration,
            "success_rate": success_rate,
            "rate_limit_hits": self.rate_limit_hits,
            "circuit_breaker_trips": self.circuit_breaker_trips,
            "retry_attempts": self.retry_attempts,
        }


class APIClientBase(ABC):
    """Base class for all API clients."""

    def __init__(self, config: APIClientConfig):
        self.config = config
        self.metrics = APIClientMetrics() if config.enable_metrics else None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Initialize components
        self._auth_handler = None
        self._rate_limiter = None
        self._retry_handler = None
        self._circuit_breaker = None
        self._connection_pool = None
        self._interceptors: List[Callable] = []

        self._initialize_components()

    def _initialize_components(self):
        """Initialize client components."""
        from api_auth import get_auth_handler
        from api_utils import (
            RateLimiter, RetryHandler, CircuitBreaker,
            ConnectionPool, RequestInterceptor
        )

        # Authentication
        if self.config.auth_config:
            self._auth_handler = get_auth_handler(self.config.auth_config)

        # Rate limiting
        self._rate_limiter = RateLimiter(
            requests_per_period=self.config.rate_limit_requests,
            period=self.config.rate_limit_period
        )

        # Retry logic
        self._retry_handler = RetryHandler(
            max_attempts=self.config.retry_attempts,
            backoff_factor=self.config.retry_backoff
        )

        # Circuit breaker
        if self.config.enable_circuit_breaker:
            self._circuit_breaker = CircuitBreaker(
                failure_threshold=self.config.circuit_breaker_threshold,
                recovery_timeout=self.config.circuit_breaker_timeout
            )

        # Connection pool
        self._connection_pool = ConnectionPool(
            pool_size=self.config.connection_pool_size,
            max_keepalive=self.config.max_keepalive
        )

        # Default interceptors
        self._interceptors = [
            RequestInterceptor.log_requests,
            RequestInterceptor.add_default_headers,
        ]

    async def __aenter__(self):
        """Async context manager entry."""
        await self._initialize_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session()

    @abstractmethod
    async def _initialize_session(self):
        """Initialize the client session."""
        pass

    @abstractmethod
    async def _close_session(self):
        """Close the client session."""
        pass

    @abstractmethod
    async def _make_request(self, request: APIRequest) -> APIResponse:
        """Make an actual API request."""
        pass

    async def request(self, request: APIRequest) -> APIResponse:
        """Make a request with all middleware applied."""
        start_time = time.time()

        try:
            # Apply request interceptors
            for interceptor in self._interceptors:
                request = await interceptor(request, self)

            # Check circuit breaker
            if self._circuit_breaker and not self._circuit_breaker.can_proceed():
                raise CircuitBreakerError("Circuit breaker is open")

            # Apply rate limiting
            if self._rate_limiter:
                await self._rate_limiter.acquire()

            # Apply authentication
            if self._auth_handler:
                request = await self._auth_handler.authenticate_request(request)

            # Make the actual request with retry logic
            response = await self._retry_handler.execute(
                self._make_request,
                request
            )

            # Record success
            if self.metrics:
                self.metrics.record_request(time.time() - start_time, True)

            return response

        except Exception as e:
            # Record failure
            if self.metrics:
                self.metrics.record_request(time.time() - start_time, False)

            # Update circuit breaker
            if self._circuit_breaker:
                self._circuit_breaker.record_failure()

            # Re-raise with appropriate error type
            if isinstance(e, APIClientError):
                raise
            else:
                raise APIClientError(f"Request failed: {str(e)}") from e

    def add_interceptor(self, interceptor: Callable):
        """Add a request/response interceptor."""
        self._interceptors.append(interceptor)

    def get_metrics(self) -> Optional[Dict[str, Any]]:
        """Get client metrics."""
        return self.metrics.get_stats() if self.metrics else None


class APIClientManager:
    """
    Main API client manager and factory.

    Provides unified access to all API clients with centralized configuration
    and monitoring.
    """

    def __init__(self):
        self._clients: Dict[str, APIClientBase] = {}
        self._client_configs: Dict[str, APIClientConfig] = {}
        self._client_types: Dict[str, Type[APIClientBase]] = {}
        self.logger = logging.getLogger(__name__)

        # Register built-in client types
        self._register_builtin_clients()

    def _register_builtin_clients(self):
        """Register built-in client implementations."""
        from api_clients import (
            RESTAPIClient, GraphQLAPIClient, WebSocketAPIClient,
            ScraperAPIClient, MAMAPIClient, AudiobookshelfAPIClient,
            QBittorrentAPIClient, ProwlarrAPIClient
        )

        self.register_client_type("rest", RESTAPIClient)
        self.register_client_type("graphql", GraphQLAPIClient)
        self.register_client_type("websocket", WebSocketAPIClient)
        self.register_client_type("scraper", ScraperAPIClient)
        self.register_client_type("mam", MAMAPIClient)
        self.register_client_type("audiobookshelf", AudiobookshelfAPIClient)
        self.register_client_type("qbittorrent", QBittorrentAPIClient)
        self.register_client_type("prowlarr", ProwlarrAPIClient)

    def register_client_type(self, name: str, client_class: Type[APIClientBase]):
        """Register a new client type."""
        self._client_types[name] = client_class
        self.logger.info(f"Registered client type: {name}")

    def configure_client(self, name: str, config: APIClientConfig):
        """Configure a client."""
        self._client_configs[name] = config
        self.logger.info(f"Configured client: {name}")

    def get_client(self, name: str) -> APIClientBase:
        """Get or create a client instance."""
        if name not in self._clients:
            if name not in self._client_configs:
                raise ValueError(f"No configuration found for client: {name}")

            config = self._client_configs[name]
            client_class = self._client_types.get(name)

            if not client_class:
                raise ValueError(f"No client type registered for: {name}")

            self._clients[name] = client_class(config)

        return self._clients[name]

    async def close_all_clients(self):
        """Close all client sessions."""
        for client in self._clients.values():
            await client._close_session()
        self._clients.clear()

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all clients."""
        return {
            name: client.get_metrics() or {}
            for name, client in self._clients.items()
        }

    def list_clients(self) -> List[str]:
        """List all configured clients."""
        return list(self._client_configs.keys())

    def list_client_types(self) -> List[str]:
        """List all registered client types."""
        return list(self._client_types.keys())


# Global client manager instance
api_client_manager = APIClientManager()


def get_api_client(name: str) -> APIClientBase:
    """Convenience function to get an API client."""
    return api_client_manager.get_client(name)


def configure_api_client(name: str, config: APIClientConfig):
    """Convenience function to configure an API client."""
    api_client_manager.configure_client(name, config)


async def initialize_api_clients():
    """Initialize all configured API clients."""
    logger.info("Initializing API clients...")

    # Configure built-in clients from config
    client_configs = {
        "audiobookshelf": APIClientConfig(
            base_url=config.audiobookshelf.base_url,
            auth_config={
                "type": "bearer",
                "token": config.audiobookshelf.api_token
            }
        ),
        "qbittorrent": APIClientConfig(
            base_url=config.qbittorrent.base_url,
            auth_config={
                "type": "basic",
                "username": config.qbittorrent.username,
                "password": config.qbittorrent.password
            }
        ),
        "prowlarr": APIClientConfig(
            base_url=config.prowlarr.base_url,
            auth_config={
                "type": "api_key",
                "api_key": config.prowlarr.api_key
            }
        ),
        "goodreads": APIClientConfig(
            base_url="https://www.goodreads.com",
            rate_limit_requests=5,
            rate_limit_period=1
        ),
        "google_books": APIClientConfig(
            base_url="https://www.googleapis.com/books/v1",
            auth_config={
                "type": "api_key",
                "api_key": config.google_books.api_key
            } if hasattr(config, 'google_books') and config.google_books.api_key else None
        )
    }

    for name, client_config in client_configs.items():
        try:
            configure_api_client(name, client_config)
            logger.info(f"Configured API client: {name}")
        except Exception as e:
            logger.warning(f"Failed to configure client {name}: {e}")


async def shutdown_api_clients():
    """Shutdown all API clients."""
    logger.info("Shutting down API clients...")
    await api_client_manager.close_all_clients()


# Initialize on import
asyncio.create_task(initialize_api_clients())