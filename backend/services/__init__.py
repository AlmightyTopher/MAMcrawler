"""
Service Layer Package

Business logic services for database operations (CRUD) on all models.
Provides clean separation between routes/API and database models.

Usage:
    from backend.services import BookService, SeriesService, AuthorService

    # Book operations
    result = BookService.create_book(db, title="My Book", author="Author Name")
    if result["success"]:
        book = result["data"]
        print(f"Created book: {book.title}")

    # Series operations
    result = SeriesService.get_series_by_name(db, "Harry Potter")
    series = result["data"]

    # Author operations
    result = AuthorService.get_favorite_authors(db)
    authors = result["data"]

    # Download operations
    result = DownloadService.create_download(
        db, book_id=1, source="MAM", title="Book Title", magnet_link="magnet:..."
    )

    # Metadata tracking
    result = MetadataService.create_correction(
        db, book_id=1, field_name="title", old_value="Old", new_value="New", source="GoogleBooks"
    )

    # Task execution tracking
    result = TaskService.create_task(db, task_name="MAM", scheduled_time=datetime.now())
    task_id = result["task_id"]
    TaskService.mark_started(db, task_id)
    # ... perform task ...
    TaskService.mark_completed(db, task_id, items_processed=10, items_succeeded=8, items_failed=2)

    # Permanent failure tracking
    result = FailedAttemptService.record_failure(
        db, task_name="MAM", item_id=1, item_name="Book Name", reason="Connection timeout"
    )

All service methods return Dict with:
    - success: bool - Whether operation succeeded
    - data: Any - Result data (model instance, list, etc.)
    - error: Optional[str] - Error message if failed
    - Additional context-specific fields
"""

from backend.services.book_service import BookService
from backend.services.series_service import SeriesService
from backend.services.author_service import AuthorService
from backend.services.download_service import DownloadService
from backend.services.metadata_service import MetadataService
from backend.services.task_service import TaskService
from backend.services.failed_attempt_service import FailedAttemptService

__all__ = [
    "BookService",
    "SeriesService",
    "AuthorService",
    "DownloadService",
    "MetadataService",
    "TaskService",
    "FailedAttemptService",
]
