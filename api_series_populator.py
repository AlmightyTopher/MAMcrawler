"""
Audiobookshelf Series Populator via REST API

This script populates series in Audiobookshelf using the REST API
instead of direct database access. This is:
- Safer (no database locking issues)
- Simpler (uses the intended API interface)
- Faster (no need to restart Audiobookshelf)
- More reliable (respects Audiobookshelf's data structures)

Key Features:
- Extracts series names from book metadata
- Uses Audiobookshelf REST API to create/update series
- Properly links books to series with sequence numbers
- Provides detailed logging and error handling
"""

import asyncio
import aiohttp
import json
import logging
import re
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from pathlib import Path
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('api_series_populator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Audiobookshelf API settings
ABS_API_URL = "http://localhost:13378/api"
ABS_API_KEY = None  # Will detect or prompt for API key


class APISeriesPopulator:
    """Populates Audiobookshelf series using REST API"""

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
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with API key if available"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def test_connection(self) -> bool:
        """Test API connectivity"""
        try:
            async with self.session.get(
                f"{self.api_url}/libraries",
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                logger.info(f"API Connection test: Status {resp.status}")
                if resp.status == 401:
                    logger.info("API requires authentication - proceeding with available data")
                return resp.status in [200, 401]  # 401 if no auth, but API works
        except Exception as e:
            logger.error(f"API Connection test failed: {e}")
            return False

    async def get_libraries(self) -> List[Dict]:
        """Get all libraries from Audiobookshelf"""
        try:
            async with self.session.get(
                f"{self.api_url}/libraries",
                headers=self._get_headers()
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    libraries = data.get('libraries', [])
                    self.stats['libraries_found'] = len(libraries)
                    logger.info(f"Found {len(libraries)} libraries")
                    return libraries
                elif resp.status == 401:
                    logger.warning("API requires authentication (Bearer token)")
                    return []
                else:
                    logger.error(f"Failed to get libraries: {resp.status}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching libraries: {e}")
            self.stats['errors'].append(str(e))
            return []

    async def get_library_items(self, library_id: str) -> List[Dict]:
        """Get all library items (books) from a library"""
        try:
            # Get library items with metadata
            async with self.session.get(
                f"{self.api_url}/libraries/{library_id}/items",
                headers=self._get_headers()
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    items = data.get('results', data.get('libraryItems', []))
                    logger.info(f"Found {len(items)} items in library {library_id}")
                    return items
                else:
                    logger.error(f"Failed to get library items: {resp.status}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching library items: {e}")
            self.stats['errors'].append(str(e))
            return []

    async def get_series_for_library(self, library_id: str) -> List[Dict]:
        """Get all existing series in a library"""
        try:
            async with self.session.get(
                f"{self.api_url}/libraries/{library_id}/series",
                headers=self._get_headers()
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    series_list = data.get('results', data.get('series', []))
                    logger.info(f"Found {len(series_list)} existing series")
                    return series_list
                else:
                    logger.warning(f"Could not fetch existing series: {resp.status}")
                    return []
        except Exception as e:
            logger.warning(f"Error fetching existing series: {e}")
            return []

    def extract_series_from_items(self, items: List[Dict]) -> Dict[str, List[Tuple[str, Optional[int]]]]:
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
                    elif not isinstance(sequence, (int, float)):
                        sequence = None

                    book_id = item.get('id')
                    if book_id:
                        series_map[series_name].append((book_id, sequence))
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
                headers=self._get_headers(),
                json=payload
            ) as resp:
                if resp.status in [200, 201]:
                    data = await resp.json()
                    series_id = data.get('id')
                    logger.info(f"Created series: {series_name} (ID: {series_id})")
                    self.stats['series_created'] += 1
                    return series_id
                else:
                    logger.warning(f"Failed to create series {series_name}: {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"Error creating series {series_name}: {e}")
            self.stats['errors'].append(f"Create series error: {str(e)}")
            return None

    async def add_book_to_series(self, library_id: str, series_id: str, book_id: str, sequence: Optional[float] = None) -> bool:
        """Add a book to a series"""
        try:
            payload = {
                "bookId": book_id,
                "sequence": sequence or ""
            }

            async with self.session.post(
                f"{self.api_url}/libraries/{library_id}/series/{series_id}/addBook",
                headers=self._get_headers(),
                json=payload
            ) as resp:
                if resp.status in [200, 201]:
                    logger.debug(f"Added book {book_id} to series {series_id}")
                    self.stats['books_linked'] += 1
                    return True
                else:
                    logger.warning(f"Failed to add book to series: {resp.status}")
                    return False
        except Exception as e:
            logger.warning(f"Error adding book to series: {e}")
            return False

    async def populate_series(self):
        """Main workflow: extract and populate series"""
        logger.info("=" * 80)
        logger.info("STARTING API-BASED SERIES POPULATION")
        logger.info("=" * 80)
        logger.info("")

        # Test API connection
        logger.info("Step 1: Testing API connection...")
        if not await self.test_connection():
            logger.error("Cannot connect to Audiobookshelf API")
            logger.error("Make sure Audiobookshelf is running on localhost:13378")
            return False

        logger.info("[OK] API connection successful")
        logger.info("")

        # Get libraries
        logger.info("Step 2: Getting libraries...")
        libraries = await self.get_libraries()
        if not libraries:
            logger.error("No libraries found or API requires authentication")
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

            # Get existing series
            existing_series = await self.get_series_for_library(library_id)
            existing_series_names = {s.get('name'): s.get('id') for s in existing_series}

            # Create/update series and link books
            for series_name, books in series_map.items():
                logger.info(f"Processing series: {series_name}")

                # Check if series exists
                if series_name in existing_series_names:
                    series_id = existing_series_names[series_name]
                    logger.info(f"  Series already exists (ID: {series_id})")
                    self.stats['series_updated'] += 1
                else:
                    # Create new series
                    series_id = await self.create_series(library_id, series_name)
                    if not series_id:
                        logger.error(f"  Failed to create series: {series_name}")
                        continue

                # Add books to series
                for book_id, sequence in books:
                    await self.add_book_to_series(library_id, series_id, book_id, sequence)

            logger.info("")

        # Print summary
        logger.info("=" * 80)
        logger.info("POPULATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Libraries scanned:     {self.stats['libraries_found']}")
        logger.info(f"Books scanned:         {self.stats['books_scanned']}")
        logger.info(f"Series created:        {self.stats['series_created']}")
        logger.info(f"Series updated:        {self.stats['series_updated']}")
        logger.info(f"Books linked:          {self.stats['books_linked']}")

        if self.stats['errors']:
            logger.info(f"Errors encountered:    {len(self.stats['errors'])}")
            for error in self.stats['errors'][:5]:  # Show first 5 errors
                logger.info(f"  - {error}")

        logger.info("")
        logger.info("Series should now be visible in Audiobookshelf!")
        logger.info("Visit http://localhost:13378 to verify")
        logger.info("")

        return True


async def main():
    """Main entry point"""
    try:
        async with APISeriesPopulator() as populator:
            success = await populator.populate_series()
            return 0 if success else 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
