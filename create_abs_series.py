"""
Create Audiobookshelf Series Objects

This script creates actual series objects in Audiobookshelf and links books to them.
Unlike just setting seriesName metadata, this creates proper series relationships
that appear in the UI.

Audiobookshelf API:
- POST /api/series - Create a new series
- PATCH /api/series/:id - Update series
- POST /api/series/:id/addBook - Add book to series
"""

import asyncio
import logging
import re
from typing import Dict, List, Any, Optional
from collections import defaultdict
from datetime import datetime

from backend.config import get_settings
from backend.integrations.abs_client import AudiobookshelfClient
from backend.utils.log_config import setup_logging

logger = logging.getLogger(__name__)

# Initialize logging
setup_logging()

# Get settings
settings = get_settings()


class SeriesCreator:
    """Creates Audiobookshelf series and links books"""

    def __init__(self, abs_client: AudiobookshelfClient):
        self.abs_client = abs_client
        self.session = abs_client.session
        self.base_url = abs_client.base_url
        self.auth_headers = {
            "Authorization": f"Bearer {abs_client.api_token}",
            "Content-Type": "application/json"
        }
        self.series_created = 0
        self.books_linked = 0
        self.errors = []

    async def extract_series_from_books(self, books: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Extract series and their books from metadata"""
        series_map = defaultdict(list)

        for book in books:
            metadata = book.get("media", {}).get("metadata", {})
            series_name = metadata.get("seriesName", "")

            if series_name and "#" in series_name:
                # Extract series name (remove the #N part)
                base_series = re.sub(r"\s*#\d+.*$", "", series_name).strip()
                if base_series:
                    series_map[base_series].append(book["id"])

        return dict(series_map)

    async def create_series(self, series_name: str, book_ids: List[str]) -> Optional[str]:
        """Create a series and add books to it"""
        try:
            # Create series
            series_data = {
                "name": series_name,
                "description": f"Auto-created series from metadata enrichment"
            }

            logger.debug(f"Creating series: {series_name}")

            # POST to create series
            endpoint = f"{self.base_url}/api/series"
            async with self.session.post(
                endpoint,
                json=series_data,
                headers=self.auth_headers,
                timeout=30
            ) as response:
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    logger.error(f"Failed to create series '{series_name}': {error_text}")
                    return None

                result = await response.json()
                series_id = result.get("id")

                if not series_id:
                    logger.error(f"No series ID returned for '{series_name}'")
                    return None

                logger.info(f"Created series '{series_name}' (ID: {series_id})")
                self.series_created += 1

                # Add books to series
                for i, book_id in enumerate(book_ids, 1):
                    await self.add_book_to_series(series_id, book_id, i)

                return series_id

        except Exception as e:
            error_msg = f"Error creating series '{series_name}': {str(e)}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return None

    async def add_book_to_series(self, series_id: str, book_id: str, sequence: int) -> bool:
        """Add a book to a series with sequence number"""
        try:
            endpoint = f"{self.base_url}/api/series/{series_id}/addBook"
            payload = {
                "bookId": book_id,
                "sequence": str(sequence)
            }

            logger.debug(f"Adding book {book_id} to series {series_id} as #{ sequence}")

            async with self.session.post(
                endpoint,
                json=payload,
                headers=self.auth_headers,
                timeout=30
            ) as response:
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    logger.warning(f"Failed to add book to series: {error_text}")
                    return False

                self.books_linked += 1
                return True

        except Exception as e:
            logger.error(f"Error adding book to series: {str(e)}")
            return False

    async def create_all_series(self, books: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create all series from books"""
        logger.info("Extracting series from book metadata...")
        series_map = await self.extract_series_from_books(books)

        if not series_map:
            logger.info("No series found in metadata")
            return {"created": 0, "linked": 0, "errors": 0}

        logger.info(f"Found {len(series_map)} series to create")

        for i, (series_name, book_ids) in enumerate(sorted(series_map.items()), 1):
            logger.info(f"[{i}/{len(series_map)}] Processing series: {series_name} ({len(book_ids)} books)")
            await self.create_series(series_name, book_ids)
            await asyncio.sleep(0.2)  # Rate limiting

        return {
            "created": self.series_created,
            "linked": self.books_linked,
            "errors": len(self.errors)
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


async def fetch_all_books(client: AudiobookshelfClient) -> List[Dict[str, Any]]:
    """Fetch all books from Audiobookshelf"""
    logger.info("Fetching all books...")
    all_books = await client.get_library_items(limit=100, offset=0)
    logger.info(f"Retrieved {len(all_books)} books")
    return all_books


async def main():
    """Main entry point"""
    print("\n" + "="*80)
    print("AUDIOBOOKSHELF SERIES CREATION")
    print("="*80)
    print("This script creates actual series objects in Audiobookshelf")
    print("and links books to them based on seriesName metadata")
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

        # Create series
        creator = SeriesCreator(abs_client=abs_client)
        logger.info("Creating series...")
        results = await creator.create_all_series(all_books)

        # Results
        print("\n" + "="*80)
        print("SERIES CREATION RESULTS")
        print("="*80)
        print(f"Series Created:           {results['created']}")
        print(f"Books Linked:             {results['linked']}")
        print(f"Errors:                   {results['errors']}")
        if creator.errors:
            print("\nErrors Encountered:")
            for error in creator.errors[:10]:  # Show first 10 errors
                print(f"  - {error}")
        print("="*80 + "\n")

        logger.info("Series creation completed successfully")

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        print(f"\n[ERROR] Fatal error: {str(e)}\n")
        raise


if __name__ == "__main__":
    asyncio.run(main())
