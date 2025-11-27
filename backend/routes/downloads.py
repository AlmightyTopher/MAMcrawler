"""
Download Queue and Tracking Routes
FastAPI router for download management, queue operations, and status tracking
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import logging

from backend.database import get_db
from backend.services.download_service import DownloadService
from backend.rate_limit import limiter, get_rate_limit

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# ============================================================================
# Pydantic Models (Request/Response schemas)
# ============================================================================

class DownloadCreate(BaseModel):
    """Schema for creating a new download"""
    book_id: Optional[int] = Field(None, description="Book ID (if book exists)")
    missing_book_id: Optional[int] = Field(None, description="Missing book ID")
    title: str = Field(..., min_length=1, max_length=500, description="Book title")
    author: Optional[str] = Field(None, max_length=500, description="Author name")
    source: str = Field(..., description="Download source (MAM, GoogleBooks, Goodreads, Manual)")
    magnet_link: Optional[str] = Field(None, description="Magnet link for torrent")
    torrent_url: Optional[str] = Field(None, description="URL to torrent file")

    class Config:
        json_schema_extra = {
            "example": {
                "book_id": 123,
                "title": "The Name of the Wind",
                "author": "Patrick Rothfuss",
                "source": "MAM",
                "magnet_link": "magnet:?xt=urn:btih:..."
            }
        }


class DownloadStatusUpdate(BaseModel):
    """Schema for updating download status"""
    status: str = Field(..., pattern="^(queued|downloading|completed|failed|abandoned)$")
    qb_hash: Optional[str] = Field(None, description="qBittorrent info hash")
    qb_status: Optional[str] = Field(None, description="qBittorrent status")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "downloading",
                "qb_hash": "abc123def456",
                "qb_status": "downloading"
            }
        }


class DownloadMarkComplete(BaseModel):
    """Schema for marking download as completed"""
    abs_import_status: str = Field(
        "pending",
        pattern="^(pending|imported|import_failed)$",
        description="Audiobookshelf import status"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "abs_import_status": "imported"
            }
        }


class DownloadMarkFailed(BaseModel):
    """Schema for marking download as failed"""
    error_msg: str = Field(..., description="Error message")
    retry_attempt: int = Field(1, ge=1, description="Current retry attempt number")

    class Config:
        json_schema_extra = {
            "example": {
                "error_msg": "Connection timeout",
                "retry_attempt": 2
            }
        }


class DownloadRetry(BaseModel):
    """Schema for scheduling download retry"""
    days_until_retry: int = Field(1, ge=1, le=30, description="Days to wait before retry")

    class Config:
        json_schema_extra = {
            "example": {
                "days_until_retry": 3
            }
        }


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
    "/",
    response_model=StandardResponse,
    summary="List downloads",
    description="Get downloads filtered by status with pagination"
)
async def list_downloads(
    status_filter: Optional[str] = Query(
        None,
        description="Filter by status (queued, downloading, completed, failed, abandoned)"
    ),
    limit: int = Query(100, ge=1, le=500, description="Maximum results per page"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    db: Session = Depends(get_db)
):
    """
    Get list of downloads filtered by status

    - **status_filter**: Optional filter by status
    - **limit**: Maximum number of results (1-500, default 100)
    - **offset**: Number of records to skip for pagination (default 0)

    Returns:
        Standard response with download list, total count, and pagination info
    """
    try:
        from backend.models.download import Download

        # Build query
        query = db.query(Download)

        if status_filter:
            query = query.filter(Download.status == status_filter)

        # Get total count
        total = query.count()

        # Get paginated results
        downloads = query.order_by(
            Download.date_queued.desc()
        ).limit(limit).offset(offset).all()

        # Convert downloads to dict format
        downloads_data = [
            {
                "id": download.id,
                "book_id": download.book_id,
                "missing_book_id": download.missing_book_id,
                "title": download.title,
                "author": download.author,
                "source": download.source,
                "status": download.status,
                "qbittorrent_status": download.qbittorrent_status,
                "abs_import_status": download.abs_import_status,
                "retry_count": download.retry_count,
                "max_retries": download.max_retries,
                "date_queued": download.date_queued.isoformat() if download.date_queued else None,
                "date_completed": download.date_completed.isoformat() if download.date_completed else None,
                "last_attempt": download.last_attempt.isoformat() if download.last_attempt else None,
                "next_retry": download.next_retry.isoformat() if download.next_retry else None
            }
            for download in downloads
        ]

        return {
            "success": True,
            "data": {
                "downloads": downloads_data,
                "total": total,
                "page_info": {
                    "limit": limit,
                    "offset": offset,
                    "has_more": (offset + limit) < total
                }
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error listing downloads: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/{download_id}",
    response_model=StandardResponse,
    summary="Get download",
    description="Get detailed information about a specific download"
)
async def get_download(
    download_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific download

    - **download_id**: Download ID (integer)

    Returns:
        Standard response with complete download details
    """
    try:
        result = DownloadService.get_download(db, download_id)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )

        download = result["data"]

        # Convert download to dict with all fields
        download_data = {
            "id": download.id,
            "book_id": download.book_id,
            "missing_book_id": download.missing_book_id,
            "title": download.title,
            "author": download.author,
            "source": download.source,
            "magnet_link": download.magnet_link,
            "torrent_url": download.torrent_url,
            "status": download.status,
            "qbittorrent_hash": download.qbittorrent_hash,
            "qbittorrent_status": download.qbittorrent_status,
            "abs_import_status": download.abs_import_status,
            "abs_import_error": download.abs_import_error,
            "retry_count": download.retry_count,
            "max_retries": download.max_retries,
            "date_queued": download.date_queued.isoformat() if download.date_queued else None,
            "date_completed": download.date_completed.isoformat() if download.date_completed else None,
            "last_attempt": download.last_attempt.isoformat() if download.last_attempt else None,
            "next_retry": download.next_retry.isoformat() if download.next_retry else None
        }

        return {
            "success": True,
            "data": download_data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting download {download_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post(
    "/",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Queue download",
    description="Add a new download to the queue"
)
async def queue_download(
    download: DownloadCreate,
    db: Session = Depends(get_db)
):
    """
    Queue a new download

    Request body should contain download information following the DownloadCreate schema.
    Either magnet_link or torrent_url must be provided.

    Returns:
        Standard response with created download data and download_id
    """
    try:
        result = DownloadService.create_download(
            db,
            book_id=download.book_id,
            source=download.source,
            title=download.title,
            author=download.author,
            magnet_link=download.magnet_link,
            torrent_url=download.torrent_url,
            missing_book_id=download.missing_book_id
        )

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )

        created_download = result["data"]

        return {
            "success": True,
            "data": {
                "download_id": result["download_id"],
                "title": created_download.title,
                "author": created_download.author,
                "source": created_download.source,
                "status": created_download.status
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error queueing download: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.put(
    "/{download_id}/status",
    response_model=StandardResponse,
    summary="Update download status",
    description="Update download status and qBittorrent information"
)
async def update_download_status(
    download_id: int,
    status_update: DownloadStatusUpdate,
    db: Session = Depends(get_db)
):
    """
    Update download status

    - **download_id**: Download ID to update
    - Request body contains new status and optional qBittorrent details

    Returns:
        Standard response with updated download data
    """
    try:
        result = DownloadService.update_status(
            db,
            download_id=download_id,
            status=status_update.status,
            qb_hash=status_update.qb_hash,
            qb_status=status_update.qb_status
        )

        if not result["success"]:
            if "not found" in result["error"]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result["error"]
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        updated_download = result["data"]

        return {
            "success": True,
            "data": {
                "download_id": download_id,
                "status": updated_download.status,
                "qbittorrent_status": updated_download.qbittorrent_status,
                "last_attempt": updated_download.last_attempt.isoformat() if updated_download.last_attempt else None
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating download {download_id} status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.put(
    "/{download_id}/mark-complete",
    response_model=StandardResponse,
    summary="Mark download complete",
    description="Mark download as completed with import status"
)
async def mark_download_complete(
    download_id: int,
    complete_data: DownloadMarkComplete,
    db: Session = Depends(get_db)
):
    """
    Mark download as completed

    - **download_id**: Download ID
    - **abs_import_status**: Audiobookshelf import status (pending, imported, import_failed)

    Returns:
        Standard response with completion confirmation
    """
    try:
        result = DownloadService.mark_completed(
            db,
            download_id=download_id,
            abs_import_status=complete_data.abs_import_status
        )

        if not result["success"]:
            if "not found" in result["error"]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result["error"]
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        completed_download = result["data"]

        return {
            "success": True,
            "data": {
                "download_id": download_id,
                "title": completed_download.title,
                "status": completed_download.status,
                "abs_import_status": completed_download.abs_import_status,
                "date_completed": completed_download.date_completed.isoformat() if completed_download.date_completed else None
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking download {download_id} as complete: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.put(
    "/{download_id}/mark-failed",
    response_model=StandardResponse,
    summary="Mark download failed",
    description="Mark download as failed with error message"
)
async def mark_download_failed(
    download_id: int,
    failed_data: DownloadMarkFailed,
    db: Session = Depends(get_db)
):
    """
    Mark download as failed

    - **download_id**: Download ID
    - **error_msg**: Error message describing the failure
    - **retry_attempt**: Current retry attempt number

    If retry_attempt >= max_retries, download will be marked as 'abandoned'.

    Returns:
        Standard response with failure confirmation
    """
    try:
        result = DownloadService.mark_failed(
            db,
            download_id=download_id,
            error_msg=failed_data.error_msg,
            retry_attempt=failed_data.retry_attempt
        )

        if not result["success"]:
            if "not found" in result["error"]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result["error"]
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        failed_download = result["data"]

        return {
            "success": True,
            "data": {
                "download_id": download_id,
                "title": failed_download.title,
                "status": failed_download.status,
                "retry_count": failed_download.retry_count,
                "max_retries": failed_download.max_retries,
                "error": failed_download.abs_import_error
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking download {download_id} as failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.put(
    "/{download_id}/retry",
    response_model=StandardResponse,
    summary="Schedule download retry",
    description="Schedule download for retry after specified delay"
)
async def schedule_download_retry(
    download_id: int,
    retry_data: DownloadRetry,
    db: Session = Depends(get_db)
):
    """
    Schedule download for retry

    - **download_id**: Download ID
    - **days_until_retry**: Number of days to wait before retry (1-30)

    Returns:
        Standard response with retry schedule confirmation
    """
    try:
        result = DownloadService.schedule_retry(
            db,
            download_id=download_id,
            days_until_retry=retry_data.days_until_retry
        )

        if not result["success"]:
            if "not found" in result["error"]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result["error"]
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        return {
            "success": True,
            "data": {
                "download_id": download_id,
                "next_retry": result["next_retry"],
                "days_until_retry": retry_data.days_until_retry
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scheduling retry for download {download_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/pending",
    response_model=StandardResponse,
    summary="Get pending downloads",
    description="Get all downloads with 'queued' status"
)
async def get_pending_downloads(
    db: Session = Depends(get_db)
):
    """
    Get all pending downloads (status = 'queued')

    Returns:
        Standard response with list of queued downloads
    """
    try:
        result = DownloadService.get_all_pending(db)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        # Convert downloads to dict format
        downloads_data = [
            {
                "id": download.id,
                "title": download.title,
                "author": download.author,
                "source": download.source,
                "status": download.status,
                "retry_count": download.retry_count,
                "date_queued": download.date_queued.isoformat() if download.date_queued else None,
                "next_retry": download.next_retry.isoformat() if download.next_retry else None
            }
            for download in result["data"]
        ]

        return {
            "success": True,
            "data": {
                "downloads": downloads_data,
                "total_pending": result["count"]
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pending downloads: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/failed",
    response_model=StandardResponse,
    summary="Get failed downloads",
    description="Get all downloads with 'failed' or 'abandoned' status"
)
async def get_failed_downloads(
    db: Session = Depends(get_db)
):
    """
    Get all failed downloads (status = 'failed' or 'abandoned')

    Returns:
        Standard response with list of failed downloads
    """
    try:
        result = DownloadService.get_failed_downloads(db)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        # Convert downloads to dict format
        downloads_data = [
            {
                "id": download.id,
                "title": download.title,
                "author": download.author,
                "source": download.source,
                "status": download.status,
                "retry_count": download.retry_count,
                "max_retries": download.max_retries,
                "error": download.abs_import_error,
                "last_attempt": download.last_attempt.isoformat() if download.last_attempt else None
            }
            for download in result["data"]
        ]

        return {
            "success": True,
            "data": {
                "downloads": downloads_data,
                "total_failed": result["count"]
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting failed downloads: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/retry-due",
    response_model=StandardResponse,
    summary="Get downloads ready to retry",
    description="Get downloads with next_retry <= current time"
)
async def get_retry_due_downloads(
    db: Session = Depends(get_db)
):
    """
    Get downloads ready to retry (next_retry <= now)

    Returns:
        Standard response with list of downloads ready for retry
    """
    try:
        result = DownloadService.get_retry_due(db)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        # Convert downloads to dict format
        downloads_data = [
            {
                "id": download.id,
                "title": download.title,
                "author": download.author,
                "source": download.source,
                "retry_count": download.retry_count,
                "next_retry": download.next_retry.isoformat() if download.next_retry else None,
                "last_attempt": download.last_attempt.isoformat() if download.last_attempt else None
            }
            for download in result["data"]
        ]

        return {
            "success": True,
            "data": {
                "downloads": downloads_data,
                "total_ready_for_retry": result["count"]
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting retry-due downloads: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.delete(
    "/{download_id}",
    response_model=StandardResponse,
    summary="Remove download",
    description="Remove download from queue (hard delete)"
)
async def remove_download(
    download_id: int,
    db: Session = Depends(get_db)
):
    """
    Remove download from queue

    WARNING: This is a hard delete and cannot be undone.

    - **download_id**: Download ID to remove

    Returns:
        Standard response with deletion confirmation
    """
    try:
        from backend.models.download import Download

        # Get download first
        download = db.query(Download).filter(Download.id == download_id).first()

        if not download:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Download with ID {download_id} not found"
            )

        download_title = download.title

        # Delete download
        db.delete(download)
        db.commit()

        logger.info(f"Removed download {download_id}: {download_title}")

        return {
            "success": True,
            "data": {
                "message": f"Download '{download_title}' removed from queue"
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error removing download {download_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
