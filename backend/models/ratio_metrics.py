"""
SQLAlchemy ORM model for RatioMetrics table
Tracks historical ratio and point generation metrics for analysis
"""

from sqlalchemy import Column, Integer, Float, Boolean, String, TIMESTAMP, Index, func
from datetime import datetime

from backend.database import Base


class RatioMetrics(Base):
    """
    RatioMetrics model representing historical ratio and point generation snapshots

    Purpose: Store periodic snapshots of MAM account metrics to enable:
    - Ratio trend analysis (identify decline before emergency)
    - Upload/download bandwidth tracking
    - Point earning/spending patterns
    - Emergency event tracking and impact analysis

    Attributes:
        id: Primary key
        timestamp: When snapshot was taken
        global_ratio: Overall upload/download ratio (e.g., 1.234)
        upload_rate_mbps: Current upload rate in megabits per second
        download_rate_mbps: Current download rate in megabits per second
        active_uploads: Count of currently seeding torrents
        active_downloads: Count of currently downloading torrents
        points_earned: Bonus points earned in this snapshot period
        points_spent: Bonus points spent in this snapshot period
        emergency_active: Whether ratio emergency freeze was active during snapshot
        notes: Optional notes about unusual conditions

    Indexes:
        - timestamp (DESC) - Most recent snapshots first
        - (emergency_active, timestamp) - Find all emergency periods
    """

    __tablename__ = "ratio_metrics"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Snapshot timing
    timestamp = Column(TIMESTAMP, nullable=False, default=func.now(), index=True)

    # Ratio metrics
    global_ratio = Column(Float, nullable=False)  # e.g., 1.234 (upload/download)

    # Bandwidth metrics
    upload_rate_mbps = Column(Float, default=0.0, nullable=False)
    download_rate_mbps = Column(Float, default=0.0, nullable=False)

    # Activity metrics
    active_uploads = Column(Integer, default=0, nullable=False)  # Seeding torrents
    active_downloads = Column(Integer, default=0, nullable=False)  # Downloading torrents

    # Point tracking
    points_earned = Column(Integer, default=0, nullable=False)  # Points earned in period
    points_spent = Column(Integer, default=0, nullable=False)  # Points spent in period

    # Emergency tracking
    emergency_active = Column(Boolean, default=False, nullable=False)

    # Notes
    notes = Column(String(1000), nullable=True)

    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_emergency_timestamp", "emergency_active", "timestamp"),
        Index("idx_timestamp_desc", "timestamp", postgresql_ops={"timestamp": "DESC"}),
    )

    def __repr__(self) -> str:
        return (
            f"<RatioMetrics(id={self.id}, timestamp={self.timestamp}, "
            f"ratio={self.global_ratio:.3f}, emergency={self.emergency_active})>"
        )

    def calculate_net_points(self) -> int:
        """
        Calculate net point change for this period

        Returns:
            Net points (earned - spent)
        """
        return self.points_earned - self.points_spent

    def is_ratio_declining(self, previous_ratio: float) -> bool:
        """
        Check if ratio has declined compared to previous snapshot

        Args:
            previous_ratio: Ratio from previous snapshot

        Returns:
            True if ratio has declined, False otherwise
        """
        if previous_ratio is None or previous_ratio == 0:
            return False
        return self.global_ratio < previous_ratio

    def get_bandwidth_utilization(self) -> dict:
        """
        Get bandwidth utilization summary

        Returns:
            Dict with upload/download rates and total bandwidth
        """
        return {
            "upload_mbps": self.upload_rate_mbps,
            "download_mbps": self.download_rate_mbps,
            "total_mbps": self.upload_rate_mbps + self.download_rate_mbps,
            "ratio_trend": "upload" if self.upload_rate_mbps > self.download_rate_mbps else "download"
        }
