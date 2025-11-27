"""
Book Management Routes
FastAPI router for book CRUD operations, metadata tracking, and search
"""

from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import logging

from backend.database import get_db
from backend.services.book_service import BookService
from backend.models.book import Book
from backend.rate_limit import limiter, get_rate_limit

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# ============================================================================
# Pydantic Models (Request/Response schemas)
# ============================================================================

class BookCreate(BaseModel):
    """Schema for creating a new book"""
    title: str = Field(..., min_length=1, max_length=500, description="Book title")
    author: Optional[str] = Field(None, max_length=500, description="Author name")
    abs_id: Optional[str] = Field(None, max_length=255, description="Audiobookshelf ID")
    series: Optional[str] = Field(None, max_length=500, description="Series name")
    series_number: Optional[str] = Field(None, max_length=50, description="Position in series")
    isbn: Optional[str] = Field(None, max_length=50, description="ISBN identifier")
    asin: Optional[str] = Field(None, max_length=50, description="Amazon ASIN")
    publisher: Optional[str] = Field(None, max_length=500, description="Publisher name")
    published_year: Optional[int] = Field(None, description="Year of publication")
    duration_minutes: Optional[int] = Field(None, description="Audiobook duration in minutes")
    description: Optional[str] = Field(None, description="Book description/synopsis")
    import_source: Optional[str] = Field(None, max_length=100, description="Import source")
    metadata_source: Optional[dict] = Field(None, description="Field -> source mapping")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "The Name of the Wind",
                "author": "Patrick Rothfuss",
                "abs_id": "li_abc123xyz",
                "series": "The Kingkiller Chronicle",
                "series_number": "1",
                "isbn": "9780756404079",
                "publisher": "DAW Books",
                "published_year": 2007,
                "duration_minutes": 1037,
                "description": "A legendary story about a legendary hero.",
                "import_source": "user_import"
            }
        }


class BookUpdate(BaseModel):
    """Schema for updating book fields"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    author: Optional[str] = Field(None, max_length=500)
    series: Optional[str] = Field(None, max_length=500)
    series_number: Optional[str] = Field(None, max_length=50)
    isbn: Optional[str] = Field(None, max_length=50)
    asin: Optional[str] = Field(None, max_length=50)
    publisher: Optional[str] = Field(None, max_length=500)
    published_year: Optional[int] = None
    duration_minutes: Optional[int] = None
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|duplicate|archived)$")

    class Config:
        json_schema_extra = {
            "example": {
                "series": "The Kingkiller Chronicle",
                "series_number": "1",
                "published_year": 2007
            }
        }


class MetadataSourceUpdate(BaseModel):
    """Schema for updating metadata source"""
    field_name: str = Field(..., description="Field name (e.g., 'title', 'author')")
    source: str = Field(..., description="Source name (e.g., 'GoogleBooks', 'Goodreads')")

    class Config:
        json_schema_extra = {
            "example": {
                "field_name": "description",
                "source": "GoogleBooks"
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
    summary="List all books",
    description="Get paginated list of books with optional filtering by status and search query"
)
@limiter.limit(get_rate_limit("authenticated"))
async def list_books(
    request: Request,
    limit: int = Query(100, ge=1, le=500, description="Maximum results per page"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    status: Optional[str] = Query("active", description="Filter by status (active, duplicate, archived, or null for all)"),
    search: Optional[str] = Query(None, description="Search query for title/author"),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of books with optional filtering and search

    - **limit**: Maximum number of results (1-500, default 100)
    - **offset**: Number of records to skip for pagination (default 0)
    - **status**: Filter by status (active, duplicate, archived, or null for all)
    - **search**: Optional search query to filter by title or author

    Returns:
        Standard response with book list, total count, and pagination info
    """
    try:
        # If search query provided, use search instead of get_all
        if search:
            result = BookService.search_books(db, query=search, limit=limit)
            if not result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result["error"]
                )

            # Convert books to dict format
            books_data = [
                {
                    "id": book.id,
                    "abs_id": book.abs_id,
                    "title": book.title,
                    "author": book.author,
                    "series": book.series,
                    "series_number": book.series_number,
                    "metadata_completeness_percent": book.metadata_completeness_percent,
                    "status": book.status,
                    "date_added": book.date_added.isoformat() if book.date_added else None
                }
                for book in result["data"]
            ]

            return {
                "success": True,
                "data": {
                    "books": books_data,
                    "total": result["count"],
                    "page_info": {
                        "limit": limit,
                        "offset": 0,
                        "has_more": False
                    }
                },
                "error": None,
                "timestamp": datetime.utcnow().isoformat()
            }

        # Normal pagination
        result = BookService.get_all_books(
            db,
            status=status if status else None,
            limit=limit,
            offset=offset
        )

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        # Convert books to dict format
        books_data = [
            {
                "id": book.id,
                "abs_id": book.abs_id,
                "title": book.title,
                "author": book.author,
                "series": book.series,
                "series_number": book.series_number,
                "metadata_completeness_percent": book.metadata_completeness_percent,
                "status": book.status,
                "date_added": book.date_added.isoformat() if book.date_added else None
            }
            for book in result["data"]
        ]

        return {
            "success": True,
            "data": {
                "books": books_data,
                "total": result["total"],
                "page_info": result["page_info"]
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing books: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/{book_id}",
    response_model=StandardResponse,
    summary="Get single book",
    description="Get detailed information about a specific book including all metadata"
)
@limiter.limit(get_rate_limit("authenticated"))
async def get_book(
    request: Request,
    book_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific book

    - **book_id**: Book ID (integer)

    Returns:
        Standard response with complete book details
    """
    try:
        result = BookService.get_book(db, book_id)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )

        book = result["data"]

        # Convert book to dict with all fields
        book_data = {
            "id": book.id,
            "abs_id": book.abs_id,
            "title": book.title,
            "author": book.author,
            "series": book.series,
            "series_number": book.series_number,
            "isbn": book.isbn,
            "asin": book.asin,
            "publisher": book.publisher,
            "published_year": book.published_year,
            "duration_minutes": book.duration_minutes,
            "description": book.description,
            "metadata_completeness_percent": book.metadata_completeness_percent,
            "last_metadata_update": book.last_metadata_update.isoformat() if book.last_metadata_update else None,
            "metadata_source": book.metadata_source,
            "date_added": book.date_added.isoformat() if book.date_added else None,
            "date_updated": book.date_updated.isoformat() if book.date_updated else None,
            "import_source": book.import_source,
            "status": book.status
        }

        return {
            "success": True,
            "data": book_data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting book {book_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post(
    "/",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create book",
    description="Create a new book record with metadata"
)
@limiter.limit(get_rate_limit("authenticated"))
async def create_book(
    request: Request,
    book: BookCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new book record

    Request body should contain book metadata following the BookCreate schema.

    Returns:
        Standard response with created book data and book_id
    """
    try:
        # Extract metadata fields
        metadata_dict = {
            "series": book.series,
            "series_number": book.series_number,
            "isbn": book.isbn,
            "asin": book.asin,
            "publisher": book.publisher,
            "published_year": book.published_year,
            "duration_minutes": book.duration_minutes,
            "description": book.description,
            "import_source": book.import_source,
            "metadata_source": book.metadata_source or {}
        }

        result = BookService.create_book(
            db,
            title=book.title,
            author=book.author,
            abs_id=book.abs_id,
            metadata_dict=metadata_dict
        )

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )

        created_book = result["data"]

        return {
            "success": True,
            "data": {
                "book_id": result["book_id"],
                "title": created_book.title,
                "author": created_book.author,
                "metadata_completeness_percent": created_book.metadata_completeness_percent
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating book: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.put(
    "/{book_id}",
    response_model=StandardResponse,
    summary="Update book",
    description="Update book fields"
)
@limiter.limit(get_rate_limit("authenticated"))
async def update_book(
    request: Request,
    book_id: int,
    updates: BookUpdate,
    db: Session = Depends(get_db)
):
    """
    Update book fields

    - **book_id**: Book ID to update
    - Request body contains fields to update (only provided fields will be updated)

    Returns:
        Standard response with updated book data and changes made
    """
    try:
        # Convert Pydantic model to dict, excluding unset fields
        updates_dict = updates.model_dump(exclude_unset=True)

        if not updates_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update"
            )

        result = BookService.update_book(db, book_id, updates_dict)

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
                "book_id": book_id,
                "changes_made": result["changes_made"],
                "metadata_completeness_percent": result["data"].metadata_completeness_percent
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating book {book_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.delete(
    "/{book_id}",
    response_model=StandardResponse,
    summary="Delete book",
    description="Soft delete book (marks as archived)"
)
@limiter.limit(get_rate_limit("authenticated"))
async def delete_book(
    request: Request,
    book_id: int,
    db: Session = Depends(get_db)
):
    """
    Soft delete a book (marks status as 'archived')

    - **book_id**: Book ID to delete

    Returns:
        Standard response with deletion confirmation
    """
    try:
        result = BookService.delete_book(db, book_id)

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
        logger.error(f"Error deleting book {book_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/{book_id}/metadata-history",
    response_model=StandardResponse,
    summary="Get metadata correction history",
    description="Get all metadata corrections for a specific book"
)
@limiter.limit(get_rate_limit("authenticated"))
async def get_metadata_history(
    request: Request,
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
        # First verify book exists
        book_result = BookService.get_book(db, book_id)
        if not book_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=book_result["error"]
            )

        book = book_result["data"]

        # Get metadata corrections from relationship
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
            for correction in book.metadata_corrections
        ]

        return {
            "success": True,
            "data": {
                "book_id": book_id,
                "book_title": book.title,
                "corrections": corrections_data,
                "total_corrections": len(corrections_data)
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metadata history for book {book_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/series/{series_name}",
    response_model=StandardResponse,
    summary="Get books in series",
    description="Get all books in a specific series, sorted by series number"
)
@limiter.limit(get_rate_limit("authenticated"))
async def get_books_by_series(
    request: Request,
    series_name: str,
    db: Session = Depends(get_db)
):
    """
    Get all books in a specific series

    - **series_name**: Series name (exact match)

    Returns:
        Standard response with list of books sorted by series_number
    """
    try:
        result = BookService.get_books_by_series(db, series_name)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        # Convert books to dict format
        books_data = [
            {
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "series_number": book.series_number,
                "published_year": book.published_year,
                "metadata_completeness_percent": book.metadata_completeness_percent,
                "status": book.status
            }
            for book in result["data"]
        ]

        return {
            "success": True,
            "data": {
                "series_name": series_name,
                "books": books_data,
                "total_books": result["count"]
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting books for series '{series_name}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/search",
    response_model=StandardResponse,
    summary="Search books",
    description="Full-text search for books by title or author"
)
@limiter.limit(get_rate_limit("search"))
async def search_books(
    request: Request,
    query: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results"),
    db: Session = Depends(get_db)
):
    """
    Search for books by title or author

    - **query**: Search query string (searches in title and author fields)
    - **limit**: Maximum number of results (1-100, default 10)

    Returns:
        Standard response with matching books
    """
    try:
        result = BookService.search_books(db, query=query, limit=limit)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        # Convert books to dict format
        books_data = [
            {
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "series": book.series,
                "series_number": book.series_number,
                "metadata_completeness_percent": book.metadata_completeness_percent,
                "status": book.status
            }
            for book in result["data"]
        ]

        return {
            "success": True,
            "data": {
                "query": query,
                "books": books_data,
                "total_results": result["count"]
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching books with query '{query}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.put(
    "/{book_id}/metadata-source",
    response_model=StandardResponse,
    summary="Update metadata source",
    description="Track which source provided a specific metadata field"
)
@limiter.limit(get_rate_limit("metadata"))
async def update_metadata_source(
    request: Request,
    book_id: int,
    metadata_update: MetadataSourceUpdate,
    db: Session = Depends(get_db)
):
    """
    Update which source provided a specific metadata field

    - **book_id**: Book ID
    - **field_name**: Field name (e.g., 'title', 'author', 'description')
    - **source**: Source name (e.g., 'GoogleBooks', 'Goodreads', 'Manual')

    Returns:
        Standard response with update confirmation
    """
    try:
        result = BookService.update_metadata_source(
            db,
            book_id=book_id,
            field_name=metadata_update.field_name,
            source=metadata_update.source
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
                "book_id": book_id,
                "field_name": metadata_update.field_name,
                "source": metadata_update.source,
                "metadata_source": result["data"].metadata_source
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating metadata source for book {book_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/incomplete-metadata",
    response_model=StandardResponse,
    summary="Get books with incomplete metadata",
    description="Get books below metadata completeness threshold"
)
@limiter.limit(get_rate_limit("authenticated"))
async def get_incomplete_metadata_books(
    request: Request,
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
                "series": book.series,
                "metadata_completeness_percent": book.metadata_completeness_percent,
                "last_metadata_update": book.last_metadata_update.isoformat() if book.last_metadata_update else None,
                "missing_fields": _get_missing_fields(book)
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


# ============================================================================
# Helper Functions
# ============================================================================

def _get_missing_fields(book: Book) -> List[str]:
    """
    Identify which metadata fields are missing from a book

    Args:
        book: Book object

    Returns:
        List of missing field names
    """
    fields_to_check = [
        'author', 'series', 'series_number', 'isbn', 'asin',
        'publisher', 'published_year', 'duration_minutes', 'description'
    ]

    missing = []
    for field in fields_to_check:
        value = getattr(book, field, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)

    return missing
