#!/usr/bin/env python3
"""
Audiobookshelf Series Array Populator

Updates books by modifying the series array directly (not seriesName field).
The series array is the proper way to store series relationships in Audiobookshelf.
"""

import asyncio
import aiohttp
import logging
import os
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import sys
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('populate_series_array.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

ABS_URL = os.getenv('ABS_URL', 'http://localhost:13378').rstrip('/')
ABS_TOKEN = os.getenv('ABS_TOKEN')
ABS_API_URL = f"{ABS_URL}/api"


class SeriesArrayPopulator:
    """Populates series array in book metadata"""

    def __init__(self, api_url: str = ABS_API_URL, api_key: Optional[str] = None):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.session = None
        self.stats = {
            'libraries_found': 0,
            'books_scanned': 0,
            'books_with_series': 0,
            'books_updated': 0,
            'errors': []
        }

    async def __aenter__(self):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        self.session = aiohttp.ClientSession(headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_connection(self) -> bool:
        try:
            async with self.session.get(
                f"{self.api_url}/libraries",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    async def get_libraries(self) -> List[Dict]:
        try:
            async with self.session.get(f"{self.api_url}/libraries") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('libraries', [])
        except Exception as e:
            logger.error(f"Error fetching libraries: {e}")
        return []

    async def get_library_items(self, library_id: str, limit: int = 100) -> List[Dict]:
        all_items = []
        offset = 0

        try:
            while True:
                async with self.session.get(
                    f"{self.api_url}/libraries/{library_id}/items",
                    params={"limit": limit, "offset": offset}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        items = data.get('results', [])
                        if not items:
                            break
                        all_items.extend(items)
                        if offset + len(items) >= data.get('total', 0):
                            break
                        offset += len(items)
                    else:
                        break
            return all_items
        except Exception as e:
            logger.error(f"Error fetching items: {e}")
            return all_items

    def extract_series_from_metadata(self, metadata: Dict) -> Tuple[Optional[str], Optional[str]]:
        """Extract series name and sequence from seriesName field"""
        series_name = metadata.get('seriesName')
        if not series_name:
            return None, None

        series_name = series_name.strip()

        # Format: "Series Name #12"
        match = re.search(r'^(.+?)\s*#\s*([0-9.]+)', series_name)
        if match:
            return match.group(1).strip(), match.group(2).strip()

        return series_name, None

    async def update_book_series_array(
        self,
        book_id: str,
        series_name: str,
        series_sequence: Optional[str] = None,
        title: Optional[str] = None
    ) -> bool:
        """Update book's series array"""
        try:
            # Get current book to preserve other data
            async with self.session.get(f"{self.api_url}/items/{book_id}") as resp:
                if resp.status != 200:
                    logger.warning(f"Could not fetch book {book_id}")
                    return False

                book_data = await resp.json()
                media = book_data.get('media', {})
                metadata = media.get('metadata', {})

                # Create or update series array
                # Generate a simple ID for the series (can be any unique string)
                series_id = series_name.lower().replace(' ', '-')[:16]

                new_series = {
                    "id": series_id,
                    "name": series_name,
                    "sequence": series_sequence or ""
                }

                metadata['series'] = [new_series]

                # Prepare update payload
                payload = {"metadata": metadata}

                # Update the book
                async with self.session.patch(
                    f"{self.api_url}/items/{book_id}/media",
                    json=payload
                ) as update_resp:
                    if update_resp.status in [200, 204]:
                        logger.debug(f"Updated: {title} -> {series_name} #{series_sequence}")
                        self.stats['books_updated'] += 1
                        return True
                    else:
                        logger.warning(f"Failed to update {book_id}: {update_resp.status}")
                        return False

        except Exception as e:
            logger.warning(f"Error updating book {book_id}: {e}")
            return False

    async def process_books(self, items: List[Dict]) -> None:
        """Process books and update series array"""
        logger.info(f"Processing {len(items)} books...")

        for idx, item in enumerate(items, 1):
            if idx % 200 == 0:
                logger.info(f"  Progress: {idx}/{len(items)}")

            try:
                book_id = item.get('id')
                media = item.get('media', {})
                metadata = media.get('metadata', {})
                title = metadata.get('title', 'Unknown')

                self.stats['books_scanned'] += 1

                # Extract series from seriesName field
                series_name, series_sequence = self.extract_series_from_metadata(metadata)

                if series_name:
                    self.stats['books_with_series'] += 1

                    # Check if series array already has data
                    existing_series = metadata.get('series', [])

                    # Only update if series array is empty or different
                    if not existing_series or (
                        len(existing_series) > 0 and
                        existing_series[0].get('name') != series_name
                    ):
                        await self.update_book_series_array(
                            book_id,
                            series_name,
                            series_sequence,
                            title
                        )

            except Exception as e:
                logger.warning(f"Error processing book: {e}")
                self.stats['errors'].append(str(e))

    async def run(self):
        """Main workflow"""
        logger.info("=" * 80)
        logger.info("AUDIOBOOKSHELF SERIES ARRAY POPULATOR")
        logger.info("=" * 80)
        logger.info("")

        logger.info("Step 1: Testing API connection...")
        logger.info(f"  URL: {self.api_url}")
        logger.info(f"  Token: {'*' * 20}...{self.api_key[-10:] if self.api_key else 'NONE'}")

        if not await self.test_connection():
            logger.error("Cannot connect to Audiobookshelf API")
            logger.error("Make sure:")
            logger.error(f"  1. Audiobookshelf is running on {ABS_URL}")
            logger.error("  2. ABS_TOKEN is set in .env")
            logger.error("  3. The token is valid")
            return False

        logger.info("[OK] API connection successful")
        logger.info("")

        logger.info("Step 2: Getting libraries...")
        libraries = await self.get_libraries()
        if not libraries:
            logger.error("No libraries found")
            return False

        logger.info(f"[OK] Found {len(libraries)} libraries")
        logger.info("")

        # Process each library
        for library in libraries:
            library_id = library.get('id')
            library_name = library.get('name', 'Unknown')

            logger.info(f"Processing library: {library_name}")
            logger.info("-" * 80)

            items = await self.get_library_items(library_id)
            if items:
                await self.process_books(items)

            logger.info("")

        # Summary
        logger.info("=" * 80)
        logger.info("SERIES ARRAY POPULATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Books scanned:        {self.stats['books_scanned']}")
        logger.info(f"Books with series:    {self.stats['books_with_series']}")
        logger.info(f"Books updated:        {self.stats['books_updated']}")

        if self.stats['errors']:
            logger.info(f"Errors encountered:   {len(self.stats['errors'])}")
            for error in self.stats['errors'][:10]:
                logger.info(f"  - {error}")

        logger.info("")
        logger.info("Series arrays are now updated!")
        logger.info(f"Visit {ABS_URL} to verify")
        logger.info("")

        return True


async def main():
    if not ABS_TOKEN:
        logger.error("ERROR: ABS_TOKEN not found in environment!")
        logger.error("Please add ABS_TOKEN to your .env file")
        return 1

    try:
        async with SeriesArrayPopulator(ABS_API_URL, ABS_TOKEN) as populator:
            success = await populator.run()
            return 0 if success else 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
