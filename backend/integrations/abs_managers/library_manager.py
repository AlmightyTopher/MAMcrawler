"""
Audiobookshelf Library Management

Manages library items, book metadata, searches, and library operations.
"""

import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)


class LibraryManager:
    """
    Manager for Audiobookshelf library operations.

    Encapsulates all library-related operations including:
    - Fetching library items with pagination
    - Book metadata retrieval and updates
    - Book import and deletion
    - Library scanning and searching
    - Library management

    Args:
        client: Reference to AudiobookshelfClient for making requests
    """

    def __init__(self, client):
        """Initialize library manager with client reference."""
        self.client = client

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
            >>> books = await client.libraries.get_library_items(limit=50)
            >>> print(f"Found {len(books)} books")
        """
        # Get libraries if no library_id specified
        if not library_id:
            libraries = await self.client._request("GET", "/api/libraries")
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

            response = await self.client._request("GET", endpoint, params=params)

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
            book = await self.client._request("GET", endpoint)
            logger.debug(f"Found book: {book.get('media', {}).get('metadata', {}).get('title', 'Unknown')}")
            return book
        except Exception as e:
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
            >>> result = await client.libraries.import_book(
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
            >>> await client.libraries.update_book_metadata(
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
            result = await self.client._request("PATCH", endpoint, json=payload)
            logger.info(f"Successfully updated metadata for {abs_id}")
            return result
        except Exception as e:
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
            libraries = await self.client._request("GET", "/api/libraries")
            if not libraries or not libraries.get("libraries"):
                raise Exception("No libraries found")
            library_id = libraries["libraries"][0]["id"]

        logger.info(f"Triggering scan for library: {library_id}")
        endpoint = f"/api/libraries/{library_id}/scan"

        try:
            result = await self.client._request("POST", endpoint)
            logger.info("Library scan triggered successfully")
            return result
        except Exception as e:
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
            >>> results = await client.libraries.search_books("Foundation Asimov")
            >>> for book in results:
            ...     print(book["media"]["metadata"]["title"])
        """
        logger.info(f"Searching for: {query}")

        endpoint = "/api/search/books"
        params = {"q": query, "limit": limit}

        if library_id:
            params["library"] = library_id

        try:
            response = await self.client._request("GET", endpoint, params=params)
            results = response.get("book", [])  # API returns {"book": [...]}
            logger.info(f"Found {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise

    async def get_libraries(self) -> List[Dict[str, Any]]:
        """
        Get all libraries.

        Returns:
            List of library dictionaries
        """
        logger.info("Fetching libraries")
        response = await self.client._request("GET", "/api/libraries")
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
            result = await self.client._request("DELETE", endpoint, params=params)
            logger.info(f"Successfully deleted book {abs_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to delete book {abs_id}: {str(e)}")
            raise
