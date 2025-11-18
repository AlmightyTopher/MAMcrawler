# APScheduler System - Backend Schedulers

This directory contains the APScheduler setup for the Audiobook Automation System.

## Files

### Core Files

1. **scheduler.py** (9.0 KB)
   - Global scheduler instance with thread-safe singleton pattern
   - SQLAlchemy job store configuration
   - Event listeners for job execution monitoring
   - Utility functions for scheduler management

2. **tasks.py** (21 KB)
   - All 6 scheduled task handler functions
   - Task database record management utilities
   - Comprehensive error handling and logging
   - Placeholder implementations for Phase 4 integration

3. **__init__.py** (1.1 KB)
   - Package initialization
   - Exports all public functions

### Documentation

4. **USAGE.md**
   - Comprehensive usage guide
   - Quick start examples
   - Integration with FastAPI
   - Monitoring and troubleshooting

5. **README.md** (this file)
   - Package overview
   - File structure
   - Implementation status

6. **requirements.txt**
   - APScheduler dependency specification

## Scheduled Tasks

| Task Name | Function | Schedule | Status |
|-----------|----------|----------|--------|
| MAM Scraping | `mam_scraping_task()` | Daily 2:00 AM | Phase 3 ✓ |
| Top-10 Discovery | `top10_discovery_task()` | Sunday 3:00 AM | Phase 3 ✓ |
| Full Metadata Refresh | `metadata_full_refresh_task()` | 1st of month 4:00 AM | Phase 3 ✓ |
| New Books Metadata | `metadata_new_books_task()` | Sunday 4:30 AM | Phase 3 ✓ |
| Series Completion | `series_completion_task()` | 2nd of month 3:00 AM | Phase 3 ✓ |
| Author Completion | `author_completion_task()` | 3rd of month 3:00 AM | Phase 3 ✓ |
| Task Cleanup | `cleanup_old_tasks()` | Daily 1:00 AM | Phase 3 ✓ |

## Implementation Status

### Phase 3 (Current) ✓
- [x] Scheduler manager with SQLAlchemy job store
- [x] Thread-safe singleton pattern
- [x] Event listeners for monitoring
- [x] All 6 task handler functions
- [x] Task database record management
- [x] Error handling and logging
- [x] Placeholder implementations
- [x] Comprehensive documentation

### Phase 4 (Next)
- [ ] Connect tasks to module wrappers
- [ ] MAM crawler integration
- [ ] Top-10 discovery integration
- [ ] Metadata correction integration
- [ ] Series completion integration
- [ ] Author completion integration
- [ ] Integration testing

## Architecture

### Scheduler Manager (scheduler.py)

```
┌─────────────────────────────────────────┐
│    Global Scheduler Instance (_scheduler)│
│    Thread-safe with Lock                │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
┌──────────────┐  ┌──────────────┐
│  Job Store   │  │  Executors   │
│  (SQLAlchemy)│  │  (ThreadPool)│
└──────────────┘  └──────────────┘
       │               │
       └───────┬───────┘
               ▼
     ┌─────────────────┐
     │ Event Listeners │
     │  - Executed     │
     │  - Error        │
     │  - Missed       │
     └─────────────────┘
```

### Task Execution Flow (tasks.py)

```
1. Scheduled Time Reached
   ↓
2. Create Task Record (status='running')
   ↓
3. Execute Task Logic
   │
   ├─ Success → update_task_success()
   │            - Set status='completed'
   │            - Record metrics
   │            - Save logs
   │
   └─ Failure → update_task_failure()
                - Set status='failed'
                - Record error
                - Save partial logs
```

## Database Integration

### Task Table Fields

Tasks are tracked in the `tasks` table with these fields:

- **id**: Primary key
- **task_name**: Task identifier (MAM, TOP10, etc.)
- **scheduled_time**: When task was scheduled
- **actual_start**: When task started
- **actual_end**: When task ended
- **duration_seconds**: Execution time
- **status**: scheduled | running | completed | failed
- **items_processed**: Total items
- **items_succeeded**: Successful items
- **items_failed**: Failed items
- **log_output**: Full execution log
- **error_message**: Error details (if failed)
- **metadata**: Task-specific JSON metadata
- **date_created**: Record creation time

### Retention Policy

- Task records older than 30 days are automatically deleted
- Handled by `cleanup_old_tasks()` running daily at 1:00 AM
- Configured via `HISTORY_RETENTION_DAYS` in settings

## Installation

```bash
# Install APScheduler
pip install -r backend/schedulers/requirements.txt

# Or install directly
pip install APScheduler==3.10.4
```

## Quick Start

### 1. Initialize Scheduler (Application Startup)

```python
from backend.schedulers import initialize_scheduler, start_scheduler
from backend.schedulers.tasks import mam_scraping_task

# Initialize
scheduler = initialize_scheduler()

# Register jobs
scheduler.add_job(
    mam_scraping_task,
    trigger='cron',
    hour=2,
    minute=0,
    id='mam_scraping',
    name='Daily MAM Scraping'
)

# Start
start_scheduler()
```

### 2. Monitor Execution

```python
from backend.database import get_db_context
from backend.models.task import Task

with get_db_context() as db:
    recent_tasks = db.query(Task).order_by(Task.date_created.desc()).limit(10).all()
    for task in recent_tasks:
        print(f"{task.task_name}: {task.status} ({task.items_succeeded}/{task.items_processed})")
```

### 3. Shutdown (Application Teardown)

```python
from backend.schedulers import shutdown_scheduler

# Graceful shutdown
shutdown_scheduler(wait=True)
```

## Features

### Thread Safety
- Singleton pattern with double-checked locking
- Safe concurrent access from multiple threads
- Thread pool executor for parallel task execution

### Monitoring
- Event listeners for all job executions
- Comprehensive logging (INFO, ERROR, WARNING)
- Database record of all executions

### Error Handling
- Try/except blocks in all tasks
- Detailed error messages with tracebacks
- Task status tracking (failed vs completed)
- Failed attempt tracking (separate table)

### Configuration
- All settings loaded from environment variables
- Configurable schedules via cron expressions
- Adjustable retention policies
- Feature flags for enabling/disabling tasks

## Testing

```bash
# Test imports
python -c "from backend.schedulers import initialize_scheduler; print('Success')"

# Test scheduler initialization (requires database)
python -c "
from backend.schedulers import initialize_scheduler, start_scheduler
scheduler = initialize_scheduler()
print(f'Scheduler created: {scheduler}')
"

# Test task registration
python -c "
from backend.schedulers import initialize_scheduler
from backend.schedulers.tasks import mam_scraping_task
scheduler = initialize_scheduler()
scheduler.add_job(mam_scraping_task, 'interval', minutes=1, id='test')
print(f'Jobs: {scheduler.get_jobs()}')
"
```

## Troubleshooting

### ModuleNotFoundError: No module named 'apscheduler'
```bash
pip install APScheduler==3.10.4
```

### RuntimeError: Scheduler has not been initialized
```python
from backend.schedulers import initialize_scheduler
scheduler = initialize_scheduler()
```

### Jobs not executing
1. Check scheduler is running: `is_scheduler_running()`
2. Check jobs are registered: `get_scheduled_jobs()`
3. Check logs for errors
4. Verify database connection

### Database errors
1. Verify PostgreSQL is running
2. Check DATABASE_URL in .env
3. Ensure database exists
4. Check credentials

## Next Steps (Phase 4)

1. **Create module wrappers** in `backend/modules/`
   - `mam_crawler.py` - Wrapper for stealth_mam_crawler
   - `top10_discovery.py` - Top-10 genre scraper
   - `metadata_correction.py` - Google Books + Goodreads pipeline
   - `series_completion.py` - Series completion logic
   - `author_completion.py` - Author completion logic

2. **Replace placeholder implementations**
   - Import module wrappers in tasks.py
   - Call actual functions instead of placeholders
   - Process real results

3. **Integration testing**
   - Test each task end-to-end
   - Verify database records
   - Monitor execution logs

4. **Production deployment**
   - Set up monitoring/alerting
   - Configure backup schedules
   - Test failure scenarios

## Related Documentation

- **USAGE.md** - Detailed usage guide with examples
- **backend/config.py** - Configuration settings
- **backend/models/task.py** - Task database model
- **backend/database.py** - Database connection management

## License

Part of the Audiobook Automation System project.
