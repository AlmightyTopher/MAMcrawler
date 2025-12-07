"""
Audiobookshelf Email Management

Manages email sending and email settings configuration.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class EmailManager:
    """
    Manager for Audiobookshelf email operations.

    Encapsulates all email-related operations including:
    - Email sending
    - Email settings management
    - Email settings testing

    Args:
        client: Reference to AudiobookshelfClient for making requests
    """

    def __init__(self, client):
        """Initialize email manager with client reference."""
        self.client = client

    async def send_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send an email.

        Args:
            email_data: Email configuration data

        Returns:
            Email send result

        Example:
            >>> result = await client.email.send_email({
            ...     "to": "user@example.com",
            ...     "subject": "Test Email",
            ...     "body": "Hello World!"
            ... })
        """
        logger.info("Sending email")

        try:
            result = await self.client._request("POST", "/api/email", json=email_data)
            logger.info("Successfully sent email")
            return result
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            raise

    async def get_email_settings(self) -> Dict[str, Any]:
        """
        Get email settings.

        Returns:
            Email settings data

        Example:
            >>> settings = await client.email.get_email_settings()
        """
        logger.info("Getting email settings")

        try:
            result = await self.client._request("GET", "/api/email/settings")
            logger.info("Successfully retrieved email settings")
            return result
        except Exception as e:
            logger.error(f"Failed to get email settings: {str(e)}")
            raise

    async def update_email_settings(self, settings_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update email settings.

        Args:
            settings_data: Email settings data

        Returns:
            Updated email settings

        Example:
            >>> await client.email.update_email_settings({"smtp_host": "smtp.example.com"})
        """
        logger.info("Updating email settings")

        try:
            result = await self.client._request("PATCH", "/api/email/settings", json=settings_data)
            logger.info("Successfully updated email settings")
            return result
        except Exception as e:
            logger.error(f"Failed to update email settings: {str(e)}")
            raise

    async def test_email_settings(self) -> Dict[str, Any]:
        """
        Test email settings by sending a test email.

        Returns:
            Test result data

        Example:
            >>> result = await client.email.test_email_settings()
        """
        logger.info("Testing email settings")

        try:
            result = await self.client._request("POST", "/api/email/test")
            logger.info("Successfully tested email settings")
            return result
        except Exception as e:
            logger.error(f"Failed to test email settings: {str(e)}")
            raise
