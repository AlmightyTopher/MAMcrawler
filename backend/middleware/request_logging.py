"""
API Request Logging Middleware
Logs all incoming requests and response metrics to database
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models.api_log import ApiLog

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all API requests to the database

    Captures:
        - Request method, path, query params
        - Response status code and time
        - Client user agent and IP
        - Error messages for failed requests
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log to database

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response from route handler
        """
        start_time = time.time()

        # Extract request info
        method = request.method
        path = request.url.path
        query_params = str(request.query_params) if request.query_params else None
        user_agent = request.headers.get("user-agent", "")[:500]
        ip_address = self._get_client_ip(request)

        # Initialize response variables
        status_code = 500
        error_message = None
        response_size = 0

        try:
            # Call the actual route handler
            response = await call_next(request)
            status_code = response.status_code

            # Try to get response size from content-length header
            content_length = response.headers.get("content-length")
            if content_length:
                response_size = int(content_length)

            return response

        except Exception as e:
            error_message = str(e)[:1000]  # Limit error message length
            logger.exception(f"Request error: {method} {path}")
            raise

        finally:
            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000

            # Log to database (non-blocking)
            try:
                await self._log_request(
                    method=method,
                    path=path,
                    query_params=query_params,
                    status_code=status_code,
                    response_time_ms=response_time_ms,
                    response_size=response_size,
                    user_agent=user_agent,
                    ip_address=ip_address,
                    error_message=error_message
                )
            except Exception as log_error:
                # Don't let logging errors affect the request
                logger.error(f"Failed to log request: {log_error}")

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP from request, handling proxies

        Args:
            request: Incoming request

        Returns:
            Client IP address
        """
        # Check for forwarded headers (behind proxy/load balancer)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Get first IP in chain (original client)
            return forwarded_for.split(",")[0].strip()

        # Check for real IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"

    async def _log_request(
        self,
        method: str,
        path: str,
        query_params: str,
        status_code: int,
        response_time_ms: float,
        response_size: int,
        user_agent: str,
        ip_address: str,
        error_message: str = None
    ) -> None:
        """
        Save request log to database

        Args:
            method: HTTP method
            path: Request path
            query_params: Query string
            status_code: Response status code
            response_time_ms: Response time in milliseconds
            response_size: Response size in bytes
            user_agent: Client user agent
            ip_address: Client IP
            error_message: Error message if failed
        """
        # Skip logging for certain paths
        skip_paths = ["/health", "/metrics", "/docs", "/openapi.json", "/favicon.ico"]
        if any(path.startswith(skip) for skip in skip_paths):
            return

        db: Session = SessionLocal()
        try:
            log_entry = ApiLog(
                method=method,
                path=path,
                query_params=query_params,
                status_code=status_code,
                response_time_ms=round(response_time_ms, 2),
                response_size=response_size,
                user_agent=user_agent,
                ip_address=ip_address,
                error_message=error_message
            )
            db.add(log_entry)
            db.commit()

            # Log slow requests
            if response_time_ms > 1000:
                logger.warning(
                    f"Slow request: {method} {path} took {response_time_ms:.2f}ms"
                )

        except Exception as e:
            db.rollback()
            logger.error(f"Error saving API log: {e}")
        finally:
            db.close()
