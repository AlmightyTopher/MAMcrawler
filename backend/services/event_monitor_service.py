"""
EventMonitorService - Event-Aware Download Management
Monitors MAM events and adjusts download strategy accordingly
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from sqlalchemy.orm import Session

from backend.models import EventStatus, Download
from backend.database import SessionLocal

logger = logging.getLogger(__name__)


class EventMonitorService:
    """
    Service for event-aware download management.

    Events monitored:
    - Freeleech (no upload required, guaranteed ratio gain)
    - Bonus events (extra points)
    - Multiplier events (upload multiplier)
    - Flashback events (old torrent specials)

    Download strategy adjusts based on active events:
    - Freeleech: Download all quality levels
    - Bonus: Prioritize high-point releases
    - Multiplier: Maximize seeding time
    - Normal: Conservative downloading
    """

    # Event impact on download decisions
    EVENT_IMPACTS = {
        'freeleech': {
            'download_rate_multiplier': 2.0,    # 2x more downloads
            'quality_minimum': 40,               # Lower quality threshold
            'priority': 'high',
            'vip_impact': 'high'                 # Uses bonus points
        },
        'bonus': {
            'download_rate_multiplier': 1.5,    # 50% more downloads
            'quality_minimum': 60,               # Standard quality
            'priority': 'medium',
            'vip_impact': 'medium'
        },
        'multiplier': {
            'download_rate_multiplier': 0.8,    # Slight slowdown
            'quality_minimum': 70,               # Higher quality focus
            'priority': 'low',
            'vip_impact': 'high'                 # Focus on seeding
        }
    }

    def __init__(self):
        self.active_events = {}
        self.last_check = None
        self.event_history = []

    async def check_active_events(self) -> Dict[str, bool]:
        """
        Check which events are currently active.

        Returns:
            Dictionary of event status
        """
        db = SessionLocal()

        try:
            now = datetime.utcnow()

            active = db.query(EventStatus).filter(
                EventStatus.active == True,
                EventStatus.start_date <= now,
                EventStatus.end_date >= now
            ).all()

            events = {}

            for event in active:
                event_type = event.event_type.lower()
                events[event_type] = {
                    'active': True,
                    'start': event.start_date.isoformat() if event.start_date else None,
                    'end': event.end_date.isoformat() if event.end_date else None,
                    'description': event.description
                }

                logger.info(f"Active event detected: {event_type}")

            self.active_events = events
            self.last_check = datetime.utcnow()

            return events

        except Exception as e:
            logger.error(f"Error checking active events: {e}")
            return {}

        finally:
            db.close()

    def calculate_download_rate(self) -> float:
        """
        Calculate recommended download rate based on active events.

        Base rate: 1.0
        Freeleech event: 2.0x (download more)
        Bonus event: 1.5x (download more)
        Multiplier event: 0.8x (focus on seeding)

        Returns:
            Download rate multiplier
        """
        rate_multiplier = 1.0

        # Apply event impacts
        if self.active_events.get('freeleech'):
            rate_multiplier *= self.EVENT_IMPACTS['freeleech']['download_rate_multiplier']

        if self.active_events.get('bonus'):
            rate_multiplier *= self.EVENT_IMPACTS['bonus']['download_rate_multiplier']

        if self.active_events.get('multiplier'):
            rate_multiplier *= self.EVENT_IMPACTS['multiplier']['download_rate_multiplier']

        logger.debug(f"Calculated download rate multiplier: {rate_multiplier}")

        return rate_multiplier

    def get_quality_threshold(self) -> int:
        """
        Get recommended quality threshold based on active events.

        Returns:
            Minimum quality score (0-100)
        """
        # Start with standard threshold
        threshold = 60

        # Freeleech allows lower quality
        if self.active_events.get('freeleech'):
            threshold = min(threshold, 40)

        # Bonus allows standard quality
        if self.active_events.get('bonus'):
            threshold = min(threshold, 60)

        # Multiplier demands higher quality
        if self.active_events.get('multiplier'):
            threshold = max(threshold, 70)

        logger.debug(f"Quality threshold: {threshold}")

        return threshold

    async def adjust_download_strategy(self) -> Dict[str, any]:
        """
        Adjust download strategy based on active events.

        Returns:
            Strategy adjustments
        """
        await self.check_active_events()

        strategy = {
            'download_rate': self.calculate_download_rate(),
            'quality_threshold': self.get_quality_threshold(),
            'active_events': list(self.active_events.keys()),
            'recommendations': []
        }

        # Generate recommendations
        if self.active_events.get('freeleech'):
            strategy['recommendations'].append(
                'Freeleech active: Increase downloads, lower quality threshold'
            )

        if self.active_events.get('bonus'):
            strategy['recommendations'].append(
                'Bonus event: Prioritize high-point releases'
            )

        if self.active_events.get('multiplier'):
            strategy['recommendations'].append(
                'Multiplier active: Focus on seeding and upload'
            )

        if not self.active_events:
            strategy['recommendations'].append(
                'No events active: Use standard conservative strategy'
            )

        logger.info(f"Download strategy adjusted: {len(strategy['recommendations'])} recommendations")

        return strategy

    async def should_download_release(
        self,
        release_type: str,      # freeleech/free/paid
        quality_score: float,
        point_cost: int = 0
    ) -> Tuple[bool, str]:
        """
        Determine if a release should be downloaded based on events.

        Args:
            release_type: Type of release
            quality_score: Quality score 0-100
            point_cost: Bonus point cost

        Returns:
            Tuple of (should_download: bool, reason: str)
        """
        strategy = await self.adjust_download_strategy()

        # Always download freeleech
        if release_type == 'freeleech':
            return True, "Freeleech - always download"

        # Check quality threshold
        if quality_score < strategy['quality_threshold']:
            return False, f"Quality {quality_score} below threshold {strategy['quality_threshold']}"

        # During freeleech/bonus, be more aggressive
        if self.active_events.get('freeleech') or self.active_events.get('bonus'):
            return True, "Event active - aggressive downloading enabled"

        # During multiplier, be conservative on downloads
        if self.active_events.get('multiplier'):
            # Only download high-quality or free
            if release_type in ['free', 'free_leech']:
                return True, "Multiplier event - prioritizing free releases"
            elif quality_score >= 80:
                return True, "Multiplier event - high quality download"
            else:
                return False, "Multiplier event - focusing on seeding"

        # Default behavior
        if release_type == 'free':
            return True, "Free release"
        elif release_type == 'paid' and quality_score >= 70:
            return True, "High quality paid release"
        else:
            return False, "Standard conservative threshold not met"

    def get_event_summary(self) -> Dict:
        """Get summary of current event status."""
        summary = {
            'timestamp': datetime.utcnow().isoformat(),
            'active_events': self.active_events,
            'event_count': len(self.active_events),
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'download_rate': self.calculate_download_rate(),
            'quality_threshold': self.get_quality_threshold()
        }

        return summary

    async def log_event_impact(self, event_type: str, action: str) -> None:
        """Log the impact of an event on system behavior."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': event_type,
            'action': action
        }

        self.event_history.append(log_entry)

        logger.info(f"Event impact: {event_type} -> {action}")

    def get_event_history(self, limit: int = 100) -> List[Dict]:
        """Get event history."""
        return self.event_history[-limit:]
