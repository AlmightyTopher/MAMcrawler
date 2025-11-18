#!/usr/bin/env python3
"""
Prepare Audiobook Files for Audio Verification

Creates a structured list of uncertain books with file paths
so we can listen to them and extract correct metadata.

This generates a manifest file that can be used with audio tools to:
1. Extract the opening 30-60 seconds
2. Convert to text with speech recognition
3. Manually verify and correct metadata
"""

import asyncio
import aiohttp
import logging
import os
import json
from typing import Dict, List, Optional
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('audio_verification_prep.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

ABS_URL = os.getenv('ABS_URL', 'http://localhost:13378').rstrip('/')
ABS_TOKEN = os.getenv('ABS_TOKEN')
ABS_API_URL = f"{ABS_URL}/api"
ABS_DATA_PATH = os.getenv('ABS_DATA_PATH', r'C:\Users\dogma\AppData\Local\Programs\Audiobookshelf\config\metadata')


class AudioVerificationPrepper:
    """Prepares uncertain books for audio verification"""

    def __init__(self, api_url: str = ABS_API_URL, api_key: Optional[str] = None):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.session = None
        self.verification_manifest = []
        self.stats = {
            'books_analyzed': 0,
            'books_with_audio_files': 0,
            'audio_files_found': 0,
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

    async def get_book_details(self, book_id: str) -> Optional[Dict]:
        """Get full book details including files and paths"""
        try:
            async with self.session.get(f"{self.api_url}/items/{book_id}") as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.warning(f"Error fetching book {book_id}: {e}")
        return None

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

        logger.info(f"Analyzing {len(unique_books)} unique uncertain books...")
        logger.info("")

        for idx, book_info in enumerate(unique_books, 1):
            if idx % 20 == 0:
                logger.info(f"  Progress: {idx}/{len(unique_books)}")

            try:
                self.stats['books_analyzed'] += 1
                book_id = book_info.get('id')
                current_metadata = book_info.get('metadata', {})
                title = current_metadata.get('title', 'Unknown')
                confidence = book_info.get('confidence', 0)

                # Get full book details
                book_details = await self.get_book_details(book_id)
                if not book_details:
                    continue

                media = book_details.get('media', {})
                files = media.get('files', [])

                # Find audio files
                audio_extensions = {'.m4b', '.mp3', '.m4a', '.aac', '.flac', '.ogg', '.wma', '.wav'}
                audio_files = [f for f in files if Path(f.get('filename', '')).suffix.lower() in audio_extensions]

                if audio_files:
                    self.stats['books_with_audio_files'] += 1
                    self.stats['audio_files_found'] += len(audio_files)

                    # Get book metadata for path
                    libraryItemId = book_details.get('libraryItemId')
                    libraryId = book_details.get('libraryId')

                    manifest_entry = {
                        'book_id': book_id,
                        'library_id': libraryId,
                        'library_item_id': libraryItemId,
                        'current_title': title,
                        'confidence': confidence,
                        'metadata': current_metadata,
                        'audio_files': [
                            {
                                'filename': f.get('filename'),
                                'path': f.get('path'),
                                'size_bytes': f.get('size'),
                                'duration_ms': f.get('duration')
                            }
                            for f in audio_files
                        ],
                        'extraction_notes': self._get_extraction_notes(title)
                    }

                    self.verification_manifest.append(manifest_entry)

            except Exception as e:
                logger.warning(f"Error processing book: {e}")
                self.stats['errors'].append(str(e))

    @staticmethod
    def _get_extraction_notes(title: str) -> str:
        """Generate notes about what to listen for"""
        notes = []

        if ' - ' in title and '(' not in title:
            notes.append("Title appears to have author embedded (contains ' - ')")

        if any(ext in title.lower() for ext in ['.mp3', '.m4b', '(mp3)', '(mp4)']):
            notes.append("File extension found in title - should be removed")

        if 'book' in title.lower() or '#' in title:
            notes.append("Series number mentioned in title")

        if len(title) > 100:
            notes.append("Title is very long - may be malformed")

        if title.count('_') > 3:
            notes.append("Multiple underscores - possible encoding issue")

        return " | ".join(notes) if notes else "No obvious issues detected"

    async def run(self):
        """Main workflow"""
        logger.info("=" * 80)
        logger.info("PREPARE AUDIOBOOKS FOR VERIFICATION")
        logger.info("=" * 80)
        logger.info("")

        await self.process_uncertain_books()

        # Save manifest
        manifest_file = "audio_verification_manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(self.verification_manifest, f, indent=2)

        logger.info("")
        logger.info("=" * 80)
        logger.info("PREPARATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Books analyzed:             {self.stats['books_analyzed']}")
        logger.info(f"Books with audio files:     {self.stats['books_with_audio_files']}")
        logger.info(f"Total audio files found:    {self.stats['audio_files_found']}")
        logger.info("")
        logger.info(f"Manifest saved to: {manifest_file}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. For each book in the manifest, listen to the first 30-60 seconds")
        logger.info("2. Extract: Title, Author, Series, Series Number")
        logger.info("3. Use update_from_verification.py to apply corrections")
        logger.info("")

        return True


async def main():
    if not ABS_TOKEN:
        logger.error("ERROR: ABS_TOKEN not found in environment!")
        return 1

    try:
        async with AudioVerificationPrepper(ABS_API_URL, ABS_TOKEN) as prepper:
            success = await prepper.run()
            return 0 if success else 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
