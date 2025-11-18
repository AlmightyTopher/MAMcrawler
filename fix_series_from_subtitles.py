#!/usr/bin/env python3
"""
Extract Series Info from Subtitles and Update Books

Some books have series info in the subtitle field (e.g., "Expeditionary Force, Book 12")
This script extracts that and properly populates seriesName and seriesSequence fields.
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
        logging.FileHandler('fix_series_from_subtitles.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

ABS_URL = os.getenv('ABS_URL', 'http://localhost:13378').rstrip('/')
ABS_TOKEN = os.getenv('ABS_TOKEN')
ABS_API_URL = f"{ABS_URL}/api"


class SubtitleSeriesExtractor:
    """Extracts series info from subtitles and updates book metadata"""

    def __init__(self, api_url: str = ABS_API_URL, api_key: Optional[str] = None):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.session = None
        self.stats = {
            'books_scanned': 0,
            'series_in_subtitle': 0,
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

    def extract_series_from_subtitle(self, subtitle: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract series info from subtitle.
        Patterns:
        - "Series Name, Book 12" -> ("Series Name", "12")
        - "Series Name Book 12" -> ("Series Name", "12")
        - "Series Name #12" -> ("Series Name", "12")
        - "Book 12 in Series Name" -> ("Series Name", "12")
        """
        if not subtitle:
            return None, None

        subtitle = subtitle.strip()

        # Pattern 1: "Series Name, Book X" (with comma)
        match = re.search(r'^(.+?),\s+[Bb]ook\s+([0-9.]+)', subtitle)
        if match:
            return match.group(1).strip(), match.group(2).strip()

        # Pattern 1b: "Series Name Book X" (without comma)
        match = re.search(r'^(.+?)\s+[Bb]ook\s+([0-9.]+)$', subtitle)
        if match:
            return match.group(1).strip(), match.group(2).strip()

        # Pattern 2: "Series Name #X"
        match = re.search(r'^(.+?)\s*#\s*([0-9.]+)', subtitle)
        if match:
            return match.group(1).strip(), match.group(2).strip()

        # Pattern 3: "Book X in Series Name" or "Book X: Series Name"
        match = re.search(r'[Bb]ook\s+([0-9.]+)\s+[in|:]+\s*(.+)', subtitle)
        if match:
            return match.group(2).strip(), match.group(1).strip()

        return None, None

    async def update_book_metadata(
        self,
        book_id: str,
        series_name: str,
        series_sequence: str,
        title: Optional[str] = None
    ) -> bool:
        """Update book with series metadata"""
        try:
            payload = {
                "metadata": {
                    "seriesName": f"{series_name} #{series_sequence}",
                    "seriesSequence": series_sequence
                }
            }

            async with self.session.patch(
                f"{self.api_url}/items/{book_id}/media",
                json=payload
            ) as resp:
                if resp.status in [200, 204]:
                    logger.debug(f"Updated: {title} -> {series_name} #{series_sequence}")
                    self.stats['books_updated'] += 1
                    return True
                else:
                    logger.warning(f"Failed to update {book_id}: {resp.status}")
                    return False
        except Exception as e:
            logger.warning(f"Error updating {book_id}: {e}")
            return False

    async def process_books(self, items: List[Dict]) -> None:
        """Process books and extract series from subtitles"""
        logger.info(f"Processing {len(items)} books...")

        for idx, item in enumerate(items, 1):
            if idx % 200 == 0:
                logger.info(f"  Progress: {idx}/{len(items)}")

            try:
                book_id = item.get('id')
                media = item.get('media', {})
                metadata = media.get('metadata', {})
                title = metadata.get('title', 'Unknown')
                subtitle = metadata.get('subtitle', '')
                series_name = metadata.get('seriesName')
                series_sequence = metadata.get('seriesSequence')

                self.stats['books_scanned'] += 1

                # Skip if already has proper series metadata
                if series_name and series_sequence:
                    continue

                # Try to extract from subtitle
                extracted_series, extracted_seq = self.extract_series_from_subtitle(subtitle)

                if extracted_series and extracted_seq:
                    self.stats['series_in_subtitle'] += 1
                    logger.info(f"Found in subtitle: {title}")
                    logger.info(f"  Subtitle: {subtitle}")
                    logger.info(f"  -> Series: {extracted_series} #{extracted_seq}")

                    # Update the book
                    await self.update_book_metadata(
                        book_id,
                        extracted_series,
                        extracted_seq,
                        title
                    )

            except Exception as e:
                logger.warning(f"Error processing book: {e}")
                self.stats['errors'].append(str(e))

    async def run(self):
        """Main workflow"""
        logger.info("=" * 80)
        logger.info("EXTRACT SERIES FROM SUBTITLES AND UPDATE BOOKS")
        logger.info("=" * 80)
        logger.info("")

        logger.info("Step 1: Testing API connection...")
        if not await self.test_connection():
            logger.error("Cannot connect to API")
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
        logger.info("COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Books scanned:                 {self.stats['books_scanned']}")
        logger.info(f"Books with series in subtitle: {self.stats['series_in_subtitle']}")
        logger.info(f"Books updated:                 {self.stats['books_updated']}")

        if self.stats['errors']:
            logger.info(f"Errors:                        {len(self.stats['errors'])}")

        logger.info("")
        logger.info("Done! Series info extracted and updated.")
        logger.info("")

        return True


async def main():
    if not ABS_TOKEN:
        logger.error("ERROR: ABS_TOKEN not found in environment!")
        return 1

    try:
        async with SubtitleSeriesExtractor(ABS_API_URL, ABS_TOKEN) as extractor:
            success = await extractor.run()
            return 0 if success else 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
