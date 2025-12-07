"""
Audiobookshelf User Management

Manages user profile, settings, permissions, and password changes.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class UserManager:
    """
    Manager for Audiobookshelf user operations.

    Encapsulates all user-related operations including:
    - User profile management
    - User settings management
    - User statistics and permissions
    - Password changes

    Args:
        client: Reference to AudiobookshelfClient for making requests
    """

    def __init__(self, client):
        """Initialize user manager with client reference."""
        self.client = client

    async def get_user_profile(self) -> Dict[str, Any]:
        """
        Get current user profile information.

        Returns:
            User profile data

        Example:
            >>> profile = await client.users.get_user_profile()
            >>> print(f"Username: {profile.get('username')}")
        """
        logger.info("Getting user profile")

        try:
            result = await self.client._request("GET", "/me")
            logger.info("Successfully retrieved user profile")
            return result
        except Exception as e:
            logger.error(f"Failed to get user profile: {str(e)}")
            raise

    async def update_user_profile(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update current user profile.

        Args:
            profile_data: Profile fields to update

        Returns:
            Updated profile data

        Example:
            >>> await client.users.update_user_profile({"username": "newname"})
        """
        logger.info("Updating user profile")

        try:
            result = await self.client._request("PATCH", "/me", json=profile_data)
            logger.info("Successfully updated user profile")
            return result
        except Exception as e:
            logger.error(f"Failed to update user profile: {str(e)}")
            raise

    async def get_user_settings(self) -> Dict[str, Any]:
        """
        Get current user settings.

        Returns:
            User settings data

        Example:
            >>> settings = await client.users.get_user_settings()
        """
        logger.info("Getting user settings")

        try:
            result = await self.client._request("GET", "/me/settings")
            logger.info("Successfully retrieved user settings")
            return result
        except Exception as e:
            logger.error(f"Failed to get user settings: {str(e)}")
            raise

    async def update_user_settings(self, settings_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update current user settings.

        Args:
            settings_data: Settings fields to update

        Returns:
            Updated settings data

        Example:
            >>> await client.users.update_user_settings({"playbackRate": 1.25})
        """
        logger.info("Updating user settings")

        try:
            result = await self.client._request("PATCH", "/me/settings", json=settings_data)
            logger.info("Successfully updated user settings")
            return result
        except Exception as e:
            logger.error(f"Failed to update user settings: {str(e)}")
            raise

    async def get_user_stats(self) -> Dict[str, Any]:
        """
        Get current user statistics.

        Returns:
            User statistics data

        Example:
            >>> stats = await client.users.get_user_stats()
            >>> print(f"Books completed: {stats.get('booksCompleted', 0)}")
        """
        logger.info("Getting user stats")

        try:
            result = await self.client._request("GET", "/me/stats")
            logger.info("Successfully retrieved user stats")
            return result
        except Exception as e:
            logger.error(f"Failed to get user stats: {str(e)}")
            raise

    async def get_user_permissions(self) -> Dict[str, Any]:
        """
        Get current user permissions.

        Returns:
            User permissions data

        Example:
            >>> permissions = await client.users.get_user_permissions()
        """
        logger.info("Getting user permissions")

        try:
            result = await self.client._request("GET", "/me/permissions")
            logger.info("Successfully retrieved user permissions")
            return result
        except Exception as e:
            logger.error(f"Failed to get user permissions: {str(e)}")
            raise

    async def change_password(self, current_password: str, new_password: str) -> bool:
        """
        Change current user password.

        Args:
            current_password: Current password
            new_password: New password

        Returns:
            True if successful

        Example:
            >>> await client.users.change_password("oldpass", "newpass")
        """
        logger.info("Changing user password")

        payload = {
            "currentPassword": current_password,
            "newPassword": new_password,
        }

        try:
            await self.client._request("PATCH", "/me/password", json=payload)
            logger.info("Successfully changed password")
            return True
        except Exception as e:
            logger.error(f"Failed to change password: {str(e)}")
            raise
