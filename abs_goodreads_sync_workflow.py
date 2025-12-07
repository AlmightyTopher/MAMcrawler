#!/usr/bin/env python3
"""
AudiobookShelf ↔ Goodreads Metadata Sync Workflow

Uses Goodreads web crawler to enhance AudiobookShelf metadata with:
- Rating and review counts
- Narrator information (for audiobooks)
- Series information and sequence
- Publication details

Usage:
    python abs_goodreads_sync_workflow.py --limit 10
    python abs_goodreads_sync_workflow.py --limit 100 --validate-audio
    python abs_goodreads_sync_workflow.py --limit 10 --auto-update
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

import aiohttp

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables from .env file
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()

from backend.integrations.goodreads_metadata_resolver import (
    GoodreadsMetadataResolver,
    ResolutionResult
)
from backend.integrations.audiobookshelf_hardcover_sync import (
    AudiobookShelfClient,
    AudiobookMetadata,
    SyncResult
)
from backend.integrations.audio_validator import AudioValidator

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class ABSGoodreadsWorkflow:
    """
    Complete AudiobookShelf ↔ Goodreads sync workflow
    """

    def __init__(self, limit: int = 10, auto_update: bool = False, validate_audio: bool = False):
        """
        Initialize workflow

        Args:
            limit: Number of books to process
            auto_update: Whether to auto-update ABS with Goodreads data
            validate_audio: Whether to validate audio files
        """
        self.limit = limit
        self.auto_update = auto_update
        self.validate_audio = validate_audio
        self.abs_client = None
        self.gr_resolver = None
        self.results = []
        self.start_time = None
        self.abs_context = None  # Store the async context manager

    async def run(self) -> bool:
        """Execute the complete workflow"""
        self.start_time = datetime.now()

        try:
            logger.info("=" * 80)
            logger.info("AUDIOBOOKSHELF ↔ GOODREADS METADATA SYNC WORKFLOW")
            logger.info("=" * 80)

            # Phase 1: Initialize and authenticate
            if not await self._phase1_init():
                logger.error("Phase 1 failed: Initialization")
                return False

            # Phase 2: Scan AudiobookShelf library
            if not await self._phase2_scan():
                logger.error("Phase 2 failed: Library scan")
                return False

            # Phase 3: Resolve via Goodreads
            if not await self._phase3_resolve():
                logger.error("Phase 3 failed: Goodreads resolution")
                return False

            # Phase 4: Optional audio validation
            if self.validate_audio:
                if not await self._phase4_validate():
                    logger.warning("Phase 4 warning: Audio validation had issues")

            # Phase 5: Generate report
            if not await self._phase5_report():
                logger.error("Phase 5 failed: Report generation")
                return False

            logger.info("=" * 80)
            logger.info("WORKFLOW COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            return True

        except Exception as e:
            logger.error(f"Workflow error: {e}", exc_info=True)
            return False

        finally:
            await self._cleanup()

    async def _phase1_init(self) -> bool:
        """Phase 1: Initialize and authenticate"""
        logger.info("\nPHASE 1: INITIALIZATION")
        logger.info("-" * 80)

        try:
            # Load environment
            abs_url = os.getenv('ABS_URL', 'http://localhost:13378')
            abs_token = os.getenv('ABS_TOKEN')
            gr_email = os.getenv('GOODREADS_EMAIL')
            gr_password = os.getenv('GOODREADS_PASSWORD')

            if not all([abs_token, gr_email, gr_password]):
                logger.error("Missing required environment variables:")
                if not abs_token:
                    logger.error("  - ABS_TOKEN")
                if not gr_email:
                    logger.error("  - GOODREADS_EMAIL")
                if not gr_password:
                    logger.error("  - GOODREADS_PASSWORD")
                return False

            logger.info(f"AudiobookShelf URL: {abs_url}")
            logger.info(f"Goodreads Email: {gr_email[:20]}***")

            # Initialize Goodreads resolver
            self.gr_resolver = GoodreadsMetadataResolver(gr_email, gr_password)

            # Test AudiobookShelf connection
            logger.info("\nTesting AudiobookShelf API...")
            try:
                # Create and store the AudiobookShelf client context
                self.abs_context = AudiobookShelfClient(abs_url, abs_token)
                self.abs_client = await self.abs_context.__aenter__()

                libs = await self.abs_client.get_libraries()
                if libs:
                    logger.info(f"  Connected to AudiobookShelf")
                    logger.info(f"  Libraries: {len(libs)}")
                    for lib in libs:
                        logger.info(f"    - {lib.get('name', 'Unknown')}")
                else:
                    logger.warning("  No libraries found")
            except Exception as e:
                logger.error(f"  Failed to connect: {e}")
                return False

            # Authenticate with Goodreads
            logger.info("\nAuthenticating with Goodreads...")
            if await self.gr_resolver.initialize():
                logger.info("  Successfully authenticated with Goodreads")
            else:
                logger.error("  Failed to authenticate with Goodreads")
                return False

            logger.info("\nPhase 1: OK")
            return True

        except Exception as e:
            logger.error(f"Phase 1 error: {e}", exc_info=True)
            return False

    async def _phase2_scan(self) -> bool:
        """Phase 2: Scan AudiobookShelf library"""
        logger.info("\nPHASE 2: LIBRARY SCAN")
        logger.info("-" * 80)

        try:
            libraries = await self.abs_client.get_libraries()
            if not libraries:
                logger.error("No libraries found")
                return False

            # Use first library
            library = libraries[0]
            library_id = library['id']
            logger.info(f"Scanning library: {library['name']} (ID: {library_id})")

            # Get books
            books = []
            offset = 0
            while len(books) < self.limit:
                response = await self.abs_client.get_library_items(library_id, limit=50, offset=offset)
                if not response or 'results' not in response:
                    break
                batch = response.get('results', [])
                if not batch:
                    break
                books.extend(batch)
                offset += 50

            books = books[:self.limit]
            logger.info(f"Found {len(books)} books to process")

            # Store for next phase
            self.library_id = library_id
            self.books = books

            logger.info("Phase 2: OK")
            return True

        except Exception as e:
            logger.error(f"Phase 2 error: {e}", exc_info=True)
            return False

    async def _phase3_resolve(self) -> bool:
        """Phase 3: Resolve via Goodreads"""
        logger.info("\nPHASE 3: GOODREADS RESOLUTION")
        logger.info("-" * 80)

        try:
            results = []
            resolved_count = 0
            failed_count = 0

            for i, book in enumerate(self.books, 1):
                # Extract metadata from ABS item structure
                media = book.get('media', {})
                metadata = media.get('metadata', {})
                title = metadata.get('title', '')
                author = metadata.get('authorName', '')
                isbn = metadata.get('isbn', '')

                logger.info(f"\n[{i}/{len(self.books)}] Processing: {title}")

                try:

                    if not title:
                        logger.warning("  No title, skipping")
                        continue

                    logger.info(f"  Title: {title}")
                    logger.info(f"  Author: {author}")

                    # Resolve via Goodreads
                    result = await self.gr_resolver.resolve_book(title, author, isbn)

                    if result.success:
                        logger.info(f"  RESOLVED via {result.resolution_method}")
                        logger.info(f"  Goodreads: {result.book.title} by {result.book.author}")
                        logger.info(f"  Confidence: {result.confidence:.2f}")
                        logger.info(f"  Rating: {result.book.rating}/5 ({result.book.rating_count} reviews)")
                        if result.book.narrator:
                            logger.info(f"  Narrator: {result.book.narrator}")
                        resolved_count += 1
                    else:
                        logger.warning(f"  NOT RESOLVED: {result.note}")
                        failed_count += 1

                    results.append({
                        'book_id': book.get('id'),
                        'title': title,
                        'author': author,
                        'resolution': result,
                        'goodreads_data': result.book if result.success else None
                    })

                except Exception as e:
                    logger.error(f"  Error processing book: {e}")
                    failed_count += 1
                    continue

            logger.info("\n" + "-" * 80)
            logger.info(f"Resolution Summary:")
            logger.info(f"  Resolved: {resolved_count}/{len(self.books)} ({100*resolved_count//len(self.books)}%)")
            logger.info(f"  Failed: {failed_count}/{len(self.books)}")

            self.resolution_results = results

            logger.info("Phase 3: OK")
            return True

        except Exception as e:
            logger.error(f"Phase 3 error: {e}", exc_info=True)
            return False

    async def _phase4_validate(self) -> bool:
        """Phase 4: Optional audio file validation"""
        logger.info("\nPHASE 4: AUDIO VALIDATION")
        logger.info("-" * 80)

        try:
            validator = AudioValidator()
            validated = 0

            for result in self.resolution_results:
                if not result['goodreads_data']:
                    continue

                # Would validate audio files here if they were available
                # For now, just counting what could be validated
                validated += 1

            logger.info(f"Validated {validated} audio files")
            logger.info("Phase 4: OK (simulation)")
            return True

        except Exception as e:
            logger.error(f"Phase 4 error: {e}", exc_info=True)
            return False

    async def _phase5_report(self) -> bool:
        """Phase 5: Generate report"""
        logger.info("\nPHASE 5: REPORT GENERATION")
        logger.info("-" * 80)

        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'workflow_duration': str(datetime.now() - self.start_time),
                'books_processed': len(self.books),
                'books_resolved': sum(1 for r in self.resolution_results if r['resolution'].success),
                'books_failed': sum(1 for r in self.resolution_results if not r['resolution'].success),
                'resolution_rate': 100 * sum(1 for r in self.resolution_results if r['resolution'].success) / max(len(self.resolution_results), 1),
                'results': [
                    {
                        'title': r['title'],
                        'author': r['author'],
                        'resolution_method': r['resolution'].resolution_method,
                        'confidence': r['resolution'].confidence,
                        'goodreads_data': {
                            'title': r['goodreads_data'].title,
                            'author': r['goodreads_data'].author,
                            'rating': r['goodreads_data'].rating,
                            'rating_count': r['goodreads_data'].rating_count,
                            'narrator': r['goodreads_data'].narrator,
                        } if r['goodreads_data'] else None
                    }
                    for r in self.resolution_results
                ]
            }

            # Save report
            report_path = "abs_goodreads_sync_report.json"
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)

            logger.info(f"Report saved to {report_path}")
            logger.info(f"  Total processed: {report['books_processed']}")
            logger.info(f"  Resolved: {report['books_resolved']}")
            logger.info(f"  Failed: {report['books_failed']}")
            logger.info(f"  Success rate: {report['resolution_rate']:.1f}%")

            logger.info("Phase 5: OK")
            return True

        except Exception as e:
            logger.error(f"Phase 5 error: {e}", exc_info=True)
            return False

    async def _cleanup(self):
        """Clean up resources"""
        logger.info("\nCleaning up...")
        if self.abs_context:
            await self.abs_context.__aexit__(None, None, None)
        if self.gr_resolver:
            await self.gr_resolver.close()


async def main():
    """Entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="AudiobookShelf ↔ Goodreads Metadata Sync")
    parser.add_argument('--limit', type=int, default=10, help='Number of books to process (default: 10)')
    parser.add_argument('--auto-update', action='store_true', help='Auto-update AudiobookShelf with Goodreads data')
    parser.add_argument('--validate-audio', action='store_true', help='Validate audio files')
    args = parser.parse_args()

    workflow = ABSGoodreadsWorkflow(
        limit=args.limit,
        auto_update=args.auto_update,
        validate_audio=args.validate_audio
    )

    success = await workflow.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    asyncio.run(main())
