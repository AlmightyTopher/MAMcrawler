# APScheduler Setup - Implementation Summary

## Overview

Created complete APScheduler system for the Audiobook Automation System with:
- Thread-safe scheduler manager
- 6 scheduled task handlers with database tracking
- Task registration helper
- Comprehensive documentation and examples

## Files Created

### Core Implementation (3 files)

1. **scheduler.py** (9.0 KB)
   - `initialize_scheduler()` - Create scheduler with SQLAlchemy job store
   - `get_scheduler()` - Thread-safe singleton access
   - `start_scheduler()` - Start executing jobs
   - `shutdown_scheduler()` - Graceful shutdown
   - Event listeners for monitoring
   - Utility functions (pause, resume, remove jobs)

2. **tasks.py** (21 KB)
   - `mam_scraping_task()` - Daily MAM crawler
   - `top10_discovery_task()` - Weekly top-10 genre discovery
   - `metadata_full_refresh_task()` - Monthly full metadata refresh
   - `metadata_new_books_task()` - Weekly new books metadata
   - `series_completion_task()` - Monthly series completion
   - `author_completion_task()` - Monthly author completion
   - `cleanup_old_tasks()` - Daily task cleanup (30-day retention)
   - Task record management utilities

3. **register_tasks.py** (12 KB)
   - `register_all_tasks()` - Register all 7 tasks at once
   - `unregister_all_tasks()` - Remove all tasks
   - `register_task()` - Register individual task by ID
   - Feature flag integration (respects config settings)

### Package Files (2 files)

4. **__init__.py** (1.3 KB)
   - Package initialization
   - Exports all public functions
   - Clean API surface

5. **requirements.txt** (430 bytes)
   - APScheduler dependency specification
   - Version pinning for stability

### Documentation (4 files)

6. **README.md** (9.0 KB)
   - Package overview and architecture
   - Implementation status
   - Quick start guide
   - Testing instructions
   - Phase 4 integration roadmap

7. **USAGE.md** (8.8 KB)
   - Comprehensive usage guide
   - Initialization examples
   - Task schedule reference
   - Monitoring and troubleshooting
   - Best practices

8. **INTEGRATION_EXAMPLE.py** (7.3 KB)
   - Complete FastAPI integration example
   - Lifespan management
   - API endpoints for scheduler management
   - Task history endpoints

9. **SUMMARY.md** (this file)
   - Implementation overview
   - File listing and descriptions
   - Next steps

## Task Schedule Reference

| Task | Schedule | Cron Expression | Purpose |
|------|----------|----------------|---------|
| MAM Scraping | Daily 2:00 AM | `0 2 * * *` | Crawl MAM for guides/torrents |
| Top-10 Discovery | Sunday 3:00 AM | `0 3 * * 6` | Scrape top-10 for enabled genres |
| Full Metadata | 1st 4:00 AM | `0 4 1 * *` | Refresh all book metadata |
| New Books Metadata | Sunday 4:30 AM | `30 4 * * 6` | Refresh recent books metadata |
| Series Completion | 2nd 3:00 AM | `0 3 2 * *` | Download missing series books |
| Author Completion | 3rd 3:00 AM | `0 3 3 * *` | Download missing author books |
| Task Cleanup | Daily 1:00 AM | `0 1 * * *` | Delete old task records (30d) |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Application                        │
│                                                              │
│  Startup: initialize_scheduler() + register_all_tasks()     │
│  Shutdown: shutdown_scheduler(wait=True)                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              APScheduler (BackgroundScheduler)               │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Job Store   │  │  Executors   │  │   Triggers   │     │
│  │ (SQLAlchemy) │  │(ThreadPool)  │  │    (Cron)    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Scheduled Tasks                           │
│                                                              │
│  mam_scraping_task()          → MAM Crawler Module          │
│  top10_discovery_task()       → Top-10 Module               │
│  metadata_full_refresh_task() → Metadata Module             │
│  metadata_new_books_task()    → Metadata Module             │
│  series_completion_task()     → Series Module               │
│  author_completion_task()     → Author Module               │
│  cleanup_old_tasks()          → Database Cleanup            │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   PostgreSQL Database                        │
│                                                              │
│  tasks (execution history, 30-day retention)                 │
│  failed_attempts (permanent retention)                       │
│  apscheduler_jobs (job store persistence)                    │
└─────────────────────────────────────────────────────────────┘
```

## Task Execution Flow

```
1. Scheduled Time Reached
   │
   ├─ APScheduler triggers job
   │
2. Task Handler Called (e.g., mam_scraping_task)
   │
   ├─ Create Task record (status='running')
   │  ├─ task_name: 'MAM'
   │  ├─ actual_start: now()
   │  └─ status: 'running'
   │
3. Execute Task Logic
   │
   ├─ Call module wrapper (Phase 4)
   │  └─ from backend.modules.mam_crawler import run_stealth_crawler
   │
   ├─ Process results
   │  ├─ items_processed: 100
   │  ├─ items_succeeded: 95
   │  └─ items_failed: 5
   │
4. Update Task Record
   │
   ├─ SUCCESS:
   │  ├─ status: 'completed'
   │  ├─ actual_end: now()
   │  ├─ duration_seconds: calculated
   │  ├─ items_processed/succeeded/failed
   │  └─ log_output: full logs
   │
   └─ FAILURE:
      ├─ status: 'failed'
      ├─ actual_end: now()
      ├─ duration_seconds: calculated
      ├─ error_message: exception details
      └─ log_output: partial logs
```

## Feature Highlights

### 1. Thread-Safe Singleton Pattern
```python
# Global scheduler instance with lock-based thread safety
_scheduler: Optional[BackgroundScheduler] = None
_scheduler_lock = Lock()

# Double-checked locking in initialize_scheduler()
if _scheduler is None:
    with _scheduler_lock:
        if _scheduler is None:
            _scheduler = BackgroundScheduler(...)
```

### 2. Event Listeners
```python
# Automatic logging of all job executions
scheduler.add_listener(_job_executed_listener, EVENT_JOB_EXECUTED)
scheduler.add_listener(_job_error_listener, EVENT_JOB_ERROR)
scheduler.add_listener(_job_missed_listener, EVENT_JOB_MISSED)
```

### 3. Database Task Tracking
```python
# Every task execution creates a database record
task = create_task_record(db, 'MAM')

# Comprehensive metrics tracking
update_task_success(
    db, task,
    items_processed=100,
    items_succeeded=95,
    items_failed=5,
    log_output=logs
)
```

### 4. Feature Flag Integration
```python
# Tasks respect configuration settings
if settings.ENABLE_MAM_SCRAPING:
    scheduler.add_job(mam_scraping_task, ...)
else:
    logger.info("MAM scraping disabled in config")
```

### 5. Error Handling
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

## Installation

```bash
# Install APScheduler dependency
pip install APScheduler==3.10.4

# Or use requirements file
pip install -r backend/schedulers/requirements.txt
```

## Quick Start

```python
from backend.schedulers import initialize_scheduler, start_scheduler
from backend.schedulers.register_tasks import register_all_tasks

# 1. Initialize scheduler
scheduler = initialize_scheduler()

# 2. Register all tasks
register_all_tasks(scheduler)

# 3. Start scheduler
start_scheduler()

# 4. Shutdown (on application exit)
shutdown_scheduler(wait=True)
```

## Integration with FastAPI

See `INTEGRATION_EXAMPLE.py` for complete implementation.

Key points:
- Use lifespan context manager (FastAPI 0.93+)
- Initialize scheduler in startup
- Register tasks before starting
- Graceful shutdown with wait=True

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    scheduler = initialize_scheduler()
    register_all_tasks(scheduler)
    start_scheduler()

    yield

    # Shutdown
    shutdown_scheduler(wait=True)
    close_db()

app = FastAPI(lifespan=lifespan)
```

## Testing

```bash
# Test imports (requires APScheduler installed)
python -c "from backend.schedulers import initialize_scheduler; print('OK')"

# Test scheduler initialization
python -c "
from backend.schedulers import initialize_scheduler, start_scheduler
scheduler = initialize_scheduler()
print(f'Scheduler: {scheduler}')
"

# Test task registration
python -c "
from backend.schedulers import initialize_scheduler
from backend.schedulers.register_tasks import register_all_tasks
scheduler = initialize_scheduler()
register_all_tasks(scheduler)
print(f'Jobs: {len(scheduler.get_jobs())}')
"
```

## Phase 4 Integration Tasks

### 1. Create Module Wrappers (backend/modules/)

- `mam_crawler.py` - Wrapper for stealth_mam_crawler.py
- `top10_discovery.py` - MAM top-10 scraper
- `metadata_correction.py` - Google Books + Goodreads pipeline
- `series_completion.py` - Series discovery and download
- `author_completion.py` - Author catalog and download

### 2. Update Task Functions

Replace placeholder implementations in tasks.py:

```python
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

### 3. Integration Testing

- Test each task individually
- Verify database records
- Check log output
- Monitor execution times
- Test error handling

### 4. Production Deployment

- Set up monitoring/alerting
- Configure backup schedules
- Test failure scenarios
- Document operational procedures

## Current Status

### Phase 3 Complete ✓

- [x] Scheduler manager implementation
- [x] Thread-safe singleton pattern
- [x] SQLAlchemy job store configuration
- [x] Event listeners for monitoring
- [x] All 6 task handler functions
- [x] Task record management utilities
- [x] Error handling and logging
- [x] Task registration helper
- [x] Comprehensive documentation
- [x] Integration examples
- [x] Requirements specification

### Phase 4 Next Steps

- [ ] Create module wrappers
- [ ] Connect tasks to modules
- [ ] Integration testing
- [ ] Production deployment

## Configuration Reference

All settings in `backend/config.py`:

```python
# Scheduler
SCHEDULER_ENABLED: bool = True
SCHEDULER_JOB_STORE: str = "sqlalchemy"

# Task Schedules (cron format)
TASK_MAM_TIME: str = "0 2 * * *"           # Daily 2:00 AM
TASK_TOP10_TIME: str = "0 3 * * 6"         # Sunday 3:00 AM
TASK_METADATA_FULL_TIME: str = "0 4 1 * *" # 1st 4:00 AM
TASK_METADATA_NEW_TIME: str = "30 4 * * 6" # Sunday 4:30 AM
TASK_SERIES_TIME: str = "0 3 2 * *"        # 2nd 3:00 AM
TASK_AUTHOR_TIME: str = "0 3 3 * *"        # 3rd 3:00 AM

# Retention
HISTORY_RETENTION_DAYS: int = 30

# Feature Flags
ENABLE_MAM_SCRAPING: bool = True
ENABLE_TOP10_DISCOVERY: bool = True
ENABLE_METADATA_CORRECTION: bool = True
ENABLE_SERIES_COMPLETION: bool = True
ENABLE_AUTHOR_COMPLETION: bool = True
```

## API Endpoints

See `INTEGRATION_EXAMPLE.py` for implementation:

- `GET /scheduler/status` - Get scheduler status
- `GET /scheduler/jobs` - List all scheduled jobs
- `POST /scheduler/jobs/{job_id}/pause` - Pause a job
- `POST /scheduler/jobs/{job_id}/resume` - Resume a job
- `GET /tasks/recent` - Get recent task execution history
- `GET /tasks/{task_id}` - Get task details

## Monitoring

### Scheduler Status
```python
from backend.schedulers import is_scheduler_running, get_scheduled_jobs

if is_scheduler_running():
    jobs = get_scheduled_jobs()
    for job in jobs:
        print(f"{job.id}: next run at {job.next_run_time}")
```

### Task History
```python
from backend.database import get_db_context
from backend.models.task import Task

with get_db_context() as db:
    recent = db.query(Task).order_by(Task.date_created.desc()).limit(10).all()
    for task in recent:
        print(f"{task.task_name}: {task.status} ({task.items_succeeded}/{task.items_processed})")
```

## Troubleshooting

See `USAGE.md` for detailed troubleshooting guide.

Common issues:
- **ModuleNotFoundError**: Install APScheduler
- **RuntimeError**: Call initialize_scheduler()
- **Jobs not executing**: Check scheduler is running
- **Database errors**: Verify PostgreSQL connection

## Related Files

- `backend/config.py` - Application configuration
- `backend/database.py` - Database connection
- `backend/models/task.py` - Task ORM model
- `backend/models/failed_attempt.py` - Failed attempt tracking
- `backend/main.py` - FastAPI application (integrate here)

## License

Part of the Audiobook Automation System project.
