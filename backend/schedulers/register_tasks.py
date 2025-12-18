"""
Task Registration Helper
Registers all scheduled tasks with APScheduler

This module provides a single function to register all scheduled tasks.
Call this during application startup to configure the scheduler.
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler

from backend.config import get_settings
from backend.schedulers.tasks import (
    mam_scraping_task,
    top10_discovery_task,
    metadata_full_refresh_task,
    metadata_new_books_task,
    series_completion_task,
    author_completion_task,
    cleanup_old_tasks,
    mam_rules_scraping_task,
    ratio_emergency_monitoring_task,
    weekly_metadata_maintenance_task,
    weekly_category_sync_task,
    weekly_seeding_management_task,
    series_author_completion_task,
    weekly_metadata_sync_task,
    monthly_drift_correction_task,
    daily_metadata_update_task,
    daily_metadata_update_task,
    repair_batch_task,
    process_download_queue_task,
    execute_full_workflow_task
)
from backend.services.vip_management_service import daily_vip_management_task

logger = logging.getLogger(__name__)


def register_all_tasks(scheduler: BackgroundScheduler) -> None:
    """
    Register all scheduled tasks with the scheduler

    This function registers all 7 scheduled tasks:
    - MAM scraping (daily)
    - Top-10 discovery (weekly)
    - Full metadata refresh (monthly)
    - New books metadata refresh (weekly)
    - Series completion (monthly)
    - Author completion (monthly)
    - Task cleanup (daily)

    Args:
        scheduler: APScheduler instance to register tasks with

    Usage:
        from backend.schedulers import initialize_scheduler, start_scheduler
        from backend.schedulers.register_tasks import register_all_tasks

        scheduler = initialize_scheduler()
        register_all_tasks(scheduler)
        start_scheduler()
    """
    settings = get_settings()

    # Only register tasks if scheduler is enabled
    if not settings.SCHEDULER_ENABLED:
        logger.warning("Scheduler is disabled in configuration, skipping task registration")
        return

    logger.info("Registering scheduled tasks...")

    # ========================================================================
    # Task 1: MAM Scraping (Daily 2:00 AM)
    # ========================================================================
    if settings.ENABLE_MAM_SCRAPING:
        scheduler.add_job(
            mam_scraping_task,
            trigger='cron',
            hour=2,
            minute=0,
            id='mam_scraping',
            name='Daily MAM Scraping',
            replace_existing=True
        )
        logger.info("✓ Registered: MAM Scraping (Daily 2:00 AM)")
    else:
        logger.info("✗ Skipped: MAM Scraping (disabled in config)")

    # ========================================================================
    # Task 2: Top-10 Discovery (Sunday 3:00 AM)
    # ========================================================================
    if settings.ENABLE_TOP10_DISCOVERY:
        scheduler.add_job(
            top10_discovery_task,
            trigger='cron',
            day_of_week='sun',
            hour=3,
            minute=0,
            id='top10_discovery',
            name='Weekly Top-10 Discovery',
            replace_existing=True
        )
        logger.info("✓ Registered: Top-10 Discovery (Sunday 3:00 AM)")
    else:
        logger.info("✗ Skipped: Top-10 Discovery (disabled in config)")

    # ========================================================================
    # Task 3: Full Metadata Refresh (1st of month 4:00 AM)
    # ========================================================================
    if settings.ENABLE_METADATA_CORRECTION:
        scheduler.add_job(
            metadata_full_refresh_task,
            trigger='cron',
            day=1,
            hour=4,
            minute=0,
            id='metadata_full',
            name='Monthly Full Metadata Refresh',
            replace_existing=True
        )
        logger.info("✓ Registered: Full Metadata Refresh (1st of month 4:00 AM)")
    else:
        logger.info("✗ Skipped: Full Metadata Refresh (disabled in config)")

    # ========================================================================
    # Task 4: New Books Metadata Refresh (Sunday 4:30 AM)
    # ========================================================================
    if settings.ENABLE_METADATA_CORRECTION:
        scheduler.add_job(
            metadata_new_books_task,
            trigger='cron',
            day_of_week='sun',
            hour=4,
            minute=30,
            id='metadata_new',
            name='Weekly New Books Metadata Refresh',
            replace_existing=True
        )
        logger.info("✓ Registered: New Books Metadata Refresh (Sunday 4:30 AM)")
    else:
        logger.info("✗ Skipped: New Books Metadata Refresh (disabled in config)")

    # ========================================================================
    # Task 5: Series Completion (2nd of month 3:00 AM)
    # ========================================================================
    if settings.ENABLE_SERIES_COMPLETION:
        scheduler.add_job(
            series_completion_task,
            trigger='cron',
            day=2,
            hour=3,
            minute=0,
            id='series_completion',
            name='Monthly Series Completion',
            replace_existing=True
        )
        logger.info("✓ Registered: Series Completion (2nd of month 3:00 AM)")
    else:
        logger.info("✗ Skipped: Series Completion (disabled in config)")

    # ========================================================================
    # Task 6: Author Completion (3rd of month 3:00 AM)
    # ========================================================================
    if settings.ENABLE_AUTHOR_COMPLETION:
        scheduler.add_job(
            author_completion_task,
            trigger='cron',
            day=3,
            hour=3,
            minute=0,
            id='author_completion',
            name='Monthly Author Completion',
            replace_existing=True
        )
        logger.info("✓ Registered: Author Completion (3rd of month 3:00 AM)")
    else:
        logger.info("✗ Skipped: Author Completion (disabled in config)")

    # ========================================================================
    # Task 7: Task Cleanup (Daily 1:00 AM)
    # ========================================================================
    scheduler.add_job(
        cleanup_old_tasks,
        trigger='cron',
        hour=1,
        minute=0,
        id='cleanup_tasks',
        name='Daily Task Cleanup',
        replace_existing=True
    )
    logger.info("✓ Registered: Task Cleanup (Daily 1:00 AM)")

    # ========================================================================
    # Task 7.5: Download Queue Processing (Every 30 Minutes)
    # ========================================================================
    scheduler.add_job(
        process_download_queue_task,
        trigger='interval',
        minutes=30,
        id='process_download_queue',
        name='Download Queue Processing',
        replace_existing=True
    )
    logger.info("✓ Registered: Download Queue Processing (Every 30 Minutes)")

    # ========================================================================
    # Phase 1 Tasks
    # ========================================================================

    # ========================================================================
    # Task 8: MAM Rules Scraping (Daily 12:00 PM)
    # ========================================================================
    scheduler.add_job(
        mam_rules_scraping_task,
        trigger='cron',
        hour=12,
        minute=0,
        id='mam_rules_scraping',
        name='Daily MAM Rules Scraping',
        replace_existing=True
    )
    logger.info("✓ Registered: MAM Rules Scraping (Daily 12:00 PM)")

    # ========================================================================
    # Task 9: Ratio Emergency Monitoring (Every 5 Minutes)
    # ========================================================================
    scheduler.add_job(
        ratio_emergency_monitoring_task,
        trigger='interval',
        minutes=5,
        id='ratio_emergency_monitoring',
        name='Continuous Ratio Emergency Monitoring',
        replace_existing=True
    )
    logger.info("✓ Registered: Ratio Emergency Monitoring (Every 5 minutes)")

    # ========================================================================
    # Phase 2 Tasks
    # ========================================================================

    # ========================================================================
    # Task 10: Weekly Metadata Maintenance (Sunday 5:00 AM)
    # ========================================================================
    scheduler.add_job(
        weekly_metadata_maintenance_task,
        trigger='cron',
        day_of_week='sun',
        hour=5,
        minute=0,
        id='metadata_maintenance_weekly',
        name='Weekly Metadata Maintenance',
        replace_existing=True
    )
    logger.info("✓ Registered: Weekly Metadata Maintenance (Sunday 5:00 AM)")

    # ========================================================================
    # Task 11: Weekly Category Sync (Sunday 6:00 AM)
    # ========================================================================
    scheduler.add_job(
        weekly_category_sync_task,
        trigger='cron',
        day_of_week='sun',
        hour=6,
        minute=0,
        id='category_sync_weekly',
        name='Weekly Category Synchronization',
        replace_existing=True
    )
    logger.info("✓ Registered: Weekly Category Synchronization (Sunday 6:00 AM)")

    # ========================================================================
    # Task 12: Weekly Seeding Management (Sunday 7:00 AM)
    # ========================================================================
    scheduler.add_job(
        weekly_seeding_management_task,
        trigger='cron',
        day_of_week='sun',
        hour=7,
        minute=0,
        id='seeding_management_weekly',
        name='Weekly Seeding Management',
        replace_existing=True
    )
    logger.info("✓ Registered: Weekly Seeding Management (Sunday 7:00 AM)")

    # ========================================================================
    # Task 13: Weekly Series/Author Completion (Monday 2:00 AM)
    # ========================================================================
    scheduler.add_job(
        series_author_completion_task,
        trigger='cron',
        day_of_week='mon',
        hour=2,
        minute=0,
        id='series_author_completion_weekly',
        name='Weekly Series/Author Completion',
        replace_existing=True
    )
    logger.info("✓ Registered: Weekly Series/Author Completion (Monday 2:00 AM)")

    # ========================================================================
    # VIP Management and Monitoring Tasks
    # ========================================================================

    # ========================================================================
    # Task 14: Daily VIP Status Check (12:00 PM UTC)
    # ========================================================================
    try:
        scheduler.add_job(
            daily_vip_management_task,
            trigger='cron',
            hour=12,
            minute=0,
            id='daily_vip_check',
            name='Daily VIP Status Check and Renewal (12:00 PM)',
            replace_existing=True,
            coalesce=True,
            max_instances=1
        )
        logger.info("✓ Registered: Daily VIP Status Check and Renewal (12:00 PM UTC)")
    except Exception as e:
        logger.error(f"Failed to register daily VIP check: {e}")

    # ========================================================================
    # Task 15: Continuous Ratio Monitoring (Every 5 Minutes)
    # ========================================================================
    # Note: This task is already registered as 'ratio_emergency_monitoring'
    # Keeping existing registration (Task 9) - no duplicate needed
    logger.info("✓ Ratio Emergency Monitoring already registered (Every 5 minutes)")

    # ========================================================================
    # Task 16: Weekly Metadata Sync (Sundays at 2:00 AM UTC)
    # ========================================================================
    try:
        scheduler.add_job(
            weekly_metadata_sync_task,
            trigger='cron',
            day_of_week='sun',
            hour=2,
            minute=0,
            id='weekly_metadata_sync',
            name='Weekly Metadata Sync (Sundays 2:00 AM)',
            replace_existing=True,
            coalesce=True,
            max_instances=1
        )
        logger.info("✓ Registered: Weekly Metadata Sync (Sundays 2:00 AM UTC)")
    except Exception as e:
        logger.error(f"Failed to register weekly metadata sync: {e}")

    # ========================================================================
    # Task 17: Monthly Drift Correction (First Sunday at 3:00 AM UTC)
    # ========================================================================
    try:
        scheduler.add_job(
            monthly_drift_correction_task,
            trigger='cron',
            day_of_week='sun',
            day='1-7',  # First week of month
            hour=3,
            minute=0,
            id='monthly_drift_correction',
            name='Monthly Metadata Drift Correction (First Sunday 3:00 AM)',
            replace_existing=True,
            coalesce=True,
            max_instances=1
        )
        logger.info("✓ Registered: Monthly Metadata Drift Correction (First Sunday 3:00 AM UTC)")
    except Exception as e:
        logger.error(f"Failed to register monthly drift correction: {e}")

    # ========================================================================
    # Task 18: Daily Metadata Update (Google Books API) (Daily 3:00 AM UTC)
    # ========================================================================
    try:
        scheduler.add_job(
            daily_metadata_update_task,
            trigger='cron',
            hour=3,
            minute=0,
            id='daily_metadata_update',
            name='Daily Metadata Update (Google Books API - 3:00 AM)',
            replace_existing=True,
            coalesce=True,
            max_instances=1
        )
        logger.info("✓ Registered: Daily Metadata Update (Google Books API - 3:00 AM UTC)")
    except Exception as e:
        logger.error(f"Failed to register daily metadata update: {e}")

    # ========================================================================
    # Phase 5: Automated Batch Repair (Saturday 8:00 AM)
    # ========================================================================
    try:
        scheduler.add_job(
            repair_batch_task,
            trigger='cron',
            day_of_week='sat',
            hour=8,
            minute=0,
            id='repair_batch',
            name='Weekly Automated Batch Repair',
            replace_existing=True,
            coalesce=True,
            max_instances=1
        )
        logger.info("✓ Registered: Weekly Automated Batch Repair (Saturday 8:00 AM)")
    except Exception as e:
        logger.error(f"Failed to register repair batch task: {e}")

    # ========================================================================
    # Summary
    # ========================================================================
    registered_count = len(scheduler.get_jobs())
    logger.info(f"Task registration complete: {registered_count} tasks registered")

    # Log next run times
    logger.info("Next scheduled executions:")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job.name}: {job.next_run_time}")


def unregister_all_tasks(scheduler: BackgroundScheduler) -> None:
    """
    Unregister all scheduled tasks

    Args:
        scheduler: APScheduler instance to unregister tasks from

    Usage:
        from backend.schedulers import get_scheduler
        from backend.schedulers.register_tasks import unregister_all_tasks

        scheduler = get_scheduler()
        unregister_all_tasks(scheduler)
    """
    logger.info("Unregistering all scheduled tasks...")

    job_ids = [
        'mam_scraping',
        'top10_discovery',
        'metadata_full',
        'metadata_new',
        'series_completion',
        'author_completion',
        'cleanup_tasks',
        'mam_rules_scraping',
        'ratio_emergency_monitoring',
        'metadata_maintenance_weekly',
        'category_sync_weekly',
        'seeding_management_weekly',
        'series_author_completion_weekly',
        'daily_vip_check',
        'weekly_metadata_sync',
        'monthly_drift_correction',
        'daily_metadata_update',
        'daily_metadata_update',
        'repair_batch',
        'process_download_queue'
    ]

    unregistered_count = 0
    for job_id in job_ids:
        try:
            scheduler.remove_job(job_id)
            logger.info(f"✓ Unregistered: {job_id}")
            unregistered_count += 1
        except Exception as e:
            logger.debug(f"✗ Job not found: {job_id} ({e})")

    logger.info(f"Task unregistration complete: {unregistered_count} tasks removed")


def register_task(
    scheduler: BackgroundScheduler,
    task_id: str
) -> bool:
    """
    Register a single task by ID

    Args:
        scheduler: APScheduler instance
        task_id: Task ID to register (e.g., 'mam_scraping')

    Returns:
        bool: True if task was registered, False otherwise

    Usage:
        from backend.schedulers import get_scheduler
        from backend.schedulers.register_tasks import register_task

        scheduler = get_scheduler()
        register_task(scheduler, 'mam_scraping')
    """
    settings = get_settings()

    task_registry = {
        'mam_scraping': {
            'func': mam_scraping_task,
            'trigger': 'cron',
            'hour': 2,
            'minute': 0,
            'name': 'Daily MAM Scraping',
            'enabled': settings.ENABLE_MAM_SCRAPING
        },
        'top10_discovery': {
            'func': top10_discovery_task,
            'trigger': 'cron',
            'day_of_week': 'sun',
            'hour': 3,
            'minute': 0,
            'name': 'Weekly Top-10 Discovery',
            'enabled': settings.ENABLE_TOP10_DISCOVERY
        },
        'metadata_full': {
            'func': metadata_full_refresh_task,
            'trigger': 'cron',
            'day': 1,
            'hour': 4,
            'minute': 0,
            'name': 'Monthly Full Metadata Refresh',
            'enabled': settings.ENABLE_METADATA_CORRECTION
        },
        'metadata_new': {
            'func': metadata_new_books_task,
            'trigger': 'cron',
            'day_of_week': 'sun',
            'hour': 4,
            'minute': 30,
            'name': 'Weekly New Books Metadata Refresh',
            'enabled': settings.ENABLE_METADATA_CORRECTION
        },
        'series_completion': {
            'func': series_completion_task,
            'trigger': 'cron',
            'day': 2,
            'hour': 3,
            'minute': 0,
            'name': 'Monthly Series Completion',
            'enabled': settings.ENABLE_SERIES_COMPLETION
        },
        'author_completion': {
            'func': author_completion_task,
            'trigger': 'cron',
            'day': 3,
            'hour': 3,
            'minute': 0,
            'name': 'Monthly Author Completion',
            'enabled': settings.ENABLE_AUTHOR_COMPLETION
        },
        'cleanup_tasks': {
            'func': cleanup_old_tasks,
            'trigger': 'cron',
            'hour': 1,
            'minute': 0,
            'name': 'Daily Task Cleanup',
            'enabled': True  # Always enabled
        },
        'mam_rules_scraping': {
            'func': mam_rules_scraping_task,
            'trigger': 'cron',
            'hour': 12,
            'minute': 0,
            'name': 'Daily MAM Rules Scraping',
            'enabled': True  # Phase 1 - Always enabled
        },
        'ratio_emergency_monitoring': {
            'func': ratio_emergency_monitoring_task,
            'trigger': 'interval',
            'minutes': 5,
            'name': 'Continuous Ratio Emergency Monitoring',
            'enabled': True  # Phase 1 - Always enabled
        },
        'metadata_maintenance_weekly': {
            'func': weekly_metadata_maintenance_task,
            'trigger': 'cron',
            'day_of_week': 'sun',
            'hour': 5,
            'minute': 0,
            'name': 'Weekly Metadata Maintenance',
            'enabled': True  # Phase 2 - Always enabled
        },
        'category_sync_weekly': {
            'func': weekly_category_sync_task,
            'trigger': 'cron',
            'day_of_week': 'sun',
            'hour': 6,
            'minute': 0,
            'name': 'Weekly Category Synchronization',
            'enabled': True  # Phase 2 - Always enabled
        },
        'seeding_management_weekly': {
            'func': weekly_seeding_management_task,
            'trigger': 'cron',
            'day_of_week': 'sun',
            'hour': 7,
            'minute': 0,
            'name': 'Weekly Seeding Management',
            'enabled': True  # Phase 2 - Always enabled
        },
        'series_author_completion_weekly': {
            'func': series_author_completion_task,
            'trigger': 'cron',
            'day_of_week': 'mon',
            'hour': 2,
            'minute': 0,
            'name': 'Weekly Series/Author Completion',
            'enabled': True  # Phase 2 - Always enabled
        },
        'daily_vip_check': {
            'func': daily_vip_management_task,
            'trigger': 'cron',
            'hour': 12,
            'minute': 0,
            'name': 'Daily VIP Status Check and Renewal (12:00 PM)',
            'enabled': True  # VIP Management - Always enabled
        },
        'weekly_metadata_sync': {
            'func': weekly_metadata_sync_task,
            'trigger': 'cron',
            'day_of_week': 'sun',
            'hour': 2,
            'minute': 0,
            'name': 'Weekly Metadata Sync (Sundays 2:00 AM)',
            'enabled': True  # Metadata Sync - Always enabled
        },
        'monthly_drift_correction': {
            'func': monthly_drift_correction_task,
            'trigger': 'cron',
            'day_of_week': 'sun',
            'day': '1-7',  # First week of month
            'hour': 3,
            'minute': 0,
            'name': 'Monthly Metadata Drift Correction (First Sunday 3:00 AM)',
            'enabled': True  # Drift Correction - Always enabled
        },
        'daily_metadata_update': {
            'func': daily_metadata_update_task,
            'trigger': 'cron',
            'hour': 3,
            'minute': 0,
            'name': 'Daily Metadata Update (Google Books API - 3:00 AM)',
            'enabled': True  # Daily Update - Always enabled
        },
        'repair_batch': {
            'func': repair_batch_task,
            'trigger': 'cron',
            'day_of_week': 'sat',
            'hour': 8,
            'minute': 0,
            'name': 'Weekly Automated Batch Repair',
            'enabled': True  # Phase 5 - Always enabled
        },
        'process_download_queue': {
            'func': process_download_queue_task,
            'trigger': 'interval',
            'minutes': 30,
            'name': 'Download Queue Processing',
            'enabled': True
        },
        'full_workflow_legacy': {
            'func': execute_full_workflow_task,
            'trigger': 'date', # On-demand only by default
            'run_date': None,
            'name': 'Full Workflow (Legacy)',
            'enabled': True
        }
    }

    if task_id not in task_registry:
        logger.error(f"Unknown task ID: {task_id}")
        return False

    task_config = task_registry[task_id]

    if not task_config['enabled']:
        logger.warning(f"Task is disabled in config: {task_id}")
        return False

    try:
        scheduler.add_job(
            task_config['func'],
            trigger=task_config['trigger'],
            hour=task_config.get('hour'),
            minute=task_config.get('minute'),
            day=task_config.get('day'),
            day_of_week=task_config.get('day_of_week'),
            id=task_id,
            name=task_config['name'],
            replace_existing=True
        )
        logger.info(f"✓ Registered: {task_config['name']}")
        return True

    except Exception as e:
        logger.error(f"Failed to register task {task_id}: {e}")
        return False
