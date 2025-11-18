"""
SQLAlchemy ORM model for Downloads table
Tracks all download attempts (queued, in-progress, completed, failed)
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP, Index, func
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.database import Base


class Download(Base):
    """
    Download model representing all download attempts and their status

    Attributes:
        id: Primary key
        book_id: Foreign key to books table
        missing_book_id: Foreign key to missing_books table
        title: Book title
        author: Author name
        source: Where download came from (MAM, GoogleBooks, Goodreads, Manual)
        magnet_link: Magnet link for torrent
        torrent_url: URL to torrent file
        qbittorrent_hash: qBittorrent info hash for tracking
        qbittorrent_status: qBittorrent status (downloading, seeding, completed)
        status: Overall download status (queued, downloading, completed, failed, abandoned)
        retry_count: Number of retry attempts
        max_retries: Maximum allowed retries (default: 3)
        last_attempt: Last time download was attempted
        next_retry: When next retry should occur
        abs_import_status: Audiobookshelf import status (pending, imported, import_failed)
        abs_import_error: Error message if import failed
        date_queued: When download was queued
        date_completed: When download was completed

    Relationships:
        book: Associated book if it exists
        missing_book: Associated missing book entry
    """

    __tablename__ = "downloads"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=True, index=True)
    missing_book_id = Column(Integer, ForeignKey("missing_books.id", ondelete="CASCADE"), nullable=True)

    # Book metadata
    title = Column(String(500), nullable=False)
    author = Column(String(500), nullable=True)

    # Source & link
    source = Column(String(100), nullable=False, index=True)  # MAM, GoogleBooks, Goodreads, Manual
    magnet_link = Column(Text, nullable=True)
    torrent_url = Column(Text, nullable=True)

    # qBittorrent tracking
    qbittorrent_hash = Column(String(255), nullable=True, index=True)
    qbittorrent_status = Column(String(100), nullable=True)  # downloading, seeding, completed

    # Retry logic
    status = Column(String(100), nullable=False, default="queued", index=True)  # queued, downloading, completed, failed, abandoned
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    last_attempt = Column(TIMESTAMP, nullable=True)
    next_retry = Column(TIMESTAMP, nullable=True, index=True)

    # Audiobookshelf import
    abs_import_status = Column(String(100), nullable=True)  # pending, imported, import_failed
    abs_import_error = Column(Text, nullable=True)

    # Timestamps
    date_queued = Column(TIMESTAMP, default=func.now(), index=True)
    date_completed = Column(TIMESTAMP, nullable=True)

    # Relationships
    book = relationship("Book", back_populates="downloads")
    missing_book = relationship("MissingBook", back_populates="download", foreign_keys=[missing_book_id])

    def __repr__(self) -> str:
        return f"<Download(id={self.id}, title={self.title}, source={self.source}, status={self.status})>"
