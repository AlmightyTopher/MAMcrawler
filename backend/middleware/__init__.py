"""
Middleware Package
FastAPI middleware components for request processing
"""

from backend.middleware.request_logging import RequestLoggingMiddleware

__all__ = [
    "RequestLoggingMiddleware",
]
