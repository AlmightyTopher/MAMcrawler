"""
Series Service - Business logic for series operations
Handles series tracking, completion status, and book counts
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
import logging

from backend.models.series import Series
from backend.models.book import Book

logger = logging.getLogger(__name__)


class SeriesService:
    """
    Service layer for series operations

    Provides methods for managing series, tracking completion status,
    and calculating book counts
    """

    @staticmethod
    def create_series(
        db: Session,
        name: str,
        author: Optional[str] = None,
        goodreads_id: Optional[str] = None,
        total_books: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new series record

        Args:
            db: Database session
            name: Series name (unique)
            author: Series author
            goodreads_id: Goodreads series ID
            total_books: Total books in series

        Returns:
            Dict with:
                - success: bool
                - data: Series object if successful
                - error: str if failed
                - series_id: int if successful
        """
        try:
            # Check if series already exists
            existing = db.query(Series).filter(Series.name == name).first()
            if existing:
                logger.warning(f"Series '{name}' already exists (ID: {existing.id})")
                return {
                    "success": False,
                    "error": f"Series '{name}' already exists",
                    "data": existing,
                    "series_id": existing.id
                }

            # Create new series
            series = Series(
                name=name,
                author=author,
                goodreads_id=goodreads_id,
                total_books_in_series=total_books
            )

            db.add(series)
            db.commit()
            db.refresh(series)

            # Calculate initial completion status
            SeriesService.update_completion_status(db, series.id)

            logger.info(f"Created series: {series.name} (ID: {series.id})")

            return {
                "success": True,
                "data": series,
                "series_id": series.id,
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error creating series '{name}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None,
                "series_id": None
            }

    @staticmethod
    def get_series(db: Session, series_id: int) -> Dict[str, Any]:
        """
        Get series by ID

        Args:
            db: Database session
            series_id: Series ID

        Returns:
            Dict with success, data (Series or None), error
        """
        try:
            series = db.query(Series).filter(Series.id == series_id).first()

            if not series:
                return {
                    "success": False,
                    "error": f"Series with ID {series_id} not found",
                    "data": None
                }

            return {
                "success": True,
                "data": series,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting series {series_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    @staticmethod
    def get_series_by_name(db: Session, name: str) -> Dict[str, Any]:
        """
        Get series by name (unique constraint)

        Args:
            db: Database session
            name: Series name

        Returns:
            Dict with success, data (Series or None), error
        """
        try:
            series = db.query(Series).filter(Series.name == name).first()

            if not series:
                return {
                    "success": False,
                    "error": f"Series '{name}' not found",
                    "data": None
                }

            return {
                "success": True,
                "data": series,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting series by name '{name}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    @staticmethod
    def search_series(db: Session, query: str) -> Dict[str, Any]:
        """
        Search series by name

        Args:
            db: Database session
            query: Search query string

        Returns:
            Dict with success, data (list of Series), count, error
        """
        try:
            search_pattern = f"%{query}%"

            series_list = db.query(Series).filter(
                Series.name.ilike(search_pattern)
            ).order_by(Series.name).all()

            return {
                "success": True,
                "data": series_list,
                "count": len(series_list),
                "error": None
            }

        except Exception as e:
            logger.error(f"Error searching series with query '{query}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0
            }

    @staticmethod
    def get_all_series(
        db: Session,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get paginated list of all series

        Args:
            db: Database session
            limit: Maximum results per page
            offset: Number of records to skip

        Returns:
            Dict with success, data (list of Series), total, page_info, error
        """
        try:
            # Get total count
            total = db.query(Series).count()

            # Get paginated results
            series_list = db.query(Series).order_by(
                Series.completion_percentage.desc(),
                Series.name
            ).limit(limit).offset(offset).all()

            return {
                "success": True,
                "data": series_list,
                "total": total,
                "page_info": {
                    "limit": limit,
                    "offset": offset,
                    "has_more": (offset + limit) < total
                },
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting all series: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "total": 0,
                "page_info": None
            }

    @staticmethod
    def update_series(
        db: Session,
        series_id: int,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update series fields

        Args:
            db: Database session
            series_id: Series ID
            updates: Dictionary of fields to update
                {
                    'name': str,
                    'author': str,
                    'goodreads_id': str,
                    'total_books_in_series': int
                }

        Returns:
            Dict with success, data (updated Series), changes_made, error
        """
        try:
            series = db.query(Series).filter(Series.id == series_id).first()

            if not series:
                return {
                    "success": False,
                    "error": f"Series with ID {series_id} not found",
                    "data": None,
                    "changes_made": {}
                }

            changes_made = {}

            # Update fields
            for key, value in updates.items():
                if hasattr(series, key):
                    old_value = getattr(series, key)
                    if old_value != value:
                        setattr(series, key, value)
                        changes_made[key] = {
                            "old": old_value,
                            "new": value
                        }

            # Update timestamp if changes were made
            if changes_made:
                series.date_updated = datetime.now()

            db.commit()
            db.refresh(series)

            # Recalculate completion status if total_books changed
            if 'total_books_in_series' in changes_made:
                SeriesService.update_completion_status(db, series_id)

            logger.info(f"Updated series {series_id}: {len(changes_made)} fields changed")

            return {
                "success": True,
                "data": series,
                "changes_made": changes_made,
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating series {series_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None,
                "changes_made": {}
            }

    @staticmethod
    def update_completion_status(db: Session, series_id: int) -> Dict[str, Any]:
        """
        Recalculate series completion status

        Counts books owned in the series and calculates completion percentage

        Args:
            db: Database session
            series_id: Series ID

        Returns:
            Dict with success, data (updated Series), stats, error
        """
        try:
            series = db.query(Series).filter(Series.id == series_id).first()

            if not series:
                return {
                    "success": False,
                    "error": f"Series with ID {series_id} not found",
                    "data": None,
                    "stats": None
                }

            # Count books in series from books table
            books_owned = db.query(Book).filter(
                Book.series == series.name,
                Book.status == "active"
            ).count()

            series.books_owned = books_owned

            # Calculate missing and percentage
            if series.total_books_in_series:
                series.books_missing = max(0, series.total_books_in_series - books_owned)
                series.completion_percentage = int(
                    (books_owned / series.total_books_in_series) * 100
                )
            else:
                series.books_missing = 0
                series.completion_percentage = 0

            # Update status
            if series.completion_percentage == 100:
                series.completion_status = "complete"
            elif series.completion_percentage >= 50:
                series.completion_status = "partial"
            else:
                series.completion_status = "incomplete"

            series.last_completion_check = datetime.now()

            db.commit()
            db.refresh(series)

            stats = {
                "books_owned": series.books_owned,
                "books_missing": series.books_missing,
                "total_books": series.total_books_in_series,
                "completion_percentage": series.completion_percentage,
                "completion_status": series.completion_status
            }

            logger.info(f"Updated completion for series {series_id}: {stats}")

            return {
                "success": True,
                "data": series,
                "stats": stats,
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating completion status for series {series_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None,
                "stats": None
            }

    @staticmethod
    def get_series_completion_summary(db: Session) -> Dict[str, Any]:
        """
        Get summary statistics for all series

        Returns:
            Dict with success, stats, error
        """
        try:
            # Count series by status
            complete = db.query(Series).filter(Series.completion_status == "complete").count()
            partial = db.query(Series).filter(Series.completion_status == "partial").count()
            incomplete = db.query(Series).filter(Series.completion_status == "incomplete").count()

            # Total series
            total_series = db.query(Series).count()

            # Average completion percentage
            avg_completion = db.query(func.avg(Series.completion_percentage)).scalar() or 0

            # Total books owned across all series
            total_books_owned = db.query(func.sum(Series.books_owned)).scalar() or 0

            # Total books missing across all series
            total_books_missing = db.query(func.sum(Series.books_missing)).scalar() or 0

            stats = {
                "total_series": total_series,
                "complete": complete,
                "partial": partial,
                "incomplete": incomplete,
                "average_completion_percentage": round(avg_completion, 2),
                "total_books_owned": total_books_owned,
                "total_books_missing": total_books_missing
            }

            return {
                "success": True,
                "stats": stats,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting series completion summary: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "stats": None
            }

    @staticmethod
    def delete_series(db: Session, series_id: int) -> Dict[str, Any]:
        """
        Delete series (hard delete - use with caution)

        Args:
            db: Database session
            series_id: Series ID

        Returns:
            Dict with success, message, error
        """
        try:
            series = db.query(Series).filter(Series.id == series_id).first()

            if not series:
                return {
                    "success": False,
                    "error": f"Series with ID {series_id} not found",
                    "message": None
                }

            series_name = series.name

            db.delete(series)
            db.commit()

            logger.info(f"Deleted series {series_id}: {series_name}")

            return {
                "success": True,
                "message": f"Series '{series_name}' deleted",
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting series {series_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": None
            }
