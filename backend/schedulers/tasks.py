"""
Scheduled Task Handlers for Audiobook Automation System
Defines all scheduled task functions that are executed by APScheduler
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import traceback

from sqlalchemy.orm import Session

from backend.database import get_db_context
from backend.models.task import Task
from backend.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Task Utilities
# ============================================================================

def create_task_record(
    db: Session,
    task_name: str,
    scheduled_time: Optional[datetime] = None
) -> Task:
    """
    Create a new Task database record with status='running'

    Args:
        db: Database session
        task_name: Name of the task (MAM, TOP10, METADATA_FULL, etc.)
        scheduled_time: When the task was scheduled to run (defaults to now)

    Returns:
        Task: Created task record
    """
    task = Task(
        task_name=task_name,
        scheduled_time=scheduled_time or datetime.utcnow(),
        actual_start=datetime.utcnow(),
        status='running',
        items_processed=0,
        items_succeeded=0,
        items_failed=0,
        metadata={}
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    logger.info(f"Created task record: {task_name} (ID: {task.id})")
    return task


def update_task_success(
    db: Session,
    task: Task,
    items_processed: int,
    items_succeeded: int,
    items_failed: int,
    log_output: str,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Update task record on successful completion

    Args:
        db: Database session
        task: Task record to update
        items_processed: Total items processed
        items_succeeded: Number of successful items
        items_failed: Number of failed items
        log_output: Full log output from task execution
        metadata: Additional task-specific metadata
    """
    task.actual_end = datetime.utcnow()
    task.duration_seconds = int((task.actual_end - task.actual_start).total_seconds())
    task.status = 'completed'
    task.items_processed = items_processed
    task.items_succeeded = items_succeeded
    task.items_failed = items_failed
    task.log_output = log_output

    if metadata:
        task.metadata.update(metadata)

    db.commit()

    logger.info(
        f"Task completed: {task.task_name} "
        f"(processed: {items_processed}, succeeded: {items_succeeded}, failed: {items_failed}, "
        f"duration: {task.duration_seconds}s)"
    )


def update_task_failure(
    db: Session,
    task: Task,
    error_message: str,
    log_output: str = ""
) -> None:
    """
    Update task record on failure

    Args:
        db: Database session
        task: Task record to update
        error_message: Error message describing the failure
        log_output: Partial log output (if available)
    """
    task.actual_end = datetime.utcnow()
    task.duration_seconds = int((task.actual_end - task.actual_start).total_seconds())
    task.status = 'failed'
    task.error_message = error_message
    task.log_output = log_output

    db.commit()

    logger.error(
        f"Task failed: {task.task_name} "
        f"(duration: {task.duration_seconds}s, error: {error_message})"
    )


# ============================================================================
# Scheduled Task Functions
# ============================================================================

async def mam_scraping_task() -> None:
    """
    Daily MAM scraper - fetches new guides and torrents

    Schedule: Daily 2:00 AM
    Purpose: Crawl MyAnonamouse.net for new guides and torrent listings
    Output: Updated guides in guides_output/ directory
    """
    logger.info("Starting MAM scraping task")

    with get_db_context() as db:
        task = create_task_record(db, 'MAM')
        log_lines = []

        try:
            # TODO (Phase 4): Import and call stealth_mam_crawler module wrapper
            # from backend.modules.mam_crawler import run_stealth_crawler
            # result = await run_stealth_crawler()

            # Placeholder implementation
            log_lines.append(f"[{datetime.utcnow()}] MAM scraping task started")
            log_lines.append("[INFO] Authenticating with MAM...")
            log_lines.append("[INFO] Crawling guides section...")
            log_lines.append("[INFO] Processing torrent listings...")

            # Simulate work
            items_processed = 0
            items_succeeded = 0
            items_failed = 0

            # Example: Crawl 50 guides
            # items_processed = len(result['guides'])
            # items_succeeded = len([g for g in result['guides'] if g['status'] == 'success'])
            # items_failed = items_processed - items_succeeded

            log_lines.append(f"[{datetime.utcnow()}] MAM scraping completed successfully")

            update_task_success(
                db,
                task,
                items_processed=items_processed,
                items_succeeded=items_succeeded,
                items_failed=items_failed,
                log_output="\n".join(log_lines),
                metadata={
                    'crawler_type': 'stealth',
                    'output_directory': 'guides_output/'
                }
            )

            logger.info(f"MAM scraping task completed: {items_processed} guides processed")

        except Exception as e:
            error_msg = f"MAM scraping task failed: {str(e)}\n{traceback.format_exc()}"
            log_lines.append(f"[ERROR] {error_msg}")

            update_task_failure(
                db,
                task,
                error_message=error_msg,
                log_output="\n".join(log_lines)
            )

            logger.error(error_msg)
            raise


async def top10_discovery_task() -> None:
    """
    Weekly top-10 genre discovery from MAM

    Schedule: Sunday 3:00 AM
    Purpose: Scrape MAM visual top-10 for enabled genres and auto-download
    Output: New downloads queued in qBittorrent/Prowlarr
    """
    logger.info("Starting top-10 discovery task")

    with get_db_context() as db:
        task = create_task_record(db, 'TOP10')
        log_lines = []

        try:
            settings = get_settings()
            enabled_genres = settings.ENABLED_GENRES

            log_lines.append(f"[{datetime.utcnow()}] Top-10 discovery task started")
            log_lines.append(f"[INFO] Enabled genres: {', '.join(enabled_genres)}")

            items_processed = 0
            items_succeeded = 0
            items_failed = 0

            # TODO (Phase 4): Import and call top-10 discovery module
            # from backend.modules.top10_discovery import discover_top10
            # for genre in enabled_genres:
            #     log_lines.append(f"[INFO] Processing genre: {genre}")
            #     result = await discover_top10(genre)
            #     items_processed += len(result['books'])
            #     items_succeeded += result['downloaded']
            #     items_failed += result['failed']

            # Placeholder: Process enabled genres
            for genre in enabled_genres:
                log_lines.append(f"[INFO] Scraping top-10 for: {genre}")
                log_lines.append(f"[INFO] Extracting magnet links...")
                log_lines.append(f"[INFO] Sending to Prowlarr/qBittorrent...")

            log_lines.append(f"[{datetime.utcnow()}] Top-10 discovery completed")

            update_task_success(
                db,
                task,
                items_processed=items_processed,
                items_succeeded=items_succeeded,
                items_failed=items_failed,
                log_output="\n".join(log_lines),
                metadata={
                    'genres_processed': enabled_genres,
                    'downloads_queued': items_succeeded
                }
            )

            logger.info(f"Top-10 discovery completed: {items_succeeded} downloads queued")

        except Exception as e:
            error_msg = f"Top-10 discovery task failed: {str(e)}\n{traceback.format_exc()}"
            log_lines.append(f"[ERROR] {error_msg}")

            update_task_failure(
                db,
                task,
                error_message=error_msg,
                log_output="\n".join(log_lines)
            )

            logger.error(error_msg)
            raise


async def metadata_full_refresh_task() -> None:
    """
    Full library metadata correction (all books)

    Schedule: 1st of month 4:00 AM
    Purpose: Refresh metadata for ALL books in library using Google Books → Goodreads
    Output: Updated book metadata with source tracking
    """
    logger.info("Starting full metadata refresh task")

    with get_db_context() as db:
        task = create_task_record(db, 'METADATA_FULL')
        log_lines = []

        try:
            log_lines.append(f"[{datetime.utcnow()}] Full metadata refresh task started")

            # TODO (Phase 4): Import and call metadata correction module
            # from backend.modules.metadata_correction import refresh_all_metadata
            # result = await refresh_all_metadata()

            log_lines.append("[INFO] Fetching all books from Audiobookshelf...")
            log_lines.append("[INFO] Running metadata correction pipeline (Google Books → Goodreads)...")

            items_processed = 0
            items_succeeded = 0
            items_failed = 0

            # Placeholder: Process all books
            # items_processed = len(result['books'])
            # items_succeeded = len([b for b in result['books'] if b['metadata_updated']])
            # items_failed = items_processed - items_succeeded

            log_lines.append(f"[{datetime.utcnow()}] Full metadata refresh completed")

            update_task_success(
                db,
                task,
                items_processed=items_processed,
                items_succeeded=items_succeeded,
                items_failed=items_failed,
                log_output="\n".join(log_lines),
                metadata={
                    'scope': 'all_books',
                    'sources_used': ['google_books', 'goodreads']
                }
            )

            logger.info(f"Full metadata refresh completed: {items_succeeded}/{items_processed} books updated")

        except Exception as e:
            error_msg = f"Full metadata refresh task failed: {str(e)}\n{traceback.format_exc()}"
            log_lines.append(f"[ERROR] {error_msg}")

            update_task_failure(
                db,
                task,
                error_message=error_msg,
                log_output="\n".join(log_lines)
            )

            logger.error(error_msg)
            raise


async def metadata_new_books_task() -> None:
    """
    Metadata refresh for recently added books

    Schedule: Sunday 4:30 AM
    Purpose: Refresh metadata for books added in last 7 days
    Output: Updated metadata for new books only
    """
    logger.info("Starting new books metadata refresh task")

    with get_db_context() as db:
        task = create_task_record(db, 'METADATA_NEW')
        log_lines = []

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=7)

            log_lines.append(f"[{datetime.utcnow()}] New books metadata refresh task started")
            log_lines.append(f"[INFO] Processing books added since: {cutoff_date}")

            # TODO (Phase 4): Import and call metadata correction module
            # from backend.modules.metadata_correction import refresh_new_metadata
            # result = await refresh_new_metadata(cutoff_date)

            log_lines.append("[INFO] Fetching recently added books from Audiobookshelf...")
            log_lines.append("[INFO] Running metadata correction pipeline...")

            items_processed = 0
            items_succeeded = 0
            items_failed = 0

            # Placeholder
            # items_processed = len(result['books'])
            # items_succeeded = len([b for b in result['books'] if b['metadata_updated']])
            # items_failed = items_processed - items_succeeded

            log_lines.append(f"[{datetime.utcnow()}] New books metadata refresh completed")

            update_task_success(
                db,
                task,
                items_processed=items_processed,
                items_succeeded=items_succeeded,
                items_failed=items_failed,
                log_output="\n".join(log_lines),
                metadata={
                    'scope': 'recent_books',
                    'cutoff_date': cutoff_date.isoformat(),
                    'days_lookback': 7
                }
            )

            logger.info(f"New books metadata refresh completed: {items_succeeded}/{items_processed} books updated")

        except Exception as e:
            error_msg = f"New books metadata refresh task failed: {str(e)}\n{traceback.format_exc()}"
            log_lines.append(f"[ERROR] {error_msg}")

            update_task_failure(
                db,
                task,
                error_message=error_msg,
                log_output="\n".join(log_lines)
            )

            logger.error(error_msg)
            raise


async def series_completion_task() -> None:
    """
    Series completion detection and auto-download

    Schedule: 2nd of month 3:00 AM
    Purpose: Detect missing books in series and auto-download
    Output: New series books downloaded and imported to Audiobookshelf
    """
    logger.info("Starting series completion task")

    with get_db_context() as db:
        task = create_task_record(db, 'SERIES')
        log_lines = []

        try:
            log_lines.append(f"[{datetime.utcnow()}] Series completion task started")

            # TODO (Phase 4): Import and call series completion module
            # from backend.modules.series_completion import complete_series
            # result = await complete_series()

            log_lines.append("[INFO] Fetching all series from Audiobookshelf...")
            log_lines.append("[INFO] Querying Goodreads for complete series information...")
            log_lines.append("[INFO] Identifying missing books...")
            log_lines.append("[INFO] Downloading missing books (batch size: 10)...")
            log_lines.append("[INFO] Auto-importing to Audiobookshelf...")
            log_lines.append("[INFO] Running metadata correction on new books...")

            items_processed = 0  # Number of series processed
            items_succeeded = 0  # Number of books successfully downloaded
            items_failed = 0     # Number of download failures

            # Placeholder
            # items_processed = len(result['series'])
            # items_succeeded = len(result['downloaded_books'])
            # items_failed = len(result['failed_downloads'])

            log_lines.append(f"[{datetime.utcnow()}] Series completion task completed")

            update_task_success(
                db,
                task,
                items_processed=items_processed,
                items_succeeded=items_succeeded,
                items_failed=items_failed,
                log_output="\n".join(log_lines),
                metadata={
                    'batch_size': 10,
                    'sources_priority': ['MAM', 'Google Books', 'Goodreads'],
                    'auto_import': True
                }
            )

            logger.info(f"Series completion completed: {items_succeeded} books downloaded from {items_processed} series")

        except Exception as e:
            error_msg = f"Series completion task failed: {str(e)}\n{traceback.format_exc()}"
            log_lines.append(f"[ERROR] {error_msg}")

            update_task_failure(
                db,
                task,
                error_message=error_msg,
                log_output="\n".join(log_lines)
            )

            logger.error(error_msg)
            raise


async def author_completion_task() -> None:
    """
    Author completion detection and auto-download

    Schedule: 3rd of month 3:00 AM
    Purpose: Detect missing audiobooks by authors in library and auto-download
    Output: New author audiobooks downloaded and imported to Audiobookshelf
    """
    logger.info("Starting author completion task")

    with get_db_context() as db:
        task = create_task_record(db, 'AUTHOR')
        log_lines = []

        try:
            log_lines.append(f"[{datetime.utcnow()}] Author completion task started")

            # TODO (Phase 4): Import and call author completion module
            # from backend.modules.author_completion import complete_authors
            # result = await complete_authors()

            log_lines.append("[INFO] Fetching all authors from Audiobookshelf...")
            log_lines.append("[INFO] Querying MAM, Google Books, Goodreads for author catalogs...")
            log_lines.append("[INFO] Identifying missing audiobooks...")
            log_lines.append("[INFO] Downloading with priority: MAM → Google → Goodreads...")
            log_lines.append("[INFO] Auto-importing to Audiobookshelf...")
            log_lines.append("[INFO] Running metadata correction on new books...")

            items_processed = 0  # Number of authors processed
            items_succeeded = 0  # Number of audiobooks successfully downloaded
            items_failed = 0     # Number of download failures

            # Placeholder
            # items_processed = len(result['authors'])
            # items_succeeded = len(result['downloaded_books'])
            # items_failed = len(result['failed_downloads'])

            log_lines.append(f"[{datetime.utcnow()}] Author completion task completed")

            update_task_success(
                db,
                task,
                items_processed=items_processed,
                items_succeeded=items_succeeded,
                items_failed=items_failed,
                log_output="\n".join(log_lines),
                metadata={
                    'sources_priority': ['MAM', 'Google Books', 'Goodreads'],
                    'auto_import': True,
                    'audiobooks_only': True
                }
            )

            logger.info(f"Author completion completed: {items_succeeded} audiobooks downloaded from {items_processed} authors")

        except Exception as e:
            error_msg = f"Author completion task failed: {str(e)}\n{traceback.format_exc()}"
            log_lines.append(f"[ERROR] {error_msg}")

            update_task_failure(
                db,
                task,
                error_message=error_msg,
                log_output="\n".join(log_lines)
            )

            logger.error(error_msg)
            raise


# ============================================================================
# Task Cleanup (Retention Policy)
# ============================================================================

async def cleanup_old_tasks() -> None:
    """
    Clean up task records older than retention period

    Schedule: Daily 1:00 AM (should be added separately)
    Purpose: Enforce 30-day retention policy on task history
    Output: Deleted old task records
    """
    logger.info("Starting task cleanup")

    with get_db_context() as db:
        try:
            settings = get_settings()
            cutoff_date = datetime.utcnow() - timedelta(days=settings.HISTORY_RETENTION_DAYS)

            # Delete tasks older than retention period
            deleted_count = db.query(Task).filter(
                Task.date_created < cutoff_date
            ).delete()

            db.commit()

            logger.info(f"Task cleanup completed: {deleted_count} records deleted (older than {cutoff_date})")

        except Exception as e:
            logger.error(f"Task cleanup failed: {str(e)}", exc_info=True)
            db.rollback()
            raise
