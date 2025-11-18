#!/usr/bin/env python3
"""
Verify All Uncertain Books

Main orchestration script that processes all books in uncertain_books.json
using audio-based verification.

Outputs:
- verification_results.json: Complete results for all books
- verification_summary.txt: Human-readable summary
- verification_audit.log: Detailed operation log
- books_needing_manual_review.json: Books that couldn't be auto-verified
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from dotenv import load_dotenv

from audiobook_audio_verifier import VerificationController, VerificationResult, to_dict

load_dotenv()

# Configure logging to both file and console
log_file = "verification_audit.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='w'),  # Overwrite each run
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
ABS_URL = os.getenv('ABS_URL', 'http://localhost:13378')
ABS_TOKEN = os.getenv('ABS_TOKEN')
UNCERTAIN_BOOKS_FILE = "uncertain_books.json"
RESULTS_FILE = "verification_results.json"
SUMMARY_FILE = "verification_summary.txt"
MANUAL_REVIEW_FILE = "books_needing_manual_review.json"


class VerificationOrchestrator:
    """Orchestrates verification of all uncertain books"""

    def __init__(self, abs_url: str, abs_token: str):
        self.abs_url = abs_url
        self.abs_token = abs_token
        self.stats = {
            'total_books': 0,
            'unique_books': 0,
            'audio_extracted': 0,
            'transcribed': 0,
            'verified_external': 0,
            'updated': 0,
            'manual_review': 0,
            'errors': 0
        }
        self.results: List[VerificationResult] = []

    def load_uncertain_books(self) -> List[Dict]:
        """Load and deduplicate uncertain books"""
        logger.info(f"Loading uncertain books from {UNCERTAIN_BOOKS_FILE}...")

        if not Path(UNCERTAIN_BOOKS_FILE).exists():
            logger.error(f"File not found: {UNCERTAIN_BOOKS_FILE}")
            return []

        with open(UNCERTAIN_BOOKS_FILE, 'r') as f:
            books = json.load(f)

        self.stats['total_books'] = len(books)

        # Deduplicate by book ID
        unique_books = {}
        for book in books:
            book_id = book.get('id')
            if book_id and book_id not in unique_books:
                unique_books[book_id] = book

        unique_list = list(unique_books.values())
        self.stats['unique_books'] = len(unique_list)

        logger.info(f"Loaded {len(books)} entries, {len(unique_list)} unique books")

        return unique_list

    async def verify_all_books(self, books: List[Dict]):
        """Verify all books sequentially"""
        logger.info(f"\n{'='*80}")
        logger.info(f"STARTING VERIFICATION OF {len(books)} BOOKS")
        logger.info(f"{'='*80}\n")

        async with VerificationController(self.abs_url, self.abs_token) as controller:
            for idx, book in enumerate(books, 1):
                book_id = book.get('id')
                current_title = book.get('metadata', {}).get('title', 'Unknown')

                logger.info(f"\n[{idx}/{len(books)}] Processing book...")

                try:
                    result = await controller.verify_book(book_id, current_title)
                    self.results.append(result)

                    # Update stats
                    if result.audio_extraction.success:
                        self.stats['audio_extracted'] += 1

                    if result.transcription.success:
                        self.stats['transcribed'] += 1

                    if result.external_verification:
                        self.stats['verified_external'] += 1

                    if result.updated:
                        self.stats['updated'] += 1

                    if result.final_confidence < 0.95:
                        self.stats['manual_review'] += 1

                except Exception as e:
                    logger.error(f"Error verifying book {book_id}: {e}", exc_info=True)
                    self.stats['errors'] += 1

                # Brief pause between books
                await asyncio.sleep(1)

        logger.info(f"\n{'='*80}")
        logger.info("VERIFICATION COMPLETE")
        logger.info(f"{'='*80}\n")

    def save_results(self):
        """Save all results to JSON file"""
        logger.info(f"Saving results to {RESULTS_FILE}...")

        # Convert results to dictionaries
        results_data = [to_dict(result) for result in self.results]

        with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved: {len(results_data)} books")

    def save_manual_review(self):
        """Save books needing manual review"""
        manual_review = []

        for result in self.results:
            if result.final_confidence < 0.95:
                manual_review.append({
                    'book_id': result.book_id,
                    'current_title': result.current_title,
                    'confidence': result.final_confidence,
                    'audio_extracted': result.audio_extraction.success,
                    'transcribed': result.transcription.success,
                    'transcript': result.parsed_metadata.raw_transcript if result.parsed_metadata else None,
                    'parsed_title': result.parsed_metadata.title if result.parsed_metadata else None,
                    'parsed_author': result.parsed_metadata.author if result.parsed_metadata else None,
                    'external_match': result.external_verification.title if result.external_verification else None,
                    'reason': self._get_review_reason(result)
                })

        if manual_review:
            with open(MANUAL_REVIEW_FILE, 'w', encoding='utf-8') as f:
                json.dump(manual_review, f, indent=2, ensure_ascii=False)

            logger.info(f"Books needing manual review: {len(manual_review)} (saved to {MANUAL_REVIEW_FILE})")

    def _get_review_reason(self, result: VerificationResult) -> str:
        """Determine why a book needs manual review"""
        if not result.audio_extraction.success:
            return f"Audio extraction failed: {result.audio_extraction.error}"

        if not result.transcription.success:
            return f"Transcription failed: {result.transcription.error}"

        if not result.parsed_metadata.title or not result.parsed_metadata.author:
            return "Could not parse title/author from transcript"

        if not result.external_verification:
            return "No external match found on Goodreads"

        if result.final_confidence < 0.95:
            return f"Low confidence ({result.final_confidence*100:.1f}%) - external match uncertain"

        return "Unknown reason"

    def generate_summary(self):
        """Generate human-readable summary report"""
        logger.info(f"Generating summary report...")

        summary_lines = []

        summary_lines.append("=" * 80)
        summary_lines.append("AUDIOBOOK METADATA VERIFICATION SUMMARY")
        summary_lines.append("=" * 80)
        summary_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        summary_lines.append("")

        summary_lines.append("STATISTICS")
        summary_lines.append("-" * 80)
        summary_lines.append(f"Total books processed:        {self.stats['unique_books']}")
        summary_lines.append(f"Audio extracted:              {self.stats['audio_extracted']} ({self._pct(self.stats['audio_extracted'], self.stats['unique_books'])}%)")
        summary_lines.append(f"Successfully transcribed:     {self.stats['transcribed']} ({self._pct(self.stats['transcribed'], self.stats['unique_books'])}%)")
        summary_lines.append(f"Verified externally:          {self.stats['verified_external']} ({self._pct(self.stats['verified_external'], self.stats['unique_books'])}%)")
        summary_lines.append(f"Auto-updated (conf >= 95%):   {self.stats['updated']} ({self._pct(self.stats['updated'], self.stats['unique_books'])}%)")
        summary_lines.append(f"Need manual review:           {self.stats['manual_review']} ({self._pct(self.stats['manual_review'], self.stats['unique_books'])}%)")
        summary_lines.append(f"Errors:                       {self.stats['errors']}")
        summary_lines.append("")

        summary_lines.append("UPDATED BOOKS (Confidence >= 95%)")
        summary_lines.append("-" * 80)

        updated_books = [r for r in self.results if r.updated]
        if updated_books:
            for result in updated_books:
                summary_lines.append(f"\nBook ID: {result.book_id}")
                summary_lines.append(f"  Original: {result.current_title}")
                if result.external_verification:
                    summary_lines.append(f"  Updated:  {result.external_verification.title}")
                    summary_lines.append(f"  Author:   {result.external_verification.author}")
                    if result.external_verification.series_name:
                        summary_lines.append(f"  Series:   {result.external_verification.series_name} #{result.external_verification.series_position}")
                summary_lines.append(f"  Confidence: {result.final_confidence*100:.1f}%")
        else:
            summary_lines.append("No books updated automatically")

        summary_lines.append("")
        summary_lines.append("")
        summary_lines.append("BOOKS NEEDING MANUAL REVIEW")
        summary_lines.append("-" * 80)

        manual_review = [r for r in self.results if r.final_confidence < 0.95]
        if manual_review:
            for result in manual_review:
                summary_lines.append(f"\nBook ID: {result.book_id}")
                summary_lines.append(f"  Current: {result.current_title}")
                summary_lines.append(f"  Confidence: {result.final_confidence*100:.1f}%")
                summary_lines.append(f"  Reason: {self._get_review_reason(result)}")

                if result.parsed_metadata.title:
                    summary_lines.append(f"  Audio says: '{result.parsed_metadata.title}' by {result.parsed_metadata.author}")

                if result.external_verification:
                    summary_lines.append(f"  Goodreads: '{result.external_verification.title}' by {result.external_verification.author}")
        else:
            summary_lines.append("All books successfully verified!")

        summary_lines.append("")
        summary_lines.append("=" * 80)
        summary_lines.append("END OF REPORT")
        summary_lines.append("=" * 80)

        summary_text = "\n".join(summary_lines)

        # Save to file
        with open(SUMMARY_FILE, 'w', encoding='utf-8') as f:
            f.write(summary_text)

        # Also print to console
        print("\n" + summary_text)

        logger.info(f"Summary saved to {SUMMARY_FILE}")

    def _pct(self, numerator: int, denominator: int) -> int:
        """Calculate percentage"""
        if denominator == 0:
            return 0
        return int((numerator / denominator) * 100)

    async def run(self):
        """Main workflow"""
        logger.info("=" * 80)
        logger.info("AUDIOBOOK AUDIO-BASED VERIFICATION SYSTEM")
        logger.info("=" * 80)
        logger.info("")

        # Load books
        books = self.load_uncertain_books()
        if not books:
            logger.error("No books to process")
            return False

        # Verify all books
        await self.verify_all_books(books)

        # Save results
        self.save_results()
        self.save_manual_review()
        self.generate_summary()

        logger.info("")
        logger.info("Verification complete!")
        logger.info(f"Results: {RESULTS_FILE}")
        logger.info(f"Summary: {SUMMARY_FILE}")
        logger.info(f"Audit log: {log_file}")

        if self.stats['manual_review'] > 0:
            logger.info(f"Manual review: {MANUAL_REVIEW_FILE}")

        return True


async def main():
    """Entry point"""
    if not ABS_TOKEN:
        logger.error("ERROR: ABS_TOKEN not found in environment!")
        logger.error("Please set ABS_TOKEN in .env file")
        return 1

    try:
        orchestrator = VerificationOrchestrator(ABS_URL, ABS_TOKEN)
        success = await orchestrator.run()
        return 0 if success else 1

    except KeyboardInterrupt:
        logger.info("\n\nInterrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
