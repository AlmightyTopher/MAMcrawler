"""
SQLAlchemy ORM model for VIPPendingItem table
Tracks audiobooks wishlisted but not downloaded due to VIP/cost constraints
"""

from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, Index, func
from datetime import datetime

from backend.database import Base


class VIPPendingItem(Base):
    """
    VIPPendingItem model representing audiobooks awaiting VIP renewal or point availability

    Purpose: Track audiobooks user has wishlisted but cannot download yet due to:
    - VIP subscription expired (need freeleech access)
    - Insufficient bonus points for paid downloads
    - Quality verification in progress
    - Manual hold/waiting for better release

    Attributes:
        id: Primary key
        title: Audiobook title
        author: Author name
        mam_torrent_id: MAM torrent ID for this release
        added_date: When item was added to pending list
        priority: User-assigned priority (1-10, where 10 = highest priority)
        auto_download: If True, system will auto-download when affordable
        reason_pending: Why download is pending (awaiting_vip_renewal, awaiting_points, checking_quality, manual_hold)
        status: Current status (pending, downloaded, no_longer_available, cancelled)
        estimated_cost: Bonus points needed to download (0 if freeleech)
        notes: Optional user notes about this item

    Relationships:
        - Links to Download record via mam_torrent_id once purchased

    Indexes:
        - (status, auto_download) - Find items ready for auto-download
        - (added_date) - Sort by age for prioritization
    """

    __tablename__ = "vip_pending_items"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Book identification
    title = Column(String(500), nullable=False)
    author = Column(String(500), nullable=True)
    mam_torrent_id = Column(Integer, nullable=False, index=True)

    # Prioritization
    added_date = Column(TIMESTAMP, nullable=False, default=func.now(), index=True)
    priority = Column(Integer, default=5, nullable=False)  # 1-10 scale

    # Automation
    auto_download = Column(Boolean, default=True, nullable=False)

    # Status tracking
    reason_pending = Column(
        String(100),
        nullable=False,
        default="awaiting_vip_renewal"
    )  # awaiting_vip_renewal, awaiting_points, checking_quality, manual_hold
    status = Column(
        String(100),
        nullable=False,
        default="pending",
        index=True
    )  # pending, downloaded, no_longer_available, cancelled

    # Cost tracking
    estimated_cost = Column(Integer, default=0, nullable=False)  # Bonus points needed

    # Notes
    notes = Column(String(1000), nullable=True)

    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_status_auto_download", "status", "auto_download"),
    )

    def __repr__(self) -> str:
        return (
            f"<VIPPendingItem(id={self.id}, title={self.title}, "
            f"status={self.status}, priority={self.priority}, "
            f"auto_download={self.auto_download})>"
        )

    def can_auto_process(self) -> bool:
        """
        Check if item is eligible for automatic processing

        Returns:
            True if item should be processed by automation, False otherwise
        """
        return self.status == "pending" and self.auto_download

    def is_affordable(self, current_points: int) -> bool:
        """
        Check if user has enough points to download this item

        Args:
            current_points: User's current bonus point balance

        Returns:
            True if user can afford download, False otherwise
        """
        return current_points >= self.estimated_cost
