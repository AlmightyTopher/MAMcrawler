# Backend Schemas & Utils Guide

Complete guide to using the request/response schemas and utility modules in the audiobook management system.

## Overview

Five production-ready files have been created:

1. **backend/schemas.py** (689 lines) - Pydantic request/response models
2. **backend/utils/errors.py** (623 lines) - Custom exception classes
3. **backend/utils/logging.py** (451 lines) - Logging configuration
4. **backend/utils/helpers.py** (829 lines) - Utility functions
5. **backend/utils/__init__.py** (222 lines) - Package initialization

**Total: 2,814 lines of production-ready code**

---

## 1. Schemas (backend/schemas.py)

Pydantic models for API request/response validation with OpenAPI documentation support.

### Book Schemas

```python
from backend.schemas import BookCreate, BookUpdate, BookResponse

# Create a new book
book_data = BookCreate(
    title="The Fellowship of the Ring",
    author="J.R.R. Tolkien",
    series="The Lord of the Rings",
    series_number="1",
    isbn="9780547928210",
    asin="B007978NPG",
    publisher="Houghton Mifflin Harcourt",
    published_year=1954,
    duration_minutes=1140,
    description="The first volume of The Lord of the Rings trilogy",
    import_source="user_import",
    status="active"
)

# Update existing book (all fields optional)
update_data = BookUpdate(
    title="The Fellowship of the Ring (Unabridged)",
    metadata_completeness_percent=95
)

# Response model (from database)
book_response = BookResponse(
    id=1,
    abs_id="li_abc123def456",
    title="The Fellowship of the Ring",
    author="J.R.R. Tolkien",
    # ... all other fields
    metadata_completeness_percent=85,
    date_added=datetime.now(),
    date_updated=datetime.now()
)
```

### Series Schemas

```python
from backend.schemas import SeriesCreate, SeriesUpdate, SeriesResponse

series_data = SeriesCreate(
    name="The Lord of the Rings",
    author="J.R.R. Tolkien",
    goodreads_id="66",
    total_books_in_series=3
)

series_response = SeriesResponse(
    id=1,
    name="The Lord of the Rings",
    books_owned=3,
    books_missing=0,
    completion_percentage=100,
    completion_status="complete"
)
```

### Author Schemas

```python
from backend.schemas import AuthorCreate, AuthorUpdate, AuthorResponse

author_data = AuthorCreate(
    name="J.R.R. Tolkien",
    goodreads_id="656983",
    total_audiobooks_external=25
)
```

### Download Schemas

```python
from backend.schemas import DownloadCreate, DownloadUpdate, DownloadResponse

download_data = DownloadCreate(
    title="The Two Towers",
    author="J.R.R. Tolkien",
    source="MAM",
    magnet_link="magnet:?xt=urn:btih:abc123...",
    missing_book_id=5,
    priority=1  # 1=high, 2=medium, 3=low
)
```

### Metadata & Task Schemas

```python
from backend.schemas import (
    MetadataCorrectionResponse,
    MetadataStatusResponse,
    TaskResponse,
    TaskHistoryResponse
)

# Metadata correction history
correction = MetadataCorrectionResponse(
    id=1,
    book_id=15,
    field_name="author",
    old_value="J.R. Tolkien",
    new_value="J.R.R. Tolkien",
    source="GoogleBooks",
    correction_date=datetime.now()
)

# Task execution result
task = TaskResponse(
    id=1,
    task_name="METADATA_FULL",
    status="completed",
    items_processed=1500,
    items_succeeded=1480,
    items_failed=20,
    duration_seconds=2725
)
```

### System Schemas

```python
from backend.schemas import SystemStatsResponse, HealthResponse, ErrorResponse

# System statistics
stats = SystemStatsResponse(
    total_books=1500,
    total_series=250,
    total_authors=400,
    avg_metadata_completeness=82.5,
    active_downloads=5
)

# Health check
health = HealthResponse(
    status="healthy",
    timestamp=datetime.now(),
    database_connected=True,
    scheduler_running=True,
    integrations={
        "audiobookshelf": True,
        "qbittorrent": True,
        "prowlarr": True
    }
)

# Error response
error = ErrorResponse(
    error="BookNotFoundError",
    message="Book with ID 999 not found",
    details={"book_id": 999},
    path="/api/books/999"
)
```

### Pagination

```python
from backend.schemas import PaginatedResponse, BookResponse

# Generic paginated response
paginated = PaginatedResponse[BookResponse](
    items=[book1, book2, book3],
    total=1500,
    page=1,
    page_size=20,
    total_pages=75,
    has_next=True,
    has_prev=False
)
```

### Enums

```python
from backend.schemas import (
    ImportSource,
    BookStatus,
    DownloadStatus,
    DownloadSource,
    TaskStatus,
    TaskName,
    CompletionStatus
)

# Use enums for type safety
book = BookCreate(
    title="Example",
    import_source=ImportSource.MAM_SCRAPER,
    status=BookStatus.ACTIVE
)

download = DownloadCreate(
    title="Example",
    source=DownloadSource.MAM,
    status=DownloadStatus.QUEUED
)
```

---

## 2. Error Classes (backend/utils/errors.py)

Custom exceptions with HTTP status codes and automatic logging.

### Basic Usage

```python
from backend.utils.errors import (
    BookNotFoundError,
    SeriesNotFoundError,
    AuthorNotFoundError,
    MetadataError,
    ExternalAPIError,
    DatabaseError
)

# Resource not found (404)
raise BookNotFoundError(book_id=999)
# Output: "Book with ID 999 not found" (status: 404)

raise SeriesNotFoundError(series_name="The Lord of the Rings")
# Output: "Series 'The Lord of the Rings' not found" (status: 404)

# Validation error (400)
raise MetadataError(
    message="Invalid ISBN format",
    field="isbn",
    value="12345"
)

# External API error (502)
raise ExternalAPIError(
    service="GoogleBooks",
    message="Request timeout",
    status_code=504
)

# Database error (500)
raise DatabaseError(
    message="Failed to insert book",
    operation="INSERT",
    table="books"
)
```

### Error Response in FastAPI

```python
from fastapi import HTTPException
from backend.utils.errors import BookNotFoundError, handle_exception, get_status_code

@app.get("/books/{book_id}")
async def get_book(book_id: int):
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise BookNotFoundError(book_id=book_id)
        return book
    except Exception as e:
        error_dict = handle_exception(e)
        raise HTTPException(
            status_code=get_status_code(e),
            detail=error_dict
        )
```

### Available Exceptions

| Exception | Status Code | Use Case |
|-----------|-------------|----------|
| `BookNotFoundError` | 404 | Book not found in database |
| `SeriesNotFoundError` | 404 | Series not found |
| `AuthorNotFoundError` | 404 | Author not found |
| `DownloadNotFoundError` | 404 | Download not found |
| `MetadataError` | 400 | Metadata validation error |
| `InvalidCredentialsError` | 401 | Authentication failed |
| `SchedulerError` | 500 | Task scheduler error |
| `ExternalAPIError` | 502 | External API call failed |
| `DatabaseError` | 500 | Database operation failed |
| `QBittorrentError` | 502 | qBittorrent client error |
| `AudiobookshelfError` | 502 | Audiobookshelf client error |
| `ProwlarrError` | 502 | Prowlarr client error |
| `DuplicateResourceError` | 409 | Resource already exists |
| `RateLimitError` | 429 | Rate limit exceeded |
| `FileSystemError` | 500 | File system operation failed |

---

## 3. Logging (backend/utils/logging.py)

Centralized logging with file rotation and structured output.

### Basic Setup

```python
from backend.utils.logging import setup_logging, get_logger

# Initialize logging (auto-initialized when module is imported)
setup_logging(
    log_level_console="INFO",
    log_level_file="DEBUG",
    log_format="detailed",
    max_file_size_mb=10,
    backup_count=30  # Keep 30 days of logs
)

# Get logger for your module
logger = get_logger(__name__)

logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical error")
```

### Specialized Loggers

```python
from backend.utils.logging import (
    setup_scheduler_logging,
    setup_access_logging,
    log_request
)

# Scheduler logging (separate file)
scheduler_logger = setup_scheduler_logging("DEBUG")
scheduler_logger.info("Task scheduled: METADATA_FULL at 02:00")

# Access logging (HTTP requests)
log_request(
    method="GET",
    path="/api/books/1",
    status_code=200,
    duration_ms=45.3,
    user="admin"
)
```

### Log Files

All logs are stored in `C:\Users\dogma\Projects\MAMcrawler\logs\`:

- **audiobook_system.log** - Main application log (DEBUG level, all events)
- **error.log** - Error-only log (ERROR level and above)
- **access.log** - HTTP request/response log
- **scheduler.log** - Scheduled task execution log

All logs rotate daily and keep 30 days of history.

### Log Formats

**Detailed format** (file logs):
```
2025-11-16 10:30:45 | INFO     | backend.services.book_service | get_book          | Line 45   | Retrieved book ID 123
```

**Simple format** (console):
```
2025-11-16 10:30:45 | INFO     | Retrieved book ID 123
```

**JSON format** (structured):
```json
{"timestamp": "2025-11-16 10:30:45", "level": "INFO", "logger": "backend.services.book_service", "function": "get_book", "line": 45, "message": "Retrieved book ID 123"}
```

### Advanced Features

```python
from backend.utils.logging import LogContext, cleanup_old_logs, get_log_file_info

# Temporary log level change
logger = get_logger(__name__)
with LogContext(logger, logging.DEBUG):
    logger.debug("This will be logged even if normal level is INFO")

# Clean up old logs
cleanup_old_logs(days_to_keep=7)  # Keep only 7 days

# Get log file information
info = get_log_file_info()
print(f"Main log size: {info['main_log']['size_mb']:.2f} MB")
```

---

## 4. Helper Functions (backend/utils/helpers.py)

Reusable utility functions for common operations.

### Time & Duration

```python
from backend.utils.helpers import (
    format_duration,
    parse_duration,
    get_timestamp_iso,
    time_ago
)

# Format duration
format_duration(3665)  # "1h 1m 5s"
format_duration(90)    # "1m 30s"

# Parse duration
parse_duration("1h 30m")      # 5400 seconds
parse_duration("2h 15m 30s")  # 8130 seconds

# Get current timestamp
timestamp = get_timestamp_iso()  # "2025-11-16T10:30:45.123456"

# Human-readable time ago
from datetime import datetime, timedelta
dt = datetime.utcnow() - timedelta(hours=2)
time_ago(dt)  # "2 hours ago"
```

### Metadata Completeness

```python
from backend.utils.helpers import (
    calculate_metadata_completeness,
    get_missing_metadata_fields
)

book_dict = {
    "title": "The Hobbit",
    "author": "J.R.R. Tolkien",
    "series": "Middle Earth",
    "isbn": "9780547928227",
    "published_year": 1937,
    "description": "A fantasy adventure novel"
}

# Calculate completeness (0-100%)
completeness = calculate_metadata_completeness(book_dict)  # 78%

# Get missing fields
missing = get_missing_metadata_fields(book_dict)
# ["publisher", "asin", "duration_minutes"]
```

### Magnet Links & Torrents

```python
from backend.utils.helpers import parse_magnet_link, validate_magnet_link

magnet = "magnet:?xt=urn:btih:abc123def456&dn=MyBook"

# Extract info hash
info_hash = parse_magnet_link(magnet)  # "abc123def456"

# Validate magnet link
is_valid = validate_magnet_link(magnet)  # True
```

### File System

```python
from backend.utils.helpers import (
    sanitize_filename,
    get_file_size_mb,
    ensure_directory_exists
)

# Safe filename
safe = sanitize_filename("My Book: The Story?")  # "My_Book_The_Story"

# File size
size = get_file_size_mb("C:/path/to/audiobook.m4b")  # 245.67

# Ensure directory exists
ensure_directory_exists("C:/path/to/logs")  # Creates if needed
```

### List Utilities

```python
from backend.utils.helpers import chunk_list, deduplicate_list, safe_get

# Split list into chunks
chunks = chunk_list([1, 2, 3, 4, 5, 6, 7], 3)
# [[1, 2, 3], [4, 5, 6], [7]]

# Remove duplicates (preserve order)
unique = deduplicate_list([1, 2, 2, 3, 1, 4])  # [1, 2, 3, 4]

# Safe nested dictionary access
data = {"user": {"profile": {"name": "John"}}}
name = safe_get(data, "user", "profile", "name")  # "John"
theme = safe_get(data, "user", "settings", "theme", default="dark")  # "dark"
```

### String Utilities

```python
from backend.utils.helpers import (
    truncate_string,
    normalize_whitespace,
    extract_numbers
)

# Truncate string
short = truncate_string("This is a very long string", 15)  # "This is a ve..."

# Normalize whitespace
clean = normalize_whitespace("  Too   many    spaces  ")  # "Too many spaces"

# Extract numbers
numbers = extract_numbers("Book 1, Book 2, and Book 3")  # [1, 2, 3]
```

### Validation

```python
from backend.utils.helpers import validate_isbn, validate_asin, validate_year

# Validate ISBN
validate_isbn("9780547928227")  # True
validate_isbn("invalid")        # False

# Validate ASIN
validate_asin("B007978NPG")  # True

# Validate year
validate_year(2025)  # True
validate_year(3000)  # False
```

### Retry Decorator

```python
from backend.utils.helpers import retry_decorator

@retry_decorator(max_retries=3, backoff_factor=2.0)
def unreliable_api_call():
    # This will retry up to 3 times with exponential backoff
    # Delays: 1s, 2s, 4s
    response = external_api.get_data()
    return response

# Custom exception handling
@retry_decorator(
    max_retries=5,
    backoff_factor=1.5,
    exceptions=(ConnectionError, TimeoutError),
    on_retry=lambda exc, count: logger.warning(f"Retry {count}: {exc}")
)
def critical_operation():
    pass
```

### Performance Timing

```python
from backend.utils.helpers import Timer

with Timer() as t:
    # Code to time
    process_large_dataset()

print(f"Execution time: {t.elapsed:.2f}s")
```

---

## 5. Integration Examples

### FastAPI Endpoint with Full Integration

```python
from fastapi import FastAPI, HTTPException, Query
from backend.schemas import BookCreate, BookUpdate, BookResponse, PaginatedResponse, ErrorResponse
from backend.utils import (
    BookNotFoundError,
    DatabaseError,
    get_logger,
    handle_exception,
    get_status_code,
    calculate_metadata_completeness
)

app = FastAPI()
logger = get_logger(__name__)

@app.post("/books", response_model=BookResponse)
async def create_book(book_data: BookCreate):
    """Create a new book"""
    try:
        logger.info(f"Creating book: {book_data.title}")

        # Calculate metadata completeness
        completeness = calculate_metadata_completeness(book_data.dict())

        # Create book in database
        book = Book(**book_data.dict(), metadata_completeness_percent=completeness)
        db.add(book)
        db.commit()

        logger.info(f"Created book ID {book.id}")
        return BookResponse.from_orm(book)

    except Exception as e:
        logger.error(f"Failed to create book: {e}")
        error_dict = handle_exception(e)
        raise HTTPException(
            status_code=get_status_code(e),
            detail=error_dict
        )


@app.get("/books/{book_id}", response_model=BookResponse, responses={404: {"model": ErrorResponse}})
async def get_book(book_id: int):
    """Get book by ID"""
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise BookNotFoundError(book_id=book_id)

        return BookResponse.from_orm(book)

    except Exception as e:
        error_dict = handle_exception(e)
        raise HTTPException(
            status_code=get_status_code(e),
            detail=error_dict
        )


@app.get("/books", response_model=PaginatedResponse[BookResponse])
async def list_books(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """List books with pagination"""
    try:
        offset = (page - 1) * page_size

        books = db.query(Book).offset(offset).limit(page_size).all()
        total = db.query(Book).count()

        total_pages = (total + page_size - 1) // page_size

        return PaginatedResponse(
            items=[BookResponse.from_orm(book) for book in books],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )

    except Exception as e:
        error_dict = handle_exception(e)
        raise HTTPException(
            status_code=get_status_code(e),
            detail=error_dict
        )
```

### Service Layer Example

```python
from backend.schemas import BookCreate, BookUpdate
from backend.utils import (
    BookNotFoundError,
    DatabaseError,
    get_logger,
    calculate_metadata_completeness,
    retry_decorator
)

logger = get_logger(__name__)

class BookService:
    def __init__(self, db_session):
        self.db = db_session

    @retry_decorator(max_retries=3, exceptions=(DatabaseError,))
    def create_book(self, book_data: BookCreate) -> Book:
        """Create a new book with metadata completeness calculation"""
        try:
            # Calculate completeness
            completeness = calculate_metadata_completeness(book_data.dict())

            # Create book
            book = Book(
                **book_data.dict(),
                metadata_completeness_percent=completeness
            )

            self.db.add(book)
            self.db.commit()
            self.db.refresh(book)

            logger.info(f"Created book ID {book.id}: {book.title}")
            return book

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create book: {e}")
            raise DatabaseError(
                message=f"Failed to create book: {str(e)}",
                operation="INSERT",
                table="books"
            )

    def get_book(self, book_id: int) -> Book:
        """Get book by ID"""
        book = self.db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise BookNotFoundError(book_id=book_id)
        return book

    def update_book(self, book_id: int, update_data: BookUpdate) -> Book:
        """Update existing book"""
        book = self.get_book(book_id)

        # Update fields
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(book, field, value)

        # Recalculate completeness if metadata changed
        if any(field in update_dict for field in ["title", "author", "series", "isbn", "asin"]):
            book.metadata_completeness_percent = calculate_metadata_completeness(
                book.__dict__
            )

        try:
            self.db.commit()
            self.db.refresh(book)
            logger.info(f"Updated book ID {book_id}")
            return book

        except Exception as e:
            self.db.rollback()
            raise DatabaseError(
                message=f"Failed to update book: {str(e)}",
                operation="UPDATE",
                table="books"
            )
```

---

## Testing Examples

### Unit Test with Schemas

```python
import pytest
from backend.schemas import BookCreate, BookResponse
from backend.utils import calculate_metadata_completeness

def test_book_create_validation():
    """Test book creation validation"""
    book = BookCreate(
        title="The Hobbit",
        author="J.R.R. Tolkien",
        series="Middle Earth",
        series_number="1"
    )

    assert book.title == "The Hobbit"
    assert book.author == "J.R.R. Tolkien"
    assert book.status == "active"  # Default value


def test_book_metadata_completeness():
    """Test metadata completeness calculation"""
    book_dict = {
        "title": "The Hobbit",
        "author": "J.R.R. Tolkien",
        "series": "Middle Earth",
        "isbn": "9780547928227"
    }

    completeness = calculate_metadata_completeness(book_dict)
    assert 0 <= completeness <= 100
    assert completeness > 50  # Should be above 50% with these fields
```

### Error Handling Test

```python
import pytest
from backend.utils import BookNotFoundError, handle_exception, get_status_code

def test_book_not_found_error():
    """Test BookNotFoundError exception"""
    with pytest.raises(BookNotFoundError) as exc_info:
        raise BookNotFoundError(book_id=999)

    error = exc_info.value
    assert error.status_code == 404
    assert "999" in error.message
    assert error.details["book_id"] == 999


def test_exception_handler():
    """Test exception handler utility"""
    error = BookNotFoundError(book_id=123)
    error_dict = handle_exception(error)

    assert error_dict["error"] == "BookNotFoundError"
    assert error_dict["status_code"] == 404
    assert "timestamp" in error_dict
```

---

## Best Practices

### 1. Use Schemas for API Validation

```python
# Good
@app.post("/books")
async def create_book(book: BookCreate):
    # Automatic validation, type checking, and OpenAPI docs
    pass

# Bad
@app.post("/books")
async def create_book(book: dict):
    # No validation, no type safety, no docs
    pass
```

### 2. Use Custom Exceptions for Error Handling

```python
# Good
if not book:
    raise BookNotFoundError(book_id=book_id)

# Bad
if not book:
    raise Exception("Book not found")  # Generic, no status code, no logging
```

### 3. Use Logger Instead of Print

```python
# Good
logger = get_logger(__name__)
logger.info(f"Processing book ID {book_id}")

# Bad
print(f"Processing book ID {book_id}")  # No log file, no timestamps, no levels
```

### 4. Calculate Metadata Completeness

```python
# Good
completeness = calculate_metadata_completeness(book_dict)
book.metadata_completeness_percent = completeness

# Bad
book.metadata_completeness_percent = 50  # Hardcoded, inaccurate
```

### 5. Use Retry Decorator for Unreliable Operations

```python
# Good
@retry_decorator(max_retries=3, backoff_factor=2.0)
def fetch_from_external_api():
    pass

# Bad
def fetch_from_external_api():
    # No retry, fails on first error
    pass
```

---

## File Structure

```
backend/
├── schemas.py                      # Pydantic request/response models
├── utils/
│   ├── __init__.py                 # Package exports
│   ├── errors.py                   # Custom exceptions
│   ├── logging.py                  # Logging configuration
│   └── helpers.py                  # Utility functions
├── test_utils_schemas.py           # Verification script
└── SCHEMAS_UTILS_GUIDE.md         # This guide

logs/
├── audiobook_system.log            # Main application log
├── error.log                       # Error-only log
├── access.log                      # HTTP request/response log
└── scheduler.log                   # Scheduled task execution log
```

---

## Quick Reference

### Import Cheat Sheet

```python
# Schemas
from backend.schemas import (
    BookCreate, BookUpdate, BookResponse,
    SeriesCreate, SeriesResponse,
    AuthorCreate, AuthorResponse,
    DownloadCreate, DownloadResponse,
    ErrorResponse, PaginatedResponse
)

# Errors
from backend.utils import (
    BookNotFoundError,
    SeriesNotFoundError,
    MetadataError,
    DatabaseError,
    handle_exception,
    get_status_code
)

# Logging
from backend.utils import (
    setup_logging,
    get_logger,
    log_request
)

# Helpers
from backend.utils import (
    format_duration,
    calculate_metadata_completeness,
    sanitize_filename,
    retry_decorator,
    Timer
)
```

---

## Support

For questions or issues:

1. Check this guide first
2. Review inline documentation (docstrings)
3. Run verification script: `python backend/test_utils_schemas.py`
4. Check logs in `C:\Users\dogma\Projects\MAMcrawler\logs\`

---

**Last Updated:** 2025-11-16
**Version:** 1.0.0
