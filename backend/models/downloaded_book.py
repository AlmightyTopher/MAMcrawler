"""
SQLAlchemy ORM model for Downloaded Books
Migrated from downloaded_books.db SQLite to Postgres
"""

from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, Float, Boolean, func
from datetime import datetime

from backend.database import Base


class DownloadedBook(Base):
    """
    Downloaded Book model representing books tracked through the download workflow.

    Migrated from SQLite downloaded_books.db to Postgres for consolidated state management.

    Attributes:
        id: Primary key
        title: Book title (unique)
        author: Author name
        genre: Genre classification
        magnet_link: Torrent magnet link
        status: Download status (queued, downloading, completed, failed)
        queued_time: When book was added to queue
        downloaded_time: When download completed
        added_to_abs_time: When added to Audiobookshelf
        estimated_value: Estimated storage value
        file_size: File size in bytes
        bitrate: Audio bitrate
        quality_check: Whether quality check passed
    """

    __tablename__ = "downloaded_books"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Book info
    title = Column(Text, nullable=False, unique=True, index=True)
    author = Column(Text, nullable=True)
    genre = Column(Text, nullable=True)

    # Download tracking
    magnet_link = Column(Text, nullable=True)
    status = Column(String(100), nullable=True, index=True)

    # Timestamps
    queued_time = Column(TIMESTAMP, nullable=True)
    downloaded_time = Column(TIMESTAMP, nullable=True)
    added_to_abs_time = Column(TIMESTAMP, nullable=True)

    # Quality metadata
    estimated_value = Column(Float, nullable=True)
    file_size = Column(Integer, nullable=True)
    bitrate = Column(Integer, nullable=True)
    quality_check = Column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<DownloadedBook(id={self.id}, title={self.title}, status={self.status})>"
