"""
REST API Client

Provides a comprehensive REST API client with automatic retry, rate limiting,
and error handling.

Author: Agent 10 - API Client Consolidation Specialist
"""

import aiohttp
from aiohttp import ClientTimeout
from typing import Optional
from ..api_client_system import APIClientBase, APIClientConfig, APIRequest, APIResponse


class RESTAPIClient(APIClientBase):
    """
    REST API client implementation.

    Supports all standard HTTP methods with automatic retry, rate limiting,
    and comprehensive error handling.
    """

    def __init__(self, config: APIClientConfig):
        super().__init__(config)
        self.session: Optional[aiohttp.ClientSession] = None

    async def _initialize_session(self):
        """Initialize aiohttp session."""
        self.session = aiohttp.ClientSession(
            timeout=ClientTimeout(total=self.config.timeout),
            headers=self.config.headers
        )

    async def _close_session(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None

    async def _make_request(self, request: APIRequest) -> APIResponse:
        """Make HTTP request."""
        if not self.session:
            await self._initialize_session()

        url = f"{self.config.base_url.rstrip('/')}{request.endpoint}"
        start_time = __import__('time').time()

        try:
            async with self.session.request(
                request.method,
                url,
                params=request.params,
                data=request.data,
                json=request.json_data,
                headers=request.headers,
                timeout=request.timeout
            ) as response:
                # Read response
                if response.status == 204:  # No Content
                    data = None
                else:
                    try:
                        data = await response.json()
                    except:
                        data = await response.text()

                api_response = APIResponse(
                    status_code=response.status,
                    headers=dict(response.headers),
                    data=data,
                    request_time=__import__('time').time() - start_time,
                    success=response.status < 400,
                    error_message=None if response.status < 400 else str(data)
                )

                return api_response

        except Exception as e:
            return APIResponse(
                status_code=0,
                headers={},
                data=None,
                request_time=__import__('time').time() - start_time,
                success=False,
                error_message=str(e)
            )

    # Convenience methods
    async def get(self, endpoint: str, **kwargs) -> APIResponse:
        """GET request."""
        return await self.request(APIRequest("GET", endpoint, **kwargs))

    async def post(self, endpoint: str, **kwargs) -> APIResponse:
        """POST request."""
        return await self.request(APIRequest("POST", endpoint, **kwargs))

    async def put(self, endpoint: str, **kwargs) -> APIResponse:
        """PUT request."""
        return await self.request(APIRequest("PUT", endpoint, **kwargs))

    async def patch(self, endpoint: str, **kwargs) -> APIResponse:
        """PATCH request."""
        return await self.request(APIRequest("PATCH", endpoint, **kwargs))

    async def delete(self, endpoint: str, **kwargs) -> APIResponse:
        """DELETE request."""
        return await self.request(APIRequest("DELETE", endpoint, **kwargs))