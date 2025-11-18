#!/usr/bin/env python3
"""
Clean Malformed Metadata

Automatically fixes common metadata issues in uncertain books:
- Removes file format extensions from titles (MP3, mp3, .m4b, etc.)
- Extracts author names from titles
- Extracts series info from titles
- Cleans up special characters and duplicates
"""

import asyncio
import aiohttp
import logging
import os
import re
import json
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('clean_metadata.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

ABS_URL = os.getenv('ABS_URL', 'http://localhost:13378').rstrip('/')
ABS_TOKEN = os.getenv('ABS_TOKEN')
ABS_API_URL = f"{ABS_URL}/api"


class MetadataCleaner:
    """Cleans and normalizes malformed metadata"""

    # File format patterns to remove
    FILE_FORMATS = r'\.(MP3|mp3|m4b|m4a|aac|flac|ogg|wma|wav)$'
    FILE_FORMAT_SUFFIX = r'\s*\(MP3\)|\s*\(mp3\)|\s*\bmp3\b|\s*\bMP3\b'

    # Author extraction patterns
    AUTHOR_PATTERNS = [
        r'^(.+?)\s*-\s*(.+)$',  # "Author - Title"
        r'^([A-Z][a-z]+\s+[A-Z][a-z]+)\s*-\s*(.+)$',  # "FirstName LastName - Title"
        r'^\(.*?\)\s+(.+)$',  # "(Year) Title"
    ]

    # Series extraction patterns
    SERIES_PATTERNS = [
        r',\s*(?:Book|book|Vol\.?|Volume)\s+(\d+)(?:\s*-\s*(.+))?',  # ", Book 12" or ", Book 12 - Series Name"
        r'-\s*(.+?),\s+(?:Book|book)\s+(\d+)',  # "Title - Series, Book 12"
        r'(?:Book|book)\s+(\d+)\s+(?:in\s+)?(?:the\s+)?(.+?)(?:\s+series)?$',  # "Book 12 in Series Name"
    ]

    @staticmethod
    def clean_title(title: str) -> Tuple[str, Dict]:
        """
        Clean title and extract metadata

        Returns: (cleaned_title, extracted_metadata_dict)
        """
        original_title = title
        extracted = {
            'author': None,
            'series_name': None,
            'sequence': None,
            'original_title': original_title
        }

        # Step 1: Remove file format suffixes
        title = re.sub(MetadataCleaner.FILE_FORMAT_SUFFIX, '', title).strip()
        title = re.sub(MetadataCleaner.FILE_FORMATS, '', title).strip()

        # Step 2: Try to extract author from common patterns
        for pattern in MetadataCleaner.AUTHOR_PATTERNS:
            match = re.match(pattern, title)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    extracted['author'] = groups[0].strip()
                    title = groups[1].strip()
                    break

        # Step 3: Extract series information
        # Look for patterns like "Title, Book 12 in Series Name"
        for pattern in MetadataCleaner.SERIES_PATTERNS:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                groups = match.groups()
                # Pattern varies, try to find sequence and series
                if len(groups) >= 1:
                    # First group is usually the book number or series name
                    first = groups[0].strip() if groups[0] else None

                    # Check if first is a number (sequence)
                    if first and first.isdigit():
                        extracted['sequence'] = first
                        if len(groups) > 1 and groups[1]:
                            extracted['series_name'] = groups[1].strip()
                    else:
                        # First is series name
                        extracted['series_name'] = first
                        if len(groups) > 1 and groups[1] and groups[1].isdigit():
                            extracted['sequence'] = groups[1].strip()

                # Remove series info from title
                title = re.sub(pattern, '', title, flags=re.IGNORECASE).strip()
                break

        # Step 4: Clean up remaining title
        # Remove leading/trailing dashes, colons, commas
        title = re.sub(r'^[\s\-:,]+', '', title).strip()
        title = re.sub(r'[\s\-:,]+$', '', title).strip()

        # Remove duplicate spaces
        title = re.sub(r'\s+', ' ', title).strip()

        return title, extracted

    @staticmethod
    def should_update(current_title: str, cleaned_title: str, extracted: Dict) -> bool:
        """Determine if metadata should be updated"""
        # Only update if we found significant issues
        has_file_format = bool(re.search(MetadataCleaner.FILE_FORMAT_SUFFIX, current_title))
        has_embedded_author = ' - ' in current_title and extracted.get('author')
        has_embedded_series = extracted.get('series_name') is not None

        return has_file_format or has_embedded_author or has_embedded_series


class MetadataUpdater:
    """Updates book metadata in Audiobookshelf"""

    def __init__(self, api_url: str = ABS_API_URL, api_key: Optional[str] = None):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.session = None
        self.stats = {
            'books_analyzed': 0,
            'books_updated': 0,
            'updates_made': {
                'title': 0,
                'author': 0,
                'series': 0,
            },
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

    async def update_book(self, book_id: str, cleaned_title: str, extracted: Dict) -> bool:
        """Update book metadata"""
        try:
            async with self.session.get(f"{self.api_url}/items/{book_id}") as resp:
                if resp.status != 200:
                    return False

                book_data = await resp.json()
                media = book_data.get('media', {})
                metadata = media.get('metadata', {})

                # Apply updates
                old_title = metadata.get('title')
                if cleaned_title != old_title:
                    metadata['title'] = cleaned_title
                    self.stats['updates_made']['title'] += 1

                if extracted.get('author') and extracted['author'] != metadata.get('authorName'):
                    metadata['authorName'] = extracted['author']
                    self.stats['updates_made']['author'] += 1

                if extracted.get('series_name'):
                    series_id = extracted['series_name'].lower().replace(' ', '-')[:16]
                    metadata['series'] = [{
                        'id': series_id,
                        'name': extracted['series_name'],
                        'sequence': extracted.get('sequence', '')
                    }]
                    self.stats['updates_made']['series'] += 1

                payload = {"metadata": metadata}

                async with self.session.patch(
                    f"{self.api_url}/items/{book_id}/media",
                    json=payload
                ) as update_resp:
                    if update_resp.status in [200, 204]:
                        logger.info(f"Updated: {cleaned_title}")
                        if extracted.get('author'):
                            logger.info(f"  Author: {extracted['author']}")
                        if extracted.get('series_name'):
                            logger.info(f"  Series: {extracted['series_name']} #{extracted.get('sequence', '?')}")
                        self.stats['books_updated'] += 1
                        return True

        except Exception as e:
            logger.warning(f"Error updating {book_id}: {e}")
            self.stats['errors'].append(str(e))

        return False

    async def process_uncertain_books(self) -> None:
        """Process books from uncertain_books.json"""
        uncertain_file = "uncertain_books.json"
        if not os.path.exists(uncertain_file):
            logger.error(f"File not found: {uncertain_file}")
            return

        with open(uncertain_file, 'r') as f:
            uncertain_books = json.load(f)

        # Remove duplicates by ID
        seen_ids = set()
        unique_books = []
        for book in uncertain_books:
            book_id = book.get('id')
            if book_id not in seen_ids:
                seen_ids.add(book_id)
                unique_books.append(book)

        logger.info(f"Processing {len(unique_books)} uncertain books (after deduplication)...")
        logger.info("")

        for idx, book_info in enumerate(unique_books, 1):
            if idx % 20 == 0:
                logger.info(f"  Progress: {idx}/{len(unique_books)}")

            try:
                self.stats['books_analyzed'] += 1
                book_id = book_info.get('id')
                current_title = book_info.get('metadata', {}).get('title', 'Unknown')

                # Clean the title
                cleaned_title, extracted = MetadataCleaner.clean_title(current_title)

                # Check if update is needed
                if MetadataCleaner.should_update(current_title, cleaned_title, extracted):
                    logger.info(f"[{idx}/{len(unique_books)}] Cleaning: {current_title}")
                    logger.info(f"  -> {cleaned_title}")
                    await self.update_book(book_id, cleaned_title, extracted)
                else:
                    logger.debug(f"[{idx}/{len(unique_books)}] No changes needed: {current_title}")

            except Exception as e:
                logger.warning(f"Error processing book: {e}")
                self.stats['errors'].append(str(e))

    async def run(self):
        """Main workflow"""
        logger.info("=" * 80)
        logger.info("CLEAN MALFORMED METADATA")
        logger.info("=" * 80)
        logger.info("")

        await self.process_uncertain_books()

        logger.info("")
        logger.info("=" * 80)
        logger.info("METADATA CLEANING COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Books analyzed:       {self.stats['books_analyzed']}")
        logger.info(f"Books updated:        {self.stats['books_updated']}")
        logger.info("")
        logger.info("Updates made:")
        logger.info(f"  - Titles cleaned:     {self.stats['updates_made']['title']}")
        logger.info(f"  - Authors extracted:  {self.stats['updates_made']['author']}")
        logger.info(f"  - Series extracted:   {self.stats['updates_made']['series']}")

        if self.stats['errors']:
            logger.info(f"Errors:               {len(self.stats['errors'])}")

        logger.info("")
        logger.info("Done!")
        logger.info("")

        return True


async def main():
    if not ABS_TOKEN:
        logger.error("ERROR: ABS_TOKEN not found in environment!")
        return 1

    try:
        async with MetadataUpdater(ABS_API_URL, ABS_TOKEN) as updater:
            success = await updater.run()
            return 0 if success else 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
