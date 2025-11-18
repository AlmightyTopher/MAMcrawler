"""
Schedulers Package for Audiobook Automation System
Provides APScheduler management and scheduled task handlers
"""

from .scheduler import (
    initialize_scheduler,
    get_scheduler,
    start_scheduler,
    shutdown_scheduler,
    is_scheduler_running,
    get_scheduled_jobs,
    pause_job,
    resume_job,
    remove_job
)

from .tasks import (
    mam_scraping_task,
    top10_discovery_task,
    metadata_full_refresh_task,
    metadata_new_books_task,
    series_completion_task,
    author_completion_task,
    cleanup_old_tasks
)

from .register_tasks import (
    register_all_tasks,
    unregister_all_tasks,
    register_task
)

__all__ = [
    # Scheduler management
    'initialize_scheduler',
    'get_scheduler',
    'start_scheduler',
    'shutdown_scheduler',
    'is_scheduler_running',
    'get_scheduled_jobs',
    'pause_job',
    'resume_job',
    'remove_job',

    # Scheduled tasks
    'mam_scraping_task',
    'top10_discovery_task',
    'metadata_full_refresh_task',
    'metadata_new_books_task',
    'series_completion_task',
    'author_completion_task',
    'cleanup_old_tasks',

    # Task registration
    'register_all_tasks',
    'unregister_all_tasks',
    'register_task',
]
