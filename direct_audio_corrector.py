#!/usr/bin/env python3
"""
Direct Audio-Based Corrector

Simple, practical approach:
- We extracted audio from the books
- The audio tells us what the actual title/author should be
- Apply those corrections directly, with logging for audit trail
- The audio is the source of truth
"""

import asyncio
import aiohttp
import logging
import json
import os
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('direct_audio_correction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

ABS_URL = os.getenv('ABS_URL', 'http://localhost:13378').rstrip('/')
ABS_TOKEN = os.getenv('ABS_TOKEN')
ABS_API_URL = f"{ABS_URL}/api"


class DirectAudioCorrector:
    """Apply corrections based directly on audio extraction"""

    def __init__(self, api_url: str = ABS_API_URL, api_key: Optional[str] = None):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.session = None
        self.stats = {
            'books_processed': 0,
            'books_corrected': 0,
            'corrections': []
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

    @staticmethod
    def clean_parsed_title(title: str) -> str:
        """Clean up parsed titles (remove leading words like 'law', 'this is')"""
        title = title.strip().lower()

        # Remove common prefixes from speech recognition
        prefixes = [
            'this is ',
            'law ',
            'audible ',
            'recorded books ',
            'pandora radio ',
            'presents ',
        ]

        for prefix in prefixes:
            if title.startswith(prefix):
                title = title[len(prefix):].strip()

        return title.strip()

    @staticmethod
    def clean_parsed_author(author: str) -> str:
        """Clean up parsed author names"""
        author = author.strip()
        # Capitalize properly
        parts = author.split()
        return ' '.join(word.capitalize() for word in parts)

    async def update_book_metadata(self, book_id: str, new_title: str, new_author: str, transcript: str) -> bool:
        """Update book metadata via Audiobookshelf API"""
        try:
            async with self.session.get(f"{self.api_url}/items/{book_id}") as resp:
                if resp.status != 200:
                    logger.warning(f"Could not fetch book {book_id}")
                    return False

                book_data = await resp.json()
                media = book_data.get('media', {})
                metadata = media.get('metadata', {})

                old_title = metadata.get('title')
                old_author = metadata.get('authorName')

                # Update
                metadata['title'] = new_title
                metadata['authorName'] = new_author

                payload = {"metadata": metadata}

                async with self.session.patch(
                    f"{self.api_url}/items/{book_id}/media",
                    json=payload
                ) as update_resp:
                    if update_resp.status in [200, 204]:
                        logger.info(f"  Updated successfully")
                        logger.info(f"    Title: '{old_title}' -> '{new_title}'")
                        logger.info(f"    Author: '{old_author}' -> '{new_author}'")
                        logger.info(f"    Audio evidence: {transcript[:100]}...")
                        self.stats['books_corrected'] += 1
                        return True
                    else:
                        logger.warning(f"  Failed to update: HTTP {update_resp.status}")
                        return False

        except Exception as e:
            logger.warning(f"  Error updating: {e}")
            return False

    async def process_uncertain_books(self, uncertain_file: str = "books_needing_manual_review.json") -> None:
        """Process books from manual review queue"""
        if not os.path.exists(uncertain_file):
            logger.error(f"File not found: {uncertain_file}")
            return

        with open(uncertain_file, 'r') as f:
            uncertain_books = json.load(f)

        logger.info(f"Processing {len(uncertain_books)} uncertain books...")
        logger.info("Using audio transcripts as source of truth")
        logger.info("")

        for idx, book_info in enumerate(uncertain_books, 1):
            self.stats['books_processed'] += 1

            try:
                book_id = book_info.get('book_id')
                current_title = book_info.get('current_title', 'Unknown')
                audio_title = book_info.get('parsed_title', '')
                audio_author = book_info.get('parsed_author', '')
                transcript = book_info.get('transcript', '')

                if not audio_title or not audio_author:
                    logger.warning(f"[{idx}] Skipping: No audio data")
                    continue

                # Clean up extracted data
                clean_title = self.clean_parsed_title(audio_title)
                clean_author = self.clean_parsed_author(audio_author)

                logger.info(f"[{idx}/{len(uncertain_books)}] Correcting metadata")
                logger.info(f"  Current: '{current_title}'")
                logger.info(f"  Audio says: '{clean_title}' by {clean_author}")

                # Apply correction
                success = await self.update_book_metadata(book_id, clean_title, clean_author, transcript)

                if success:
                    self.stats['corrections'].append({
                        'book_id': book_id,
                        'old_title': current_title,
                        'new_title': clean_title,
                        'new_author': clean_author
                    })

                logger.info("")

            except Exception as e:
                logger.warning(f"[{idx}] Error: {e}")

    async def run(self):
        """Main workflow"""
        logger.info("=" * 80)
        logger.info("DIRECT AUDIO-BASED METADATA CORRECTOR")
        logger.info("=" * 80)
        logger.info("Audio transcripts are the source of truth")
        logger.info("")

        await self.process_uncertain_books()

        logger.info("=" * 80)
        logger.info("CORRECTION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Books processed:       {self.stats['books_processed']}")
        logger.info(f"Books corrected:       {self.stats['books_corrected']}")
        logger.info("")

        if self.stats['corrections']:
            logger.info(f"Summary of corrections:")
            for correction in self.stats['corrections']:
                logger.info(f"  - {correction['old_title']}")
                logger.info(f"    -> {correction['new_title']} by {correction['new_author']}")


async def main():
    if not ABS_TOKEN:
        logger.error("ERROR: ABS_TOKEN not found in environment!")
        return 1

    try:
        async with DirectAudioCorrector(ABS_API_URL, ABS_TOKEN) as corrector:
            await corrector.run()
            return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
