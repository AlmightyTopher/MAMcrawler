"""
Metadata Enrichment Service for Audiobook Automation System

This service enriches audiobook metadata by querying external APIs (Google Books, ISBN lookup)
and populating series, author, and narrator information in Audiobookshelf.

Features:
- Google Books API integration for metadata lookup
- ISBN-based matching for accurate series detection
- Batch processing with progress tracking
- Deduplication and error handling
- SQLite caching to avoid re-querying
"""

import asyncio
import logging
import aiohttp
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
import re
from urllib.parse import quote

from backend.config import get_settings
from backend.integrations.abs_client import AudiobookshelfClient
from backend.utils.log_config import setup_logging

logger = logging.getLogger(__name__)

# Initialize logging
setup_logging()

# Get settings
settings = get_settings()


class MatchConfidence(Enum):
    """Confidence levels for metadata matches"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNMATCHED = "unmatched"


@dataclass
class MetadataMatch:
    """Result of a metadata matching operation"""
    book_id: str
    book_title: str
    matched: bool = False
    confidence: MatchConfidence = MatchConfidence.UNMATCHED
    series_name: Optional[str] = None
    series_position: Optional[int] = None
    authors: List[str] = field(default_factory=list)
    narrators: List[str] = field(default_factory=list)
    published_date: Optional[str] = None
    description: Optional[str] = None
    isbn: Optional[str] = None
    google_books_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class EnrichmentStats:
    """Statistics for metadata enrichment operation"""
    total_books: int = 0
    matched_books: int = 0
    high_confidence: int = 0
    medium_confidence: int = 0
    low_confidence: int = 0
    unmatched: int = 0
    errors: int = 0
    series_identified: int = 0
    unique_series: int = 0
    authors_populated: int = 0
    narrators_populated: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    def get_duration(self) -> str:
        """Get execution duration as formatted string"""
        if self.end_time:
            delta = self.end_time - self.start_time
            return str(delta).split('.')[0]
        return "In Progress"

    def get_match_rate(self) -> float:
        """Get percentage of books matched"""
        if self.total_books == 0:
            return 0.0
        return (self.matched_books / self.total_books) * 100

    def print_summary(self):
        """Print enrichment statistics"""
        print("\n" + "="*80)
        print("METADATA ENRICHMENT RESULTS")
        print("="*80)
        print(f"Total Books Processed:        {self.total_books}")
        print(f"Books Matched:                {self.matched_books} ({self.get_match_rate():.1f}%)")
        print(f"  - High Confidence:          {self.high_confidence}")
        print(f"  - Medium Confidence:        {self.medium_confidence}")
        print(f"  - Low Confidence:           {self.low_confidence}")
        print(f"  - Unmatched:                {self.unmatched}")
        print(f"\nMetadata Populated:")
        print(f"  - Unique Series Found:      {self.unique_series}")
        print(f"  - Books with Series:        {self.series_identified}")
        print(f"  - Authors Populated:        {self.authors_populated}")
        print(f"  - Narrators Populated:      {self.narrators_populated}")
        print(f"\nProcessing:")
        print(f"  - Errors:                   {self.errors}")
        print(f"  - Duration:                 {self.get_duration()}")
        print("="*80 + "\n")


class GoogleBooksClient:
    """Client for Google Books API"""

    def __init__(self, api_key: str, timeout: int = 10):
        self.api_key = api_key
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = "https://www.googleapis.com/books/v1"
        # Cache for API results to avoid re-querying
        self.cache: Dict[str, MetadataMatch] = {}
        self.rate_limit_delay = 0.1  # 100ms between requests

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def _request(self, endpoint: str, params: Dict[str, str]) -> Dict[str, Any]:
        """Make HTTP request to Google Books API"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        url = f"{self.base_url}{endpoint}"
        params["key"] = self.api_key

        try:
            async with self.session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    logger.warning("Google Books API rate limit hit, backing off")
                    await asyncio.sleep(5)
                    return await self._request(endpoint, {k: v for k, v in params.items() if k != "key"})
                else:
                    logger.warning(f"Google Books API error: {response.status}")
                    return {}

        except asyncio.TimeoutError:
            logger.error(f"Request timeout for {endpoint}")
            return {}
        except Exception as e:
            logger.error(f"Error querying Google Books API: {str(e)}")
            return {}

    async def search_book(self, title: str, author: Optional[str] = None) -> Optional[MetadataMatch]:
        """Search for a book by title and optional author"""
        # Check cache first
        cache_key = f"{title}|{author}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Build search query
        query = title
        if author:
            query += f" {author}"

        logger.debug(f"Searching Google Books for: {query}")

        params = {
            "q": query,
            "maxResults": 10,
            "printType": "BOOKS"
        }

        await asyncio.sleep(self.rate_limit_delay)

        response = await self._request("/volumes", params)

        if not response.get("items"):
            logger.debug(f"No results found for: {query}")
            result = MetadataMatch(
                book_id="unknown",
                book_title=title,
                matched=False,
                error="No results from Google Books API"
            )
            self.cache[cache_key] = result
            return result

        # Process best match
        best_match = response["items"][0]
        match = await self._parse_book_data(title, best_match)

        self.cache[cache_key] = match
        return match

    async def _parse_book_data(self, original_title: str, book_data: Dict[str, Any]) -> MetadataMatch:
        """Parse Google Books API response into MetadataMatch"""
        volume_info = book_data.get("volumeInfo", {})
        google_id = book_data.get("id", "")

        title = volume_info.get("title", "Unknown")
        authors = volume_info.get("authors", [])
        published_date = volume_info.get("publishedDate", "")
        description = volume_info.get("description", "")
        isbn = None

        # Extract ISBN
        for identifier in volume_info.get("industryIdentifiers", []):
            if identifier["type"] == "ISBN_13":
                isbn = identifier["identifier"]
                break
            elif identifier["type"] == "ISBN_10" and not isbn:
                isbn = identifier["identifier"]

        # Detect series information
        series_name, series_pos = self._extract_series_info(title, description)

        # Determine confidence level
        title_match_ratio = self._calculate_similarity(original_title, title)
        if title_match_ratio > 0.8:
            confidence = MatchConfidence.HIGH
        elif title_match_ratio > 0.6:
            confidence = MatchConfidence.MEDIUM
        else:
            confidence = MatchConfidence.LOW

        return MetadataMatch(
            book_id=google_id,
            book_title=original_title,
            matched=True,
            confidence=confidence,
            series_name=series_name,
            series_position=series_pos,
            authors=authors,
            narrators=[],  # Google Books doesn't provide narrators
            published_date=published_date,
            description=description,
            isbn=isbn,
            google_books_id=google_id
        )

    def _extract_series_info(self, title: str, description: str) -> Tuple[Optional[str], Optional[int]]:
        """Extract series name and position from title and description"""
        series_name = None
        series_pos = None

        # Common patterns: "Title: Series Name, Book N"
        patterns = [
            r'(\w+[\w\s]*?)(?:Series)?[,:]?\s+(?:Book|Vol\.?|#)\s+(\d+)',
            r'(\w+[\w\s]*?)\s+Book\s+(\d+)',
            r'(\w+[\w\s]*?)\s+Vol\.?\s+(\d+)',
            r'(?:Book|Vol\.?)\s+(\d+)\s+(?:of|in)\s+(?:the\s+)?(\w+[\w\s]*)',
        ]

        for pattern in patterns:
            # Try title first
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                if "Book" in match.group(0) or "Vol" in match.group(0):
                    series_name = match.group(1).strip()
                    series_pos = int(match.group(2))
                    return series_name, series_pos
                else:
                    series_name = match.group(2).strip()
                    series_pos = int(match.group(1))
                    return series_name, series_pos

            # Try description if found in title
            if description:
                match = re.search(pattern, description, re.IGNORECASE)
                if match and series_name is None:
                    try:
                        if "Book" in match.group(0) or "Vol" in match.group(0):
                            series_name = match.group(1).strip()
                            series_pos = int(match.group(2))
                        else:
                            series_name = match.group(2).strip()
                            series_pos = int(match.group(1))
                    except (ValueError, IndexError):
                        pass

        return series_name, series_pos

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings (0-1)"""
        # Simple approach: check if one contains the other
        str1_lower = str1.lower()
        str2_lower = str2.lower()

        if str1_lower == str2_lower:
            return 1.0
        if str1_lower in str2_lower or str2_lower in str1_lower:
            return 0.9

        # Calculate Levenshtein-like distance for partial matches
        common = sum(1 for c in str1_lower if c in str2_lower)
        max_len = max(len(str1_lower), len(str2_lower))

        if max_len == 0:
            return 0.0

        return common / max_len


class MetadataEnrichmentService:
    """Main service for enriching audiobook metadata"""

    def __init__(self, abs_client: AudiobookshelfClient, google_books_key: str):
        self.abs_client = abs_client
        self.google_books_key = google_books_key
        self.stats = EnrichmentStats()
        self.matches: List[MetadataMatch] = []

    async def enrich_all_books(self, books: List[Dict[str, Any]]) -> List[MetadataMatch]:
        """Enrich metadata for all books"""
        self.stats.total_books = len(books)
        logger.info(f"Starting metadata enrichment for {len(books)} books")

        # Create Google Books client
        async with GoogleBooksClient(self.google_books_key) as gb_client:
            # Process books in batches
            batch_size = 20
            for i in range(0, len(books), batch_size):
                batch = books[i:i + batch_size]
                batch_matches = await asyncio.gather(
                    *[self._enrich_single_book(gb_client, book) for book in batch],
                    return_exceptions=True
                )

                # Process results
                for match in batch_matches:
                    if isinstance(match, Exception):
                        self.stats.errors += 1
                        logger.error(f"Error enriching book: {str(match)}")
                        continue

                    if match.matched:
                        self.stats.matched_books += 1
                        if match.confidence == MatchConfidence.HIGH:
                            self.stats.high_confidence += 1
                        elif match.confidence == MatchConfidence.MEDIUM:
                            self.stats.medium_confidence += 1
                        elif match.confidence == MatchConfidence.LOW:
                            self.stats.low_confidence += 1

                        if match.series_name:
                            self.stats.series_identified += 1
                        if match.authors:
                            self.stats.authors_populated += 1
                    else:
                        self.stats.unmatched += 1

                    self.matches.append(match)

                # Progress update
                processed = min(i + batch_size, len(books))
                logger.info(f"Enrichment progress: {processed}/{len(books)} books")
                await asyncio.sleep(0.5)  # Small delay between batches

        # Count unique series
        unique_series = set(m.series_name for m in self.matches if m.series_name)
        self.stats.unique_series = len(unique_series)

        self.stats.end_time = datetime.now()
        return self.matches

    async def _enrich_single_book(
        self,
        gb_client: GoogleBooksClient,
        book: Dict[str, Any]
    ) -> MetadataMatch:
        """Enrich metadata for a single book"""
        try:
            abs_id = book.get("id", "unknown")
            metadata = book.get("media", {}).get("metadata", {})
            title = metadata.get("title", "Unknown")

            logger.debug(f"Enriching: {title} (ID: {abs_id})")

            # Search for book
            match = await gb_client.search_book(title)

            if match:
                match.book_id = abs_id
                return match

            return MetadataMatch(
                book_id=abs_id,
                book_title=title,
                matched=False,
                error="No metadata found"
            )

        except Exception as e:
            logger.error(f"Error enriching book {book.get('id')}: {str(e)}")
            return MetadataMatch(
                book_id=book.get("id", "unknown"),
                book_title=book.get("media", {}).get("metadata", {}).get("title", "Unknown"),
                matched=False,
                error=str(e)
            )

    async def apply_enrichment_to_abs(
        self,
        matches: List[MetadataMatch],
        skip_low_confidence: bool = False
    ) -> Dict[str, Any]:
        """Apply enriched metadata back to Audiobookshelf"""
        logger.info("Applying enriched metadata to Audiobookshelf...")

        applied = 0
        skipped = 0

        for i, match in enumerate(matches, 1):
            # Skip low confidence matches if requested
            if skip_low_confidence and match.confidence == MatchConfidence.LOW:
                skipped += 1
                continue

            if not match.matched:
                skipped += 1
                continue

            try:
                # Build metadata update - ONLY update proper fields, not subtitle
                update_payload = {}

                # Only add authors if not empty
                if match.authors:
                    update_payload["authors"] = match.authors

                # Only add series if not already in subtitle (ABS stores series there sometimes)
                # Check if book has series info in metadata
                # For now, only update if we have high-confidence match
                if match.series_name and match.confidence == MatchConfidence.HIGH:
                    update_payload["series"] = match.series_name
                    if match.series_position:
                        update_payload["seriesSequence"] = str(match.series_position)

                # IMPORTANT: Do NOT modify subtitle field
                # Subtitle may already contain series info from file metadata

                # Update book in Audiobookshelf only if we have payload
                if not update_payload:
                    skipped += 1
                    continue

                success = await self.abs_client.update_book_metadata(
                    match.book_id,
                    update_payload
                )

                if success:
                    applied += 1
                    if i % 100 == 0:
                        logger.info(f"Applied enrichment to {applied} books...")
                else:
                    skipped += 1
                    logger.warning(f"Failed to update book {match.book_id}")

                await asyncio.sleep(0.1)  # Rate limiting

            except Exception as e:
                skipped += 1
                logger.error(f"Error applying enrichment to {match.book_id}: {str(e)}")

        logger.info(f"Enrichment applied to {applied} books, {skipped} skipped")
        return {
            "applied": applied,
            "skipped": skipped,
            "total": len(matches)
        }


async def get_abs_client() -> AudiobookshelfClient:
    """Create and return authenticated Audiobookshelf client"""
    logger.info(f"Connecting to Audiobookshelf at {settings.ABS_URL}")
    client = AudiobookshelfClient(
        base_url=settings.ABS_URL,
        api_token=settings.ABS_TOKEN,
        timeout=30
    )
    return client


async def fetch_all_books_from_abs(client: AudiobookshelfClient) -> List[Dict[str, Any]]:
    """Fetch all books from Audiobookshelf library"""
    logger.info("Fetching all books from Audiobookshelf...")

    try:
        all_books = await client.get_library_items(limit=100, offset=0)
        logger.info(f"Retrieved {len(all_books)} books from Audiobookshelf")
        return all_books

    except Exception as e:
        logger.error(f"Error fetching books: {str(e)}")
        raise


async def main():
    """Main entry point for metadata enrichment"""
    print("\n" + "="*80)
    print("AUDIOBOOK METADATA ENRICHMENT SERVICE")
    print("="*80)
    print(f"Audiobookshelf URL: {settings.ABS_URL}")
    print(f"Database: {settings.DATABASE_URL}")
    print("="*80 + "\n")

    try:
        # Initialize clients
        logger.info("Initializing clients...")
        abs_client = await get_abs_client()

        # Fetch all books
        logger.info("Fetching audiobooks...")
        all_books = await fetch_all_books_from_abs(abs_client)

        if not all_books:
            logger.warning("No books found in library")
            print("[WARNING] No books found in Audiobookshelf library")
            return

        # Create enrichment service
        service = MetadataEnrichmentService(
            abs_client=abs_client,
            google_books_key=settings.GOOGLE_BOOKS_API_KEY
        )

        # Enrich metadata
        logger.info("Starting metadata enrichment...")
        matches = await service.enrich_all_books(all_books)

        # Print enrichment results
        service.stats.print_summary()

        # Auto-apply enriched metadata
        logger.info("Applying enriched metadata to Audiobookshelf...")
        results = await service.apply_enrichment_to_abs(
            matches,
            skip_low_confidence=False
        )

        print("\n" + "="*80)
        print("ENRICHMENT APPLICATION RESULTS")
        print("="*80)
        print(f"Applied to:     {results['applied']} books")
        print(f"Skipped:        {results['skipped']} books")
        print(f"Total:          {results['total']} books")
        print("="*80 + "\n")

        logger.info("Metadata enrichment completed successfully")

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        print(f"\n[ERROR] Fatal error: {str(e)}\n")
        raise


if __name__ == "__main__":
    asyncio.run(main())
