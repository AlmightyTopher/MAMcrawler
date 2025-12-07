"""
Torrent Control Manager

Handles torrent control operations: pause, resume, restart, etc.
Provides centralized torrent action interface.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class TorrentControlManager:
    """
    Manager for torrent control operations.

    Encapsulates all torrent control including:
    - Restarting stalled torrents
    - Pausing downloading torrents
    - Resuming paused torrents
    - Per-torrent error recovery

    Args:
        monitor_service: Reference to parent QBittorrentMonitorService
    """

    def __init__(self, monitor_service):
        """Initialize control manager with monitor service reference."""
        self.monitor_service = monitor_service

    async def auto_restart_stalled_torrents(self) -> int:
        """
        Automatically restart all stalled torrents.

        Iterates through stalled torrents and forces continue on each.
        Continues on individual errors to maximize recovery.

        Returns:
            Number of torrents successfully restarted

        Example:
            >>> count = await manager.auto_restart_stalled_torrents()
            >>> print(f"Restarted {count} torrents")
        """
        if not self.monitor_service.qb_client:
            logger.warning("qBittorrent client not initialized")
            return 0

        restarted_count = 0
        failed_count = 0

        try:
            stalled_torrents = self.monitor_service.state_manager.stalled_torrents

            if not stalled_torrents:
                logger.debug("No stalled torrents to restart")
                return 0

            logger.info(f"Attempting to restart {len(stalled_torrents)} stalled torrents")

            for torrent in stalled_torrents:
                try:
                    torrent_hash = torrent.get('hash')
                    torrent_name = torrent.get('name', 'Unknown')

                    if not torrent_hash:
                        logger.warning(f"Torrent has no hash: {torrent_name}")
                        failed_count += 1
                        continue

                    # Force continue the torrent
                    await self.monitor_service.qb_client.force_continue(torrent_hash)
                    restarted_count += 1
                    logger.info(f"Force-continued stalled torrent: {torrent_name} ({torrent_hash})")

                except Exception as e:
                    torrent_name = torrent.get('name', 'Unknown')
                    logger.warning(f"Failed to restart torrent {torrent_name}: {e}")
                    failed_count += 1
                    # Continue with next torrent even if this one fails

            logger.info(
                f"Restart complete - "
                f"Successful: {restarted_count}, "
                f"Failed: {failed_count}, "
                f"Total: {restarted_count + failed_count}"
            )

            return restarted_count

        except Exception as e:
            logger.error(f"Error restarting stalled torrents: {e}", exc_info=True)
            return restarted_count

    async def restart_torrent(self, torrent_hash: str) -> bool:
        """
        Restart a specific torrent.

        Args:
            torrent_hash: Hash of torrent to restart

        Returns:
            True if successful, False otherwise

        Example:
            >>> success = await manager.restart_torrent("abc123def456")
            >>> if success:
            ...     print("Torrent restarted")
        """
        if not self.monitor_service.qb_client:
            logger.warning("qBittorrent client not initialized")
            return False

        try:
            await self.monitor_service.qb_client.force_continue(torrent_hash)
            logger.info(f"Force-continued torrent: {torrent_hash}")
            return True
        except Exception as e:
            logger.error(f"Failed to restart torrent {torrent_hash}: {e}")
            return False

    async def pause_downloading_torrents(self) -> int:
        """
        Pause all currently downloading torrents.

        Used during ratio emergency to stop bandwidth consumption.

        Returns:
            Number of torrents paused

        Example:
            >>> count = await manager.pause_downloading_torrents()
            >>> print(f"Paused {count} torrents")
        """
        if not self.monitor_service.qb_client:
            logger.warning("qBittorrent client not initialized")
            return 0

        paused_count = 0
        failed_count = 0

        try:
            downloading = self.monitor_service.state_manager.downloading_torrents

            if not downloading:
                logger.debug("No downloading torrents to pause")
                return 0

            logger.info(f"Pausing {len(downloading)} downloading torrents")

            for torrent in downloading:
                try:
                    torrent_hash = torrent.get('hash')
                    torrent_name = torrent.get('name', 'Unknown')

                    if not torrent_hash:
                        logger.warning(f"Torrent has no hash: {torrent_name}")
                        failed_count += 1
                        continue

                    await self.monitor_service.qb_client.pause_torrent(torrent_hash)
                    paused_count += 1
                    logger.info(f"Paused downloading torrent: {torrent_name}")

                except Exception as e:
                    logger.warning(f"Failed to pause torrent: {e}")
                    failed_count += 1
                    continue

            logger.info(
                f"Pause complete - "
                f"Successful: {paused_count}, "
                f"Failed: {failed_count}"
            )

            return paused_count

        except Exception as e:
            logger.error(f"Error pausing downloading torrents: {e}", exc_info=True)
            return paused_count

    async def resume_paused_torrents(self, filter_completed_only: bool = False) -> int:
        """
        Resume paused torrents.

        Args:
            filter_completed_only: If True, only resume completed (progress >= 100%) torrents

        Returns:
            Number of torrents resumed

        Example:
            >>> count = await manager.resume_paused_torrents(filter_completed_only=True)
            >>> print(f"Resumed {count} completed torrents")
        """
        if not self.monitor_service.qb_client:
            logger.warning("qBittorrent client not initialized")
            return 0

        resumed_count = 0
        skipped_count = 0
        failed_count = 0

        try:
            paused = self.monitor_service.state_manager.paused_torrents

            if not paused:
                logger.debug("No paused torrents to resume")
                return 0

            logger.info(f"Resuming {len(paused)} paused torrents")

            for torrent in paused:
                try:
                    torrent_hash = torrent.get('hash')
                    torrent_name = torrent.get('name', 'Unknown')
                    progress = torrent.get('progress', 0)

                    if not torrent_hash:
                        logger.warning(f"Torrent has no hash: {torrent_name}")
                        failed_count += 1
                        continue

                    # Skip incomplete torrents if filter enabled
                    if filter_completed_only and progress < 1.0:
                        logger.debug(f"Skipping incomplete torrent: {torrent_name} ({progress*100:.1f}%)")
                        skipped_count += 1
                        continue

                    await self.monitor_service.qb_client.resume_torrent(torrent_hash)
                    resumed_count += 1
                    logger.info(f"Resumed paused torrent: {torrent_name}")

                except Exception as e:
                    logger.warning(f"Failed to resume torrent: {e}")
                    failed_count += 1
                    continue

            logger.info(
                f"Resume complete - "
                f"Successful: {resumed_count}, "
                f"Skipped: {skipped_count}, "
                f"Failed: {failed_count}"
            )

            return resumed_count

        except Exception as e:
            logger.error(f"Error resuming paused torrents: {e}", exc_info=True)
            return resumed_count

    async def pause_torrent(self, torrent_hash: str) -> bool:
        """
        Pause a specific torrent.

        Args:
            torrent_hash: Hash of torrent to pause

        Returns:
            True if successful

        Example:
            >>> await manager.pause_torrent("abc123def456")
        """
        if not self.monitor_service.qb_client:
            logger.warning("qBittorrent client not initialized")
            return False

        try:
            await self.monitor_service.qb_client.pause_torrent(torrent_hash)
            logger.info(f"Paused torrent: {torrent_hash}")
            return True
        except Exception as e:
            logger.error(f"Failed to pause torrent {torrent_hash}: {e}")
            return False

    async def resume_torrent(self, torrent_hash: str) -> bool:
        """
        Resume a specific torrent.

        Args:
            torrent_hash: Hash of torrent to resume

        Returns:
            True if successful

        Example:
            >>> await manager.resume_torrent("abc123def456")
        """
        if not self.monitor_service.qb_client:
            logger.warning("qBittorrent client not initialized")
            return False

        try:
            await self.monitor_service.qb_client.resume_torrent(torrent_hash)
            logger.info(f"Resumed torrent: {torrent_hash}")
            return True
        except Exception as e:
            logger.error(f"Failed to resume torrent {torrent_hash}: {e}")
            return False
