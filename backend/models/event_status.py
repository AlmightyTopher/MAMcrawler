"""
SQLAlchemy ORM model for EventStatus table
Tracks current and historical MAM events (freeleech, bonus, multiplier)
"""

from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, Boolean, Index, func
from datetime import datetime

from backend.database import Base


class EventStatus(Base):
    """
    EventStatus model tracking MAM events and their active periods

    Attributes:
        id: Primary key
        event_type: Type of event (freeleech/bonus/multiplier)
        start_date: When event starts
        end_date: When event ends
        active: Whether event is currently active
        description: Human-readable event description
    """

    __tablename__ = "event_status"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Event metadata
    event_type = Column(String(50), nullable=False, index=True)  # freeleech/bonus/multiplier
    start_date = Column(TIMESTAMP, nullable=False)
    end_date = Column(TIMESTAMP, nullable=False)
    active = Column(Boolean, default=True, index=True)
    description = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<EventStatus(type={self.event_type}, start={self.start_date}, end={self.end_date}, active={self.active})>"
