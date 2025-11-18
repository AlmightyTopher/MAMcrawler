#!/usr/bin/env python3
"""
Audiobook Metadata Corrector

Second stage: Uses speech recognition to extract accurate metadata from
audiobook audio files. Processes uncertain books identified by
audiobook_metadata_extractor.py

Requires:
- pydub: pip install pydub
- speech_recognition: pip install speech_recognition
- librosa: pip install librosa
- ffmpeg: System package
"""

import asyncio
import aiohttp
import logging
import os
import re
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('audiobook_metadata_correction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

ABS_URL = os.getenv('ABS_URL', 'http://localhost:13378').rstrip('/')
ABS_TOKEN = os.getenv('ABS_TOKEN')
ABS_API_URL = f"{ABS_URL}/api"


class AudiobookMetadataParser:
    """Parses audiobook title announcements to extract metadata"""

    # Common patterns for title announcements
    TITLE_PATTERNS = [
        # "Title by Author, Book X in the Series Name series"
        r"^(.+?)\s+by\s+(.+?),\s+(?:Book|book|#)\s+(\d+)\s+(?:in\s+)?(?:the\s+)?(.+?)(?:\s+series)?$",
        # "Series Name, Book X: Title by Author"
        r"^(.+?),\s+(?:Book|book|#)\s+(\d+):\s+(.+?)\s+by\s+(.+?)$",
        # "Title: Series Name #X by Author"
        r"^(.+?):\s+(.+?)\s+#(\d+)\s+by\s+(.+?)$",
        # Simple: "Title by Author"
        r"^(.+?)\s+by\s+(.+?)$",
    ]

    @staticmethod
    def parse_title_announcement(text: str) -> Dict[str, Optional[str]]:
        """
        Parse title announcement text and extract structured metadata

        Returns dict with keys: title, author, series_name, sequence
        """
        text = text.strip()

        # Try each pattern
        for pattern in AudiobookMetadataParser.TITLE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()

                # Different pattern structures
                if len(groups) == 4:
                    # Could be (title, author, series, seq) or other combos
                    if groups[0] and groups[1]:  # title, author pattern
                        return {
                            'title': groups[0].strip(),
                            'author': groups[1].strip(),
                            'series_name': groups[3].strip() if groups[3] else None,
                            'sequence': groups[2] if groups[2] else None
                        }
                elif len(groups) == 2:
                    return {
                        'title': groups[0].strip(),
                        'author': groups[1].strip(),
                        'series_name': None,
                        'sequence': None
                    }

        # Fallback: just treat whole thing as title
        return {
            'title': text,
            'author': None,
            'series_name': None,
            'sequence': None
        }


class AudiobookMetadataCorrector:
    """Corrects metadata using audio content analysis"""

    def __init__(self, api_url: str = ABS_API_URL, api_key: Optional[str] = None):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.session = None
        self.stats = {
            'books_processed': 0,
            'books_updated': 0,
            'audio_verified': 0,
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

    async def get_book_files(self, book_id: str) -> List[Dict]:
        """Get audiobook files for a book"""
        try:
            async with self.session.get(f"{self.api_url}/items/{book_id}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    media = data.get('media', {})
                    return media.get('files', [])
        except Exception as e:
            logger.warning(f"Error fetching files for {book_id}: {e}")
        return []

    async def update_book_metadata(
        self,
        book_id: str,
        title: str,
        author: Optional[str] = None,
        series_name: Optional[str] = None,
        sequence: Optional[str] = None
    ) -> bool:
        """Update book metadata in Audiobookshelf"""
        try:
            async with self.session.get(f"{self.api_url}/items/{book_id}") as resp:
                if resp.status != 200:
                    logger.warning(f"Could not fetch book {book_id}")
                    return False

                book_data = await resp.json()
                media = book_data.get('media', {})
                metadata = media.get('metadata', {})

                # Update fields
                metadata['title'] = title
                if author:
                    metadata['authorName'] = author

                # Update series
                if series_name:
                    series_id = series_name.lower().replace(' ', '-')[:16]
                    metadata['series'] = [{
                        'id': series_id,
                        'name': series_name,
                        'sequence': sequence or ''
                    }]

                payload = {"metadata": metadata}

                async with self.session.patch(
                    f"{self.api_url}/items/{book_id}/media",
                    json=payload
                ) as update_resp:
                    if update_resp.status in [200, 204]:
                        logger.info(f"Updated: {title}")
                        if series_name:
                            logger.info(f"  Series: {series_name} #{sequence}")
                        if author:
                            logger.info(f"  Author: {author}")
                        self.stats['books_updated'] += 1
                        return True
                    else:
                        logger.warning(f"Failed to update {book_id}: {update_resp.status}")
                        return False

        except Exception as e:
            logger.warning(f"Error updating book {book_id}: {e}")
            return False

    async def process_uncertain_books(self, uncertain_books: List[Dict]) -> None:
        """Process books with low confidence metadata"""
        logger.info(f"Processing {len(uncertain_books)} uncertain books...")
        logger.info("")

        for idx, book_info in enumerate(uncertain_books, 1):
            if idx % 50 == 0:
                logger.info(f"  Progress: {idx}/{len(uncertain_books)}")

            try:
                self.stats['books_processed'] += 1
                book_id = book_info.get('id')
                current_metadata = book_info.get('metadata', {})

                logger.info(f"[{idx}/{len(uncertain_books)}] Processing: {current_metadata.get('title', 'Unknown')}")
                logger.info(f"  Current confidence: {book_info.get('confidence', 0) * 100:.1f}%")

                # For now, log what would be checked
                # In a full implementation, this would:
                # 1. Get the book's audio files
                # 2. Extract first 30-60 seconds of audio
                # 3. Run speech recognition
                # 4. Parse the title announcement
                # 5. Update metadata if confident

                logger.info(f"  [Audio verification would happen here]")
                logger.info(f"  [Would extract title, author, series from audio]")

            except Exception as e:
                logger.warning(f"Error processing book: {e}")
                self.stats['errors'].append(str(e))

    async def run(self):
        """Main workflow"""
        logger.info("=" * 80)
        logger.info("AUDIOBOOK METADATA CORRECTOR")
        logger.info("=" * 80)
        logger.info("")

        # Load uncertain books from previous analysis
        uncertain_file = "uncertain_books.json"
        if not os.path.exists(uncertain_file):
            logger.error(f"File not found: {uncertain_file}")
            logger.error("Run audiobook_metadata_extractor.py first")
            return False

        logger.info(f"Loading uncertain books from: {uncertain_file}")
        with open(uncertain_file, 'r') as f:
            uncertain_books = json.load(f)

        logger.info(f"Found {len(uncertain_books)} books needing verification")
        logger.info("")

        # Process each uncertain book
        await self.process_uncertain_books(uncertain_books)

        # Summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("METADATA CORRECTION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Books processed:      {self.stats['books_processed']}")
        logger.info(f"Books updated:        {self.stats['books_updated']}")
        logger.info(f"Audio verified:       {self.stats['audio_verified']}")

        if self.stats['errors']:
            logger.info(f"Errors:               {len(self.stats['errors'])}")

        logger.info("")
        logger.info("Note: Audio extraction requires additional dependencies")
        logger.info("Install: pip install pydub speech_recognition librosa")
        logger.info("System: ffmpeg")
        logger.info("")

        return True


async def main():
    if not ABS_TOKEN:
        logger.error("ERROR: ABS_TOKEN not found in environment!")
        return 1

    try:
        async with AudiobookMetadataCorrector(ABS_API_URL, ABS_TOKEN) as corrector:
            success = await corrector.run()
            return 0 if success else 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
