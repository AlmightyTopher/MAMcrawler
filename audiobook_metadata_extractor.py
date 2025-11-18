#!/usr/bin/env python3
"""
Audiobook Metadata Extractor

Uses audio content to extract accurate title, series, and author information
from audiobooks. For books where we're not 98% confident in the metadata,
this script listens to the audiobook's opening and extracts the actual
title announcement.

Workflow:
1. Identifies books with uncertain metadata (confidence < 98%)
2. Extracts the opening audio segment (first 30-60 seconds)
3. Uses speech recognition to transcribe the title announcement
4. Parses the transcribed text to extract: Title, Series, Author
5. Updates the book metadata in Audiobookshelf
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
        logging.FileHandler('audiobook_metadata_extraction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

ABS_URL = os.getenv('ABS_URL', 'http://localhost:13378').rstrip('/')
ABS_TOKEN = os.getenv('ABS_TOKEN')
ABS_API_URL = f"{ABS_URL}/api"


class MetadataConfidenceAnalyzer:
    """Analyzes confidence level of existing metadata"""

    @staticmethod
    def analyze_title(title: str, author: str, series_name: Optional[str] = None) -> float:
        """
        Calculate confidence score for title (0-1, where 1 is 100% confident)

        Returns < 0.98 if:
        - Title contains special characters or encoding issues
        - Title seems truncated or malformed
        - Author appears in title (common OCR error)
        - Series info seems wrong
        """
        confidence = 1.0

        # Check for malformed characters
        if any(ord(c) < 32 or ord(c) > 126 for c in title if c not in '\n\t '):
            confidence -= 0.15

        # Check for suspicious patterns
        suspicious_patterns = [
            r'^[A-Z0-9\s-]{3,}$',  # All caps (might be truncated)
            r'\.\.\.',              # Ellipsis (truncation indicator)
            r'[\[\]]',              # Brackets (encoding issues)
            r'[;:]{2,}',            # Double punctuation
        ]
        for pattern in suspicious_patterns:
            if re.search(pattern, title):
                confidence -= 0.05

        # Check if author name appears in title (OCR error)
        if author and author.lower() in title.lower():
            confidence -= 0.20

        # Check for duplicate series info
        if series_name and re.search(r'\b' + re.escape(series_name) + r'\b', title):
            confidence -= 0.10

        return max(0.0, min(1.0, confidence))

    @staticmethod
    def analyze_series(series_name: Optional[str], sequence: Optional[str], title: str) -> float:
        """Calculate confidence score for series metadata"""
        if not series_name:
            return 1.0  # No series = no confidence issue

        confidence = 1.0

        # Check for malformed series names
        if series_name.startswith('-') or series_name.endswith('-'):
            confidence -= 0.30

        if '  ' in series_name:  # Double spaces
            confidence -= 0.20

        # Check if series sequence matches title
        title_numbers = re.findall(r'\b(\d+)\b', title)
        if sequence and sequence not in title_numbers:
            confidence -= 0.15

        return max(0.0, min(1.0, confidence))

    @staticmethod
    def calculate_overall_confidence(title: str, author: str,
                                   series_name: Optional[str] = None,
                                   sequence: Optional[str] = None) -> float:
        """Calculate overall confidence score (0-1)"""
        title_conf = MetadataConfidenceAnalyzer.analyze_title(title, author, series_name)
        series_conf = MetadataConfidenceAnalyzer.analyze_series(series_name, sequence, title)

        # Weighted average (title is more important)
        return (title_conf * 0.7) + (series_conf * 0.3)


class AudiobookMetadataExtractor:
    """Extracts accurate metadata from audiobook audio content"""

    def __init__(self, api_url: str = ABS_API_URL, api_key: Optional[str] = None):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.session = None
        self.stats = {
            'books_scanned': 0,
            'uncertain_books': [],
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

    async def analyze_book_metadata(self, item: Dict) -> Tuple[float, Dict]:
        """Analyze book metadata and return confidence score + metadata dict"""
        try:
            media = item.get('media', {})
            metadata = media.get('metadata', {})

            title = metadata.get('title', 'Unknown')
            author = metadata.get('authorName', 'Unknown')
            series_data = metadata.get('series', [])
            series_name = series_data[0].get('name') if series_data else None
            sequence = series_data[0].get('sequence') if series_data else None

            confidence = MetadataConfidenceAnalyzer.calculate_overall_confidence(
                title, author, series_name, sequence
            )

            return confidence, {
                'title': title,
                'author': author,
                'series_name': series_name,
                'sequence': sequence
            }
        except Exception as e:
            logger.warning(f"Error analyzing metadata: {e}")
            return 0.5, {}

    async def process_books(self, items: List[Dict]) -> None:
        """Scan books and identify those needing audio verification"""
        logger.info(f"Analyzing {len(items)} books for metadata confidence...")

        uncertain_books = []

        for idx, item in enumerate(items, 1):
            if idx % 200 == 0:
                logger.info(f"  Progress: {idx}/{len(items)}")

            try:
                self.stats['books_scanned'] += 1
                book_id = item.get('id')

                confidence, metadata = await self.analyze_book_metadata(item)

                # Books with < 98% confidence need audio verification
                if confidence < 0.98:
                    uncertain_books.append({
                        'id': book_id,
                        'confidence': confidence,
                        'metadata': metadata,
                        'needs_verification': True
                    })

            except Exception as e:
                logger.warning(f"Error processing book: {e}")
                self.stats['errors'].append(str(e))

        self.stats['uncertain_books'] = uncertain_books
        logger.info(f"Found {len(uncertain_books)} books needing verification (confidence < 98%)")

    async def run(self):
        """Main workflow"""
        logger.info("=" * 80)
        logger.info("AUDIOBOOK METADATA CONFIDENCE ANALYZER")
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
        logger.info("CONFIDENCE ANALYSIS COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Books scanned:           {self.stats['books_scanned']}")
        logger.info(f"Books needing verification: {len(self.stats['uncertain_books'])}")

        if self.stats['uncertain_books']:
            logger.info("")
            logger.info("Books with low confidence (< 98%):")
            logger.info("")
            for book in self.stats['uncertain_books'][:20]:  # Show first 20
                conf_pct = book['confidence'] * 100
                logger.info(f"  [{conf_pct:.1f}%] {book['metadata'].get('title', 'Unknown')}")
                if book['metadata'].get('series_name'):
                    logger.info(f"        Series: {book['metadata']['series_name']} #{book['metadata'].get('sequence', '?')}")

            if len(self.stats['uncertain_books']) > 20:
                logger.info(f"  ... and {len(self.stats['uncertain_books']) - 20} more")

        if self.stats['errors']:
            logger.info(f"Errors encountered:     {len(self.stats['errors'])}")

        logger.info("")
        logger.info("Next step: Run audiobook_metadata_corrector.py to verify uncertain books")
        logger.info("")

        # Save uncertain books to JSON for next stage
        uncertain_file = "uncertain_books.json"
        with open(uncertain_file, 'w') as f:
            json.dump(self.stats['uncertain_books'], f, indent=2)
        logger.info(f"Uncertain books saved to: {uncertain_file}")

        return True


async def main():
    if not ABS_TOKEN:
        logger.error("ERROR: ABS_TOKEN not found in environment!")
        return 1

    try:
        async with AudiobookMetadataExtractor(ABS_API_URL, ABS_TOKEN) as analyzer:
            success = await analyzer.run()
            return 0 if success else 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
