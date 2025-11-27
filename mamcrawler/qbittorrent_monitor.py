"""
Continuous qBittorrent Monitoring (Section 10).
Real-time torrent state tracking and optimization.
"""

import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class QBittorrentMonitor:
    """
    Monitors qBittorrent torrents in real-time.
    Handles stalled torrents, seeding optimization, and ratio protection.
    """
    
    def __init__(self, qbt_client):
        """
        Args:
            qbt_client: qBittorrent API client
        """
        self.qbt_client = qbt_client
        self.monitoring = False
        self.stalled_torrents = {}  # hash -> stall_count
        self.monitoring_task = None
    
    async def start_monitoring(self, interval: int = 60):
        """
        Start continuous monitoring.
        
        Args:
            interval: Check interval in seconds (default 60)
        """
        if self.monitoring:
            logger.warning("Monitoring already running")
            return
        
        self.monitoring = True
        logger.info(f"🔍 Starting qBittorrent monitoring (interval: {interval}s)")
        
        self.monitoring_task = asyncio.create_task(self._monitoring_loop(interval))
    
    async def stop_monitoring(self):
        """Stop continuous monitoring."""
        if not self.monitoring:
            return
        
        self.monitoring = False
        logger.info("🛑 Stopping qBittorrent monitoring")
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def _monitoring_loop(self, interval: int):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                await self._check_torrents()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(interval)
    
    async def _check_torrents(self):
        """Check all torrents and take action."""
        try:
            torrents = await self.qbt_client.get_torrents()
            
            if not torrents:
                return
            
            logger.debug(f"📊 Checking {len(torrents)} torrents...")
            
            for torrent in torrents:
                await self._check_torrent(torrent)
            
        except Exception as e:
            logger.error(f"Failed to check torrents: {e}")
    
    async def _check_torrent(self, torrent: Dict):
        """
        Check individual torrent and take action.
        
        Actions:
        1. Restart stalled torrents
        2. Ensure completed torrents are seeding
        3. Track ratio and upload stats
        """
        torrent_hash = torrent.get('hash')
        name = torrent.get('name', 'Unknown')
        state = torrent.get('state', '')
        progress = torrent.get('progress', 0)
        ratio = torrent.get('ratio', 0)
        
        # 1. Check for stalled downloads
        if state in ['stalledDL', 'metaDL'] and progress < 1.0:
            await self._handle_stalled_download(torrent_hash, name)
        
        # 2. Ensure completed torrents are seeding
        elif progress >= 1.0 and state not in ['uploading', 'stalledUP', 'queuedUP', 'checkingUP']:
            await self._ensure_seeding(torrent_hash, name)
        
        # 3. Track seeding progress
        elif state in ['uploading', 'stalledUP']:
            self._track_seeding(torrent_hash, name, ratio)
    
    async def _handle_stalled_download(self, torrent_hash: str, name: str):
        """
        Handle stalled download.
        
        Strategy:
        1. First stall: Wait and monitor
        2. Second stall: Force reannounce
        3. Third stall: Pause and resume
        4. Fourth+ stall: Log error
        """
        stall_count = self.stalled_torrents.get(torrent_hash, 0) + 1
        self.stalled_torrents[torrent_hash] = stall_count
        
        logger.warning(f"⚠️  Stalled download detected: {name} (Stall #{stall_count})")
        
        if stall_count == 1:
            # Just monitor
            logger.info(f"  Monitoring for next check...")
        
        elif stall_count == 2:
            # Force reannounce
            logger.info(f"  Forcing reannounce...")
            try:
                await self.qbt_client.reannounce_torrent(torrent_hash)
            except Exception as e:
                logger.error(f"  Failed to reannounce: {e}")
        
        elif stall_count == 3:
            # Pause and resume
            logger.info(f"  Pausing and resuming...")
            try:
                await self.qbt_client.pause_torrent(torrent_hash)
                await asyncio.sleep(2)
                await self.qbt_client.resume_torrent(torrent_hash)
            except Exception as e:
                logger.error(f"  Failed to pause/resume: {e}")
        
        else:
            # Log persistent stall
            logger.error(f"  ❌ Persistent stall detected! Manual intervention may be required.")
    
    async def _ensure_seeding(self, torrent_hash: str, name: str):
        """Ensure completed torrent is seeding."""
        logger.info(f"🌱 Ensuring seeding: {name}")
        
        try:
            # Resume torrent to ensure it's seeding
            await self.qbt_client.resume_torrent(torrent_hash)
            
            # Clear stall count
            if torrent_hash in self.stalled_torrents:
                del self.stalled_torrents[torrent_hash]
            
        except Exception as e:
            logger.error(f"Failed to ensure seeding: {e}")
    
    def _track_seeding(self, torrent_hash: str, name: str, ratio: float):
        """Track seeding progress."""
        # Clear stall count for actively seeding torrents
        if torrent_hash in self.stalled_torrents:
            del self.stalled_torrents[torrent_hash]
        
        # Log milestone ratios
        if ratio >= 2.0 and ratio < 2.1:
            logger.info(f"🎯 Excellent ratio: {name} (Ratio: {ratio:.2f})")
        elif ratio >= 5.0 and ratio < 5.1:
            logger.info(f"🏆 Outstanding ratio: {name} (Ratio: {ratio:.2f})")
    
    async def get_torrent_stats(self) -> Dict:
        """
        Get overall torrent statistics.
        
        Returns:
            Dict with stats: total, downloading, seeding, stalled, ratio
        """
        try:
            torrents = await self.qbt_client.get_torrents()
            
            stats = {
                'total': len(torrents),
                'downloading': 0,
                'seeding': 0,
                'stalled': 0,
                'completed': 0,
                'total_ratio': 0,
                'total_uploaded': 0,
                'total_downloaded': 0
            }
            
            for torrent in torrents:
                state = torrent.get('state', '')
                progress = torrent.get('progress', 0)
                
                if progress >= 1.0:
                    stats['completed'] += 1
                
                if state in ['downloading', 'metaDL', 'allocating']:
                    stats['downloading'] += 1
                elif state in ['uploading', 'stalledUP', 'queuedUP']:
                    stats['seeding'] += 1
                
                if 'stalled' in state.lower():
                    stats['stalled'] += 1
                
                stats['total_uploaded'] += torrent.get('uploaded', 0)
                stats['total_downloaded'] += torrent.get('downloaded', 0)
            
            # Calculate global ratio
            if stats['total_downloaded'] > 0:
                stats['total_ratio'] = stats['total_uploaded'] / stats['total_downloaded']
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get torrent stats: {e}")
            return {}
    
    async def optimize_seeding(self):
        """
        Optimize seeding allocation.
        
        Strategy:
        1. Prioritize torrents with ratio < 1.0
        2. Limit upload slots for high-ratio torrents
        3. Ensure VIP-generating torrents are active
        """
        try:
            torrents = await self.qbt_client.get_torrents()
            
            # Categorize torrents
            low_ratio = []  # ratio < 1.0
            medium_ratio = []  # 1.0 <= ratio < 2.0
            high_ratio = []  # ratio >= 2.0
            
            for torrent in torrents:
                ratio = torrent.get('ratio', 0)
                progress = torrent.get('progress', 0)
                
                if progress < 1.0:
                    continue  # Skip incomplete
                
                if ratio < 1.0:
                    low_ratio.append(torrent)
                elif ratio < 2.0:
                    medium_ratio.append(torrent)
                else:
                    high_ratio.append(torrent)
            
            logger.info(f"🎯 Seeding optimization:")
            logger.info(f"  Low ratio (< 1.0): {len(low_ratio)}")
            logger.info(f"  Medium ratio (1.0-2.0): {len(medium_ratio)}")
            logger.info(f"  High ratio (>= 2.0): {len(high_ratio)}")
            
            # Prioritize low ratio torrents
            for torrent in low_ratio:
                await self.qbt_client.set_torrent_priority(torrent['hash'], 'high')
            
            # Normal priority for medium
            for torrent in medium_ratio:
                await self.qbt_client.set_torrent_priority(torrent['hash'], 'normal')
            
            # Low priority for high ratio (already contributed enough)
            for torrent in high_ratio:
                await self.qbt_client.set_torrent_priority(torrent['hash'], 'low')
            
            logger.info(f"✓ Seeding optimization complete")
            
        except Exception as e:
            logger.error(f"Failed to optimize seeding: {e}")
    
    async def force_continue_all_stalled(self):
        """Force-continue all stalled torrents (for ratio emergency)."""
        try:
            torrents = await self.qbt_client.get_torrents()
            
            stalled_count = 0
            for torrent in torrents:
                state = torrent.get('state', '')
                if 'stalled' in state.lower():
                    await self.qbt_client.resume_torrent(torrent['hash'])
                    await self.qbt_client.reannounce_torrent(torrent['hash'])
                    stalled_count += 1
            
            logger.info(f"🚀 Force-continued {stalled_count} stalled torrents")
            
        except Exception as e:
            logger.error(f"Failed to force-continue stalled torrents: {e}")
