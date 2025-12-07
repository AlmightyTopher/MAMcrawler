"""
JWT/Bearer Token Authentication Handler

Handles JWT and Bearer token authentication for APIs.

Author: Agent 10 - API Client Consolidation Specialist
"""

import time
from typing import Dict, Any, Optional
from .base_auth import BaseAuthHandler
from ..api_client_system import APIRequest


class JWTAuthHandler(BaseAuthHandler):
    """
    Handles JWT and Bearer token authentication.

    Supports static tokens and token refresh mechanisms.
    """

    def __init__(self, auth_config: Dict[str, Any]):
        """
        Initialize JWT authentication handler.

        Args:
            auth_config: Authentication configuration with:
                - token: Static JWT token (optional if refresh_url provided)
                - refresh_url: URL to refresh tokens (optional)
                - refresh_data: Data to send for token refresh (optional)
                - token_field: Field name containing token in refresh response (default: "access_token")
                - expires_field: Field name containing expiration in refresh response (optional)
                - token_prefix: Prefix for Authorization header (default: "Bearer")
        """
        super().__init__(auth_config)

        self.static_token = self.config.credentials.get('token')
        self.refresh_url = self.config.credentials.get('refresh_url')
        self.refresh_data = self.config.credentials.get('refresh_data', {})
        self.token_field = self.config.credentials.get('token_field', 'access_token')
        self.expires_field = self.config.credentials.get('expires_field')
        self.token_prefix = self.config.credentials.get('token_prefix', 'Bearer')

        # Initialize token state
        if self.static_token:
            self._cached_token = self.static_token
            # Assume static tokens don't expire
            self._token_expires_at = None

    async def authenticate_request(self, request: APIRequest) -> APIRequest:
        """
        Add JWT/Bearer token authentication to the request.

        Args:
            request: The API request to authenticate

        Returns:
            The authenticated API request
        """
        await self._ensure_valid_token()

        if not self._cached_token:
            raise ValueError("No valid token available for authentication")

        return self._add_bearer_token(request, self._cached_token)

    async def refresh_token(self) -> bool:
        """
        Refresh the JWT token if refresh URL is configured.

        Returns:
            True if token was refreshed, False otherwise
        """
        if not self.refresh_url:
            return False

        try:
            # Import here to avoid circular imports
            from ..api_client_system import APIClientConfig, APIClientBase
            from ..api_clients.rest_client import RESTAPIClient

            # Create a temporary client for token refresh
            # Use a minimal config without auth to avoid recursion
            temp_config = APIClientConfig(
                base_url=self.refresh_url.split('/')[0] + '//' + self.refresh_url.split('/')[2],
                timeout=30,
                enable_metrics=False,
                enable_circuit_breaker=False
            )

            async with RESTAPIClient(temp_config) as client:
                # Make refresh request
                refresh_request = APIRequest(
                    method="POST",
                    endpoint=self.refresh_url.split('/', 3)[-1] if '/' in self.refresh_url[8:] else '',
                    json_data=self.refresh_data
                )

                response = await client._make_request(refresh_request)

                if response.success and response.data:
                    # Extract new token
                    new_token = response.data.get(self.token_field)
                    if new_token:
                        self._cached_token = new_token

                        # Extract expiration if provided
                        if self.expires_field and self.expires_field in response.data:
                            expires_in = response.data[self.expires_field]
                            if isinstance(expires_in, (int, float)):
                                self._token_expires_at = time.time() + expires_in
                            else:
                                # Assume static token doesn't expire
                                self._token_expires_at = None

                        return True

        except Exception as e:
            # Log error but don't raise - let caller handle
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to refresh JWT token: {e}")

        return False