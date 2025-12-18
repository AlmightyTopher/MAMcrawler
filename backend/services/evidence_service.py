"""
Evidence Service - Business logic for Voting-Based Evidence Model
Handles capturing raw evidence, generating assertions, and source management.
This service is currently in WRITE-ONLY Shadow Mode (does not update Book table).
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
import logging
import json

from backend.models.evidence import EvidenceSource, EvidenceEvent, Assertion
from backend.models.book import Book

logger = logging.getLogger(__name__)


# Resolution Method Weights
RESOLUTION_WEIGHTS = {
    "isbn_exact": 1.0,
    "exact": 0.8,
    "normalized": 0.7,
    "fuzzy": 0.5,
    "inferred": 0.3
}


class EvidenceService:
    """
    Service layer for Evidence Model operations.
    
    Responsibilities:
    1. Manage EvidenceSources (get or create).
    2. Record EvidenceEvents (raw payload logs).
    3. Generate and store Assertions (normalized claims).
    """

    @staticmethod
    def ensure_source(db: Session, name: str, default_modifier: float = 1.0) -> EvidenceSource:
        """
        Get an existing EvidenceSource or create a new one.
        
        Args:
            db: Database session
            name: Name of the source (e.g., 'GoogleBooks', 'Goodreads')
            default_modifier: Default trust multiplier for this source
            
        Returns:
            EvidenceSource object
        """
        try:
            source = db.query(EvidenceSource).filter(EvidenceSource.name == name).first()
            if not source:
                logger.info(f"Creating new EvidenceSource: {name}")
                source = EvidenceSource(name=name, default_modifier=default_modifier)
                db.add(source)
                db.commit()
                db.refresh(source)
            return source
        except Exception as e:
            db.rollback()
            logger.error(f"Error ensuring evidence source '{name}': {e}", exc_info=True)
            raise

    @staticmethod
    def record_event(
        db: Session,
        source_name: str,
        book_id: Optional[int],
        raw_payload: Dict[str, Any],
        request_context: Optional[str] = None
    ) -> EvidenceEvent:
        """
        Record a raw EvidenceEvent.
        
        Args:
            db: Database session
            source_name: Name of the source
            book_id: ID of the local Book entity (if known)
            raw_payload: The raw JSON response from the provider
            request_context: Optional string identifying the request (e.g. "search:Title")
            
        Returns:
            EvidenceEvent object
        """
        try:
            source = EvidenceService.ensure_source(db, source_name)
            
            event = EvidenceEvent(
                source_id=source.id,
                book_id=book_id,
                raw_payload=raw_payload
            )
            db.add(event)
            db.commit()
            db.refresh(event)
            return event
        except Exception as e:
            db.rollback()
            logger.error(f"Error recording evidence event from '{source_name}': {e}", exc_info=True)
            raise

    @staticmethod
    def create_assertions(
        db: Session,
        evidence_event_id: int,
        assertions_data: List[Dict[str, Any]]
    ) -> List[Assertion]:
        """
        Create multiple assertions from a single evidence event.
        
        Args:
            db: Database session
            evidence_event_id: ID of the parent EvidenceEvent
            assertions_data: List of dicts containing:
                - field: str
                - value: Any (will be JSON encoded)
                - resolution_method: str (default 'inferred')
                - resolution_weight: float (optional override)
                
        Returns:
            List of created Assertion objects
        """
        try:
            event = db.query(EvidenceEvent).get(evidence_event_id)
            if not event:
                raise ValueError(f"EvidenceEvent {evidence_event_id} not found")
            
            source = db.query(EvidenceSource).get(event.source_id)
            
            created_assertions = []
            
            for item in assertions_data:
                field = item.get('field')
                value = item.get('value')
                
                # Skip assertions with empty values
                if value is None or value == "":
                    continue
                
                resolution_method = item.get('resolution_method', 'inferred')
                
                # Calculate weights
                method_weight = RESOLUTION_WEIGHTS.get(resolution_method, 0.3)
                source_modifier = source.default_modifier
                final_weight = method_weight * source_modifier
                
                # Create fingerprint
                # For complex types (list/dict), sort to ensure consistent string rep
                if isinstance(value, (list, dict)):
                    value_fingerprint = str(json.dumps(value, sort_keys=True))
                else:
                    value_fingerprint = str(value).strip().lower()

                assertion = Assertion(
                    evidence_event_id=event.id,
                    book_id=event.book_id,
                    field=field,
                    value=value,
                    value_fingerprint=value_fingerprint,
                    resolution_method=resolution_method,
                    method_weight=method_weight,
                    source_modifier=source_modifier,
                    weight=final_weight
                )
                db.add(assertion)
                created_assertions.append(assertion)
            
            db.commit()
            return created_assertions
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating assertions for event {evidence_event_id}: {e}", exc_info=True)
            raise

    @staticmethod
    def ingest_evidence(
        db: Session,
        source_name: str,
        book_id: Optional[int],
        raw_payload: Dict[str, Any],
        normalized_data: Dict[str, Any],
        resolution_method: str = "inferred"
    ):
        """
        Convenience workflow: Record Event -> Create Assertions.
        
        Args:
            db: Session
            source_name: Source
            book_id: Local Book ID
            raw_payload: Raw API response
            normalized_data: Dictionary of {field: value} that was parsed from payload
            resolution_method: Method used to obtain this data (default 'inferred')
        """
        try:
            # 1. Record Event
            event = EvidenceService.record_event(db, source_name, book_id, raw_payload)
            
            # 2. Prepare Assertions
            assertions_payload = []
            for field, value in normalized_data.items():
                if value:
                    assertions_payload.append({
                        "field": field,
                        "value": value,
                        "resolution_method": resolution_method
                    })
            
            # 3. Create Assertions
            if assertions_payload:
                EvidenceService.create_assertions(db, event.id, assertions_payload)
                
            logger.info(f"Ingested evidence from {source_name} for book {book_id}: {len(assertions_payload)} assertions")
            
        except Exception as e:
            logger.error(f"Failed to ingest evidence from {source_name}: {e}")
            # Do not re-raise to avoid breaking the main application flow (Shadow Mode)
