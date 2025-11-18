#!/usr/bin/env python3
"""
Update Books from Audio Verification

Applies corrected metadata to books after manual audio verification.

Usage:
    python update_from_verification.py

    Then enter book details when prompted, or create a verification_data.json file with:
    [
      {
        "book_id": "6288ddbe-...",
        "title": "Correct Title",
        "author": "Correct Author",
        "series_name": "Series Name",
        "sequence": "12"
      }
    ]
"""

import asyncio
import aiohttp
import logging
import os
import json
import sys
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('update_from_verification.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

ABS_URL = os.getenv('ABS_URL', 'http://localhost:13378').rstrip('/')
ABS_TOKEN = os.getenv('ABS_TOKEN')
ABS_API_URL = f"{ABS_URL}/api"


class VerificationUpdater:
    """Updates book metadata based on verification data"""

    def __init__(self, api_url: str = ABS_API_URL, api_key: Optional[str] = None):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.session = None
        self.stats = {
            'books_processed': 0,
            'books_updated': 0,
            'updates': {
                'title': 0,
                'author': 0,
                'series': 0
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

    async def update_book(self, book_id: str, verified_metadata: Dict) -> bool:
        """Update a single book with verified metadata"""
        try:
            # Get current book data
            async with self.session.get(f"{self.api_url}/items/{book_id}") as resp:
                if resp.status != 200:
                    logger.warning(f"Could not fetch book {book_id}")
                    return False

                book_data = await resp.json()
                media = book_data.get('media', {})
                metadata = media.get('metadata', {})

                # Apply updates
                old_title = metadata.get('title')
                if verified_metadata.get('title'):
                    metadata['title'] = verified_metadata['title']
                    if verified_metadata['title'] != old_title:
                        self.stats['updates']['title'] += 1
                        logger.info(f"  Title: {old_title} → {verified_metadata['title']}")

                if verified_metadata.get('author'):
                    old_author = metadata.get('authorName')
                    if verified_metadata['author'] != old_author:
                        metadata['authorName'] = verified_metadata['author']
                        self.stats['updates']['author'] += 1
                        logger.info(f"  Author: {old_author} → {verified_metadata['author']}")

                if verified_metadata.get('series_name'):
                    series_id = verified_metadata['series_name'].lower().replace(' ', '-')[:16]
                    old_series = metadata.get('series', [])
                    old_series_name = old_series[0].get('name') if old_series else None

                    new_series = {
                        'id': series_id,
                        'name': verified_metadata['series_name'],
                        'sequence': verified_metadata.get('sequence', '')
                    }
                    metadata['series'] = [new_series]

                    if verified_metadata['series_name'] != old_series_name:
                        self.stats['updates']['series'] += 1
                        seq = verified_metadata.get('sequence', '?')
                        logger.info(f"  Series: {old_series_name} → {verified_metadata['series_name']} #{seq}")

                # Prepare and send update
                payload = {"metadata": metadata}

                async with self.session.patch(
                    f"{self.api_url}/items/{book_id}/media",
                    json=payload
                ) as update_resp:
                    if update_resp.status in [200, 204]:
                        self.stats['books_updated'] += 1
                        return True
                    else:
                        logger.warning(f"Failed to update {book_id}: {update_resp.status}")
                        return False

        except Exception as e:
            logger.warning(f"Error updating book {book_id}: {e}")
            self.stats['errors'].append(str(e))

        return False

    async def process_verifications(self, verifications: List[Dict]) -> None:
        """Process list of verified metadata"""
        logger.info(f"Processing {len(verifications)} verified books...")
        logger.info("")

        for idx, verification in enumerate(verifications, 1):
            try:
                self.stats['books_processed'] += 1
                book_id = verification.get('book_id')
                title = verification.get('title', 'Unknown')

                logger.info(f"[{idx}/{len(verifications)}] Updating: {title}")

                await self.update_book(book_id, verification)

            except Exception as e:
                logger.warning(f"Error processing verification: {e}")
                self.stats['errors'].append(str(e))

    async def interactive_verification(self) -> None:
        """Interactive mode for entering verified metadata"""
        logger.info("Interactive Verification Mode")
        logger.info("(Leave fields blank to skip updating that field)")
        logger.info("")

        verifications = []

        while True:
            print("\n" + "=" * 60)
            book_id = input("Book ID (or 'done' to finish): ").strip()

            if book_id.lower() == 'done':
                break

            if not book_id:
                print("Book ID cannot be empty")
                continue

            metadata = {
                'book_id': book_id,
                'title': input("Title (leave blank to skip): ").strip() or None,
                'author': input("Author (leave blank to skip): ").strip() or None,
                'series_name': input("Series Name (leave blank to skip): ").strip() or None,
                'sequence': input("Series Number (leave blank to skip): ").strip() or None,
            }

            # Remove None values
            metadata = {k: v for k, v in metadata.items() if v is not None}
            verifications.append(metadata)

            print(f"\n✓ Added: {metadata}")

        if verifications:
            await self.process_verifications(verifications)

    async def load_and_process_file(self, filepath: str) -> None:
        """Load verification data from JSON file and process"""
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return

        with open(filepath, 'r') as f:
            verifications = json.load(f)

        if not isinstance(verifications, list):
            verifications = [verifications]

        await self.process_verifications(verifications)

    async def run(self):
        """Main workflow"""
        logger.info("=" * 80)
        logger.info("UPDATE FROM AUDIO VERIFICATION")
        logger.info("=" * 80)
        logger.info("")

        # Check for verification file
        verification_file = "verification_data.json"

        if os.path.exists(verification_file):
            logger.info(f"Found verification file: {verification_file}")
            await self.load_and_process_file(verification_file)
        else:
            logger.info("No verification_data.json found")
            logger.info("Starting interactive mode...")
            logger.info("")
            await self.interactive_verification()

        # Summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("UPDATE COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Books processed:      {self.stats['books_processed']}")
        logger.info(f"Books updated:        {self.stats['books_updated']}")
        logger.info("")
        logger.info("Updates made:")
        logger.info(f"  - Titles updated:     {self.stats['updates']['title']}")
        logger.info(f"  - Authors updated:    {self.stats['updates']['author']}")
        logger.info(f"  - Series updated:     {self.stats['updates']['series']}")

        if self.stats['errors']:
            logger.info(f"Errors:               {len(self.stats['errors'])}")
            for error in self.stats['errors'][:5]:
                logger.info(f"  - {error}")

        logger.info("")
        logger.info("Done!")
        logger.info("")

        return True


async def main():
    if not ABS_TOKEN:
        logger.error("ERROR: ABS_TOKEN not found in environment!")
        return 1

    try:
        async with VerificationUpdater(ABS_API_URL, ABS_TOKEN) as updater:
            success = await updater.run()
            return 0 if success else 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
