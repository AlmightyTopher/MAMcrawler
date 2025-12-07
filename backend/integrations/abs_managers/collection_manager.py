"""
Audiobookshelf Collection Management

Manages collections and collection membership operations.
"""

import logging
from typing import Any, Dict, List, Optional

from backend.integrations.patterns.batch_operations import BatchOperationsMixin

logger = logging.getLogger(__name__)


class CollectionManager(BatchOperationsMixin):
    """
    Manager for Audiobookshelf collection operations.

    Encapsulates all collection-related operations including:
    - Collection CRUD operations
    - Adding/removing books from collections
    - Batch operations on collections

    Args:
        client: Reference to AudiobookshelfClient for making requests
    """

    def __init__(self, client):
        """Initialize collection manager with client reference."""
        self.client = client

    async def create_collection(
        self,
        name: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new collection.

        Args:
            name: Collection name
            description: Optional collection description

        Returns:
            Created collection data

        Example:
            >>> collection = await client.collections.create_collection("My Favorites", "Best audiobooks")
        """
        logger.info(f"Creating collection: {name}")

        payload = {"name": name}
        if description:
            payload["description"] = description

        try:
            result = await self.client._request("POST", "/api/collections", json=payload)
            logger.info(f"Successfully created collection: {name}")
            return result
        except Exception as e:
            logger.error(f"Failed to create collection {name}: {str(e)}")
            raise

    async def get_collections(self) -> List[Dict[str, Any]]:
        """
        Get all collections.

        Returns:
            List of collection dictionaries

        Example:
            >>> collections = await client.collections.get_collections()
            >>> print(f"Found {len(collections)} collections")
        """
        logger.info("Fetching collections")

        try:
            response = await self.client._request("GET", "/api/collections")
            collections = response.get("results", [])
            logger.info(f"Found {len(collections)} collections")
            return collections
        except Exception as e:
            logger.error(f"Failed to get collections: {str(e)}")
            raise

    async def get_collection(self, collection_id: str) -> Dict[str, Any]:
        """
        Get a specific collection by ID.

        Args:
            collection_id: Collection ID

        Returns:
            Collection data dictionary

        Example:
            >>> collection = await client.collections.get_collection("collection123")
        """
        logger.info(f"Fetching collection: {collection_id}")

        try:
            result = await self.client._request("GET", f"/api/collections/{collection_id}")
            logger.debug(f"Found collection: {result.get('name', 'Unknown')}")
            return result
        except Exception as e:
            logger.error(f"Failed to get collection {collection_id}: {str(e)}")
            raise

    async def update_collection(
        self,
        collection_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update a collection.

        Args:
            collection_id: Collection ID
            name: New collection name
            description: New collection description

        Returns:
            Updated collection data

        Example:
            >>> await client.collections.update_collection("col123", name="New Name")
        """
        logger.info(f"Updating collection: {collection_id}")

        payload = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description

        if not payload:
            raise ValueError("Must provide name or description to update")

        try:
            result = await self.client._request("PATCH", f"/api/collections/{collection_id}", json=payload)
            logger.info(f"Successfully updated collection: {collection_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to update collection {collection_id}: {str(e)}")
            raise

    async def delete_collection(self, collection_id: str) -> bool:
        """
        Delete a collection.

        Args:
            collection_id: Collection ID to delete

        Returns:
            True if successful

        Example:
            >>> await client.collections.delete_collection("collection123")
        """
        logger.info(f"Deleting collection: {collection_id}")

        try:
            await self.client._request("DELETE", f"/api/collections/{collection_id}")
            logger.info(f"Successfully deleted collection: {collection_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection {collection_id}: {str(e)}")
            raise

    async def add_book_to_collection(
        self,
        collection_id: str,
        book_id: str,
    ) -> Dict[str, Any]:
        """
        Add a book to a collection.

        Args:
            collection_id: Collection ID
            book_id: Book/library item ID

        Returns:
            Updated collection data

        Example:
            >>> await client.collections.add_book_to_collection("col123", "book456")
        """
        logger.info(f"Adding book {book_id} to collection {collection_id}")

        payload = {"id": book_id}

        try:
            result = await self.client._request("POST", f"/api/collections/{collection_id}/book", json=payload)
            logger.info(f"Successfully added book {book_id} to collection {collection_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to add book {book_id} to collection {collection_id}: {str(e)}")
            raise

    async def remove_book_from_collection(
        self,
        collection_id: str,
        book_id: str,
    ) -> Dict[str, Any]:
        """
        Remove a book from a collection.

        Args:
            collection_id: Collection ID
            book_id: Book/library item ID

        Returns:
            Updated collection data

        Example:
            >>> await client.collections.remove_book_from_collection("col123", "book456")
        """
        logger.info(f"Removing book {book_id} from collection {collection_id}")

        try:
            result = await self.client._request("DELETE", f"/api/collections/{collection_id}/book/{book_id}")
            logger.info(f"Successfully removed book {book_id} from collection {collection_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to remove book {book_id} from collection {collection_id}: {str(e)}")
            raise

    async def batch_add_to_collection(
        self,
        collection_id: str,
        book_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Add multiple books to a collection.

        Args:
            collection_id: Collection ID
            book_ids: List of book/library item IDs

        Returns:
            Batch operation result with succeeded/failed counts

        Example:
            >>> result = await client.collections.batch_add_to_collection("col123", ["book1", "book2", "book3"])
            >>> print(f"Added {result['success_count']} books")
        """
        logger.info(f"Batch adding {len(book_ids)} books to collection {collection_id}")

        async def add_book(book_id: str) -> None:
            """Add single book to collection."""
            await self.client._request(
                "POST",
                f"/api/collections/{collection_id}/book",
                json={"id": book_id}
            )

        result = await self.batch_operation(
            items=book_ids,
            operation=add_book,
            description=f"Adding {len(book_ids)} books to collection {collection_id}"
        )
        logger.info(f"Batch add result: {result['success_count']} succeeded, {result['failure_count']} failed")
        return result

    async def batch_remove_from_collection(
        self,
        collection_id: str,
        book_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Remove multiple books from a collection.

        Args:
            collection_id: Collection ID
            book_ids: List of book/library item IDs

        Returns:
            Batch operation result with succeeded/failed counts

        Example:
            >>> result = await client.collections.batch_remove_from_collection("col123", ["book1", "book2"])
            >>> print(f"Removed {result['success_count']} books")
        """
        logger.info(f"Batch removing {len(book_ids)} books from collection {collection_id}")

        async def remove_book(book_id: str) -> None:
            """Remove single book from collection."""
            await self.client._request(
                "DELETE",
                f"/api/collections/{collection_id}/book/{book_id}"
            )

        result = await self.batch_operation(
            items=book_ids,
            operation=remove_book,
            description=f"Removing {len(book_ids)} books from collection {collection_id}"
        )
        logger.info(f"Batch remove result: {result['success_count']} succeeded, {result['failure_count']} failed")
        return result
