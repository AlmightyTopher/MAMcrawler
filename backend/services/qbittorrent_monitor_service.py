"""
QBittorrentMonitorService - Continuous Torrent Monitoring and Point Optimization
Monitors all torrent states and optimizes seeding for point maximization

PHASE 3 REFACTORING: Decomposed into 4 specialized managers.
This service acts as coordinator and maintains backwards-compatible public API.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.models import Download, RatioLog
from backend.database import SessionLocal
from backend.services.qbittorrent_managers import (
    TorrentStateManager,
    TorrentControlManager,
    RatioMonitoringManager,
    CompletionEventManager
)

logger = logging.getLogger(__name__)


class QBittorrentMonitorService:
    """
    Service for continuous qBittorrent monitoring and point optimization.

    PHASE 3 REFACTORED: Now uses 4 specialized managers for single responsibility.

    Manager Responsibilities:
    - TorrentStateManager: Fetch and categorize torrents by state
    - TorrentControlManager: Control operations (pause, resume, restart)
    - RatioMonitoringManager: Monitor efficiency and seeding allocation
    - CompletionEventManager: Detect and handle torrent completions (GAP 1)

    Public API remains unchanged for backwards compatibility.
    """

    def __init__(self):
        self.qb_client = None
        self.monitoring_active = False

        # Initialize 4 specialized managers
        self.state_manager = TorrentStateManager(self)
        self.control_manager = TorrentControlManager(self)
        self.ratio_manager = RatioMonitoringManager(self)
        self.completion_manager = CompletionEventManager(self)

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

        Delegates to TorrentStateManager - backwards compatible wrapper.

        Returns:
            Dictionary with lists of torrents by state
        """
        return await self.state_manager.get_torrent_states()

    async def auto_restart_stalled_torrents(self) -> int:
        """
        Automatically restart stalled torrents.

        Delegates to TorrentControlManager - backwards compatible wrapper.

        Returns:
            Number of torrents restarted
        """
        return await self.control_manager.auto_restart_stalled_torrents()

    async def optimize_seeding_allocation(self) -> Dict[str, int]:
        """
        Optimize seeding allocation for point maximization.

        Delegates to RatioMonitoringManager - backwards compatible wrapper.

        Returns:
            Dictionary with optimization metrics
        """
        return await self.ratio_manager.optimize_seeding_allocation()

    async def calculate_point_generation(self) -> Dict[str, any]:
        """
        Calculate estimated point generation from current seeding activity.

        Delegates to RatioMonitoringManager - backwards compatible wrapper.

        Returns:
            Dictionary with point generation metrics
        """
        return await self.ratio_manager.calculate_point_generation()

    async def continuous_monitoring_loop(self) -> None:
        """
        Main continuous monitoring loop (should run every 5 minutes).

        Orchestrates all 4 managers:
        1. Get torrent states via TorrentStateManager
        2. Detect completions via CompletionEventManager
        3. Handle completions via CompletionEventManager
        4. Restart stalled via TorrentControlManager
        5. Optimize seeding via RatioMonitoringManager
        6. Calculate points via RatioMonitoringManager

        Includes GAP 1 implementation: completion event detection and handling.
        """
        try:
            # Step 1: Get current torrent states (caches results in state_manager)
            states = await self.state_manager.get_torrent_states()

            # Step 2-3: GAP 1 - Detect and handle completion events
            completion_events = await self.completion_manager.detect_completion_events()
            completion_result = None
            if completion_events:
                completion_result = await self.completion_manager.handle_completion_events(completion_events)
                logger.info(f"GAP 1: Completion events processed: {completion_result}")

            # Step 4: Auto-restart stalled torrents
            restarted = await self.control_manager.auto_restart_stalled_torrents()

            # Step 5-6: Optimize seeding and calculate points
            optimization = await self.ratio_manager.optimize_seeding_allocation()
            points = await self.ratio_manager.calculate_point_generation()

            # Log monitoring snapshot
            db = SessionLocal()
            try:
                monitoring_log = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'downloading': len(states.get('downloading', [])),
                    'seeding': len(states.get('seeding', [])),
                    'stalled': len(states.get('stalled', [])),
                    'paused': len(states.get('paused', [])),
                    'restarted': restarted,
                    'completion_events': len(completion_events),
                    'completion_processed': completion_result.get('processed', 0) if completion_result else 0,
                    'points_per_hour': points.get('estimated_points_per_hour', 0)
                }

                logger.debug(f"Monitoring snapshot: {monitoring_log}")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}", exc_info=True)

    async def get_monitoring_status(self) -> Dict[str, any]:
        """
        Get current monitoring status.

        Returns status from cached state manager results.
        """
        summary = await self.state_manager.get_state_summary()
        return {
            'monitoring_active': self.monitoring_active,
            'downloading': summary.get('downloading', 0),
            'seeding': summary.get('seeding', 0),
            'stalled': summary.get('stalled', 0),
            'paused': summary.get('paused', 0),
            'errored': summary.get('errored', 0),
            'total': summary.get('total', 0),
            'last_check': self.state_manager.get_last_check_time().isoformat() if self.state_manager.get_last_check_time() else None
        }

    async def detect_completion_events(self) -> List[Dict[str, str]]:
        """
        GAP 1 IMPLEMENTATION: Detect torrent completion events.

        Delegates to CompletionEventManager - backwards compatible wrapper.

        Returns:
            List of completion events (torrent_hash, torrent_name)
        """
        return await self.completion_manager.detect_completion_events()

    async def handle_completion_events(self, completion_events: List[Dict]) -> Dict[str, int]:
        """
        GAP 1 IMPLEMENTATION: Handle detected completion events.

        Delegates to CompletionEventManager - backwards compatible wrapper.

        Args:
            completion_events: List of completion events from detect_completion_events()

        Returns:
            Dict with count of processed events
        """
        return await self.completion_manager.handle_completion_events(completion_events)
