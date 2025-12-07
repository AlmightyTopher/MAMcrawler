"""
Basic HTTP Authentication Handler

Handles HTTP Basic authentication for APIs.

Author: Agent 10 - API Client Consolidation Specialist
"""

from typing import Dict, Any
from .base_auth import BaseAuthHandler
from ..api_client_system import APIRequest


class BasicAuthHandler(BaseAuthHandler):
    """
    Handles HTTP Basic authentication.
    """

    def __init__(self, auth_config: Dict[str, Any]):
        """
        Initialize basic authentication handler.

        Args:
            auth_config: Authentication configuration with:
                - username: Username for basic auth
                - password: Password for basic auth
        """
        super().__init__(auth_config)

        self.username = self.config.credentials.get('username', '')
        self.password = self.config.credentials.get('password', '')

        if not self.username or not self.password:
            raise ValueError("Username and password are required for basic authentication")

    async def authenticate_request(self, request: APIRequest) -> APIRequest:
        """
        Add basic authentication to the request.

        Args:
            request: The API request to authenticate

        Returns:
            The authenticated API request
        """
        return self._add_basic_auth(request, self.username, self.password)

    async def refresh_token(self) -> bool:
        """
        Basic auth doesn't need refreshing.

        Returns:
            False (no refresh needed)
        """
        return False