"""
Circuit Breaker Pattern Implementation

Prevents cascading failures by failing fast when external services are unavailable.
Provides automatic recovery and monitoring for service health.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5        # Failures before opening
    success_threshold: int = 3        # Successes to close from half-open
    timeout: float = 30.0             # Seconds before trying half-open
    excluded_exceptions: tuple = ()   # Exceptions that don't count as failures


@dataclass
class CircuitStats:
    """Statistics for circuit breaker monitoring."""
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_changes: int = 0


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    def __init__(self, service_name: str, time_until_retry: float):
        self.service_name = service_name
        self.time_until_retry = time_until_retry
        super().__init__(
            f"Circuit breaker open for '{service_name}'. "
            f"Retry in {time_until_retry:.1f} seconds."
        )


class CircuitBreaker:
    """
    Circuit breaker for external service calls.

    States:
    - CLOSED: Normal operation, calls pass through
    - OPEN: Failing fast, all calls immediately rejected
    - HALF_OPEN: Testing if service recovered

    Example:
        >>> breaker = CircuitBreaker("audiobookshelf", failure_threshold=3)

        >>> @breaker
        ... async def fetch_books():
        ...     return await abs_client.get_books()

        >>> # Or use as context manager
        >>> async with breaker:
        ...     result = await abs_client.get_books()
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        timeout: float = 30.0,
        excluded_exceptions: tuple = (),
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Service name for logging/monitoring
            failure_threshold: Failures before opening circuit
            success_threshold: Successes to close from half-open
            timeout: Seconds to wait before attempting recovery
            excluded_exceptions: Exceptions that don't trigger breaker
        """
        self.name = name
        self.config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            timeout=timeout,
            excluded_exceptions=excluded_exceptions,
        )
        self.state = CircuitState.CLOSED
        self.stats = CircuitStats()
        self._last_state_change = time.time()
        self._lock = asyncio.Lock()

        logger.info(
            f"CircuitBreaker '{name}' initialized: "
            f"threshold={failure_threshold}, timeout={timeout}s"
        )

    async def _check_state(self) -> None:
        """Check and potentially update circuit state."""
        if self.state == CircuitState.OPEN:
            elapsed = time.time() - self._last_state_change
            if elapsed >= self.config.timeout:
                await self._transition_to(CircuitState.HALF_OPEN)

    async def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state with logging."""
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            self._last_state_change = time.time()
            self.stats.state_changes += 1

            logger.warning(
                f"CircuitBreaker '{self.name}': {old_state.value} -> {new_state.value}"
            )

            if new_state == CircuitState.OPEN:
                logger.error(
                    f"CircuitBreaker '{self.name}' OPENED after "
                    f"{self.stats.consecutive_failures} consecutive failures"
                )
            elif new_state == CircuitState.CLOSED:
                logger.info(
                    f"CircuitBreaker '{self.name}' CLOSED - service recovered"
                )

    async def _record_success(self) -> None:
        """Record successful call."""
        async with self._lock:
            self.stats.total_calls += 1
            self.stats.total_successes += 1
            self.stats.consecutive_successes += 1
            self.stats.consecutive_failures = 0
            self.stats.last_success_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                if self.stats.consecutive_successes >= self.config.success_threshold:
                    await self._transition_to(CircuitState.CLOSED)

    async def _record_failure(self, exception: Exception) -> None:
        """Record failed call."""
        # Check if exception should be excluded
        if isinstance(exception, self.config.excluded_exceptions):
            logger.debug(
                f"CircuitBreaker '{self.name}': excluded exception {type(exception).__name__}"
            )
            return

        async with self._lock:
            self.stats.total_calls += 1
            self.stats.total_failures += 1
            self.stats.consecutive_failures += 1
            self.stats.consecutive_successes = 0
            self.stats.last_failure_time = time.time()

            logger.warning(
                f"CircuitBreaker '{self.name}': failure {self.stats.consecutive_failures}/"
                f"{self.config.failure_threshold} - {type(exception).__name__}: {exception}"
            )

            if self.state == CircuitState.HALF_OPEN:
                # Any failure in half-open reopens the circuit
                await self._transition_to(CircuitState.OPEN)
            elif self.state == CircuitState.CLOSED:
                if self.stats.consecutive_failures >= self.config.failure_threshold:
                    await self._transition_to(CircuitState.OPEN)

    def _time_until_retry(self) -> float:
        """Calculate time until retry is allowed."""
        elapsed = time.time() - self._last_state_change
        return max(0, self.config.timeout - elapsed)

    async def __aenter__(self):
        """Async context manager entry."""
        await self._check_state()

        if self.state == CircuitState.OPEN:
            raise CircuitBreakerError(self.name, self._time_until_retry())

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if exc_type is None:
            await self._record_success()
        elif exc_val is not None:
            await self._record_failure(exc_val)
        return False  # Don't suppress exceptions

    def __call__(self, func: Callable) -> Callable:
        """Decorator for wrapping functions with circuit breaker."""
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                async with self:
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # For sync functions, use synchronous state check
                if self.state == CircuitState.OPEN:
                    elapsed = time.time() - self._last_state_change
                    if elapsed < self.config.timeout:
                        raise CircuitBreakerError(self.name, self._time_until_retry())
                    self.state = CircuitState.HALF_OPEN
                    self._last_state_change = time.time()

                try:
                    result = func(*args, **kwargs)
                    self.stats.total_calls += 1
                    self.stats.total_successes += 1
                    self.stats.consecutive_successes += 1
                    self.stats.consecutive_failures = 0

                    if self.state == CircuitState.HALF_OPEN:
                        if self.stats.consecutive_successes >= self.config.success_threshold:
                            self.state = CircuitState.CLOSED
                    return result

                except Exception as e:
                    if not isinstance(e, self.config.excluded_exceptions):
                        self.stats.total_calls += 1
                        self.stats.total_failures += 1
                        self.stats.consecutive_failures += 1
                        self.stats.consecutive_successes = 0

                        if self.stats.consecutive_failures >= self.config.failure_threshold:
                            self.state = CircuitState.OPEN
                            self._last_state_change = time.time()
                    raise

            return sync_wrapper

    def get_stats(self) -> Dict[str, Any]:
        """Get current circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "total_calls": self.stats.total_calls,
            "total_failures": self.stats.total_failures,
            "total_successes": self.stats.total_successes,
            "failure_rate": (
                self.stats.total_failures / self.stats.total_calls
                if self.stats.total_calls > 0 else 0
            ),
            "consecutive_failures": self.stats.consecutive_failures,
            "consecutive_successes": self.stats.consecutive_successes,
            "last_failure": self.stats.last_failure_time,
            "last_success": self.stats.last_success_time,
            "state_changes": self.stats.state_changes,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout,
            },
        }

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self.state = CircuitState.CLOSED
        self.stats = CircuitStats()
        self._last_state_change = time.time()
        logger.info(f"CircuitBreaker '{self.name}' reset to CLOSED")

    def force_open(self) -> None:
        """Force circuit breaker to open state (for testing/maintenance)."""
        self.state = CircuitState.OPEN
        self._last_state_change = time.time()
        logger.warning(f"CircuitBreaker '{self.name}' forced OPEN")


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.

    Provides centralized access and monitoring for all service circuit breakers.

    Example:
        >>> registry = CircuitBreakerRegistry()
        >>> abs_breaker = registry.get_or_create("audiobookshelf", failure_threshold=3)
        >>> qbt_breaker = registry.get_or_create("qbittorrent", failure_threshold=5)

        >>> # Get all stats
        >>> all_stats = registry.get_all_stats()
    """

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}

    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        timeout: float = 30.0,
        excluded_exceptions: tuple = (),
    ) -> CircuitBreaker:
        """Get existing or create new circuit breaker."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                success_threshold=success_threshold,
                timeout=timeout,
                excluded_exceptions=excluded_exceptions,
            )
        return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._breakers.get(name)

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers."""
        return {
            name: breaker.get_stats()
            for name, breaker in self._breakers.items()
        }

    def reset_all(self) -> None:
        """Reset all circuit breakers to closed state."""
        for breaker in self._breakers.values():
            breaker.reset()
        logger.info(f"All {len(self._breakers)} circuit breakers reset")

    def get_open_breakers(self) -> List[str]:
        """Get names of all currently open circuit breakers."""
        return [
            name for name, breaker in self._breakers.items()
            if breaker.state == CircuitState.OPEN
        ]

    def is_healthy(self) -> bool:
        """Check if all circuit breakers are healthy (closed)."""
        return all(
            breaker.state == CircuitState.CLOSED
            for breaker in self._breakers.values()
        )


# Global registry instance
circuit_registry = CircuitBreakerRegistry()


# Pre-configured circuit breakers for common services
def get_audiobookshelf_breaker() -> CircuitBreaker:
    """Get circuit breaker for Audiobookshelf API."""
    return circuit_registry.get_or_create(
        "audiobookshelf",
        failure_threshold=3,
        success_threshold=2,
        timeout=60.0,
    )


def get_goodreads_breaker() -> CircuitBreaker:
    """Get circuit breaker for Goodreads scraping."""
    return circuit_registry.get_or_create(
        "goodreads",
        failure_threshold=5,
        success_threshold=3,
        timeout=120.0,  # Longer timeout for scraping
    )


def get_mam_breaker() -> CircuitBreaker:
    """Get circuit breaker for MAM crawling."""
    return circuit_registry.get_or_create(
        "mam",
        failure_threshold=5,
        success_threshold=3,
        timeout=300.0,  # 5 min timeout, MAM may have maintenance
    )


def get_qbittorrent_breaker() -> CircuitBreaker:
    """Get circuit breaker for qBittorrent API."""
    return circuit_registry.get_or_create(
        "qbittorrent",
        failure_threshold=3,
        success_threshold=2,
        timeout=30.0,
    )


def get_google_books_breaker() -> CircuitBreaker:
    """Get circuit breaker for Google Books API."""
    return circuit_registry.get_or_create(
        "google_books",
        failure_threshold=10,  # Higher threshold for rate limits
        success_threshold=5,
        timeout=3600.0,  # 1 hour timeout for quota resets
    )
