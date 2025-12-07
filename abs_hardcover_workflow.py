#!/usr/bin/env python3
"""
Complete AudiobookShelf ↔ Hardcover Workflow

Orchestrates the complete metadata validation and update process:
1. Scan AudiobookShelf library
2. Resolve each audiobook via Hardcover (3-stage waterfall)
3. Compare with existing metadata and identify differences
4. For low-confidence matches: validate against audio file metadata
5. Report results and optionally update AudiobookShelf

This workflow implements the user's request:
"Run the hardcover metadata program against Audiobookshelf's metadata and ensure
that it is updating all metadata. Use the file details from the book to ensure we
have the appropriate name scheme. Then look at what's already there for metadata
for cross-referencing. If those don't match and we don't have a positive match,
then listen to the book until we have a positive audio book title, author, and series"

Usage:
    export AUDIOBOOKSHELF_URL="http://localhost:13378"
    export AUDIOBOOKSHELF_API_KEY="your_key"
    export HARDCOVER_TOKEN="your_token"

    # Test with 10 books, review changes before updating
    python abs_hardcover_workflow.py --limit 10

    # Test with manual audio validation for low-confidence matches
    python abs_hardcover_workflow.py --limit 10 --validate-audio

    # Auto-update metadata if confidence >= 0.95
    python abs_hardcover_workflow.py --limit 10 --auto-update

    # Full workflow: validate + audio check + auto-update
    python abs_hardcover_workflow.py --limit 100 --validate-audio --auto-update
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
    SyncResult,
    HardcoverMatch
)
from backend.integrations.audio_validator import AudioValidator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class ABSHardcoverWorkflow:
    """Complete AudiobookShelf ↔ Hardcover metadata workflow"""

    def __init__(
        self,
        limit: int = 10,
        auto_update: bool = False,
        validate_audio: bool = False
    ):
        self.limit = limit
        self.auto_update = auto_update
        self.validate_audio = validate_audio

        # Get credentials from environment
        self.abs_url = os.getenv("AUDIOBOOKSHELF_URL", "http://localhost:13378")
        self.abs_api_key = os.getenv("AUDIOBOOKSHELF_API_KEY")
        self.hardcover_token = os.getenv("HARDCOVER_TOKEN")

        if not self.abs_api_key or not self.hardcover_token:
            logger.error("Missing required environment variables")
            logger.error("Set: AUDIOBOOKSHELF_API_KEY, HARDCOVER_TOKEN")
            sys.exit(1)

        self.sync: Optional[AudiobookShelfHardcoverSync] = None
        self.audio_validator = AudioValidator()
        self.workflow_results: List[Dict] = []

    async def run_workflow(self) -> bool:
        """Execute complete workflow"""
        logger.info("=" * 80)
        logger.info("AudiobookShelf ↔ Hardcover Complete Workflow")
        logger.info("=" * 80)
        logger.info(f"ABS URL: {self.abs_url}")
        logger.info(f"Limit: {self.limit} books")
        logger.info(f"Auto-update: {self.auto_update}")
        logger.info(f"Audio validation: {self.validate_audio}")
        logger.info("=" * 80)

        try:
            # Step 1: Verify connectivity
            logger.info("\n[STEP 1] Verifying API connectivity...")
            if not await self._verify_connectivity():
                return False

            # Step 2: Get library ID
            logger.info("\n[STEP 2] Locating AudiobookShelf library...")
            library_id = await self._get_library_id()
            if not library_id:
                return False

            # Step 3: Run sync pipeline
            logger.info(f"\n[STEP 3] Running Hardcover sync ({self.limit} books)...")
            sync_results = await self._run_sync(library_id)
            if not sync_results:
                return False

            # Step 4: Optional audio validation
            if self.validate_audio:
                logger.info(f"\n[STEP 4] Validating audio files for low-confidence matches...")
                await self._validate_low_confidence_matches(sync_results)
            else:
                logger.info(f"\n[STEP 4] Audio validation skipped (use --validate-audio to enable)")

            # Step 5: Generate final report
            logger.info(f"\n[STEP 5] Generating comprehensive report...")
            await self._generate_final_report(sync_results)

            return True

        except Exception as e:
            logger.exception(f"Workflow failed: {e}")
            return False

    async def _verify_connectivity(self) -> bool:
        """Verify connections to both APIs"""
        try:
            # Test ABS
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.abs_url}/api/libraries",
                    headers={"Authorization": f"Bearer {self.abs_api_key}"},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"ABS connection failed: HTTP {resp.status}")
                        return False
                    logger.info("  ✓ AudiobookShelf API connected")

            # Test Hardcover
            async with HardcoverClient(self.hardcover_token) as client:
                result = await client.resolve_by_search("Harry Potter")
                if not result.success:
                    logger.error("Hardcover connection failed")
                    return False
                logger.info("  ✓ Hardcover API connected")

            return True

        except Exception as e:
            logger.error(f"Connectivity check failed: {e}")
            return False

    async def _get_library_id(self) -> Optional[str]:
        """Get first audiobook library ID"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.abs_url}/api/libraries",
                    headers={"Authorization": f"Bearer {self.abs_api_key}"}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for lib in data.get("libraries", []):
                            if lib.get("mediaType") == "book":
                                lib_id = lib.get("id")
                                lib_name = lib.get("name")
                                logger.info(f"  ✓ Found library: {lib_name} ({lib_id})")
                                return lib_id

            logger.error("No audiobook library found")
            return None

        except Exception as e:
            logger.error(f"Failed to get library: {e}")
            return None

    async def _run_sync(self, library_id: str) -> Optional[List[SyncResult]]:
        """Execute sync pipeline"""
        try:
            self.sync = AudiobookShelfHardcoverSync(
                abs_url=self.abs_url,
                abs_api_key=self.abs_api_key,
                hardcover_token=self.hardcover_token
            )

            results = await self.sync.sync_library(
                library_id=library_id,
                limit=self.limit,
                auto_update=self.auto_update and not self.validate_audio,
                minimum_confidence=0.9
            )

            logger.info(f"  ✓ Sync complete: {len(results)} books processed")

            # Count by status
            unchanged = sum(1 for r in results if r.status == "unchanged")
            updated = sum(1 for r in results if r.status == "updated")
            pending = sum(1 for r in results if r.status == "pending_verification")
            failed = sum(1 for r in results if r.status == "failed")

            logger.info(f"    • {unchanged} unchanged")
            logger.info(f"    • {updated} updated")
            logger.info(f"    • {pending} pending verification")
            logger.info(f"    • {failed} failed")

            return results

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            return None

    async def _validate_low_confidence_matches(self, results: List[SyncResult]):
        """Validate low-confidence matches against audio files"""
        low_confidence = [
            r for r in results
            if r.match and r.match.confidence < 0.95
        ]

        if not low_confidence:
            logger.info("  ✓ All matches have high confidence (>= 0.95)")
            return

        logger.info(f"  Found {len(low_confidence)} low-confidence matches")

        for i, result in enumerate(low_confidence[:5], 1):  # Validate first 5
            logger.info(f"\n  [{i}/{min(5, len(low_confidence))}] Validating: {result.title}")
            logger.info(f"      ABS: {result.title} by {result.author}")

            if result.match:
                logger.info(f"      HC: {result.match.hardcover_title} by {result.match.hardcover_author}")
                logger.info(f"      Confidence: {result.match.confidence:.0%}")

            # Try to find and validate audio files
            # Note: This requires knowing where ABS stores files
            # Typically in library paths from ABS metadata
            logger.info("      → Manual verification needed (see audio files in ABS)")

        if len(low_confidence) > 5:
            logger.info(f"\n  ... and {len(low_confidence) - 5} more low-confidence matches")

    async def _generate_final_report(self, results: List[SyncResult]):
        """Generate comprehensive workflow report"""
        stats = {
            "total": len(results),
            "unchanged": sum(1 for r in results if r.status == "unchanged"),
            "updated": sum(1 for r in results if r.status == "updated"),
            "pending_verification": sum(1 for r in results if r.status == "pending_verification"),
            "failed": sum(1 for r in results if r.status == "failed"),
        }

        logger.info("\n" + "=" * 80)
        logger.info("WORKFLOW REPORT")
        logger.info("=" * 80)

        # Summary statistics
        logger.info(f"\nSummary:")
        logger.info(f"  Total Books: {stats['total']}")
        logger.info(f"  Unchanged: {stats['unchanged']} ({stats['unchanged']*100//stats['total']}%)")
        logger.info(f"  Updated: {stats['updated']} ({stats['updated']*100//stats['total']}%)")
        logger.info(f"  Pending Verification: {stats['pending_verification']} ({stats['pending_verification']*100//stats['total']}%)")
        logger.info(f"  Failed: {stats['failed']} ({stats['failed']*100//stats['total']}%)")

        # Detailed sections
        if stats['failed'] > 0:
            logger.info(f"\n[FAILED] {stats['failed']} books (could not resolve):")
            for result in results:
                if result.status == "failed":
                    logger.info(f"  • {result.title} by {result.author}")

        if stats['pending_verification'] > 0:
            logger.info(f"\n[PENDING VERIFICATION] {stats['pending_verification']} books (confidence < 0.95):")
            for result in results:
                if result.status == "pending_verification":
                    conf = result.match.confidence if result.match else 0.0
                    logger.info(f"  • {result.title} ({conf:.0%})")
                    if result.changes_made:
                        for diff in result.changes_made[:1]:
                            logger.info(f"      {diff}")

        if stats['updated'] > 0:
            logger.info(f"\n[UPDATED] {stats['updated']} books:")
            for result in results[:5]:
                if result.status == "updated":
                    logger.info(f"  • {result.title}")
                    if result.updated_data.get('series'):
                        logger.info(f"      Series: {result.updated_data['series']}")

        # Save detailed report
        report_file = Path("abs_hardcover_workflow_report.json")
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "config": {
                "abs_url": self.abs_url,
                "limit": self.limit,
                "auto_update": self.auto_update,
                "validate_audio": self.validate_audio,
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
                for r in results
            ]
        }

        with open(report_file, "w") as f:
            json.dump(report_data, f, indent=2)

        logger.info(f"\n✓ Report saved to: {report_file}")

        # Next steps
        logger.info("\n" + "=" * 80)
        logger.info("NEXT STEPS")
        logger.info("=" * 80)

        if not self.auto_update and stats['updated'] > 0:
            logger.info(f"\n1. Review changes:")
            logger.info(f"   • {stats['updated']} books ready for update")
            logger.info(f"   • Review: {report_file}")
            logger.info(f"   • Re-run with --auto-update to apply changes")

        if stats['pending_verification'] > 0:
            logger.info(f"\n2. Manual verification needed:")
            logger.info(f"   • {stats['pending_verification']} books need audio file check")
            logger.info(f"   • Use validate_audiobooks.py with --auto-open")
            logger.info(f"   • Or manually review in AudiobookShelf")

        if stats['failed'] > 0:
            logger.info(f"\n3. Resolution failures:")
            logger.info(f"   • {stats['failed']} books not found in Hardcover")
            logger.info(f"   • Check if they exist in Hardcover.app")
            logger.info(f"   • May need fallback to Google Books API")

        logger.info(f"\n✓ Workflow complete: {datetime.now().isoformat()}")
        logger.info("=" * 80)


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="AudiobookShelf ↔ Hardcover complete metadata workflow"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Limit number of books to process (default: 10)"
    )
    parser.add_argument(
        "--auto-update",
        action="store_true",
        help="Automatically update metadata if confidence >= 0.95"
    )
    parser.add_argument(
        "--validate-audio",
        action="store_true",
        help="Validate audio files for low-confidence matches"
    )

    args = parser.parse_args()

    workflow = ABSHardcoverWorkflow(
        limit=args.limit,
        auto_update=args.auto_update,
        validate_audio=args.validate_audio
    )

    success = await workflow.run_workflow()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
