# APScheduler Usage Guide

This guide explains how to use the APScheduler system for the Audiobook Automation System.

## Overview

The scheduler system consists of two main files:

1. **scheduler.py** - Manages the APScheduler instance with SQLAlchemy job store
2. **tasks.py** - Defines all scheduled task handler functions

## Quick Start

### Initialization (Application Startup)

```python
from backend.schedulers import initialize_scheduler, start_scheduler
from backend.schedulers.tasks import (
    mam_scraping_task,
    top10_discovery_task,
    metadata_full_refresh_task,
    metadata_new_books_task,
    series_completion_task,
    author_completion_task,
    cleanup_old_tasks
)

# Initialize scheduler (creates global instance)
scheduler = initialize_scheduler()

# Register scheduled tasks
scheduler.add_job(
    mam_scraping_task,
    trigger='cron',
    hour=2,
    minute=0,
    id='mam_scraping',
    name='Daily MAM Scraping',
    replace_existing=True
)

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

scheduler.add_job(
    cleanup_old_tasks,
    trigger='cron',
    hour=1,
    minute=0,
    id='cleanup_tasks',
    name='Daily Task Cleanup',
    replace_existing=True
)

# Start scheduler (begins executing jobs)
start_scheduler()
```

### Shutdown (Application Teardown)

```python
from backend.schedulers import shutdown_scheduler

# Graceful shutdown (waits for running jobs to finish)
shutdown_scheduler(wait=True)

# Or immediate shutdown (don't wait for jobs)
shutdown_scheduler(wait=False)
```

## Task Schedules

| Task | Schedule | Description |
|------|----------|-------------|
| **mam_scraping_task** | Daily 2:00 AM | Crawl MAM for new guides and torrents |
| **top10_discovery_task** | Sunday 3:00 AM | Scrape MAM top-10 for enabled genres |
| **metadata_full_refresh_task** | 1st of month 4:00 AM | Refresh metadata for ALL books |
| **metadata_new_books_task** | Sunday 4:30 AM | Refresh metadata for books added in last 7 days |
| **series_completion_task** | 2nd of month 3:00 AM | Download missing books in series |
| **author_completion_task** | 3rd of month 3:00 AM | Download missing audiobooks by authors |
| **cleanup_old_tasks** | Daily 1:00 AM | Delete task records older than 30 days |

## Scheduler Features

### Thread-Safe Singleton

The scheduler uses a thread-safe singleton pattern:

```python
from backend.schedulers import get_scheduler

# Get scheduler instance (anywhere in your code)
scheduler = get_scheduler()

# All calls return the same instance
assert scheduler is get_scheduler()
```

### Job Management

```python
from backend.schedulers import (
    get_scheduled_jobs,
    pause_job,
    resume_job,
    remove_job
)

# Get all scheduled jobs
jobs = get_scheduled_jobs()
for job in jobs:
    print(f"{job.id}: {job.name} (next run: {job.next_run_time})")

# Pause a job
pause_job('mam_scraping')

# Resume a paused job
resume_job('mam_scraping')

# Remove a job
remove_job('mam_scraping')
```

### Event Listeners

The scheduler automatically logs job execution events:

- **Job Executed**: Logs successful job completion
- **Job Error**: Logs job execution errors
- **Job Missed**: Logs missed job executions (e.g., system was down)

### Job Configuration

Default job settings (configured in `scheduler.py`):

```python
job_defaults = {
    'coalesce': True,        # Combine multiple pending executions
    'max_instances': 1,      # Only one instance per job
    'misfire_grace_time': 900  # 15 minutes grace period
}
```

## Task Implementation Details

### Task Record Lifecycle

Each task follows this lifecycle:

1. **Create Task Record** (status='running')
   ```python
   task = create_task_record(db, 'MAM')
   ```

2. **Execute Task Logic**
   ```python
   # ... do work ...
   items_processed = 100
   items_succeeded = 95
   items_failed = 5
   ```

3. **Update Task Record**
   - **Success**:
     ```python
     update_task_success(db, task, items_processed, items_succeeded, items_failed, log_output)
     ```
   - **Failure**:
     ```python
     update_task_failure(db, task, error_message, log_output)
     ```

### Error Handling

All tasks include comprehensive error handling:

```python
try:
    # Task logic
    ...
except Exception as e:
    error_msg = f"Task failed: {str(e)}\n{traceback.format_exc()}"
    update_task_failure(db, task, error_message=error_msg)
    logger.error(error_msg)
    raise
```

### Database Access

Tasks use context managers for database access:

```python
from backend.database import get_db_context

with get_db_context() as db:
    # Database operations
    task = create_task_record(db, 'MAM')
    # ... work ...
    update_task_success(db, task, ...)
```

## Integration with FastAPI

### Startup Event

```python
from fastapi import FastAPI
from backend.schedulers import initialize_scheduler, start_scheduler

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    # Initialize database
    init_db()

    # Initialize and start scheduler
    scheduler = initialize_scheduler()

    # Register jobs (see Quick Start)
    # ...

    start_scheduler()
```

### Shutdown Event

```python
@app.on_event("shutdown")
async def shutdown_event():
    shutdown_scheduler(wait=True)
```

## Monitoring

### Check Scheduler Status

```python
from backend.schedulers import is_scheduler_running

if is_scheduler_running():
    print("Scheduler is running")
else:
    print("Scheduler is stopped")
```

### View Task History

Query the `tasks` table to view execution history:

```python
from backend.database import get_db_context
from backend.models.task import Task
from sqlalchemy import desc

with get_db_context() as db:
    # Get recent tasks
    recent_tasks = db.query(Task)\
        .order_by(desc(Task.date_created))\
        .limit(10)\
        .all()

    for task in recent_tasks:
        print(f"{task.task_name}: {task.status} ({task.items_succeeded}/{task.items_processed})")
```

## Phase 4 Integration

In Phase 4, tasks will be connected to actual module wrappers:

```python
# TODO (Phase 4): Replace placeholder implementations

# Before (Phase 3)
items_processed = 0
items_succeeded = 0
items_failed = 0

# After (Phase 4)
from backend.modules.mam_crawler import run_stealth_crawler
result = await run_stealth_crawler()
items_processed = len(result['guides'])
items_succeeded = len([g for g in result['guides'] if g['status'] == 'success'])
items_failed = items_processed - items_succeeded
```

## Troubleshooting

### Scheduler Not Starting

```python
# Check if scheduler is initialized
try:
    scheduler = get_scheduler()
except RuntimeError as e:
    print(f"Scheduler not initialized: {e}")
    scheduler = initialize_scheduler()
```

### Jobs Not Executing

1. Check scheduler is running: `is_scheduler_running()`
2. Check job is registered: `get_scheduled_jobs()`
3. Check job is not paused: `scheduler.get_job('job_id').state`
4. Check logs for errors

### Database Connection Issues

- Verify `DATABASE_URL` in `.env`
- Check PostgreSQL is running
- Verify database exists and credentials are correct

## Best Practices

1. **Always use context managers** for database access
2. **Log comprehensively** - include timestamps and details
3. **Track metrics** - items_processed, items_succeeded, items_failed
4. **Handle errors gracefully** - use try/except blocks
5. **Update task status** - ensure task records are always updated
6. **Use meaningful task names** - helps with debugging and monitoring
7. **Set appropriate timeouts** - prevent tasks from hanging indefinitely
8. **Test scheduler logic** - verify jobs execute at expected times
