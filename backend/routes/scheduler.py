"""
Scheduler Control Routes
FastAPI router for managing APScheduler tasks, execution history, and manual triggers
"""

from typing import Optional, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import logging

from backend.database import get_db
from backend.services.task_service import TaskService
from backend.main import scheduler

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# ============================================================================
# Pydantic Models (Request/Response schemas)
# ============================================================================

class StandardResponse(BaseModel):
    """Standard API response format"""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ============================================================================
# Route Handlers
# ============================================================================

@router.get(
    "/status",
    response_model=StandardResponse,
    summary="Get scheduler status",
    description="Get current scheduler status and next scheduled tasks"
)
async def get_scheduler_status():
    """
    Get scheduler status

    Returns:
        Standard response with scheduler status, running state, and job count
    """
    try:
        if not scheduler:
            return {
                "success": True,
                "data": {
                    "scheduler_enabled": False,
                    "running": False,
                    "message": "Scheduler is disabled in configuration"
                },
                "error": None,
                "timestamp": datetime.utcnow().isoformat()
            }

        is_running = scheduler.running if scheduler else False
        jobs = scheduler.get_jobs() if scheduler and is_running else []

        # Get next run times for all jobs
        next_jobs = []
        if jobs:
            for job in jobs:
                next_jobs.append({
                    "job_id": job.id,
                    "job_name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
                })

        # Sort by next_run_time
        next_jobs.sort(key=lambda x: x["next_run_time"] if x["next_run_time"] else "9999")

        return {
            "success": True,
            "data": {
                "scheduler_enabled": True,
                "running": is_running,
                "total_jobs": len(jobs),
                "next_jobs": next_jobs[:5]  # Show next 5 jobs
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/tasks",
    response_model=StandardResponse,
    summary="List all tasks",
    description="Get all registered tasks with schedules"
)
async def list_tasks():
    """
    List all registered scheduled tasks

    Returns:
        Standard response with list of all registered tasks and their schedules
    """
    try:
        if not scheduler or not scheduler.running:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Scheduler is not running"
            )

        jobs = scheduler.get_jobs()

        tasks_data = [
            {
                "job_id": job.id,
                "job_name": job.name,
                "trigger": str(job.trigger),
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "args": job.args,
                "kwargs": job.kwargs
            }
            for job in jobs
        ]

        return {
            "success": True,
            "data": {
                "tasks": tasks_data,
                "total_tasks": len(tasks_data)
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing tasks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/task/{task_name}",
    response_model=StandardResponse,
    summary="Get task details",
    description="Get task schedule and last execution information"
)
async def get_task(
    task_name: str,
    db: Session = Depends(get_db)
):
    """
    Get details about a specific task

    - **task_name**: Task name (MAM, TOP10, METADATA_FULL, METADATA_NEW, SERIES, AUTHOR)

    Returns:
        Standard response with task schedule and execution history
    """
    try:
        # Get task history from database
        history_result = TaskService.get_task_history(db, task_name, limit=10)

        if not history_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=history_result["error"]
            )

        # Get scheduled job info if scheduler is running
        schedule_info = None
        if scheduler and scheduler.running:
            jobs = scheduler.get_jobs()
            matching_job = next((job for job in jobs if task_name.lower() in job.id.lower()), None)

            if matching_job:
                schedule_info = {
                    "job_id": matching_job.id,
                    "trigger": str(matching_job.trigger),
                    "next_run_time": matching_job.next_run_time.isoformat() if matching_job.next_run_time else None
                }

        # Convert history to dict format
        history_data = [
            {
                "id": task.id,
                "status": task.status,
                "scheduled_time": task.scheduled_time.isoformat() if task.scheduled_time else None,
                "actual_start": task.actual_start.isoformat() if task.actual_start else None,
                "actual_end": task.actual_end.isoformat() if task.actual_end else None,
                "duration_seconds": task.duration_seconds,
                "items_processed": task.items_processed,
                "items_succeeded": task.items_succeeded,
                "items_failed": task.items_failed,
                "error_message": task.error_message
            }
            for task in history_result["data"]
        ]

        return {
            "success": True,
            "data": {
                "task_name": task_name,
                "schedule": schedule_info,
                "execution_history": history_data,
                "history_count": history_result["count"]
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task {task_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post(
    "/trigger/{task_name}",
    response_model=StandardResponse,
    summary="Manually trigger task",
    description="Manually trigger a scheduled task to run immediately"
)
async def trigger_task(
    task_name: str,
    db: Session = Depends(get_db)
):
    """
    Manually trigger a task to run immediately

    - **task_name**: Task name to trigger (MAM, TOP10, METADATA_FULL, METADATA_NEW, SERIES, AUTHOR)

    Returns:
        Standard response with trigger confirmation
    """
    try:
        # Valid task names
        valid_tasks = ["MAM", "TOP10", "METADATA_FULL", "METADATA_NEW", "SERIES", "AUTHOR", "GAPS"]

        if task_name.upper() not in valid_tasks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid task name. Must be one of: {', '.join(valid_tasks)}"
            )

        if not scheduler or not scheduler.running:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Scheduler is not running"
            )

        # Find the matching job
        jobs = scheduler.get_jobs()
        matching_job = next((job for job in jobs if task_name.lower() in job.id.lower()), None)

        if not matching_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task '{task_name}' not found in scheduler"
            )

        # Trigger the job immediately
        matching_job.modify(next_run_time=datetime.now())

        logger.info(f"Manually triggered task: {task_name}")

        return {
            "success": True,
            "data": {
                "task_name": task_name,
                "job_id": matching_job.id,
                "message": f"Task '{task_name}' has been triggered and will run shortly",
                "next_run_time": matching_job.next_run_time.isoformat() if matching_job.next_run_time else None
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering task {task_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.put(
    "/task/{task_name}/pause",
    response_model=StandardResponse,
    summary="Pause task",
    description="Pause a scheduled task (prevents automatic execution)"
)
async def pause_task(
    task_name: str
):
    """
    Pause a scheduled task

    - **task_name**: Task name to pause

    Returns:
        Standard response with pause confirmation
    """
    try:
        if not scheduler or not scheduler.running:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Scheduler is not running"
            )

        # Find the matching job
        jobs = scheduler.get_jobs()
        matching_job = next((job for job in jobs if task_name.lower() in job.id.lower()), None)

        if not matching_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task '{task_name}' not found in scheduler"
            )

        # Pause the job
        matching_job.pause()

        logger.info(f"Paused task: {task_name}")

        return {
            "success": True,
            "data": {
                "task_name": task_name,
                "job_id": matching_job.id,
                "message": f"Task '{task_name}' has been paused"
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing task {task_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.put(
    "/task/{task_name}/resume",
    response_model=StandardResponse,
    summary="Resume task",
    description="Resume a paused task"
)
async def resume_task(
    task_name: str
):
    """
    Resume a paused task

    - **task_name**: Task name to resume

    Returns:
        Standard response with resume confirmation
    """
    try:
        if not scheduler or not scheduler.running:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Scheduler is not running"
            )

        # Find the matching job
        jobs = scheduler.get_jobs()
        matching_job = next((job for job in jobs if task_name.lower() in job.id.lower()), None)

        if not matching_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task '{task_name}' not found in scheduler"
            )

        # Resume the job
        matching_job.resume()

        logger.info(f"Resumed task: {task_name}")

        return {
            "success": True,
            "data": {
                "task_name": task_name,
                "job_id": matching_job.id,
                "message": f"Task '{task_name}' has been resumed",
                "next_run_time": matching_job.next_run_time.isoformat() if matching_job.next_run_time else None
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming task {task_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/execution-history/{task_name}",
    response_model=StandardResponse,
    summary="Get task execution history",
    description="Get execution history for a specific task"
)
async def get_execution_history(
    task_name: str,
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
    db: Session = Depends(get_db)
):
    """
    Get execution history for a task

    - **task_name**: Task name
    - **limit**: Maximum number of records (1-500, default 50)

    Returns:
        Standard response with execution history
    """
    try:
        result = TaskService.get_task_history(db, task_name, limit=limit)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        # Convert history to dict format
        history_data = [
            {
                "id": task.id,
                "status": task.status,
                "scheduled_time": task.scheduled_time.isoformat() if task.scheduled_time else None,
                "actual_start": task.actual_start.isoformat() if task.actual_start else None,
                "actual_end": task.actual_end.isoformat() if task.actual_end else None,
                "duration_seconds": task.duration_seconds,
                "items_processed": task.items_processed,
                "items_succeeded": task.items_succeeded,
                "items_failed": task.items_failed,
                "error_message": task.error_message
            }
            for task in result["data"]
        ]

        return {
            "success": True,
            "data": {
                "task_name": task_name,
                "executions": history_data,
                "total_executions": result["count"]
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution history for {task_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/upcoming-tasks",
    response_model=StandardResponse,
    summary="Get upcoming tasks",
    description="Get tasks scheduled to run in the next 24 hours"
)
async def get_upcoming_tasks(
    hours: int = Query(24, ge=1, le=168, description="Hours to look ahead")
):
    """
    Get tasks scheduled to run in the next X hours

    - **hours**: Number of hours to look ahead (1-168, default 24)

    Returns:
        Standard response with upcoming tasks
    """
    try:
        if not scheduler or not scheduler.running:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Scheduler is not running"
            )

        cutoff_time = datetime.now() + timedelta(hours=hours)
        jobs = scheduler.get_jobs()

        upcoming = []
        for job in jobs:
            if job.next_run_time and job.next_run_time <= cutoff_time:
                upcoming.append({
                    "job_id": job.id,
                    "job_name": job.name,
                    "next_run_time": job.next_run_time.isoformat(),
                    "hours_until_run": (job.next_run_time - datetime.now()).total_seconds() / 3600
                })

        # Sort by next_run_time
        upcoming.sort(key=lambda x: x["next_run_time"])

        return {
            "success": True,
            "data": {
                "hours": hours,
                "cutoff_time": cutoff_time.isoformat(),
                "upcoming_tasks": upcoming,
                "total_upcoming": len(upcoming)
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting upcoming tasks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post(
    "/trigger-all",
    response_model=StandardResponse,
    summary="Trigger all tasks",
    description="Trigger all enabled tasks to run immediately (use with caution)"
)
async def trigger_all_tasks():
    """
    Trigger all enabled tasks to run immediately

    WARNING: This will trigger ALL scheduled tasks. Use with caution.

    Returns:
        Standard response with list of triggered tasks
    """
    try:
        if not scheduler or not scheduler.running:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Scheduler is not running"
            )

        jobs = scheduler.get_jobs()
        triggered_jobs = []

        for job in jobs:
            job.modify(next_run_time=datetime.now())
            triggered_jobs.append({
                "job_id": job.id,
                "job_name": job.name
            })

        logger.warning(f"Manually triggered ALL tasks ({len(triggered_jobs)} jobs)")

        return {
            "success": True,
            "data": {
                "message": f"Triggered {len(triggered_jobs)} tasks",
                "triggered_tasks": triggered_jobs
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering all tasks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/configuration",
    response_model=StandardResponse,
    summary="Get scheduler configuration",
    description="Get scheduler configuration and settings"
)
async def get_configuration():
    """
    Get scheduler configuration

    Returns:
        Standard response with scheduler configuration
    """
    try:
        from backend.config import get_settings

        settings = get_settings()

        config_data = {
            "scheduler_enabled": settings.SCHEDULER_ENABLED,
            "task_schedules": {
                "MAM": settings.TASK_MAM_TIME,
                "TOP10": settings.TASK_TOP10_TIME,
                "METADATA_FULL": settings.TASK_METADATA_FULL_TIME,
                "METADATA_NEW": settings.TASK_METADATA_NEW_TIME,
                "SERIES": settings.TASK_SERIES_TIME,
                "AUTHOR": settings.TASK_AUTHOR_TIME,
                "GAPS": settings.TASK_GAPS_TIME
            },
            "enabled_features": {
                "metadata_correction": settings.ENABLE_METADATA_CORRECTION,
                "series_completion": settings.ENABLE_SERIES_COMPLETION,
                "author_completion": settings.ENABLE_AUTHOR_COMPLETION,
                "top10_discovery": settings.ENABLE_TOP10_DISCOVERY,
                "mam_scraping": settings.ENABLE_MAM_SCRAPING,
                "gap_analysis": settings.ENABLE_GAP_ANALYSIS
            },
            "gap_analysis_config": {
                "max_downloads_per_run": settings.GAP_MAX_DOWNLOADS_PER_RUN,
                "series_priority": settings.GAP_SERIES_PRIORITY,
                "author_priority": settings.GAP_AUTHOR_PRIORITY,
                "min_seeds": settings.MAM_MIN_SEEDS,
                "title_match_threshold": settings.MAM_TITLE_MATCH_THRESHOLD
            }
        }

        return {
            "success": True,
            "data": config_data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting scheduler configuration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
