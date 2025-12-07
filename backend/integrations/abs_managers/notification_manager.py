"""
Audiobookshelf Notification Management

Manages notifications and notification settings.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class NotificationManager:
    """
    Manager for Audiobookshelf notification operations.

    Encapsulates all notification-related operations including:
    - Notification creation and deletion
    - Notification retrieval and updates
    - Notification read status management
    - Notification settings

    Args:
        client: Reference to AudiobookshelfClient for making requests
    """

    def __init__(self, client):
        """Initialize notification manager with client reference."""
        self.client = client

    async def create_notification(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new notification.

        Args:
            notification_data: Notification configuration data

        Returns:
            Created notification data

        Example:
            >>> notification = await client.notifications.create_notification({
            ...     "title": "Download Complete",
            ...     "message": "Your book has finished downloading",
            ...     "type": "info"
            ... })
        """
        logger.info("Creating notification")

        try:
            result = await self.client._request("POST", "/api/notifications", json=notification_data)
            logger.info("Successfully created notification")
            return result
        except Exception as e:
            logger.error(f"Failed to create notification: {str(e)}")
            raise

    async def get_notifications(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get notifications.

        Args:
            limit: Maximum number of notifications to return

        Returns:
            List of notification data

        Example:
            >>> notifications = await client.notifications.get_notifications(limit=20)
            >>> print(f"Found {len(notifications)} notifications")
        """
        logger.info(f"Getting notifications (limit: {limit})")

        try:
            response = await self.client._request("GET", "/api/notifications", params={"limit": limit})
            notifications = response.get("notifications", [])
            logger.info(f"Found {len(notifications)} notifications")
            return notifications
        except Exception as e:
            logger.error(f"Failed to get notifications: {str(e)}")
            raise

    async def get_notification(self, notification_id: str) -> Dict[str, Any]:
        """
        Get a specific notification by ID.

        Args:
            notification_id: Notification ID

        Returns:
            Notification data

        Example:
            >>> notification = await client.notifications.get_notification("notif123")
        """
        logger.info(f"Getting notification: {notification_id}")

        try:
            result = await self.client._request("GET", f"/api/notifications/{notification_id}")
            logger.info(f"Successfully retrieved notification {notification_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to get notification {notification_id}: {str(e)}")
            raise

    async def update_notification(self, notification_id: str, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a notification.

        Args:
            notification_id: Notification ID
            notification_data: Updated notification data

        Returns:
            Updated notification data

        Example:
            >>> await client.notifications.update_notification("notif123", {"read": True})
        """
        logger.info(f"Updating notification: {notification_id}")

        try:
            result = await self.client._request("PATCH", f"/api/notifications/{notification_id}", json=notification_data)
            logger.info(f"Successfully updated notification {notification_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to update notification {notification_id}: {str(e)}")
            raise

    async def delete_notification(self, notification_id: str) -> bool:
        """
        Delete a notification.

        Args:
            notification_id: Notification ID to delete

        Returns:
            True if successful

        Example:
            >>> await client.notifications.delete_notification("notif123")
        """
        logger.info(f"Deleting notification: {notification_id}")

        try:
            await self.client._request("DELETE", f"/api/notifications/{notification_id}")
            logger.info(f"Successfully deleted notification {notification_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete notification {notification_id}: {str(e)}")
            raise

    async def mark_notification_read(self, notification_id: str) -> Dict[str, Any]:
        """
        Mark a notification as read.

        Args:
            notification_id: Notification ID

        Returns:
            Updated notification data

        Example:
            >>> await client.notifications.mark_notification_read("notif123")
        """
        logger.info(f"Marking notification as read: {notification_id}")

        try:
            result = await self.client._request("POST", f"/api/notifications/{notification_id}/read")
            logger.info(f"Successfully marked notification {notification_id} as read")
            return result
        except Exception as e:
            logger.error(f"Failed to mark notification {notification_id} as read: {str(e)}")
            raise

    async def mark_all_notifications_read(self) -> Dict[str, Any]:
        """
        Mark all notifications as read.

        Returns:
            Result data

        Example:
            >>> await client.notifications.mark_all_notifications_read()
        """
        logger.info("Marking all notifications as read")

        try:
            result = await self.client._request("POST", "/api/notifications/read-all")
            logger.info("Successfully marked all notifications as read")
            return result
        except Exception as e:
            logger.error(f"Failed to mark all notifications as read: {str(e)}")
            raise

    async def get_notification_settings(self) -> Dict[str, Any]:
        """
        Get notification settings.

        Returns:
            Notification settings data

        Example:
            >>> settings = await client.notifications.get_notification_settings()
        """
        logger.info("Getting notification settings")

        try:
            result = await self.client._request("GET", "/api/notifications/settings")
            logger.info("Successfully retrieved notification settings")
            return result
        except Exception as e:
            logger.error(f"Failed to get notification settings: {str(e)}")
            raise
