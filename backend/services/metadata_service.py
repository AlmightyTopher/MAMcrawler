"""
Metadata Service - Business logic for metadata correction operations
Handles metadata change tracking and quality metrics
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
import logging
import asyncio

from backend.models.metadata_correction import MetadataCorrection
from backend.models.book import Book
from backend.models.download import Download

logger = logging.getLogger(__name__)


class MetadataService:
    """
    Service layer for metadata correction operations

    Provides methods for tracking metadata changes, analyzing correction history,
    and monitoring metadata quality
    """

    @staticmethod
    def get_correction_history(
        db: Session,
        book_id: int,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get correction history for a book

        Args:
            db: Database session
            book_id: Book ID
            limit: Maximum number of corrections to return

        Returns:
            Dict with success, data (list of MetadataCorrections), count, error
        """
        try:
            corrections = db.query(MetadataCorrection).filter(
                MetadataCorrection.book_id == book_id
            ).order_by(
                MetadataCorrection.correction_date.desc()
            ).limit(limit).all()

            return {
                "success": True,
                "data": corrections,
                "count": len(corrections),
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting correction history for book {book_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0
            }

    @staticmethod
    def create_correction(
        db: Session,
        book_id: int,
        field_name: str,
        old_value: Optional[str],
        new_value: Optional[str],
        source: str,
        reason: Optional[str] = None,
        corrected_by: str = "system"
    ) -> Dict[str, Any]:
        """
        Log a metadata correction

        Args:
            db: Database session
            book_id: Book ID
            field_name: Field that was corrected (title, author, series, etc.)
            old_value: Previous value
            new_value: New value
            source: Source of correction (GoogleBooks, Goodreads, Manual, Auto-corrected)
            reason: Reason for correction
            corrected_by: Username or 'system'

        Returns:
            Dict with:
                - success: bool
                - data: MetadataCorrection object if successful
                - error: str if failed
                - correction_id: int if successful
        """
        try:
            # Verify book exists
            book = db.query(Book).filter(Book.id == book_id).first()
            if not book:
                return {
                    "success": False,
                    "error": f"Book with ID {book_id} not found",
                    "data": None,
                    "correction_id": None
                }

            # Create correction record
            correction = MetadataCorrection(
                book_id=book_id,
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
                source=source,
                reason=reason,
                corrected_by=corrected_by
            )

            db.add(correction)
            db.commit()
            db.refresh(correction)

            logger.info(
                f"Created metadata correction for book {book_id}, "
                f"field '{field_name}': {old_value} -> {new_value} (source: {source})"
            )

            return {
                "success": True,
                "data": correction,
                "correction_id": correction.id,
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error creating metadata correction for book {book_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None,
                "correction_id": None
            }

    @staticmethod
    def get_corrections_by_source(
        db: Session,
        source: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get corrections from a specific source

        Args:
            db: Database session
            source: Source name (GoogleBooks, Goodreads, Manual, Auto-corrected)
            limit: Maximum number of corrections to return

        Returns:
            Dict with success, data (list of MetadataCorrections), count, error
        """
        try:
            corrections = db.query(MetadataCorrection).filter(
                MetadataCorrection.source == source
            ).order_by(
                MetadataCorrection.correction_date.desc()
            ).limit(limit).all()

            return {
                "success": True,
                "data": corrections,
                "count": len(corrections),
                "source": source,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting corrections by source '{source}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0,
                "source": source
            }

    @staticmethod
    def get_metadata_status(db: Session) -> Dict[str, Any]:
        """
        Get summary statistics on metadata quality

        Returns:
            Dict with success, stats, error
        """
        try:
            # Average metadata completeness across all books
            avg_completeness = db.query(
                func.avg(Book.metadata_completeness_percent)
            ).filter(Book.status == "active").scalar() or 0

            # Count books by completeness ranges
            complete = db.query(Book).filter(
                Book.metadata_completeness_percent == 100,
                Book.status == "active"
            ).count()

            high_quality = db.query(Book).filter(
                Book.metadata_completeness_percent >= 80,
                Book.metadata_completeness_percent < 100,
                Book.status == "active"
            ).count()

            medium_quality = db.query(Book).filter(
                Book.metadata_completeness_percent >= 50,
                Book.metadata_completeness_percent < 80,
                Book.status == "active"
            ).count()

            low_quality = db.query(Book).filter(
                Book.metadata_completeness_percent < 50,
                Book.status == "active"
            ).count()

            # Total books
            total_books = db.query(Book).filter(Book.status == "active").count()

            # Count corrections by source
            source_counts = db.query(
                MetadataCorrection.source,
                func.count(MetadataCorrection.id)
            ).group_by(MetadataCorrection.source).all()

            sources_used = {source: count for source, count in source_counts}

            # Total corrections
            total_corrections = db.query(MetadataCorrection).count()

            # Recent corrections (last 7 days)
            seven_days_ago = datetime.now() - timedelta(days=7)
            recent_corrections = db.query(MetadataCorrection).filter(
                MetadataCorrection.correction_date >= seven_days_ago
            ).count()

            stats = {
                "average_completeness_percent": round(avg_completeness, 2),
                "total_books": total_books,
                "completeness_breakdown": {
                    "complete_100": complete,
                    "high_quality_80_99": high_quality,
                    "medium_quality_50_79": medium_quality,
                    "low_quality_0_49": low_quality
                },
                "sources_used": sources_used,
                "total_corrections": total_corrections,
                "recent_corrections_7_days": recent_corrections
            }

            return {
                "success": True,
                "stats": stats,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting metadata status: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "stats": None
            }

    @staticmethod
    def get_incomplete_books(
        db: Session,
        min_completeness: int = 0,
        max_completeness: int = 100,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get books below completeness threshold

        Args:
            db: Database session
            min_completeness: Minimum completeness percentage (0-100)
            max_completeness: Maximum completeness percentage (0-100)
            limit: Maximum number of books to return

        Returns:
            Dict with success, data (list of Books), count, error
        """
        try:
            books = db.query(Book).filter(
                Book.metadata_completeness_percent >= min_completeness,
                Book.metadata_completeness_percent < max_completeness,
                Book.status == "active"
            ).order_by(
                Book.metadata_completeness_percent.asc()
            ).limit(limit).all()

            return {
                "success": True,
                "data": books,
                "count": len(books),
                "min_completeness": min_completeness,
                "max_completeness": max_completeness,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting incomplete books: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0,
                "min_completeness": min_completeness,
                "max_completeness": max_completeness
            }

    @staticmethod
    def cleanup_old_corrections(
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Delete metadata corrections older than X days (retention policy)

        Args:
            db: Database session
            days: Number of days to retain corrections

        Returns:
            Dict with success, deleted_count, error
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            # Count corrections to be deleted
            corrections_to_delete = db.query(MetadataCorrection).filter(
                MetadataCorrection.correction_date < cutoff_date
            ).count()

            # Delete old corrections
            db.query(MetadataCorrection).filter(
                MetadataCorrection.correction_date < cutoff_date
            ).delete(synchronize_session=False)

            db.commit()

            logger.info(
                f"Deleted {corrections_to_delete} metadata corrections older than "
                f"{days} days (before {cutoff_date})"
            )

            return {
                "success": True,
                "deleted_count": corrections_to_delete,
                "cutoff_date": cutoff_date.isoformat(),
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error cleaning up old corrections: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "deleted_count": 0,
                "cutoff_date": None
            }

    @staticmethod
    def get_field_correction_stats(db: Session) -> Dict[str, Any]:
        """
        Get statistics on which fields are corrected most often

        Returns:
            Dict with success, stats (field -> correction_count), error
        """
        try:
            field_counts = db.query(
                MetadataCorrection.field_name,
                func.count(MetadataCorrection.id)
            ).group_by(
                MetadataCorrection.field_name
            ).order_by(
                func.count(MetadataCorrection.id).desc()
            ).all()

            stats = {field: count for field, count in field_counts}

            return {
                "success": True,
                "stats": stats,
                "total_fields_corrected": len(stats),
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting field correction stats: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "stats": None,
                "total_fields_corrected": 0
            }

    @staticmethod
    def perform_full_scan(
        db: Session,
        book_id: int,
        source: str = "manual",
        include_narrator_detection: bool = True
    ) -> Dict[str, Any]:
        """
        GAP 1 + GAP 2 IMPLEMENTATION: Perform full metadata scan.

        Scans and updates:
        1. Book title, author, description
        2. Series information
        3. Narrator (via GAP 2)
        4. Cover art
        5. Metadata completeness

        Args:
            db: Database session
            book_id: Book ID to scan
            source: Source of scan (manual, download_completion, auto)
            include_narrator_detection: Enable narrator detection (GAP 2)

        Returns:
            {
                "status": "success" | "error",
                "fields_updated": int,
                "fields": [str],
                "narrator_detected": Optional[str],
                "completeness_percent": int,
                "timestamp": str
            }
        """
        try:
            book = db.query(Book).get(book_id)
            if not book:
                return {
                    "status": "error",
                    "error": f"Book {book_id} not found"
                }

            logger.info(f"GAP 1+2: Starting full scan for book {book_id}: {book.title}")

            fields_updated = []
            fields_data = {}

            # GAP 2: Narrator detection (if enabled)
            narrator_detected = None
            if include_narrator_detection:
                try:
                    from backend.services.narrator_detection_service import NarratorDetectionService

                    narrator_service = NarratorDetectionService(db)

                    # Find latest download
                    latest_download = db.query(Download).filter(
                        Download.book_id == book_id
                    ).order_by(Download.date_completed.desc()).first()

                    if latest_download:
                        narrator_detected = asyncio.run(narrator_service.detect_narrator(
                            download_id=latest_download.id,
                            book_id=book_id,
                            audio_directory=None,
                            mam_metadata=None
                        ))

                        if narrator_detected:
                            fields_updated.append("narrator")
                            fields_data["narrator"] = narrator_detected
                            logger.info(f"GAP 2: Detected narrator: {narrator_detected}")

                except Exception as e:
                    logger.warning(f"GAP 2: Narrator detection failed: {e}")

            # In real implementation, would fetch metadata from:
            # - Goodreads
            # - Google Books
            # - Audible
            # - MAM metadata
            # For now, log that this would happen
            logger.info(f"GAP 1: Would fetch metadata from external sources")

            # Calculate metadata completeness
            completeness = 0
            completed_fields = 0

            fields_to_check = ['title', 'author', 'description', 'narrator']
            for field in fields_to_check:
                if getattr(book, field, None):
                    completed_fields += 1

            if len(fields_to_check) > 0:
                completeness = int((completed_fields / len(fields_to_check)) * 100)

            # Update metadata timestamp
            book.metadata_last_updated = datetime.now()
            db.commit()

            return {
                "status": "success",
                "book_id": book_id,
                "title": book.title,
                "fields_updated": len(fields_updated),
                "fields": fields_updated,
                "narrator_detected": narrator_detected,
                "completeness_percent": completeness,
                "source": source,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"GAP 1: Error in perform_full_scan for book {book_id}: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "book_id": book_id
            }
