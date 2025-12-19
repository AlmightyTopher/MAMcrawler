"""
SQLAlchemy ORM model for Hardcover User Mappings
Migrated from hardcover_user_sync.db SQLite to Postgres
"""

from sqlalchemy import Column, String, TIMESTAMP, Boolean, func
from datetime import datetime

from backend.database import Base


class HardcoverUserMapping(Base):
    """
    Hardcover User Mapping model for syncing ABS users with Hardcover accounts.

    Migrated from SQLite hardcover_user_sync.db to Postgres for consolidated state management.

    Attributes:
        abs_user_id: Audiobookshelf user ID (primary key)
        abs_username: Audiobookshelf username
        hardcover_token: Hardcover API token for this user
        last_synced_at: Last sync timestamp
        is_active: Whether this mapping is active
    """

    __tablename__ = "hardcover_user_mappings"

    # Primary key
    abs_user_id = Column(String(255), primary_key=True, index=True)

    # User info
    abs_username = Column(String(255), nullable=True)
    hardcover_token = Column(String(500), nullable=True)

    # Sync tracking
    last_synced_at = Column(TIMESTAMP, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<HardcoverUserMapping(abs_user_id={self.abs_user_id}, username={self.abs_username}, active={self.is_active})>"
