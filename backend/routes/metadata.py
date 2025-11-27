"""
Metadata Operations Routes
FastAPI router for metadata correction, quality tracking, and cleanup operations
"""

from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import logging

from backend.database import get_db
from backend.services.metadata_service import MetadataService
from backend.services.book_service import BookService
from backend.rate_limit import limiter, get_rate_limit

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# ============================================================================
# Pydantic Models (Request/Response schemas)
# ============================================================================

class MetadataCorrectBook(BaseModel):
    """Schema for triggering single book metadata correction"""
    book_id: int = Field(..., description="Book ID to correct")
    force: bool = Field(False, description="Force correction even if recently updated")

    class Config:
        json_schema_extra = {
            "example": {
                "book_id": 123,
                "force": False
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

@router.post(
    "/correct-book",
    response_model=StandardResponse,
    summary="Correct single book metadata",
    description="Trigger metadata correction for a specific book"
)
async def correct_book_metadata(
    correct_data: MetadataCorrectBook,
    db: Session = Depends(get_db)
):
    """
    Trigger metadata correction for a single book

    This will fetch metadata from GoogleBooks and other sources to fill in
    missing or incomplete fields.

    - **book_id**: Book ID to correct
    - **force**: Force correction even if recently updated (default False)

    Returns:
        Standard response with correction results
    """
    try:
        # Get book first
        book_result = BookService.get_book(db, correct_data.book_id)
        if not book_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=book_result["error"]
            )

        book = book_result["data"]

        # Check if recently updated (unless force=True)
        if not correct_data.force and book.last_metadata_update:
            hours_since_update = (datetime.now() - book.last_metadata_update).total_seconds() / 3600
            if hours_since_update < 24:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Book was updated {int(hours_since_update)} hours ago. Use force=True to override."
                )

        # Trigger metadata correction
        result = MetadataService.correct_book_metadata(db, correct_data.book_id)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        return {
            "success": True,
            "data": {
                "book_id": correct_data.book_id,
                "book_title": book.title,
                "corrections_made": result.get("corrections_made", 0),
                "new_completeness": result.get("metadata_completeness_percent", 0),
                "sources_used": result.get("sources_used", [])
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error correcting book metadata: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post(
    "/correct-all",
    response_model=StandardResponse,
    summary="Correct all book metadata",
    description="Trigger full library metadata correction (long-running operation)"
)
async def correct_all_metadata(
    completeness_threshold: int = Query(80, ge=0, le=100, description="Only correct books below this threshold"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum books to process"),
    db: Session = Depends(get_db)
):
    """
    Trigger full library metadata correction

    WARNING: This is a long-running operation that may take considerable time.

    - **completeness_threshold**: Only correct books below this percentage (0-100, default 80)
    - **limit**: Maximum number of books to process (1-1000, default 100)

    Returns:
        Standard response with batch correction results
    """
    try:
        result = MetadataService.correct_all_books(
            db,
            completeness_threshold=completeness_threshold,
            limit=limit
        )

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        return {
            "success": True,
            "data": {
                "books_processed": result.get("books_processed", 0),
                "books_corrected": result.get("books_corrected", 0),
                "total_corrections": result.get("total_corrections", 0),
                "average_completeness_before": result.get("avg_completeness_before", 0),
                "average_completeness_after": result.get("avg_completeness_after", 0),
                "duration_seconds": result.get("duration_seconds", 0)
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error correcting all metadata: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post(
    "/correct-recent",
    response_model=StandardResponse,
    summary="Correct recent books metadata",
    description="Correct metadata for recently added books (last 7 days)"
)
async def correct_recent_metadata(
    days: int = Query(7, ge=1, le=30, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """
    Correct metadata for recently added books

    - **days**: Number of days to look back (1-30, default 7)

    Returns:
        Standard response with correction results
    """
    try:
        result = MetadataService.correct_recent_books(db, days=days)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        return {
            "success": True,
            "data": {
                "days": days,
                "books_processed": result.get("books_processed", 0),
                "books_corrected": result.get("books_corrected", 0),
                "total_corrections": result.get("total_corrections", 0)
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error correcting recent metadata: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/history/{book_id}",
    response_model=StandardResponse,
    summary="Get correction history",
    description="Get metadata correction history for a specific book"
)
async def get_correction_history(
    book_id: int,
    db: Session = Depends(get_db)
):
    """
    Get metadata correction history for a book

    - **book_id**: Book ID

    Returns:
        Standard response with list of metadata corrections
    """
    try:
        result = MetadataService.get_correction_history(db, book_id)

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

        # Convert corrections to dict format
        corrections_data = [
            {
                "id": correction.id,
                "field_name": correction.field_name,
                "old_value": correction.old_value,
                "new_value": correction.new_value,
                "source": correction.source,
                "reason": correction.reason,
                "correction_date": correction.correction_date.isoformat() if correction.correction_date else None,
                "corrected_by": correction.corrected_by
            }
            for correction in result["data"]
        ]

        return {
            "success": True,
            "data": {
                "book_id": book_id,
                "corrections": corrections_data,
                "total_corrections": result["count"]
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting correction history for book {book_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/status",
    response_model=StandardResponse,
    summary="Get metadata quality status",
    description="Get overall metadata quality statistics"
)
async def get_metadata_status(
    db: Session = Depends(get_db)
):
    """
    Get overall metadata quality status

    Returns:
        Standard response with library-wide metadata quality metrics
    """
    try:
        result = MetadataService.get_quality_status(db)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        return {
            "success": True,
            "data": result["stats"],
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metadata status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/by-source",
    response_model=StandardResponse,
    summary="Get corrections by source",
    description="Get metadata corrections grouped by source"
)
async def get_corrections_by_source(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """
    Get metadata corrections grouped by source

    - **days**: Number of days to look back (1-365, default 30)

    Returns:
        Standard response with corrections grouped by source
    """
    try:
        from backend.models.metadata_correction import MetadataCorrection
        from sqlalchemy import func

        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days)

        # Query corrections grouped by source
        source_counts = db.query(
            MetadataCorrection.source,
            func.count(MetadataCorrection.id).label('count')
        ).filter(
            MetadataCorrection.correction_date >= cutoff_date
        ).group_by(
            MetadataCorrection.source
        ).all()

        source_breakdown = {
            source: count
            for source, count in source_counts
        }

        total_corrections = sum(source_breakdown.values())

        return {
            "success": True,
            "data": {
                "days": days,
                "cutoff_date": cutoff_date.isoformat(),
                "total_corrections": total_corrections,
                "source_breakdown": source_breakdown
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting corrections by source: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/incomplete",
    response_model=StandardResponse,
    summary="Get books with incomplete metadata",
    description="Get books below completeness threshold"
)
async def get_incomplete_metadata(
    threshold: int = Query(80, ge=0, le=100, description="Completeness threshold percentage"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    db: Session = Depends(get_db)
):
    """
    Get books with incomplete metadata (below threshold)

    - **threshold**: Completeness threshold (0-100%, default 80)
    - **limit**: Maximum number of results (1-500, default 100)

    Returns:
        Standard response with books needing metadata improvement
    """
    try:
        from backend.models.book import Book

        # Query books below threshold
        books = db.query(Book).filter(
            Book.metadata_completeness_percent < threshold,
            Book.status == "active"
        ).order_by(
            Book.metadata_completeness_percent.asc()
        ).limit(limit).all()

        # Convert to dict format
        books_data = [
            {
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "metadata_completeness_percent": book.metadata_completeness_percent,
                "last_metadata_update": book.last_metadata_update.isoformat() if book.last_metadata_update else None,
                "metadata_source": book.metadata_source
            }
            for book in books
        ]

        return {
            "success": True,
            "data": {
                "threshold": threshold,
                "books": books_data,
                "total_incomplete": len(books_data)
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting incomplete metadata books: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.delete(
    "/cleanup-old",
    response_model=StandardResponse,
    summary="Cleanup old metadata corrections",
    description="Manually trigger cleanup of metadata corrections older than 30 days"
)
async def cleanup_old_corrections(
    days: int = Query(30, ge=1, le=365, description="Delete corrections older than this many days"),
    db: Session = Depends(get_db)
):
    """
    Manually trigger cleanup of old metadata corrections

    - **days**: Delete corrections older than this many days (1-365, default 30)

    Returns:
        Standard response with deletion count
    """
    try:
        result = MetadataService.cleanup_old_corrections(db, days=days)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        return {
            "success": True,
            "data": {
                "deleted_count": result["deleted_count"],
                "cutoff_date": result["cutoff_date"],
                "days": days
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up old corrections: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
