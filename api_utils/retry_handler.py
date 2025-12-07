"""
Retry Handler

Implements exponential backoff retry logic with configurable parameters.

Author: Agent 10 - API Client Consolidation Specialist
"""

import asyncio
import random
from typing import Callable, Any, Optional


class RetryHandler:
    """
    Handles retry logic with exponential backoff and jitter.
    """

    def __init__(self, max_attempts: int = 3, backoff_factor: float = 1.0, jitter: bool = True):
        """
        Initialize retry handler.

        Args:
            max_attempts: Maximum number of retry attempts
            backoff_factor: Exponential backoff multiplier
            jitter: Whether to add random jitter to delay
        """
        self.max_attempts = max_attempts
        self.backoff_factor = backoff_factor
        self.jitter = jitter

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            Last exception encountered
        """
        last_exception = None

        for attempt in range(self.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if attempt < self.max_attempts - 1:
                    delay = self.backoff_factor * (2 ** attempt)

                    if self.jitter:
                        delay *= random.uniform(0.5, 1.5)

                    await asyncio.sleep(delay)

        raise last_exception