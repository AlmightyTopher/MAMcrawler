#!/usr/bin/env python3
"""
Audiobookshelf Series Populator - Enhanced Version with Environment Support

This script populates series in Audiobookshelf using the REST API.
It loads the API token from .env automatically.
"""

import asyncio
import aiohttp
import json
import logging
import re
import os
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
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
        logging.FileHandler('series_populator_run.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Get configuration from environment
ABS_URL = os.getenv('ABS_URL', 'http://localhost:13378').rstrip('/')
ABS_TOKEN = os.getenv('ABS_TOKEN')
ABS_API_URL = f"{ABS_URL}/api"


class SeriesPopulator:
    """Populates Audiobookshelf series using REST API with proper authentication"""

    def __init__(self, api_url: str = ABS_API_URL, api_key: Optional[str] = None):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.session = None
        self.stats = {
            'libraries_found': 0,
            'books_scanned': 0,
            'series_created': 0,
            'series_updated': 0,
            'books_linked': 0,
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

    def extract_series_from_items(self, items: List[Dict]) -> Dict[str, List[Tuple[str, Optional[float]]]]:
        """
        Extract series information from library items.
        Returns: {series_name: [(book_id, sequence_number), ...]}
        """
        series_map = defaultdict(list)

        for item in items:
            try:
                # Get book metadata
                media = item.get('media', {})
                metadata = media.get('metadata', {})

                book_id = item.get('id')
                title = metadata.get('title', 'Unknown')

                # Extract series name and sequence
                series_name = metadata.get('seriesName') or metadata.get('series')
                sequence = metadata.get('seriesSequence')

                # Clean up series name
                if series_name:
                    series_name = series_name.strip()

                    # Try to parse sequence if it's a string
                    if isinstance(sequence, str):
                        match = re.search(r'[\d.]+', sequence)
                        sequence = float(match.group()) if match else None
                    elif isinstance(sequence, (int, float)):
                        sequence = float(sequence)
                    else:
                        sequence = None

                    if book_id:
                        series_map[series_name].append((book_id, sequence, title))
                        self.stats['books_scanned'] += 1

            except Exception as e:
                logger.warning(f"Error extracting series from item: {e}")
                self.stats['errors'].append(f"Extract error: {str(e)}")

        logger.info(f"Extracted {len(series_map)} unique series from {self.stats['books_scanned']} books")
        return dict(series_map)

    async def create_series(self, library_id: str, series_name: str) -> Optional[str]:
        """Create a new series in the library"""
        try:
            payload = {
                "name": series_name,
                "description": ""
            }

            async with self.session.post(
                f"{self.api_url}/libraries/{library_id}/series",
                json=payload
            ) as resp:
                if resp.status in [200, 201]:
                    data = await resp.json()
                    series_id = data.get('id')
                    logger.info(f"  Created series: {series_name} (ID: {series_id})")
                    self.stats['series_created'] += 1
                    return series_id
                else:
                    logger.warning(f"  Failed to create series {series_name}: {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"  Error creating series {series_name}: {e}")
            self.stats['errors'].append(f"Create series error: {str(e)}")
            return None

    async def add_book_to_series(
        self,
        library_id: str,
        series_id: str,
        book_id: str,
        sequence: Optional[float] = None,
        title: Optional[str] = None
    ) -> bool:
        """Add a book to a series"""
        try:
            payload = {
                "bookId": book_id,
                "sequence": sequence or ""
            }

            async with self.session.post(
                f"{self.api_url}/libraries/{library_id}/series/{series_id}/addBook",
                json=payload
            ) as resp:
                if resp.status in [200, 201]:
                    seq_str = f" (seq: {sequence})" if sequence else ""
                    logger.debug(f"    Added {title or book_id}{seq_str}")
                    self.stats['books_linked'] += 1
                    return True
                else:
                    logger.warning(f"    Failed to add book to series: {resp.status}")
                    return False
        except Exception as e:
            logger.warning(f"    Error adding book to series: {e}")
            return False

    async def populate_series(self):
        """Main workflow: extract and populate series"""
        logger.info("=" * 80)
        logger.info("AUDIOBOOKSHELF SERIES POPULATOR - API VERSION")
        logger.info("=" * 80)
        logger.info("")

        # Test API connection
        logger.info("Step 1: Testing API connection...")
        logger.info(f"  URL: {self.api_url}")
        logger.info(f"  Token: {'*' * 20}...{self.api_key[-10:] if self.api_key else 'NONE'}")

        if not await self.test_connection():
            logger.error("Cannot connect to Audiobookshelf API")
            logger.error("Make sure:")
            logger.error("  1. Audiobookshelf is running on {ABS_URL}")
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

            # Extract series from metadata
            series_map = self.extract_series_from_items(items)

            if not series_map:
                logger.info("No series found in book metadata")
                continue

            # Create/update series and link books
            for series_name, books in series_map.items():
                logger.info(f"Series: {series_name} ({len(books)} books)")

                # Create series
                series_id = await self.create_series(library_id, series_name)
                if not series_id:
                    logger.error(f"  Failed to create series: {series_name}")
                    continue

                # Add books to series
                for book_id, sequence, title in books:
                    await self.add_book_to_series(library_id, series_id, book_id, sequence, title)

            logger.info("")

        # Print summary
        logger.info("=" * 80)
        logger.info("POPULATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Libraries scanned:     {self.stats['libraries_found']}")
        logger.info(f"Books scanned:         {self.stats['books_scanned']}")
        logger.info(f"Series created:        {self.stats['series_created']}")
        logger.info(f"Books linked:          {self.stats['books_linked']}")

        if self.stats['errors']:
            logger.info(f"Errors encountered:    {len(self.stats['errors'])}")
            for error in self.stats['errors'][:10]:
                logger.info(f"  - {error}")

        logger.info("")
        logger.info("Series should now be visible in Audiobookshelf!")
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
        async with SeriesPopulator(ABS_API_URL, ABS_TOKEN) as populator:
            success = await populator.populate_series()
            return 0 if success else 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
