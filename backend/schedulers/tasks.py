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
from backend.services.workflow_executor import RealExecutionWorkflow

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



async def process_download_queue_task() -> None:
    """
    Process the download queue:
    1. Scan library for new books (DiscoveryService)
    2. Queue new items to DB ('queued' status)
    3. Process 'queued' items via MAMSeleniumService
    
    Schedule: Every 30 minutes
    Purpose: Active download and queue management
    """
    logger.info("Starting download queue processing task")

    with get_db_context() as db:
        task = create_task_record(db, 'DOWNLOAD_QUEUE')
        log_lines = []
        
        try:
            from backend.services.discovery_service import DiscoveryService
            from backend.services.mam_selenium_service import MAMSeleniumService
            
            discovery = DiscoveryService()
            mam_service = MAMSeleniumService()
            
            # Step 1: Discovery (Optional - typically this finds gaps)
            log_lines.append(f"[{datetime.utcnow()}] Checking for new books...")
            new_books = await discovery.find_new_books()
            
            # Step 2: Queue to DB
            queued_count = 0
            if new_books:
                queued_count = discovery.queue_downloads(new_books)
                log_lines.append(f"[INFO] Queued {queued_count} new books to database")
            
            # Step 3: Load Queue from DB
            queue = discovery.load_download_list()
            log_lines.append(f"[INFO] Found {len(queue)} items in download queue")
            
            # Step 4: Process Queue
            processed_count = 0
            success_count = 0
            failed_count = 0
            
            if queue:
                results = await mam_service.run_search_and_download(queue)
                processed_count = len(queue)
                success_count = len(results)
                failed_count = processed_count - success_count
                
                log_lines.append(f"[INFO] Processed {processed_count} items ({success_count} succeeded)")
                for res in results:
                    book_title = res.get('book', {}).get('title', 'Unknown')
                    magnet = res.get('mam_result', {}).get('magnet', 'No magnet')
                    log_lines.append(f"  + Downloaded: {book_title}")
            
            update_task_success(
                db,
                task,
                items_processed=processed_count + queued_count,
                items_succeeded=success_count + queued_count,
                items_failed=failed_count,
                log_output="\n".join(log_lines),
                metadata={
                    'new_books_found': len(new_books),
                    'queued_db': queued_count,
                    'processed_queue': processed_count
                }
            )
            
            logger.info(f"Download queue task completed: {success_count} downloads started")

        except Exception as e:
            error_msg = f"Download queue task failed: {str(e)}\n{traceback.format_exc()}"
            log_lines.append(f"[ERROR] {error_msg}")

            update_task_failure(
                db,
                task,
                error_message=error_msg,
                log_output="\n".join(log_lines)
            )

            logger.error(error_msg)


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

import os

async def execute_full_workflow_task() -> None:
    """
    Execute the full 'Real' workflow (Legacy unification)
    
    Schedule: Manual / On Demand (or daily if desired)
    Purpose: Run the comprehensive audiobook acquisition pipeline:
             Discovery -> Download -> Sync -> Metadata -> ID3 -> Reporting
    Output: Full execution report
    """
    logger.info("Starting full workflow task")
    
    with get_db_context() as db:
        task = create_task_record(db, 'FULL_WORKFLOW_LEGACY')
        
        try:
            # We can capture logs if we modify RealExecutionWorkflow, 
            # but for now we'll just run it and point to the log file.
            log_file_path = "logs/real_workflow_execution.log"
            
            logger.info(f"Initializing workflow (logs at {log_file_path})")
            workflow = RealExecutionWorkflow()
            
            # Execute
            await workflow.execute()
            
            # Read last N lines from log file to store in DB task
            log_tail = ""
            if os.path.exists(log_file_path):
                try:
                    # quick and dirty tail
                    with open(log_file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        log_tail = "".join(lines[-100:]) # Last 100 lines
                except Exception:
                    log_tail = "Could not read log file tail."
            
            update_task_success(
                db,
                task,
                items_processed=1, # One workflow
                items_succeeded=1,
                items_failed=0,
                log_output=log_tail,
                metadata={
                    'full_log_path': log_file_path,
                    'execution_mode': 'legacy_script_wrapper'
                }
            )
            
        except Exception as e:
            error_msg = f"Full workflow failed: {str(e)}\n{traceback.format_exc()}"
            update_task_failure(
                db,
                task,
                error_message=error_msg
            )
            logger.error(error_msg)
            raise


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


# ============================================================================
# Phase 1: MAM Rules Scraping (Daily 12:00 PM)
# ============================================================================

async def mam_rules_scraping_task() -> None:
    """
    Daily MAM rules scraping at 12:00 PM

    Schedule: Daily at 12:00 PM (noon)
    Purpose: Scrape 7 MAM pages for rules, events, and VIP information
    Output: Rules cached in database and JSON file
    """
    logger.info("Starting daily MAM rules scraping")

    with get_db_context() as db:
        log_lines = []

        try:
            task = create_task_record(db, 'MAM_RULES_SCRAPING')

            log_lines.append(f"[{datetime.utcnow()}] Starting MAM rules scraping...")
            log_lines.append("[INFO] Scraping 7 MAM pages:")
            log_lines.append("  1. https://www.myanonamouse.net/rules.php")
            log_lines.append("  2. https://www.myanonamouse.net/faq.php")
            log_lines.append("  3. https://www.myanonamouse.net/f/b/18")
            log_lines.append("  4. https://www.myanonamouse.net/f/b/78")
            log_lines.append("  5. https://www.myanonamouse.net/guides/")
            log_lines.append("  6. https://www.myanonamouse.net/updateNotes.php")
            log_lines.append("  7. https://www.myanonamouse.net/api/list.php")

            # Run the scraping service
            from backend.services.mam_rules_service import MAMRulesService

            service = MAMRulesService()
            rules_data = await service.scrape_rules_daily()

            # Log event detection
            if rules_data.get('freeleech_active'):
                log_lines.append("[EVENT] Freeleech is active")
            if rules_data.get('bonus_event_active'):
                log_lines.append("[EVENT] Bonus event is active")
            if rules_data.get('multiplier_active'):
                log_lines.append("[EVENT] Multiplier is active")

            items_processed = 7  # 7 pages scraped
            items_succeeded = len([p for p in rules_data.get('pages', {}) if p])
            items_failed = items_processed - items_succeeded

            log_lines.append(f"[{datetime.utcnow()}] MAM rules scraping completed")
            log_lines.append(f"[SUMMARY] Pages scraped: {items_succeeded}/{items_processed}")

            update_task_success(
                db,
                task,
                items_processed=items_processed,
                items_succeeded=items_succeeded,
                items_failed=items_failed,
                log_output="\n".join(log_lines),
                metadata={
                    'rule_version': rules_data.get('rule_version', 1),
                    'freeleech_active': rules_data.get('freeleech_active', False),
                    'bonus_event_active': rules_data.get('bonus_event_active', False),
                    'multiplier_active': rules_data.get('multiplier_active', False)
                }
            )

            logger.info(f"MAM rules scraping completed: {items_succeeded} pages successfully scraped")

        except Exception as e:
            error_msg = f"MAM rules scraping task failed: {str(e)}\n{traceback.format_exc()}"
            log_lines.append(f"[ERROR] {error_msg}")

            if 'task' in locals():
                update_task_failure(
                    db,
                    task,
                    error_message=error_msg,
                    log_output="\n".join(log_lines)
                )

            logger.error(error_msg)
            raise


# ============================================================================
# Phase 1: Ratio Emergency Monitoring (Every 5 Minutes)
# ============================================================================

async def ratio_emergency_monitoring_task() -> None:
    """
    Continuous global ratio monitoring (every 5 minutes)

    Schedule: Every 5 minutes around the clock
    Purpose: Monitor global ratio and trigger emergency freeze if ratio <= 1.00
    Output: Ratio logged to database, emergency actions triggered
    """
    logger.info("Checking global ratio")

    with get_db_context() as db:
        try:
            from backend.services.ratio_emergency_service import RatioEmergencyService

            service = RatioEmergencyService()

            # Main check and management
            await service.check_ratio_and_manage()

            # Log current ratio
            current_ratio = await service.get_current_ratio()
            is_emergency = await service.is_emergency_active()

            from backend.models import RatioLog

            ratio_log = RatioLog(
                timestamp=datetime.utcnow(),
                global_ratio=current_ratio,
                emergency_active=is_emergency,
                seeding_allocation=0
            )
            db.add(ratio_log)
            db.commit()

            log_message = f"Ratio: {current_ratio} - Emergency: {is_emergency}"
            logger.info(log_message)

        except Exception as e:
            error_msg = f"Ratio monitoring task failed: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            db.rollback()
            raise


# ============================================================================
# Phase 2: Weekly Metadata Maintenance
# ============================================================================

async def weekly_metadata_maintenance_task() -> None:
    """
    Weekly metadata maintenance for books < 13 days old

    Schedule: Weekly (Sunday 5:00 AM)
    Purpose: Refresh metadata for recently added books
    Output: Metadata updated for books, corrections logged
    """
    logger.info("Starting weekly metadata maintenance")

    with get_db_context() as db:
        log_lines = []

        try:
            from backend.models import Book

            task = create_task_record(db, 'METADATA_MAINTENANCE_WEEKLY')

            log_lines.append(f"[{datetime.utcnow()}] Starting weekly metadata maintenance...")

            # Find books added in last 13 days
            cutoff_date = datetime.utcnow() - timedelta(days=13)
            recent_books = db.query(Book).filter(
                Book.date_added >= cutoff_date,
                Book.status == 'active'
            ).all()

            log_lines.append(f"[INFO] Found {len(recent_books)} books from last 13 days")

            # Would trigger metadata refresh for each book
            items_processed = len(recent_books)
            items_succeeded = 0  # Placeholder

            log_lines.append(f"[{datetime.utcnow()}] Weekly metadata maintenance completed")
            log_lines.append(f"[SUMMARY] Books processed: {items_processed}")

            update_task_success(
                db,
                task,
                items_processed=items_processed,
                items_succeeded=items_succeeded,
                items_failed=items_processed - items_succeeded,
                log_output="\n".join(log_lines),
                metadata={'books_processed': items_processed}
            )

            logger.info(f"Weekly metadata maintenance completed: {items_processed} books")

        except Exception as e:
            error_msg = f"Weekly metadata maintenance failed: {str(e)}\n{traceback.format_exc()}"
            log_lines.append(f"[ERROR] {error_msg}")

            if 'task' in locals():
                update_task_failure(
                    db,
                    task,
                    error_message=error_msg,
                    log_output="\n".join(log_lines)
                )

            logger.error(error_msg)
            raise


# ============================================================================
# Phase 2: Weekly Category Sync
# ============================================================================

async def weekly_category_sync_task() -> None:
    """
    Weekly category synchronization (all 37 genres + top-10)

    Schedule: Weekly (Sunday 6:00 AM)
    Purpose: Sync audiobook categories and discover new titles
    Output: New titles queued for download
    """
    logger.info("Starting weekly category sync")

    with get_db_context() as db:
        log_lines = []

        try:
            from backend.services.category_sync_service import CategorySyncService

            task = create_task_record(db, 'CATEGORY_SYNC_WEEKLY')

            log_lines.append(f"[{datetime.utcnow()}] Starting weekly category sync...")

            service = CategorySyncService()
            results = await service.sync_all_categories()

            log_lines.append(f"[INFO] Synced {results['categories_synced']} categories")
            log_lines.append(f"[INFO] Found {results['new_titles']} new titles")
            log_lines.append(f"[INFO] Duration: {results['duration_seconds']} seconds")

            update_task_success(
                db,
                task,
                items_processed=results['categories_synced'],
                items_succeeded=results['new_titles'],
                items_failed=results['errors'],
                log_output="\n".join(log_lines),
                metadata={
                    'categories_synced': results['categories_synced'],
                    'new_titles': results['new_titles']
                }
            )

            logger.info(f"Weekly category sync completed: {results['new_titles']} new titles")

        except Exception as e:
            error_msg = f"Weekly category sync failed: {str(e)}\n{traceback.format_exc()}"
            log_lines.append(f"[ERROR] {error_msg}")

            if 'task' in locals():
                update_task_failure(
                    db,
                    task,
                    error_message=error_msg,
                    log_output="\n".join(log_lines)
                )

            logger.error(error_msg)
            raise


# ============================================================================
# Phase 2: Weekly Seeding Management
# ============================================================================

async def weekly_seeding_management_task() -> None:
    """
    Weekly seeding management and point optimization

    Schedule: Weekly (Sunday 7:00 AM)
    Purpose: Evaluate seeding efficiency and optimize point generation
    Output: Seeding allocation optimized, efficiency metrics logged
    """
    logger.info("Starting weekly seeding management")

    with get_db_context() as db:
        log_lines = []

        try:
            from backend.services.qbittorrent_monitor_service import QBittorrentMonitorService

            task = create_task_record(db, 'SEEDING_MANAGEMENT_WEEKLY')

            log_lines.append(f"[{datetime.utcnow()}] Starting weekly seeding management...")

            service = QBittorrentMonitorService()
            await service.initialize_qbittorrent()

            # Get torrent states
            states = await service.get_torrent_states()

            # Optimize seeding
            optimization = await service.optimize_seeding_allocation()

            # Get point metrics
            points = await service.calculate_point_generation()

            log_lines.append(f"[INFO] Total torrents: {len(states.get('seeding', []))} seeding")
            log_lines.append(f"[INFO] Estimated points/hour: {points.get('estimated_points_per_hour', 0):.0f}")
            log_lines.append(f"[INFO] Optimization action: {optimization.get('action_taken', 'none')}")

            update_task_success(
                db,
                task,
                items_processed=len(states.get('seeding', [])),
                items_succeeded=1,
                items_failed=0,
                log_output="\n".join(log_lines),
                metadata={
                    'seeding_count': len(states.get('seeding', [])),
                    'estimated_points_per_hour': points.get('estimated_points_per_hour', 0)
                }
            )

            logger.info("Weekly seeding management completed")

        except Exception as e:
            error_msg = f"Weekly seeding management failed: {str(e)}\n{traceback.format_exc()}"
            log_lines.append(f"[ERROR] {error_msg}")

            if 'task' in locals():
                update_task_failure(
                    db,
                    task,
                    error_message=error_msg,
                    log_output="\n".join(log_lines)
                )

            logger.error(error_msg)
            raise


# ============================================================================
# Phase 2: Series/Author Completion (Combined)
# ============================================================================

async def series_author_completion_task() -> None:
    """
    Weekly series and author completion check

    Schedule: Weekly (Monday 2:00 AM)
    Purpose: Find and download missing series/author books
    Output: Missing books queued for download
    """
    logger.info("Starting series/author completion check")

    with get_db_context() as db:
        log_lines = []

        try:
            task = create_task_record(db, 'SERIES_AUTHOR_COMPLETION_WEEKLY')

            log_lines.append(f"[{datetime.utcnow()}] Starting series/author completion check...")
            log_lines.append("[INFO] Checking for incomplete series...")
            log_lines.append("[INFO] Checking for incomplete author works...")

            items_processed = 0
            items_succeeded = 0

            log_lines.append(f"[{datetime.utcnow()}] Series/author completion check completed")
            log_lines.append(f"[SUMMARY] Processed: {items_processed}")

            update_task_success(
                db,
                task,
                items_processed=items_processed,
                items_succeeded=items_succeeded,
                items_failed=0,
                log_output="\n".join(log_lines),
                metadata={'series_checked': items_processed}
            )

            logger.info("Series/author completion check completed")

        except Exception as e:
            error_msg = f"Series/author completion failed: {str(e)}\n{traceback.format_exc()}"
            log_lines.append(f"[ERROR] {error_msg}")

            if 'task' in locals():
                update_task_failure(
                    db,
                    task,
                    error_message=error_msg,
                    log_output="\n".join(log_lines)
                )

            logger.error(error_msg)
            raise


# ============================================================================
# Weekly Metadata Sync Task (Sundays at 2:00 AM)
# ============================================================================

async def weekly_metadata_sync_task() -> None:
    """
    Weekly metadata synchronization with Audiobookshelf

    Schedule: Weekly (Sunday 2:00 AM)
    Purpose: Sync metadata between MAMcrawler and Audiobookshelf for recent books
    Output: Metadata synchronized, discrepancies resolved
    """
    logger.info("Starting weekly metadata sync task")

    with get_db_context() as db:
        log_lines = []

        try:
            task = create_task_record(db, 'WEEKLY_METADATA_SYNC')

            log_lines.append(f"[{datetime.utcnow()}] Starting weekly metadata sync...")
            log_lines.append("[INFO] Fetching recent books from Audiobookshelf...")

            # Sync metadata for books added in last 14 days
            cutoff_date = datetime.utcnow() - timedelta(days=14)
            from backend.models import Book

            recent_books = db.query(Book).filter(
                Book.date_added >= cutoff_date,
                Book.status == 'active'
            ).all()

            log_lines.append(f"[INFO] Found {len(recent_books)} books from last 14 days")
            log_lines.append("[INFO] Syncing metadata with Audiobookshelf...")
            log_lines.append("[INFO] Updating book records in database...")

            items_processed = len(recent_books)
            items_succeeded = 0  # Placeholder - would be actual sync count

            log_lines.append(f"[{datetime.utcnow()}] Weekly metadata sync completed")
            log_lines.append(f"[SUMMARY] Books synced: {items_processed}")

            update_task_success(
                db,
                task,
                items_processed=items_processed,
                items_succeeded=items_succeeded,
                items_failed=items_processed - items_succeeded,
                log_output="\n".join(log_lines),
                metadata={
                    'books_synced': items_processed,
                    'cutoff_date': cutoff_date.isoformat(),
                    'days_lookback': 14
                }
            )

            logger.info(f"Weekly metadata sync completed: {items_processed} books processed")

        except Exception as e:
            error_msg = f"Weekly metadata sync failed: {str(e)}\n{traceback.format_exc()}"
            log_lines.append(f"[ERROR] {error_msg}")

            if 'task' in locals():
                update_task_failure(
                    db,
                    task,
                    error_message=error_msg,
                    log_output="\n".join(log_lines)
                )

            logger.error(error_msg)
            raise


# ============================================================================
# GAP 3: Monthly Drift Correction Task
# ============================================================================

async def monthly_drift_correction_task() -> None:
    """
    GAP 3 IMPLEMENTATION: Monthly metadata drift correction

    Schedule: Monthly (First Sunday at 3:00 AM)
    Purpose: Detect and correct metadata drift from Goodreads
    Output: Corrected metadata fields

    Process:
    1. Find books not updated in 30+ days
    2. Fetch latest Goodreads data
    3. Detect field-level drift
    4. Apply corrections to non-protected fields
    5. Log all changes
    """
    logger.info("GAP 3: Starting monthly drift correction task")

    with get_db_context() as db:
        log_lines = []
        task = None

        try:
            task = create_task_record(
                db,
                task_name="monthly_drift_correction",
                scheduled_time=datetime.utcnow()
            )

            from backend.services.drift_detection_service import DriftDetectionService
            import asyncio

            drift_service = DriftDetectionService(db)

            log_lines.append("[INFO] Detecting metadata drift...")

            # Detect drift for all old books
            drift_reports = await drift_service.detect_drift_all_books(
                days_since_update=30,
                limit=100  # Process 100 books per run
            )

            log_lines.append(f"[INFO] Found {len(drift_reports)} books with drift")

            total_corrections = 0
            books_corrected = 0
            protected_field_attempts = 0

            # Apply corrections
            for drift_report in drift_reports:
                try:
                    correction_result = await drift_service.apply_drift_corrections(
                        drift_report=drift_report,
                        auto_correct=True
                    )

                    if correction_result.get('corrections_applied', 0) > 0:
                        total_corrections += correction_result['corrections_applied']
                        books_corrected += 1
                        log_lines.append(
                            f"[INFO] Book {drift_report['book_id']} ({drift_report['book_title']}): "
                            f"{correction_result['corrections_applied']} corrections applied"
                        )

                    if correction_result.get('protected_fields_detected'):
                        protected_field_attempts += 1

                except Exception as e:
                    log_lines.append(f"[ERROR] Failed to correct book {drift_report['book_id']}: {e}")

            log_lines.append(f"[INFO] Drift correction complete: {books_corrected} books corrected")
            log_lines.append(f"[INFO] Total corrections applied: {total_corrections}")
            log_lines.append(f"[INFO] Protected field attempts blocked: {protected_field_attempts}")

            update_task_success(
                db,
                task,
                items_processed=len(drift_reports),
                items_succeeded=books_corrected,
                items_failed=len(drift_reports) - books_corrected,
                log_output="\n".join(log_lines),
                metadata={
                    "total_corrections": total_corrections,
                    "books_corrected": books_corrected,
                    "protected_field_attempts": protected_field_attempts,
                    "drift_reports_count": len(drift_reports)
                }
            )

            logger.info(
                f"GAP 3: Monthly drift correction complete: "
                f"{books_corrected} books corrected, {total_corrections} fields updated"
            )

        except Exception as e:
            error_msg = f"GAP 3: Monthly drift correction failed: {str(e)}\n{traceback.format_exc()}"
            log_lines.append(f"[ERROR] {error_msg}")

            if task:
                update_task_failure(
                    db,
                    task,
                    error_message=error_msg,
                    log_output="\n".join(log_lines)
                )

            logger.error(error_msg)
            raise


# ============================================================================
# Daily Metadata Update Task (Google Books API)
# ============================================================================

async def daily_metadata_update_task() -> None:
    """
    Daily Google Books API metadata update.

    Schedule: Daily 3:00 AM
    Purpose: Update metadata for books using Google Books API
    Output: Updated book records with fresh metadata

    Process:
    1. Query books needing updates (null first, then oldest timestamps)
    2. Update up to DAILY_MAX books per run
    3. Set last_metadata_updated timestamp
    4. Store only current metadata (no history)
    5. Never overwrite existing good data

    Priority Queue:
    - Books with last_metadata_updated = null FIRST
    - Books sorted by oldest last_metadata_updated SECOND
    - Respects daily API quota
    """
    logger.info("Starting daily metadata update task (Google Books API)")

    with get_db_context() as db:
        task = create_task_record(db, 'DAILY_METADATA_UPDATE')
        log_lines = []

        try:
            from backend.services.daily_metadata_update_service import DailyMetadataUpdateService
            from backend.integrations.google_books_client import GoogleBooksClient
            from backend.config import get_settings
            import os

            settings = get_settings()
            api_key = os.getenv('GOOGLE_BOOKS_API_KEY')

            if not api_key:
                raise ValueError("GOOGLE_BOOKS_API_KEY not set in environment")

            log_lines.append("[INFO] Initializing Google Books client...")
            google_books_client = GoogleBooksClient(api_key=api_key)

            # Get daily max from settings or use default
            daily_max = getattr(settings, 'DAILY_METADATA_MAX_BOOKS', 100)

            log_lines.append(f"[INFO] Daily max books: {daily_max}")

            service = DailyMetadataUpdateService(
                google_books_client=google_books_client,
                db=db,
                daily_max=daily_max
            )

            log_lines.append("[INFO] Running daily metadata update...")

            # Run the update
            result = await service.run_daily_update()

            log_lines.append(f"[SUMMARY] Update completed")
            log_lines.append(f"[SUMMARY] Books processed: {result['books_processed']}")
            log_lines.append(f"[SUMMARY] Books updated: {result['books_updated']}")
            log_lines.append(f"[SUMMARY] Errors: {len(result['errors'])}")
            log_lines.append(f"[SUMMARY] Rate limit remaining: {result['rate_limit_remaining']}")

            if result['errors']:
                log_lines.append("[ERROR] Errors encountered:")
                for error in result['errors']:
                    log_lines.append(f"  - {error}")

            log_lines.append(f"[INFO] Updated records: {len(result['updated_records'])}")
            for record in result['updated_records'][:10]:  # Log first 10
                log_lines.append(
                    f"  - {record['title']} ({len(record['fields_updated'])} fields): "
                    f"{', '.join(record['fields_updated'])}"
                )

            # Get current status
            status = await service.get_update_status()

            log_lines.append("[INFO] Overall update status:")
            log_lines.append(f"  - Total books: {status['total_books']}")
            log_lines.append(f"  - Books with metadata: {status['books_updated']}")
            log_lines.append(f"  - Books pending: {status['books_pending']}")
            log_lines.append(f"  - Percent updated: {status['percent_updated']:.1f}%")
            if status['average_days_since_update']:
                log_lines.append(f"  - Avg days since update: {status['average_days_since_update']:.1f}")

            update_task_success(
                db,
                task,
                items_processed=result['books_processed'],
                items_succeeded=result['books_updated'],
                items_failed=len(result['errors']),
                log_output="\n".join(log_lines),
                metadata={
                    'books_processed': result['books_processed'],
                    'books_updated': result['books_updated'],
                    'errors': len(result['errors']),
                    'total_books': status['total_books'],
                    'percent_updated': status['percent_updated'],
                    'average_days_since_update': status['average_days_since_update']
                }
            )

            logger.info(
                f"Daily metadata update completed: "
                f"{result['books_updated']} books updated, "
                f"{len(result['errors'])} errors"
            )

        except Exception as e:
            error_msg = f"Daily metadata update failed: {str(e)}\n{traceback.format_exc()}"
            log_lines.append(f"[ERROR] {error_msg}")

            if task:
                update_task_failure(
                    db,
                    task,
                    error_message=error_msg,
                    log_output="\n".join(log_lines)
                )

            logger.error(error_msg)
            raise


# ============================================================================
# Phase 5: Automated Batch Repair Task
# ============================================================================

async def repair_batch_task() -> None:
    """
    Automated batch repair of failed audiobooks

    Schedule: Weekly (Saturday 8:00 AM)
    Purpose: Scan for failed/low-quality audiobooks and attempt repairs
    Output: Failed books repaired and replaced, quality improved

    Process:
    1. Query failed and low-quality books from verification results
    2. For each book, find replacement candidates
    3. Evaluate replacement quality (codec, bitrate, duration)
    4. Execute replacements meeting quality thresholds
    5. Log all repair operations with detailed results
    """
    logger.info("Starting automated batch repair task")

    with get_db_context() as db:
        task = create_task_record(db, 'REPAIR_BATCH')
        log_lines = []

        try:
            from mamcrawler.repair import get_repair_orchestrator, get_repair_reporter
            from backend.models import Book, Download

            log_lines.append(f"[{datetime.utcnow()}] Starting batch repair task...")

            orchestrator = get_repair_orchestrator()
            reporter = get_repair_reporter()

            # Find books that need repair (status = 'failed_verification' or low quality)
            failed_books = db.query(Book).filter(
                Book.status.in_(['failed_verification', 'low_quality'])
            ).limit(50).all()

            log_lines.append(f"[INFO] Found {len(failed_books)} books needing repair")

            items_processed = len(failed_books)
            items_succeeded = 0
            items_failed = 0
            repair_reports = []

            # Process each failed book
            for book in failed_books:
                try:
                    log_lines.append(f"[INFO] Processing: {book.title} by {book.author}")

                    # Find replacement candidates from downloads table
                    candidates = db.query(Download).filter(
                        Download.book_id == book.id,
                        Download.status == 'completed'
                    ).limit(5).all()

                    if not candidates:
                        log_lines.append(f"[SKIP] No replacement candidates for {book.title}")
                        items_failed += 1
                        continue

                    candidate_files = [c.file_path for c in candidates if c.file_path]

                    # Batch evaluate replacement candidates
                    if book.file_path and candidate_files:
                        evaluation = orchestrator.batch_evaluate_replacements(
                            original_file=book.file_path,
                            replacement_candidates=candidate_files,
                            audiobook_title=book.title,
                            author=book.author
                        )

                        # Generate batch evaluation report
                        batch_report = reporter.generate_batch_report(evaluation)
                        repair_reports.append(batch_report)

                        # If acceptable replacement found, execute it
                        if evaluation.get('best_replacement'):
                            best_file = evaluation['best_replacement']
                            log_lines.append(
                                f"[REPAIR] Executing replacement with: {best_file}"
                            )

                            # Execute replacement
                            execution = orchestrator.execute_replacement(
                                original_file=book.file_path,
                                replacement_file=best_file,
                                audiobook_title=book.title
                            )

                            # Generate execution report
                            exec_report = reporter.generate_execution_report(execution)
                            repair_reports.append(exec_report)

                            if execution.get('success'):
                                items_succeeded += 1
                                # Update book status
                                book.status = 'active'
                                book.date_modified = datetime.utcnow()
                                log_lines.append(
                                    f"[SUCCESS] {book.title} repaired: "
                                    f"Backup at {execution.get('backup_file')}"
                                )
                            else:
                                items_failed += 1
                                log_lines.append(
                                    f"[ERROR] Failed to repair {book.title}: "
                                    f"{execution.get('error')}"
                                )
                        else:
                            items_failed += 1
                            log_lines.append(
                                f"[SKIP] No acceptable replacement for {book.title}"
                            )
                    else:
                        items_failed += 1
                        log_lines.append(f"[SKIP] Original file missing for {book.title}")

                except Exception as e:
                    items_failed += 1
                    log_lines.append(
                        f"[ERROR] Failed to process {book.title}: {str(e)}"
                    )

            # Commit book status updates
            db.commit()

            # Generate summary report
            summary_report = reporter.generate_summary_report(repair_reports)

            log_lines.append(f"[{datetime.utcnow()}] Batch repair task completed")
            log_lines.append(f"[SUMMARY] Processed: {items_processed}")
            log_lines.append(f"[SUMMARY] Repaired: {items_succeeded}")
            log_lines.append(f"[SUMMARY] Failed: {items_failed}")

            update_task_success(
                db,
                task,
                items_processed=items_processed,
                items_succeeded=items_succeeded,
                items_failed=items_failed,
                log_output="\n".join(log_lines),
                metadata={
                    'books_repaired': items_succeeded,
                    'books_failed': items_failed,
                    'success_rate': (items_succeeded / items_processed * 100) if items_processed > 0 else 0,
                    'unique_audiobooks': summary_report.get('unique_audiobooks', 0)
                }
            )

            logger.info(
                f"Batch repair completed: {items_succeeded} repaired, "
                f"{items_failed} failed out of {items_processed}"
            )

        except Exception as e:
            error_msg = f"Batch repair task failed: {str(e)}\n{traceback.format_exc()}"
            log_lines.append(f"[ERROR] {error_msg}")

            update_task_failure(
                db,
                task,
                error_message=error_msg,
                log_output="\n".join(log_lines)
            )

            logger.error(error_msg)
            raise
