"""
Rate Limiter

Implements token bucket algorithm for API rate limiting.

Author: Agent 10 - API Client Consolidation Specialist
"""

import asyncio
import time
from typing import Optional


class RateLimiter:
    """
    Token bucket rate limiter.

    Ensures requests don't exceed the specified rate limit.
    """

    def __init__(self, requests_per_period: int, period: int):
        """
        Initialize rate limiter.

        Args:
            requests_per_period: Maximum requests allowed per period
            period: Time period in seconds
        """
        self.requests_per_period = requests_per_period
        self.period = period
        self.tokens = requests_per_period
        self.last_refill = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """
        Acquire a token, waiting if necessary.

        Raises:
            asyncio.TimeoutError: If rate limit is exceeded
        """
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_refill

            # Refill tokens based on elapsed time
            refill_amount = int(elapsed / self.period * self.requests_per_period)
            self.tokens = min(self.requests_per_period, self.tokens + refill_amount)
            self.last_refill = now

            if self.tokens > 0:
                self.tokens -= 1
                return

            # Wait for next token
            wait_time = self.period / self.requests_per_period
            await asyncio.sleep(wait_time)
            self.tokens = self.requests_per_period - 1
            self.last_refill = time.time()