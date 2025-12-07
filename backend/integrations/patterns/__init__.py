"""
Reusable patterns for API clients and integrations.

This package contains common patterns extracted from multiple API client
implementations for reuse across the codebase.

Patterns:
- AuthenticatedAsyncClient: Base class for authenticated HTTP clients
- PaginationMixin: Pagination support for offset/limit-based APIs
- BatchOperationsMixin: Batch operation wrapper with error aggregation
- MetadataMapper: Field mapping and transformation framework
"""

from .authenticated_client import (
    AuthenticatedAsyncClient,
    AuthenticationError,
    RequestError,
)
from .pagination import PaginationMixin
from .batch_operations import BatchOperationsMixin
from .metadata_mapper import MetadataMapper

__all__ = [
    # Authenticated client
    "AuthenticatedAsyncClient",
    "AuthenticationError",
    "RequestError",
    # Pagination
    "PaginationMixin",
    # Batch operations
    "BatchOperationsMixin",
    # Metadata mapping
    "MetadataMapper",
]
