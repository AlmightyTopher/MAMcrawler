"""
Audiobookshelf Playlist Management

Manages playlists and playlist membership operations.
"""

import logging
from typing import Any, Dict, List, Optional

from backend.integrations.patterns.batch_operations import BatchOperationsMixin

logger = logging.getLogger(__name__)


class PlaylistManager(BatchOperationsMixin):
    """
    Manager for Audiobookshelf playlist operations.

    Encapsulates all playlist-related operations including:
    - Playlist CRUD operations
    - Adding/removing items from playlists
    - Batch operations on playlists
    - Creating playlists from collections

    Args:
        client: Reference to AudiobookshelfClient for making requests
    """

    def __init__(self, client):
        """Initialize playlist manager with client reference."""
        self.client = client

    async def create_playlist(
        self,
        name: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new playlist.

        Args:
            name: Playlist name
            description: Optional playlist description

        Returns:
            Created playlist data

        Example:
            >>> playlist = await client.playlists.create_playlist("My Playlist", "Curated selection")
        """
        logger.info(f"Creating playlist: {name}")

        payload = {"name": name}
        if description:
            payload["description"] = description

        try:
            result = await self.client._request("POST", "/api/playlists", json=payload)
            logger.info(f"Successfully created playlist: {name}")
            return result
        except Exception as e:
            logger.error(f"Failed to create playlist {name}: {str(e)}")
            raise

    async def get_playlists(self) -> List[Dict[str, Any]]:
        """
        Get all playlists for the current user.

        Returns:
            List of playlist dictionaries

        Example:
            >>> playlists = await client.playlists.get_playlists()
            >>> print(f"Found {len(playlists)} playlists")
        """
        logger.info("Fetching user playlists")

        try:
            response = await self.client._request("GET", "/api/playlists")
            playlists = response.get("results", [])
            logger.info(f"Found {len(playlists)} playlists")
            return playlists
        except Exception as e:
            logger.error(f"Failed to get playlists: {str(e)}")
            raise

    async def get_playlist(self, playlist_id: str) -> Dict[str, Any]:
        """
        Get a specific playlist by ID.

        Args:
            playlist_id: Playlist ID

        Returns:
            Playlist data dictionary

        Example:
            >>> playlist = await client.playlists.get_playlist("playlist123")
        """
        logger.info(f"Fetching playlist: {playlist_id}")

        try:
            result = await self.client._request("GET", f"/api/playlists/{playlist_id}")
            logger.debug(f"Found playlist: {result.get('name', 'Unknown')}")
            return result
        except Exception as e:
            logger.error(f"Failed to get playlist {playlist_id}: {str(e)}")
            raise

    async def update_playlist(
        self,
        playlist_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update a playlist.

        Args:
            playlist_id: Playlist ID
            name: New playlist name
            description: New playlist description

        Returns:
            Updated playlist data

        Example:
            >>> await client.playlists.update_playlist("pl123", name="New Name")
        """
        logger.info(f"Updating playlist: {playlist_id}")

        payload = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description

        if not payload:
            raise ValueError("Must provide name or description to update")

        try:
            result = await self.client._request("PATCH", f"/api/playlists/{playlist_id}", json=payload)
            logger.info(f"Successfully updated playlist: {playlist_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to update playlist {playlist_id}: {str(e)}")
            raise

    async def delete_playlist(self, playlist_id: str) -> bool:
        """
        Delete a playlist.

        Args:
            playlist_id: Playlist ID to delete

        Returns:
            True if successful

        Example:
            >>> await client.playlists.delete_playlist("playlist123")
        """
        logger.info(f"Deleting playlist: {playlist_id}")

        try:
            await self.client._request("DELETE", f"/api/playlists/{playlist_id}")
            logger.info(f"Successfully deleted playlist: {playlist_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete playlist {playlist_id}: {str(e)}")
            raise

    async def add_item_to_playlist(
        self,
        playlist_id: str,
        library_item_id: str,
        episode_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Add an item to a playlist.

        Args:
            playlist_id: Playlist ID
            library_item_id: Library item ID
            episode_id: Optional episode ID for podcasts

        Returns:
            Updated playlist data

        Example:
            >>> await client.playlists.add_item_to_playlist("pl123", "item456")
            >>> await client.playlists.add_item_to_playlist("pl123", "item456", "ep789")  # Podcast episode
        """
        logger.info(f"Adding item {library_item_id} to playlist {playlist_id}")

        payload = {"libraryItemId": library_item_id}
        if episode_id:
            payload["episodeId"] = episode_id

        try:
            result = await self.client._request("POST", f"/api/playlists/{playlist_id}/item", json=payload)
            logger.info(f"Successfully added item {library_item_id} to playlist {playlist_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to add item {library_item_id} to playlist {playlist_id}: {str(e)}")
            raise

    async def remove_item_from_playlist(
        self,
        playlist_id: str,
        library_item_id: str,
        episode_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Remove an item from a playlist.

        Args:
            playlist_id: Playlist ID
            library_item_id: Library item ID
            episode_id: Optional episode ID for podcasts

        Returns:
            Updated playlist data

        Example:
            >>> await client.playlists.remove_item_from_playlist("pl123", "item456")
        """
        logger.info(f"Removing item {library_item_id} from playlist {playlist_id}")

        endpoint = f"/api/playlists/{playlist_id}/item/{library_item_id}"
        if episode_id:
            endpoint += f"/{episode_id}"

        try:
            result = await self.client._request("DELETE", endpoint)
            logger.info(f"Successfully removed item {library_item_id} from playlist {playlist_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to remove item {library_item_id} from playlist {playlist_id}: {str(e)}")
            raise

    async def batch_add_to_playlist(
        self,
        playlist_id: str,
        items: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Add multiple items to a playlist.

        Args:
            playlist_id: Playlist ID
            items: List of item dictionaries with 'libraryItemId' and optional 'episodeId'

        Returns:
            Batch operation result with succeeded/failed counts

        Example:
            >>> items = [
            ...     {"libraryItemId": "item1"},
            ...     {"libraryItemId": "item2", "episodeId": "ep1"}
            ... ]
            >>> result = await client.playlists.batch_add_to_playlist("pl123", items)
            >>> print(f"Added {result['success_count']} items")
        """
        logger.info(f"Batch adding {len(items)} items to playlist {playlist_id}")

        async def add_item(item: Dict[str, str]) -> None:
            """Add single item to playlist."""
            await self.client._request(
                "POST",
                f"/api/playlists/{playlist_id}/item",
                json=item
            )

        result = await self.batch_operation(
            items=items,
            operation=add_item,
            description=f"Adding {len(items)} items to playlist {playlist_id}"
        )
        logger.info(f"Batch add result: {result['success_count']} succeeded, {result['failure_count']} failed")
        return result

    async def batch_remove_from_playlist(
        self,
        playlist_id: str,
        items: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Remove multiple items from a playlist.

        Args:
            playlist_id: Playlist ID
            items: List of item dictionaries with 'libraryItemId' and optional 'episodeId'

        Returns:
            Batch operation result with succeeded/failed counts

        Example:
            >>> items = [
            ...     {"libraryItemId": "item1"},
            ...     {"libraryItemId": "item2", "episodeId": "ep1"}
            ... ]
            >>> result = await client.playlists.batch_remove_from_playlist("pl123", items)
            >>> print(f"Removed {result['success_count']} items")
        """
        logger.info(f"Batch removing {len(items)} items from playlist {playlist_id}")

        async def remove_item(item: Dict[str, str]) -> None:
            """Remove single item from playlist."""
            library_item_id = item.get("libraryItemId")
            episode_id = item.get("episodeId")

            endpoint = f"/api/playlists/{playlist_id}/item/{library_item_id}"
            if episode_id:
                endpoint += f"/{episode_id}"

            await self.client._request("DELETE", endpoint)

        result = await self.batch_operation(
            items=items,
            operation=remove_item,
            description=f"Removing {len(items)} items from playlist {playlist_id}"
        )
        logger.info(f"Batch remove result: {result['success_count']} succeeded, {result['failure_count']} failed")
        return result

    async def create_playlist_from_collection(
        self,
        collection_id: str,
        playlist_name: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a playlist from an existing collection.

        Args:
            collection_id: Collection ID to base playlist on
            playlist_name: Name for the new playlist
            description: Optional playlist description

        Returns:
            Created playlist data

        Example:
            >>> playlist = await client.playlists.create_playlist_from_collection(
            ...     "collection123", "My Collection Playlist"
            ... )
        """
        logger.info(f"Creating playlist '{playlist_name}' from collection {collection_id}")

        payload = {"name": playlist_name}
        if description:
            payload["description"] = description

        try:
            result = await self.client._request("POST", f"/api/playlists/collection/{collection_id}", json=payload)
            logger.info(f"Successfully created playlist from collection: {playlist_name}")
            return result
        except Exception as e:
            logger.error(f"Failed to create playlist from collection {collection_id}: {str(e)}")
            raise
