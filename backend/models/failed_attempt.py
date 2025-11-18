"""
SQLAlchemy ORM model for Failed Attempts table
PERMANENT tally of all failures (never deleted) for analytics
"""

from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, JSON, Index, func
from datetime import datetime

from backend.database import Base


class FailedAttempt(Base):
    """
    Failed Attempt model representing permanent record of all failures

    Attributes:
        id: Primary key
        task_name: Task that failed (MAM, TOP10, METADATA_FULL, METADATA_NEW, SERIES, AUTHOR, DOWNLOAD)
        item_id: ID of the item that failed (book_id, series_id, etc.)
        item_name: Name/title of the failed item
        reason: Why it failed (human-readable description)
        error_code: Machine-readable error code
        error_details: Full error details/stack trace
        first_attempt: When first attempt occurred
        last_attempt: When most recent attempt occurred
        attempt_count: Total number of attempts
        metadata: Additional metadata for analysis (JSON)
        created_at: When failure record was created

    Note:
        This table has PERMANENT retention - records are never deleted.
        Used for analytics and pattern detection in system failures.
    """

    __tablename__ = "failed_attempts"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Task identification
    task_name = Column(String(100), nullable=False, index=True)  # MAM, TOP10, METADATA_FULL, METADATA_NEW, SERIES, AUTHOR, DOWNLOAD

    # What failed
    item_id = Column(Integer, nullable=True, index=True)  # book_id or other relevant ID
    item_name = Column(String(500), nullable=True)

    # Why it failed
    reason = Column(String(500), nullable=False)
    error_code = Column(String(100), nullable=True)
    error_details = Column(Text, nullable=True)

    # Tracking
    first_attempt = Column(TIMESTAMP, nullable=True)
    last_attempt = Column(TIMESTAMP, nullable=False, index=True)
    attempt_count = Column(Integer, default=1, index=True)

    # Metadata for analysis
    attempt_metadata = Column(JSON, default={})

    # Timestamps
    created_at = Column(TIMESTAMP, default=func.now(), index=True)

    def __repr__(self) -> str:
        return f"<FailedAttempt(id={self.id}, task={self.task_name}, item={self.item_name}, attempts={self.attempt_count})>"
