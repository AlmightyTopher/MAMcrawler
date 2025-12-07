"""
HTTPS Enforcement Utility

Ensures all external API communication uses HTTPS/TLS encryption.
Validates URLs, enforces protocol, and provides fallback strategies for development.
"""

import logging
from typing import Optional, Tuple
from urllib.parse import urlparse, urlunparse
import os

logger = logging.getLogger(__name__)


class HTTPSEnforcementError(Exception):
    """Raised when HTTPS enforcement is violated."""
    pass


class HTTPSEnforcer:
    """
    Enforces HTTPS for external API connections.

    Configuration:
    - ENFORCE_HTTPS=true (production) - blocks HTTP connections
    - ENFORCE_HTTPS=false (development) - allows localhost HTTP for testing

    Environment Variables:
    - ENFORCE_HTTPS: Boolean, enforce HTTPS for all external connections
    - ALLOW_LOCALHOST_HTTP: Boolean, allow http://localhost for development
    """

    def __init__(self, enforce: bool = True, allow_localhost: bool = False):
        """
        Initialize HTTPS enforcer.

        Args:
            enforce: If True, enforce HTTPS for all connections
            allow_localhost: If True, allow http://localhost for development
        """
        self.enforce = enforce
        self.allow_localhost = allow_localhost

        # Read from environment if not explicitly set
        if os.getenv("ENFORCE_HTTPS", "").lower() == "false":
            self.enforce = False
        if os.getenv("ALLOW_LOCALHOST_HTTP", "").lower() == "true":
            self.allow_localhost = True

        logger.info(
            f"HTTPS Enforcer initialized: "
            f"enforce={self.enforce}, allow_localhost={self.allow_localhost}"
        )

    def validate_url(self, url: str, service_name: str = "external") -> Tuple[bool, Optional[str]]:
        """
        Validate URL for HTTPS compliance.

        Args:
            url: URL to validate
            service_name: Name of service (for logging)

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url:
            return False, "URL cannot be empty"

        try:
            parsed = urlparse(url)
        except Exception as e:
            return False, f"Invalid URL format: {str(e)}"

        # Check protocol
        if parsed.scheme not in ["http", "https"]:
            return False, f"Invalid protocol '{parsed.scheme}'. Must be 'http' or 'https'"

        # HTTPS enforcement
        if self.enforce and parsed.scheme == "http":
            # Check if localhost exception applies
            is_localhost = parsed.hostname in ("localhost", "127.0.0.1", "0.0.0.0")

            if is_localhost and self.allow_localhost:
                logger.warning(
                    f"Allowing HTTP for localhost {service_name}: {url} "
                    "(development only, not for production)"
                )
                return True, None

            error_msg = (
                f"HTTPS enforcement enabled: {service_name} must use HTTPS. "
                f"Got: {url}"
            )
            return False, error_msg

        return True, None

    def enforce_url(self, url: str, service_name: str = "external") -> str:
        """
        Validate and return URL, raising exception if invalid.

        Args:
            url: URL to validate
            service_name: Name of service (for logging)

        Returns:
            Original URL if valid

        Raises:
            HTTPSEnforcementError: If URL violates HTTPS policy
        """
        is_valid, error = self.validate_url(url, service_name)

        if not is_valid:
            logger.error(f"HTTPS enforcement violation: {error}")
            raise HTTPSEnforcementError(error)

        return url

    def upgrade_to_https(self, url: str) -> str:
        """
        Attempt to upgrade HTTP URL to HTTPS.

        Args:
            url: URL to upgrade

        Returns:
            HTTPS URL if possible, original if already HTTPS
        """
        parsed = urlparse(url)

        if parsed.scheme == "https":
            return url

        if parsed.scheme == "http":
            # Upgrade to HTTPS
            https_url = urlunparse((
                "https",
                parsed.netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            logger.info(f"Upgraded URL from HTTP to HTTPS: {url} -> {https_url}")
            return https_url

        return url

    def get_secure_url(self, url: str, service_name: str = "external") -> str:
        """
        Get secure version of URL (upgraded to HTTPS if needed).

        Args:
            url: URL to secure
            service_name: Name of service (for logging)

        Returns:
            HTTPS URL

        Raises:
            HTTPSEnforcementError: If URL cannot be made secure
        """
        # First try to upgrade
        upgraded_url = self.upgrade_to_https(url)

        # Then validate
        return self.enforce_url(upgraded_url, service_name)


# Global enforcer instance
_enforcer: Optional[HTTPSEnforcer] = None


def get_https_enforcer() -> HTTPSEnforcer:
    """Get or create global HTTPS enforcer instance."""
    global _enforcer
    if _enforcer is None:
        # Production default: enforce HTTPS
        # Development: allow localhost HTTP
        is_production = os.getenv("ENVIRONMENT", "development") == "production"
        _enforcer = HTTPSEnforcer(
            enforce=is_production,
            allow_localhost=not is_production
        )
    return _enforcer


def validate_url(url: str, service_name: str = "external") -> Tuple[bool, Optional[str]]:
    """
    Validate URL using global enforcer.

    Args:
        url: URL to validate
        service_name: Name of service (for logging)

    Returns:
        Tuple of (is_valid, error_message)
    """
    enforcer = get_https_enforcer()
    return enforcer.validate_url(url, service_name)


def enforce_url(url: str, service_name: str = "external") -> str:
    """
    Enforce HTTPS on URL using global enforcer.

    Args:
        url: URL to enforce
        service_name: Name of service (for logging)

    Returns:
        Original URL if valid

    Raises:
        HTTPSEnforcementError: If URL violates HTTPS policy
    """
    enforcer = get_https_enforcer()
    return enforcer.enforce_url(url, service_name)


def get_secure_url(url: str, service_name: str = "external") -> str:
    """
    Get secure version of URL using global enforcer.

    Args:
        url: URL to secure
        service_name: Name of service (for logging)

    Returns:
        HTTPS URL
    """
    enforcer = get_https_enforcer()
    return enforcer.get_secure_url(url, service_name)
