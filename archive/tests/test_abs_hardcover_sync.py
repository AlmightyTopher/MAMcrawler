#!/usr/bin/env python3
"""
AudiobookShelf ↔ Hardcover Integration Test

Tests the complete sync pipeline:
1. Connect to AudiobookShelf API
2. Scan library and extract metadata
3. Resolve via Hardcover (3-stage waterfall)
4. Compare metadata and identify differences
5. Validate with audio file analysis
6. Report confidence scores and recommended actions
7. Optionally update metadata

Usage:
    export AUDIOBOOKSHELF_URL="http://localhost:13378"
    export AUDIOBOOKSHELF_API_KEY="your_key"
    export HARDCOVER_TOKEN="your_token"
    python test_abs_hardcover_sync.py [--limit 10] [--auto-update]
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
import aiohttp

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.integrations.hardcover_client import HardcoverClient
from backend.integrations.audiobookshelf_hardcover_sync import (
    AudiobookShelfHardcoverSync,
    AudiobookMetadata,
    SyncResult
)
from backend.integrations.audio_validator import AudioValidator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class IntegrationTestRunner:
    """Run comprehensive ABS-Hardcover sync tests"""

    def __init__(self, limit: int = 10, auto_update: bool = False):
        self.limit = limit
        self.auto_update = auto_update
        self.results: List[SyncResult] = []
        self.audio_validations: Dict = {}

        # Get credentials from environment
        self.abs_url = os.getenv("AUDIOBOOKSHELF_URL", "http://localhost:13378")
        self.abs_api_key = os.getenv("AUDIOBOOKSHELF_API_KEY")
        self.hardcover_token = os.getenv("HARDCOVER_TOKEN")

        if not self.abs_api_key:
            logger.error("AUDIOBOOKSHELF_API_KEY not set")
            sys.exit(1)
        if not self.hardcover_token:
            logger.error("HARDCOVER_TOKEN not set")
            sys.exit(1)

    async def run_tests(self):
        """Execute full test pipeline"""
        logger.info("=" * 80)
        logger.info("AudiobookShelf ↔ Hardcover Sync Integration Test")
        logger.info("=" * 80)
        logger.info(f"ABS URL: {self.abs_url}")
        logger.info(f"Limit: {self.limit} books")
        logger.info(f"Auto-update: {self.auto_update}")
        logger.info("=" * 80)

        try:
            # Test 1: API connectivity
            logger.info("\n[TEST 1] Verifying API connectivity...")
            if not await self._test_api_connectivity():
                logger.error("Failed to connect to APIs")
                return False

            logger.info("✓ API connectivity verified")

            # Test 2: Library scan
            logger.info("\n[TEST 2] Scanning AudiobookShelf library...")
            library_id = await self._get_first_library_id()
            if not library_id:
                logger.error("No library found")
                return False

            logger.info(f"✓ Found library: {library_id}")

            # Test 3: Full sync
            logger.info(f"\n[TEST 3] Running sync pipeline ({self.limit} books)...")
            await self._run_sync(library_id)

            # Test 4: Generate report
            logger.info("\n[TEST 4] Generating report...")
            await self._generate_report()

            return True

        except Exception as e:
            logger.exception(f"Test failed: {e}")
            return False

    async def _test_api_connectivity(self) -> bool:
        """Verify connections to both APIs"""
        try:
            # Test AudiobookShelf
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.abs_url}/api/libraries",
                    headers={"Authorization": f"Bearer {self.abs_api_key}"},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"ABS connection failed: HTTP {resp.status}")
                        return False
                    logger.info("  ✓ AudiobookShelf API responding")

            # Test Hardcover
            async with HardcoverClient(self.hardcover_token) as client:
                result = await client.resolve_by_search("Harry Potter")
                if not result.success:
                    logger.error("Hardcover connection failed")
                    return False
                logger.info("  ✓ Hardcover API responding")

            return True

        except Exception as e:
            logger.error(f"Connectivity test failed: {e}")
            return False

    async def _get_first_library_id(self) -> Optional[str]:
        """Get the first audiobook library ID"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.abs_url}/api/libraries",
                    headers={"Authorization": f"Bearer {self.abs_api_key}"}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        libraries = data.get("libraries", [])

                        # Find audiobook library
                        for lib in libraries:
                            if lib.get("mediaType") == "book":
                                return lib.get("id")

            logger.warning("No audiobook library found")
            return None

        except Exception as e:
            logger.error(f"Failed to get library: {e}")
            return None

    async def _run_sync(self, library_id: str):
        """Execute full sync pipeline"""
        sync = AudiobookShelfHardcoverSync(
            abs_url=self.abs_url,
            abs_api_key=self.abs_api_key,
            hardcover_token=self.hardcover_token
        )

        self.results = await sync.sync_library(
            library_id=library_id,
            limit=self.limit,
            auto_update=self.auto_update
        )

        logger.info(f"✓ Sync complete: {len(self.results)} books processed")

    async def _generate_report(self):
        """Generate detailed test report"""
        if not self.results:
            logger.warning("No results to report")
            return

        stats = {
            "total": len(self.results),
            "unchanged": sum(1 for r in self.results if r.status == "unchanged"),
            "updated": sum(1 for r in self.results if r.status == "updated"),
            "pending_verification": sum(1 for r in self.results if r.status == "pending_verification"),
            "failed": sum(1 for r in self.results if r.status == "failed"),
        }

        logger.info("\n" + "=" * 80)
        logger.info("SYNC REPORT")
        logger.info("=" * 80)

        logger.info(f"\nStatistics:")
        logger.info(f"  Total Books: {stats['total']}")
        logger.info(f"  Unchanged: {stats['unchanged']}")
        logger.info(f"  Updated: {stats['updated']}")
        logger.info(f"  Pending Verification: {stats['pending_verification']}")
        logger.info(f"  Failed: {stats['failed']}")

        # Detailed results by status
        if stats['failed'] > 0:
            logger.info(f"\n[FAILED] {stats['failed']} books:")
            for result in self.results:
                if result.status == "failed":
                    logger.info(f"  - {result.title} by {result.author}")
                    if result.match and result.match.notes:
                        logger.info(f"    Reason: {result.match.notes}")

        if stats['pending_verification'] > 0:
            logger.info(f"\n[PENDING VERIFICATION] {stats['pending_verification']} books (confidence < 0.95):")
            for result in self.results:
                if result.status == "pending_verification":
                    confidence = result.match.confidence if result.match else 0.0
                    logger.info(f"  - {result.title} by {result.author}")
                    logger.info(f"    Confidence: {confidence:.0%}")
                    if result.changes_made:
                        logger.info(f"    Differences:")
                        for diff in result.changes_made[:3]:  # Show first 3
                            logger.info(f"      • {diff}")

        if stats['updated'] > 0:
            logger.info(f"\n[UPDATED] {stats['updated']} books:")
            for result in self.results:
                if result.status == "updated":
                    logger.info(f"  - {result.title} → {result.updated_data.get('title', result.title)}")

        if stats['unchanged'] > 0:
            logger.info(f"\n[UNCHANGED] {stats['unchanged']} books (already match Hardcover):")
            count = 0
            for result in self.results:
                if result.status == "unchanged" and count < 5:  # Show first 5
                    logger.info(f"  - {result.title} by {result.author}")
                    count += 1
            if stats['unchanged'] > 5:
                logger.info(f"  ... and {stats['unchanged'] - 5} more")

        # Save detailed report
        report_file = Path("abs_hardcover_sync_report.json")
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "config": {
                "abs_url": self.abs_url,
                "limit": self.limit,
                "auto_update": self.auto_update,
            },
            "summary": stats,
            "results": [
                {
                    "id": r.audiobook_id,
                    "title": r.title,
                    "author": r.author,
                    "status": r.status,
                    "confidence": r.match.confidence if r.match else 0.0,
                    "changes": r.changes_made,
                    "previous_data": r.previous_data,
                    "updated_data": r.updated_data,
                    "notes": r.match.notes if r.match else None,
                }
                for r in self.results
            ]
        }

        with open(report_file, "w") as f:
            json.dump(report_data, f, indent=2)

        logger.info(f"\n✓ Detailed report saved to: {report_file}")

        logger.info("\n" + "=" * 80)
        logger.info("RECOMMENDATIONS")
        logger.info("=" * 80)

        if stats['pending_verification'] > 0:
            logger.info(f"\n1. Manual Verification Required ({stats['pending_verification']} books):")
            logger.info("   - Run audio_validator on low-confidence matches")
            logger.info("   - Listen to audiobooks to confirm title/author/series")
            logger.info("   - Use open_in_player() method for quick preview")

        if stats['failed'] > 0:
            logger.info(f"\n2. Resolution Failures ({stats['failed']} books):")
            logger.info("   - Check if books exist in Hardcover.app")
            logger.info("   - May need to use fallback API (Google Books)")
            logger.info("   - Consider fuzzy search with different author names")

        if stats['updated'] > 0 and not self.auto_update:
            logger.info(f"\n3. Ready to Update ({stats['updated']} books):")
            logger.info("   - Run with --auto-update flag to apply changes")
            logger.info("   - Review updated_data in report for each book")

        logger.info("\nNext Steps:")
        logger.info("  1. Review pending verification items")
        logger.info("  2. Validate audio files using audio_validator.py")
        logger.info("  3. Confirm metadata matches Hardcover canonical names")
        logger.info("  4. Run sync again with --auto-update to apply changes")


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Test AudiobookShelf ↔ Hardcover sync integration"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Limit number of books to sync (default: 10)"
    )
    parser.add_argument(
        "--auto-update",
        action="store_true",
        help="Automatically update metadata if confidence >= 0.95"
    )

    args = parser.parse_args()

    runner = IntegrationTestRunner(
        limit=args.limit,
        auto_update=args.auto_update
    )

    success = await runner.run_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
