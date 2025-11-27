"""
Audiobookshelf API Client

Provides async interface to Audiobookshelf server for managing audiobook library.
Supports book import, metadata updates, library scanning, and search.
"""

import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
import asyncio

import aiohttp
from aiohttp import ClientTimeout, ClientError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)


class AudiobookshelfError(Exception):
    """Base exception for Audiobookshelf client errors."""
    pass


class AudiobookshelfClient:
    """
    Async client for Audiobookshelf API.

    Handles authentication, pagination, retries, and error handling for all
    Audiobookshelf operations.

    Args:
        base_url: Audiobookshelf server URL (e.g., "http://localhost:13378")
        api_token: Bearer token for authentication
        timeout: Request timeout in seconds (default: 30)

    Example:
        >>> async with AudiobookshelfClient(base_url, token) as client:
        ...     books = await client.get_library_items(limit=50)
        ...     book = await client.get_book_by_id("abc123")
    """

    def __init__(
        self,
        base_url: str,
        api_token: str,
        timeout: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.timeout = ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None

        # Headers for all requests
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

        logger.info(f"Initialized AudiobookshelfClient for {self.base_url}")

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            headers=self.headers,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _ensure_session(self):
        """Ensure session is initialized."""
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers=self.headers,
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ClientError, asyncio.TimeoutError)),
        reraise=True,
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            **kwargs: Additional arguments for aiohttp request

        Returns:
            JSON response as dict

        Raises:
            AudiobookshelfError: On API errors
        """
        await self._ensure_session()
        url = f"{self.base_url}{endpoint}"

        logger.debug(f"{method} {url}")

        try:
            async with self.session.request(method, url, **kwargs) as response:
                response.raise_for_status()

                # Handle empty responses
                if response.status == 204:
                    return {}

                data = await response.json()
                logger.debug(f"Response: {response.status}")
                return data

        except aiohttp.ClientResponseError as e:
            logger.error(f"API error: {e.status} - {e.message}")
            raise AudiobookshelfError(f"API request failed: {e.status} {e.message}")
        except aiohttp.ClientError as e:
            logger.error(f"Client error: {str(e)}")
            raise AudiobookshelfError(f"Request failed: {str(e)}")
        except asyncio.TimeoutError:
            logger.error(f"Request timeout for {url}")
            raise AudiobookshelfError(f"Request timeout")

    async def get_library_items(
        self,
        library_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get library items with automatic pagination.

        Fetches all items by respecting the API's total field and paginating
        through results.

        Args:
            library_id: Specific library ID (if None, uses first library)
            limit: Items per page (max 1000)
            offset: Starting offset

        Returns:
            List of book metadata dictionaries

        Example:
            >>> books = await client.get_library_items(limit=50)
            >>> print(f"Found {len(books)} books")
        """
        # Get libraries if no library_id specified
        if not library_id:
            libraries = await self._request("GET", "/api/libraries")
            if not libraries or not libraries.get("libraries"):
                logger.warning("No libraries found")
                return []
            library_id = libraries["libraries"][0]["id"]
            logger.info(f"Using library: {library_id}")

        all_items = []
        current_offset = offset

        while True:
            endpoint = f"/api/libraries/{library_id}/items"
            params = {
                "limit": min(limit, 1000),  # API max is 1000
                "offset": current_offset,
            }

            logger.info(f"Fetching items: offset={current_offset}, limit={params['limit']}")

            response = await self._request("GET", endpoint, params=params)

            items = response.get("results", [])
            all_items.extend(items)

            total = response.get("total", 0)
            logger.info(f"Got {len(items)} items, total in library: {total}")

            # Check if we have all items
            if current_offset + len(items) >= total:
                break

            current_offset += len(items)

            # Safety check to avoid infinite loops
            if current_offset > 100000:
                logger.warning("Offset exceeded 100k, stopping pagination")
                break

        logger.info(f"Retrieved {len(all_items)} total items")
        return all_items

    async def get_book_by_id(self, abs_id: str) -> Dict[str, Any]:
        """
        Get single book metadata by ID.

        Args:
            abs_id: Audiobookshelf library item ID

        Returns:
            Book metadata dictionary

        Raises:
            AudiobookshelfError: If book not found
        """
        logger.info(f"Fetching book: {abs_id}")
        endpoint = f"/api/items/{abs_id}"

        try:
            book = await self._request("GET", endpoint)
            logger.debug(f"Found book: {book.get('media', {}).get('metadata', {}).get('title', 'Unknown')}")
            return book
        except AudiobookshelfError as e:
            logger.error(f"Failed to fetch book {abs_id}: {str(e)}")
            raise

    async def import_book(
        self,
        library_id: str,
        file_path: str,
        metadata_dict: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Import downloaded book to library.

        Note: This triggers a library scan to detect the new file.
        For direct upload, use the upload endpoint instead.

        Args:
            library_id: Target library ID
            file_path: Path to book file (must be in library folder)
            metadata_dict: Optional metadata to apply after import

        Returns:
            Import result dictionary

        Example:
            >>> result = await client.import_book(
            ...     library_id="lib123",
            ...     file_path="/audiobooks/Book.m4b",
            ...     metadata_dict={"title": "Book Title", "author": "Author Name"}
            ... )
        """
        logger.info(f"Importing book from {file_path}")

        # Trigger library scan to detect new file
        scan_result = await self.scan_library(library_id)

        # If metadata provided, search for the newly imported book and update it
        if metadata_dict:
            # Wait a bit for scan to complete
            await asyncio.sleep(2)

            # Try to find the book by filename
            file_name = Path(file_path).stem
            search_results = await self.search_books(file_name, library_id)

            if search_results:
                book_id = search_results[0].get("id")
                logger.info(f"Found imported book: {book_id}")
                await self.update_book_metadata(book_id, metadata_dict)
                return {"success": True, "book_id": book_id}

        return scan_result

    async def update_book_metadata(
        self,
        abs_id: str,
        metadata_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update book metadata.

        Args:
            abs_id: Audiobookshelf library item ID
            metadata_dict: Metadata fields to update (title, authorName, seriesName, etc.)
                For series, use format: "Series Name #1" for seriesName field

        Returns:
            Updated book metadata

        Example:
            >>> await client.update_book_metadata(
            ...     "book123",
            ...     {
            ...         "title": "New Title",
            ...         "authorName": "Author Name",
            ...         "seriesName": "Series Name #1"
            ...     }
            ... )
        """
        logger.info(f"Updating metadata for book: {abs_id}")
        logger.debug(f"Metadata: {metadata_dict}")

        endpoint = f"/api/items/{abs_id}/media"

        # Transform field names to match Audiobookshelf API expectations
        transformed_dict = {}

        for key, value in metadata_dict.items():
            # Map common field name variations to ABS field names
            if key == "authors" and isinstance(value, list):
                # Convert list of authors to single authorName string
                transformed_dict["authorName"] = ", ".join(value) if value else ""
            elif key == "series" and value:
                # Convert series + seriesSequence to seriesName format "Name #Position"
                sequence = metadata_dict.get("seriesSequence", "")
                if sequence:
                    transformed_dict["seriesName"] = f"{value} #{sequence}"
                else:
                    transformed_dict["seriesName"] = value
            elif key == "seriesSequence":
                # Skip this as it's handled above with series
                continue
            else:
                # Pass through other fields as-is
                transformed_dict[key] = value

        # Wrap metadata in media structure
        payload = {"metadata": transformed_dict}

        try:
            result = await self._request("PATCH", endpoint, json=payload)
            logger.info(f"Successfully updated metadata for {abs_id}")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to update metadata for {abs_id}: {str(e)}")
            raise

    async def scan_library(self, library_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Trigger library rescan.

        Args:
            library_id: Specific library ID (if None, uses first library)

        Returns:
            Scan status dictionary
        """
        # Get library_id if not specified
        if not library_id:
            libraries = await self._request("GET", "/api/libraries")
            if not libraries or not libraries.get("libraries"):
                raise AudiobookshelfError("No libraries found")
            library_id = libraries["libraries"][0]["id"]

        logger.info(f"Triggering scan for library: {library_id}")
        endpoint = f"/api/libraries/{library_id}/scan"

        try:
            result = await self._request("POST", endpoint)
            logger.info("Library scan triggered successfully")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to trigger library scan: {str(e)}")
            raise

    async def search_books(
        self,
        query: str,
        library_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Search library for books.

        Args:
            query: Search query (searches title, author, series)
            library_id: Optional library ID to restrict search
            limit: Maximum results to return

        Returns:
            List of matching book dictionaries

        Example:
            >>> results = await client.search_books("Foundation Asimov")
            >>> for book in results:
            ...     print(book["media"]["metadata"]["title"])
        """
        logger.info(f"Searching for: {query}")

        endpoint = "/api/search/books"
        params = {"q": query, "limit": limit}

        if library_id:
            params["library"] = library_id

        try:
            response = await self._request("GET", endpoint, params=params)
            results = response.get("book", [])  # API returns {"book": [...]}
            logger.info(f"Found {len(results)} results")
            return results
        except AudiobookshelfError as e:
            logger.error(f"Search failed: {str(e)}")
            raise

    async def get_libraries(self) -> List[Dict[str, Any]]:
        """
        Get all libraries.

        Returns:
            List of library dictionaries
        """
        logger.info("Fetching libraries")
        response = await self._request("GET", "/api/libraries")
        libraries = response.get("libraries", [])
        logger.info(f"Found {len(libraries)} libraries")
        return libraries

    async def delete_book(self, abs_id: str, hard_delete: bool = False) -> Dict[str, Any]:
        """
        Delete book from library.

        Args:
            abs_id: Audiobookshelf library item ID
            hard_delete: If True, deletes files from disk

        Returns:
            Deletion result
        """
        logger.info(f"Deleting book: {abs_id} (hard_delete={hard_delete})")
        endpoint = f"/api/items/{abs_id}"
        params = {"hard": "1" if hard_delete else "0"}

        try:
            result = await self._request("DELETE", endpoint, params=params)
            logger.info(f"Successfully deleted book {abs_id}")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to delete book {abs_id}: {str(e)}")
            raise

    # ========================================
    # COLLECTIONS MANAGEMENT
    # ========================================

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
            >>> collection = await client.create_collection("My Favorites", "Best audiobooks")
        """
        logger.info(f"Creating collection: {name}")

        payload = {"name": name}
        if description:
            payload["description"] = description

        try:
            result = await self._request("POST", "/api/collections", json=payload)
            logger.info(f"Successfully created collection: {name}")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to create collection {name}: {str(e)}")
            raise

    async def get_collections(self) -> List[Dict[str, Any]]:
        """
        Get all collections.

        Returns:
            List of collection dictionaries

        Example:
            >>> collections = await client.get_collections()
            >>> print(f"Found {len(collections)} collections")
        """
        logger.info("Fetching collections")

        try:
            response = await self._request("GET", "/api/collections")
            collections = response.get("results", [])
            logger.info(f"Found {len(collections)} collections")
            return collections
        except AudiobookshelfError as e:
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
            >>> collection = await client.get_collection("collection123")
        """
        logger.info(f"Fetching collection: {collection_id}")

        try:
            result = await self._request("GET", f"/api/collections/{collection_id}")
            logger.debug(f"Found collection: {result.get('name', 'Unknown')}")
            return result
        except AudiobookshelfError as e:
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
            >>> await client.update_collection("col123", name="New Name")
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
            result = await self._request("PATCH", f"/api/collections/{collection_id}", json=payload)
            logger.info(f"Successfully updated collection: {collection_id}")
            return result
        except AudiobookshelfError as e:
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
            >>> await client.delete_collection("collection123")
        """
        logger.info(f"Deleting collection: {collection_id}")

        try:
            await self._request("DELETE", f"/api/collections/{collection_id}")
            logger.info(f"Successfully deleted collection: {collection_id}")
            return True
        except AudiobookshelfError as e:
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
            >>> await client.add_book_to_collection("col123", "book456")
        """
        logger.info(f"Adding book {book_id} to collection {collection_id}")

        payload = {"id": book_id}

        try:
            result = await self._request("POST", f"/api/collections/{collection_id}/book", json=payload)
            logger.info(f"Successfully added book {book_id} to collection {collection_id}")
            return result
        except AudiobookshelfError as e:
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
            >>> await client.remove_book_from_collection("col123", "book456")
        """
        logger.info(f"Removing book {book_id} from collection {collection_id}")

        try:
            result = await self._request("DELETE", f"/api/collections/{collection_id}/book/{book_id}")
            logger.info(f"Successfully removed book {book_id} from collection {collection_id}")
            return result
        except AudiobookshelfError as e:
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
            Updated collection data

        Example:
            >>> await client.batch_add_to_collection("col123", ["book1", "book2", "book3"])
        """
        logger.info(f"Batch adding {len(book_ids)} books to collection {collection_id}")

        payload = {"books": book_ids}

        try:
            result = await self._request("POST", f"/api/collections/{collection_id}/batch/add", json=payload)
            logger.info(f"Successfully batch added {len(book_ids)} books to collection {collection_id}")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to batch add books to collection {collection_id}: {str(e)}")
            raise

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
            Updated collection data

        Example:
            >>> await client.batch_remove_from_collection("col123", ["book1", "book2"])
        """
        logger.info(f"Batch removing {len(book_ids)} books from collection {collection_id}")

        payload = {"books": book_ids}

        try:
            result = await self._request("POST", f"/api/collections/{collection_id}/batch/remove", json=payload)
            logger.info(f"Successfully batch removed {len(book_ids)} books from collection {collection_id}")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to batch remove books from collection {collection_id}: {str(e)}")
            raise

    # ========================================
    # PLAYLISTS MANAGEMENT
    # ========================================

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
            >>> playlist = await client.create_playlist("My Playlist", "Curated selection")
        """
        logger.info(f"Creating playlist: {name}")

        payload = {"name": name}
        if description:
            payload["description"] = description

        try:
            result = await self._request("POST", "/api/playlists", json=payload)
            logger.info(f"Successfully created playlist: {name}")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to create playlist {name}: {str(e)}")
            raise

    async def get_playlists(self) -> List[Dict[str, Any]]:
        """
        Get all playlists for the current user.

        Returns:
            List of playlist dictionaries

        Example:
            >>> playlists = await client.get_playlists()
            >>> print(f"Found {len(playlists)} playlists")
        """
        logger.info("Fetching user playlists")

        try:
            response = await self._request("GET", "/api/playlists")
            playlists = response.get("results", [])
            logger.info(f"Found {len(playlists)} playlists")
            return playlists
        except AudiobookshelfError as e:
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
            >>> playlist = await client.get_playlist("playlist123")
        """
        logger.info(f"Fetching playlist: {playlist_id}")

        try:
            result = await self._request("GET", f"/api/playlists/{playlist_id}")
            logger.debug(f"Found playlist: {result.get('name', 'Unknown')}")
            return result
        except AudiobookshelfError as e:
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
            >>> await client.update_playlist("pl123", name="New Name")
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
            result = await self._request("PATCH", f"/api/playlists/{playlist_id}", json=payload)
            logger.info(f"Successfully updated playlist: {playlist_id}")
            return result
        except AudiobookshelfError as e:
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
            >>> await client.delete_playlist("playlist123")
        """
        logger.info(f"Deleting playlist: {playlist_id}")

        try:
            await self._request("DELETE", f"/api/playlists/{playlist_id}")
            logger.info(f"Successfully deleted playlist: {playlist_id}")
            return True
        except AudiobookshelfError as e:
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
            >>> await client.add_item_to_playlist("pl123", "item456")
            >>> await client.add_item_to_playlist("pl123", "item456", "ep789")  # Podcast episode
        """
        logger.info(f"Adding item {library_item_id} to playlist {playlist_id}")

        payload = {"libraryItemId": library_item_id}
        if episode_id:
            payload["episodeId"] = episode_id

        try:
            result = await self._request("POST", f"/api/playlists/{playlist_id}/item", json=payload)
            logger.info(f"Successfully added item {library_item_id} to playlist {playlist_id}")
            return result
        except AudiobookshelfError as e:
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
            >>> await client.remove_item_from_playlist("pl123", "item456")
        """
        logger.info(f"Removing item {library_item_id} from playlist {playlist_id}")

        endpoint = f"/api/playlists/{playlist_id}/item/{library_item_id}"
        if episode_id:
            endpoint += f"/{episode_id}"

        try:
            result = await self._request("DELETE", endpoint)
            logger.info(f"Successfully removed item {library_item_id} from playlist {playlist_id}")
            return result
        except AudiobookshelfError as e:
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
            Updated playlist data

        Example:
            >>> items = [
            ...     {"libraryItemId": "item1"},
            ...     {"libraryItemId": "item2", "episodeId": "ep1"}
            ... ]
            >>> await client.batch_add_to_playlist("pl123", items)
        """
        logger.info(f"Batch adding {len(items)} items to playlist {playlist_id}")

        payload = {"items": items}

        try:
            result = await self._request("POST", f"/api/playlists/{playlist_id}/batch/add", json=payload)
            logger.info(f"Successfully batch added {len(items)} items to playlist {playlist_id}")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to batch add items to playlist {playlist_id}: {str(e)}")
            raise

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
            Updated playlist data

        Example:
            >>> items = [
            ...     {"libraryItemId": "item1"},
            ...     {"libraryItemId": "item2", "episodeId": "ep1"}
            ... ]
            >>> await client.batch_remove_from_playlist("pl123", items)
        """
        logger.info(f"Batch removing {len(items)} items from playlist {playlist_id}")

        payload = {"items": items}

        try:
            result = await self._request("POST", f"/api/playlists/{playlist_id}/batch/remove", json=payload)
            logger.info(f"Successfully batch removed {len(items)} items from playlist {playlist_id}")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to batch remove items from playlist {playlist_id}: {str(e)}")
            raise

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
            >>> playlist = await client.create_playlist_from_collection(
            ...     "collection123", "My Collection Playlist"
            ... )
        """
        logger.info(f"Creating playlist '{playlist_name}' from collection {collection_id}")

        payload = {"name": playlist_name}
        if description:
            payload["description"] = description

        try:
            result = await self._request("POST", f"/api/playlists/collection/{collection_id}", json=payload)
            logger.info(f"Successfully created playlist from collection: {playlist_name}")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to create playlist from collection {collection_id}: {str(e)}")
            raise

    # ========================================
    # PROGRESS TRACKING & BOOKMARKS
    # ========================================

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
            >>> progress = await client.get_media_progress("item123")
            >>> print(f"Progress: {progress.get('progress', 0)*100:.1f}%")
        """
        logger.debug(f"Getting progress for item: {library_item_id}")

        endpoint = f"/me/progress/{library_item_id}"
        if episode_id:
            endpoint += f"/{episode_id}"

        try:
            result = await self._request("GET", endpoint)
            logger.debug(f"Got progress for {library_item_id}")
            return result
        except AudiobookshelfError as e:
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
            >>> await client.update_media_progress("item123", 0.75, 1800.5)
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
            result = await self._request("PATCH", endpoint, json=payload)
            logger.info(f"Successfully updated progress for {library_item_id}")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to update progress for {library_item_id}: {str(e)}")
            raise

    async def batch_update_progress(self, progress_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Batch update media progress for multiple items.

        Args:
            progress_updates: List of progress update dictionaries

        Returns:
            Batch update result

        Example:
            >>> updates = [
            ...     {"libraryItemId": "item1", "progress": 0.5},
            ...     {"libraryItemId": "item2", "progress": 1.0, "isFinished": True}
            ... ]
            >>> await client.batch_update_progress(updates)
        """
        logger.info(f"Batch updating progress for {len(progress_updates)} items")

        try:
            result = await self._request("PATCH", "/me/progress/batch/update", json={"updates": progress_updates})
            logger.info("Successfully batch updated progress")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to batch update progress: {str(e)}")
            raise

    async def remove_media_progress(self, library_item_id: str) -> bool:
        """
        Remove media progress for a library item.

        Args:
            library_item_id: Library item ID

        Returns:
            True if successful

        Example:
            >>> await client.remove_media_progress("item123")
        """
        logger.info(f"Removing progress for {library_item_id}")

        try:
            await self._request("DELETE", f"/me/progress/{library_item_id}")
            logger.info(f"Successfully removed progress for {library_item_id}")
            return True
        except AudiobookshelfError as e:
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
            >>> bookmark = await client.create_bookmark("item123", "Chapter 5", 1800.0)
        """
        logger.info(f"Creating bookmark '{title}' at {time}s for {library_item_id}")

        payload = {
            "libraryItemId": library_item_id,
            "title": title,
            "time": time,
        }

        try:
            result = await self._request("POST", f"/me/item/{library_item_id}/bookmark", json=payload)
            logger.info(f"Successfully created bookmark for {library_item_id}")
            return result
        except AudiobookshelfError as e:
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
            >>> await client.update_bookmark("item123", {"title": "New Title", "time": 1900.0})
        """
        logger.info(f"Updating bookmark for {library_item_id}")

        try:
            result = await self._request("PATCH", f"/me/item/{library_item_id}/bookmark", json=bookmark_data)
            logger.info(f"Successfully updated bookmark for {library_item_id}")
            return result
        except AudiobookshelfError as e:
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
            >>> await client.remove_bookmark("item123", 1800.0)
        """
        logger.info(f"Removing bookmark at {time}s for {library_item_id}")

        try:
            await self._request("DELETE", f"/me/item/{library_item_id}/bookmark/{time}")
            logger.info(f"Successfully removed bookmark for {library_item_id}")
            return True
        except AudiobookshelfError as e:
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
            >>> sessions = await client.get_listening_sessions()
            >>> item_sessions = await client.get_listening_sessions("item123")
        """
        logger.info("Getting listening sessions")

        if library_item_id:
            endpoint = f"/me/item/listening-sessions/{library_item_id}"
            if episode_id:
                endpoint += f"/{episode_id}"
        else:
            endpoint = "/me/listening-sessions"

        try:
            result = await self._request("GET", endpoint)
            sessions = result.get("sessions", [])
            logger.info(f"Found {len(sessions)} listening sessions")
            return sessions
        except AudiobookshelfError as e:
            logger.error(f"Failed to get listening sessions: {str(e)}")
            raise

    async def get_listening_stats(self) -> Dict[str, Any]:
        """
        Get listening statistics for current user.

        Returns:
            Listening statistics dictionary

        Example:
            >>> stats = await client.get_listening_stats()
            >>> print(f"Total listening time: {stats['totalTime']} seconds")
        """
        logger.info("Getting listening stats")

        try:
            result = await self._request("GET", "/me/listening-stats")
            logger.info("Successfully retrieved listening stats")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to get listening stats: {str(e)}")
            raise

    async def get_items_in_progress(self) -> List[Dict[str, Any]]:
        """
        Get library items currently in progress for the user.

        Returns:
            List of items in progress

        Example:
            >>> items = await client.get_items_in_progress()
            >>> print(f"{len(items)} items in progress")
        """
        logger.info("Getting items in progress")

        try:
            result = await self._request("GET", "/me/items-in-progress")
            items = result.get("libraryItems", [])
            logger.info(f"Found {len(items)} items in progress")
            return items
        except AudiobookshelfError as e:
            logger.error(f"Failed to get items in progress: {str(e)}")
            raise

    # ========================================
    # USER MANAGEMENT
    # ========================================

    async def get_user_profile(self) -> Dict[str, Any]:
        """
        Get current user profile information.

        Returns:
            User profile data

        Example:
            >>> profile = await client.get_user_profile()
            >>> print(f"Username: {profile.get('username')}")
        """
        logger.info("Getting user profile")

        try:
            result = await self._request("GET", "/me")
            logger.info("Successfully retrieved user profile")
            return result
        except AudiobookshelfError as e:
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
            >>> await client.update_user_profile({"username": "newname"})
        """
        logger.info("Updating user profile")

        try:
            result = await self._request("PATCH", "/me", json=profile_data)
            logger.info("Successfully updated user profile")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to update user profile: {str(e)}")
            raise

    async def get_user_settings(self) -> Dict[str, Any]:
        """
        Get current user settings.

        Returns:
            User settings data

        Example:
            >>> settings = await client.get_user_settings()
        """
        logger.info("Getting user settings")

        try:
            result = await self._request("GET", "/me/settings")
            logger.info("Successfully retrieved user settings")
            return result
        except AudiobookshelfError as e:
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
            >>> await client.update_user_settings({"playbackRate": 1.25})
        """
        logger.info("Updating user settings")

        try:
            result = await self._request("PATCH", "/me/settings", json=settings_data)
            logger.info("Successfully updated user settings")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to update user settings: {str(e)}")
            raise

    async def get_user_stats(self) -> Dict[str, Any]:
        """
        Get current user statistics.

        Returns:
            User statistics data

        Example:
            >>> stats = await client.get_user_stats()
            >>> print(f"Books completed: {stats.get('booksCompleted', 0)}")
        """
        logger.info("Getting user stats")

        try:
            result = await self._request("GET", "/me/stats")
            logger.info("Successfully retrieved user stats")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to get user stats: {str(e)}")
            raise

    async def get_user_permissions(self) -> Dict[str, Any]:
        """
        Get current user permissions.

        Returns:
            User permissions data

        Example:
            >>> permissions = await client.get_user_permissions()
        """
        logger.info("Getting user permissions")

        try:
            result = await self._request("GET", "/me/permissions")
            logger.info("Successfully retrieved user permissions")
            return result
        except AudiobookshelfError as e:
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
            >>> await client.change_password("oldpass", "newpass")
        """
        logger.info("Changing user password")

        payload = {
            "currentPassword": current_password,
            "newPassword": new_password,
        }

        try:
            await self._request("PATCH", "/me/password", json=payload)
            logger.info("Successfully changed password")
            return True
        except AudiobookshelfError as e:
            logger.error(f"Failed to change password: {str(e)}")
            raise

    # ========================================
    # BACKUP MANAGEMENT
    # ========================================

    async def create_backup(self, backup_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new backup.

        Args:
            backup_data: Backup configuration data

        Returns:
            Backup creation result

        Example:
            >>> backup = await client.create_backup({"name": "Daily Backup"})
        """
        logger.info("Creating backup")

        try:
            result = await self._request("POST", "/api/backups", json=backup_data)
            logger.info("Successfully created backup")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to create backup: {str(e)}")
            raise

    async def get_backups(self) -> List[Dict[str, Any]]:
        """
        Get all backups.

        Returns:
            List of backup data

        Example:
           
            >>> backups = await client.get_backups()
            >>> print(f"Found {len(backups)} backups")
        """
        logger.info("Getting backups")

        try:
            response = await self._request("GET", "/api/backups")
            backups = response.get("backups", [])
            logger.info(f"Found {len(backups)} backups")
            return backups
        except AudiobookshelfError as e:
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
            >>> backup = await client.get_backup("backup123")
        """
        logger.info(f"Getting backup: {backup_id}")

        try:
            result = await self._request("GET", f"/api/backups/{backup_id}")
            logger.info(f"Successfully retrieved backup {backup_id}")
            return result
        except AudiobookshelfError as e:
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
            >>> await client.update_backup("backup123", {"name": "New Name"})
        """
        logger.info(f"Updating backup: {backup_id}")

        try:
            result = await self._request("PATCH", f"/api/backups/{backup_id}", json=backup_data)
            logger.info(f"Successfully updated backup {backup_id}")
            return result
        except AudiobookshelfError as e:
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
            >>> await client.delete_backup("backup123")
        """
        logger.info(f"Deleting backup: {backup_id}")

        try:
            await self._request("DELETE", f"/api/backups/{backup_id}")
            logger.info(f"Successfully deleted backup {backup_id}")
            return True
        except AudiobookshelfError as e:
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
            >>> result = await client.run_backup("backup123")
        """
        logger.info(f"Running backup: {backup_id}")

        try:
            result = await self._request("POST", f"/api/backups/{backup_id}/run")
            logger.info(f"Successfully started backup {backup_id}")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to run backup {backup_id}: {str(e)}")
            raise

    # ========================================
    # RSS FEED MANAGEMENT
    # ========================================

    async def create_rss_feed(self, feed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new RSS feed.

        Args:
            feed_data: RSS feed configuration data

        Returns:
            Created RSS feed data

        Example:
            >>> feed = await client.create_rss_feed({
            ...     "title": "My Feed",
            ...     "url": "https://example.com/feed.xml"
            ... })
        """
        logger.info("Creating RSS feed")

        try:
            result = await self._request("POST", "/api/feeds", json=feed_data)
            logger.info("Successfully created RSS feed")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to create RSS feed: {str(e)}")
            raise

    async def get_rss_feeds(self) -> List[Dict[str, Any]]:
        """
        Get all RSS feeds.

        Returns:
            List of RSS feed data

        Example:
            >>> feeds = await client.get_rss_feeds()
            >>> print(f"Found {len(feeds)} RSS feeds")
        """
        logger.info("Getting RSS feeds")

        try:
            response = await self._request("GET", "/api/feeds")
            feeds = response.get("feeds", [])
            logger.info(f"Found {len(feeds)} RSS feeds")
            return feeds
        except AudiobookshelfError as e:
            logger.error(f"Failed to get RSS feeds: {str(e)}")
            raise

    async def update_rss_feed(self, feed_id: str, feed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an RSS feed.

        Args:
            feed_id: RSS feed ID
            feed_data: Updated feed data

        Returns:
            Updated RSS feed data

        Example:
            >>> await client.update_rss_feed("feed123", {"title": "New Title"})
        """
        logger.info(f"Updating RSS feed: {feed_id}")

        try:
            result = await self._request("PATCH", f"/api/feeds/{feed_id}", json=feed_data)
            logger.info(f"Successfully updated RSS feed {feed_id}")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to update RSS feed {feed_id}: {str(e)}")
            raise

    async def delete_rss_feed(self, feed_id: str) -> bool:
        """
        Delete an RSS feed.

        Args:
            feed_id: RSS feed ID to delete

        Returns:
            True if successful

        Example:
            >>> await client.delete_rss_feed("feed123")
        """
        logger.info(f"Deleting RSS feed: {feed_id}")

        try:
            await self._request("DELETE", f"/api/feeds/{feed_id}")
            logger.info(f"Successfully deleted RSS feed {feed_id}")
            return True
        except AudiobookshelfError as e:
            logger.error(f"Failed to delete RSS feed {feed_id}: {str(e)}")
            raise

    # ========================================
    # API KEY MANAGEMENT
    # ========================================

    async def create_api_key(self, key_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new API key.

        Args:
            key_data: API key configuration data

        Returns:
            Created API key data

        Example:
            >>> key = await client.create_api_key({
            ...     "name": "My App",
            ...     "permissions": ["read", "write"]
            ... })
        """
        logger.info("Creating API key")

        try:
            result = await self._request("POST", "/api/keys", json=key_data)
            logger.info("Successfully created API key")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to create API key: {str(e)}")
            raise

    async def get_api_keys(self) -> List[Dict[str, Any]]:
        """
        Get all API keys.

        Returns:
            List of API key data

        Example:
            >>> keys = await client.get_api_keys()
            >>> print(f"Found {len(keys)} API keys")
        """
        logger.info("Getting API keys")

        try:
            response = await self._request("GET", "/api/keys")
            keys = response.get("keys", [])
            logger.info(f"Found {len(keys)} API keys")
            return keys
        except AudiobookshelfError as e:
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
            >>> await client.update_api_key("key123", {"name": "New Name"})
        """
        logger.info(f"Updating API key: {key_id}")

        try:
            result = await self._request("PATCH", f"/api/keys/{key_id}", json=key_data)
            logger.info(f"Successfully updated API key {key_id}")
            return result
        except AudiobookshelfError as e:
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
            >>> await client.delete_api_key("key123")
        """
        logger.info(f"Deleting API key: {key_id}")

        try:
            await self._request("DELETE", f"/api/keys/{key_id}")
            logger.info(f"Successfully deleted API key {key_id}")
            return True
        except AudiobookshelfError as e:
            logger.error(f"Failed to delete API key {key_id}: {str(e)}")
            raise

    # ========================================
    # NOTIFICATIONS MANAGEMENT
    # ========================================

    async def create_notification(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new notification.

        Args:
            notification_data: Notification configuration data

        Returns:
            Created notification data

        Example:
            >>> notification = await client.create_notification({
            ...     "title": "Download Complete",
            ...     "message": "Your book has finished downloading",
            ...     "type": "info"
            ... })
        """
        logger.info("Creating notification")

        try:
            result = await self._request("POST", "/api/notifications", json=notification_data)
            logger.info("Successfully created notification")
            return result
        except AudiobookshelfError as e:
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
            >>> notifications = await client.get_notifications(limit=20)
            >>> print(f"Found {len(notifications)} notifications")
        """
        logger.info(f"Getting notifications (limit: {limit})")

        try:
            response = await self._request("GET", "/api/notifications", params={"limit": limit})
            notifications = response.get("notifications", [])
            logger.info(f"Found {len(notifications)} notifications")
            return notifications
        except AudiobookshelfError as e:
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
            >>> notification = await client.get_notification("notif123")
        """
        logger.info(f"Getting notification: {notification_id}")

        try:
            result = await self._request("GET", f"/api/notifications/{notification_id}")
            logger.info(f"Successfully retrieved notification {notification_id}")
            return result
        except AudiobookshelfError as e:
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
            >>> await client.update_notification("notif123", {"read": True})
        """
        logger.info(f"Updating notification: {notification_id}")

        try:
            result = await self._request("PATCH", f"/api/notifications/{notification_id}", json=notification_data)
            logger.info(f"Successfully updated notification {notification_id}")
            return result
        except AudiobookshelfError as e:
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
            >>> await client.delete_notification("notif123")
        """
        logger.info(f"Deleting notification: {notification_id}")

        try:
            await self._request("DELETE", f"/api/notifications/{notification_id}")
            logger.info(f"Successfully deleted notification {notification_id}")
            return True
        except AudiobookshelfError as e:
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
            >>> await client.mark_notification_read("notif123")
        """
        logger.info(f"Marking notification as read: {notification_id}")

        try:
            result = await self._request("POST", f"/api/notifications/{notification_id}/read")
            logger.info(f"Successfully marked notification {notification_id} as read")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to mark notification {notification_id} as read: {str(e)}")
            raise

    async def mark_all_notifications_read(self) -> Dict[str, Any]:
        """
        Mark all notifications as read.

        Returns:
            Result data

        Example:
            >>> await client.mark_all_notifications_read()
        """
        logger.info("Marking all notifications as read")

        try:
            result = await self._request("POST", "/api/notifications/read-all")
            logger.info("Successfully marked all notifications as read")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to mark all notifications as read: {str(e)}")
            raise

    async def get_notification_settings(self) -> Dict[str, Any]:
        """
        Get notification settings.

        Returns:
            Notification settings data

        Example:
            >>> settings = await client.get_notification_settings()
        """
        logger.info("Getting notification settings")

        try:
            result = await self._request("GET", "/api/notifications/settings")
            logger.info("Successfully retrieved notification settings")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to get notification settings: {str(e)}")
            raise

    # ========================================
    # EMAIL MANAGEMENT
    # ========================================

    async def send_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send an email.

        Args:
            email_data: Email configuration data

        Returns:
            Email send result

        Example:
            >>> result = await client.send_email({
            ...     "to": "user@example.com",
            ...     "subject": "Test Email",
            ...     "body": "Hello World!"
            ... })
        """
        logger.info("Sending email")

        try:
            result = await self._request("POST", "/api/email", json=email_data)
            logger.info("Successfully sent email")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to send email: {str(e)}")
            raise

    async def get_email_settings(self) -> Dict[str, Any]:
        """
        Get email settings.

        Returns:
            Email settings data

        Example:
            >>> settings = await client.get_email_settings()
        """
        logger.info("Getting email settings")

        try:
            result = await self._request("GET", "/api/email/settings")
            logger.info("Successfully retrieved email settings")
            return result
        except AudiobookshelfError as e:
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
            >>> await client.update_email_settings({"smtp_host": "smtp.example.com"})
        """
        logger.info("Updating email settings")

        try:
            result = await self._request("PATCH", "/api/email/settings", json=settings_data)
            logger.info("Successfully updated email settings")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to update email settings: {str(e)}")
            raise

    async def test_email_settings(self) -> Dict[str, Any]:
        """
        Test email settings by sending a test email.

        Returns:
            Test result data

        Example:
            >>> result = await client.test_email_settings()
        """
        logger.info("Testing email settings")

        try:
            result = await self._request("POST", "/api/email/test")
            logger.info("Successfully tested email settings")
            return result
        except AudiobookshelfError as e:
            logger.error(f"Failed to test email settings: {str(e)}")
            raise

    async def close(self):
        """Close client session."""
        if self.session:
            await self.session.close()
            self.session = None