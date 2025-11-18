"""
SQLAlchemy ORM model for GenreSetting table
Tracks enabled/disabled genres for Top-10 discovery feature
"""

from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, func
from datetime import datetime

from backend.database import Base


class GenreSetting(Base):
    """
    GenreSetting model representing genre preferences for Top-10 discovery

    Attributes:
        id: Primary key
        genre_name: Genre name (unique)
        is_enabled: Whether genre is enabled for Top-10 discovery
        priority: Priority order for processing (higher = first)
        date_created: When setting was created
        date_updated: Last update timestamp
    """

    __tablename__ = "genre_settings"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Genre info
    genre_name = Column(String(255), nullable=False, unique=True, index=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=0, nullable=False)

    # Timestamps
    date_created = Column(TIMESTAMP, default=func.now())
    date_updated = Column(TIMESTAMP, default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        status = "enabled" if self.is_enabled else "disabled"
        return f"<GenreSetting(id={self.id}, genre={self.genre_name}, {status})>"
