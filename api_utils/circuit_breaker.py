"""
Circuit Breaker

Implements circuit breaker pattern to prevent cascading failures.

Author: Agent 10 - API Client Consolidation Specialist
"""

import time
from enum import Enum


class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Circuit breaker implementation.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None

    def can_proceed(self) -> bool:
        """Check if request can proceed."""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                return True
            return False
        else:  # HALF_OPEN
            return True

    def record_failure(self):
        """Record a failure."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN

    def record_success(self):
        """Record a success."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.CLOSED
            self.failure_count = 0