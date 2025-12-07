"""
Request/Response Interceptors

Provides middleware for request/response processing.

Author: Agent 10 - API Client Consolidation Specialist
"""

from ..api_client_system import APIRequest


class RequestInterceptor:
    """Request/response interceptors."""

    @staticmethod
    async def log_requests(request: APIRequest, client) -> APIRequest:
        """Log outgoing requests."""
        client.logger.debug(f"Request: {request.method} {request.endpoint}")
        return request

    @staticmethod
    async def add_default_headers(request: APIRequest, client) -> APIRequest:
        """Add default headers."""
        headers = dict(request.headers) if request.headers else {}
        headers.setdefault("User-Agent", "MAMcrawler-API-Client/1.0")
        return APIRequest(
            method=request.method,
            endpoint=request.endpoint,
            params=request.params,
            data=request.data,
            json_data=request.json_data,
            headers=headers,
            timeout=request.timeout
        )