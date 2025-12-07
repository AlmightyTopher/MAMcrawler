"""
Batch operations pattern for handling multiple items in one operation.

Provides a mixin for API clients that need to perform batch operations
on collections of items, with proper error handling and aggregation.

Usage:
    >>> class MyApiClient(AuthenticatedAsyncClient, BatchOperationsMixin):
    ...     async def add_items_to_collection(self, collection_id, item_ids):
    ...         return await self.batch_operation(
    ...             items=item_ids,
    ...             operation=lambda id: self.add_to_collection(collection_id, id)
    ...         )
"""

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class BatchOperationsMixin:
    """
    Mixin for handling batch operations on multiple items.

    Provides batch_operation() method for executing operations on
    multiple items and aggregating results with error handling.

    Automatically:
    - Executes operation for each item
    - Collects successful results
    - Collects failed items with error details
    - Provides detailed summary of batch operation

    Subclass must:
    - Implement the async operation function

    Example:
        >>> class LibraryClient(AuthenticatedAsyncClient, BatchOperationsMixin):
        ...     async def add_book_to_collection(self, collection_id, book_id):
        ...         return await self._request(
        ...             "POST",
        ...             f"/api/collections/{collection_id}/books",
        ...             json={"bookId": book_id}
        ...         )
        ...
        ...     async def batch_add_books(self, collection_id, book_ids):
        ...         return await self.batch_operation(
        ...             items=book_ids,
        ...             operation=lambda id: self.add_book_to_collection(
        ...                 collection_id, id
        ...             ),
        ...             description="Adding books to collection"
        ...         )
        ...
        >>> async with LibraryClient(...) as client:
        ...     result = await client.batch_add_books("col1", ["book1", "book2", "book3"])
        ...     print(f"Success: {len(result['succeeded'])}, Failed: {len(result['failed'])}")
    """

    async def batch_operation(
        self,
        items: List[Any],
        operation: Callable,
        description: Optional[str] = None,
        stop_on_error: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute an operation on multiple items.

        Runs the provided operation for each item and aggregates results,
        collecting both successful and failed items.

        Args:
            items: List of items to process
            operation: Async function that takes an item and performs operation
            description: Human-readable description of the batch operation
            stop_on_error: If True, stop processing on first error
                          (default: False, process all items)

        Returns:
            Dictionary with structure:
            {
                "succeeded": [item1, item2, ...],
                "failed": [
                    {"item": item, "error": "error message"},
                    ...
                ],
                "total": int,
                "success_count": int,
                "failure_count": int,
                "description": str
            }

        Example:
            >>> result = await client.batch_operation(
            ...     items=["user1", "user2", "user3"],
            ...     operation=lambda uid: delete_user(uid),
            ...     description="Deleting users"
            ... )
            >>> print(f"Deleted {result['success_count']} users")
            >>> if result['failed']:
            ...     print(f"Failed to delete {result['failure_count']} users:")
            ...     for failure in result['failed']:
            ...         print(f"  {failure['item']}: {failure['error']}")
        """
        results = {
            "succeeded": [],
            "failed": [],
            "total": len(items),
            "success_count": 0,
            "failure_count": 0,
            "description": description or "Batch operation",
        }

        logger.info(f"Starting batch operation: {results['description']} ({len(items)} items)")

        for i, item in enumerate(items, 1):
            try:
                logger.debug(f"Processing item {i}/{len(items)}: {item}")
                await operation(item)
                results["succeeded"].append(item)
                results["success_count"] += 1
                logger.debug(f"Successfully processed: {item}")

            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Failed to process item: {item}, error: {error_msg}")
                results["failed"].append({
                    "item": item,
                    "error": error_msg,
                })
                results["failure_count"] += 1

                if stop_on_error:
                    logger.error(f"Stopping batch operation due to error: {error_msg}")
                    break

        # Log summary
        logger.info(
            f"Batch operation complete: {results['success_count']}/{results['total']} "
            f"succeeded, {results['failure_count']} failed"
        )

        return results

    async def batch_operation_with_limit(
        self,
        items: List[Any],
        operation: Callable,
        concurrency: int = 5,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute an operation on multiple items with concurrency limit.

        Useful for operations that can be parallelized but need rate limiting
        to avoid overwhelming the server.

        Args:
            items: List of items to process
            operation: Async function that takes an item
            concurrency: Maximum concurrent operations (default: 5)
            description: Human-readable description

        Returns:
            Same structure as batch_operation()

        Example:
            >>> result = await client.batch_operation_with_limit(
            ...     items=["url1", "url2", "url3", ...],
            ...     operation=lambda url: download_file(url),
            ...     concurrency=3,
            ...     description="Downloading files"
            ... )
        """
        import asyncio

        results = {
            "succeeded": [],
            "failed": [],
            "total": len(items),
            "success_count": 0,
            "failure_count": 0,
            "description": description or "Batch operation with limit",
        }

        logger.info(
            f"Starting batch operation with concurrency={concurrency}: "
            f"{results['description']} ({len(items)} items)"
        )

        # Process items in batches
        semaphore = asyncio.Semaphore(concurrency)

        async def limited_operation(item):
            async with semaphore:
                try:
                    await operation(item)
                    results["succeeded"].append(item)
                    results["success_count"] += 1
                    logger.debug(f"Successfully processed: {item}")
                except Exception as e:
                    error_msg = str(e)
                    logger.warning(f"Failed to process: {item}, error: {error_msg}")
                    results["failed"].append({
                        "item": item,
                        "error": error_msg,
                    })
                    results["failure_count"] += 1

        # Create tasks for all items
        tasks = [limited_operation(item) for item in items]

        # Execute all tasks
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(
            f"Batch operation complete: {results['success_count']}/{results['total']} "
            f"succeeded, {results['failure_count']} failed"
        )

        return results


__all__ = ["BatchOperationsMixin"]
