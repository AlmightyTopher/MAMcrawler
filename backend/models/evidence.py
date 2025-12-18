"""
SQLAlchemy ORM models for Voting-Based Evidence System.

This module defines the schema for the Evidence Model, which tracks:
1. Sources of Truth (EvidenceSource)
2. Raw API interaction events (EvidenceEvent)
3. Normalized field-level claims (Assertion)
"""

from sqlalchemy import Column, Integer, String, Float, Text, Boolean, JSON, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import relationship

from backend.database import Base

class EvidenceSource(Base):
    """
    Registry of external systems that provide metadata evidence.
    
    Attributes:
        id: Primary key
        name: Unique name of the source (e.g., 'Goodreads', 'GoogleBooks')
        default_modifier: Base weight modifier for this source (e.g., 1.0, 0.5)
        notes: Human-readable description or notes
    """
    __tablename__ = "evidence_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    default_modifier = Column(Float, default=1.0)
    notes = Column(Text, nullable=True)

    # Relationships
    events = relationship("EvidenceEvent", back_populates="source")
    assertions = relationship("Assertion", back_populates="source")

    def __repr__(self):
        return f"<EvidenceSource(name={self.name}, modifier={self.default_modifier})>"


class EvidenceEvent(Base):
    """
    Audit log of a raw interaction with an Evidence Source.
    
    Captures the exact moment and payload received from an API, acting as
    the raw proof for any downstream Assertions.
    
    Attributes:
        id: Primary key
        book_id: The local Book ID this event relates to (optional if unresolved)
        source_id: The source that provided this evidence
        fetched_at: Timestamp when the data was retrieved
        request_fingerprint: Unique hash of the request (to detect duplicates)
        raw_payload: The exact JSON response from the external API
        status: 'ok' or 'error'
        error: Error details if status is 'error'
    """
    __tablename__ = "evidence_events"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    book_id = Column(Integer, ForeignKey("books.id"), nullable=True, index=True)
    source_id = Column(Integer, ForeignKey("evidence_sources.id"), nullable=False, index=True)

    # Data
    fetched_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    request_fingerprint = Column(String(255), nullable=True, index=True)
    raw_payload = Column(JSON, nullable=True)
    status = Column(String(50), default="ok")
    error = Column(JSON, nullable=True)

    # Relationships
    source = relationship("EvidenceSource", back_populates="events")
    # book = relationship("Book") # Relationship to be defined in Book model or here if needed, keeping minimal for now
    assertions = relationship("Assertion", back_populates="event")

    def __repr__(self):
        return f"<EvidenceEvent(id={self.id}, source_id={self.source_id}, status={self.status})>"


class Assertion(Base):
    """
    A specific, weighable claim about a single field on a book.
    
    An Assertion is the atomic unit of the Voting Model. It breaks down a 
    complex API response into individual facts (e.g., "Google Books claims Title is X").
    
    Attributes:
        id: Primary key
        book_id: The local Book ID being described
        source_id: The source making the claim
        evidence_event_id: The raw event that generated this claim
        field: The field being contested (e.g., 'title', 'isbn', 'published_year')
        value: The value being claimed (normalized for comparison)
        value_fingerprint: Hash/Normalized version of value for grouping identical votes
        resolution_method: How this value was derived (e.g., 'exact', 'fuzzy', 'isbn_exact')
        method_weight: Confidence score of the resolution method (0.0 - 1.0)
        source_modifier: Weight multiplier from the source
        weight: Final calculated weight (method_weight * source_modifier)
        is_human_override: If True, this assertion manually overrides all others
        is_active: If False, this assertion is ignored by the judge (soft delete)
        created_at: When this assertion was created
    """
    __tablename__ = "assertions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    book_id = Column(Integer, ForeignKey("books.id"), nullable=True, index=True)
    source_id = Column(Integer, ForeignKey("evidence_sources.id"), nullable=False, index=True)
    evidence_event_id = Column(Integer, ForeignKey("evidence_events.id"), nullable=False, index=True)

    # The Claim
    field = Column(String(100), nullable=False, index=True)
    value = Column(JSON, nullable=True) # Text or JSON supported
    value_fingerprint = Column(String(500), nullable=True, index=True)

    # The Logic
    resolution_method = Column(String(100), default="inferred")
    method_weight = Column(Float, default=0.0)
    source_modifier = Column(Float, default=1.0)
    weight = Column(Float, default=0.0)

    # Governance
    is_human_override = Column(Boolean, default=False, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=func.now())

    # Relationships
    source = relationship("EvidenceSource", back_populates="assertions")
    event = relationship("EvidenceEvent", back_populates="assertions")
    # book = relationship("Book") # Relationship to be defined in Book model or here if needed

    def __repr__(self):
        return f"<Assertion(field={self.field}, weight={self.weight}, value={str(self.value)[:30]})>"
