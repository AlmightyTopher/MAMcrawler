#!/usr/bin/env python3
"""
AudiobookShelf ↔ Goodreads Metadata Sync Worker

Processes a batch of books and resolves them via Goodreads.
Spawned by the dual orchestrator to run in parallel (VPN + Direct modes).

Usage:
    python abs_goodreads_sync_worker.py --config worker_config_vpn.json --output results_vpn.json
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Load environment variables from .env file
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.integrations.goodreads_metadata_resolver import (
    GoodreadsMetadataResolver,
    ResolutionResult
)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class SyncWorker:
    """
    Worker process for metadata resolution.

    Each worker instance:
    - Processes books from a config file
    - Authenticates independently with Goodreads
    - Resolves books via 3-stage waterfall
    - Writes results to output file
    """

    def __init__(self, config_path: str, output_path: str):
        """
        Initialize worker

        Args:
            config_path: Path to worker_config_{mode}.json
            output_path: Path to write results
        """
        self.config_path = Path(config_path)
        self.output_path = Path(output_path)
        self.config = None
        self.books = []
        self.gr_resolver = None
        self.results = []
        self.start_time = None

    async def run(self) -> bool:
        """Execute the worker"""
        self.start_time = datetime.now()

        try:
            logger.info("=" * 80)
            logger.info(f"WORKER STARTED (Mode: {self._get_mode()})")
            logger.info("=" * 80)

            # Load config
            if not self._load_config():
                return False

            # Initialize Goodreads
            gr_email = os.getenv('GOODREADS_EMAIL')
            gr_password = os.getenv('GOODREADS_PASSWORD')

            if not gr_email or not gr_password:
                logger.error("Missing Goodreads credentials in environment")
                return False

            self.gr_resolver = GoodreadsMetadataResolver(gr_email, gr_password)

            logger.info(f"Authenticating with Goodreads...")
            if not await self.gr_resolver.initialize():
                logger.error("Failed to authenticate with Goodreads")
                return False

            logger.info(f"Successfully authenticated with Goodreads")

            # Process books
            logger.info(f"\nProcessing {len(self.books)} books...")
            await self._resolve_books()

            # Write results
            if not await self._write_results():
                return False

            logger.info("\n" + "=" * 80)
            logger.info(f"WORKER COMPLETED SUCCESSFULLY (Mode: {self._get_mode()})")
            logger.info("=" * 80)
            return True

        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            return False

        finally:
            if self.gr_resolver:
                await self.gr_resolver.close()

    def _load_config(self) -> bool:
        """Load worker configuration"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)

            self.books = self.config.get('books', [])
            logger.info(f"Loaded {len(self.books)} books from {self.config_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return False

    async def _resolve_books(self):
        """Resolve all books via Goodreads"""
        resolved_count = 0
        failed_count = 0

        for i, book in enumerate(self.books, 1):
            title = book.get('title', '')
            author = book.get('author', '')
            isbn = book.get('isbn', '')

            logger.info(f"\n[{i}/{len(self.books)}] {title}")

            try:
                # Resolve via Goodreads
                result = await self.gr_resolver.resolve_book(title, author, isbn)

                if result.success:
                    logger.info(f"  RESOLVED via {result.resolution_method}")
                    logger.info(f"  Confidence: {result.confidence:.2f}")
                    logger.info(f"  Rating: {result.book.rating}/5")
                    resolved_count += 1
                else:
                    logger.warning(f"  NOT RESOLVED: {result.note}")
                    failed_count += 1

                self.results.append({
                    'title': title,
                    'author': author,
                    'resolution_method': result.resolution_method,
                    'confidence': result.confidence,
                    'goodreads_data': {
                        'title': result.book.title,
                        'author': result.book.author,
                        'rating': result.book.rating,
                        'rating_count': result.book.rating_count,
                        'narrator': result.book.narrator,
                    } if result.success else None
                })

            except Exception as e:
                logger.error(f"  Error processing: {e}")
                failed_count += 1
                self.results.append({
                    'title': title,
                    'author': author,
                    'resolution_method': 'error',
                    'confidence': 0.0,
                    'goodreads_data': None,
                    'error': str(e)
                })

        logger.info(f"\n{'-' * 80}")
        logger.info(f"Resolution Summary:")
        logger.info(f"  Resolved: {resolved_count}/{len(self.books)}")
        logger.info(f"  Failed: {failed_count}/{len(self.books)}")
        logger.info(f"  Success rate: {100 * resolved_count / max(len(self.books), 1):.1f}%")

    async def _write_results(self) -> bool:
        """Write results to output file"""
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'mode': self.config.get('mode', 'unknown'),
                'workflow_duration': str(datetime.now() - self.start_time),
                'books_processed': len(self.books),
                'books_resolved': sum(1 for r in self.results if r.get('resolution_method') != 'error' and r.get('goodreads_data')),
                'books_failed': sum(1 for r in self.results if r.get('resolution_method') == 'error' or not r.get('goodreads_data')),
                'results': self.results
            }

            with open(self.output_path, 'w') as f:
                json.dump(report, f, indent=2)

            logger.info(f"Results written to {self.output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to write results: {e}")
            return False

    def _get_mode(self) -> str:
        """Get worker mode (vpn or direct)"""
        return self.config.get('mode', 'unknown') if self.config else 'unknown'


async def main():
    """Entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="AudiobookShelf ↔ Goodreads Metadata Sync Worker"
    )
    parser.add_argument(
        '--config',
        type=str,
        required=True,
        help='Path to worker config file'
    )
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Path to write results'
    )
    args = parser.parse_args()

    worker = SyncWorker(args.config, args.output)
    success = await worker.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    asyncio.run(main())
