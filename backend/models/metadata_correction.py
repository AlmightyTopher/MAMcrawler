"""
SQLAlchemy ORM model for Metadata Corrections table
Tracks history of all metadata changes (1-month retention)
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP, Index, func
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.database import Base


class MetadataCorrection(Base):
    """
    Metadata Correction model representing history of metadata changes

    Attributes:
        id: Primary key
        book_id: Foreign key to books table
        field_name: Name of field that was corrected (title, author, series, etc.)
        old_value: Previous value
        new_value: New value
        source: Source of correction (GoogleBooks, Goodreads, Manual, Auto-corrected)
        reason: Reason for correction
        correction_date: When correction was made
        corrected_by: Username or 'system' if automated

    Relationships:
        book: Associated book that was corrected

    Note:
        This table has a 1-month retention policy. Records older than 30 days
        should be automatically deleted via scheduled cleanup job.
    """

    __tablename__ = "metadata_corrections"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign key
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)

    # Correction details
    field_name = Column(String(100), nullable=False, index=True)  # title, author, series, etc.
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)

    # Source of correction
    source = Column(String(100), nullable=False, index=True)  # GoogleBooks, Goodreads, Manual, Auto-corrected

    # Reason
    reason = Column(String(255), nullable=True)

    # Tracking
    correction_date = Column(TIMESTAMP, default=func.now(), index=True)
    corrected_by = Column(String(100), default="system")  # Username or 'system'

    # Relationships
    book = relationship("Book", back_populates="metadata_corrections")

    def __repr__(self) -> str:
        return f"<MetadataCorrection(id={self.id}, book_id={self.book_id}, field={self.field_name}, source={self.source})>"
