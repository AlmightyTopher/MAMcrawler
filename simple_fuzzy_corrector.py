#!/usr/bin/env python3
"""
Simple Fuzzy Logic Book Metadata Corrector

Uses standard fuzzy matching to correct audiobook metadata based on:
1. Audio transcriptions we already extracted
2. Reasonable variations and common mistakes
3. Manual fallback when confidence is low

This is a practical, working approach using proven fuzzy matching techniques.
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
        logging.FileHandler('fuzzy_correction.log'),
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
        """
        Calculate similarity between two strings (0-1, where 1 = identical)
        Uses difflib.SequenceMatcher ratio
        """
        if not a or not b:
            return 0.0
        a = a.lower().strip()
        b = b.lower().strip()
        return SequenceMatcher(None, a, b).ratio()

    @staticmethod
    def contains_all_words(text: str, words: list) -> bool:
        """Check if text contains all given words (in any order)"""
        text_lower = text.lower()
        return all(word.lower() in text_lower for word in words)

    @staticmethod
    def title_match_score(current: str, audio: str, threshold: float = 0.75) -> Tuple[float, str]:
        """
        Score how well the audio title matches current title
        Returns: (score: 0-1, reason: why it matched or didn't)
        """
        similarity = FuzzyMatcher.string_similarity(current, audio)

        # Exact match
        if similarity >= 0.95:
            return (1.0, "Exact or near-exact match")

        # Very close (typo range)
        if similarity >= 0.85:
            return (0.95, "Very close match (likely typo)")

        # Good match (word overlap)
        if similarity >= 0.75:
            return (0.85, "Good word overlap")

        # Check if audio is substring or vice versa
        if audio.lower() in current.lower() or current.lower() in audio.lower():
            return (0.80, "One is substring of other")

        # Check word-for-word overlap
        current_words = set(current.lower().split())
        audio_words = set(audio.lower().split())
        overlap = len(current_words & audio_words)
        total = len(current_words | audio_words)

        if total > 0:
            word_overlap = overlap / total
            if word_overlap >= 0.7:
                return (0.75, f"Word overlap: {overlap}/{total} words match")
            elif word_overlap >= 0.5:
                return (0.60, f"Partial word overlap: {overlap}/{total}")

        return (0.0, f"No match (similarity: {similarity:.2f})")

    @staticmethod
    def author_match_score(current: str, audio: str, known_pen_names: Dict[str, list] = None) -> Tuple[float, str]:
        """
        Score author match, accounting for pen names and variations
        known_pen_names: {"Real Name": ["Pen Name 1", "Pen Name 2"]}
        """
        if known_pen_names is None:
            known_pen_names = {
                "Nathaniel Evans": ["Neven Iliev"],  # Known pen name
                "Craig Alanson": ["Craig Alanson", "C. Alanson"],
                "Eric Ugland": ["Eric Ugland", "E. Ugland"],
            }

        current_lower = current.lower().strip()
        audio_lower = audio.lower().strip()

        # Check for direct match
        if current_lower == audio_lower:
            return (1.0, "Exact author match")

        # Check for substring match (handles "First Last" vs "Last, First")
        if current_lower in audio_lower or audio_lower in current_lower:
            return (0.95, "Author names overlap significantly")

        # Check for known pen names
        for real_name, pen_names in known_pen_names.items():
            real_lower = real_name.lower()
            # If current is real name and audio is a pen name (or vice versa)
            if (current_lower == real_lower and any(p.lower() == audio_lower for p in pen_names)):
                return (0.90, f"Audio uses pen name '{audio}' for author '{current}'")
            if (any(p.lower() == current_lower for p in pen_names) and audio_lower == real_lower):
                return (0.90, f"Current uses pen name, audio has real name")

        # Check word overlap
        current_words = set(current_lower.split())
        audio_words = set(audio_lower.split())
        if current_words & audio_words:
            return (0.80, "Partial name overlap")

        # String similarity
        similarity = SequenceMatcher(None, current_lower, audio_lower).ratio()
        if similarity >= 0.75:
            return (0.70, f"Name similarity: {similarity:.2f}")

        return (0.0, "Author names don't match")


class MetadataCorrector:
    """Apply corrections based on audio + fuzzy matching"""

    def __init__(self, api_url: str = ABS_API_URL, api_key: Optional[str] = None):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.session = None
        self.stats = {
            'books_processed': 0,
            'books_updated': 0,
            'books_flagged_manual': 0,
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

    def analyze_correction(self, current_title: str, audio_title: str, current_author: str, audio_author: str) -> Dict:
        """
        Analyze if correction should be applied based on fuzzy matching
        Returns: {should_correct, confidence, reason, new_metadata}
        """
        title_score, title_reason = FuzzyMatcher.title_match_score(current_title, audio_title)
        author_score, author_reason = FuzzyMatcher.author_match_score(current_author, audio_author)

        # Combined confidence (weighted)
        combined_confidence = (title_score * 0.7) + (author_score * 0.3)

        # Decision logic
        should_correct = combined_confidence >= 0.80  # Practical threshold

        return {
            'should_correct': should_correct,
            'confidence': combined_confidence,
            'title_score': title_score,
            'title_reason': title_reason,
            'author_score': author_score,
            'author_reason': author_reason,
            'new_title': audio_title if should_correct else None,
            'new_author': audio_author if should_correct else None,
        }

    async def update_book_metadata(self, book_id: str, new_title: str, new_author: str) -> bool:
        """Update book metadata via Audiobookshelf API"""
        try:
            async with self.session.get(f"{self.api_url}/items/{book_id}") as resp:
                if resp.status != 200:
                    logger.warning(f"Could not fetch book {book_id}")
                    return False

                book_data = await resp.json()
                media = book_data.get('media', {})
                metadata = media.get('metadata', {})

                # Update
                metadata['title'] = new_title
                metadata['authorName'] = new_author

                payload = {"metadata": metadata}

                async with self.session.patch(
                    f"{self.api_url}/items/{book_id}/media",
                    json=payload
                ) as update_resp:
                    if update_resp.status in [200, 204]:
                        logger.info(f"✓ Updated: '{new_title}' by {new_author}")
                        self.stats['books_updated'] += 1
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

        logger.info(f"Processing {len(uncertain_books)} books from manual review queue...")
        logger.info("")

        manual_review = []

        for book_info in uncertain_books:
            self.stats['books_processed'] += 1

            try:
                book_id = book_info.get('book_id')
                current_title = book_info.get('current_title', 'Unknown')
                audio_title = book_info.get('parsed_title')
                audio_author = book_info.get('parsed_author')
                transcript = book_info.get('transcript', '')

                if not audio_title or not audio_author:
                    logger.warning(f"Skipping {current_title}: No audio extraction data")
                    manual_review.append(book_info)
                    continue

                # Analyze correction
                analysis = self.analyze_correction(current_title, audio_title, 'Unknown', audio_author)

                logger.info(f"Book: {current_title}")
                logger.info(f"  Audio says: '{audio_title}' by {audio_author}")
                logger.info(f"  Title match: {analysis['title_reason']} ({analysis['title_score']:.2%})")
                logger.info(f"  Author match: {analysis['author_reason']} ({analysis['author_score']:.2%})")
                logger.info(f"  Overall confidence: {analysis['confidence']:.2%}")

                if analysis['should_correct']:
                    logger.info(f"  → CORRECTING to: '{audio_title}'")
                    await self.update_book_metadata(book_id, audio_title, audio_author)
                    logger.info("")
                else:
                    logger.info(f"  → FLAGGING for manual review (confidence too low)")
                    manual_review.append({
                        **book_info,
                        'analysis': analysis,
                        'recommendation': f"Consider '{audio_title}' based on audio; verify with user"
                    })
                    logger.info("")
                    self.stats['books_flagged_manual'] += 1

            except Exception as e:
                logger.warning(f"Error processing book: {e}")

        # Save manual review list
        if manual_review:
            with open('manual_review_required.json', 'w') as f:
                json.dump(manual_review, f, indent=2)
            logger.info(f"Flagged {len(manual_review)} books for manual review")
            logger.info(f"See: manual_review_required.json")

    async def run(self):
        """Main workflow"""
        logger.info("=" * 80)
        logger.info("FUZZY LOGIC METADATA CORRECTOR")
        logger.info("=" * 80)
        logger.info("")

        await self.process_uncertain_books()

        logger.info("")
        logger.info("=" * 80)
        logger.info("CORRECTION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Books processed:       {self.stats['books_processed']}")
        logger.info(f"Books updated:         {self.stats['books_updated']}")
        logger.info(f"Books flagged manual:  {self.stats['books_flagged_manual']}")
        logger.info("")


async def main():
    if not ABS_TOKEN:
        logger.error("ERROR: ABS_TOKEN not found in environment!")
        return 1

    try:
        async with MetadataCorrector(ABS_API_URL, ABS_TOKEN) as corrector:
            await corrector.run()
            return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
