"""
Pydantic request/response models for API endpoints
Provides type validation, serialization, and OpenAPI documentation
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class ImportSource(str, Enum):
    """Source of book import"""
    USER_IMPORT = "user_import"
    MAM_SCRAPER = "mam_scraper"
    SERIES_COMPLETION = "series_completion"
    AUTHOR_DISCOVERY = "author_discovery"


class BookStatus(str, Enum):
    """Book status options"""
    ACTIVE = "active"
    DUPLICATE = "duplicate"
    ARCHIVED = "archived"


class DownloadStatus(str, Enum):
    """Download status options"""
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class DownloadSource(str, Enum):
    """Download source options"""
    MAM = "MAM"
    GOOGLE_BOOKS = "GoogleBooks"
    GOODREADS = "Goodreads"
    MANUAL = "Manual"


class TaskStatus(str, Enum):
    """Task execution status"""
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskName(str, Enum):
    """Scheduled task names"""
    MAM = "MAM"
    TOP10 = "TOP10"
    METADATA_FULL = "METADATA_FULL"
    METADATA_NEW = "METADATA_NEW"
    SERIES = "SERIES"
    AUTHOR = "AUTHOR"


class CompletionStatus(str, Enum):
    """Series/Author completion status"""
    COMPLETE = "complete"
    PARTIAL = "partial"
    INCOMPLETE = "incomplete"


# ============================================================================
# BOOK SCHEMAS
# ============================================================================

class BookBase(BaseModel):
    """Base book schema with common fields"""
    title: str = Field(..., min_length=1, max_length=500, description="Book title")
    author: Optional[str] = Field(None, max_length=500, description="Author name")
    series: Optional[str] = Field(None, max_length=500, description="Series name")
    series_number: Optional[str] = Field(None, max_length=50, description="Position in series (e.g., '3' or '3.5')")
    isbn: Optional[str] = Field(None, max_length=50, description="ISBN identifier")
    asin: Optional[str] = Field(None, max_length=50, description="Amazon Standard Identifier")
    publisher: Optional[str] = Field(None, max_length=500, description="Publisher name")
    published_year: Optional[int] = Field(None, ge=1000, le=9999, description="Year of publication")
    duration_minutes: Optional[int] = Field(None, ge=0, description="Audiobook duration in minutes")
    description: Optional[str] = Field(None, description="Book description/synopsis")
    import_source: Optional[ImportSource] = Field(None, description="Where book came from")
    status: Optional[BookStatus] = Field(BookStatus.ACTIVE, description="Current status")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "The Fellowship of the Ring",
                "author": "J.R.R. Tolkien",
                "series": "The Lord of the Rings",
                "series_number": "1",
                "isbn": "9780547928210",
                "asin": "B007978NPG",
                "publisher": "Houghton Mifflin Harcourt",
                "published_year": 1954,
                "duration_minutes": 1140,
                "description": "The first volume of The Lord of the Rings trilogy",
                "import_source": "user_import",
                "status": "active"
            }
        }
    )


class BookCreate(BookBase):
    """Schema for creating a new book"""
    abs_id: Optional[str] = Field(None, max_length=255, description="Audiobookshelf internal ID")


class BookUpdate(BaseModel):
    """Schema for updating an existing book (all fields optional)"""
    abs_id: Optional[str] = Field(None, max_length=255, description="Audiobookshelf internal ID")
    title: Optional[str] = Field(None, min_length=1, max_length=500, description="Book title")
    author: Optional[str] = Field(None, max_length=500, description="Author name")
    series: Optional[str] = Field(None, max_length=500, description="Series name")
    series_number: Optional[str] = Field(None, max_length=50, description="Position in series")
    isbn: Optional[str] = Field(None, max_length=50, description="ISBN identifier")
    asin: Optional[str] = Field(None, max_length=50, description="Amazon Standard Identifier")
    publisher: Optional[str] = Field(None, max_length=500, description="Publisher name")
    published_year: Optional[int] = Field(None, ge=1000, le=9999, description="Year of publication")
    duration_minutes: Optional[int] = Field(None, ge=0, description="Audiobook duration in minutes")
    description: Optional[str] = Field(None, description="Book description/synopsis")
    import_source: Optional[ImportSource] = Field(None, description="Where book came from")
    status: Optional[BookStatus] = Field(None, description="Current status")
    metadata_completeness_percent: Optional[int] = Field(None, ge=0, le=100, description="Metadata completeness percentage")


class BookResponse(BookBase):
    """Schema for book response with all fields"""
    id: int = Field(..., description="Database primary key")
    abs_id: Optional[str] = Field(None, description="Audiobookshelf internal ID")
    metadata_completeness_percent: int = Field(..., ge=0, le=100, description="Metadata completeness (0-100)")
    last_metadata_update: Optional[datetime] = Field(None, description="Last metadata update timestamp")
    metadata_source: Dict[str, str] = Field(default_factory=dict, description="Field-to-source mapping")
    date_added: datetime = Field(..., description="When book was added to library")
    date_updated: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "abs_id": "li_abc123def456",
                "title": "The Fellowship of the Ring",
                "author": "J.R.R. Tolkien",
                "series": "The Lord of the Rings",
                "series_number": "1",
                "isbn": "9780547928210",
                "asin": "B007978NPG",
                "publisher": "Houghton Mifflin Harcourt",
                "published_year": 1954,
                "duration_minutes": 1140,
                "description": "The first volume of The Lord of the Rings trilogy",
                "metadata_completeness_percent": 85,
                "last_metadata_update": "2025-11-16T10:30:00",
                "metadata_source": {
                    "title": "Audiobookshelf",
                    "author": "GoogleBooks",
                    "series": "Goodreads",
                    "isbn": "GoogleBooks"
                },
                "date_added": "2025-11-01T08:00:00",
                "date_updated": "2025-11-16T10:30:00",
                "import_source": "user_import",
                "status": "active"
            }
        }
    )


# ============================================================================
# SERIES SCHEMAS
# ============================================================================

class SeriesBase(BaseModel):
    """Base series schema with common fields"""
    name: str = Field(..., min_length=1, max_length=500, description="Series name")
    author: Optional[str] = Field(None, max_length=500, description="Series author")
    goodreads_id: Optional[str] = Field(None, max_length=255, description="Goodreads series ID")
    total_books_in_series: Optional[int] = Field(None, ge=0, description="Total books in series per Goodreads")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "The Lord of the Rings",
                "author": "J.R.R. Tolkien",
                "goodreads_id": "66",
                "total_books_in_series": 3
            }
        }
    )


class SeriesCreate(SeriesBase):
    """Schema for creating a new series"""
    pass


class SeriesUpdate(BaseModel):
    """Schema for updating an existing series (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=500, description="Series name")
    author: Optional[str] = Field(None, max_length=500, description="Series author")
    goodreads_id: Optional[str] = Field(None, max_length=255, description="Goodreads series ID")
    total_books_in_series: Optional[int] = Field(None, ge=0, description="Total books in series")
    books_owned: Optional[int] = Field(None, ge=0, description="Number of books owned")
    books_missing: Optional[int] = Field(None, ge=0, description="Number of books missing")
    completion_percentage: Optional[int] = Field(None, ge=0, le=100, description="Completion percentage")
    completion_status: Optional[CompletionStatus] = Field(None, description="Completion status")


class SeriesResponse(SeriesBase):
    """Schema for series response with all fields"""
    id: int = Field(..., description="Database primary key")
    books_owned: int = Field(..., ge=0, description="Number of books owned")
    books_missing: int = Field(..., ge=0, description="Number of books missing")
    completion_percentage: int = Field(..., ge=0, le=100, description="Completion percentage (0-100)")
    last_completion_check: Optional[datetime] = Field(None, description="Last completion check timestamp")
    completion_status: Optional[CompletionStatus] = Field(None, description="Completion status")
    date_created: datetime = Field(..., description="When series was created")
    date_updated: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "The Lord of the Rings",
                "author": "J.R.R. Tolkien",
                "goodreads_id": "66",
                "total_books_in_series": 3,
                "books_owned": 3,
                "books_missing": 0,
                "completion_percentage": 100,
                "last_completion_check": "2025-11-16T10:00:00",
                "completion_status": "complete",
                "date_created": "2025-11-01T08:00:00",
                "date_updated": "2025-11-16T10:00:00"
            }
        }
    )


# ============================================================================
# AUTHOR SCHEMAS
# ============================================================================

class AuthorBase(BaseModel):
    """Base author schema with common fields"""
    name: str = Field(..., min_length=1, max_length=500, description="Author name")
    goodreads_id: Optional[str] = Field(None, max_length=255, description="Goodreads author ID")
    google_books_id: Optional[str] = Field(None, max_length=255, description="Google Books author ID")
    mam_author_id: Optional[str] = Field(None, max_length=255, description="MyAnonamouse author ID")
    total_audiobooks_external: Optional[int] = Field(None, ge=0, description="Total audiobooks found in external sources")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "J.R.R. Tolkien",
                "goodreads_id": "656983",
                "google_books_id": "abc123",
                "mam_author_id": "12345",
                "total_audiobooks_external": 25
            }
        }
    )


class AuthorCreate(AuthorBase):
    """Schema for creating a new author"""
    pass


class AuthorUpdate(BaseModel):
    """Schema for updating an existing author (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=500, description="Author name")
    goodreads_id: Optional[str] = Field(None, max_length=255, description="Goodreads author ID")
    google_books_id: Optional[str] = Field(None, max_length=255, description="Google Books author ID")
    mam_author_id: Optional[str] = Field(None, max_length=255, description="MyAnonamouse author ID")
    total_audiobooks_external: Optional[int] = Field(None, ge=0, description="Total audiobooks found externally")
    audiobooks_owned: Optional[int] = Field(None, ge=0, description="Number of audiobooks owned")
    audiobooks_missing: Optional[int] = Field(None, ge=0, description="Number of audiobooks missing")
    completion_status: Optional[CompletionStatus] = Field(None, description="Completion status")


class AuthorResponse(AuthorBase):
    """Schema for author response with all fields"""
    id: int = Field(..., description="Database primary key")
    audiobooks_owned: int = Field(..., ge=0, description="Number of audiobooks owned")
    audiobooks_missing: int = Field(..., ge=0, description="Number of audiobooks missing")
    last_completion_check: Optional[datetime] = Field(None, description="Last completion check timestamp")
    completion_status: Optional[CompletionStatus] = Field(None, description="Completion status")
    date_created: datetime = Field(..., description="When author was created")
    date_updated: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "J.R.R. Tolkien",
                "goodreads_id": "656983",
                "google_books_id": "abc123",
                "mam_author_id": "12345",
                "total_audiobooks_external": 25,
                "audiobooks_owned": 20,
                "audiobooks_missing": 5,
                "last_completion_check": "2025-11-16T10:00:00",
                "completion_status": "partial",
                "date_created": "2025-11-01T08:00:00",
                "date_updated": "2025-11-16T10:00:00"
            }
        }
    )


# ============================================================================
# DOWNLOAD SCHEMAS
# ============================================================================

class DownloadBase(BaseModel):
    """Base download schema with common fields"""
    title: str = Field(..., min_length=1, max_length=500, description="Book title")
    author: Optional[str] = Field(None, max_length=500, description="Author name")
    source: DownloadSource = Field(..., description="Download source")
    magnet_link: Optional[str] = Field(None, description="Magnet link for torrent")
    torrent_url: Optional[str] = Field(None, description="URL to torrent file")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "The Two Towers",
                "author": "J.R.R. Tolkien",
                "source": "MAM",
                "magnet_link": "magnet:?xt=urn:btih:abc123...",
                "torrent_url": None
            }
        }
    )


class DownloadCreate(DownloadBase):
    """Schema for creating a new download"""
    book_id: Optional[int] = Field(None, description="Foreign key to books table")
    missing_book_id: Optional[int] = Field(None, description="Foreign key to missing_books table")
    priority: Optional[int] = Field(1, ge=1, le=3, description="Download priority (1=high, 2=medium, 3=low)")


class DownloadUpdate(BaseModel):
    """Schema for updating an existing download (all fields optional)"""
    title: Optional[str] = Field(None, min_length=1, max_length=500, description="Book title")
    author: Optional[str] = Field(None, max_length=500, description="Author name")
    source: Optional[DownloadSource] = Field(None, description="Download source")
    magnet_link: Optional[str] = Field(None, description="Magnet link")
    torrent_url: Optional[str] = Field(None, description="Torrent URL")
    qbittorrent_hash: Optional[str] = Field(None, max_length=255, description="qBittorrent info hash")
    qbittorrent_status: Optional[str] = Field(None, max_length=100, description="qBittorrent status")
    status: Optional[DownloadStatus] = Field(None, description="Overall download status")
    retry_count: Optional[int] = Field(None, ge=0, description="Number of retry attempts")
    max_retries: Optional[int] = Field(None, ge=0, description="Maximum allowed retries")
    abs_import_status: Optional[str] = Field(None, max_length=100, description="Audiobookshelf import status")
    abs_import_error: Optional[str] = Field(None, description="Import error message")


class DownloadResponse(DownloadBase):
    """Schema for download response with all fields"""
    id: int = Field(..., description="Database primary key")
    book_id: Optional[int] = Field(None, description="Associated book ID")
    missing_book_id: Optional[int] = Field(None, description="Associated missing book ID")
    qbittorrent_hash: Optional[str] = Field(None, description="qBittorrent info hash")
    qbittorrent_status: Optional[str] = Field(None, description="qBittorrent status")
    status: DownloadStatus = Field(..., description="Overall download status")
    retry_count: int = Field(..., ge=0, description="Number of retry attempts")
    max_retries: int = Field(..., ge=0, description="Maximum allowed retries")
    last_attempt: Optional[datetime] = Field(None, description="Last attempt timestamp")
    next_retry: Optional[datetime] = Field(None, description="Next retry timestamp")
    abs_import_status: Optional[str] = Field(None, description="Audiobookshelf import status")
    abs_import_error: Optional[str] = Field(None, description="Import error message")
    date_queued: datetime = Field(..., description="When download was queued")
    date_completed: Optional[datetime] = Field(None, description="When download was completed")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "book_id": None,
                "missing_book_id": 5,
                "title": "The Two Towers",
                "author": "J.R.R. Tolkien",
                "source": "MAM",
                "magnet_link": "magnet:?xt=urn:btih:abc123...",
                "torrent_url": None,
                "qbittorrent_hash": "abc123def456",
                "qbittorrent_status": "downloading",
                "status": "downloading",
                "retry_count": 0,
                "max_retries": 3,
                "last_attempt": "2025-11-16T10:00:00",
                "next_retry": None,
                "abs_import_status": "pending",
                "abs_import_error": None,
                "date_queued": "2025-11-16T09:00:00",
                "date_completed": None
            }
        }
    )


# ============================================================================
# METADATA SCHEMAS
# ============================================================================

class MetadataCorrectionResponse(BaseModel):
    """Schema for metadata correction history response"""
    id: int = Field(..., description="Database primary key")
    book_id: int = Field(..., description="Associated book ID")
    field_name: str = Field(..., description="Field that was corrected")
    old_value: Optional[str] = Field(None, description="Previous value")
    new_value: Optional[str] = Field(None, description="New value")
    source: str = Field(..., description="Source of correction")
    reason: Optional[str] = Field(None, description="Reason for correction")
    correction_date: datetime = Field(..., description="When correction was made")
    corrected_by: str = Field(..., description="Username or 'system'")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "book_id": 15,
                "field_name": "author",
                "old_value": "J.R. Tolkien",
                "new_value": "J.R.R. Tolkien",
                "source": "GoogleBooks",
                "reason": "Author name standardization",
                "correction_date": "2025-11-16T10:30:00",
                "corrected_by": "system"
            }
        }
    )


class MetadataStatusResponse(BaseModel):
    """Schema for metadata status dashboard response"""
    total_books: int = Field(..., description="Total number of books")
    avg_completeness: float = Field(..., ge=0, le=100, description="Average metadata completeness percentage")
    books_below_threshold: int = Field(..., description="Books with completeness below threshold")
    corrections_by_source: Dict[str, int] = Field(..., description="Correction count by source")
    recent_corrections: List[MetadataCorrectionResponse] = Field(..., description="Recent corrections (last 10)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_books": 1500,
                "avg_completeness": 82.5,
                "books_below_threshold": 120,
                "corrections_by_source": {
                    "GoogleBooks": 450,
                    "Goodreads": 320,
                    "Manual": 75,
                    "Auto-corrected": 200
                },
                "recent_corrections": []
            }
        }
    )


# ============================================================================
# TASK SCHEMAS
# ============================================================================

class TaskResponse(BaseModel):
    """Schema for task execution history response"""
    id: int = Field(..., description="Database primary key")
    task_name: TaskName = Field(..., description="Task name")
    scheduled_time: Optional[datetime] = Field(None, description="When task was scheduled")
    actual_start: Optional[datetime] = Field(None, description="When task started")
    actual_end: Optional[datetime] = Field(None, description="When task ended")
    duration_seconds: Optional[int] = Field(None, description="Execution duration in seconds")
    status: TaskStatus = Field(..., description="Task status")
    items_processed: int = Field(..., description="Total items processed")
    items_succeeded: int = Field(..., description="Number of successful items")
    items_failed: int = Field(..., description="Number of failed items")
    log_output: Optional[str] = Field(None, description="Full log output")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Task-specific metadata")
    date_created: datetime = Field(..., description="When task record was created")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "task_name": "METADATA_FULL",
                "scheduled_time": "2025-11-16T02:00:00",
                "actual_start": "2025-11-16T02:00:05",
                "actual_end": "2025-11-16T02:45:30",
                "duration_seconds": 2725,
                "status": "completed",
                "items_processed": 1500,
                "items_succeeded": 1480,
                "items_failed": 20,
                "log_output": "Task execution logs...",
                "error_message": None,
                "metadata": {"source": "GoogleBooks", "threshold": 70},
                "date_created": "2025-11-16T02:00:00"
            }
        }
    )


class TaskHistoryResponse(BaseModel):
    """Schema for task history with aggregated statistics"""
    task_name: TaskName = Field(..., description="Task name")
    total_executions: int = Field(..., description="Total number of executions")
    successful_executions: int = Field(..., description="Number of successful executions")
    failed_executions: int = Field(..., description="Number of failed executions")
    avg_duration_seconds: Optional[float] = Field(None, description="Average execution duration")
    last_execution: Optional[TaskResponse] = Field(None, description="Most recent execution")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_name": "METADATA_FULL",
                "total_executions": 30,
                "successful_executions": 28,
                "failed_executions": 2,
                "avg_duration_seconds": 2650.5,
                "last_execution": None
            }
        }
    )


# ============================================================================
# SYSTEM SCHEMAS
# ============================================================================

class SystemStatsResponse(BaseModel):
    """Schema for system statistics response"""
    total_books: int = Field(..., description="Total number of books")
    total_series: int = Field(..., description="Total number of series")
    total_authors: int = Field(..., description="Total number of authors")
    total_downloads: int = Field(..., description="Total number of downloads")
    active_downloads: int = Field(..., description="Number of active downloads")
    queued_downloads: int = Field(..., description="Number of queued downloads")
    completed_downloads: int = Field(..., description="Number of completed downloads")
    failed_downloads: int = Field(..., description="Number of failed downloads")
    avg_metadata_completeness: float = Field(..., ge=0, le=100, description="Average metadata completeness")
    books_below_threshold: int = Field(..., description="Books with metadata below 70%")
    series_complete: int = Field(..., description="Number of complete series")
    series_partial: int = Field(..., description="Number of partial series")
    recent_tasks: List[TaskResponse] = Field(..., description="Recent task executions (last 5)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_books": 1500,
                "total_series": 250,
                "total_authors": 400,
                "total_downloads": 350,
                "active_downloads": 5,
                "queued_downloads": 12,
                "completed_downloads": 320,
                "failed_downloads": 13,
                "avg_metadata_completeness": 82.5,
                "books_below_threshold": 120,
                "series_complete": 180,
                "series_partial": 70,
                "recent_tasks": []
            }
        }
    )


class HealthResponse(BaseModel):
    """Schema for health check response"""
    status: str = Field(..., description="Health status (healthy, degraded, unhealthy)")
    timestamp: datetime = Field(..., description="Check timestamp")
    database_connected: bool = Field(..., description="Database connection status")
    scheduler_running: bool = Field(..., description="Scheduler status")
    integrations: Dict[str, bool] = Field(..., description="External integration status")
    version: str = Field(..., description="API version")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "timestamp": "2025-11-16T10:00:00",
                "database_connected": True,
                "scheduler_running": True,
                "integrations": {
                    "audiobookshelf": True,
                    "qbittorrent": True,
                    "prowlarr": True,
                    "google_books": True
                },
                "version": "1.0.0"
            }
        }
    )


# ============================================================================
# ERROR SCHEMAS
# ============================================================================

class ErrorResponse(BaseModel):
    """Schema for error responses"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    path: Optional[str] = Field(None, description="Request path that caused the error")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "BookNotFoundError",
                "message": "Book with ID 999 not found",
                "details": {"book_id": 999},
                "timestamp": "2025-11-16T10:00:00",
                "path": "/api/books/999"
            }
        }
    )


# ============================================================================
# PAGINATION SCHEMAS
# ============================================================================

T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response schema"""
    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [],
                "total": 1500,
                "page": 1,
                "page_size": 20,
                "total_pages": 75,
                "has_next": True,
                "has_prev": False
            }
        }
    )


# ============================================================================
# VALIDATORS
# ============================================================================

@field_validator('series_number', mode='before')
def validate_series_number(cls, v):
    """Validate series number format"""
    if v is None:
        return v

    # Allow integers and floats as strings (e.g., "1", "3.5")
    try:
        float(v)
        return str(v)
    except ValueError:
        raise ValueError("Series number must be a valid number or decimal (e.g., '3' or '3.5')")


# Apply validator to both BookBase and BookUpdate
BookBase.model_fields['series_number'].metadata.append(validate_series_number)
BookUpdate.model_fields['series_number'].metadata.append(validate_series_number)
