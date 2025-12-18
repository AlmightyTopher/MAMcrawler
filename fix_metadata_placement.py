"""
Fix Metadata Placement Script

This script corrects metadata that was incorrectly placed in the subtitle field
and moves it to the proper fields in Audiobookshelf (series, seriesSequence, authors).

The issue was that the metadata was being written to the subtitle field instead of
the proper metadata fields. This script:

1. Fetches all books from Audiobookshelf
2. Identifies books where series/author info is in the subtitle
3. Extracts and moves that data to proper fields
4. Cleans up subtitle field
5. Prevents future issues by using correct API structure
"""

import asyncio
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from backend.config import get_settings
from backend.integrations.abs_client import AudiobookshelfClient
from backend.utils.log_config import setup_logging

logger = logging.getLogger(__name__)

# Initialize logging
setup_logging()

# Get settings
settings = get_settings()


class MetadataFixer:
    """Fixes incorrectly placed metadata in Audiobookshelf"""

    def __init__(self, abs_client: AudiobookshelfClient):
        self.abs_client = abs_client
        self.books_fixed = 0
        self.books_skipped = 0
        self.errors = []

    async def fix_all_metadata(self, books: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fix metadata placement for all books"""
        logger.info(f"Starting metadata cleanup for {len(books)} books...")

        for i, book in enumerate(books, 1):
            try:
                metadata = book.get("media", {}).get("metadata", {})
                subtitle = metadata.get("subtitle", "")

                # Check if subtitle contains series or author info
                if self._is_misplaced_metadata(subtitle):
                    logger.info(f"[{i}/{len(books)}] Fixing: {metadata.get('title')}")

                    # Extract metadata from subtitle
                    extracted = self._extract_metadata_from_subtitle(subtitle)

                    if extracted:
                        # Build corrected metadata
                        update_payload = {
                            "subtitle": extracted.get("cleaned_subtitle", "")
                        }

                        if extracted.get("series"):
                            update_payload["series"] = extracted["series"]

                        if extracted.get("series_sequence"):
                            update_payload["seriesSequence"] = str(extracted["series_sequence"])

                        if extracted.get("authors"):
                            update_payload["authors"] = extracted["authors"]

                        # Apply fix
                        success = await self.abs_client.update_book_metadata(
                            book.get("id"),
                            update_payload
                        )

                        if success:
                            self.books_fixed += 1
                            logger.info(f"✓ Fixed: {metadata.get('title')}")
                            logger.debug(f"  Extracted: {extracted}")
                        else:
                            self.books_skipped += 1
                            logger.warning(f"✗ Failed to fix: {metadata.get('title')}")

                        await asyncio.sleep(0.1)  # Rate limiting
                    else:
                        self.books_skipped += 1
                else:
                    self.books_skipped += 1

            except Exception as e:
                self.books_skipped += 1
                error_msg = f"Error fixing {book.get('id')}: {str(e)}"
                logger.error(error_msg)
                self.errors.append(error_msg)

        return {
            "fixed": self.books_fixed,
            "skipped": self.books_skipped,
            "errors": len(self.errors)
        }

    def _is_misplaced_metadata(self, subtitle: str) -> bool:
        """Check if subtitle contains misplaced metadata patterns"""
        if not subtitle:
            return False

        # Patterns that indicate misplaced metadata
        patterns = [
            r"Series\s*[:=]",  # "Series: Name"
            r"seriesSequence\s*[:=]",  # "seriesSequence: 1"
            r"authors\s*[:=]",  # "authors: ["
            r"\[.*@.*\]",  # JSON array format ["Author"]
            r"Book\s+\d+\s+(?:of|in)",  # "Book 1 of Series"
        ]

        for pattern in patterns:
            if re.search(pattern, subtitle, re.IGNORECASE):
                return True

        return False

    def _extract_metadata_from_subtitle(self, subtitle: str) -> Optional[Dict[str, Any]]:
        """Extract metadata from subtitle field"""
        extracted = {
            "series": None,
            "series_sequence": None,
            "authors": None,
            "cleaned_subtitle": subtitle
        }

        # Try to extract series and sequence
        series_match = re.search(
            r"Series\s*[:=]\s*([^,;\n]+?)(?:\s*,|\s*seriesSequence|$)",
            subtitle,
            re.IGNORECASE
        )
        if series_match:
            extracted["series"] = series_match.group(1).strip().strip('"\'')
            extracted["cleaned_subtitle"] = re.sub(
                r"Series\s*[:=][^,;]*", "", subtitle, flags=re.IGNORECASE
            ).strip()

        # Try to extract series sequence
        seq_match = re.search(r"seriesSequence\s*[:=]\s*(\d+)", subtitle, re.IGNORECASE)
        if seq_match:
            extracted["series_sequence"] = int(seq_match.group(1))
            extracted["cleaned_subtitle"] = re.sub(
                r"seriesSequence\s*[:=]\s*\d+", "", extracted["cleaned_subtitle"], flags=re.IGNORECASE
            ).strip()

        # Try to extract authors from JSON-like format
        authors_match = re.search(r"authors\s*[:=]\s*(\[.*?\])", subtitle, re.IGNORECASE)
        if authors_match:
            try:
                import json
                authors_str = authors_match.group(1)
                extracted["authors"] = json.loads(authors_str)
                extracted["cleaned_subtitle"] = re.sub(
                    r"authors\s*[:=]\s*\[.*?\]", "", extracted["cleaned_subtitle"], flags=re.IGNORECASE
                ).strip()
            except (json.JSONDecodeError, ValueError):
                # If JSON parsing fails, try manual extraction
                author_list = re.findall(r'"([^"]+)"', authors_match.group(1))
                if author_list:
                    extracted["authors"] = author_list
                    extracted["cleaned_subtitle"] = re.sub(
                        r"authors\s*[:=]\s*\[.*?\]", "", extracted["cleaned_subtitle"], flags=re.IGNORECASE
                    ).strip()

        # Clean up any remaining metadata syntax
        extracted["cleaned_subtitle"] = re.sub(r",\s*$", "", extracted["cleaned_subtitle"]).strip()

        # Return None if nothing was extracted
        if not any([extracted["series"], extracted["series_sequence"], extracted["authors"]]):
            return None

        return extracted


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
    all_books = await client.get_library_items(limit=100, offset=0)
    logger.info(f"Retrieved {len(all_books)} books from Audiobookshelf")
    return all_books


async def main():
    """Main entry point"""
    print("\n" + "="*80)
    print("AUDIOBOOKSHELF METADATA PLACEMENT FIX")
    print("="*80)
    print("This script corrects metadata that was placed in the subtitle field")
    print("and moves it to the proper fields (series, seriesSequence, authors)")
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

        # Create fixer
        fixer = MetadataFixer(abs_client=abs_client)

        # Fix metadata
        logger.info("Starting metadata fixes...")
        results = await fixer.fix_all_metadata(all_books)

        # Print results
        print("\n" + "="*80)
        print("METADATA FIX RESULTS")
        print("="*80)
        print(f"Books Fixed:              {results['fixed']}")
        print(f"Books Skipped:            {results['skipped']}")
        print(f"Errors:                   {results['errors']}")
        if fixer.errors:
            print("\nErrors Encountered:")
            for error in fixer.errors:
                print(f"  - {error}")
        print("="*80 + "\n")

        logger.info("Metadata placement fix completed successfully")

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        print(f"\n[ERROR] Fatal error: {str(e)}\n")
        raise


if __name__ == "__main__":
    asyncio.run(main())
