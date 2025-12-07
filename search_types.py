#!/usr/bin/env python3
"""
Common types and interfaces for the unified search system.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum


class SearchMode(Enum):
    """Search modes with different priorities and behaviors"""
    QUICK = "quick"           # Fast search, fewer results, prioritize quality
    COMPREHENSIVE = "comprehensive"  # Thorough search, more results, broader coverage
    BATCH = "batch"           # Optimized for bulk operations, prioritize reliability


@dataclass
class SearchQuery:
    """Standardized search query structure"""
    query: str
    mode: SearchMode = SearchMode.QUICK
    limit: int = 20
    author: Optional[str] = None
    series: Optional[str] = None
    genre: Optional[str] = None
    min_confidence: float = 0.0
    include_metadata: bool = True
    timeout: int = 30


@dataclass
class SearchResult:
    """Standardized search result structure"""
    provider: str
    query: str
    title: str
    author: Optional[str] = None
    series_name: Optional[str] = None
    series_position: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    confidence: float = 0.5
    magnet_link: Optional[str] = None
    size: Optional[int] = None  # Size in bytes
    seeders: Optional[int] = None
    leechers: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'provider': self.provider,
            'query': self.query,
            'title': self.title,
            'author': self.author,
            'series_name': self.series_name,
            'series_position': self.series_position,
            'url': self.url,
            'description': self.description,
            'confidence': self.confidence,
            'magnet_link': self.magnet_link,
            'size': self.size,
            'seeders': self.seeders,
            'leechers': self.leechers,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchResult':
        """Create from dictionary"""
        return cls(**data)


class SearchProviderInterface(ABC):
    """
    Abstract base class for all search providers.

    Defines the common interface that all search providers must implement.
    """

    PROVIDER_TYPE: str = "base"
    CAPABILITIES: List[str] = []
    RATE_LIMITS: Dict[str, Union[int, float]] = {
        "requests_per_minute": 60,
        "delay_seconds": 1
    }
    CONFIG_REQUIRED: List[str] = []

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._validate_config()

    def _validate_config(self):
        """Validate that required configuration is present"""
        missing = []
        for required in self.CONFIG_REQUIRED:
            if required not in self.config or self.config[required] is None:
                missing.append(required)

        if missing:
            raise ValueError(f"Missing required configuration for {self.PROVIDER_TYPE}: {missing}")

    @abstractmethod
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Perform search using this provider

        Args:
            query: Standardized search query

        Returns:
            List of search results in standardized format
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is healthy and accessible

        Returns:
            True if healthy, False otherwise
        """
        pass

    async def __aenter__(self):
        """Context manager entry - setup resources"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources"""
        pass


class CacheInterface(ABC):
    """
    Abstract base class for caching implementations
    """

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set cached value with optional TTL"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete cached value"""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cached values"""
        pass

    @abstractmethod
    async def cleanup(self):
        """Cleanup resources"""
        pass


# Provider capability constants
class ProviderCapabilities:
    """Constants for provider capabilities"""
    METADATA_SEARCH = "metadata_search"
    LIBRARY_SEARCH = "library_search"
    TORRENT_SEARCH = "torrent_search"
    INDEXER_SEARCH = "indexer_search"
    VECTOR_SEARCH = "vector_search"
    SEMANTIC_SEARCH = "semantic_search"
    LOCAL_KNOWLEDGE = "local_knowledge"
    MAGNET_EXTRACTION = "magnet_extraction"
    AUTHOR_SEARCH = "author_search"
    BOOK_VERIFICATION = "book_verification"
    COLLECTION_SEARCH = "collection_search"


# Result quality indicators
class ResultQuality:
    """Constants for result quality assessment"""
    EXCELLENT = 0.9
    GOOD = 0.7
    FAIR = 0.5
    POOR = 0.3
    UNRELIABLE = 0.1

    @staticmethod
    def from_seeders(seeders: int) -> float:
        """Calculate quality based on number of seeders"""
        if seeders >= 50:
            return ResultQuality.EXCELLENT
        elif seeders >= 20:
            return ResultQuality.GOOD
        elif seeders >= 5:
            return ResultQuality.FAIR
        elif seeders >= 1:
            return ResultQuality.POOR
        else:
            return ResultQuality.UNRELIABLE

    @staticmethod
    def from_size_mb(size_mb: float) -> float:
        """Calculate quality based on file size (audiobooks are typically 100MB-2GB)"""
        if 100 <= size_mb <= 2000:
            return ResultQuality.EXCELLENT
        elif 50 <= size_mb <= 3000:
            return ResultQuality.GOOD
        elif 10 <= size_mb <= 5000:
            return ResultQuality.FAIR
        else:
            return ResultQuality.POOR