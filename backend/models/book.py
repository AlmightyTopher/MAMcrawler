"""
SQLAlchemy ORM model for Books table
Represents all imported books with metadata completeness tracking
"""

from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, JSON, Index, func, Float
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.database import Base


class Book(Base):
    """
    Book model representing all discovered/imported audiobooks

    Attributes:
        id: Primary key
        abs_id: Audiobookshelf internal ID (unique)
        title: Book title
        author: Author name
        series: Series name
        series_number: Position in series (e.g., "3" or "3.5")
        isbn: ISBN identifier
        asin: Amazon Standard Identifier
        publisher: Publisher name
        published_year: Year of publication
        duration_minutes: Audiobook duration in minutes
        description: Book description/synopsis
        metadata_completeness_percent: Percentage of complete metadata (0-100)
        last_metadata_update: Last time metadata was updated
        metadata_source: JSONB mapping field → source (e.g., {"title": "GoogleBooks", "author": "Goodreads"})
        date_added: When book was added to library
        date_updated: Last update timestamp
        import_source: Where book came from (user_import, mam_scraper, series_completion, author_discovery)
        status: Current status (active, duplicate, archived)
    """

    __tablename__ = "books"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Identifiers
    abs_id = Column(String(255), unique=True, nullable=True, index=True)

    # Book metadata
    title = Column(String(500), nullable=False, index=True)
    author = Column(String(500), nullable=True, index=True)
    series = Column(String(500), nullable=True, index=True)
    series_number = Column(String(50), nullable=True)

    # External identifiers
    isbn = Column(String(50), nullable=True)
    asin = Column(String(50), nullable=True)

    # Publishing info
    publisher = Column(String(500), nullable=True)
    published_year = Column(Integer, nullable=True)

    # Media info
    duration_minutes = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)

    # Metadata tracking
    metadata_completeness_percent = Column(Integer, default=0)
    last_metadata_update = Column(TIMESTAMP, nullable=True)
    metadata_source = Column(JSON, default={})  # {"field": "source", ...}

    # Timestamps
    date_added = Column(TIMESTAMP, default=func.now(), index=True)
    date_updated = Column(TIMESTAMP, default=func.now(), onupdate=func.now())

    # Import tracking
    import_source = Column(String(100), nullable=True)

    # Status
    status = Column(String(50), default="active")

    # Phase 1: VIP Maintenance + Ratio Emergency tracking
    narrator = Column(String(255), nullable=True)
    quality_score = Column(Float, nullable=True)
    mam_rule_version = Column(Integer, nullable=True)
    duplicate_status = Column(String(50), default="none")  # none/inferior/superior_available

    # Relationships
    downloads = relationship("Download", back_populates="book")
    # missing_book_entries = relationship("MissingBook", back_populates="book")
    # metadata_corrections = relationship("MetadataCorrection", back_populates="book")

    def __repr__(self) -> str:
        return f"<Book(id={self.id}, title={self.title}, author={self.author})>"
