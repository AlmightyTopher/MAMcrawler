"""
Unified Metadata Provider - Multi-source fallback chain

Implements a cascading metadata extraction strategy:
1. PRIMARY: MyAnonamouse (MAM) torrent pages - most complete for audiobooks
2. SECONDARY: Google Books API - good coverage, standardized metadata
3. TERTIARY: Hardcover API - fallback for general book metadata

Each source is queried in order, with fallback to the next if:
- Source fails to return data
- Source returns incomplete data
- Source has no matching entry

This ensures maximum metadata coverage while prioritizing the most accurate source.
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MetadataSource(Enum):
    """Metadata sources in priority order."""
    MAM = "mam"
    GOOGLE_BOOKS = "google_books"
    HARDCOVER = "hardcover"


@dataclass
class MetadataResult:
    """Result of metadata extraction attempt."""
    source: MetadataSource
    success: bool
    metadata: Optional[Dict[str, Any]]
    completeness: float  # 0.0-1.0 indicating how complete the metadata is
    error: Optional[str] = None


class UnifiedMetadataProvider:
    """
    Unified provider that cascades through multiple metadata sources.

    Priority order:
    1. MAM (MyAnonamouse) - most detailed for audiobooks
    2. Google Books API - good coverage, standardized
    3. Hardcover API - general fallback
    """

    def __init__(
        self,
        mam_client: Optional[Any] = None,
        google_books_client: Optional[Any] = None,
        hardcover_client: Optional[Any] = None
    ):
        """
        Initialize with optional clients for each source.

        Args:
            mam_client: MAMMetadataExtractor instance (optional)
            google_books_client: GoogleBooksClient instance (optional)
            hardcover_client: HardcoverClient instance (optional)
        """
        self.mam_client = mam_client
        self.google_books_client = google_books_client
        self.hardcover_client = hardcover_client

        # Metadata completeness weights for each field
        self.field_weights = {
            'title': 0.15,
            'authors': 0.15,
            'narrators': 0.15,  # Critical for audiobooks
            'duration_minutes': 0.15,  # Critical for audiobooks
            'description': 0.10,
            'publisher': 0.10,
            'published_date': 0.05,
            'series': 0.05,
            'isbn': 0.05,
            'is_abridged': 0.05,
        }

    def _calculate_completeness(self, metadata: Dict[str, Any]) -> float:
        """Calculate completeness score (0.0-1.0) for metadata."""
        if not metadata:
            return 0.0

        score = 0.0
        for field, weight in self.field_weights.items():
            if metadata.get(field):
                score += weight

        return min(score, 1.0)

    async def get_metadata(
        self,
        title: str,
        author: str = "",
        mam_torrent_url: str = ""
    ) -> Dict[str, Any]:
        """
        Get metadata with cascading fallback strategy.

        Args:
            title: Book title
            author: Author name (optional)
            mam_torrent_url: Direct MAM torrent URL (optional, skips search)

        Returns:
            Merged metadata dict with source attribution
        """
        all_results = []
        final_metadata = {
            'title': title,
            'sources': [],
            'completeness': 0.0
        }

        # Step 1: Try MAM (primary source)
        if self.mam_client:
            logger.info(f"Attempting MAM extraction for: {title} by {author}")
            mam_result = await self._try_mam(title, author, mam_torrent_url)
            all_results.append(mam_result)

            if mam_result.success and mam_result.metadata:
                logger.info(f"✓ MAM succeeded with {mam_result.completeness:.0%} completeness")
                self._merge_metadata(final_metadata, mam_result.metadata, MetadataSource.MAM)

                # If MAM gives us good data, might skip other sources
                if mam_result.completeness >= 0.75:
                    final_metadata['completeness'] = mam_result.completeness
                    return final_metadata

        # Step 2: Try Google Books (secondary source)
        if self.google_books_client and final_metadata.get('completeness', 0) < 0.80:
            logger.info(f"Attempting Google Books for: {title} by {author}")
            google_result = await self._try_google_books(title, author)
            all_results.append(google_result)

            if google_result.success and google_result.metadata:
                logger.info(f"✓ Google Books succeeded with {google_result.completeness:.0%} completeness")
                self._merge_metadata(final_metadata, google_result.metadata, MetadataSource.GOOGLE_BOOKS)

        # Step 3: Try Hardcover (tertiary source)
        if self.hardcover_client and final_metadata.get('completeness', 0) < 0.70:
            logger.info(f"Attempting Hardcover for: {title} by {author}")
            hardcover_result = await self._try_hardcover(title, author)
            all_results.append(hardcover_result)

            if hardcover_result.success and hardcover_result.metadata:
                logger.info(f"✓ Hardcover succeeded with {hardcover_result.completeness:.0%} completeness")
                self._merge_metadata(final_metadata, hardcover_result.metadata, MetadataSource.HARDCOVER)

        # Calculate final completeness
        final_metadata['completeness'] = self._calculate_completeness(final_metadata)

        # Log results
        logger.info(
            f"Final metadata completeness: {final_metadata['completeness']:.0%} "
            f"from sources: {', '.join(final_metadata.get('sources', []))}"
        )

        return final_metadata

    async def _try_mam(
        self,
        title: str,
        author: str,
        mam_torrent_url: str = ""
    ) -> MetadataResult:
        """Try to extract metadata from MAM."""
        try:
            if not self.mam_client:
                return MetadataResult(
                    source=MetadataSource.MAM,
                    success=False,
                    metadata=None,
                    completeness=0.0,
                    error="MAM client not configured"
                )

            # If we have a direct URL, use it
            if mam_torrent_url:
                metadata = await self.mam_client.extract_from_torrent_url(mam_torrent_url)
            else:
                # Otherwise search MAM
                metadata = await self.mam_client.search_and_extract(title, author)

            if metadata:
                completeness = self._calculate_completeness(metadata)
                return MetadataResult(
                    source=MetadataSource.MAM,
                    success=True,
                    metadata=metadata,
                    completeness=completeness
                )
            else:
                return MetadataResult(
                    source=MetadataSource.MAM,
                    success=False,
                    metadata=None,
                    completeness=0.0,
                    error="No metadata returned"
                )

        except Exception as e:
            logger.error(f"MAM extraction failed: {e}")
            return MetadataResult(
                source=MetadataSource.MAM,
                success=False,
                metadata=None,
                completeness=0.0,
                error=str(e)
            )

    async def _try_google_books(self, title: str, author: str = "") -> MetadataResult:
        """Try to extract metadata from Google Books API."""
        try:
            if not self.google_books_client:
                return MetadataResult(
                    source=MetadataSource.GOOGLE_BOOKS,
                    success=False,
                    metadata=None,
                    completeness=0.0,
                    error="Google Books client not configured"
                )

            metadata = await self.google_books_client.search_and_extract(title, author)

            if metadata:
                completeness = self._calculate_completeness(metadata)
                return MetadataResult(
                    source=MetadataSource.GOOGLE_BOOKS,
                    success=True,
                    metadata=metadata,
                    completeness=completeness
                )
            else:
                return MetadataResult(
                    source=MetadataSource.GOOGLE_BOOKS,
                    success=False,
                    metadata=None,
                    completeness=0.0,
                    error="No metadata returned"
                )

        except Exception as e:
            logger.error(f"Google Books extraction failed: {e}")
            return MetadataResult(
                source=MetadataSource.GOOGLE_BOOKS,
                success=False,
                metadata=None,
                completeness=0.0,
                error=str(e)
            )

    async def _try_hardcover(self, title: str, author: str = "") -> MetadataResult:
        """Try to extract metadata from Hardcover."""
        try:
            if not self.hardcover_client:
                return MetadataResult(
                    source=MetadataSource.HARDCOVER,
                    success=False,
                    metadata=None,
                    completeness=0.0,
                    error="Hardcover client not configured"
                )

            # Hardcover extraction (simplified - actual implementation would call real API)
            metadata = None

            if metadata:
                completeness = self._calculate_completeness(metadata)
                return MetadataResult(
                    source=MetadataSource.HARDCOVER,
                    success=True,
                    metadata=metadata,
                    completeness=completeness
                )
            else:
                return MetadataResult(
                    source=MetadataSource.HARDCOVER,
                    success=False,
                    metadata=None,
                    completeness=0.0,
                    error="No metadata returned"
                )

        except Exception as e:
            logger.error(f"Hardcover extraction failed: {e}")
            return MetadataResult(
                source=MetadataSource.HARDCOVER,
                success=False,
                metadata=None,
                completeness=0.0,
                error=str(e)
            )

    def _merge_metadata(
        self,
        target: Dict[str, Any],
        source: Dict[str, Any],
        source_name: MetadataSource
    ):
        """
        Merge source metadata into target, preferring existing non-None values.

        This implements quality preservation - only adds/overwrites if:
        - Field is missing in target
        - New data is more complete
        - New data is specifically audiobook-related (narrator, duration)
        """
        # List of audiobook-specific fields that should always be imported
        audiobook_fields = {'narrators', 'duration_minutes', 'is_abridged'}

        for field, value in source.items():
            if field in ('source', 'sources', 'torrent_url', 'extracted_at', 'completeness'):
                # Skip metadata fields
                continue

            existing = target.get(field)

            # Always import audiobook-specific fields
            if field in audiobook_fields and value is not None and not existing:
                target[field] = value
                logger.debug(f"Added {field} from {source_name.value}: {value}")

            # For other fields, only update if target is empty
            elif existing is None and value is not None:
                target[field] = value
                logger.debug(f"Added {field} from {source_name.value}: {value}")

        # Track source
        if 'sources' not in target:
            target['sources'] = []
        if source_name.value not in target['sources']:
            target['sources'].append(source_name.value)

    async def get_metadata_parallel(
        self,
        books: List[tuple]
    ) -> List[Dict[str, Any]]:
        """
        Extract metadata for multiple books in parallel.

        Args:
            books: List of (title, author) tuples

        Returns:
            List of metadata dicts
        """
        tasks = [
            self.get_metadata(title, author)
            for title, author in books
        ]
        return await asyncio.gather(*tasks)
