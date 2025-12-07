"""
Completion Event Manager

Handles detection and processing of torrent completion events.
Implements GAP 1: Torrent completion event detection and handling.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CompletionEventManager:
    """
    Manager for torrent completion event detection and handling.

    Encapsulates all completion-related operations including:
    - Detecting state transitions (downloading -> seeding)
    - Triggering completion handlers
    - Maintaining completion history
    - Database integration for downloads

    GAP 1 Implementation: Automatically detects when torrents complete
    and triggers metadata scanning via DownloadService.

    Args:
        monitor_service: Reference to parent QBittorrentMonitorService
    """

    def __init__(self, monitor_service):
        """Initialize completion manager with monitor service reference."""
        self.monitor_service = monitor_service
        self.last_checked_torrents = {}  # Track torrent states for change detection
        self.completion_history = []  # Recent completions

    async def detect_completion_events(self) -> List[Dict[str, str]]:
        """
        Detect torrent completion events by comparing state transitions.

        Compares current torrent states with previous states to identify
        transitions from downloading/allocating to seeding/uploading.

        Returns:
            List of completion events with structure:
            {
                'torrent_hash': str,
                'torrent_name': str,
                'previous_state': str,
                'current_state': str,
                'detected_at': str (ISO datetime)
            }

        Example:
            >>> events = await manager.detect_completion_events()
            >>> for event in events:
            ...     print(f"Completed: {event['torrent_name']}")
        """
        completion_events = []

        try:
            if not self.monitor_service.qb_client:
                if not await self.monitor_service.initialize_qbittorrent():
                    return []

            # Get all torrents
            torrents = await self.monitor_service.qb_client.get_all_torrents()

            if not torrents:
                logger.debug("No torrents to check for completion")
                return []

            logger.debug(f"Checking {len(torrents)} torrents for completion events")

            for torrent in torrents:
                torrent_hash = torrent.get('hash')
                torrent_name = torrent.get('name', 'Unknown')
                current_state = torrent.get('state', '').lower()

                if not torrent_hash:
                    logger.warning(f"Torrent has no hash: {torrent_name}")
                    continue

                # Get previous state from tracking
                previous_state = self.last_checked_torrents.get(torrent_hash, {}).get('state')

                # Detect state transition: downloading/allocating -> seeding/uploading
                if previous_state and previous_state != current_state:
                    # Check for download to seeding transition
                    is_download_to_seeding = (
                        ('downloading' in previous_state or 'allocating' in previous_state or 'metaDL' in previous_state) and
                        ('uploading' in current_state or 'seeding' in current_state or 'forcedUP' in current_state)
                    )

                    if is_download_to_seeding:
                        logger.info(
                            f"Completion detected: {torrent_name} "
                            f"({torrent_hash}) transitioned "
                            f"from {previous_state} -> {current_state}"
                        )

                        event = {
                            'torrent_hash': torrent_hash,
                            'torrent_name': torrent_name,
                            'previous_state': previous_state,
                            'current_state': current_state,
                            'detected_at': datetime.utcnow().isoformat()
                        }

                        completion_events.append(event)
                        self.completion_history.append(event)

                # Update state tracking for next check
                self.last_checked_torrents[torrent_hash] = {
                    'state': current_state,
                    'name': torrent_name,
                    'checked_at': datetime.utcnow()
                }

            if completion_events:
                logger.info(f"Detected {len(completion_events)} completion events")

            return completion_events

        except Exception as e:
            logger.error(f"Error detecting completion events: {e}", exc_info=True)
            return []

    async def handle_completion_events(self, completion_events: List[Dict]) -> Dict[str, int]:
        """
        Handle detected completion events.

        For each completion event, triggers metadata scan via DownloadService
        and updates download records.

        Args:
            completion_events: List of completion events from detect_completion_events()

        Returns:
            Dictionary with:
            - processed: Number of successfully handled events
            - errors: Number of failed events
            - total_events: Total number of events

        Example:
            >>> events = await manager.detect_completion_events()
            >>> result = await manager.handle_completion_events(events)
            >>> print(f"Processed {result['processed']} completions")
        """
        processed_count = 0
        error_count = 0

        try:
            if not completion_events:
                return {'processed': 0, 'errors': 0, 'total_events': 0}

            from backend.services.download_service import DownloadService
            from backend.models import Download
            from backend.database import SessionLocal

            logger.info(f"Handling {len(completion_events)} completion events")

            db = SessionLocal()

            try:
                for event in completion_events:
                    try:
                        torrent_hash = event['torrent_hash']
                        torrent_name = event['torrent_name']

                        logger.debug(f"Processing completion for: {torrent_name}")

                        # Find matching download record
                        download = db.query(Download).filter(
                            (Download.qbittorrent_hash == torrent_hash) |
                            (Download.title.contains(torrent_name.split('.')[0]))
                        ).first()

                        if not download:
                            logger.warning(
                                f"No download record found for: {torrent_name} "
                                f"(hash: {torrent_hash})"
                            )
                            error_count += 1
                            continue

                        # Trigger completion handler
                        result = await DownloadService.on_download_completed(
                            db=db,
                            download_id=download.id,
                            torrent_name=torrent_name
                        )

                        if result.get('status') == 'success':
                            processed_count += 1
                            logger.info(
                                f"Completion handled for download {download.id}: "
                                f"{torrent_name}"
                            )
                        else:
                            error_count += 1
                            error_msg = result.get('error', 'Unknown error')
                            logger.warning(
                                f"Failed to handle completion for {torrent_name}: "
                                f"{error_msg}"
                            )

                    except Exception as e:
                        logger.error(
                            f"Error handling completion for {event.get('torrent_name')}: {e}",
                            exc_info=True
                        )
                        error_count += 1
                        continue

            finally:
                db.close()

            logger.info(
                f"Completion handling complete - "
                f"Processed: {processed_count}, Errors: {error_count}"
            )

            return {
                'processed': processed_count,
                'errors': error_count,
                'total_events': len(completion_events)
            }

        except Exception as e:
            logger.error(f"Error in completion event handling: {e}", exc_info=True)
            return {
                'processed': processed_count,
                'errors': len(completion_events),
                'total_events': len(completion_events)
            }

    async def on_torrent_completed(self, torrent_hash: str) -> bool:
        """
        Handle completion of a specific torrent.

        Args:
            torrent_hash: Hash of completed torrent

        Returns:
            True if handled successfully

        Example:
            >>> success = await manager.on_torrent_completed("abc123def456")
        """
        try:
            from backend.services.download_service import DownloadService
            from backend.models import Download
            from backend.database import SessionLocal

            db = SessionLocal()

            try:
                # Find download by hash
                download = db.query(Download).filter(
                    Download.qbittorrent_hash == torrent_hash
                ).first()

                if not download:
                    logger.warning(f"No download found for hash: {torrent_hash}")
                    return False

                result = await DownloadService.on_download_completed(
                    db=db,
                    download_id=download.id,
                    torrent_name=download.title
                )

                success = result.get('status') == 'success'

                if success:
                    logger.info(f"Handled completion for download {download.id}")
                else:
                    logger.warning(f"Failed to handle completion: {result.get('error')}")

                return success

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error handling torrent completion: {e}", exc_info=True)
            return False

    def get_recent_completions(self, limit: int = 10) -> List[Dict]:
        """
        Get recent torrent completions from history.

        Args:
            limit: Maximum number of recent completions to return

        Returns:
            List of recent completion events

        Example:
            >>> recent = manager.get_recent_completions(limit=5)
            >>> for event in recent:
            ...     print(f"{event['torrent_name']} at {event['detected_at']}")
        """
        return self.completion_history[-limit:] if self.completion_history else []

    def clear_completion_history(self) -> int:
        """
        Clear completion history.

        Returns:
            Number of events cleared

        Example:
            >>> cleared = manager.clear_completion_history()
            >>> print(f"Cleared {cleared} completion events")
        """
        count = len(self.completion_history)
        self.completion_history = []
        logger.debug(f"Cleared {count} completion events from history")
        return count

    def get_completion_stats(self) -> Dict[str, int]:
        """
        Get statistics about detected completions.

        Returns:
            Dictionary with completion statistics

        Example:
            >>> stats = manager.get_completion_stats()
            >>> print(f"Total completions: {stats['total_tracked']}")
        """
        return {
            'total_tracked': len(self.completion_history),
            'torrents_being_monitored': len(self.last_checked_torrents),
            'last_update': datetime.utcnow().isoformat()
        }
