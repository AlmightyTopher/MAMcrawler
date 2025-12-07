#!/usr/bin/env python3
"""
Dual AudiobookShelf ↔ Goodreads Metadata Sync Workflow

Runs two instances in parallel:
1. VPN instance (via WireGuard tunnel) - slower but stealthy
2. Direct instance (direct network) - faster but visible

Each instance processes half of the library concurrently.

Usage:
    python dual_abs_goodreads_sync_workflow.py --limit 100
    python dual_abs_goodreads_sync_workflow.py --limit 500 --auto-update
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

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

import aiohttp
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


class DualABSGoodreadsWorkflow:
    """
    Orchestrates two concurrent Goodreads sync workflows:
    - VPN Worker: Uses WireGuard tunnel for stealth (slower)
    - Direct Worker: Direct network connection (faster)
    """

    def __init__(
        self,
        limit: int = 100,
        auto_update: bool = False,
        validate_audio: bool = False,
        vpn_python: Optional[str] = None
    ):
        """
        Initialize dual workflow orchestrator

        Args:
            limit: Total number of books to process (split evenly)
            auto_update: Whether to auto-update ABS with Goodreads data
            validate_audio: Whether to validate audio files
            vpn_python: Path to python executable routed through WireGuard
        """
        self.limit = limit
        self.auto_update = auto_update
        self.validate_audio = validate_audio
        # VPN Python: use provided path or construct from current project directory
        if vpn_python:
            self.vpn_python = Path(vpn_python)
        else:
            project_dir = Path(__file__).parent
            self.vpn_python = project_dir / "python_vpn.exe"
        self.direct_python = Path(sys.executable)
        self.results = []
        self.start_time = None

    async def run(self) -> bool:
        """Execute both workflows concurrently"""
        self.start_time = datetime.now()

        try:
            logger.info("=" * 80)
            logger.info("DUAL AUDIOBOOKSHELF ↔ GOODREADS SYNC WORKFLOW")
            logger.info("=" * 80)
            logger.info(f"Processing {self.limit} books across 2 workers")
            logger.info(f"VPN Worker (Stealth): {self.vpn_python}")
            logger.info(f"Direct Worker (Fast): {self.direct_python}")

            # Get books from ABS first (only once, then split)
            books = await self._get_books_to_process()
            if not books:
                logger.error("No books found in AudiobookShelf")
                return False

            # Split books between workers
            mid = len(books) // 2
            vpn_books = books[:mid]
            direct_books = books[mid:]

            logger.info(f"\nSpawning workers:")
            logger.info(f"  VPN Worker: {len(vpn_books)} books")
            logger.info(f"  Direct Worker: {len(direct_books)} books")

            # Create worker config files
            await self._write_worker_config(vpn_books, "vpn")
            await self._write_worker_config(direct_books, "direct")

            # Start workers concurrently
            vpn_task = asyncio.create_task(self._run_worker("vpn"))
            direct_task = asyncio.create_task(self._run_worker("direct"))

            # Wait for both to complete
            vpn_result = await vpn_task
            direct_result = await direct_task

            if not (vpn_result and direct_result):
                logger.error("One or both workers failed")
                return False

            # Merge results
            await self._merge_results()

            logger.info("\n" + "=" * 80)
            logger.info("DUAL WORKFLOW COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            return True

        except Exception as e:
            logger.error(f"Workflow error: {e}", exc_info=True)
            return False

    async def _get_books_to_process(self) -> List[Dict]:
        """Get books from AudiobookShelf for processing"""
        try:
            async with AudiobookShelfClient(
                os.getenv('ABS_URL', 'http://localhost:13378'),
                os.getenv('ABS_TOKEN')
            ) as abs_client:
                libraries = await abs_client.get_libraries()
                if not libraries:
                    logger.error("No libraries found")
                    return []

                library_id = libraries[0]['id']
                books = []
                offset = 0

                while len(books) < self.limit:
                    response = await abs_client.get_library_items(
                        library_id,
                        limit=50,
                        offset=offset
                    )
                    if not response or 'results' not in response:
                        break

                    batch = response.get('results', [])
                    if not batch:
                        break

                    books.extend(batch)
                    offset += 50

                return books[:self.limit]

        except Exception as e:
            logger.error(f"Failed to get books: {e}")
            return []

    async def _write_worker_config(self, books: List[Dict], mode: str):
        """Write books to worker config file"""
        config = {
            'mode': mode,
            'limit': len(books),
            'auto_update': self.auto_update,
            'validate_audio': self.validate_audio,
            'books': [
                {
                    'id': b.get('id'),
                    'title': b.get('media', {}).get('metadata', {}).get('title', ''),
                    'author': b.get('media', {}).get('metadata', {}).get('authorName', ''),
                    'isbn': b.get('media', {}).get('metadata', {}).get('isbn', '')
                }
                for b in books
            ]
        }

        config_path = Path(f"worker_config_{mode}.json")
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        logger.info(f"  Wrote {len(books)} books to {config_path}")

    async def _run_worker(self, mode: str) -> bool:
        """Run a single worker (VPN or Direct)"""
        python_exe = self.vpn_python if mode == "vpn" else self.direct_python
        config_file = f"worker_config_{mode}.json"
        output_file = f"worker_results_{mode}.json"

        # Check if VPN worker executable is valid (only for VPN mode)
        if mode == "vpn" and not Path(python_exe).exists():
            logger.warning(f"[{mode.upper()} WORKER] VPN executable not found: {python_exe}")
            logger.warning(f"[{mode.upper()} WORKER] Falling back to Direct worker (non-VPN)")
            # Use Direct python instead
            python_exe = self.direct_python
            # Rename output to indicate this is direct mode
            output_file = f"worker_results_direct_fallback.json"

        logger.info(f"\n[{mode.upper()} WORKER] Starting...")

        try:
            cmd = [
                str(python_exe),
                "abs_goodreads_sync_worker.py",
                "--config", config_file,
                "--output", output_file
            ]

            logger.info(f"[{mode.upper()} WORKER] Command: {' '.join(cmd)}")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"[{mode.upper()} WORKER] Failed with code {process.returncode}")
                if stderr:
                    logger.error(f"[{mode.upper()} WORKER] Error: {stderr.decode()}")
                return False

            logger.info(f"[{mode.upper()} WORKER] Completed successfully")
            return True

        except Exception as e:
            logger.error(f"[{mode.upper()} WORKER] Exception: {e}")
            return False

    async def _merge_results(self):
        """Merge results from both workers"""
        logger.info("\nMerging results...")

        all_results = []
        total_resolved = 0
        total_failed = 0
        total_time = datetime.now() - self.start_time

        # Try to load results from both workers (including fallback)
        result_files = [
            ("worker_results_vpn.json", "vpn"),
            ("worker_results_direct_fallback.json", "vpn_fallback"),  # VPN fallback
            ("worker_results_direct.json", "direct")
        ]

        for result_file, mode_label in result_files:
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    results = data.get('results', [])
                    all_results.extend(results)

                    total_resolved += data.get('books_resolved', 0)
                    total_failed += data.get('books_failed', 0)

                    logger.info(
                        f"  {mode_label.upper()}: "
                        f"{data.get('books_resolved', 0)}/"
                        f"{data.get('books_processed', 0)} resolved"
                    )
            except FileNotFoundError:
                pass  # File doesn't exist, skip
            except Exception as e:
                logger.error(f"Error reading {result_file}: {e}")

        # Write final merged report
        final_report = {
            'timestamp': datetime.now().isoformat(),
            'workflow_type': 'dual',
            'workflow_duration': str(total_time),
            'books_processed': len(all_results),
            'books_resolved': total_resolved,
            'books_failed': total_failed,
            'resolution_rate': 100 * total_resolved / max(len(all_results), 1),
            'worker_stats': {
                'vpn_mode': 'stealth (via WireGuard)',
                'direct_mode': 'fast (direct network)'
            },
            'results': all_results
        }

        output_file = "abs_goodreads_dual_sync_report.json"
        with open(output_file, 'w') as f:
            json.dump(final_report, f, indent=2)

        logger.info(f"\nFinal Report: {output_file}")
        logger.info(f"  Total books: {len(all_results)}")
        logger.info(f"  Resolved: {total_resolved}")
        logger.info(f"  Failed: {total_failed}")
        logger.info(f"  Success rate: {final_report['resolution_rate']:.1f}%")
        logger.info(f"  Total time: {total_time}")


async def main():
    """Entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Dual AudiobookShelf ↔ Goodreads Metadata Sync"
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='Total books to process (split between workers)'
    )
    parser.add_argument(
        '--auto-update',
        action='store_true',
        help='Auto-update AudiobookShelf with Goodreads data'
    )
    parser.add_argument(
        '--validate-audio',
        action='store_true',
        help='Validate audio files'
    )
    parser.add_argument(
        '--vpn-python',
        type=str,
        default=None,
        help='Path to Python executable routed through WireGuard'
    )
    args = parser.parse_args()

    workflow = DualABSGoodreadsWorkflow(
        limit=args.limit,
        auto_update=args.auto_update,
        validate_audio=args.validate_audio,
        vpn_python=args.vpn_python
    )

    success = await workflow.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    asyncio.run(main())
