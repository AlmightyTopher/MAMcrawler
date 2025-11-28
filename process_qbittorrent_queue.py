#!/usr/bin/env python3
"""
Process qBittorrent Queue File

Reads qbittorrent_queue.json and attempts to add queued magnet links
to available qBittorrent instances (primary or secondary).

Usage:
    python process_qbittorrent_queue.py

Features:
- Automatic retry with primary and secondary instances
- Detailed logging of processing results
- Queue file cleanup after successful processing
- Support for manual triggering via command line
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'integrations'))

from qbittorrent_resilient import ResilientQBittorrentClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)5s] %(message)s',
    handlers=[
        logging.FileHandler('queue_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class QueueProcessor:
    """Process queued magnet links from JSON file"""

    def __init__(self, queue_file: str = "qbittorrent_queue.json"):
        self.queue_file = Path(queue_file)
        self.primary_url = os.getenv('QBITTORRENT_URL', 'http://192.168.0.48:52095/')
        self.secondary_url = os.getenv('QBITTORRENT_SECONDARY_URL', 'http://localhost:52095/')
        self.username = os.getenv('QBITTORRENT_USERNAME')
        self.password = os.getenv('QBITTORRENT_PASSWORD')
        self.savepath = os.getenv('QBITTORRENT_SAVEPATH', 'F:/Audiobookshelf/Books')

        if not self.username or not self.password:
            logger.error("Missing qBittorrent credentials in environment")
            logger.error("Set QBITTORRENT_USERNAME and QBITTORRENT_PASSWORD")
            sys.exit(1)

    async def process_queue(self) -> dict:
        """
        Process queue file and return results

        Returns:
            dict: {
                'queue_exists': bool,
                'total_queued': int,
                'successful': int,
                'failed': int,
                'still_queued': int,
                'queue_deleted': bool
            }
        """
        logger.info("=" * 80)
        logger.info("qBittorrent Queue Processor")
        logger.info("=" * 80)

        # Check if queue file exists
        if not self.queue_file.exists():
            logger.info(f"No queue file found at: {self.queue_file}")
            logger.info("Nothing to process.")
            return {
                'queue_exists': False,
                'total_queued': 0,
                'successful': 0,
                'failed': 0,
                'still_queued': 0,
                'queue_deleted': False
            }

        logger.info(f"Found queue file: {self.queue_file}")

        # Read queue file to show what we're processing
        try:
            import json
            with open(self.queue_file, 'r') as f:
                queue_data = json.load(f)

            saved_at = queue_data.get('saved_at', 'Unknown')
            reason = queue_data.get('reason', 'Unknown')
            magnets = queue_data.get('magnets', [])

            logger.info(f"Queue File Details:")
            logger.info(f"  Saved At: {saved_at}")
            logger.info(f"  Reason: {reason}")
            logger.info(f"  Total Magnets: {len(magnets)}")
            logger.info("")

            if not magnets:
                logger.warning("Queue file is empty (no magnets)")
                # Delete empty queue file
                self.queue_file.unlink()
                logger.info("Deleted empty queue file")
                return {
                    'queue_exists': True,
                    'total_queued': 0,
                    'successful': 0,
                    'failed': 0,
                    'still_queued': 0,
                    'queue_deleted': True
                }

            # Display queued magnets
            logger.info("Queued Magnets:")
            for i, magnet in enumerate(magnets[:5], 1):
                # Extract torrent name from magnet link
                dn_start = magnet.find('dn=')
                if dn_start != -1:
                    dn_end = magnet.find('&', dn_start)
                    torrent_name = magnet[dn_start+3:dn_end] if dn_end != -1 else magnet[dn_start+3:]
                    logger.info(f"  {i}. {torrent_name}")
                else:
                    logger.info(f"  {i}. {magnet[:60]}...")

            if len(magnets) > 5:
                logger.info(f"  ... and {len(magnets) - 5} more")
            logger.info("")

        except Exception as e:
            logger.error(f"Failed to read queue file: {e}")
            return {
                'queue_exists': True,
                'total_queued': 0,
                'successful': 0,
                'failed': 0,
                'still_queued': 0,
                'queue_deleted': False,
                'error': str(e)
            }

        # Process queue using resilient client
        try:
            async with ResilientQBittorrentClient(
                primary_url=self.primary_url,
                secondary_url=self.secondary_url,
                username=self.username,
                password=self.password,
                queue_file=str(self.queue_file),
                savepath=self.savepath
            ) as client:

                # Perform health check first
                logger.info("Checking qBittorrent instance health...")
                health = await client.perform_health_check()

                vpn_status = "CONNECTED" if health['vpn_connected'] else "DOWN"
                logger.info(f"  VPN Status: {vpn_status}")
                logger.info(f"  Primary Instance ({self.primary_url}): {health['primary']}")
                logger.info(f"  Secondary Instance ({self.secondary_url}): {health['secondary']}")
                logger.info("")

                # Warn if both instances are down
                if health['primary'] != 'OK' and health['secondary'] != 'OK':
                    logger.warning("WARNING: Both instances are unavailable!")
                    logger.warning("Cannot process queue at this time.")
                    logger.warning("Please ensure at least one qBittorrent instance is running.")
                    return {
                        'queue_exists': True,
                        'total_queued': len(magnets),
                        'successful': 0,
                        'failed': 0,
                        'still_queued': len(magnets),
                        'queue_deleted': False,
                        'error': 'All instances unavailable'
                    }

                # Process the queue
                logger.info(f"Processing {len(magnets)} queued magnets...")
                logger.info("")

                successful, failed = await client.process_queue_file()

                logger.info("")
                logger.info("=" * 80)
                logger.info("Processing Results:")
                logger.info("=" * 80)
                logger.info(f"  Total Queued: {len(magnets)}")
                logger.info(f"  Successfully Added: {len(successful)}")
                logger.info(f"  Failed to Add: {len(failed)}")

                # Check if queue file was deleted (all processed)
                queue_deleted = not self.queue_file.exists()

                if queue_deleted:
                    logger.info(f"  Queue File: DELETED (all magnets processed)")
                else:
                    # Re-read to see what's left
                    with open(self.queue_file, 'r') as f:
                        remaining_data = json.load(f)
                    remaining_magnets = remaining_data.get('magnets', [])
                    logger.info(f"  Still Queued: {len(remaining_magnets)}")
                    logger.info(f"  Queue File: RETAINED (some magnets failed)")

                logger.info("=" * 80)

                # Success summary
                if queue_deleted and len(successful) == len(magnets):
                    logger.info("")
                    logger.info("SUCCESS: All queued magnets were successfully added!")
                    logger.info("You can now check your qBittorrent Web UI to see them downloading.")
                elif len(successful) > 0:
                    logger.info("")
                    logger.info(f"PARTIAL SUCCESS: {len(successful)} magnets added, {len(failed)} still in queue")
                    logger.info("Run this script again later to retry failed magnets.")
                else:
                    logger.info("")
                    logger.info("NO MAGNETS ADDED: All attempts failed")
                    logger.info("Check qBittorrent instances and network connectivity.")

                return {
                    'queue_exists': True,
                    'total_queued': len(magnets),
                    'successful': len(successful),
                    'failed': len(failed),
                    'still_queued': len(remaining_magnets) if not queue_deleted else 0,
                    'queue_deleted': queue_deleted
                }

        except Exception as e:
            logger.error(f"Error processing queue: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'queue_exists': True,
                'total_queued': len(magnets) if 'magnets' in locals() else 0,
                'successful': 0,
                'failed': len(magnets) if 'magnets' in locals() else 0,
                'still_queued': len(magnets) if 'magnets' in locals() else 0,
                'queue_deleted': False,
                'error': str(e)
            }

    def print_manual_instructions(self):
        """Print instructions for manual queue processing"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("MANUAL RECOVERY INSTRUCTIONS")
        logger.info("=" * 80)
        logger.info("")
        logger.info("If automatic processing fails, you can manually add magnets:")
        logger.info("")
        logger.info("1. Open queue file:")
        logger.info(f"   notepad {self.queue_file}")
        logger.info("")
        logger.info("2. Copy magnet links from 'magnets' array")
        logger.info("")
        logger.info("3. Add to qBittorrent Web UI:")
        logger.info(f"   - Primary: {self.primary_url}")
        logger.info(f"   - Secondary: {self.secondary_url}")
        logger.info("")
        logger.info("4. In Web UI:")
        logger.info("   - Click 'Add Torrent' (+ icon)")
        logger.info("   - Paste magnets (one per line)")
        logger.info("   - Set Category: audiobooks")
        logger.info(f"   - Set Save Path: {self.savepath}")
        logger.info("   - Click 'Download'")
        logger.info("")
        logger.info("5. Delete queue file after manual addition:")
        logger.info(f"   del {self.queue_file}")
        logger.info("")
        logger.info("=" * 80)


async def main():
    """Main entry point"""
    processor = QueueProcessor()

    try:
        result = await processor.process_queue()

        # If processing failed and queue still exists, show manual instructions
        if result.get('error') or (result['still_queued'] > 0 and result['successful'] == 0):
            processor.print_manual_instructions()

        # Exit with appropriate code
        if result.get('error'):
            sys.exit(1)
        elif result['still_queued'] > 0:
            sys.exit(2)  # Partial success
        else:
            sys.exit(0)  # Full success

    except KeyboardInterrupt:
        logger.info("")
        logger.info("Processing interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
