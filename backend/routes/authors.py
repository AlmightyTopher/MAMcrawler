"""
Author Management Routes
FastAPI router for author CRUD operations, book tracking, and completion statistics
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import logging

from backend.database import get_db
from backend.services.author_service import AuthorService
from backend.services.book_service import BookService
from backend.rate_limit import limiter, get_rate_limit

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# ============================================================================
# Pydantic Models (Request/Response schemas)
# ============================================================================

class AuthorCreate(BaseModel):
    """Schema for creating a new author"""
    name: str = Field(..., min_length=1, max_length=500, description="Author name")
    goodreads_id: Optional[str] = Field(None, max_length=100, description="Goodreads author ID")
    google_books_id: Optional[str] = Field(None, max_length=100, description="Google Books author ID")
    total_books: Optional[int] = Field(None, ge=1, description="Total books by author")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Patrick Rothfuss",
                "goodreads_id": "108424",
                "total_books": 10
            }
        }


class AuthorUpdate(BaseModel):
    """Schema for updating author fields"""
    name: Optional[str] = Field(None, min_length=1, max_length=500)
    goodreads_id: Optional[str] = Field(None, max_length=100)
    google_books_id: Optional[str] = Field(None, max_length=100)
    total_books_authored: Optional[int] = Field(None, ge=1)

    class Config:
        json_schema_extra = {
            "example": {
                "total_books_authored": 12
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
    summary="List all authors",
    description="Get paginated list of authors with book counts"
)
async def list_authors(
    limit: int = Query(100, ge=1, le=500, description="Maximum results per page"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of all authors

    - **limit**: Maximum number of results (1-500, default 100)
    - **offset**: Number of records to skip for pagination (default 0)

    Returns:
        Standard response with author list, total count, and pagination info
    """
    try:
        result = AuthorService.get_all_authors(db, limit=limit, offset=offset)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        # Convert authors to dict format
        authors_data = [
            {
                "id": author.id,
                "name": author.name,
                "goodreads_id": author.goodreads_id,
                "google_books_id": author.google_books_id,
                "total_books_authored": author.total_books_authored,
                "books_owned": author.books_owned,
                "books_missing": author.books_missing,
                "completion_percentage": author.completion_percentage,
                "completion_status": author.completion_status,
                "date_added": author.date_added.isoformat() if author.date_added else None
            }
            for author in result["data"]
        ]

        return {
            "success": True,
            "data": {
                "authors": authors_data,
                "total": result["total"],
                "page_info": result["page_info"]
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing authors: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/{author_id}",
    response_model=StandardResponse,
    summary="Get single author",
    description="Get detailed information about a specific author including book list"
)
async def get_author(
    author_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific author

    - **author_id**: Author ID (integer)

    Returns:
        Standard response with complete author details and book list
    """
    try:
        result = AuthorService.get_author(db, author_id)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )

        author = result["data"]

        # Get books by this author
        books_result = AuthorService.get_books_by_author(db, author_id)
        books_data = []
        if books_result["success"]:
            books_data = [
                {
                    "id": book.id,
                    "title": book.title,
                    "series": book.series,
                    "series_number": book.series_number,
                    "published_year": book.published_year,
                    "status": book.status
                }
                for book in books_result["data"]
            ]

        # Convert author to dict with all fields
        author_data = {
            "id": author.id,
            "name": author.name,
            "goodreads_id": author.goodreads_id,
            "google_books_id": author.google_books_id,
            "total_books_authored": author.total_books_authored,
            "books_owned": author.books_owned,
            "books_missing": author.books_missing,
            "completion_percentage": author.completion_percentage,
            "completion_status": author.completion_status,
            "last_completion_check": author.last_completion_check.isoformat() if author.last_completion_check else None,
            "date_added": author.date_added.isoformat() if author.date_added else None,
            "date_updated": author.date_updated.isoformat() if author.date_updated else None,
            "books": books_data
        }

        return {
            "success": True,
            "data": author_data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting author {author_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post(
    "/",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create author",
    description="Create a new author record"
)
async def create_author(
    author: AuthorCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new author record

    Request body should contain author information following the AuthorCreate schema.

    Returns:
        Standard response with created author data and author_id
    """
    try:
        result = AuthorService.create_author(
            db,
            name=author.name,
            goodreads_id=author.goodreads_id,
            google_books_id=author.google_books_id,
            total_books=author.total_books
        )

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )

        created_author = result["data"]

        return {
            "success": True,
            "data": {
                "author_id": result["author_id"],
                "name": created_author.name,
                "completion_percentage": created_author.completion_percentage
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating author: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.put(
    "/{author_id}",
    response_model=StandardResponse,
    summary="Update author",
    description="Update author fields"
)
async def update_author(
    author_id: int,
    updates: AuthorUpdate,
    db: Session = Depends(get_db)
):
    """
    Update author fields

    - **author_id**: Author ID to update
    - Request body contains fields to update (only provided fields will be updated)

    Returns:
        Standard response with updated author data and changes made
    """
    try:
        # Convert Pydantic model to dict, excluding unset fields
        updates_dict = updates.model_dump(exclude_unset=True)

        if not updates_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update"
            )

        result = AuthorService.update_author(db, author_id, updates_dict)

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
                "author_id": author_id,
                "changes_made": result["changes_made"],
                "completion_percentage": result["data"].completion_percentage
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating author {author_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.delete(
    "/{author_id}",
    response_model=StandardResponse,
    summary="Delete author",
    description="Delete author record (hard delete - use with caution)"
)
async def delete_author(
    author_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete an author record

    WARNING: This is a hard delete and cannot be undone.

    - **author_id**: Author ID to delete

    Returns:
        Standard response with deletion confirmation
    """
    try:
        result = AuthorService.delete_author(db, author_id)

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
        logger.error(f"Error deleting author {author_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/{author_id}/books",
    response_model=StandardResponse,
    summary="Get author's books",
    description="Get all books by a specific author"
)
async def get_author_books(
    author_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all books by a specific author

    - **author_id**: Author ID

    Returns:
        Standard response with list of books by this author
    """
    try:
        result = AuthorService.get_books_by_author(db, author_id)

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

        # Convert books to dict format
        books_data = [
            {
                "id": book.id,
                "title": book.title,
                "series": book.series,
                "series_number": book.series_number,
                "published_year": book.published_year,
                "status": book.status
            }
            for book in result["data"]
        ]

        return {
            "success": True,
            "data": {
                "author_id": author_id,
                "author_name": result.get("author_name"),
                "books": books_data,
                "total_books": result["count"]
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting books for author {author_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/{author_id}/completion",
    response_model=StandardResponse,
    summary="Get author completion",
    description="Get completion percentage and statistics for an author"
)
async def get_author_completion(
    author_id: int,
    db: Session = Depends(get_db)
):
    """
    Get completion percentage and statistics for an author

    - **author_id**: Author ID

    Returns:
        Standard response with completion statistics
    """
    try:
        result = AuthorService.get_author(db, author_id)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )

        author = result["data"]

        completion_data = {
            "author_id": author.id,
            "author_name": author.name,
            "total_books_authored": author.total_books_authored,
            "books_owned": author.books_owned,
            "books_missing": author.books_missing,
            "completion_percentage": author.completion_percentage,
            "completion_status": author.completion_status,
            "last_completion_check": author.last_completion_check.isoformat() if author.last_completion_check else None
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
        logger.error(f"Error getting author completion for {author_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/favorites",
    response_model=StandardResponse,
    summary="Get favorite authors",
    description="Get authors with 2 or more books owned"
)
async def get_favorite_authors(
    min_books: int = Query(2, ge=1, description="Minimum books owned to be considered a favorite"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    db: Session = Depends(get_db)
):
    """
    Get favorite authors (those with multiple books in library)

    - **min_books**: Minimum books owned (default 2)
    - **limit**: Maximum number of results (1-500, default 100)

    Returns:
        Standard response with favorite authors sorted by books_owned descending
    """
    try:
        from backend.models.author import Author

        # Query authors with >= min_books owned
        authors = db.query(Author).filter(
            Author.books_owned >= min_books
        ).order_by(
            Author.books_owned.desc(),
            Author.name
        ).limit(limit).all()

        # Convert to dict format
        authors_data = [
            {
                "id": author.id,
                "name": author.name,
                "total_books_authored": author.total_books_authored,
                "books_owned": author.books_owned,
                "books_missing": author.books_missing,
                "completion_percentage": author.completion_percentage,
                "completion_status": author.completion_status
            }
            for author in authors
        ]

        return {
            "success": True,
            "data": {
                "min_books": min_books,
                "authors": authors_data,
                "total_favorites": len(authors_data)
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting favorite authors: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/completion-summary",
    response_model=StandardResponse,
    summary="Get completion summary",
    description="Get summary statistics for all authors"
)
async def get_completion_summary(
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for all authors

    Returns:
        Standard response with overall author completion statistics
    """
    try:
        result = AuthorService.get_author_completion_summary(db)

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
        logger.error(f"Error getting author completion summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.put(
    "/{author_id}/recalculate-completion",
    response_model=StandardResponse,
    summary="Recalculate completion",
    description="Manually trigger recalculation of author completion statistics"
)
async def recalculate_completion(
    author_id: int,
    db: Session = Depends(get_db)
):
    """
    Manually trigger recalculation of author completion statistics

    This updates books_owned, books_missing, completion_percentage, and completion_status
    by counting actual books in the database.

    - **author_id**: Author ID

    Returns:
        Standard response with updated statistics
    """
    try:
        result = AuthorService.update_completion_status(db, author_id)

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
                "author_id": author_id,
                "stats": result["stats"]
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recalculating completion for author {author_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
