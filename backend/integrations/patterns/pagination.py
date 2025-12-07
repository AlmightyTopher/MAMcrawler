"""
Pagination pattern for offset/limit-based APIs.

Provides a mixin class for API clients that support paginated responses
with offset/limit query parameters.

Usage:
    >>> class MyApiClient(AuthenticatedAsyncClient, PaginationMixin):
    ...     async def get_items(self, **kwargs):
    ...         return await self.paginate(
    ...             endpoint="/api/items",
    ...             limit=100,
    ...             results_key="items",
    ...             total_key="total",
    ...             **kwargs
    ...         )
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PaginationMixin:
    """
    Mixin for handling pagination in API clients.

    Provides paginate() method for APIs that use offset/limit pagination.
    Automatically handles:
    - Multiple page fetches
    - Tracking total items
    - Stopping when all items received
    - Customizable result/total key names

    Subclass must:
    - Implement _request(method, endpoint, **kwargs) method
    - Optionally override paginate() for custom pagination logic

    Example:
        >>> class LibraryClient(AuthenticatedAsyncClient, PaginationMixin):
        ...     async def get_all_books(self):
        ...         return await self.paginate(
        ...             endpoint="/api/libraries/lib1/items",
        ...             limit=100,
        ...             results_key="results",
        ...             total_key="total"
        ...         )
        ...
        >>> async with LibraryClient("http://localhost:13378", token) as client:
        ...     books = await client.get_all_books()
        ...     print(f"Found {len(books)} books")
    """

    async def paginate(
        self,
        endpoint: str,
        limit: int = 100,
        offset: int = 0,
        results_key: str = "results",
        total_key: str = "total",
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all results from a paginated endpoint.

        Automatically handles pagination by making multiple requests
        with increasing offsets until all results are retrieved.

        Args:
            endpoint: API endpoint path (e.g., "/api/items")
            limit: Items per page (default: 100)
            offset: Starting offset (default: 0)
            results_key: Key in response containing results list
                        (default: "results")
            total_key: Key in response containing total count
                      (default: "total")
            **kwargs: Additional parameters passed to _request()
                     (e.g., params={"filter": "active"})

        Returns:
            List of all items across all pages

        Raises:
            RequestError: If any request fails

        Example:
            >>> # Get all books with optional filters
            >>> books = await client.paginate(
            ...     endpoint="/api/items",
            ...     limit=50,
            ...     results_key="libraryItems",
            ...     total_key="total",
            ...     params={"filter": "completed"}
            ... )
        """
        all_items = []
        current_offset = offset

        while True:
            # Add pagination params
            params = kwargs.get("params", {}).copy()
            params["limit"] = limit
            params["offset"] = current_offset
            kwargs["params"] = params

            logger.debug(
                f"Fetching {endpoint} with offset={current_offset}, limit={limit}"
            )

            # Make request
            response = await self._request("GET", endpoint, **kwargs)

            # Extract results
            items = response.get(results_key, [])
            all_items.extend(items)

            # Check if we have all results
            total = response.get(total_key, 0)
            if current_offset + len(items) >= total:
                logger.debug(f"Pagination complete: {len(all_items)} total items")
                break

            # Move to next page
            current_offset += len(items)

        return all_items

    async def paginate_with_callback(
        self,
        endpoint: str,
        callback,
        limit: int = 100,
        offset: int = 0,
        results_key: str = "results",
        total_key: str = "total",
        **kwargs,
    ) -> int:
        """
        Fetch paginated results and call callback for each page.

        Useful for processing large datasets without loading all into memory.

        Args:
            endpoint: API endpoint path
            callback: Async function to call for each page result list
            limit: Items per page
            offset: Starting offset
            results_key: Key in response containing results
            total_key: Key in response containing total count
            **kwargs: Additional parameters for _request()

        Returns:
            Total number of items processed

        Example:
            >>> async def process_page(items):
            ...     for item in items:
            ...         await db.save(item)
            ...
            >>> total = await client.paginate_with_callback(
            ...     endpoint="/api/items",
            ...     callback=process_page,
            ...     limit=50
            ... )
            >>> print(f"Processed {total} items")
        """
        total_items = 0
        current_offset = offset

        while True:
            # Add pagination params
            params = kwargs.get("params", {}).copy()
            params["limit"] = limit
            params["offset"] = current_offset
            kwargs["params"] = params

            logger.debug(
                f"Fetching {endpoint} with offset={current_offset}, limit={limit}"
            )

            # Make request
            response = await self._request("GET", endpoint, **kwargs)

            # Extract results
            items = response.get(results_key, [])

            # Call callback for this page
            if items:
                await callback(items)
                total_items += len(items)

            # Check if we have all results
            total = response.get(total_key, 0)
            if current_offset + len(items) >= total:
                logger.debug(f"Pagination complete: {total_items} total items processed")
                break

            # Move to next page
            current_offset += len(items)

        return total_items


__all__ = ["PaginationMixin"]
