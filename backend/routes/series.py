"""
Series Management Routes
FastAPI router for series CRUD operations, completion tracking, and statistics
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import logging

from backend.database import get_db
from backend.services.series_service import SeriesService
from backend.services.book_service import BookService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# ============================================================================
# Pydantic Models (Request/Response schemas)
# ============================================================================

class SeriesCreate(BaseModel):
    """Schema for creating a new series"""
    name: str = Field(..., min_length=1, max_length=500, description="Series name")
    author: Optional[str] = Field(None, max_length=500, description="Series author")
    goodreads_id: Optional[str] = Field(None, max_length=100, description="Goodreads series ID")
    total_books: Optional[int] = Field(None, ge=1, description="Total books in series")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "The Kingkiller Chronicle",
                "author": "Patrick Rothfuss",
                "goodreads_id": "45262",
                "total_books": 3
            }
        }


class SeriesUpdate(BaseModel):
    """Schema for updating series fields"""
    name: Optional[str] = Field(None, min_length=1, max_length=500)
    author: Optional[str] = Field(None, max_length=500)
    goodreads_id: Optional[str] = Field(None, max_length=100)
    total_books_in_series: Optional[int] = Field(None, ge=1)

    class Config:
        json_schema_extra = {
            "example": {
                "total_books_in_series": 3
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
    summary="List all series",
    description="Get paginated list of series with optional completion status filter"
)
async def list_series(
    limit: int = Query(100, ge=1, le=500, description="Maximum results per page"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    completion_status: Optional[str] = Query(
        None,
        description="Filter by completion status (complete, partial, incomplete)"
    ),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of all series

    - **limit**: Maximum number of results (1-500, default 100)
    - **offset**: Number of records to skip for pagination (default 0)
    - **completion_status**: Optional filter by completion status

    Returns:
        Standard response with series list, total count, and pagination info
    """
    try:
        result = SeriesService.get_all_series(db, limit=limit, offset=offset)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        # Filter by completion status if provided
        series_list = result["data"]
        if completion_status:
            series_list = [s for s in series_list if s.completion_status == completion_status]

        # Convert series to dict format
        series_data = [
            {
                "id": series.id,
                "name": series.name,
                "author": series.author,
                "goodreads_id": series.goodreads_id,
                "total_books_in_series": series.total_books_in_series,
                "books_owned": series.books_owned,
                "books_missing": series.books_missing,
                "completion_percentage": series.completion_percentage,
                "completion_status": series.completion_status,
                "last_completion_check": series.last_completion_check.isoformat() if series.last_completion_check else None,
                "date_added": series.date_added.isoformat() if series.date_added else None
            }
            for series in series_list
        ]

        return {
            "success": True,
            "data": {
                "series": series_data,
                "total": len(series_data) if completion_status else result["total"],
                "page_info": result["page_info"]
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing series: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/{series_id}",
    response_model=StandardResponse,
    summary="Get single series",
    description="Get detailed information about a specific series including book list"
)
async def get_series(
    series_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific series

    - **series_id**: Series ID (integer)

    Returns:
        Standard response with complete series details and book list
    """
    try:
        result = SeriesService.get_series(db, series_id)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )

        series = result["data"]

        # Get books in this series
        books_result = BookService.get_books_by_series(db, series.name)
        books_data = []
        if books_result["success"]:
            books_data = [
                {
                    "id": book.id,
                    "title": book.title,
                    "series_number": book.series_number,
                    "published_year": book.published_year,
                    "status": book.status
                }
                for book in books_result["data"]
            ]

        # Convert series to dict with all fields
        series_data = {
            "id": series.id,
            "name": series.name,
            "author": series.author,
            "goodreads_id": series.goodreads_id,
            "total_books_in_series": series.total_books_in_series,
            "books_owned": series.books_owned,
            "books_missing": series.books_missing,
            "completion_percentage": series.completion_percentage,
            "completion_status": series.completion_status,
            "last_completion_check": series.last_completion_check.isoformat() if series.last_completion_check else None,
            "date_added": series.date_added.isoformat() if series.date_added else None,
            "date_updated": series.date_updated.isoformat() if series.date_updated else None,
            "books": books_data
        }

        return {
            "success": True,
            "data": series_data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting series {series_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post(
    "/",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create series",
    description="Create a new series record"
)
async def create_series(
    series: SeriesCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new series record

    Request body should contain series information following the SeriesCreate schema.

    Returns:
        Standard response with created series data and series_id
    """
    try:
        result = SeriesService.create_series(
            db,
            name=series.name,
            author=series.author,
            goodreads_id=series.goodreads_id,
            total_books=series.total_books
        )

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )

        created_series = result["data"]

        return {
            "success": True,
            "data": {
                "series_id": result["series_id"],
                "name": created_series.name,
                "author": created_series.author,
                "completion_percentage": created_series.completion_percentage
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating series: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.put(
    "/{series_id}",
    response_model=StandardResponse,
    summary="Update series",
    description="Update series fields"
)
async def update_series(
    series_id: int,
    updates: SeriesUpdate,
    db: Session = Depends(get_db)
):
    """
    Update series fields

    - **series_id**: Series ID to update
    - Request body contains fields to update (only provided fields will be updated)

    Returns:
        Standard response with updated series data and changes made
    """
    try:
        # Convert Pydantic model to dict, excluding unset fields
        updates_dict = updates.model_dump(exclude_unset=True)

        if not updates_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update"
            )

        result = SeriesService.update_series(db, series_id, updates_dict)

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
                "series_id": series_id,
                "changes_made": result["changes_made"],
                "completion_percentage": result["data"].completion_percentage
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating series {series_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.delete(
    "/{series_id}",
    response_model=StandardResponse,
    summary="Delete series",
    description="Delete series record (hard delete - use with caution)"
)
async def delete_series(
    series_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a series record

    WARNING: This is a hard delete and cannot be undone.

    - **series_id**: Series ID to delete

    Returns:
        Standard response with deletion confirmation
    """
    try:
        result = SeriesService.delete_series(db, series_id)

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
            "data": {"message": result["message"]},
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting series {series_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/{series_id}/completion",
    response_model=StandardResponse,
    summary="Get series completion",
    description="Get completion percentage and statistics for a series"
)
async def get_series_completion(
    series_id: int,
    db: Session = Depends(get_db)
):
    """
    Get completion percentage and statistics for a series

    - **series_id**: Series ID

    Returns:
        Standard response with completion statistics
    """
    try:
        result = SeriesService.get_series(db, series_id)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )

        series = result["data"]

        completion_data = {
            "series_id": series.id,
            "series_name": series.name,
            "total_books_in_series": series.total_books_in_series,
            "books_owned": series.books_owned,
            "books_missing": series.books_missing,
            "completion_percentage": series.completion_percentage,
            "completion_status": series.completion_status,
            "last_completion_check": series.last_completion_check.isoformat() if series.last_completion_check else None
        }

        return {
            "success": True,
            "data": completion_data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting series completion for {series_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/completion-summary",
    response_model=StandardResponse,
    summary="Get completion summary",
    description="Get summary statistics for all series completion"
)
async def get_completion_summary(
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for all series completion

    Returns:
        Standard response with overall completion statistics
    """
    try:
        result = SeriesService.get_series_completion_summary(db)

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
        logger.error(f"Error getting series completion summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.put(
    "/{series_id}/recalculate-completion",
    response_model=StandardResponse,
    summary="Recalculate completion",
    description="Manually trigger recalculation of series completion statistics"
)
async def recalculate_completion(
    series_id: int,
    db: Session = Depends(get_db)
):
    """
    Manually trigger recalculation of series completion statistics

    This updates books_owned, books_missing, completion_percentage, and completion_status
    by counting actual books in the database.

    - **series_id**: Series ID

    Returns:
        Standard response with updated statistics
    """
    try:
        result = SeriesService.update_completion_status(db, series_id)

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
                "series_id": series_id,
                "stats": result["stats"]
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recalculating completion for series {series_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/incomplete",
    response_model=StandardResponse,
    summary="Get incomplete series",
    description="Get all series with completion percentage < 100%"
)
async def get_incomplete_series(
    min_completion: int = Query(0, ge=0, le=100, description="Minimum completion percentage"),
    max_completion: int = Query(99, ge=0, le=100, description="Maximum completion percentage"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    db: Session = Depends(get_db)
):
    """
    Get incomplete series (completion < 100%)

    - **min_completion**: Minimum completion percentage (0-100, default 0)
    - **max_completion**: Maximum completion percentage (0-100, default 99)
    - **limit**: Maximum number of results (1-500, default 100)

    Returns:
        Standard response with incomplete series sorted by completion percentage
    """
    try:
        from backend.models.series import Series

        # Query incomplete series
        series_list = db.query(Series).filter(
            Series.completion_percentage >= min_completion,
            Series.completion_percentage <= max_completion
        ).order_by(
            Series.completion_percentage.asc(),
            Series.name
        ).limit(limit).all()

        # Convert to dict format
        series_data = [
            {
                "id": series.id,
                "name": series.name,
                "author": series.author,
                "total_books_in_series": series.total_books_in_series,
                "books_owned": series.books_owned,
                "books_missing": series.books_missing,
                "completion_percentage": series.completion_percentage,
                "completion_status": series.completion_status
            }
            for series in series_list
        ]

        return {
            "success": True,
            "data": {
                "min_completion": min_completion,
                "max_completion": max_completion,
                "series": series_data,
                "total_incomplete": len(series_data)
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting incomplete series: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
