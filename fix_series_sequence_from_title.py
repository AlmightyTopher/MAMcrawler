#!/usr/bin/env python3
"""
Fix Series Sequence from Book Title

For books where the title contains a number (e.g., "Master Class 4")
but the series sequence doesn't match, extract the correct number from the title.
"""

import asyncio
import aiohttp
import logging
import os
import re
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('fix_series_sequence_from_title.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

ABS_URL = os.getenv('ABS_URL', 'http://localhost:13378').rstrip('/')
ABS_TOKEN = os.getenv('ABS_TOKEN')
ABS_API_URL = f"{ABS_URL}/api"


class SeriesSequenceFixer:
    """Fix series sequence numbers from book titles"""

    def __init__(self, api_url: str = ABS_API_URL, api_key: Optional[str] = None):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.session = None
        self.stats = {
            'books_scanned': 0,
            'books_fixed': 0,
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

    def extract_number_from_title(self, title: str) -> Optional[str]:
        """Extract the last number from the title"""
        # Look for patterns like "Master Class 4" or "Book 12"
        match = re.search(r'\b(\d+)\s*$', title)
        if match:
            return match.group(1)

        # Also check for patterns in the middle
        match = re.search(r'\s(\d+)\s*[-:]', title)
        if match:
            return match.group(1)

        return None

    async def fix_book_series(
        self,
        book_id: str,
        series_name: str,
        new_sequence: str,
        title: str
    ) -> bool:
        """Update book's series sequence"""
        try:
            # Get current book to preserve other data
            async with self.session.get(f"{self.api_url}/items/{book_id}") as resp:
                if resp.status != 200:
                    logger.warning(f"Could not fetch book {book_id}")
                    return False

                book_data = await resp.json()
                media = book_data.get('media', {})
                metadata = media.get('metadata', {})

                # Update series array with new sequence
                series_id = series_name.lower().replace(' ', '-')[:16]

                new_series = {
                    "id": series_id,
                    "name": series_name,
                    "sequence": new_sequence
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
                        logger.info(f"Fixed: {title}")
                        logger.info(f"  Changed to: {series_name} #{new_sequence}")
                        self.stats['books_fixed'] += 1
                        return True
                    else:
                        logger.warning(f"Failed to update {book_id}: {update_resp.status}")
                        return False

        except Exception as e:
            logger.warning(f"Error updating book {book_id}: {e}")
            return False

    async def process_books(self, items: List[Dict]) -> None:
        """Process books and fix sequence numbers"""
        logger.info(f"Scanning {len(items)} books for sequence mismatches...")

        for idx, item in enumerate(items, 1):
            if idx % 500 == 0:
                logger.info(f"  Progress: {idx}/{len(items)}")

            try:
                book_id = item.get('id')
                media = item.get('media', {})
                metadata = media.get('metadata', {})
                title = metadata.get('title', 'Unknown')
                series = metadata.get('series', [])

                self.stats['books_scanned'] += 1

                # Skip if no series
                if not series:
                    continue

                series_info = series[0]
                series_name = series_info.get('name')
                current_sequence = series_info.get('sequence')

                # Extract number from title
                title_number = self.extract_number_from_title(title)

                # Check if mismatch
                if title_number and current_sequence != title_number:
                    logger.info(f"Found mismatch: {title}")
                    logger.info(f"  Current sequence: {current_sequence}")
                    logger.info(f"  Title suggests: {title_number}")

                    # Fix it
                    await self.fix_book_series(book_id, series_name, title_number, title)

            except Exception as e:
                logger.warning(f"Error processing book: {e}")
                self.stats['errors'].append(str(e))

    async def run(self):
        """Main workflow"""
        logger.info("=" * 80)
        logger.info("FIX SERIES SEQUENCE FROM BOOK TITLE")
        logger.info("=" * 80)
        logger.info("")

        logger.info("Step 1: Testing API connection...")
        if not await self.test_connection():
            logger.error("Cannot connect to Audiobookshelf API")
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
        logger.info("SEQUENCE FIX COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Books scanned:     {self.stats['books_scanned']}")
        logger.info(f"Books fixed:       {self.stats['books_fixed']}")

        if self.stats['errors']:
            logger.info(f"Errors:            {len(self.stats['errors'])}")

        logger.info("")
        logger.info("Done!")
        logger.info("")

        return True


async def main():
    if not ABS_TOKEN:
        logger.error("ERROR: ABS_TOKEN not found in environment!")
        return 1

    try:
        async with SeriesSequenceFixer(ABS_API_URL, ABS_TOKEN) as fixer:
            success = await fixer.run()
            return 0 if success else 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
