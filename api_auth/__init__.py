"""
API Authentication Handlers

Provides unified authentication handling for various API authentication methods:
- API Key authentication
- OAuth 2.0 / OAuth 1.0
- JWT Bearer tokens
- Basic HTTP authentication
- Custom authentication schemes

Author: Agent 10 - API Client Consolidation Specialist
"""

from .base_auth import BaseAuthHandler, AuthConfig
from .api_key_auth import APIKeyAuthHandler
from .oauth_auth import OAuthAuthHandler
from .jwt_auth import JWTAuthHandler
from .basic_auth import BasicAuthHandler

__all__ = [
    'BaseAuthHandler',
    'AuthConfig',
    'APIKeyAuthHandler',
    'OAuthAuthHandler',
    'JWTAuthHandler',
    'BasicAuthHandler',
    'get_auth_handler',
]


def get_auth_handler(auth_config: dict) -> BaseAuthHandler:
    """
    Factory function to create appropriate auth handler based on config.

    Args:
        auth_config: Authentication configuration dictionary

    Returns:
        Appropriate authentication handler instance

    Raises:
        ValueError: If auth type is not supported
    """
    auth_type = auth_config.get('type', '').lower()

    handlers = {
        'api_key': APIKeyAuthHandler,
        'oauth': OAuthAuthHandler,
        'oauth2': OAuthAuthHandler,
        'jwt': JWTAuthHandler,
        'bearer': JWTAuthHandler,  # JWT with Bearer prefix
        'basic': BasicAuthHandler,
    }

    handler_class = handlers.get(auth_type)
    if not handler_class:
        raise ValueError(f"Unsupported authentication type: {auth_type}")

    return handler_class(auth_config)