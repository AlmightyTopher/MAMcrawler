"""
System Statistics and Health Routes
FastAPI router for system-wide statistics, health checks, and administrative operations
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
import logging
import os

from backend.database import get_db
from backend.services.book_service import BookService
from backend.services.series_service import SeriesService
from backend.services.author_service import AuthorService
from backend.services.download_service import DownloadService
from backend.services.metadata_service import MetadataService
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
    "/stats",
    response_model=StandardResponse,
    summary="Get system statistics",
    description="Get overall system statistics (books, series, authors, downloads)"
)
async def get_system_stats(
    db: Session = Depends(get_db)
):
    """
    Get overall system statistics

    Returns:
        Standard response with comprehensive system statistics
    """
    try:
        from backend.models.book import Book
        from backend.models.series import Series
        from backend.models.author import Author
        from backend.models.download import Download
        from backend.models.failed_attempt import FailedAttempt

        # Book statistics
        total_books = db.query(Book).filter(Book.status == "active").count()
        archived_books = db.query(Book).filter(Book.status == "archived").count()
        duplicate_books = db.query(Book).filter(Book.status == "duplicate").count()

        # Series statistics
        total_series = db.query(Series).count()

        # Author statistics
        total_authors = db.query(Author).count()

        # Download statistics
        total_downloads = db.query(Download).count()
        queued_downloads = db.query(Download).filter(Download.status == "queued").count()
        completed_downloads = db.query(Download).filter(Download.status == "completed").count()
        failed_downloads = db.query(Download).filter(Download.status.in_(["failed", "abandoned"])).count()

        # Failed attempt statistics
        total_failed_attempts = db.query(FailedAttempt).count()

        stats = {
            "books": {
                "total_active": total_books,
                "archived": archived_books,
                "duplicates": duplicate_books,
                "grand_total": total_books + archived_books + duplicate_books
            },
            "series": {
                "total": total_series
            },
            "authors": {
                "total": total_authors
            },
            "downloads": {
                "total": total_downloads,
                "queued": queued_downloads,
                "completed": completed_downloads,
                "failed": failed_downloads
            },
            "failed_attempts": {
                "total": total_failed_attempts
            }
        }

        return {
            "success": True,
            "data": stats,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting system stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/library-status",
    response_model=StandardResponse,
    summary="Get library health status",
    description="Get library health metrics (metadata completeness, series/author completion)"
)
async def get_library_status(
    db: Session = Depends(get_db)
):
    """
    Get library health status

    Returns:
        Standard response with metadata and completion statistics
    """
    try:
        from backend.models.book import Book

        # Metadata completeness
        avg_completeness = db.query(func.avg(Book.metadata_completeness_percent)).filter(
            Book.status == "active"
        ).scalar() or 0

        books_below_80 = db.query(Book).filter(
            Book.metadata_completeness_percent < 80,
            Book.status == "active"
        ).count()

        books_100 = db.query(Book).filter(
            Book.metadata_completeness_percent == 100,
            Book.status == "active"
        ).count()

        # Series completion
        series_result = SeriesService.get_series_completion_summary(db)
        series_stats = series_result.get("stats", {}) if series_result["success"] else {}

        # Author completion
        author_result = AuthorService.get_author_completion_summary(db)
        author_stats = author_result.get("stats", {}) if author_result["success"] else {}

        health_data = {
            "metadata_quality": {
                "average_completeness_percent": round(avg_completeness, 2),
                "books_below_80_percent": books_below_80,
                "books_100_percent": books_100
            },
            "series_completion": series_stats,
            "author_completion": author_stats
        }

        return {
            "success": True,
            "data": health_data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting library status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/download-stats",
    response_model=StandardResponse,
    summary="Get download queue statistics",
    description="Get download queue status and statistics"
)
async def get_download_stats(
    db: Session = Depends(get_db)
):
    """
    Get download queue statistics

    Returns:
        Standard response with download queue metrics
    """
    try:
        from backend.models.download import Download

        # Count by status
        queued = db.query(Download).filter(Download.status == "queued").count()
        downloading = db.query(Download).filter(Download.status == "downloading").count()
        completed = db.query(Download).filter(Download.status == "completed").count()
        failed = db.query(Download).filter(Download.status == "failed").count()
        abandoned = db.query(Download).filter(Download.status == "abandoned").count()

        # Count by source
        source_counts = db.query(
            Download.source,
            func.count(Download.id)
        ).group_by(Download.source).all()

        source_breakdown = {source: count for source, count in source_counts}

        # Pending retries
        retry_due_result = DownloadService.get_retry_due(db)
        retry_due_count = retry_due_result["count"] if retry_due_result["success"] else 0

        stats = {
            "status_breakdown": {
                "queued": queued,
                "downloading": downloading,
                "completed": completed,
                "failed": failed,
                "abandoned": abandoned
            },
            "source_breakdown": source_breakdown,
            "retry_due_count": retry_due_count,
            "total_downloads": queued + downloading + completed + failed + abandoned
        }

        return {
            "success": True,
            "data": stats,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting download stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/storage",
    response_model=StandardResponse,
    summary="Get storage usage",
    description="Get estimated storage usage statistics"
)
async def get_storage_usage(
    db: Session = Depends(get_db)
):
    """
    Get storage usage estimates

    Returns:
        Standard response with storage statistics
    """
    try:
        from backend.models.book import Book
        from backend.config import get_settings

        settings = get_settings()

        # Count total books
        total_books = db.query(Book).filter(Book.status == "active").count()

        # Average audiobook size estimate (in GB)
        avg_audiobook_size_gb = 0.5  # Conservative estimate

        # Estimated total storage
        estimated_storage_gb = total_books * avg_audiobook_size_gb

        # Database size (if we can get it)
        db_size_mb = 0
        try:
            db_path = settings.DATABASE_URL.replace("sqlite:///", "").replace("postgresql://", "")
            if os.path.exists(db_path):
                db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
        except:
            pass

        storage_data = {
            "total_books": total_books,
            "estimated_audiobook_storage_gb": round(estimated_storage_gb, 2),
            "database_size_mb": round(db_size_mb, 2),
            "note": "Audiobook storage is estimated based on average book size"
        }

        return {
            "success": True,
            "data": storage_data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting storage usage: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/api-usage",
    response_model=StandardResponse,
    summary="Get API usage statistics",
    description="Get API call statistics by integration"
)
async def get_api_usage(
    db: Session = Depends(get_db)
):
    """
    Get API usage statistics

    Returns:
        Standard response with API call counts by source
    """
    try:
        from backend.models.metadata_correction import MetadataCorrection

        # Count metadata corrections by source (proxy for API calls)
        source_counts = db.query(
            MetadataCorrection.source,
            func.count(MetadataCorrection.id)
        ).group_by(MetadataCorrection.source).all()

        api_usage = {
            source: count
            for source, count in source_counts
        }

        total_api_calls = sum(api_usage.values())

        return {
            "success": True,
            "data": {
                "total_metadata_corrections": total_api_calls,
                "by_source": api_usage,
                "note": "Statistics based on metadata corrections (proxy for API calls)"
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting API usage: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post(
    "/trigger-full-scan",
    response_model=StandardResponse,
    summary="Trigger full system scan",
    description="Trigger complete system scan (Audiobookshelf + metadata + series + author)"
)
async def trigger_full_scan():
    """
    Trigger complete system scan

    This will trigger:
    1. Audiobookshelf library scan
    2. Metadata correction for all books
    3. Series completion recalculation
    4. Author completion recalculation

    WARNING: This is a long-running operation.

    Returns:
        Standard response with scan trigger confirmation
    """
    try:
        if not scheduler or not scheduler.running:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Scheduler is not running - cannot trigger scan"
            )

        # Trigger relevant tasks
        tasks_to_trigger = ["METADATA_FULL", "SERIES", "AUTHOR"]
        triggered = []

        jobs = scheduler.get_jobs()
        for task_name in tasks_to_trigger:
            matching_job = next((job for job in jobs if task_name.lower() in job.id.lower()), None)
            if matching_job:
                matching_job.modify(next_run_time=datetime.now())
                triggered.append(task_name)

        logger.warning(f"Triggered full system scan ({len(triggered)} tasks)")

        return {
            "success": True,
            "data": {
                "message": "Full system scan triggered",
                "triggered_tasks": triggered,
                "note": "This is a long-running operation. Check /api/scheduler/status for progress."
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering full scan: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/configuration",
    response_model=StandardResponse,
    summary="Get system configuration",
    description="Get current system configuration (genres, retention, features)"
)
async def get_configuration():
    """
    Get system configuration

    Returns:
        Standard response with current configuration settings
    """
    try:
        from backend.config import get_settings

        settings = get_settings()

        config_data = {
            "features": {
                "metadata_correction": settings.ENABLE_METADATA_CORRECTION,
                "series_completion": settings.ENABLE_SERIES_COMPLETION,
                "author_completion": settings.ENABLE_AUTHOR_COMPLETION,
                "top10_discovery": settings.ENABLE_TOP10_DISCOVERY,
                "mam_scraping": settings.ENABLE_MAM_SCRAPING
            },
            "genres": {
                "enabled": settings.ENABLED_GENRES,
                "disabled": settings.DISABLED_GENRES
            },
            "retention_policy": {
                "history_retention_days": settings.HISTORY_RETENTION_DAYS,
                "failed_attempts_retention": settings.FAILED_ATTEMPTS_RETENTION
            },
            "integrations": {
                "audiobookshelf_url": settings.ABS_URL,
                "qbittorrent_host": settings.QB_HOST,
                "prowlarr_url": settings.PROWLARR_URL,
                "google_books_enabled": bool(settings.GOOGLE_BOOKS_API_KEY)
            }
        }

        return {
            "success": True,
            "data": config_data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting configuration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post(
    "/logs/export",
    response_model=StandardResponse,
    summary="Export system logs",
    description="Export system logs for diagnostic purposes"
)
async def export_logs(
    lines: int = 500
):
    """
    Export system logs

    - **lines**: Number of log lines to export (default 500)

    Returns:
        Standard response with log content
    """
    try:
        log_file_path = "logs/fastapi.log"

        if not os.path.exists(log_file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Log file not found"
            )

        # Read last N lines from log file
        with open(log_file_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            log_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        log_content = ''.join(log_lines)

        return {
            "success": True,
            "data": {
                "log_file": log_file_path,
                "lines_returned": len(log_lines),
                "total_lines": len(all_lines),
                "content": log_content
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting logs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/health",
    response_model=StandardResponse,
    summary="Health check",
    description="Comprehensive health check (database, scheduler, external APIs)"
)
async def health_check(
    db: Session = Depends(get_db)
):
    """
    Comprehensive health check

    NOTE: This endpoint does NOT require API key authentication.

    Returns:
        Standard response with health status for all system components
    """
    try:
        health_data = {
            "overall_status": "healthy",
            "components": {}
        }

        # Check database
        try:
            db.execute("SELECT 1")
            health_data["components"]["database"] = {
                "status": "healthy",
                "message": "Database connection successful"
            }
        except Exception as e:
            health_data["components"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_data["overall_status"] = "degraded"

        # Check scheduler
        try:
            if scheduler and scheduler.running:
                job_count = len(scheduler.get_jobs())
                health_data["components"]["scheduler"] = {
                    "status": "healthy",
                    "running": True,
                    "job_count": job_count
                }
            else:
                health_data["components"]["scheduler"] = {
                    "status": "degraded",
                    "running": False,
                    "message": "Scheduler is not running"
                }
                health_data["overall_status"] = "degraded"
        except Exception as e:
            health_data["components"]["scheduler"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_data["overall_status"] = "degraded"

        # Check external API configurations
        from backend.config import get_settings
        settings = get_settings()

        health_data["components"]["external_apis"] = {
            "audiobookshelf": "configured" if settings.ABS_TOKEN else "not_configured",
            "qbittorrent": "configured" if settings.QB_PASSWORD else "not_configured",
            "prowlarr": "configured" if settings.PROWLARR_API_KEY else "not_configured",
            "google_books": "configured" if settings.GOOGLE_BOOKS_API_KEY else "not_configured"
        }

        return {
            "success": True,
            "data": health_data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error during health check: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
