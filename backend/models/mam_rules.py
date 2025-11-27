"""
SQLAlchemy ORM model for MamRules table
Stores daily MAM rules scraping results with event detection
"""

from sqlalchemy import Column, Integer, TIMESTAMP, JSON, Text, Boolean, Index, func
from datetime import datetime

from backend.database import Base


class MamRules(Base):
    """
    MamRules model representing daily scraped MAM rules and events

    Attributes:
        rule_version: Primary key, incremented version number
        effective_date: When these rules became effective
        rules_json: Complete JSON cache of all 7 scraped MAM pages
        freeleech_active: Whether freeleech event is currently active
        bonus_event_active: Whether bonus points event is active
        multiplier_active: Whether multiplier event is active
        event_details: JSON with event information (dates, multipliers, etc.)
        created_at: When this rule version was created
    """

    __tablename__ = "mam_rules"

    # Primary key
    rule_version = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # Metadata
    effective_date = Column(TIMESTAMP, default=func.now(), index=True)
    created_at = Column(TIMESTAMP, default=func.now())

    # Full rules cache (all 7 MAM pages)
    rules_json = Column(Text, nullable=False)

    # Event flags
    freeleech_active = Column(Boolean, default=False)
    bonus_event_active = Column(Boolean, default=False)
    multiplier_active = Column(Boolean, default=False)

    # Event details
    event_details = Column(JSON, nullable=True)  # {
    #   "freeleech": {"active": true, "until": "2025-11-23T23:59:59Z"},
    #   "bonus": {"active": true, "multiplier": 2.0},
    #   "multiplier": {"active": false, "value": 1.0}
    # }

    def __repr__(self) -> str:
        return f"<MamRules(version={self.rule_version}, effective_date={self.effective_date}, freeleech={self.freeleech_active})>"
