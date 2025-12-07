"""
Base Authentication Handler

Provides the foundation for all authentication handlers in the unified API client system.

Author: Agent 10 - API Client Consolidation Specialist
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from ..api_client_system import APIRequest


@dataclass
class AuthConfig:
    """Configuration for authentication."""
    type: str
    credentials: Dict[str, Any]
    options: Optional[Dict[str, Any]] = None


class BaseAuthHandler(ABC):
    """
    Base class for all authentication handlers.

    Provides common functionality and defines the interface that all
    authentication handlers must implement.
    """

    def __init__(self, auth_config: Dict[str, Any]):
        """
        Initialize the authentication handler.

        Args:
            auth_config: Authentication configuration dictionary
        """
        self.config = AuthConfig(
            type=auth_config.get('type', ''),
            credentials=auth_config.get('credentials', {}),
            options=auth_config.get('options', {})
        )
        self._cached_token: Optional[str] = None
        self._token_expires_at: Optional[float] = None

    @abstractmethod
    async def authenticate_request(self, request: APIRequest) -> APIRequest:
        """
        Apply authentication to an API request.

        Args:
            request: The API request to authenticate

        Returns:
            The authenticated API request
        """
        pass

    @abstractmethod
    async def refresh_token(self) -> bool:
        """
        Refresh authentication token if needed.

        Returns:
            True if token was refreshed, False otherwise
        """
        pass

    def is_token_expired(self) -> bool:
        """
        Check if the current token is expired.

        Returns:
            True if token is expired or will expire soon
        """
        if not self._token_expires_at:
            return False

        # Consider token expired if it expires within 5 minutes
        import time
        return time.time() > (self._token_expires_at - 300)

    async def _ensure_valid_token(self):
        """Ensure we have a valid token, refreshing if necessary."""
        if self.is_token_expired():
            await self.refresh_token()

    def _add_header(self, request: APIRequest, header_name: str, header_value: str) -> APIRequest:
        """Add a header to the request."""
        headers = dict(request.headers) if request.headers else {}
        headers[header_name] = header_value
        return APIRequest(
            method=request.method,
            endpoint=request.endpoint,
            params=request.params,
            data=request.data,
            json_data=request.json_data,
            headers=headers,
            timeout=request.timeout
        )

    def _add_bearer_token(self, request: APIRequest, token: str) -> APIRequest:
        """Add Bearer token authorization header."""
        return self._add_header(request, "Authorization", f"Bearer {token}")

    def _add_api_key_header(self, request: APIRequest, api_key: str, header_name: str = "X-API-Key") -> APIRequest:
        """Add API key header."""
        return self._add_header(request, header_name, api_key)

    def _add_basic_auth(self, request: APIRequest, username: str, password: str) -> APIRequest:
        """Add basic authentication header."""
        import base64
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        return self._add_header(request, "Authorization", f"Basic {credentials}")

    def _add_query_param(self, request: APIRequest, param_name: str, param_value: str) -> APIRequest:
        """Add a query parameter to the request."""
        params = dict(request.params) if request.params else {}
        params[param_name] = param_value
        return APIRequest(
            method=request.method,
            endpoint=request.endpoint,
            params=params,
            data=request.data,
            json_data=request.json_data,
            headers=request.headers,
            timeout=request.timeout
        )