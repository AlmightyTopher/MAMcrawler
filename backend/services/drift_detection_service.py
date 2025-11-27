"""
DriftDetectionService - Monthly Metadata Drift Correction
Detects and corrects metadata drift from Goodreads and external sources
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging

from backend.models.book import Book
from backend.models.metadata_correction import MetadataCorrection
from backend.database import SessionLocal

logger = logging.getLogger(__name__)


class DriftDetectionService:
    """
    Service for monthly metadata drift detection and correction.

    Implements GAP 3: Compare stored metadata against Goodreads data
    and auto-correct when drift is detected.

    Fields that can be updated:
    - series_name, series_order
    - description
    - cover_url
    - published_year, publisher
    - language

    Protected fields (never overwritten):
    - title (verified from audio scan)
    - narrator (detected from speech-to-text)
    - duration_minutes (verified from audio)
    """

    # Fields that can be updated
    UPDATABLE_FIELDS = {
        'series': 'Series Information',
        'series_order': 'Series Order',
        'description': 'Description',
        'cover_url': 'Cover Art URL',
        'published_year': 'Publication Year',
        'publisher': 'Publisher',
        'language': 'Language'
    }

    # Fields that cannot be overwritten (verified data)
    PROTECTED_FIELDS = {
        'title': 'Title (verified from audio scan)',
        'narrator': 'Narrator (detected from audio)',
        'duration_minutes': 'Duration (verified from audio)'
    }

    def __init__(self, db_session: Session):
        self.db = db_session

    async def detect_drift_for_book(
        self,
        book_id: int,
        external_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        GAP 3 IMPLEMENTATION: Detect metadata drift for a single book.

        Compares stored metadata against external source (Goodreads).

        Args:
            book_id: Book ID
            external_data: External metadata dict (optional, would fetch if not provided)

        Returns:
            {
                "book_id": int,
                "drifted_fields": [str],
                "changes": {
                    "field_name": {
                        "old_value": "...",
                        "new_value": "...",
                        "source": "goodreads",
                        "change_type": "updated" | "new" | "removed"
                    }
                },
                "drift_detected": bool
            }
        """
        try:
            book = self.db.query(Book).get(book_id)
            if not book:
                return {
                    "book_id": book_id,
                    "drift_detected": False,
                    "error": "Book not found"
                }

            # Check if metadata is old enough to warrant refresh
            if not self._should_refresh(book):
                return {
                    "book_id": book_id,
                    "drift_detected": False,
                    "reason": "Metadata too recent (< 30 days)"
                }

            logger.info(f"GAP 3: Checking drift for book {book_id}: {book.title}")

            # Fetch latest external data (in real implementation, from Goodreads)
            if not external_data:
                external_data = await self._fetch_external_data(book)

            if not external_data:
                return {
                    "book_id": book_id,
                    "drift_detected": False,
                    "reason": "External metadata not available"
                }

            # Compare fields
            drift_report = {
                "book_id": book_id,
                "book_title": book.title,
                "drifted_fields": [],
                "changes": {},
                "drift_detected": False
            }

            # Check each updatable field
            for field_name, display_name in self.UPDATABLE_FIELDS.items():
                current_value = getattr(book, field_name, None)
                new_value = external_data.get(field_name)

                if self._has_drifted(current_value, new_value):
                    drift_report["drifted_fields"].append(field_name)
                    drift_report["drift_detected"] = True
                    drift_report["changes"][field_name] = {
                        "old_value": current_value,
                        "new_value": new_value,
                        "source": "goodreads",
                        "change_type": self._classify_change(current_value, new_value)
                    }

                    logger.info(
                        f"GAP 3: Drift detected in {field_name} for book {book_id}: "
                        f"{current_value} -> {new_value}"
                    )

            return drift_report

        except Exception as e:
            logger.error(f"GAP 3: Error detecting drift for book {book_id}: {e}", exc_info=True)
            return {
                "book_id": book_id,
                "drift_detected": False,
                "error": str(e)
            }

    async def detect_drift_all_books(
        self,
        days_since_update: int = 30,
        limit: int = None
    ) -> List[Dict]:
        """
        GAP 3 IMPLEMENTATION: Detect drift for all books not updated in X days.

        Args:
            days_since_update: Only check books older than this (default 30 days)
            limit: Max books to check (default None = all)

        Returns:
            List of drift reports for books with detected drift
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_since_update)

            # Find books that haven't been updated recently
            query = self.db.query(Book).filter(
                (Book.metadata_last_updated < cutoff_date) |
                (Book.metadata_last_updated.is_(None))
            ).order_by(Book.metadata_last_updated)

            if limit:
                query = query.limit(limit)

            books_to_check = query.all()

            logger.info(f"GAP 3: Checking {len(books_to_check)} books for drift")

            drift_reports = []

            for book in books_to_check:
                try:
                    report = await self.detect_drift_for_book(book.id)
                    if report.get('drift_detected'):
                        drift_reports.append(report)
                except Exception as e:
                    logger.error(f"GAP 3: Drift detection failed for book {book.id}: {e}")

            logger.info(f"GAP 3: Found {len(drift_reports)} books with drift")

            return drift_reports

        except Exception as e:
            logger.error(f"GAP 3: Error in detect_drift_all_books: {e}", exc_info=True)
            return []

    async def apply_drift_corrections(
        self,
        drift_report: Dict[str, Any],
        auto_correct: bool = True
    ) -> Dict[str, Any]:
        """
        GAP 3 IMPLEMENTATION: Apply corrections from drift report.

        Protected fields are never overwritten.

        Args:
            drift_report: Report from detect_drift_for_book()
            auto_correct: If False, require manual approval

        Returns:
            {
                "book_id": int,
                "corrections_applied": int,
                "fields_updated": [str],
                "protected_fields_detected": [str],
                "timestamp": datetime
            }
        """
        try:
            book_id = drift_report['book_id']
            book = self.db.query(Book).get(book_id)

            if not book:
                return {
                    "book_id": book_id,
                    "error": "Book not found",
                    "corrections_applied": 0
                }

            corrections_applied = 0
            fields_updated = []
            protected_detected = []

            logger.info(f"GAP 3: Applying corrections for book {book_id}")

            for field_name, change_info in drift_report.get('changes', {}).items():
                # Verify field is not protected
                if field_name in self.PROTECTED_FIELDS:
                    logger.warning(
                        f"GAP 3: Attempted to update protected field '{field_name}' "
                        f"for book {book_id}. Change blocked."
                    )
                    protected_detected.append(field_name)
                    continue

                if auto_correct:
                    # Apply correction
                    new_value = change_info['new_value']
                    old_value = change_info['old_value']

                    try:
                        setattr(book, field_name, new_value)
                        corrections_applied += 1
                        fields_updated.append(field_name)

                        # Log the correction
                        MetadataService.create_correction(
                            db=self.db,
                            book_id=book_id,
                            field_name=field_name,
                            old_value=str(old_value) if old_value else None,
                            new_value=str(new_value) if new_value else None,
                            source="drift_correction",
                            reason=f"Auto-corrected drift from {change_info['source']}",
                            corrected_by="drift_correction_system"
                        )

                        logger.info(
                            f"GAP 3: Applied drift correction for '{field_name}' "
                            f"on book {book_id}"
                        )

                    except Exception as e:
                        logger.error(f"GAP 3: Error applying correction for {field_name}: {e}")

            # Update metadata timestamp
            if corrections_applied > 0:
                book.metadata_last_updated = datetime.utcnow()
                book.last_drift_correction = datetime.utcnow()
                book.drift_correction_count = (book.drift_correction_count or 0) + 1
                self.db.commit()

                logger.info(
                    f"GAP 3: Completed {corrections_applied} corrections for book {book_id}"
                )

            return {
                "book_id": book_id,
                "corrections_applied": corrections_applied,
                "fields_updated": fields_updated,
                "protected_fields_detected": protected_detected,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"GAP 3: Error applying drift corrections: {e}", exc_info=True)
            return {
                "book_id": drift_report.get('book_id'),
                "error": str(e),
                "corrections_applied": 0
            }

    def _should_refresh(self, book: Book) -> bool:
        """Check if book metadata is old enough to warrant refresh."""
        if not book.metadata_last_updated:
            return True

        age = datetime.utcnow() - book.metadata_last_updated
        return age > timedelta(days=30)

    async def _fetch_external_data(self, book: Book) -> Optional[Dict]:
        """
        Fetch external metadata (from Goodreads).

        In real implementation, would make API call to Goodreads.

        Args:
            book: Book object

        Returns:
            Dict with external metadata or None
        """
        try:
            logger.info(f"GAP 3: Would fetch external metadata for '{book.title}' from Goodreads")
            # In real implementation, would fetch from Goodreads API
            return None

        except Exception as e:
            logger.error(f"GAP 3: Error fetching external data: {e}")
            return None

    def _has_drifted(self, current_value, new_value) -> bool:
        """Check if value has drifted from current."""
        # None -> new value is drift
        if current_value is None and new_value is not None:
            return True

        # Different values is drift
        if str(current_value) != str(new_value):
            return True

        return False

    def _classify_change(self, old_value, new_value) -> str:
        """Classify the type of change."""
        if old_value is None:
            return "new"
        if new_value is None:
            return "removed"
        return "updated"


# Import for use in corrections
from backend.services.metadata_service import MetadataService
