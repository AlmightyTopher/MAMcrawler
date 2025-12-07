"""
Comprehensive tests for PaginationMixin pattern.

Tests cover:
- Basic pagination with multiple pages
- Single page results
- Empty results
- Custom field names for results/total
- Pagination with query parameters
- Pagination with callback function
- Error handling during pagination
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.integrations.patterns.pagination import PaginationMixin
from backend.integrations.patterns.authenticated_client import AuthenticatedAsyncClient


class MockPaginatedClient(AuthenticatedAsyncClient, PaginationMixin):
    """Mock client for testing pagination."""

    async def _request(self, method, endpoint, **kwargs):
        """Mock _request method."""
        # This will be mocked in tests
        pass


class TestPaginationMixin:
    """Test suite for PaginationMixin."""

    @pytest.fixture
    def paginated_client(self):
        """Create a test client with pagination."""
        return MockPaginatedClient("http://api.example.com")

    @pytest.mark.asyncio
    async def test_paginate_single_page(self, paginated_client):
        """Test pagination with single page of results."""
        # Mock response with all results on first page
        paginated_client._request = AsyncMock(return_value={
            "results": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
            "total": 3,
        })

        result = await paginated_client.paginate(
            endpoint="/api/items",
            limit=100,
        )

        assert result == [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        paginated_client._request.assert_called_once()

    @pytest.mark.asyncio
    async def test_paginate_multiple_pages(self, paginated_client):
        """Test pagination with multiple pages."""
        # Mock responses for multiple pages
        responses = [
            {
                "results": [{"id": "1"}, {"id": "2"}],
                "total": 5,
            },
            {
                "results": [{"id": "3"}, {"id": "4"}],
                "total": 5,
            },
            {
                "results": [{"id": "5"}],
                "total": 5,
            },
        ]

        paginated_client._request = AsyncMock(side_effect=responses)

        result = await paginated_client.paginate(
            endpoint="/api/items",
            limit=2,
        )

        assert len(result) == 5
        assert result[0]["id"] == "1"
        assert result[4]["id"] == "5"
        assert paginated_client._request.call_count == 3

    @pytest.mark.asyncio
    async def test_paginate_empty_results(self, paginated_client):
        """Test pagination with empty results."""
        paginated_client._request = AsyncMock(return_value={
            "results": [],
            "total": 0,
        })

        result = await paginated_client.paginate(endpoint="/api/items")

        assert result == []

    @pytest.mark.asyncio
    async def test_paginate_custom_field_names(self, paginated_client):
        """Test pagination with custom result/total field names."""
        paginated_client._request = AsyncMock(return_value={
            "items": [{"id": "1"}, {"id": "2"}],
            "count": 2,
        })

        result = await paginated_client.paginate(
            endpoint="/api/items",
            results_key="items",
            total_key="count",
        )

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_paginate_with_query_params(self, paginated_client):
        """Test pagination preserves query parameters."""
        paginated_client._request = AsyncMock(return_value={
            "results": [{"id": "1"}],
            "total": 1,
        })

        await paginated_client.paginate(
            endpoint="/api/items",
            params={"filter": "active", "sort": "name"},
        )

        # Verify params are included in request
        call_kwargs = paginated_client._request.call_args[1]
        assert call_kwargs["params"]["filter"] == "active"
        assert call_kwargs["params"]["sort"] == "name"
        assert call_kwargs["params"]["limit"] == 100
        assert call_kwargs["params"]["offset"] == 0

    @pytest.mark.asyncio
    async def test_paginate_offset_progression(self, paginated_client):
        """Test pagination offset increases correctly."""
        responses = [
            {"results": [{"id": str(i)} for i in range(2)], "total": 5},
            {"results": [{"id": str(i)} for i in range(2, 4)], "total": 5},
            {"results": [{"id": "4"}], "total": 5},
        ]

        paginated_client._request = AsyncMock(side_effect=responses)

        await paginated_client.paginate(
            endpoint="/api/items",
            limit=2,
        )

        # Check offset progression
        calls = paginated_client._request.call_args_list
        assert calls[0][1]["params"]["offset"] == 0
        assert calls[1][1]["params"]["offset"] == 2
        assert calls[2][1]["params"]["offset"] == 4

    @pytest.mark.asyncio
    async def test_paginate_with_custom_offset(self, paginated_client):
        """Test pagination with custom starting offset."""
        # Return all remaining results to avoid additional pagination
        paginated_client._request = AsyncMock(return_value={
            "results": [{"id": "3"}, {"id": "4"}, {"id": "5"}],
            "total": 5,
        })

        result = await paginated_client.paginate(
            endpoint="/api/items",
            limit=10,
            offset=2,
        )

        # Verify the custom offset was used (first call should have offset=2)
        first_call_kwargs = paginated_client._request.call_args_list[0][1]
        assert first_call_kwargs["params"]["offset"] == 2
        # Verify we got the expected results
        assert len(result) == 3
        assert result[0]["id"] == "3"

    @pytest.mark.asyncio
    async def test_paginate_with_callback(self, paginated_client):
        """Test pagination with callback function."""
        responses = [
            {"results": [{"id": "1"}, {"id": "2"}], "total": 4},
            {"results": [{"id": "3"}, {"id": "4"}], "total": 4},
        ]

        paginated_client._request = AsyncMock(side_effect=responses)

        processed_items = []

        async def callback(items):
            processed_items.extend(items)

        total = await paginated_client.paginate_with_callback(
            endpoint="/api/items",
            callback=callback,
            limit=2,
        )

        assert total == 4
        assert len(processed_items) == 4
        assert processed_items[0]["id"] == "1"
        assert processed_items[3]["id"] == "4"

    @pytest.mark.asyncio
    async def test_paginate_with_callback_empty(self, paginated_client):
        """Test pagination with callback on empty results."""
        paginated_client._request = AsyncMock(return_value={
            "results": [],
            "total": 0,
        })

        processed_items = []

        async def callback(items):
            processed_items.extend(items)

        total = await paginated_client.paginate_with_callback(
            endpoint="/api/items",
            callback=callback,
        )

        assert total == 0
        assert len(processed_items) == 0

    @pytest.mark.asyncio
    async def test_paginate_callback_exception_propagates(self, paginated_client):
        """Test that exceptions in callback are propagated."""
        paginated_client._request = AsyncMock(return_value={
            "results": [{"id": "1"}],
            "total": 1,
        })

        async def failing_callback(items):
            raise ValueError("Callback error")

        with pytest.raises(ValueError, match="Callback error"):
            await paginated_client.paginate_with_callback(
                endpoint="/api/items",
                callback=failing_callback,
            )

    @pytest.mark.asyncio
    async def test_paginate_request_failure(self, paginated_client):
        """Test pagination handles request failures."""
        from backend.integrations.patterns.authenticated_client import RequestError

        paginated_client._request = AsyncMock(side_effect=RequestError("API Error"))

        with pytest.raises(RequestError):
            await paginated_client.paginate(endpoint="/api/items")

    @pytest.mark.asyncio
    async def test_paginate_large_dataset(self, paginated_client):
        """Test pagination with large dataset."""
        # Simulate 10 pages of 100 items each
        responses = []
        for page in range(10):
            start_id = page * 100
            responses.append({
                "results": [{"id": str(i)} for i in range(start_id, start_id + 100)],
                "total": 1000,
            })

        paginated_client._request = AsyncMock(side_effect=responses)

        result = await paginated_client.paginate(
            endpoint="/api/items",
            limit=100,
        )

        assert len(result) == 1000
        assert result[0]["id"] == "0"
        assert result[999]["id"] == "999"

    @pytest.mark.asyncio
    async def test_paginate_missing_total_defaults_to_zero(self, paginated_client):
        """Test pagination when response missing total key."""
        paginated_client._request = AsyncMock(return_value={
            "results": [{"id": "1"}],
            # Missing "total" key
        })

        result = await paginated_client.paginate(endpoint="/api/items")

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_paginate_missing_results_defaults_to_empty(self, paginated_client):
        """Test pagination when response missing results key."""
        paginated_client._request = AsyncMock(return_value={
            "total": 0,
            # Missing "results" key
        })

        result = await paginated_client.paginate(endpoint="/api/items")

        assert result == []

    @pytest.mark.asyncio
    async def test_paginate_request_parameters_preserved(self, paginated_client):
        """Test that custom request parameters are preserved."""
        paginated_client._request = AsyncMock(return_value={
            "results": [{"id": "1"}],
            "total": 1,
        })

        await paginated_client.paginate(
            endpoint="/api/items",
            headers={"X-Custom": "value"},
            params={"filter": "active"},
        )

        call_kwargs = paginated_client._request.call_args[1]
        assert call_kwargs["headers"] == {"X-Custom": "value"}
        assert "filter" in call_kwargs["params"]

    @pytest.mark.asyncio
    async def test_paginate_respects_limit_parameter(self, paginated_client):
        """Test pagination respects the limit parameter."""
        paginated_client._request = AsyncMock(return_value={
            "results": [{"id": str(i)} for i in range(50)],
            "total": 50,
        })

        await paginated_client.paginate(
            endpoint="/api/items",
            limit=50,
        )

        call_kwargs = paginated_client._request.call_args[1]
        assert call_kwargs["params"]["limit"] == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
