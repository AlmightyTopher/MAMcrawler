"""
Cleanup Subtitle Fields Script

This script fixes books where series information leaked into the subtitle field
during enrichment. It extracts series data from subtitles and places them in the
proper metadata fields.
"""

import asyncio
import logging
import re
from typing import Dict, List, Any, Optional

from backend.config import get_settings
from backend.integrations.abs_client import AudiobookshelfClient
from backend.utils.log_config import setup_logging

logger = logging.getLogger(__name__)

# Initialize logging
setup_logging()

# Get settings
settings = get_settings()


class SubtitleCleaner:
    """Cleans subtitle fields and extracts metadata"""

    def __init__(self, abs_client: AudiobookshelfClient):
        self.abs_client = abs_client
        self.books_fixed = 0
        self.books_skipped = 0

    async def clean_all_subtitles(self, books: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Clean subtitle fields for all books"""
        logger.info(f"Starting subtitle cleanup for {len(books)} books...")

        for i, book in enumerate(books, 1):
            try:
                metadata = book.get("media", {}).get("metadata", {})
                subtitle = metadata.get("subtitle", "")
                title = metadata.get("title", "Unknown")

                # Check if subtitle contains series information
                if self._has_series_in_subtitle(subtitle):
                    logger.info(f"[{i}/{len(books)}] Cleaning: {title}")

                    # Extract series from subtitle
                    series_name, series_pos = self._extract_series_from_subtitle(subtitle)
                    cleaned_subtitle = self._remove_series_from_subtitle(subtitle)

                    if series_name:
                        # Build update payload
                        update_payload = {}

                        if cleaned_subtitle and cleaned_subtitle != subtitle:
                            update_payload["subtitle"] = cleaned_subtitle

                        update_payload["series"] = series_name
                        if series_pos:
                            update_payload["seriesSequence"] = str(series_pos)

                        # Apply fix
                        success = await self.abs_client.update_book_metadata(
                            book.get("id"),
                            update_payload
                        )

                        if success:
                            self.books_fixed += 1
                            logger.info(f"✓ Fixed: {title}")
                            logger.debug(f"  Series: {series_name}, Position: {series_pos}")
                        else:
                            self.books_skipped += 1
                            logger.warning(f"✗ Failed to fix: {title}")

                        await asyncio.sleep(0.1)
                    else:
                        self.books_skipped += 1
                else:
                    self.books_skipped += 1

            except Exception as e:
                self.books_skipped += 1
                logger.error(f"Error cleaning subtitle for {book.get('id')}: {str(e)}")

        return {
            "fixed": self.books_fixed,
            "skipped": self.books_skipped
        }

    def _has_series_in_subtitle(self, subtitle: str) -> bool:
        """Check if subtitle contains series information"""
        if not subtitle:
            return False

        # Patterns for series in subtitle
        patterns = [
            r"Book\s+\d+\s+(?:of|in)",  # "Book 1 of Series Name"
            r",\s*Book\s+\d+",  # ", Book 1"
            r":\s*Book\s+\d+",  # ": Book 1"
            r"Vol\.?\s+\d+",  # "Vol 1"
            r"#\s*\d+\s*(?:of|in)",  # "#1 of Series"
        ]

        for pattern in patterns:
            if re.search(pattern, subtitle, re.IGNORECASE):
                return True

        return False

    def _extract_series_from_subtitle(self, subtitle: str) -> tuple:
        """Extract series name and position from subtitle"""
        series_name = None
        series_pos = None

        # Pattern: "Series Name, Book 1" or "Series Name: Book 1"
        match = re.search(
            r"^([^:,]+?)(?:\s*[:,]\s*Book\s+(\d+))?$",
            subtitle,
            re.IGNORECASE
        )
        if match:
            series_name = match.group(1).strip()
            if match.group(2):
                series_pos = int(match.group(2))
            return series_name, series_pos

        # Pattern: "Book 1 of Series Name" or "Book 1 in Series Name"
        match = re.search(
            r"Book\s+(\d+)\s+(?:of|in)\s+(.+)",
            subtitle,
            re.IGNORECASE
        )
        if match:
            series_pos = int(match.group(1))
            series_name = match.group(2).strip()
            return series_name, series_pos

        # Pattern: "Title, Book N"
        match = re.search(
            r"^(.+?),\s*Book\s+(\d+)$",
            subtitle,
            re.IGNORECASE
        )
        if match:
            series_name = match.group(1).strip()
            series_pos = int(match.group(2))
            return series_name, series_pos

        return None, None

    def _remove_series_from_subtitle(self, subtitle: str) -> str:
        """Remove series information from subtitle"""
        # Remove "Book N" patterns
        cleaned = re.sub(r",\s*Book\s+\d+.*$", "", subtitle, flags=re.IGNORECASE)
        cleaned = re.sub(r":\s*Book\s+\d+.*$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"Book\s+\d+\s+(?:of|in)\s+.+", "", cleaned, flags=re.IGNORECASE)

        # Remove trailing punctuation
        cleaned = re.sub(r"\s*[,:;]\s*$", "", cleaned).strip()

        return cleaned if cleaned else subtitle


async def get_abs_client() -> AudiobookshelfClient:
    """Create and return authenticated Audiobookshelf client"""
    logger.info(f"Connecting to Audiobookshelf at {settings.ABS_URL}")
    client = AudiobookshelfClient(
        base_url=settings.ABS_URL,
        api_token=settings.ABS_TOKEN,
        timeout=30
    )
    return client


async def fetch_all_books(client: AudiobookshelfClient) -> List[Dict[str, Any]]:
    """Fetch all books from Audiobookshelf"""
    logger.info("Fetching all books...")
    all_books = await client.get_library_items(limit=100, offset=0)
    logger.info(f"Retrieved {len(all_books)} books")
    return all_books


async def main():
    """Main entry point"""
    print("\n" + "="*80)
    print("SUBTITLE FIELD CLEANUP")
    print("="*80)
    print("This script extracts series information from subtitle fields")
    print("and places it in the proper metadata fields")
    print("="*80 + "\n")

    try:
        # Initialize
        logger.info("Initializing...")
        abs_client = await get_abs_client()

        # Fetch books
        all_books = await fetch_all_books(abs_client)

        if not all_books:
            logger.warning("No books found")
            print("[WARNING] No books found")
            return

        # Clean subtitles
        cleaner = SubtitleCleaner(abs_client=abs_client)
        results = await cleaner.clean_all_subtitles(all_books)

        # Results
        print("\n" + "="*80)
        print("CLEANUP RESULTS")
        print("="*80)
        print(f"Books Fixed:              {results['fixed']}")
        print(f"Books Skipped:            {results['skipped']}")
        print("="*80 + "\n")

        logger.info("Subtitle cleanup completed successfully")

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        print(f"\n[ERROR] Fatal error: {str(e)}\n")
        raise


if __name__ == "__main__":
    asyncio.run(main())
