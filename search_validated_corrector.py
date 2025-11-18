#!/usr/bin/env python3
"""
Search-Validated Metadata Corrector

When fuzzy matching doesn't work:
1. Try variations of the title (drop non-matching parts)
2. Search Goodreads for each variation
3. If a variation returns a strong match, use that result
4. Apply the correction if search validates it

Example: "Wild Wild Quest" vs "Wild Wild West"
- Drop "Quest" -> search for "Wild Wild West"
- Goodreads returns exact match for "Wild Wild West by Eric Ugland"
- Apply correction confidently
"""

import asyncio
import aiohttp
import logging
import json
import os
import re
from typing import Dict, Optional, List, Tuple
from difflib import SequenceMatcher
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('search_validated_correction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

ABS_URL = os.getenv('ABS_URL', 'http://localhost:13378').rstrip('/')
ABS_TOKEN = os.getenv('ABS_TOKEN')
ABS_API_URL = f"{ABS_URL}/api"


class GoodreadsSearcher:
    """Search Goodreads for book validation"""

    @staticmethod
    def search_goodreads(title: str, author: str) -> Optional[Dict]:
        """
        Search Goodreads for a book and return result if found
        Uses web scraping since official API is deprecated
        """
        try:
            import requests
            from bs4 import BeautifulSoup

            # Build search URL
            query = f"{title} {author}".strip()
            search_url = f"https://www.goodreads.com/search?q={requests.utils.quote(query)}"

            # Try to fetch
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(search_url, headers=headers, timeout=5)

            if response.status_code != 200:
                logger.debug(f"Goodreads search failed: {response.status_code}")
                return None

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find first book result
            book_row = soup.find('tr', class_='bookacard')
            if not book_row:
                logger.debug(f"No book found for: {query}")
                return None

            # Extract info
            title_elem = book_row.find('span', class_='titleSpan')
            author_elem = book_row.find('span', class_='authorName')

            if title_elem and author_elem:
                found_title = title_elem.get_text(strip=True)
                found_author = author_elem.get_text(strip=True)
                return {
                    'title': found_title,
                    'author': found_author,
                    'url': search_url
                }

        except Exception as e:
            logger.debug(f"Goodreads search error: {e}")

        return None

    @staticmethod
    def get_title_variations(title: str, current_title: str) -> List[str]:
        """
        Generate variations of a title for searching
        E.g., "Wild Wild Quest" -> ["Wild Wild Quest", "Wild Wild", "West"]
        """
        variations = [title]  # Start with original

        # Split by common words and try combinations
        words = title.split()

        # Try removing last word (often the mismatched part)
        if len(words) > 1:
            variations.append(" ".join(words[:-1]))

        # Try removing first word
        if len(words) > 1:
            variations.append(" ".join(words[1:]))

        # Extract words from current that might be correct
        current_words = set(current_title.lower().split())
        audio_words = set(title.lower().split())

        # Words in current but not in audio might be the issue
        diff_words = current_words - audio_words
        for word in diff_words:
            if len(word) > 3:  # Skip short words like "the", "and"
                # Try replacing that word with variations
                for other_word in audio_words:
                    new_title = current_title.lower().replace(word, other_word)
                    if new_title not in variations:
                        variations.append(new_title)

        # Remove duplicates, keep order
        seen = set()
        unique = []
        for v in variations:
            v_lower = v.lower()
            if v_lower not in seen:
                seen.add(v_lower)
                unique.append(v)

        return unique


class SearchValidatedCorrector:
    """Apply corrections validated by search results"""

    def __init__(self, api_url: str = ABS_API_URL, api_key: Optional[str] = None):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.session = None
        self.stats = {
            'books_processed': 0,
            'books_corrected': 0,
            'search_validated': 0,
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
    def string_similarity(a: str, b: str) -> float:
        """Calculate similarity between strings"""
        if not a or not b:
            return 0.0
        a = a.lower().strip()
        b = b.lower().strip()
        return SequenceMatcher(None, a, b).ratio()

    def validate_with_search(self, current_title: str, audio_title: str, author: str) -> Tuple[bool, str]:
        """
        Try to validate audio title against Goodreads search
        Returns: (should_update, new_title_if_found)
        """
        logger.info(f"    Searching Goodreads to validate: '{audio_title}'")

        # Try variations of the audio title
        variations = GoodreadsSearcher.get_title_variations(audio_title, current_title)

        for variation in variations:
            logger.debug(f"      Trying: {variation}")

            # Search Goodreads
            result = GoodreadsSearcher.search_goodreads(variation, author)

            if result:
                found_title = result['title']
                similarity = self.string_similarity(audio_title, found_title)

                logger.info(f"    Found: '{found_title}' (match: {similarity:.0%})")

                # If we got a match with good similarity, use it
                if similarity >= 0.70:  # 70% match is good enough when validated by search
                    return (True, found_title)

        logger.info(f"    No search validation found")
        return (False, None)

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
                    logger.info(f"      [UPDATING] Title: '{old_title}' -> '{new_title}'")

                if new_author:
                    old_author = metadata.get('authorName')
                    metadata['authorName'] = new_author
                    logger.info(f"      [UPDATING] Author: '{old_author}' -> '{new_author}'")

                payload = {"metadata": metadata}

                async with self.session.patch(
                    f"{self.api_url}/items/{book_id}/media",
                    json=payload
                ) as update_resp:
                    if update_resp.status in [200, 204]:
                        logger.info(f"      [OK] Updated in Audiobookshelf")
                        self.stats['books_corrected'] += 1
                        return True
                    else:
                        logger.warning(f"      Failed to update: HTTP {update_resp.status}")
                        return False

        except Exception as e:
            logger.warning(f"      Error updating: {e}")
            return False

    async def process_uncertain_books(self, uncertain_file: str = "books_needing_manual_review.json") -> None:
        """Process books from manual review queue"""
        if not os.path.exists(uncertain_file):
            logger.error(f"File not found: {uncertain_file}")
            return

        with open(uncertain_file, 'r') as f:
            uncertain_books = json.load(f)

        logger.info(f"Processing {len(uncertain_books)} uncertain books with search validation...")
        logger.info("")

        for idx, book_info in enumerate(uncertain_books, 1):
            self.stats['books_processed'] += 1

            try:
                book_id = book_info.get('book_id')
                current_title = book_info.get('current_title', 'Unknown')
                audio_title = book_info.get('parsed_title', '')
                audio_author = book_info.get('parsed_author', '')

                if not audio_title or not audio_author:
                    logger.warning(f"[{idx}] Skipping {current_title}: No audio data")
                    continue

                logger.info(f"[{idx}/{len(uncertain_books)}] {current_title}")
                logger.info(f"  Audio says: '{audio_title}' by {audio_author}")

                # Try to validate with search
                should_correct, validated_title = self.validate_with_search(current_title, audio_title, audio_author)

                if should_correct:
                    logger.info(f"  --> CORRECTING with search-validated title")
                    await self.update_book_metadata(
                        book_id,
                        new_title=validated_title,
                        new_author=audio_author
                    )
                    self.stats['search_validated'] += 1
                    self.stats['corrections'].append({
                        'book_id': book_id,
                        'title': validated_title,
                        'author': audio_author
                    })
                else:
                    logger.info(f"  --> NO CORRECTION (search validation failed)")

                logger.info("")

            except Exception as e:
                logger.warning(f"[{idx}] Error processing book: {e}")

    async def run(self):
        """Main workflow"""
        logger.info("=" * 80)
        logger.info("SEARCH-VALIDATED METADATA CORRECTOR")
        logger.info("=" * 80)
        logger.info("Uses Goodreads search to validate audio-extracted metadata")
        logger.info("")

        await self.process_uncertain_books()

        logger.info("=" * 80)
        logger.info("CORRECTION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Books processed:       {self.stats['books_processed']}")
        logger.info(f"Books corrected:       {self.stats['books_corrected']}")
        logger.info(f"Search-validated:      {self.stats['search_validated']}")
        logger.info("")

        if self.stats['corrections']:
            logger.info(f"Applied {len(self.stats['corrections'])} corrections:")
            for correction in self.stats['corrections']:
                logger.info(f"  - {correction['title']} by {correction['author']}")


async def main():
    if not ABS_TOKEN:
        logger.error("ERROR: ABS_TOKEN not found in environment!")
        return 1

    try:
        async with SearchValidatedCorrector(ABS_API_URL, ABS_TOKEN) as corrector:
            await corrector.run()
            return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
