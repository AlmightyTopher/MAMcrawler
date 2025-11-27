"""
SQLAlchemy ORM model for Tasks table
Tracks execution history of all scheduled jobs
"""

from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, JSON, Index, func, Float, Boolean
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

    # VIP Management fields (for VIP renewal tasks)
    vip_status = Column(String(100), nullable=True)  # active, expired, pending_renewal
    vip_expiry_date = Column(TIMESTAMP, nullable=True)
    renewal_decision = Column(String(100), nullable=True)  # renewed, skipped, failed, blocked_ratio_emergency, blocked_low_points
    point_balance = Column(Integer, nullable=True)  # Points available at task execution
    renewal_cost = Column(Integer, nullable=True)  # Cost of VIP renewal

    # Category sync fields (for rule cache updates)
    rules_updated = Column(Integer, nullable=True)  # Count of categories updated

    # Pending items fields (for VIP pending item processing)
    pending_items_processed = Column(Integer, nullable=True)  # Count of pending items processed

    # Ratio emergency fields (for ratio monitoring tasks)
    current_ratio = Column(Float, nullable=True)  # Ratio at task execution
    emergency_active = Column(Boolean, default=False, nullable=False)  # Whether emergency freeze was triggered

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, name={self.task_name}, status={self.status}, processed={self.items_processed})>"
