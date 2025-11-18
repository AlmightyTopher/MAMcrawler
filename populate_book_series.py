#!/usr/bin/env python3
"""
Audiobookshelf Book Series Populator - Direct Metadata Update

This script updates book metadata directly with series information.
It's the most reliable method that doesn't require special series creation endpoints.
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

# Load environment variables from .env
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('populate_book_series.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Get configuration from environment
ABS_URL = os.getenv('ABS_URL', 'http://localhost:13378').rstrip('/')
ABS_TOKEN = os.getenv('ABS_TOKEN')
ABS_API_URL = f"{ABS_URL}/api"


class BookSeriesPopulator:
    """Populates book metadata with series information via direct API updates"""

    def __init__(self, api_url: str = ABS_API_URL, api_key: Optional[str] = None):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.session = None
        self.stats = {
            'libraries_found': 0,
            'books_scanned': 0,
            'books_with_series': 0,
            'books_updated': 0,
            'books_unchanged': 0,
            'errors': []
        }

    async def __aenter__(self):
        """Async context manager entry"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self.session = aiohttp.ClientSession(headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def test_connection(self) -> bool:
        """Test API connectivity"""
        try:
            async with self.session.get(
                f"{self.api_url}/libraries",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    logger.info(f"API Connection successful (Status: {resp.status})")
                    return True
                elif resp.status == 401:
                    logger.error(f"API returned 401 Unauthorized - check ABS_TOKEN")
                    return False
                else:
                    logger.error(f"API Connection failed (Status: {resp.status})")
                    return False
        except Exception as e:
            logger.error(f"API Connection test failed: {e}")
            return False

    async def get_libraries(self) -> List[Dict]:
        """Get all libraries from Audiobookshelf"""
        try:
            async with self.session.get(f"{self.api_url}/libraries") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    libraries = data.get('libraries', [])
                    self.stats['libraries_found'] = len(libraries)
                    logger.info(f"Found {len(libraries)} libraries")
                    return libraries
                else:
                    logger.error(f"Failed to get libraries: {resp.status}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching libraries: {e}")
            self.stats['errors'].append(str(e))
            return []

    async def get_library_items(self, library_id: str, limit: int = 100) -> List[Dict]:
        """Get all library items (books) from a library with pagination"""
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
                        total = data.get('total', 0)

                        logger.debug(f"Fetched {len(items)} items (offset: {offset}, total: {total})")

                        if offset + len(items) >= total:
                            break

                        offset += len(items)
                    else:
                        logger.error(f"Failed to get library items: {resp.status}")
                        break

            logger.info(f"Found {len(all_items)} items in library {library_id}")
            return all_items

        except Exception as e:
            logger.error(f"Error fetching library items: {e}")
            self.stats['errors'].append(str(e))
            return all_items

    def extract_series_info(self, item: Dict) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract series name and sequence from book metadata.
        Handles formats like:
        - "Series Name #1"
        - "Series Name"
        - seriesName field with seriesSequence field
        """
        media = item.get('media', {})
        metadata = media.get('metadata', {})

        # Get series name
        series_name = metadata.get('seriesName') or metadata.get('series')
        series_sequence = metadata.get('seriesSequence')

        # Clean and parse
        if series_name:
            series_name = series_name.strip()

            # If series_name includes the sequence, extract it
            if '#' in series_name:
                # Format: "Series Name #1"
                parts = series_name.rsplit('#', 1)
                if len(parts) == 2:
                    return parts[0].strip(), parts[1].strip()
            elif series_sequence:
                # Format: seriesName + seriesSequence separate
                return series_name, str(series_sequence).strip()
            else:
                # Just the series name
                return series_name, None

        return None, None

    async def update_book_metadata(
        self,
        book_id: str,
        series_name: Optional[str] = None,
        series_sequence: Optional[str] = None,
        title: Optional[str] = None
    ) -> bool:
        """Update book metadata with series information"""
        try:
            metadata = {}

            if series_name:
                if series_sequence:
                    # Format as "Series Name #1"
                    metadata['seriesName'] = f"{series_name} #{series_sequence}"
                else:
                    metadata['seriesName'] = series_name

                # Also set seriesSequence separately if available
                if series_sequence:
                    metadata['seriesSequence'] = series_sequence

            if not metadata:
                return False

            payload = {"metadata": metadata}

            async with self.session.patch(
                f"{self.api_url}/items/{book_id}/media",
                json=payload
            ) as resp:
                if resp.status in [200, 204]:
                    seq_str = f" (#{series_sequence})" if series_sequence else ""
                    logger.debug(f"Updated: {title} -> {series_name}{seq_str}")
                    self.stats['books_updated'] += 1
                    return True
                else:
                    logger.warning(f"Failed to update {book_id}: {resp.status}")
                    return False

        except Exception as e:
            logger.warning(f"Error updating book {book_id}: {e}")
            return False

    async def process_books(self, items: List[Dict]) -> None:
        """Process all books and ensure series metadata is properly formatted"""
        logger.info(f"Processing {len(items)} books...")

        for idx, item in enumerate(items, 1):
            if idx % 100 == 0:
                logger.info(f"  Progress: {idx}/{len(items)}")

            try:
                book_id = item.get('id')
                media = item.get('media', {})
                metadata = media.get('metadata', {})
                title = metadata.get('title', 'Unknown')

                series_name, series_sequence = self.extract_series_info(item)

                if series_name:
                    self.stats['books_with_series'] += 1

                    # Only update if the format needs fixing or if seriesSequence is missing
                    current_series_name = metadata.get('seriesName', '')
                    current_sequence = metadata.get('seriesSequence', '')

                    # Check if it needs updating
                    needs_update = False

                    if series_sequence and not current_sequence:
                        # Has sequence but not stored separately
                        needs_update = True
                    elif not current_series_name and series_name:
                        # Missing seriesName
                        needs_update = True

                    if needs_update:
                        await self.update_book_metadata(
                            book_id,
                            series_name,
                            series_sequence,
                            title
                        )
                    else:
                        self.stats['books_unchanged'] += 1
                else:
                    self.stats['books_scanned'] += 1

            except Exception as e:
                logger.warning(f"Error processing book: {e}")
                self.stats['errors'].append(f"Process error: {str(e)}")

    async def populate_series(self):
        """Main workflow: ensure series metadata is properly set"""
        logger.info("=" * 80)
        logger.info("AUDIOBOOKSHELF BOOK SERIES POPULATOR")
        logger.info("=" * 80)
        logger.info("")

        # Test API connection
        logger.info("Step 1: Testing API connection...")
        logger.info(f"  URL: {self.api_url}")
        logger.info(f"  Token: {'*' * 20}...{self.api_key[-10:] if self.api_key else 'NONE'}")

        if not await self.test_connection():
            logger.error("Cannot connect to Audiobookshelf API")
            logger.error("Make sure:")
            logger.error(f"  1. Audiobookshelf is running on {ABS_URL}")
            logger.error("  2. ABS_TOKEN is set in .env")
            logger.error("  3. The token is valid and hasn't expired")
            return False

        logger.info("[OK] API connection successful")
        logger.info("")

        # Get libraries
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

            # Get books in library
            items = await self.get_library_items(library_id)
            if not items:
                logger.warning(f"No items in library {library_name}")
                continue

            # Process books
            await self.process_books(items)

            logger.info("")

        # Print summary
        logger.info("=" * 80)
        logger.info("SERIES METADATA POPULATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Libraries scanned:     {self.stats['libraries_found']}")
        logger.info(f"Books scanned:         {self.stats['books_scanned']}")
        logger.info(f"Books with series:     {self.stats['books_with_series']}")
        logger.info(f"Books updated:         {self.stats['books_updated']}")
        logger.info(f"Books unchanged:       {self.stats['books_unchanged']}")

        if self.stats['errors']:
            logger.info(f"Errors encountered:    {len(self.stats['errors'])}")
            for error in self.stats['errors'][:10]:
                logger.info(f"  - {error}")

        logger.info("")
        logger.info("Series information is now properly set in book metadata!")
        logger.info(f"Visit {ABS_URL} to verify")
        logger.info("")

        return True


async def main():
    """Main entry point"""
    if not ABS_TOKEN:
        logger.error("ERROR: ABS_TOKEN not found in environment!")
        logger.error("Please add ABS_TOKEN to your .env file")
        return 1

    try:
        async with BookSeriesPopulator(ABS_API_URL, ABS_TOKEN) as populator:
            success = await populator.populate_series()
            return 0 if success else 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
