"""
Audiobookshelf API Key Management

Manages API key creation, updates, and deletion.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class APIKeyManager:
    """
    Manager for Audiobookshelf API key operations.

    Encapsulates all API key-related operations including:
    - API key creation and deletion
    - API key retrieval and updates

    Args:
        client: Reference to AudiobookshelfClient for making requests
    """

    def __init__(self, client):
        """Initialize API key manager with client reference."""
        self.client = client

    async def create_api_key(self, key_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new API key.

        Args:
            key_data: API key configuration data

        Returns:
            Created API key data

        Example:
            >>> key = await client.api_keys.create_api_key({
            ...     "name": "My App",
            ...     "permissions": ["read", "write"]
            ... })
        """
        logger.info("Creating API key")

        try:
            result = await self.client._request("POST", "/api/keys", json=key_data)
            logger.info("Successfully created API key")
            return result
        except Exception as e:
            logger.error(f"Failed to create API key: {str(e)}")
            raise

    async def get_api_keys(self) -> List[Dict[str, Any]]:
        """
        Get all API keys.

        Returns:
            List of API key data

        Example:
            >>> keys = await client.api_keys.get_api_keys()
            >>> print(f"Found {len(keys)} API keys")
        """
        logger.info("Getting API keys")

        try:
            response = await self.client._request("GET", "/api/keys")
            keys = response.get("keys", [])
            logger.info(f"Found {len(keys)} API keys")
            return keys
        except Exception as e:
            logger.error(f"Failed to get API keys: {str(e)}")
            raise

    async def update_api_key(self, key_id: str, key_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an API key.

        Args:
            key_id: API key ID
            key_data: Updated key data

        Returns:
            Updated API key data

        Example:
            >>> await client.api_keys.update_api_key("key123", {"name": "New Name"})
        """
        logger.info(f"Updating API key: {key_id}")

        try:
            result = await self.client._request("PATCH", f"/api/keys/{key_id}", json=key_data)
            logger.info(f"Successfully updated API key {key_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to update API key {key_id}: {str(e)}")
            raise

    async def delete_api_key(self, key_id: str) -> bool:
        """
        Delete an API key.

        Args:
            key_id: API key ID to delete

        Returns:
            True if successful

        Example:
            >>> await client.api_keys.delete_api_key("key123")
        """
        logger.info(f"Deleting API key: {key_id}")

        try:
            await self.client._request("DELETE", f"/api/keys/{key_id}")
            logger.info(f"Successfully deleted API key {key_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete API key {key_id}: {str(e)}")
            raise
