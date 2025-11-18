"""
SQLAlchemy ORM model for Tasks table
Tracks execution history of all scheduled jobs
"""

from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, JSON, Index, func
from datetime import datetime

from backend.database import Base


class Task(Base):
    """
    Task model representing execution history of scheduled jobs

    Attributes:
        id: Primary key
        task_name: Name of the task (MAM, TOP10, METADATA_FULL, METADATA_NEW, SERIES, AUTHOR)
        scheduled_time: When task was scheduled to run
        actual_start: When task actually started
        actual_end: When task ended
        duration_seconds: Total execution time in seconds
        status: Task status (scheduled, running, completed, failed)
        items_processed: Total items processed
        items_succeeded: Number of successful items
        items_failed: Number of failed items
        log_output: Full log output from task execution
        error_message: Error message if task failed
        metadata: Task-specific metadata (JSON)
        date_created: When task record was created

    Note:
        This table has a 1-month retention policy. Records older than 30 days
        should be automatically deleted via scheduled cleanup job.
    """

    __tablename__ = "tasks"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Task identification
    task_name = Column(String(100), nullable=False, index=True)  # MAM, TOP10, METADATA_FULL, METADATA_NEW, SERIES, AUTHOR

    # Scheduling
    scheduled_time = Column(TIMESTAMP, nullable=True, index=True)
    actual_start = Column(TIMESTAMP, nullable=True)
    actual_end = Column(TIMESTAMP, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Status
    status = Column(String(100), nullable=False, index=True)  # scheduled, running, completed, failed

    # Results
    items_processed = Column(Integer, default=0)
    items_succeeded = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)

    # Logging
    log_output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Details for context
    task_metadata = Column(JSON, default={})  # Task-specific metadata

    # Timestamps
    date_created = Column(TIMESTAMP, default=func.now(), index=True)

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, name={self.task_name}, status={self.status}, processed={self.items_processed})>"
