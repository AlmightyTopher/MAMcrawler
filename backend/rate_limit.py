"""
Rate Limiting Configuration for FastAPI Application

This module provides rate limiting for API endpoints to prevent:
- Abuse and denial-of-service attacks
- Excessive API usage
- Resource exhaustion
- Unfair usage patterns

Implementation uses slowapi (https://github.com/laurentS/slowapi)
which wraps the limits library.

Usage:
    from backend.rate_limit import limiter

    @app.get("/api/endpoint")
    @limiter.limit("10/minute")
    async def my_endpoint(request: Request):
        return {"message": "success"}
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Initialize the limiter with get_remote_address as key function
# This uses the client's IP address to track rate limits
limiter = Limiter(key_func=get_remote_address)

# ============================================================================
# Rate Limit Definitions by Endpoint Type
# ============================================================================
# Format: "requests/time_period"
# Examples: "10/minute", "100/hour", "1000/day"

RATE_LIMITS = {
    # Public endpoints - strict limits
    "public": "10/minute",

    # Authenticated endpoints - more generous
    "authenticated": "60/minute",

    # Admin endpoints - very generous
    "admin": "1000/minute",

    # Download operations - limited to prevent abuse
    "download": "20/hour",

    # Metadata queries - limited due to external API calls
    "metadata": "30/minute",

    # Search operations - limited
    "search": "20/minute",

    # Status/health checks - very generous (frequent checks expected)
    "health": "100/minute",

    # File upload - limited
    "upload": "5/minute",
}


def add_rate_limiting(app: FastAPI) -> None:
    """
    Configure and attach rate limiting to a FastAPI application

    Args:
        app: FastAPI application instance

    Raises:
        RateLimitExceeded: When rate limit is exceeded
    """

    # Attach the limiter to the app state for access in routes
    app.state.limiter = limiter

    # Register exception handler for rate limit exceeded errors
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        """
        Handle rate limit exceeded exceptions

        Returns a 429 (Too Many Requests) response with retry information
        """
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please try again later.",
                "detail": str(exc.detail),
                "retry_after": exc.retry_after if hasattr(exc, 'retry_after') else 60,
                "timestamp": datetime.utcnow().isoformat()
            },
            headers={
                "Retry-After": str(exc.retry_after) if hasattr(exc, 'retry_after') else "60"
            }
        )

    logger.info("Rate limiting configured successfully")


# ============================================================================
# Helper Functions for Common Rate Limit Scenarios
# ============================================================================

def get_rate_limit(endpoint_type: str = "authenticated") -> str:
    """
    Get the rate limit string for a given endpoint type

    Args:
        endpoint_type: Type of endpoint (public, authenticated, admin, etc.)

    Returns:
        Rate limit string (e.g., "10/minute")
    """
    return RATE_LIMITS.get(endpoint_type, RATE_LIMITS["authenticated"])


def create_custom_limit(requests: int, time_period: str) -> str:
    """
    Create a custom rate limit string

    Args:
        requests: Number of requests allowed
        time_period: Time period (second, minute, hour, day)

    Returns:
        Rate limit string

    Example:
        limit = create_custom_limit(5, "minute")  # "5/minute"
    """
    valid_periods = ["second", "minute", "hour", "day"]
    if time_period not in valid_periods:
        raise ValueError(f"Time period must be one of: {valid_periods}")

    return f"{requests}/{time_period}"
