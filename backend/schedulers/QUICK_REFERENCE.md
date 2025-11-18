# APScheduler Quick Reference Card

## Installation
```bash
pip install APScheduler==3.10.4
```

## Basic Usage

### Initialize and Start
```python
from backend.schedulers import initialize_scheduler, start_scheduler
from backend.schedulers.register_tasks import register_all_tasks

scheduler = initialize_scheduler()
register_all_tasks(scheduler)
start_scheduler()
```

### Shutdown
```python
from backend.schedulers import shutdown_scheduler
shutdown_scheduler(wait=True)
```

## Task Schedule

| Task | When | Cron |
|------|------|------|
| MAM Scraping | Daily 2:00 AM | `0 2 * * *` |
| Top-10 Discovery | Sunday 3:00 AM | `0 3 * * 6` |
| Full Metadata | 1st 4:00 AM | `0 4 1 * *` |
| New Books Metadata | Sunday 4:30 AM | `30 4 * * 6` |
| Series Completion | 2nd 3:00 AM | `0 3 2 * *` |
| Author Completion | 3rd 3:00 AM | `0 3 3 * *` |
| Task Cleanup | Daily 1:00 AM | `0 1 * * *` |

## Management Commands

### Check Status
```python
from backend.schedulers import is_scheduler_running
is_scheduler_running()  # True/False
```

### List Jobs
```python
from backend.schedulers import get_scheduled_jobs
for job in get_scheduled_jobs():
    print(f"{job.id}: {job.next_run_time}")
```

### Pause/Resume Job
```python
from backend.schedulers import pause_job, resume_job
pause_job('mam_scraping')
resume_job('mam_scraping')
```

### Remove Job
```python
from backend.schedulers import remove_job
remove_job('mam_scraping')
```

## Task History

### Get Recent Tasks
```python
from backend.database import get_db_context
from backend.models.task import Task
from sqlalchemy import desc

with get_db_context() as db:
    tasks = db.query(Task).order_by(desc(Task.date_created)).limit(10).all()
    for t in tasks:
        print(f"{t.task_name}: {t.status} ({t.items_succeeded}/{t.items_processed})")
```

### Get Task Details
```python
with get_db_context() as db:
    task = db.query(Task).filter(Task.id == task_id).first()
    print(task.log_output)
```

## FastAPI Integration

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from backend.schedulers import initialize_scheduler, start_scheduler
    from backend.schedulers.register_tasks import register_all_tasks

    scheduler = initialize_scheduler()
    register_all_tasks(scheduler)
    start_scheduler()

    yield

    # Shutdown
    from backend.schedulers import shutdown_scheduler
    shutdown_scheduler(wait=True)

app = FastAPI(lifespan=lifespan)
```

## Configuration (.env)

```bash
# Scheduler
SCHEDULER_ENABLED=true

# Feature Flags
ENABLE_MAM_SCRAPING=true
ENABLE_TOP10_DISCOVERY=true
ENABLE_METADATA_CORRECTION=true
ENABLE_SERIES_COMPLETION=true
ENABLE_AUTHOR_COMPLETION=true

# Retention
HISTORY_RETENTION_DAYS=30

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/db
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| ModuleNotFoundError | `pip install APScheduler` |
| RuntimeError: not initialized | Call `initialize_scheduler()` |
| Jobs not running | Check `is_scheduler_running()` |
| Database error | Verify PostgreSQL connection |

## File Structure

```
backend/schedulers/
├── __init__.py              # Package exports
├── scheduler.py             # Scheduler manager
├── tasks.py                 # Task handlers
├── register_tasks.py        # Task registration
├── requirements.txt         # Dependencies
├── README.md                # Full documentation
├── USAGE.md                 # Usage guide
├── SUMMARY.md               # Implementation summary
├── INTEGRATION_EXAMPLE.py   # FastAPI example
└── QUICK_REFERENCE.md       # This file
```

## Task Function Signatures

```python
async def mam_scraping_task() -> None
async def top10_discovery_task() -> None
async def metadata_full_refresh_task() -> None
async def metadata_new_books_task() -> None
async def series_completion_task() -> None
async def author_completion_task() -> None
async def cleanup_old_tasks() -> None
```

## Database Schema

### tasks table
- id (PK)
- task_name (MAM, TOP10, etc.)
- scheduled_time
- actual_start
- actual_end
- duration_seconds
- status (scheduled, running, completed, failed)
- items_processed
- items_succeeded
- items_failed
- log_output (TEXT)
- error_message (TEXT)
- metadata (JSON)
- date_created

## API Endpoints (Optional)

```python
GET  /scheduler/status          # Scheduler status
GET  /scheduler/jobs            # List jobs
POST /scheduler/jobs/{id}/pause # Pause job
POST /scheduler/jobs/{id}/resume # Resume job
GET  /tasks/recent              # Recent task history
GET  /tasks/{id}                # Task details
```

## Next Steps (Phase 4)

1. Create module wrappers in `backend/modules/`
2. Replace placeholders in `tasks.py`
3. Test each task end-to-end
4. Deploy to production
