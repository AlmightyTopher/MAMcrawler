"""
API Key Authentication Handler

Handles API key-based authentication for REST APIs.

Author: Agent 10 - API Client Consolidation Specialist
"""

from typing import Dict, Any, Optional
from .base_auth import BaseAuthHandler
from ..api_client_system import APIRequest


class APIKeyAuthHandler(BaseAuthHandler):
    """
    Handles API key authentication.

    Supports various API key authentication methods:
    - Header-based API keys (X-API-Key, Authorization, etc.)
    - Query parameter API keys
    - Custom header names
    """

    def __init__(self, auth_config: Dict[str, Any]):
        """
        Initialize API key authentication handler.

        Args:
            auth_config: Authentication configuration with:
                - api_key: The API key value
                - header_name: Header name to use (default: "X-API-Key")
                - query_param: Query parameter name (optional)
                - send_in: Where to send the key ("header" or "query", default: "header")
        """
        super().__init__(auth_config)

        self.api_key = self.config.credentials.get('api_key', '')
        self.header_name = self.config.credentials.get('header_name', 'X-API-Key')
        self.query_param = self.config.credentials.get('query_param')
        self.send_in = self.config.credentials.get('send_in', 'header')

        if not self.api_key:
            raise ValueError("API key is required for API key authentication")

    async def authenticate_request(self, request: APIRequest) -> APIRequest:
        """
        Add API key authentication to the request.

        Args:
            request: The API request to authenticate

        Returns:
            The authenticated API request
        """
        if self.send_in == 'header':
            return self._add_api_key_header(request, self.api_key, self.header_name)
        elif self.send_in == 'query':
            param_name = self.query_param or 'api_key'
            return self._add_query_param(request, param_name, self.api_key)
        else:
            raise ValueError(f"Unsupported send_in method: {self.send_in}")

    async def refresh_token(self) -> bool:
        """
        API keys don't need refreshing.

        Returns:
            False (no refresh needed)
        """
        return False