"""
Failed Attempt Service - Business logic for permanent failure tracking
Handles failure audit trail, analytics, and pattern detection (NEVER DELETED)
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
import logging

from backend.models.failed_attempt import FailedAttempt

logger = logging.getLogger(__name__)


class FailedAttemptService:
    """
    Service layer for failed attempt tracking

    Provides methods for recording failures, analyzing patterns,
    and maintaining a permanent audit trail

    IMPORTANT: Records in this table are NEVER deleted (permanent retention)
    """

    @staticmethod
    def record_failure(
        db: Session,
        task_name: str,
        item_id: Optional[int],
        item_name: str,
        reason: str,
        error_code: Optional[str] = None,
        error_details: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record a permanent failure

        Args:
            db: Database session
            task_name: Task that failed (MAM, TOP10, METADATA_FULL, METADATA_NEW, SERIES, AUTHOR, DOWNLOAD)
            item_id: ID of the item that failed (book_id, series_id, etc.)
            item_name: Name/title of the failed item
            reason: Why it failed (human-readable description)
            error_code: Machine-readable error code
            error_details: Full error details/stack trace
            metadata: Additional metadata for analysis (JSON)

        Returns:
            Dict with:
                - success: bool
                - data: FailedAttempt object if successful
                - error: str if failed
                - failure_id: int if successful
        """
        try:
            # Check if failure already exists for this item
            existing = db.query(FailedAttempt).filter(
                FailedAttempt.task_name == task_name,
                FailedAttempt.item_id == item_id,
                FailedAttempt.item_name == item_name
            ).first()

            if existing:
                # Update existing failure record
                existing.last_attempt = datetime.now()
                existing.attempt_count += 1
                existing.reason = reason
                existing.error_code = error_code
                existing.error_details = error_details

                if metadata:
                    existing.metadata = metadata
                    from sqlalchemy.orm.attributes import flag_modified
                    flag_modified(existing, "metadata")

                db.commit()
                db.refresh(existing)

                logger.warning(
                    f"Updated failure record {existing.id} for {task_name}: "
                    f"{item_name} (attempt #{existing.attempt_count})"
                )

                return {
                    "success": True,
                    "data": existing,
                    "failure_id": existing.id,
                    "error": None,
                    "is_new": False
                }

            # Create new failure record
            failure = FailedAttempt(
                task_name=task_name,
                item_id=item_id,
                item_name=item_name,
                reason=reason,
                error_code=error_code,
                error_details=error_details,
                first_attempt=datetime.now(),
                last_attempt=datetime.now(),
                attempt_count=1,
                metadata=metadata or {}
            )

            db.add(failure)
            db.commit()
            db.refresh(failure)

            logger.warning(
                f"Recorded new failure for {task_name}: {item_name} "
                f"(reason: {reason}, code: {error_code})"
            )

            return {
                "success": True,
                "data": failure,
                "failure_id": failure.id,
                "error": None,
                "is_new": True
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error recording failure for '{item_name}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None,
                "failure_id": None,
                "is_new": None
            }

    @staticmethod
    def get_failure_history(
        db: Session,
        item_id: int,
        task_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get all failure records for a specific item

        Args:
            db: Database session
            item_id: Item ID (book_id, series_id, etc.)
            task_name: Optional filter by task name

        Returns:
            Dict with success, data (list of FailedAttempts), count, error
        """
        try:
            query = db.query(FailedAttempt).filter(FailedAttempt.item_id == item_id)

            if task_name:
                query = query.filter(FailedAttempt.task_name == task_name)

            failures = query.order_by(FailedAttempt.last_attempt.desc()).all()

            return {
                "success": True,
                "data": failures,
                "count": len(failures),
                "item_id": item_id,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting failure history for item {item_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0,
                "item_id": item_id
            }

    @staticmethod
    def get_failures_by_task(
        db: Session,
        task_name: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get all failures for a specific task

        Args:
            db: Database session
            task_name: Task name (MAM, TOP10, METADATA_FULL, etc.)
            limit: Maximum number of failures to return

        Returns:
            Dict with success, data (list of FailedAttempts), count, error
        """
        try:
            failures = db.query(FailedAttempt).filter(
                FailedAttempt.task_name == task_name
            ).order_by(
                FailedAttempt.last_attempt.desc()
            ).limit(limit).all()

            return {
                "success": True,
                "data": failures,
                "count": len(failures),
                "task_name": task_name,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting failures for task '{task_name}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0,
                "task_name": task_name
            }

    @staticmethod
    def get_failure_summary(db: Session) -> Dict[str, Any]:
        """
        Get summary statistics on all failures

        Returns:
            Dict with success, stats, error
        """
        try:
            # Total failures
            total_failures = db.query(FailedAttempt).count()

            # Failures by task
            task_counts = db.query(
                FailedAttempt.task_name,
                func.count(FailedAttempt.id)
            ).group_by(FailedAttempt.task_name).all()

            failures_by_task = {task: count for task, count in task_counts}

            # Failures by error code
            error_counts = db.query(
                FailedAttempt.error_code,
                func.count(FailedAttempt.id)
            ).group_by(FailedAttempt.error_code).all()

            failures_by_error_code = {
                (code or "unknown"): count
                for code, count in error_counts
            }

            # Most problematic items (highest attempt count)
            problematic_items = db.query(FailedAttempt).order_by(
                FailedAttempt.attempt_count.desc()
            ).limit(10).all()

            problematic_list = [
                {
                    "item_name": item.item_name,
                    "task_name": item.task_name,
                    "attempt_count": item.attempt_count,
                    "last_attempt": item.last_attempt.isoformat() if item.last_attempt else None,
                    "reason": item.reason
                }
                for item in problematic_items
            ]

            # Recent failures (last 7 days)
            seven_days_ago = datetime.now() - timedelta(days=7)
            recent_failures = db.query(FailedAttempt).filter(
                FailedAttempt.last_attempt >= seven_days_ago
            ).count()

            # Total retry attempts
            total_attempts = db.query(
                func.sum(FailedAttempt.attempt_count)
            ).scalar() or 0

            stats = {
                "total_failures": total_failures,
                "failures_by_task": failures_by_task,
                "failures_by_error_code": failures_by_error_code,
                "total_retry_attempts": total_attempts,
                "recent_failures_7_days": recent_failures,
                "most_problematic_items": problematic_list
            }

            return {
                "success": True,
                "stats": stats,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting failure summary: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "stats": None
            }

    @staticmethod
    def increment_attempt_count(
        db: Session,
        failure_id: int
    ) -> Dict[str, Any]:
        """
        Increment attempt count for a failure

        Args:
            db: Database session
            failure_id: Failure record ID

        Returns:
            Dict with success, data (updated FailedAttempt), new_count, error
        """
        try:
            failure = db.query(FailedAttempt).filter(FailedAttempt.id == failure_id).first()

            if not failure:
                return {
                    "success": False,
                    "error": f"Failure record with ID {failure_id} not found",
                    "data": None,
                    "new_count": None
                }

            failure.attempt_count += 1
            failure.last_attempt = datetime.now()

            db.commit()
            db.refresh(failure)

            logger.info(f"Incremented attempt count for failure {failure_id} to {failure.attempt_count}")

            return {
                "success": True,
                "data": failure,
                "new_count": failure.attempt_count,
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error incrementing attempt count for failure {failure_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None,
                "new_count": None
            }

    @staticmethod
    def get_persistent_failures(
        db: Session,
        min_attempts: int = 3,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get persistent failures (items that failed multiple times)

        Args:
            db: Database session
            min_attempts: Minimum number of attempts to be considered persistent
            limit: Maximum number of failures to return

        Returns:
            Dict with success, data (list of FailedAttempts), count, error
        """
        try:
            failures = db.query(FailedAttempt).filter(
                FailedAttempt.attempt_count >= min_attempts
            ).order_by(
                FailedAttempt.attempt_count.desc(),
                FailedAttempt.last_attempt.desc()
            ).limit(limit).all()

            return {
                "success": True,
                "data": failures,
                "count": len(failures),
                "min_attempts": min_attempts,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting persistent failures: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0,
                "min_attempts": min_attempts
            }

    @staticmethod
    def get_failures_by_error_code(
        db: Session,
        error_code: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get all failures with a specific error code

        Args:
            db: Database session
            error_code: Error code to filter by
            limit: Maximum number of failures to return

        Returns:
            Dict with success, data (list of FailedAttempts), count, error
        """
        try:
            failures = db.query(FailedAttempt).filter(
                FailedAttempt.error_code == error_code
            ).order_by(
                FailedAttempt.last_attempt.desc()
            ).limit(limit).all()

            return {
                "success": True,
                "data": failures,
                "count": len(failures),
                "error_code": error_code,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting failures by error code '{error_code}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0,
                "error_code": error_code
            }

    @staticmethod
    def get_recent_failures(
        db: Session,
        hours: int = 24,
        task_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get recent failures within X hours

        Args:
            db: Database session
            hours: Number of hours to look back
            task_name: Optional filter by task name

        Returns:
            Dict with success, data (list of FailedAttempts), count, error
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            query = db.query(FailedAttempt).filter(
                FailedAttempt.last_attempt >= cutoff_time
            )

            if task_name:
                query = query.filter(FailedAttempt.task_name == task_name)

            failures = query.order_by(FailedAttempt.last_attempt.desc()).all()

            return {
                "success": True,
                "data": failures,
                "count": len(failures),
                "hours": hours,
                "cutoff_time": cutoff_time.isoformat(),
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting recent failures: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0,
                "hours": hours,
                "cutoff_time": None
            }
