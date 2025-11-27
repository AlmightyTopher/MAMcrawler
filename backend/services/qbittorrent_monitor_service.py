"""
QBittorrentMonitorService - Continuous Torrent Monitoring and Point Optimization
Monitors all torrent states and optimizes seeding for point maximization
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.models import Download, RatioLog
from backend.database import SessionLocal

logger = logging.getLogger(__name__)


class QBittorrentMonitorService:
    """
    Service for continuous qBittorrent monitoring and point optimization.

    Responsibility:
    - Monitor all torrent states (downloading, seeding, stalled, errored)
    - Auto-restart stalled torrents
    - Optimize seeding for point generation
    - Track upload efficiency
    - Manage bandwidth allocation
    """

    def __init__(self):
        self.qb_client = None
        self.monitoring_active = False
        self.last_check = None
        self.stalled_torrents = []
        self.seeding_torrents = []
        self.downloading_torrents = []
        self.last_checked_torrents = {}  # GAP 1: Track torrent states for completion detection

    async def initialize_qbittorrent(self) -> bool:
        """Initialize qBittorrent client connection."""
        try:
            from backend.integrations.qbittorrent_client import QBittorrentClient
            self.qb_client = QBittorrentClient()
            self.monitoring_active = True
            logger.info("QBittorrent client initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize qBittorrent client: {e}")
            return False

    async def get_torrent_states(self) -> Dict[str, List[Dict]]:
        """
        Get current states of all torrents in qBittorrent.

        Returns:
            Dictionary with lists of torrents by state
        """
        if not self.qb_client:
            if not await self.initialize_qbittorrent():
                return {
                    'downloading': [],
                    'seeding': [],
                    'stalled': [],
                    'paused': [],
                    'errored': []
                }

        try:
            all_torrents = await self.qb_client.get_all_torrents()

            states = {
                'downloading': [],
                'seeding': [],
                'stalled': [],
                'paused': [],
                'errored': []
            }

            for torrent in all_torrents:
                state = torrent.get('state', '').lower()

                if 'stalled' in state or 'error' in state:
                    states['stalled'].append(torrent)
                elif 'error' in state:
                    states['errored'].append(torrent)
                elif 'uploading' in state or 'seeding' in state:
                    states['seeding'].append(torrent)
                elif 'downloading' in state or 'allocating' in state:
                    states['downloading'].append(torrent)
                elif 'paused' in state:
                    states['paused'].append(torrent)

            self.downloading_torrents = states['downloading']
            self.seeding_torrents = states['seeding']
            self.stalled_torrents = states['stalled'] + states['errored']
            self.last_check = datetime.utcnow()

            logger.info(
                f"Torrent states: {len(states['downloading'])} downloading, "
                f"{len(states['seeding'])} seeding, "
                f"{len(self.stalled_torrents)} stalled/errored"
            )

            return states

        except Exception as e:
            logger.error(f"Error getting torrent states: {e}")
            return {
                'downloading': [],
                'seeding': [],
                'stalled': [],
                'paused': [],
                'errored': []
            }

    async def auto_restart_stalled_torrents(self) -> int:
        """
        Automatically restart stalled torrents.

        Returns:
            Number of torrents restarted
        """
        if not self.qb_client:
            return 0

        restarted_count = 0

        try:
            for torrent in self.stalled_torrents:
                try:
                    torrent_hash = torrent.get('hash')
                    if torrent_hash:
                        await self.qb_client.force_continue(torrent_hash)
                        restarted_count += 1
                        logger.info(f"Force-continued stalled torrent: {torrent.get('name')}")
                except Exception as e:
                    logger.warning(f"Failed to restart torrent {torrent.get('hash')}: {e}")

            if restarted_count > 0:
                logger.info(f"Restarted {restarted_count} stalled torrents")

        except Exception as e:
            logger.error(f"Error restarting stalled torrents: {e}")

        return restarted_count

    async def optimize_seeding_allocation(self) -> Dict[str, int]:
        """
        Optimize seeding allocation for point maximization.

        Strategy:
        - Prioritize high-value seeders (high ratio, rare content)
        - Maintain minimum seeding slots for newer downloads
        - Focus upload bandwidth on high-demand torrents

        Returns:
            Dictionary with optimization metrics
        """
        try:
            # Calculate optimization metrics
            total_seeding = len(self.seeding_torrents)
            total_downloading = len(self.downloading_torrents)

            # Optimal ratio: 70% seeding, 30% downloading
            optimal_seeding = int((total_seeding + total_downloading) * 0.7)
            optimal_downloading = (total_seeding + total_downloading) - optimal_seeding

            if not self.qb_client:
                return {
                    'current_seeding': total_seeding,
                    'current_downloading': total_downloading,
                    'optimal_seeding': optimal_seeding,
                    'optimal_downloading': optimal_downloading
                }

            # Adjust qBittorrent upload slots if needed
            current_limit = await self.qb_client.get_seeding_limit()

            if optimal_seeding > 0 and current_limit != optimal_seeding:
                await self.qb_client.set_seeding_limit(optimal_seeding)
                logger.info(f"Adjusted seeding limit: {current_limit} -> {optimal_seeding}")

            return {
                'current_seeding': total_seeding,
                'current_downloading': total_downloading,
                'optimal_seeding': optimal_seeding,
                'optimal_downloading': optimal_downloading,
                'action_taken': 'adjusted_seeding_limit' if current_limit != optimal_seeding else 'no_change'
            }

        except Exception as e:
            logger.error(f"Error optimizing seeding allocation: {e}")
            return {}

    async def calculate_point_generation(self) -> Dict[str, any]:
        """
        Calculate estimated point generation from current seeding activity.

        Returns:
            Dictionary with point generation metrics
        """
        try:
            total_seeders = len(self.seeding_torrents)
            total_upload_speed = 0
            high_priority_count = 0

            for torrent in self.seeding_torrents:
                # Get upload speed
                speed = torrent.get('upspeed', 0)
                total_upload_speed += speed

                # Count high-priority seeders (ratio < 2.0)
                ratio = torrent.get('ratio', 1.0)
                if ratio < 2.0:
                    high_priority_count += 1

            # Estimate points per hour (simple model)
            # Assuming 1 MB/s = 1 point per second
            estimated_points_per_hour = (total_upload_speed / (1024 * 1024)) * 3600

            logger.info(
                f"Point generation: {total_seeders} seeders, "
                f"{total_upload_speed / (1024 * 1024):.2f} MB/s upload, "
                f"{estimated_points_per_hour:.0f} points/hour estimated"
            )

            return {
                'total_seeders': total_seeders,
                'high_priority_seeders': high_priority_count,
                'total_upload_speed': total_upload_speed,
                'estimated_points_per_hour': estimated_points_per_hour,
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error calculating point generation: {e}")
            return {}

    async def continuous_monitoring_loop(self) -> None:
        """
        Main continuous monitoring loop (should run every 5 minutes).

        Includes GAP 1 implementation: completion event detection.
        """
        try:
            # Get current torrent states
            states = await self.get_torrent_states()

            # GAP 1: Detect completion events
            completion_events = await self.detect_completion_events()

            # GAP 1: Handle completion events
            if completion_events:
                completion_result = await self.handle_completion_events(completion_events)
                logger.info(f"GAP 1: Completion events: {completion_result}")

            # Auto-restart stalled torrents
            restarted = await self.auto_restart_stalled_torrents()

            # Optimize seeding allocation
            optimization = await self.optimize_seeding_allocation()

            # Calculate point generation
            points = await self.calculate_point_generation()

            # Log to database
            db = SessionLocal()
            try:
                # Log monitoring event
                from backend.models import Task

                monitoring_log = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'downloading': len(states.get('downloading', [])),
                    'seeding': len(states.get('seeding', [])),
                    'stalled': len(states.get('stalled', [])),
                    'restarted': restarted,
                    'completion_events': len(completion_events),  # GAP 1
                    'points_per_hour': points.get('estimated_points_per_hour', 0)
                }

                # Could log to a monitoring table if created
                logger.debug(f"Monitoring snapshot: {monitoring_log}")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")

    async def get_monitoring_status(self) -> Dict[str, any]:
        """Get current monitoring status."""
        return {
            'monitoring_active': self.monitoring_active,
            'downloading': len(self.downloading_torrents),
            'seeding': len(self.seeding_torrents),
            'stalled': len(self.stalled_torrents),
            'last_check': self.last_check.isoformat() if self.last_check else None
        }

    async def detect_completion_events(self) -> List[Dict[str, str]]:
        """
        GAP 1 IMPLEMENTATION: Detect torrent completion events.

        Compares current state with previous state to identify transitions
        from downloading to seeding/uploading.

        Returns:
            List of completion events (torrent_hash, torrent_name)
        """
        completion_events = []

        try:
            if not self.qb_client:
                if not await self.initialize_qbittorrent():
                    return []

            torrents = await self.qb_client.get_all_torrents()

            for torrent in torrents:
                torrent_hash = torrent.get('hash')
                torrent_name = torrent.get('name')
                current_state = torrent.get('state', '').lower()

                # Get previous state if tracked
                previous_state = self.last_checked_torrents.get(torrent_hash, {}).get('state')

                # Detect transition: downloading -> seeding/uploading
                if previous_state and previous_state != current_state:
                    if ('downloading' in previous_state or 'allocating' in previous_state) and \
                       ('uploading' in current_state or 'seeding' in current_state or 'forcedUP' in current_state):

                        logger.info(
                            f"GAP 1: Torrent completion detected: {torrent_name} "
                            f"({torrent_hash}) transitioned from {previous_state} to {current_state}"
                        )

                        completion_events.append({
                            'torrent_hash': torrent_hash,
                            'torrent_name': torrent_name,
                            'previous_state': previous_state,
                            'current_state': current_state,
                            'detected_at': datetime.utcnow().isoformat()
                        })

                # Update state tracking
                self.last_checked_torrents[torrent_hash] = {
                    'state': current_state,
                    'name': torrent_name,
                    'checked_at': datetime.utcnow()
                }

            return completion_events

        except Exception as e:
            logger.error(f"Error detecting completion events: {e}", exc_info=True)
            return []

    async def handle_completion_events(self, completion_events: List[Dict]) -> Dict[str, int]:
        """
        GAP 1 IMPLEMENTATION: Handle detected completion events.

        For each completion event, triggers metadata scan via DownloadService.

        Args:
            completion_events: List of completion events from detect_completion_events()

        Returns:
            Dict with count of processed events
        """
        processed_count = 0
        error_count = 0

        try:
            if not completion_events:
                return {'processed': 0, 'errors': 0}

            from backend.services.download_service import DownloadService

            db = SessionLocal()

            for event in completion_events:
                try:
                    torrent_name = event['torrent_name']

                    # Find download record by torrent hash or name
                    download = db.query(Download).filter(
                        (Download.qbittorrent_hash == event['torrent_hash']) |
                        (Download.title.contains(torrent_name.split('.')[0]))  # Match first part
                    ).first()

                    if download:
                        # Trigger completion handler
                        result = await DownloadService.on_download_completed(
                            db=db,
                            download_id=download.id,
                            torrent_name=torrent_name
                        )

                        if result.get('status') == 'success':
                            processed_count += 1
                            logger.info(
                                f"GAP 1: Completion event processed for download {download.id}: "
                                f"{torrent_name}"
                            )
                        else:
                            error_count += 1
                            logger.warning(
                                f"GAP 1: Completion event processing failed for {torrent_name}: "
                                f"{result.get('error')}"
                            )
                    else:
                        logger.warning(
                            f"GAP 1: No download found for torrent: {torrent_name} "
                            f"(hash: {event['torrent_hash']})"
                        )
                        error_count += 1

                except Exception as e:
                    logger.error(
                        f"GAP 1: Error handling completion event for {event.get('torrent_name')}: {e}",
                        exc_info=True
                    )
                    error_count += 1

            db.close()

            return {
                'processed': processed_count,
                'errors': error_count,
                'total_events': len(completion_events)
            }

        except Exception as e:
            logger.error(f"Error handling completion events: {e}", exc_info=True)
            return {'processed': 0, 'errors': len(completion_events)}
