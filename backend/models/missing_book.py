"""
SQLAlchemy ORM model for Missing Books table
Tracks identified gaps in series/author completeness
"""

from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, Index, func
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.database import Base


class MissingBook(Base):
    """
    Missing Book model representing gaps in series or author completeness

    Attributes:
        id: Primary key
        book_id: Foreign key to books table (if book gets added later)
        series_id: Foreign key to series table
        author_id: Foreign key to authors table
        title: Book title
        author_name: Author name
        series_name: Series name
        series_number: Position in series (e.g., "3" or "3.5")
        reason_missing: Why this book is missing (series_gap, author_gap)
        isbn: ISBN identifier
        asin: Amazon Standard Identifier
        goodreads_id: Goodreads book ID
        identified_date: When gap was identified
        download_status: Current status (identified, queued, downloading, completed, failed)
        download_id: Foreign key to downloads table
        priority: Download priority (1=high, 2=medium, 3=low)

    Relationships:
        book: Associated book if it exists
        series: Associated series
        author: Associated author
        download: Associated download attempt
    """

    __tablename__ = "missing_books"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    book_id = Column(Integer, ForeignKey("books.id", ondelete="SET NULL"), nullable=True)
    series_id = Column(Integer, ForeignKey("series.id", ondelete="CASCADE"), nullable=True, index=True)
    author_id = Column(Integer, ForeignKey("authors.id", ondelete="CASCADE"), nullable=True, index=True)

    # Book metadata
    title = Column(String(500), nullable=False)
    author_name = Column(String(500), nullable=True)
    series_name = Column(String(500), nullable=True)
    series_number = Column(String(50), nullable=True)

    # Why it's missing
    reason_missing = Column(String(100), nullable=False)  # series_gap, author_gap

    # External source info
    isbn = Column(String(50), nullable=True)
    asin = Column(String(50), nullable=True)
    goodreads_id = Column(String(255), nullable=True)

    # Status tracking
    identified_date = Column(TIMESTAMP, default=func.now(), index=True)
    download_status = Column(String(100), default="identified", index=True)  # identified, queued, downloading, completed, failed
    download_id = Column(Integer, ForeignKey("downloads.id", ondelete="SET NULL"), nullable=True)

    # Priority
    priority = Column(Integer, default=1)  # 1 = high, 2 = medium, 3 = low

    # Relationships
    # book = relationship("Book", back_populates="missing_book_entries")
    # series = relationship("Series", back_populates="missing_books")
    # author = relationship("Author", back_populates="missing_books")
    # download = relationship("Download", foreign_keys=[download_id])

    def __repr__(self) -> str:
        return f"<MissingBook(id={self.id}, title={self.title}, reason={self.reason_missing}, status={self.download_status})>"
