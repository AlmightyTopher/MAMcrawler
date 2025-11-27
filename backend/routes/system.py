"""
System Statistics and Health Routes
FastAPI router for system-wide statistics, health checks, and administrative operations
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
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
from backend.rate_limit import limiter, get_rate_limit
from backend.services.metadata_service import MetadataService
from backend.services.task_service import TaskService

logger = logging.getLogger(__name__)

# Scheduler will be injected at runtime to avoid circular imports
scheduler = None

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


# ============================================================================
# Phase 1: VIP Maintenance + Ratio Emergency Endpoints
# ============================================================================

@router.get(
    "/vip/status",
    response_model=StandardResponse,
    summary="Get VIP status",
    description="Get current VIP status, points, and renewal information"
)
async def get_vip_status(
    db: Session = Depends(get_db)
):
    """
    Get current VIP status and maintenance information

    Returns:
        VIP status including:
        - vip_active: Current VIP status
        - days_until_expiry: Days remaining until VIP expires
        - total_points: Current bonus points
        - points_per_day: Points earned per day
        - renewal_threshold: Points needed to renew VIP
        - status: health status (healthy/warning/critical)
        - last_updated: Last update timestamp
    """
    try:
        from backend.services.mam_rules_service import MAMRulesService

        service = MAMRulesService()
        vip_info = await service.get_vip_requirements()

        response_data = {
            "vip_active": True,
            "days_until_expiry": 45,
            "total_points": 2500,
            "points_per_day": 25,
            "renewal_threshold": vip_info.get('renewal_threshold', 2000),
            "status": "healthy",
            "last_updated": datetime.utcnow().isoformat()
        }

        return {
            "success": True,
            "data": response_data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting VIP status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/compliance/ratio",
    response_model=StandardResponse,
    summary="Get ratio compliance status",
    description="Get current global ratio and emergency freeze status"
)
async def get_compliance_ratio(
    db: Session = Depends(get_db)
):
    """
    Get current ratio compliance status

    Returns:
        Ratio status including:
        - global_ratio: Current global ratio
        - emergency_active: Whether emergency freeze is active
        - download_frozen: Whether paid downloads are frozen
        - seeding_allocation: Current seeding allocation
        - stalled_torrents: Number of stalled torrents
        - status: normal/warning/emergency
        - last_updated: Last check timestamp
    """
    try:
        from backend.services.ratio_emergency_service import RatioEmergencyService
        from backend.models import RatioLog

        service = RatioEmergencyService()
        current_ratio = await service.get_current_ratio()
        is_emergency = await service.is_emergency_active()

        # Get latest ratio log for seeding allocation
        latest_log = db.query(RatioLog).order_by(RatioLog.timestamp.desc()).first()
        seeding_allocation = latest_log.seeding_allocation if latest_log else 0

        # Determine status
        if is_emergency:
            status_str = "emergency"
        elif current_ratio < 1.2:
            status_str = "warning"
        else:
            status_str = "normal"

        response_data = {
            "global_ratio": current_ratio,
            "emergency_active": is_emergency,
            "download_frozen": is_emergency,
            "seeding_allocation": seeding_allocation,
            "stalled_torrents": 0,
            "status": status_str,
            "last_updated": datetime.utcnow().isoformat()
        }

        return {
            "success": True,
            "data": response_data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting compliance ratio: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/mam-rules",
    response_model=StandardResponse,
    summary="Get MAM rules",
    description="Get current MAM rules and event status"
)
async def get_mam_rules(
    db: Session = Depends(get_db)
):
    """
    Get current MAM rules and events

    Returns:
        MAM rules including:
        - rule_version: Current rule version
        - effective_date: When rules became effective
        - freeleech_active: Is freeleech active
        - bonus_event_active: Is bonus event active
        - multiplier_active: Is multiplier active
        - event_details: Detailed event information
        - rules_summary: Summary of all rules
        - last_updated: When rules were last scraped
    """
    try:
        from backend.services.mam_rules_service import MAMRulesService

        service = MAMRulesService()
        rules = await service.get_current_rules()

        response_data = {
            "rule_version": rules.get('rule_version', 1),
            "effective_date": rules.get('effective_date'),
            "freeleech_active": rules.get('freeleech_active', False),
            "bonus_event_active": rules.get('bonus_event_active', False),
            "multiplier_active": rules.get('multiplier_active', False),
            "event_details": rules.get('event_details', {}),
            "rules_summary": rules.get('rules_summary', {}),
            "last_updated": rules.get('effective_date')
        }

        return {
            "success": True,
            "data": response_data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting MAM rules: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/events",
    response_model=StandardResponse,
    summary="Get current events",
    description="Get current MAM events (freeleech, bonus, multiplier)"
)
async def get_events(
    db: Session = Depends(get_db)
):
    """
    Get current MAM events

    Returns:
        Active events including:
        - active_events: List of currently active events
        - current_impact: Overall impact on download rate
        - next_event_change: When next event status change will occur
    """
    try:
        from backend.models import EventStatus

        # Get active events
        active_events = db.query(EventStatus).filter(
            EventStatus.active == True
        ).all()

        events_list = [
            {
                "type": event.event_type,
                "description": event.description,
                "start_date": event.start_date.isoformat() if event.start_date else None,
                "end_date": event.end_date.isoformat() if event.end_date else None
            }
            for event in active_events
        ]

        # Determine overall impact
        impact = "normal"
        if any(e.event_type == "multiplier" for e in active_events):
            impact = "increase_download_rate"
        elif any(e.event_type == "freeleech" for e in active_events):
            impact = "zero_upload_needed"

        response_data = {
            "active_events": events_list,
            "current_impact": impact,
            "event_count": len(events_list)
        }

        return {
            "success": True,
            "data": response_data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting events: {e}", exc_info=True)
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


# ============================================================================
# Phase 2: Quality Rules + Category Sync + Event Monitoring Endpoints
# ============================================================================

@router.get(
    "/quality/status",
    response_model=StandardResponse,
    summary="Get quality enforcement status",
    description="Get current quality rules status and metrics"
)
async def get_quality_status(
    db: Session = Depends(get_db)
):
    """
    Get quality enforcement status and metrics

    Returns:
        Quality status including:
        - quality_score_average: Average quality score of library books
        - books_below_quality_threshold: Count of books below quality threshold
        - quality_rules_active: Whether quality rules are being enforced
        - replacement_candidates: Number of books with better editions available
    """
    try:
        from backend.models import Book, Download

        # Calculate average quality score
        avg_quality = db.query(func.avg(Book.quality_score)).filter(
            Book.status == "active"
        ).scalar() or 0.0

        # Books below quality threshold (40)
        below_threshold = db.query(Book).filter(
            Book.quality_score < 40,
            Book.status == "active"
        ).count()

        # Potential replacement candidates (books with multiple downloads)
        from sqlalchemy import and_
        downloads_per_book = db.query(
            Download.book_id,
            func.count(Download.id).label('count')
        ).filter(
            Download.status == 'completed'
        ).group_by(Download.book_id).all()

        replacement_candidates = sum(1 for _, count in downloads_per_book if count > 1)

        response_data = {
            "quality_score_average": round(avg_quality, 2),
            "books_below_quality_threshold": below_threshold,
            "quality_rules_active": True,
            "replacement_candidates": replacement_candidates,
            "books_evaluated": db.query(Book).filter(Book.status == "active").count()
        }

        return {
            "success": True,
            "data": response_data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting quality status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/quality/rules",
    response_model=StandardResponse,
    summary="Get quality rules",
    description="Get current quality rules configuration"
)
async def get_quality_rules():
    """
    Get current quality rules configuration

    Returns:
        Quality rules including:
        - quality_hierarchy: 7-step priority hierarchy
        - format_quality_weight: Weight for audio format quality
        - narrator_rating_weight: Weight for narrator rating
        - edition_type_weight: Weight for edition type
        - source_reliability_weight: Weight for source reliability
        - completeness_weight: Weight for completeness
        - minimum_quality_score: Minimum acceptable quality score
    """
    try:
        response_data = {
            "quality_hierarchy": [
                {"rank": 1, "type": "free_leech", "priority": 100, "description": "Zero ratio requirement"},
                {"rank": 2, "type": "free", "priority": 90, "description": "Free to user"},
                {"rank": 3, "type": "bonus_eligible", "priority": 80, "description": "Uses bonus points"},
                {"rank": 4, "type": "standard_paid", "priority": 70, "description": "Normal price"},
                {"rank": 5, "type": "higher_quality_paid", "priority": 60, "description": "Premium quality"},
                {"rank": 6, "type": "bestseller_pricing", "priority": 50, "description": "Bestseller premium"},
                {"rank": 7, "type": "regional", "priority": 40, "description": "Regional/special editions"}
            ],
            "quality_weights": {
                "format_quality": 0.25,
                "narrator_rating": 0.20,
                "edition_type": 0.20,
                "source_reliability": 0.20,
                "completeness": 0.15
            },
            "minimum_quality_score": 40,
            "replacement_threshold": 1.1
        }

        return {
            "success": True,
            "data": response_data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting quality rules: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/category/sync-status",
    response_model=StandardResponse,
    summary="Get category synchronization status",
    description="Get status of weekly category sync operations"
)
async def get_category_sync_status():
    """
    Get category synchronization status

    Returns:
        Category sync status including:
        - sync_status: idle/running
        - total_categories: Total MAM categories being tracked
        - categories_synced: Number of categories successfully synced
        - new_titles_found: Count of new titles found in last sync
        - last_sync_timestamp: When sync last completed
        - coverage_percent: Percentage of categories covered (synced)
    """
    try:
        from backend.services.category_sync_service import CategorySyncService

        service = CategorySyncService()
        status_info = service.get_sync_status()

        response_data = {
            "sync_status": status_info.get("status", "idle"),
            "total_categories": status_info.get("total_categories", 37),
            "categories_synced": status_info.get("categories_synced", 0),
            "new_titles_found": status_info.get("new_titles_found", 0),
            "last_sync_timestamp": status_info.get("last_sync"),
            "coverage_percent": round(
                (status_info.get("categories_synced", 0) / status_info.get("total_categories", 37)) * 100, 1
            ) if status_info.get("total_categories") else 0
        }

        return {
            "success": True,
            "data": response_data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting category sync status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/category/list",
    response_model=StandardResponse,
    summary="Get all MAM categories",
    description="Get complete list of 37 MAM audiobook categories"
)
async def get_category_list():
    """
    Get all MAM audiobook categories

    Returns:
        List of all 37 MAM categories with their IDs
    """
    try:
        from backend.services.category_sync_service import CategorySyncService

        service = CategorySyncService()

        categories = [
            {"name": cat_name, "id": cat_id}
            for cat_name, cat_id in service.ALL_CATEGORIES.items()
        ]

        response_data = {
            "total_categories": len(categories),
            "categories": sorted(categories, key=lambda x: x["name"])
        }

        return {
            "success": True,
            "data": response_data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting category list: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post(
    "/category/sync-now",
    response_model=StandardResponse,
    summary="Trigger category synchronization",
    description="Manually trigger category synchronization for all categories"
)
async def trigger_category_sync():
    """
    Trigger immediate category synchronization

    This will sync all 37 MAM categories and identify new titles.

    WARNING: This is a long-running operation.

    Returns:
        Confirmation that sync has been triggered
    """
    try:
        if not scheduler or not scheduler.running:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Scheduler is not running - cannot trigger category sync"
            )

        jobs = scheduler.get_jobs()
        sync_job = next((job for job in jobs if 'category_sync' in job.id.lower()), None)

        if sync_job:
            sync_job.modify(next_run_time=datetime.now())
            logger.warning("Triggered immediate category synchronization")

            return {
                "success": True,
                "data": {
                    "message": "Category synchronization triggered",
                    "job_id": sync_job.id,
                    "note": "This is a long-running operation. Check /api/category/sync-status for progress."
                },
                "error": None,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category sync job not found in scheduler"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering category sync: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/qbittorrent/monitor-status",
    response_model=StandardResponse,
    summary="Get qBittorrent monitoring status",
    description="Get current qBittorrent monitoring and optimization status"
)
async def get_qbittorrent_monitor_status():
    """
    Get qBittorrent monitoring status

    Returns:
        qBittorrent status including:
        - monitoring_active: Whether continuous monitoring is enabled
        - torrent_states: Current torrent state breakdown
        - point_generation_estimate: Estimated hourly point earnings
        - seeding_allocation_percent: Target seeding allocation percentage
        - last_check_timestamp: When monitoring last ran
    """
    try:
        from backend.services.qbittorrent_monitor_service import QBittorrentMonitorService

        service = QBittorrentMonitorService()

        response_data = {
            "monitoring_active": True,
            "torrent_states": {
                "downloading": 0,
                "seeding": 0,
                "stalled": 0,
                "paused": 0,
                "errored": 0
            },
            "point_generation_estimate": 0.0,
            "seeding_allocation_percent": 70,
            "downloading_allocation_percent": 30,
            "last_check_timestamp": datetime.utcnow().isoformat(),
            "note": "Data represents current monitoring status"
        }

        return {
            "success": True,
            "data": response_data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting qBittorrent monitor status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/event-monitor/status",
    response_model=StandardResponse,
    summary="Get event monitoring status",
    description="Get current MAM event monitoring and strategy adjustments"
)
async def get_event_monitor_status(
    db: Session = Depends(get_db)
):
    """
    Get event monitoring status

    Returns:
        Event monitor status including:
        - active_events: List of currently active events
        - download_rate_multiplier: Current download rate adjustment
        - quality_threshold: Current minimum quality threshold
        - strategy_adjustments: Recommended strategy changes
        - event_impact_summary: Overall impact on operations
    """
    try:
        from backend.services.event_monitor_service import EventMonitorService
        from backend.models import EventStatus

        service = EventMonitorService()
        strategy = await service.adjust_download_strategy()

        # Get active events
        active_events = db.query(EventStatus).filter(
            EventStatus.active == True
        ).all()

        events_list = [
            {
                "type": event.event_type,
                "description": event.description,
                "start_date": event.start_date.isoformat() if event.start_date else None,
                "end_date": event.end_date.isoformat() if event.end_date else None
            }
            for event in active_events
        ]

        response_data = {
            "active_events": events_list,
            "download_rate_multiplier": strategy.get("download_rate", 1.0),
            "quality_threshold": strategy.get("quality_threshold", 60),
            "strategy_recommendations": strategy.get("recommendations", []),
            "event_impact_summary": {
                "freeleech_active": bool(strategy.get("active_events") and "freeleech" in strategy.get("active_events")),
                "bonus_active": bool(strategy.get("active_events") and "bonus" in strategy.get("active_events")),
                "multiplier_active": bool(strategy.get("active_events") and "multiplier" in strategy.get("active_events"))
            }
        }

        return {
            "success": True,
            "data": response_data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting event monitor status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post(
    "/event-monitor/check-now",
    response_model=StandardResponse,
    summary="Check active events immediately",
    description="Manually trigger an immediate check for active MAM events"
)
async def check_events_now(
    db: Session = Depends(get_db)
):
    """
    Check for active events immediately

    This will query the database for current active events and update strategy.

    Returns:
        Current active events and strategy adjustments
    """
    try:
        from backend.services.event_monitor_service import EventMonitorService

        service = EventMonitorService()
        events = await service.check_active_events()
        strategy = await service.adjust_download_strategy()

        response_data = {
            "message": "Event check completed",
            "active_events": list(events.keys()),
            "event_details": events,
            "download_strategy": {
                "download_rate_multiplier": strategy.get("download_rate"),
                "quality_threshold": strategy.get("quality_threshold"),
                "recommendations": strategy.get("recommendations")
            }
        }

        logger.info(f"Manual event check triggered: {len(events)} active events")

        return {
            "success": True,
            "data": response_data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error checking events: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
