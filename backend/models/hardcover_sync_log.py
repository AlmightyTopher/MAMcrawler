
"""
SQLAlchemy ORM model for Hardcover Sync Logs
Tracks history of synchronization between AudiobookShelf and Hardcover
"""

from sqlalchemy import Column, Integer, String, Text, Float, Boolean, TIMESTAMP, func
from sqlalchemy.orm import relationship
from backend.database import Base

class HardcoverSyncLog(Base):
    """
    Log entires for AudiobookShelf <-> Hardcover sync operations
    """
    __tablename__ = "hardcover_sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # ABS Info
    abs_item_id = Column(String(255), nullable=False, index=True)
    abs_title = Column(String(500), nullable=True)
    abs_author = Column(String(500), nullable=True)

    # Hardcover Info
    hardcover_id = Column(Integer, nullable=True)
    hardcover_title = Column(String(500), nullable=True)
    hardcover_author = Column(String(500), nullable=True)
    hardcover_series = Column(String(500), nullable=True)

    # Sync Details
    changes_made = Column(Text, nullable=True) # JSON or descriptive text
    confidence = Column(Float, nullable=True)
    resolution_method = Column(String(100), nullable=True)
    
    # Status
    synced_at = Column(TIMESTAMP, default=func.now(), index=True)
    requires_verification = Column(Boolean, default=False)
    
    def __repr__(self) -> str:
        return f"<HardcoverSyncLog(id={self.id}, abs_id={self.abs_item_id}, confidence={self.confidence})>"
