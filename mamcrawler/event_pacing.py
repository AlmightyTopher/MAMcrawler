"""
Event-Aware Pacing (Section 6).
Detects freeleech/bonus events and adjusts download pacing accordingly.
"""

import logging
import asyncio
from typing import Dict, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class EventAwarePacing:
    """
    Detects and responds to MAM events (freeleech, bonus, etc.).
    Adjusts download pacing to maximize value while protecting VIP status.
    """
    
    def __init__(self):
        self.current_event = None
        self.event_history = []
        self.pacing_mode = 'normal'  # 'normal', 'event', 'cautious'
    
    async def detect_events(self, mam_scraper) -> Optional[Dict]:
        """
        Detect active events on MAM.
        
        Args:
            mam_scraper: MAM scraper instance to check for events
            
        Returns:
            Event dict or None
        """
        try:
            logger.info("🔍 Checking for MAM events...")
            
            # Scrape MAM homepage/announcements for events
            event = await mam_scraper.check_for_events()
            
            if event:
                event_type = event.get('type', 'unknown')
                logger.info(f"🎉 Event detected: {event_type}")
                logger.info(f"  Description: {event.get('description', 'N/A')}")
                logger.info(f"  Duration: {event.get('duration', 'Unknown')}")
                
                self.current_event = event
                self.event_history.append({
                    'event': event,
                    'detected_at': datetime.now()
                })
                
                # Adjust pacing mode
                self._adjust_pacing_mode(event)
            else:
                logger.info("ℹ️  No active events detected")
                self.current_event = None
                self.pacing_mode = 'normal'
            
            return event
            
        except Exception as e:
            logger.error(f"Failed to detect events: {e}")
            return None
    
    def _adjust_pacing_mode(self, event: Dict):
        """
        Adjust pacing mode based on event type.
        
        Event Types:
        - freeleech: Downloads don't count against ratio
        - bonus_points: Extra bonus points for downloads/uploads
        - double_upload: Upload counts double
        - half_download: Downloads count half
        """
        event_type = event.get('type', '').lower()
        
        if 'freeleech' in event_type or 'free' in event_type:
            self.pacing_mode = 'event'
            logger.info("🚀 Pacing mode: EVENT (Aggressive downloading)")
        
        elif 'bonus' in event_type or 'double' in event_type:
            self.pacing_mode = 'event'
            logger.info("🚀 Pacing mode: EVENT (Increased activity)")
        
        else:
            self.pacing_mode = 'normal'
            logger.info("📊 Pacing mode: NORMAL")
    
    def get_download_delay(self) -> int:
        """
        Get download delay based on current pacing mode.
        
        Returns:
            Delay in seconds between downloads
        """
        if self.pacing_mode == 'event':
            # Aggressive during events
            return 30  # 30 seconds
        elif self.pacing_mode == 'cautious':
            # Conservative when ratio is low
            return 300  # 5 minutes
        else:
            # Normal pacing
            return 120  # 2 minutes
    
    def get_max_concurrent_downloads(self) -> int:
        """
        Get maximum concurrent downloads based on pacing mode.
        
        Returns:
            Max concurrent downloads
        """
        if self.pacing_mode == 'event':
            return 5  # Aggressive
        elif self.pacing_mode == 'cautious':
            return 1  # Conservative
        else:
            return 2  # Normal
    
    def get_download_limit(self, timeframe: str = 'hour') -> int:
        """
        Get download limit for timeframe.
        
        Args:
            timeframe: 'hour', 'day', 'week'
            
        Returns:
            Max downloads for timeframe
        """
        if self.pacing_mode == 'event':
            limits = {'hour': 20, 'day': 100, 'week': 500}
        elif self.pacing_mode == 'cautious':
            limits = {'hour': 2, 'day': 10, 'week': 50}
        else:
            limits = {'hour': 5, 'day': 30, 'week': 150}
        
        return limits.get(timeframe, 0)
    
    def should_download_now(self, ratio: float) -> bool:
        """
        Determine if it's safe to download now.
        
        Args:
            ratio: Current global ratio
            
        Returns:
            True if safe to download
        """
        # Always safe during freeleech
        if self.pacing_mode == 'event' and self.current_event:
            event_type = self.current_event.get('type', '').lower()
            if 'freeleech' in event_type:
                return True
        
        # Check ratio
        if ratio < 1.0:
            logger.warning("⚠️  Ratio too low for downloads")
            self.pacing_mode = 'cautious'
            return False
        elif ratio < 1.2:
            logger.warning("⚠️  Ratio in caution zone")
            self.pacing_mode = 'cautious'
            return True
        else:
            return True
    
    async def wait_for_next_download(self):
        """Wait appropriate delay before next download."""
        delay = self.get_download_delay()
        
        logger.info(f"⏱️  Pacing delay: {delay}s ({self.pacing_mode} mode)")
        await asyncio.sleep(delay)
    
    def get_event_status(self) -> Dict:
        """
        Get current event status.
        
        Returns:
            Dict with event info and pacing settings
        """
        return {
            'current_event': self.current_event,
            'pacing_mode': self.pacing_mode,
            'download_delay': self.get_download_delay(),
            'max_concurrent': self.get_max_concurrent_downloads(),
            'hourly_limit': self.get_download_limit('hour'),
            'daily_limit': self.get_download_limit('day')
        }
    
    def is_event_active(self) -> bool:
        """Check if an event is currently active."""
        return self.current_event is not None
    
    def get_event_type(self) -> Optional[str]:
        """Get current event type."""
        if self.current_event:
            return self.current_event.get('type')
        return None
    
    async def schedule_event_check(self, mam_scraper, interval: int = 3600):
        """
        Schedule periodic event checks.
        
        Args:
            mam_scraper: MAM scraper instance
            interval: Check interval in seconds (default 1 hour)
        """
        while True:
            try:
                await self.detect_events(mam_scraper)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Event check error: {e}")
                await asyncio.sleep(interval)
    
    def calculate_optimal_downloads(self, 
                                    available_books: int,
                                    current_ratio: float,
                                    event_duration_hours: Optional[int] = None) -> int:
        """
        Calculate optimal number of downloads for current conditions.
        
        Args:
            available_books: Number of books available to download
            current_ratio: Current global ratio
            event_duration_hours: Hours remaining in event (if applicable)
            
        Returns:
            Recommended number of downloads
        """
        if self.pacing_mode == 'event' and event_duration_hours:
            # Aggressive during events
            downloads_per_hour = self.get_download_limit('hour')
            optimal = min(
                available_books,
                downloads_per_hour * event_duration_hours
            )
            logger.info(f"📊 Optimal downloads during event: {optimal}")
            return optimal
        
        elif self.pacing_mode == 'cautious':
            # Conservative when ratio low
            optimal = min(available_books, 5)
            logger.info(f"📊 Optimal downloads (cautious): {optimal}")
            return optimal
        
        else:
            # Normal pacing
            optimal = min(available_books, 20)
            logger.info(f"📊 Optimal downloads (normal): {optimal}")
            return optimal
