"""
Torrent State Manager

Handles fetching and categorizing torrent states from qBittorrent.
Provides single source of truth for torrent state classification.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TorrentStateManager:
    """
    Manager for torrent state tracking and categorization.

    Encapsulates all state-related operations including:
    - Fetching torrents from qBittorrent
    - Categorizing torrents by state (downloading, seeding, stalled, etc.)
    - Maintaining state cache for change detection
    - Providing state statistics

    Args:
        monitor_service: Reference to parent QBittorrentMonitorService
    """

    def __init__(self, monitor_service):
        """Initialize state manager with monitor service reference."""
        self.monitor_service = monitor_service
        self.downloading_torrents = []
        self.seeding_torrents = []
        self.stalled_torrents = []
        self.paused_torrents = []
        self.errored_torrents = []
        self.last_check = None

    async def get_torrent_states(self) -> Dict[str, List[Dict]]:
        """
        Get current states of all torrents in qBittorrent.

        Fetches all torrents and categorizes them into states:
        - downloading: Active downloads
        - seeding: Active uploads/seeding
        - stalled: No progress or errors
        - paused: Manually paused
        - errored: Error state

        Returns:
            Dictionary with lists of torrents organized by state

        Example:
            >>> states = await manager.get_torrent_states()
            >>> print(f"Downloading: {len(states['downloading'])}")
            >>> print(f"Seeding: {len(states['seeding'])}")
        """
        if not self.monitor_service.qb_client:
            if not await self.monitor_service.initialize_qbittorrent():
                logger.warning("Unable to initialize qBittorrent client")
                return {
                    'downloading': [],
                    'seeding': [],
                    'stalled': [],
                    'paused': [],
                    'errored': []
                }

        try:
            # Fetch all torrents from qBittorrent
            all_torrents = await self.monitor_service.qb_client.get_all_torrents()

            # Initialize state buckets
            states = {
                'downloading': [],
                'seeding': [],
                'stalled': [],
                'paused': [],
                'errored': []
            }

            # Categorize each torrent by state
            for torrent in all_torrents:
                state = torrent.get('state', '').lower()
                torrent_name = torrent.get('name', 'Unknown')

                # Classify by state
                if 'error' in state:
                    states['errored'].append(torrent)
                    logger.debug(f"Categorized as errored: {torrent_name}")
                elif 'stalled' in state:
                    states['stalled'].append(torrent)
                    logger.debug(f"Categorized as stalled: {torrent_name}")
                elif 'uploading' in state or 'seeding' in state or 'forcedUP' in state:
                    states['seeding'].append(torrent)
                    logger.debug(f"Categorized as seeding: {torrent_name}")
                elif 'downloading' in state or 'allocating' in state or 'metaDL' in state:
                    states['downloading'].append(torrent)
                    logger.debug(f"Categorized as downloading: {torrent_name}")
                elif 'paused' in state:
                    states['paused'].append(torrent)
                    logger.debug(f"Categorized as paused: {torrent_name}")
                else:
                    # Default to seeding if state unknown but progress >= 100%
                    progress = torrent.get('progress', 0)
                    if progress >= 1.0:
                        states['seeding'].append(torrent)
                    else:
                        states['downloading'].append(torrent)
                    logger.debug(f"Categorized as unknown state (defaulted): {torrent_name} ({state})")

            # Update internal cache
            self.downloading_torrents = states['downloading']
            self.seeding_torrents = states['seeding']
            self.stalled_torrents = states['stalled'] + states['errored']
            self.paused_torrents = states['paused']
            self.errored_torrents = states['errored']
            self.last_check = datetime.utcnow()

            # Log summary
            logger.info(
                f"Torrent states updated - "
                f"Downloading: {len(states['downloading'])}, "
                f"Seeding: {len(states['seeding'])}, "
                f"Stalled: {len(states['stalled'])}, "
                f"Paused: {len(states['paused'])}, "
                f"Errored: {len(states['errored'])}"
            )

            return states

        except Exception as e:
            logger.error(f"Error getting torrent states: {e}", exc_info=True)
            return {
                'downloading': [],
                'seeding': [],
                'stalled': [],
                'paused': [],
                'errored': []
            }

    async def get_state_summary(self) -> Dict[str, int]:
        """
        Get summary counts of torrents by state.

        Returns:
            Dictionary with counts: downloading, seeding, stalled, paused, errored

        Example:
            >>> summary = await manager.get_state_summary()
            >>> print(f"Total torrents: {sum(summary.values())}")
        """
        return {
            'downloading': len(self.downloading_torrents),
            'seeding': len(self.seeding_torrents),
            'stalled': len(self.stalled_torrents),
            'paused': len(self.paused_torrents),
            'errored': len(self.errored_torrents),
            'total': len(self.downloading_torrents) + len(self.seeding_torrents) +
                    len(self.stalled_torrents) + len(self.paused_torrents) +
                    len(self.errored_torrents)
        }

    def get_downloading_count(self) -> int:
        """Get count of downloading torrents from cache."""
        return len(self.downloading_torrents)

    def get_seeding_count(self) -> int:
        """Get count of seeding torrents from cache."""
        return len(self.seeding_torrents)

    def get_stalled_count(self) -> int:
        """Get count of stalled torrents from cache."""
        return len(self.stalled_torrents)

    def get_paused_count(self) -> int:
        """Get count of paused torrents from cache."""
        return len(self.paused_torrents)

    def get_errored_count(self) -> int:
        """Get count of errored torrents from cache."""
        return len(self.errored_torrents)

    def get_last_check_time(self) -> Optional[datetime]:
        """Get timestamp of last state check."""
        return self.last_check

    async def is_stale(self, max_age_seconds: int = 300) -> bool:
        """
        Check if state cache is stale.

        Args:
            max_age_seconds: Maximum age of cache in seconds (default 5 minutes)

        Returns:
            True if cache is older than max_age_seconds

        Example:
            >>> if await manager.is_stale():
            ...     states = await manager.get_torrent_states()
        """
        if not self.last_check:
            return True

        age = (datetime.utcnow() - self.last_check).total_seconds()
        return age > max_age_seconds
