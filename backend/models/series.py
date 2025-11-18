"""
SQLAlchemy ORM model for Series table
Tracks all series in library and their completion status
"""

from sqlalchemy import Column, Integer, String, TIMESTAMP, Index, func
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.database import Base


class Series(Base):
    """
    Series model representing book series in the library

    Attributes:
        id: Primary key
        name: Series name (unique)
        author: Series author
        goodreads_id: Goodreads series ID for external lookups
        total_books_in_series: Total books in series per Goodreads
        books_owned: Number of books currently owned
        books_missing: Number of books missing from series
        completion_percentage: % of series owned (0-100)
        last_completion_check: Last time series was checked
        completion_status: Current status (complete, partial, incomplete)
        date_created: When series was added
        date_updated: Last update timestamp
    """

    __tablename__ = "series"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Series info
    name = Column(String(500), nullable=False, unique=True, index=True)
    author = Column(String(500), nullable=True)

    # External IDs
    goodreads_id = Column(String(255), nullable=True, index=True)

    # Series counts
    total_books_in_series = Column(Integer, nullable=True)
    books_owned = Column(Integer, default=0)
    books_missing = Column(Integer, default=0)
    completion_percentage = Column(Integer, default=0)

    # Tracking
    last_completion_check = Column(TIMESTAMP, nullable=True)
    completion_status = Column(String(100), nullable=True, index=True)

    # Timestamps
    date_created = Column(TIMESTAMP, default=func.now())
    date_updated = Column(TIMESTAMP, default=func.now(), onupdate=func.now())

    # Relationships
    missing_books = relationship("MissingBook", back_populates="series")

    def __repr__(self) -> str:
        return f"<Series(id={self.id}, name={self.name}, completion={self.completion_percentage}%)>"
