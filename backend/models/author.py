"""
SQLAlchemy ORM model for Authors table
Tracks all authors in library with external audiobook discovery
"""

from sqlalchemy import Column, Integer, String, TIMESTAMP, Index, func
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.database import Base


class Author(Base):
    """
    Author model representing authors in the library with completeness tracking

    Attributes:
        id: Primary key
        name: Author name (unique)
        hardcover_id: Hardcover author ID (primary metadata provider)
        goodreads_id: Goodreads author ID (legacy, RSS sync only)
        google_books_id: Google Books author ID for external lookups
        mam_author_id: MyAnonamouse author ID for external lookups
        total_audiobooks_external: Total audiobooks found in external sources
        audiobooks_owned: Number of audiobooks currently owned
        audiobooks_missing: Number of audiobooks missing from library
        last_completion_check: Last time author was checked for completeness
        completion_status: Current status (complete, partial, incomplete)
        date_created: When author was added to database
        date_updated: Last update timestamp

    Relationships:
        missing_books: List of books missing from this author's collection
    """

    __tablename__ = "authors"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Author info
    name = Column(String(500), nullable=False, unique=True, index=True)

    # External IDs for cross-platform searching (Hardcover is primary metadata provider)
    hardcover_id = Column(String(255), nullable=True, index=True)
    goodreads_id = Column(String(255), nullable=True, index=True)  # Legacy, used for RSS sync only
    google_books_id = Column(String(255), nullable=True)
    mam_author_id = Column(String(255), nullable=True)

    # Audiobook counts
    total_audiobooks_external = Column(Integer, nullable=True)  # Found in external sources
    audiobooks_owned = Column(Integer, default=0)
    audiobooks_missing = Column(Integer, default=0)

    # Author scanning
    last_completion_check = Column(TIMESTAMP, nullable=True, index=True)
    completion_status = Column(String(100), nullable=True)

    # Timestamps
    date_created = Column(TIMESTAMP, default=func.now())
    date_updated = Column(TIMESTAMP, default=func.now(), onupdate=func.now())

    # Relationships
    # missing_books = relationship("MissingBook", back_populates="author")

    def __repr__(self) -> str:
        return f"<Author(id={self.id}, name={self.name}, owned={self.audiobooks_owned}, missing={self.audiobooks_missing})>"
