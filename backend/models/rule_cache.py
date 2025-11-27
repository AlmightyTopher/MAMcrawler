"""
SQLAlchemy ORM model for RuleCache table
Caches MAM category rules scraped daily for freeleech and bonus events
"""

from sqlalchemy import Column, Integer, String, Boolean, JSON, TIMESTAMP, Index, func
from datetime import datetime

from backend.database import Base


class RuleCache(Base):
    """
    RuleCache model representing cached MAM category rules

    Purpose: Store daily-scraped MAM category rules to track freeleech events,
    bonus point multipliers, and other category-specific rules. Reduces API calls
    and enables trend analysis.

    Attributes:
        id: Primary key
        category_name: MAM category name (e.g., "Fantasy", "Science Fiction") - UNIQUE
        freeleech_active: Whether freeleech is currently active for this category
        freeleech_percent: Freeleech percentage (0-100, where 100 = fully free)
        bonus_event_active: Whether a bonus point event is currently active
        bonus_event_name: Name of the bonus event (e.g., "Double Points Weekend")
        rule_data: Full rule details as JSON (extensible for future rule types)
        last_checked: When rules were last scraped from MAM
        last_updated: When cache record was last modified (auto-updated)

    Indexes:
        - category_name (UNIQUE) - Fast lookups by category
        - last_checked - Find stale entries for refresh
    """

    __tablename__ = "rule_cache"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Category identification
    category_name = Column(String(255), nullable=False, unique=True, index=True)

    # Freeleech tracking
    freeleech_active = Column(Boolean, default=False, nullable=False)
    freeleech_percent = Column(Integer, default=0, nullable=False)  # 0-100

    # Bonus event tracking
    bonus_event_active = Column(Boolean, default=False, nullable=False)
    bonus_event_name = Column(String(255), nullable=True)

    # Full rule data (extensible)
    rule_data = Column(JSON, default={})  # Store complete rule details for future extensibility

    # Timestamps
    last_checked = Column(TIMESTAMP, nullable=False, default=func.now(), index=True)
    last_updated = Column(TIMESTAMP, nullable=False, default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return (
            f"<RuleCache(id={self.id}, category={self.category_name}, "
            f"freeleech_active={self.freeleech_active}, "
            f"bonus_active={self.bonus_event_active})>"
        )

    def is_stale(self, max_age_hours: int = 24) -> bool:
        """
        Check if rule cache is stale and needs refresh

        Args:
            max_age_hours: Maximum age in hours before cache is considered stale

        Returns:
            True if cache needs refresh, False otherwise
        """
        if not self.last_checked:
            return True

        age = datetime.utcnow() - self.last_checked
        return age.total_seconds() > (max_age_hours * 3600)
