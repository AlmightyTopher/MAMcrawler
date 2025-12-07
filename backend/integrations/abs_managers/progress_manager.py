"""
Audiobookshelf Progress and Bookmark Management

Manages listening progress, bookmarks, and session tracking.
"""

import logging
from typing import Any, Dict, List, Optional

from backend.integrations.patterns.batch_operations import BatchOperationsMixin

logger = logging.getLogger(__name__)


class ProgressManager(BatchOperationsMixin):
    """
    Manager for Audiobookshelf progress tracking operations.

    Encapsulates all progress-related operations including:
    - Media progress tracking
    - Bookmark management
    - Listening session tracking
    - Listening statistics

    Args:
        client: Reference to AudiobookshelfClient for making requests
    """

    def __init__(self, client):
        """Initialize progress manager with client reference."""
        self.client = client

    async def get_media_progress(
        self,
        library_item_id: str,
        episode_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get media progress for a library item.

        Args:
            library_item_id: Library item ID
            episode_id: Optional episode ID for podcasts

        Returns:
            Progress data dictionary

        Example:
            >>> progress = await client.progress.get_media_progress("item123")
            >>> print(f"Progress: {progress.get('progress', 0)*100:.1f}%")
        """
        logger.debug(f"Getting progress for item: {library_item_id}")

        endpoint = f"/me/progress/{library_item_id}"
        if episode_id:
            endpoint += f"/{episode_id}"

        try:
            result = await self.client._request("GET", endpoint)
            logger.debug(f"Got progress for {library_item_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to get progress for {library_item_id}: {str(e)}")
            raise

    async def update_media_progress(
        self,
        library_item_id: str,
        progress: float,  # 0.0 to 1.0
        current_time: Optional[float] = None,
        is_finished: bool = False,
        episode_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update media progress for a library item.

        Args:
            library_item_id: Library item ID
            progress: Progress as decimal (0.0 to 1.0)
            current_time: Current playback time in seconds
            is_finished: Whether the item is finished
            episode_id: Optional episode ID for podcasts

        Returns:
            Updated progress data

        Example:
            >>> await client.progress.update_media_progress("item123", 0.75, 1800.5)
        """
        logger.info(f"Updating progress for {library_item_id}: {progress*100:.1f}%")

        payload = {
            "progress": progress,
            "isFinished": is_finished,
        }
        if current_time is not None:
            payload["currentTime"] = current_time

        endpoint = f"/me/progress/{library_item_id}"
        if episode_id:
            endpoint += f"/{episode_id}"

        try:
            result = await self.client._request("PATCH", endpoint, json=payload)
            logger.info(f"Successfully updated progress for {library_item_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to update progress for {library_item_id}: {str(e)}")
            raise

    async def batch_update_progress(self, progress_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Batch update media progress for multiple items.

        Args:
            progress_updates: List of progress update dictionaries

        Returns:
            Batch operation result with succeeded/failed counts

        Example:
            >>> updates = [
            ...     {"libraryItemId": "item1", "progress": 0.5},
            ...     {"libraryItemId": "item2", "progress": 1.0, "isFinished": True}
            ... ]
            >>> result = await client.progress.batch_update_progress(updates)
            >>> print(f"Updated {result['success_count']} items")
        """
        logger.info(f"Batch updating progress for {len(progress_updates)} items")

        async def update_item_progress(update: Dict[str, Any]) -> None:
            """Update single item progress."""
            library_item_id = update.get("libraryItemId")
            episode_id = update.get("episodeId")

            endpoint = f"/me/progress/{library_item_id}"
            if episode_id:
                endpoint += f"/{episode_id}"

            # Extract payload for this item
            payload = {
                "progress": update.get("progress", 0),
                "isFinished": update.get("isFinished", False),
            }
            if "currentTime" in update:
                payload["currentTime"] = update["currentTime"]

            await self.client._request("PATCH", endpoint, json=payload)

        result = await self.batch_operation(
            items=progress_updates,
            operation=update_item_progress,
            description=f"Updating progress for {len(progress_updates)} items"
        )
        logger.info(f"Batch update result: {result['success_count']} succeeded, {result['failure_count']} failed")
        return result

    async def remove_media_progress(self, library_item_id: str) -> bool:
        """
        Remove media progress for a library item.

        Args:
            library_item_id: Library item ID

        Returns:
            True if successful

        Example:
            >>> await client.progress.remove_media_progress("item123")
        """
        logger.info(f"Removing progress for {library_item_id}")

        try:
            await self.client._request("DELETE", f"/me/progress/{library_item_id}")
            logger.info(f"Successfully removed progress for {library_item_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove progress for {library_item_id}: {str(e)}")
            raise

    async def create_bookmark(
        self,
        library_item_id: str,
        title: str,
        time: float,
    ) -> Dict[str, Any]:
        """
        Create a bookmark for a library item.

        Args:
            library_item_id: Library item ID
            title: Bookmark title
            time: Time in seconds

        Returns:
            Created bookmark data

        Example:
            >>> bookmark = await client.progress.create_bookmark("item123", "Chapter 5", 1800.0)
        """
        logger.info(f"Creating bookmark '{title}' at {time}s for {library_item_id}")

        payload = {
            "libraryItemId": library_item_id,
            "title": title,
            "time": time,
        }

        try:
            result = await self.client._request("POST", f"/me/item/{library_item_id}/bookmark", json=payload)
            logger.info(f"Successfully created bookmark for {library_item_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to create bookmark for {library_item_id}: {str(e)}")
            raise

    async def update_bookmark(
        self,
        library_item_id: str,
        bookmark_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update a bookmark for a library item.

        Args:
            library_item_id: Library item ID
            bookmark_data: Updated bookmark data

        Returns:
            Updated bookmark data

        Example:
            >>> await client.progress.update_bookmark("item123", {"title": "New Title", "time": 1900.0})
        """
        logger.info(f"Updating bookmark for {library_item_id}")

        try:
            result = await self.client._request("PATCH", f"/me/item/{library_item_id}/bookmark", json=bookmark_data)
            logger.info(f"Successfully updated bookmark for {library_item_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to update bookmark for {library_item_id}: {str(e)}")
            raise

    async def remove_bookmark(
        self,
        library_item_id: str,
        time: float,
    ) -> bool:
        """
        Remove a bookmark from a library item.

        Args:
            library_item_id: Library item ID
            time: Bookmark time in seconds

        Returns:
            True if successful

        Example:
            >>> await client.progress.remove_bookmark("item123", 1800.0)
        """
        logger.info(f"Removing bookmark at {time}s for {library_item_id}")

        try:
            await self.client._request("DELETE", f"/me/item/{library_item_id}/bookmark/{time}")
            logger.info(f"Successfully removed bookmark for {library_item_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove bookmark for {library_item_id}: {str(e)}")
            raise

    async def get_listening_sessions(
        self,
        library_item_id: Optional[str] = None,
        episode_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get listening sessions for current user.

        Args:
            library_item_id: Optional specific library item
            episode_id: Optional specific episode

        Returns:
            List of listening session dictionaries

        Example:
            >>> sessions = await client.progress.get_listening_sessions()
            >>> item_sessions = await client.progress.get_listening_sessions("item123")
        """
        logger.info("Getting listening sessions")

        if library_item_id:
            endpoint = f"/me/item/listening-sessions/{library_item_id}"
            if episode_id:
                endpoint += f"/{episode_id}"
        else:
            endpoint = "/me/listening-sessions"

        try:
            result = await self.client._request("GET", endpoint)
            sessions = result.get("sessions", [])
            logger.info(f"Found {len(sessions)} listening sessions")
            return sessions
        except Exception as e:
            logger.error(f"Failed to get listening sessions: {str(e)}")
            raise

    async def get_listening_stats(self) -> Dict[str, Any]:
        """
        Get listening statistics for current user.

        Returns:
            Listening statistics dictionary

        Example:
            >>> stats = await client.progress.get_listening_stats()
            >>> print(f"Total listening time: {stats['totalTime']} seconds")
        """
        logger.info("Getting listening stats")

        try:
            result = await self.client._request("GET", "/me/listening-stats")
            logger.info("Successfully retrieved listening stats")
            return result
        except Exception as e:
            logger.error(f"Failed to get listening stats: {str(e)}")
            raise

    async def get_items_in_progress(self) -> List[Dict[str, Any]]:
        """
        Get library items currently in progress for the user.

        Returns:
            List of items in progress

        Example:
            >>> items = await client.progress.get_items_in_progress()
            >>> print(f"{len(items)} items in progress")
        """
        logger.info("Getting items in progress")

        try:
            result = await self.client._request("GET", "/me/items-in-progress")
            items = result.get("libraryItems", [])
            logger.info(f"Found {len(items)} items in progress")
            return items
        except Exception as e:
            logger.error(f"Failed to get items in progress: {str(e)}")
            raise
