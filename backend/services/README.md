# Service Layer - Business Logic Services

The service layer provides a clean separation between the API routes and database models. All database operations should go through these services.

## Overview

All services return a standardized dictionary format:

```python
{
    "success": bool,           # Whether operation succeeded
    "data": Any,               # Result data (model instance, list, etc.)
    "error": Optional[str],    # Error message if failed
    # Additional context-specific fields
}
```

## Services

### BookService

Handles all book-related operations including metadata tracking.

**Key Methods:**

```python
from backend.services import BookService

# Create book
result = BookService.create_book(
    db,
    title="The Hobbit",
    author="J.R.R. Tolkien",
    abs_id="abs_12345",
    metadata_dict={
        "series": "Middle Earth",
        "series_number": "1",
        "isbn": "978-0547928227",
        "publisher": "Houghton Mifflin",
        "published_year": 1937,
        "duration_minutes": 683,
        "description": "A fantasy adventure...",
        "import_source": "user_import"
    }
)

# Get book
result = BookService.get_book(db, book_id=1)
book = result["data"]

# Search books
result = BookService.search_books(db, query="Tolkien", limit=10)
books = result["data"]

# Update book
result = BookService.update_book(db, book_id=1, updates_dict={
    "title": "The Hobbit: Extended Edition",
    "duration_minutes": 720
})
changes = result["changes_made"]

# Track metadata source
result = BookService.update_metadata_source(
    db, book_id=1, field_name="title", source="GoogleBooks"
)

# Get books needing refresh
result = BookService.get_books_needing_metadata_refresh(db, days=30)
stale_books = result["data"]

# Get books by series
result = BookService.get_books_by_series(db, series_name="Harry Potter")
series_books = result["data"]

# Delete book (soft delete)
result = BookService.delete_book(db, book_id=1)
```

**Features:**
- Automatic metadata completeness calculation (0-100%)
- Metadata source tracking (which API provided each field)
- Pagination support
- Search by title/author
- Soft delete (marks as archived)

---

### SeriesService

Manages series tracking and completion status.

**Key Methods:**

```python
from backend.services import SeriesService

# Create series
result = SeriesService.create_series(
    db,
    name="Harry Potter",
    author="J.K. Rowling",
    goodreads_id="45175",
    total_books=7
)

# Get series
result = SeriesService.get_series(db, series_id=1)
series = result["data"]

# Get by name
result = SeriesService.get_series_by_name(db, name="Harry Potter")
series = result["data"]

# Update completion status (recalculates books owned/missing)
result = SeriesService.update_completion_status(db, series_id=1)
stats = result["stats"]
# stats = {
#     "books_owned": 5,
#     "books_missing": 2,
#     "total_books": 7,
#     "completion_percentage": 71,
#     "completion_status": "partial"
# }

# Get completion summary
result = SeriesService.get_series_completion_summary(db)
stats = result["stats"]
# stats = {
#     "total_series": 150,
#     "complete": 45,
#     "partial": 80,
#     "incomplete": 25,
#     "average_completion_percentage": 67.5,
#     "total_books_owned": 543,
#     "total_books_missing": 210
# }
```

**Features:**
- Automatic completion percentage calculation
- Counts books owned vs. missing
- Status tracking (complete, partial, incomplete)
- Summary statistics

---

### AuthorService

Tracks authors and audiobook collection completeness.

**Key Methods:**

```python
from backend.services import AuthorService

# Create author
result = AuthorService.create_author(
    db,
    name="Brandon Sanderson",
    goodreads_id="38550",
    google_books_id="123456"
)

# Get favorite authors (2+ books)
result = AuthorService.get_favorite_authors(db)
favorite_authors = result["data"]

# Update completion status
result = AuthorService.update_completion_status(db, author_id=1)
stats = result["stats"]

# Get author's books
result = AuthorService.get_author_books(db, author_id=1)
books = result["data"]

# Get completion summary
result = AuthorService.get_author_completion_summary(db)
stats = result["stats"]
```

**Features:**
- Tracks audiobooks owned vs. missing
- Identifies "favorite" authors (2+ books)
- External platform ID tracking (Goodreads, Google Books, MAM)
- Completion status calculation

---

### DownloadService

Manages download queue, retry logic, and qBittorrent integration.

**Key Methods:**

```python
from backend.services import DownloadService

# Create download
result = DownloadService.create_download(
    db,
    book_id=1,
    source="MAM",
    title="The Hobbit",
    author="J.R.R. Tolkien",
    magnet_link="magnet:?xt=urn:btih:..."
)

# Get all pending downloads
result = DownloadService.get_all_pending(db)
pending = result["data"]

# Update status
result = DownloadService.update_status(
    db, download_id=1, status="downloading", qb_hash="abc123"
)

# Mark completed
result = DownloadService.mark_completed(db, download_id=1, abs_import_status="imported")

# Mark failed (with retry logic)
result = DownloadService.mark_failed(db, download_id=1, error_msg="Connection timeout", retry_attempt=1)

# Schedule retry
result = DownloadService.schedule_retry(db, download_id=1, days_until_retry=1)

# Get failed downloads
result = DownloadService.get_failed_downloads(db)
failed = result["data"]

# Get downloads ready for retry
result = DownloadService.get_retry_due(db)
retry_ready = result["data"]
```

**Features:**
- Automatic retry logic (max 3 attempts by default)
- qBittorrent hash tracking
- Audiobookshelf import status tracking
- Scheduled retries with exponential backoff

---

### MetadataService

Tracks all metadata corrections and quality metrics.

**Key Methods:**

```python
from backend.services import MetadataService

# Create correction record
result = MetadataService.create_correction(
    db,
    book_id=1,
    field_name="title",
    old_value="The Hobit",
    new_value="The Hobbit",
    source="GoogleBooks",
    reason="Fixed spelling error"
)

# Get correction history
result = MetadataService.get_correction_history(db, book_id=1, limit=50)
corrections = result["data"]

# Get corrections by source
result = MetadataService.get_corrections_by_source(db, source="GoogleBooks", limit=100)
corrections = result["data"]

# Get metadata status summary
result = MetadataService.get_metadata_status(db)
stats = result["stats"]
# stats = {
#     "average_completeness_percent": 85.5,
#     "total_books": 1234,
#     "completeness_breakdown": {
#         "complete_100": 456,
#         "high_quality_80_99": 567,
#         "medium_quality_50_79": 189,
#         "low_quality_0_49": 22
#     },
#     "sources_used": {"GoogleBooks": 543, "Goodreads": 321, "Manual": 45},
#     "total_corrections": 909,
#     "recent_corrections_7_days": 23
# }

# Get incomplete books
result = MetadataService.get_incomplete_books(db, max_completeness=80, limit=100)
incomplete = result["data"]

# Cleanup old corrections (1-month retention)
result = MetadataService.cleanup_old_corrections(db, days=30)
deleted_count = result["deleted_count"]
```

**Features:**
- Full audit trail of metadata changes
- Source attribution tracking
- Quality metrics dashboard
- 1-month retention policy (automatic cleanup)

---

### TaskService

Tracks execution history of all scheduled jobs.

**Key Methods:**

```python
from backend.services import TaskService

# Create task
result = TaskService.create_task(
    db,
    task_name="MAM",
    scheduled_time=datetime.now(),
    metadata={"target": "audiobooks"}
)
task_id = result["task_id"]

# Mark started
result = TaskService.mark_started(db, task_id)

# Add log output
result = TaskService.add_log_output(db, task_id, "Processing book 1 of 100...")

# Mark completed
result = TaskService.mark_completed(
    db, task_id,
    items_processed=100,
    items_succeeded=95,
    items_failed=5
)
stats = result["stats"]

# Mark failed
result = TaskService.mark_failed(db, task_id, error_msg="Database connection lost")

# Get task history
result = TaskService.get_task_history(db, task_name="MAM", limit=50)
history = result["data"]

# Get recent tasks
result = TaskService.get_recent_tasks(db, hours=24)
recent = result["data"]

# Get task statistics
result = TaskService.get_task_statistics(db)
stats = result["stats"]

# Cleanup old tasks (1-month retention)
result = TaskService.cleanup_old_tasks(db, days=30)
deleted_count = result["deleted_count"]
```

**Features:**
- Full execution tracking (scheduled, running, completed, failed)
- Duration calculation
- Success/failure statistics
- Log output capture
- 1-month retention policy

---

### FailedAttemptService

Permanent audit trail of all failures (NEVER DELETED).

**Key Methods:**

```python
from backend.services import FailedAttemptService

# Record failure (permanent)
result = FailedAttemptService.record_failure(
    db,
    task_name="MAM",
    item_id=1,
    item_name="The Hobbit",
    reason="Connection timeout after 30s",
    error_code="TIMEOUT_ERROR",
    error_details="Full traceback...",
    metadata={"attempt": 1, "target_url": "https://..."}
)

# Get failure history for item
result = FailedAttemptService.get_failure_history(db, item_id=1)
failures = result["data"]

# Get failures by task
result = FailedAttemptService.get_failures_by_task(db, task_name="MAM", limit=100)
failures = result["data"]

# Get failure summary
result = FailedAttemptService.get_failure_summary(db)
stats = result["stats"]
# stats = {
#     "total_failures": 543,
#     "failures_by_task": {"MAM": 234, "METADATA_FULL": 123, ...},
#     "failures_by_error_code": {"TIMEOUT_ERROR": 45, "AUTH_FAILED": 23, ...},
#     "total_retry_attempts": 1234,
#     "recent_failures_7_days": 12,
#     "most_problematic_items": [...]
# }

# Get persistent failures (3+ attempts)
result = FailedAttemptService.get_persistent_failures(db, min_attempts=3, limit=100)
problematic = result["data"]

# Get failures by error code
result = FailedAttemptService.get_failures_by_error_code(db, error_code="TIMEOUT_ERROR")
timeout_failures = result["data"]
```

**Features:**
- **PERMANENT RETENTION** - records are never deleted
- Automatic deduplication (updates existing failure records)
- Attempt count tracking
- Error code categorization
- Pattern detection for systemic issues

---

## Error Handling

All service methods return a standardized response. Always check the `success` field:

```python
result = BookService.create_book(db, title="Test Book")

if result["success"]:
    book = result["data"]
    print(f"Book created: {book.id}")
else:
    error = result["error"]
    print(f"Error: {error}")
```

## Database Session Management

Services accept a database session as the first parameter. Use the session factory from `backend.database`:

```python
from backend.database import get_db_context
from backend.services import BookService

# Using context manager
with get_db_context() as db:
    result = BookService.create_book(db, title="Test Book")
    book = result["data"]

# Using FastAPI dependency
from fastapi import Depends
from backend.database import get_db

@app.get("/books/{book_id}")
def get_book(book_id: int, db: Session = Depends(get_db)):
    result = BookService.get_book(db, book_id)
    return result
```

## Transaction Safety

Services handle commits and rollbacks internally:

```python
# This is safe - rollback happens automatically on error
result = BookService.create_book(db, title="Test Book")

if not result["success"]:
    # Database has already been rolled back
    print(f"Error: {result['error']}")
```

## Logging

All services use Python's built-in logging. Configure logging in your application:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

Service logs will appear with module names like:
- `backend.services.book_service`
- `backend.services.series_service`
- etc.

## Testing

Example test using services:

```python
import pytest
from backend.database import SessionLocal, init_db
from backend.services import BookService

@pytest.fixture
def db():
    init_db()
    db = SessionLocal()
    yield db
    db.close()

def test_create_book(db):
    result = BookService.create_book(
        db,
        title="Test Book",
        author="Test Author"
    )

    assert result["success"] is True
    assert result["data"].title == "Test Book"
    assert result["book_id"] is not None
```

## Best Practices

1. **Always check `success` field** before accessing `data`
2. **Use type hints** when calling service methods
3. **Pass database session** as first parameter
4. **Handle errors gracefully** - services return error messages, not exceptions
5. **Use metadata tracking** - track which source provided each field
6. **Monitor completion status** - regularly update series/author completion
7. **Clean up old data** - use cleanup methods for retention policies
8. **Never delete FailedAttempt records** - they're permanent audit trail

## Integration Example

Complete workflow using multiple services:

```python
from backend.database import get_db_context
from backend.services import (
    BookService, SeriesService, DownloadService,
    MetadataService, TaskService, FailedAttemptService
)
from datetime import datetime

# Create task
with get_db_context() as db:
    task_result = TaskService.create_task(db, task_name="MAM", scheduled_time=datetime.now())
    task_id = task_result["task_id"]

    TaskService.mark_started(db, task_id)

    try:
        # Create book
        book_result = BookService.create_book(
            db, title="The Hobbit", author="J.R.R. Tolkien",
            metadata_dict={"series": "Middle Earth", "series_number": "1"}
        )

        if book_result["success"]:
            book_id = book_result["book_id"]

            # Track metadata source
            MetadataService.create_correction(
                db, book_id=book_id, field_name="title",
                old_value=None, new_value="The Hobbit",
                source="GoogleBooks"
            )

            # Update series completion
            series_result = SeriesService.get_series_by_name(db, name="Middle Earth")
            if series_result["success"]:
                SeriesService.update_completion_status(db, series_result["data"].id)

            # Queue download
            download_result = DownloadService.create_download(
                db, book_id=book_id, source="MAM",
                title="The Hobbit", magnet_link="magnet:?xt=..."
            )

            # Mark task completed
            TaskService.mark_completed(db, task_id, items_processed=1, items_succeeded=1)
        else:
            # Record failure
            FailedAttemptService.record_failure(
                db, task_name="MAM", item_id=None,
                item_name="The Hobbit", reason=book_result["error"]
            )
            TaskService.mark_failed(db, task_id, error_msg=book_result["error"])

    except Exception as e:
        TaskService.mark_failed(db, task_id, error_msg=str(e))
        raise
```
