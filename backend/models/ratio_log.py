"""
SQLAlchemy ORM model for RatioLog table
Tracks global ratio history and emergency status changes
"""

from sqlalchemy import Column, Integer, Float, Boolean, TIMESTAMP, Index, func
from datetime import datetime

from backend.database import Base


class RatioLog(Base):
    """
    RatioLog model tracking global ratio history and emergency events

    Attributes:
        id: Primary key
        timestamp: When this ratio was recorded
        global_ratio: Current global ratio (e.g., 1.85)
        emergency_active: Whether emergency freeze is active at this timestamp
        seeding_allocation: Number of active seeding slots at this time
    """

    __tablename__ = "ratio_log"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Ratio data
    timestamp = Column(TIMESTAMP, default=func.now(), index=True)
    global_ratio = Column(Float, nullable=False, index=True)

    # Emergency state
    emergency_active = Column(Boolean, default=False, index=True)
    seeding_allocation = Column(Integer, default=0)

    def __repr__(self) -> str:
        return f"<RatioLog(timestamp={self.timestamp}, ratio={self.global_ratio}, emergency={self.emergency_active})>"
