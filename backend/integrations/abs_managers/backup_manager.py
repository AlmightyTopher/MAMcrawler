"""
Audiobookshelf Backup Management

Manages backup creation, listing, and execution.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class BackupManager:
    """
    Manager for Audiobookshelf backup operations.

    Encapsulates all backup-related operations including:
    - Backup creation and deletion
    - Backup retrieval and updates
    - Backup execution

    Args:
        client: Reference to AudiobookshelfClient for making requests
    """

    def __init__(self, client):
        """Initialize backup manager with client reference."""
        self.client = client

    async def create_backup(self, backup_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new backup.

        Args:
            backup_data: Backup configuration data

        Returns:
            Backup creation result

        Example:
            >>> backup = await client.backups.create_backup({"name": "Daily Backup"})
        """
        logger.info("Creating backup")

        try:
            result = await self.client._request("POST", "/api/backups", json=backup_data)
            logger.info("Successfully created backup")
            return result
        except Exception as e:
            logger.error(f"Failed to create backup: {str(e)}")
            raise

    async def get_backups(self) -> List[Dict[str, Any]]:
        """
        Get all backups.

        Returns:
            List of backup data

        Example:

            >>> backups = await client.backups.get_backups()
            >>> print(f"Found {len(backups)} backups")
        """
        logger.info("Getting backups")

        try:
            response = await self.client._request("GET", "/api/backups")
            backups = response.get("backups", [])
            logger.info(f"Found {len(backups)} backups")
            return backups
        except Exception as e:
            logger.error(f"Failed to get backups: {str(e)}")
            raise

    async def get_backup(self, backup_id: str) -> Dict[str, Any]:
        """
        Get a specific backup by ID.

        Args:
            backup_id: Backup ID

        Returns:
            Backup data

        Example:
            >>> backup = await client.backups.get_backup("backup123")
        """
        logger.info(f"Getting backup: {backup_id}")

        try:
            result = await self.client._request("GET", f"/api/backups/{backup_id}")
            logger.info(f"Successfully retrieved backup {backup_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to get backup {backup_id}: {str(e)}")
            raise

    async def update_backup(self, backup_id: str, backup_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a backup.

        Args:
            backup_id: Backup ID
            backup_data: Updated backup data

        Returns:
            Updated backup data

        Example:
            >>> await client.backups.update_backup("backup123", {"name": "New Name"})
        """
        logger.info(f"Updating backup: {backup_id}")

        try:
            result = await self.client._request("PATCH", f"/api/backups/{backup_id}", json=backup_data)
            logger.info(f"Successfully updated backup {backup_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to update backup {backup_id}: {str(e)}")
            raise

    async def delete_backup(self, backup_id: str) -> bool:
        """
        Delete a backup.

        Args:
            backup_id: Backup ID to delete

        Returns:
            True if successful

        Example:
            >>> await client.backups.delete_backup("backup123")
        """
        logger.info(f"Deleting backup: {backup_id}")

        try:
            await self.client._request("DELETE", f"/api/backups/{backup_id}")
            logger.info(f"Successfully deleted backup {backup_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete backup {backup_id}: {str(e)}")
            raise

    async def run_backup(self, backup_id: str) -> Dict[str, Any]:
        """
        Run a backup.

        Args:
            backup_id: Backup ID to run

        Returns:
            Backup execution result

        Example:
            >>> result = await client.backups.run_backup("backup123")
        """
        logger.info(f"Running backup: {backup_id}")

        try:
            result = await self.client._request("POST", f"/api/backups/{backup_id}/run")
            logger.info(f"Successfully started backup {backup_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to run backup {backup_id}: {str(e)}")
            raise
