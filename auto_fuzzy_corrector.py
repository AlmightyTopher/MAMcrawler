#!/usr/bin/env python3
"""
Automatic Fuzzy Logic Metadata Corrector

Uses fuzzy matching on audio-extracted data:
- If fuzzy logic says it's a match, apply it
- Don't wait for perfect confidence - if the match is reasonable, correct it
- This mirrors how humans would use search/fuzzy matching
"""

import asyncio
import aiohttp
import logging
import json
import os
from typing import Dict, Optional, Tuple
from difflib import SequenceMatcher
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('auto_fuzzy_correction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

ABS_URL = os.getenv('ABS_URL', 'http://localhost:13378').rstrip('/')
ABS_TOKEN = os.getenv('ABS_TOKEN')
ABS_API_URL = f"{ABS_URL}/api"


class FuzzyMatcher:
    """Standard fuzzy matching for book metadata"""

    @staticmethod
    def string_similarity(a: str, b: str) -> float:
        """Calculate similarity between two strings (0-1)"""
        if not a or not b:
            return 0.0
        a = a.lower().strip()
        b = b.lower().strip()
        return SequenceMatcher(None, a, b).ratio()

    @staticmethod
    def token_overlap_score(text1: str, text2: str) -> float:
        """Calculate what % of tokens match between two texts"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        overlap = len(words1 & words2)
        total = len(words1 | words2)
        return overlap / total if total > 0 else 0.0

    @staticmethod
    def is_fuzzy_match(text1: str, text2: str, threshold: float = 0.70) -> bool:
        """
        Determine if two texts are a fuzzy match
        Uses both string similarity and token overlap
        """
        similarity = FuzzyMatcher.string_similarity(text1, text2)
        token_overlap = FuzzyMatcher.token_overlap_score(text1, text2)

        # Either strong string similarity OR good token overlap = match
        if similarity >= 0.80 or token_overlap >= threshold:
            return True

        return False


class AutomaticFuzzyCorrector:
    """Apply corrections when fuzzy matching confirms them"""

    def __init__(self, api_url: str = ABS_API_URL, api_key: Optional[str] = None):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.session = None
        self.stats = {
            'books_processed': 0,
            'books_corrected': 0,
            'corrections_made': []
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

    def should_correct_title(self, current_title: str, audio_title: str) -> Tuple[bool, str]:
        """
        Determine if title should be corrected based on fuzzy matching
        Returns: (should_correct, reason)
        """
        # Clean up audio title (remove publisher names, etc)
        audio_clean = self._clean_title(audio_title)
        current_clean = self._clean_title(current_title)

        # Check fuzzy match
        if FuzzyMatcher.is_fuzzy_match(current_clean, audio_clean, threshold=0.65):
            return (True, "Fuzzy match confirmed between current and audio")

        # Check if audio is a subset of current (common case)
        if len(audio_clean) > 3 and audio_clean in current_clean:
            return (True, "Audio title is core part of current title")

        # Check if cleaning audio reveals the title
        if FuzzyMatcher.is_fuzzy_match(current_clean, audio_clean, threshold=0.70):
            return (True, "Strong fuzzy match after normalization")

        return (False, "No fuzzy match detected")

    def should_correct_author(self, current_author: str, audio_author: str) -> Tuple[bool, str]:
        """
        Determine if author should be corrected
        More permissive than title since author names vary more
        """
        if not current_author or not audio_author:
            return (False, "Missing author data")

        # Exact match
        if current_author.lower().strip() == audio_author.lower().strip():
            return (True, "Exact author match")

        # First/last name appears in both
        current_words = set(current_author.lower().split())
        audio_words = set(audio_author.lower().split())
        overlap = current_words & audio_words

        if len(overlap) > 0 and len(overlap) >= max(len(current_words), len(audio_words)) * 0.5:
            return (True, f"Author name overlap: {overlap}")

        # String similarity
        similarity = FuzzyMatcher.string_similarity(current_author, audio_author)
        if similarity >= 0.75:
            return (True, f"Author similarity: {similarity:.2%}")

        return (False, f"Author mismatch: {current_author} vs {audio_author}")

    @staticmethod
    def _clean_title(title: str) -> str:
        """Clean up title for comparison"""
        # Remove common publisher/format indicators
        title = title.lower().strip()

        # Remove file formats
        for ext in ['.mp3', '.m4b', '.m4a', '(mp3)', '[mp3]', 'mp3']:
            title = title.replace(ext, '').strip()

        # Remove author attribution patterns
        patterns = [
            r'^[^-]*-\s*',  # "Author - Title" pattern
            r'^\([0-9]{4}\)\s*',  # "(2022) Title" pattern
            r'^(audible|recorded books|podium|tantor|hachette|blackstone)[:\s]*',  # Publisher names
        ]

        import re
        for pattern in patterns:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE).strip()

        return title

    async def update_book_metadata(self, book_id: str, new_title: str = None, new_author: str = None) -> bool:
        """Update book metadata via Audiobookshelf API"""
        try:
            async with self.session.get(f"{self.api_url}/items/{book_id}") as resp:
                if resp.status != 200:
                    logger.warning(f"Could not fetch book {book_id}")
                    return False

                book_data = await resp.json()
                media = book_data.get('media', {})
                metadata = media.get('metadata', {})

                # Update fields
                if new_title:
                    old_title = metadata.get('title')
                    metadata['title'] = new_title
                    logger.info(f"  Title: '{old_title}' -> '{new_title}'")

                if new_author:
                    old_author = metadata.get('authorName')
                    metadata['authorName'] = new_author
                    logger.info(f"  Author: '{old_author}' -> '{new_author}'")

                payload = {"metadata": metadata}

                async with self.session.patch(
                    f"{self.api_url}/items/{book_id}/media",
                    json=payload
                ) as update_resp:
                    if update_resp.status in [200, 204]:
                        logger.info(f"[OK] Updated in Audiobookshelf")
                        self.stats['books_corrected'] += 1
                        return True
                    else:
                        logger.warning(f"Failed to update {book_id}: {update_resp.status}")
                        return False

        except Exception as e:
            logger.warning(f"Error updating book {book_id}: {e}")
            return False

    async def process_uncertain_books(self, uncertain_file: str = "books_needing_manual_review.json") -> None:
        """Process books from manual review queue"""
        if not os.path.exists(uncertain_file):
            logger.error(f"File not found: {uncertain_file}")
            return

        with open(uncertain_file, 'r') as f:
            uncertain_books = json.load(f)

        logger.info(f"Processing {len(uncertain_books)} uncertain books with auto-fuzzy correction...")
        logger.info("")

        for book_info in uncertain_books:
            self.stats['books_processed'] += 1

            try:
                book_id = book_info.get('book_id')
                current_title = book_info.get('current_title', 'Unknown')
                audio_title = book_info.get('parsed_title', '')
                audio_author = book_info.get('parsed_author', '')

                if not audio_title or not audio_author:
                    logger.warning(f"Skipping {current_title}: No audio data")
                    continue

                logger.info(f"Book: {current_title}")
                logger.info(f"  Audio: '{audio_title}' by {audio_author}")

                # Check title
                should_correct_title, title_reason = self.should_correct_title(current_title, audio_title)
                logger.info(f"  Title match: {title_reason}")

                # Check author
                should_correct_author, author_reason = self.should_correct_author('Unknown', audio_author)
                logger.info(f"  Author match: {author_reason}")

                # Apply corrections if fuzzy match says yes
                if should_correct_title or should_correct_author:
                    logger.info(f"  --> CORRECTING (fuzzy match confirmed)")
                    await self.update_book_metadata(
                        book_id,
                        new_title=audio_title if should_correct_title else None,
                        new_author=audio_author if should_correct_author else None
                    )
                    self.stats['corrections_made'].append({
                        'book_id': book_id,
                        'title': audio_title,
                        'author': audio_author
                    })
                else:
                    logger.info(f"  --> NO CORRECTION (fuzzy match failed)")

                logger.info("")

            except Exception as e:
                logger.warning(f"Error processing book: {e}")

    async def run(self):
        """Main workflow"""
        logger.info("=" * 80)
        logger.info("AUTO-FUZZY METADATA CORRECTOR")
        logger.info("=" * 80)
        logger.info("Uses fuzzy matching to auto-correct metadata from audio data")
        logger.info("")

        await self.process_uncertain_books()

        logger.info("=" * 80)
        logger.info("CORRECTION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Books processed:       {self.stats['books_processed']}")
        logger.info(f"Books corrected:       {self.stats['books_corrected']}")
        logger.info("")

        if self.stats['corrections_made']:
            logger.info(f"Applied {len(self.stats['corrections_made'])} corrections:")
            for correction in self.stats['corrections_made']:
                logger.info(f"  - {correction['title']} by {correction['author']}")


async def main():
    if not ABS_TOKEN:
        logger.error("ERROR: ABS_TOKEN not found in environment!")
        return 1

    try:
        async with AutomaticFuzzyCorrector(ABS_API_URL, ABS_TOKEN) as corrector:
            await corrector.run()
            return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
