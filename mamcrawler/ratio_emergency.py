"""
Ratio Emergency System (Section 10).
Protects VIP status by ensuring ratio never drops below 1.0.
"""

import logging
import asyncio
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class RatioEmergency:
    """
    Monitors and protects global ratio.
    Triggers emergency measures if ratio approaches critical threshold.
    """
    
    # Critical thresholds
    CRITICAL_RATIO = 1.0  # Absolute floor
    WARNING_RATIO = 1.1   # Warning threshold
    SAFE_RATIO = 1.2      # Safe threshold
    
    def __init__(self, qbt_client, qbt_monitor):
        """
        Args:
            qbt_client: qBittorrent API client
            qbt_monitor: QBittorrentMonitor instance
        """
        self.qbt_client = qbt_client
        self.qbt_monitor = qbt_monitor
        self.emergency_active = False
        self.last_check = None
        self.monitoring_task = None
    
    async def check_ratio(self) -> float:
        """
        Check current global ratio.
        
        Returns:
            Current ratio
        """
        try:
            stats = await self.qbt_monitor.get_torrent_stats()
            ratio = stats.get('total_ratio', 0)
            
            self.last_check = datetime.now()
            
            logger.info(f"📊 Global Ratio: {ratio:.3f}")
            
            return ratio
            
        except Exception as e:
            logger.error(f"Failed to check ratio: {e}")
            return 0
    
    async def assess_ratio_status(self) -> str:
        """
        Assess current ratio status.
        
        Returns:
            'critical', 'warning', 'safe'
        """
        ratio = await self.check_ratio()
        
        if ratio < self.CRITICAL_RATIO:
            return 'critical'
        elif ratio < self.WARNING_RATIO:
            return 'warning'
        elif ratio < self.SAFE_RATIO:
            return 'caution'
        else:
            return 'safe'
    
    async def trigger_emergency(self):
        """
        Trigger ratio emergency measures.
        
        Emergency Actions (Section 10.3):
        1. FREEZE all new downloads
        2. INCREASE seeding allocation
        3. FORCE-CONTINUE all stalled torrents
        4. PRIORITIZE low-ratio torrents
        5. MONITOR continuously until safe
        """
        if self.emergency_active:
            logger.warning("⚠️  Emergency already active")
            return
        
        self.emergency_active = True
        
        logger.critical("🚨 RATIO EMERGENCY TRIGGERED!")
        logger.critical("="*70)
        
        ratio = await self.check_ratio()
        logger.critical(f"Current Ratio: {ratio:.3f} (Critical: {self.CRITICAL_RATIO})")
        
        # Action 1: Freeze downloads
        logger.critical("1️⃣ FREEZING all new downloads...")
        await self._freeze_downloads()
        
        # Action 2: Increase seeding allocation
        logger.critical("2️⃣ INCREASING seeding allocation...")
        await self._increase_seeding()
        
        # Action 3: Force-continue stalled torrents
        logger.critical("3️⃣ FORCE-CONTINUING all stalled torrents...")
        await self.qbt_monitor.force_continue_all_stalled()
        
        # Action 4: Prioritize low-ratio torrents
        logger.critical("4️⃣ PRIORITIZING low-ratio torrents...")
        await self.qbt_monitor.optimize_seeding()
        
        # Action 5: Start continuous monitoring
        logger.critical("5️⃣ Starting continuous ratio monitoring...")
        self.monitoring_task = asyncio.create_task(self._emergency_monitoring())
        
        logger.critical("="*70)
        logger.critical("🚨 Emergency measures activated. Downloads FROZEN until ratio safe.")
    
    async def _freeze_downloads(self):
        """Pause all downloading torrents."""
        try:
            torrents = await self.qbt_client.get_torrents()
            
            paused_count = 0
            for torrent in torrents:
                state = torrent.get('state', '')
                progress = torrent.get('progress', 0)
                
                # Pause incomplete downloads
                if progress < 1.0 and state not in ['pausedDL']:
                    await self.qbt_client.pause_torrent(torrent['hash'])
                    paused_count += 1
            
            logger.critical(f"  ✓ Paused {paused_count} downloading torrents")
            
        except Exception as e:
            logger.error(f"Failed to freeze downloads: {e}")
    
    async def _increase_seeding(self):
        """Increase seeding allocation."""
        try:
            # Resume all completed torrents
            torrents = await self.qbt_client.get_torrents()
            
            resumed_count = 0
            for torrent in torrents:
                progress = torrent.get('progress', 0)
                state = torrent.get('state', '')
                
                # Resume all completed torrents
                if progress >= 1.0 and state in ['pausedUP', 'stoppedUP']:
                    await self.qbt_client.resume_torrent(torrent['hash'])
                    resumed_count += 1
            
            logger.critical(f"  ✓ Resumed {resumed_count} seeding torrents")
            
            # Increase global upload limits (if applicable)
            # await self.qbt_client.set_upload_limit(0)  # Unlimited
            
        except Exception as e:
            logger.error(f"Failed to increase seeding: {e}")
    
    async def _emergency_monitoring(self):
        """
        Continuous monitoring during emergency.
        Checks ratio every 5 minutes until safe.
        """
        check_interval = 300  # 5 minutes
        
        while self.emergency_active:
            try:
                await asyncio.sleep(check_interval)
                
                status = await self.assess_ratio_status()
                ratio = await self.check_ratio()
                
                logger.critical(f"🚨 Emergency Check: Ratio {ratio:.3f} ({status})")
                
                if status == 'safe':
                    await self.resolve_emergency()
                    break
                elif status == 'caution':
                    logger.warning(f"⚠️  Ratio improving but still cautious: {ratio:.3f}")
                else:
                    logger.critical(f"❌ Ratio still critical: {ratio:.3f}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Emergency monitoring error: {e}")
    
    async def resolve_emergency(self):
        """
        Resolve ratio emergency and resume normal operations.
        """
        if not self.emergency_active:
            return
        
        ratio = await self.check_ratio()
        
        logger.info("="*70)
        logger.info(f"✅ RATIO EMERGENCY RESOLVED!")
        logger.info(f"Current Ratio: {ratio:.3f} (Safe: {self.SAFE_RATIO})")
        logger.info("="*70)
        
        # Resume downloads
        logger.info("📥 Resuming downloads...")
        await self._resume_downloads()
        
        self.emergency_active = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def _resume_downloads(self):
        """Resume paused downloads."""
        try:
            torrents = await self.qbt_client.get_torrents()
            
            resumed_count = 0
            for torrent in torrents:
                state = torrent.get('state', '')
                progress = torrent.get('progress', 0)
                
                # Resume paused downloads
                if progress < 1.0 and state in ['pausedDL']:
                    await self.qbt_client.resume_torrent(torrent['hash'])
                    resumed_count += 1
            
            logger.info(f"  ✓ Resumed {resumed_count} downloads")
            
        except Exception as e:
            logger.error(f"Failed to resume downloads: {e}")
    
    async def is_safe_to_download(self) -> bool:
        """
        Check if it's safe to start new downloads.
        
        Returns:
            True if ratio is safe for downloads
        """
        if self.emergency_active:
            logger.warning("⚠️  Downloads frozen due to ratio emergency")
            return False
        
        status = await self.assess_ratio_status()
        
        if status == 'critical':
            # Trigger emergency
            await self.trigger_emergency()
            return False
        elif status == 'warning':
            logger.warning(f"⚠️  Ratio in warning zone. Proceeding with caution.")
            return True  # Allow but warn
        else:
            return True
    
    async def get_status_report(self) -> Dict:
        """
        Get detailed ratio status report.
        
        Returns:
            Dict with ratio, status, emergency_active, etc.
        """
        ratio = await self.check_ratio()
        status = await self.assess_ratio_status()
        stats = await self.qbt_monitor.get_torrent_stats()
        
        return {
            'ratio': ratio,
            'status': status,
            'emergency_active': self.emergency_active,
            'last_check': self.last_check,
            'total_uploaded': stats.get('total_uploaded', 0),
            'total_downloaded': stats.get('total_downloaded', 0),
            'seeding_count': stats.get('seeding', 0),
            'downloading_count': stats.get('downloading', 0)
        }
