"""
APScheduler Integration Example for FastAPI Application

This example shows how to integrate the scheduler system into the main FastAPI application.
Copy the relevant sections into backend/main.py.
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging

from backend.database import init_db, close_db
from backend.schedulers import (
    initialize_scheduler,
    start_scheduler,
    shutdown_scheduler
)
from backend.schedulers.register_tasks import register_all_tasks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# ============================================================================
# Application Lifespan Management
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager
    Handles application startup and shutdown events
    """
    # ========================================================================
    # STARTUP
    # ========================================================================
    logger.info("Starting Audiobook Automation System...")

    try:
        # 1. Initialize database
        logger.info("Initializing database...")
        init_db()

        # 2. Initialize scheduler
        logger.info("Initializing scheduler...")
        scheduler = initialize_scheduler()

        # 3. Register all scheduled tasks
        logger.info("Registering scheduled tasks...")
        register_all_tasks(scheduler)

        # 4. Start scheduler
        logger.info("Starting scheduler...")
        start_scheduler()

        logger.info("Application startup complete!")

    except Exception as e:
        logger.error(f"Application startup failed: {e}", exc_info=True)
        raise

    # Application is running
    yield

    # ========================================================================
    # SHUTDOWN
    # ========================================================================
    logger.info("Shutting down Audiobook Automation System...")

    try:
        # 1. Stop scheduler (wait for running jobs to finish)
        logger.info("Stopping scheduler...")
        shutdown_scheduler(wait=True)

        # 2. Close database connections
        logger.info("Closing database connections...")
        close_db()

        logger.info("Application shutdown complete!")

    except Exception as e:
        logger.error(f"Application shutdown error: {e}", exc_info=True)


# ============================================================================
# Create FastAPI Application
# ============================================================================

app = FastAPI(
    title="Audiobook Automation System",
    version="1.0.0",
    description="REST API for managing audiobook discovery, metadata, and downloads",
    lifespan=lifespan  # Attach lifespan handler
)


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "Audiobook Automation System API",
        "version": "1.0.0"
    }


@app.get("/scheduler/status")
async def scheduler_status():
    """Get scheduler status and job information"""
    from backend.schedulers import is_scheduler_running, get_scheduled_jobs

    running = is_scheduler_running()
    jobs = []

    if running:
        for job in get_scheduled_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })

    return {
        'running': running,
        'jobs_count': len(jobs),
        'jobs': jobs
    }


@app.get("/scheduler/jobs")
async def list_jobs():
    """List all scheduled jobs"""
    from backend.schedulers import get_scheduled_jobs

    jobs = []
    for job in get_scheduled_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
            'trigger': str(job.trigger),
            'max_instances': job.max_instances,
            'coalesce': job.coalesce
        })

    return {'jobs': jobs}


@app.post("/scheduler/jobs/{job_id}/pause")
async def pause_job_endpoint(job_id: str):
    """Pause a scheduled job"""
    from backend.schedulers import pause_job

    try:
        pause_job(job_id)
        return {'status': 'success', 'message': f'Job {job_id} paused'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


@app.post("/scheduler/jobs/{job_id}/resume")
async def resume_job_endpoint(job_id: str):
    """Resume a paused job"""
    from backend.schedulers import resume_job

    try:
        resume_job(job_id)
        return {'status': 'success', 'message': f'Job {job_id} resumed'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


@app.get("/tasks/recent")
async def recent_tasks(limit: int = 10):
    """Get recent task execution history"""
    from backend.database import get_db_context
    from backend.models.task import Task
    from sqlalchemy import desc

    with get_db_context() as db:
        tasks = db.query(Task)\
            .order_by(desc(Task.date_created))\
            .limit(limit)\
            .all()

        return {
            'tasks': [
                {
                    'id': task.id,
                    'task_name': task.task_name,
                    'status': task.status,
                    'scheduled_time': task.scheduled_time.isoformat() if task.scheduled_time else None,
                    'actual_start': task.actual_start.isoformat() if task.actual_start else None,
                    'actual_end': task.actual_end.isoformat() if task.actual_end else None,
                    'duration_seconds': task.duration_seconds,
                    'items_processed': task.items_processed,
                    'items_succeeded': task.items_succeeded,
                    'items_failed': task.items_failed,
                    'error_message': task.error_message
                }
                for task in tasks
            ]
        }


@app.get("/tasks/{task_id}")
async def get_task_details(task_id: int):
    """Get detailed information about a specific task execution"""
    from backend.database import get_db_context
    from backend.models.task import Task

    with get_db_context() as db:
        task = db.query(Task).filter(Task.id == task_id).first()

        if not task:
            return {'status': 'error', 'message': f'Task {task_id} not found'}

        return {
            'id': task.id,
            'task_name': task.task_name,
            'status': task.status,
            'scheduled_time': task.scheduled_time.isoformat() if task.scheduled_time else None,
            'actual_start': task.actual_start.isoformat() if task.actual_start else None,
            'actual_end': task.actual_end.isoformat() if task.actual_end else None,
            'duration_seconds': task.duration_seconds,
            'items_processed': task.items_processed,
            'items_succeeded': task.items_succeeded,
            'items_failed': task.items_failed,
            'log_output': task.log_output,
            'error_message': task.error_message,
            'metadata': task.metadata
        }


# ============================================================================
# Run Application
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "INTEGRATION_EXAMPLE:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable in production
        log_level="info"
    )


# ============================================================================
# ALTERNATIVE: Legacy Startup/Shutdown Events (pre-FastAPI 0.93)
# ============================================================================

"""
If using FastAPI < 0.93, use these event handlers instead of lifespan:

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Audiobook Automation System...")

    # Initialize database
    init_db()

    # Initialize and start scheduler
    scheduler = initialize_scheduler()
    register_all_tasks(scheduler)
    start_scheduler()

    logger.info("Application startup complete!")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Audiobook Automation System...")

    # Stop scheduler
    shutdown_scheduler(wait=True)

    # Close database
    close_db()

    logger.info("Application shutdown complete!")
"""
