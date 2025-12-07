"""
Comprehensive tests for BatchOperationsMixin pattern.

Tests cover:
- Successful batch operations
- Partial failures (some items fail)
- All failures
- Stop on first error
- Concurrent batch operations with limits
- Error aggregation and reporting
- Result structure validation
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from backend.integrations.patterns.batch_operations import BatchOperationsMixin
from backend.integrations.patterns.authenticated_client import AuthenticatedAsyncClient


class MockBatchClient(AuthenticatedAsyncClient, BatchOperationsMixin):
    """Mock client for testing batch operations."""
    pass


class TestBatchOperationsMixin:
    """Test suite for BatchOperationsMixin."""

    @pytest.fixture
    def batch_client(self):
        """Create a test client with batch operations."""
        return MockBatchClient("http://api.example.com")

    @pytest.mark.asyncio
    async def test_batch_all_success(self, batch_client):
        """Test batch operation with all items succeeding."""
        mock_op = AsyncMock()

        result = await batch_client.batch_operation(
            items=["item1", "item2", "item3"],
            operation=mock_op,
            description="Testing batch operation",
        )

        assert result["total"] == 3
        assert result["success_count"] == 3
        assert result["failure_count"] == 0
        assert result["succeeded"] == ["item1", "item2", "item3"]
        assert result["failed"] == []
        assert mock_op.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_partial_failure(self, batch_client):
        """Test batch operation with some items failing."""
        async def mock_op(item):
            if item == "item2":
                raise ValueError("Item 2 failed")

        result = await batch_client.batch_operation(
            items=["item1", "item2", "item3"],
            operation=mock_op,
        )

        assert result["total"] == 3
        assert result["success_count"] == 2
        assert result["failure_count"] == 1
        assert "item1" in result["succeeded"]
        assert "item3" in result["succeeded"]
        assert len(result["failed"]) == 1
        assert result["failed"][0]["item"] == "item2"

    @pytest.mark.asyncio
    async def test_batch_all_failures(self, batch_client):
        """Test batch operation with all items failing."""
        async def mock_op(item):
            raise RuntimeError(f"{item} failed")

        result = await batch_client.batch_operation(
            items=["item1", "item2", "item3"],
            operation=mock_op,
        )

        assert result["total"] == 3
        assert result["success_count"] == 0
        assert result["failure_count"] == 3
        assert result["succeeded"] == []
        assert len(result["failed"]) == 3

    @pytest.mark.asyncio
    async def test_batch_empty_list(self, batch_client):
        """Test batch operation with empty item list."""
        mock_op = AsyncMock()

        result = await batch_client.batch_operation(
            items=[],
            operation=mock_op,
        )

        assert result["total"] == 0
        assert result["success_count"] == 0
        assert result["failure_count"] == 0
        assert result["succeeded"] == []
        assert result["failed"] == []
        mock_op.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_stop_on_error(self, batch_client):
        """Test batch operation stops on first error."""
        call_count = 0

        async def mock_op(item):
            nonlocal call_count
            call_count += 1
            if item == "item2":
                raise ValueError("Stop here")

        result = await batch_client.batch_operation(
            items=["item1", "item2", "item3"],
            operation=mock_op,
            stop_on_error=True,
        )

        # Should stop after item2 fails
        assert call_count == 2
        assert result["success_count"] == 1
        assert result["failure_count"] == 1

    @pytest.mark.asyncio
    async def test_batch_error_messages_preserved(self, batch_client):
        """Test that error messages are preserved in result."""
        async def mock_op(item):
            if item == "item1":
                raise ValueError("Custom error for item1")
            elif item == "item2":
                raise RuntimeError("Custom error for item2")

        result = await batch_client.batch_operation(
            items=["item1", "item2", "item3"],
            operation=mock_op,
        )

        assert result["failed"][0]["error"] == "Custom error for item1"
        assert result["failed"][1]["error"] == "Custom error for item2"

    @pytest.mark.asyncio
    async def test_batch_description_included(self, batch_client):
        """Test batch operation includes description in result."""
        mock_op = AsyncMock()

        result = await batch_client.batch_operation(
            items=["item1"],
            operation=mock_op,
            description="Custom description",
        )

        assert result["description"] == "Custom description"

    @pytest.mark.asyncio
    async def test_batch_description_default(self, batch_client):
        """Test batch operation uses default description."""
        mock_op = AsyncMock()

        result = await batch_client.batch_operation(
            items=["item1"],
            operation=mock_op,
        )

        assert result["description"] == "Batch operation"

    @pytest.mark.asyncio
    async def test_batch_concurrent_with_limit(self, batch_client):
        """Test concurrent batch operations with concurrency limit."""
        concurrent_count = 0
        max_concurrent = 0

        async def mock_op(item):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.01)
            concurrent_count -= 1

        result = await batch_client.batch_operation_with_limit(
            items=["item1", "item2", "item3", "item4", "item5"],
            operation=mock_op,
            concurrency=2,
        )

        assert result["success_count"] == 5
        assert result["failure_count"] == 0
        # Max concurrent should not exceed limit
        assert max_concurrent <= 2

    @pytest.mark.asyncio
    async def test_batch_concurrent_all_success(self, batch_client):
        """Test concurrent batch with all items succeeding."""
        mock_op = AsyncMock()

        result = await batch_client.batch_operation_with_limit(
            items=["item1", "item2", "item3"],
            operation=mock_op,
            concurrency=3,
        )

        assert result["success_count"] == 3
        assert result["failure_count"] == 0
        assert mock_op.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_concurrent_with_failures(self, batch_client):
        """Test concurrent batch handles failures properly."""
        async def mock_op(item):
            if item in ["item2", "item4"]:
                raise ValueError(f"{item} failed")

        result = await batch_client.batch_operation_with_limit(
            items=["item1", "item2", "item3", "item4", "item5"],
            operation=mock_op,
            concurrency=2,
        )

        assert result["success_count"] == 3
        assert result["failure_count"] == 2
        assert len(result["failed"]) == 2

    @pytest.mark.asyncio
    async def test_batch_concurrent_description(self, batch_client):
        """Test concurrent batch includes description."""
        mock_op = AsyncMock()

        result = await batch_client.batch_operation_with_limit(
            items=["item1"],
            operation=mock_op,
            concurrency=1,
            description="Concurrent operation",
        )

        assert result["description"] == "Concurrent operation"

    @pytest.mark.asyncio
    async def test_batch_concurrent_default_concurrency(self, batch_client):
        """Test concurrent batch uses default concurrency."""
        call_times = []
        async def mock_op(item):
            call_times.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.001)

        result = await batch_client.batch_operation_with_limit(
            items=[f"item{i}" for i in range(10)],
            operation=mock_op,
            # No concurrency specified, should use default
        )

        assert result["success_count"] == 10

    @pytest.mark.asyncio
    async def test_batch_result_structure(self, batch_client):
        """Test batch result has correct structure."""
        mock_op = AsyncMock()

        result = await batch_client.batch_operation(
            items=["item1"],
            operation=mock_op,
        )

        # Verify all expected keys are present
        assert "succeeded" in result
        assert "failed" in result
        assert "total" in result
        assert "success_count" in result
        assert "failure_count" in result
        assert "description" in result

        # Verify types
        assert isinstance(result["succeeded"], list)
        assert isinstance(result["failed"], list)
        assert isinstance(result["total"], int)
        assert isinstance(result["success_count"], int)
        assert isinstance(result["failure_count"], int)
        assert isinstance(result["description"], str)

    @pytest.mark.asyncio
    async def test_batch_failed_item_structure(self, batch_client):
        """Test failed items have correct structure."""
        async def mock_op(item):
            raise ValueError("Test error")

        result = await batch_client.batch_operation(
            items=["item1"],
            operation=mock_op,
        )

        assert len(result["failed"]) == 1
        failed_item = result["failed"][0]
        assert "item" in failed_item
        assert "error" in failed_item
        assert failed_item["item"] == "item1"
        assert "Test error" in failed_item["error"]

    @pytest.mark.asyncio
    async def test_batch_operation_with_different_types(self, batch_client):
        """Test batch operation with different item types."""
        mock_op = AsyncMock()

        items = [
            "string_item",
            123,
            {"id": "dict_item"},
            ["list", "item"],
        ]

        result = await batch_client.batch_operation(
            items=items,
            operation=mock_op,
        )

        assert result["success_count"] == 4
        assert result["total"] == 4

    @pytest.mark.asyncio
    async def test_batch_maintains_order(self, batch_client):
        """Test batch operations process items in order."""
        processed_order = []

        async def mock_op(item):
            processed_order.append(item)

        await batch_client.batch_operation(
            items=["item1", "item2", "item3", "item4", "item5"],
            operation=mock_op,
        )

        assert processed_order == ["item1", "item2", "item3", "item4", "item5"]

    @pytest.mark.asyncio
    async def test_batch_large_dataset(self, batch_client):
        """Test batch operation with large number of items."""
        mock_op = AsyncMock()

        items = [f"item{i}" for i in range(1000)]

        result = await batch_client.batch_operation(
            items=items,
            operation=mock_op,
        )

        assert result["total"] == 1000
        assert result["success_count"] == 1000
        assert mock_op.call_count == 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
