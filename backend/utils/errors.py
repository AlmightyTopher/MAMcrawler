"""
Custom exception classes for audiobook management system
Provides specific error types with HTTP status codes and logging integration
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime


logger = logging.getLogger(__name__)


# ============================================================================
# BASE EXCEPTION
# ============================================================================

class AudiobookException(Exception):
    """
    Base exception for all audiobook system errors

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code for API responses
        details: Additional error context
        log_level: Logging level for this error
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        log_level: int = logging.ERROR
    ):
        """
        Initialize audiobook exception

        Args:
            message: Human-readable error message
            status_code: HTTP status code (default: 500)
            details: Additional error context as dictionary
            log_level: Logging level (default: ERROR)
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.log_level = log_level
        self.timestamp = datetime.utcnow()

        # Log the error
        logger.log(
            log_level,
            f"{self.__class__.__name__}: {message}",
            extra={
                "error_type": self.__class__.__name__,
                "status_code": status_code,
                "details": self.details,
                "timestamp": self.timestamp.isoformat()
            }
        )

        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for API responses

        Returns:
            Dictionary with error details
        """
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "status_code": self.status_code
        }


# ============================================================================
# RESOURCE NOT FOUND ERRORS (404)
# ============================================================================

class BookNotFoundError(AudiobookException):
    """Raised when a book is not found in the database"""

    def __init__(self, book_id: Optional[int] = None, abs_id: Optional[str] = None, message: Optional[str] = None):
        """
        Initialize book not found error

        Args:
            book_id: Database ID of the book
            abs_id: Audiobookshelf ID of the book
            message: Custom error message (optional)
        """
        if message is None:
            if book_id is not None:
                message = f"Book with ID {book_id} not found"
            elif abs_id is not None:
                message = f"Book with Audiobookshelf ID '{abs_id}' not found"
            else:
                message = "Book not found"

        details = {}
        if book_id is not None:
            details["book_id"] = book_id
        if abs_id is not None:
            details["abs_id"] = abs_id

        super().__init__(
            message=message,
            status_code=404,
            details=details,
            log_level=logging.WARNING
        )


class SeriesNotFoundError(AudiobookException):
    """Raised when a series is not found in the database"""

    def __init__(self, series_id: Optional[int] = None, series_name: Optional[str] = None, message: Optional[str] = None):
        """
        Initialize series not found error

        Args:
            series_id: Database ID of the series
            series_name: Name of the series
            message: Custom error message (optional)
        """
        if message is None:
            if series_id is not None:
                message = f"Series with ID {series_id} not found"
            elif series_name is not None:
                message = f"Series '{series_name}' not found"
            else:
                message = "Series not found"

        details = {}
        if series_id is not None:
            details["series_id"] = series_id
        if series_name is not None:
            details["series_name"] = series_name

        super().__init__(
            message=message,
            status_code=404,
            details=details,
            log_level=logging.WARNING
        )


class AuthorNotFoundError(AudiobookException):
    """Raised when an author is not found in the database"""

    def __init__(self, author_id: Optional[int] = None, author_name: Optional[str] = None, message: Optional[str] = None):
        """
        Initialize author not found error

        Args:
            author_id: Database ID of the author
            author_name: Name of the author
            message: Custom error message (optional)
        """
        if message is None:
            if author_id is not None:
                message = f"Author with ID {author_id} not found"
            elif author_name is not None:
                message = f"Author '{author_name}' not found"
            else:
                message = "Author not found"

        details = {}
        if author_id is not None:
            details["author_id"] = author_id
        if author_name is not None:
            details["author_name"] = author_name

        super().__init__(
            message=message,
            status_code=404,
            details=details,
            log_level=logging.WARNING
        )


class DownloadNotFoundError(AudiobookException):
    """Raised when a download is not found in the database"""

    def __init__(self, download_id: Optional[int] = None, qbittorrent_hash: Optional[str] = None, message: Optional[str] = None):
        """
        Initialize download not found error

        Args:
            download_id: Database ID of the download
            qbittorrent_hash: qBittorrent info hash
            message: Custom error message (optional)
        """
        if message is None:
            if download_id is not None:
                message = f"Download with ID {download_id} not found"
            elif qbittorrent_hash is not None:
                message = f"Download with hash '{qbittorrent_hash}' not found"
            else:
                message = "Download not found"

        details = {}
        if download_id is not None:
            details["download_id"] = download_id
        if qbittorrent_hash is not None:
            details["qbittorrent_hash"] = qbittorrent_hash

        super().__init__(
            message=message,
            status_code=404,
            details=details,
            log_level=logging.WARNING
        )


# ============================================================================
# VALIDATION ERRORS (400)
# ============================================================================

class MetadataError(AudiobookException):
    """Raised when there is an issue with metadata processing or validation"""

    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        """
        Initialize metadata error

        Args:
            message: Error message
            field: Field name that caused the error
            value: Invalid value
        """
        details = {}
        if field is not None:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)

        super().__init__(
            message=message,
            status_code=400,
            details=details,
            log_level=logging.WARNING
        )


class InvalidCredentialsError(AudiobookException):
    """Raised when authentication credentials are invalid"""

    def __init__(self, service: str, message: Optional[str] = None):
        """
        Initialize invalid credentials error

        Args:
            service: Service name (e.g., "Audiobookshelf", "qBittorrent")
            message: Custom error message (optional)
        """
        if message is None:
            message = f"Invalid credentials for {service}"

        super().__init__(
            message=message,
            status_code=401,
            details={"service": service},
            log_level=logging.ERROR
        )


# ============================================================================
# SCHEDULER ERRORS (500)
# ============================================================================

class SchedulerError(AudiobookException):
    """Raised when there is an issue with the task scheduler"""

    def __init__(self, message: str, task_name: Optional[str] = None, error_details: Optional[str] = None):
        """
        Initialize scheduler error

        Args:
            message: Error message
            task_name: Name of the task that failed
            error_details: Detailed error information
        """
        details = {}
        if task_name is not None:
            details["task_name"] = task_name
        if error_details is not None:
            details["error_details"] = error_details

        super().__init__(
            message=message,
            status_code=500,
            details=details,
            log_level=logging.ERROR
        )


# ============================================================================
# EXTERNAL API ERRORS (502/503)
# ============================================================================

class ExternalAPIError(AudiobookException):
    """Raised when an external API call fails"""

    def __init__(
        self,
        service: str,
        message: str,
        status_code: Optional[int] = None,
        response_text: Optional[str] = None
    ):
        """
        Initialize external API error

        Args:
            service: External service name (e.g., "GoogleBooks", "Goodreads")
            message: Error message
            status_code: HTTP status code from external API
            response_text: Response text from external API
        """
        details = {"service": service}
        if status_code is not None:
            details["external_status_code"] = status_code
        if response_text is not None:
            details["response_text"] = response_text[:500]  # Limit to 500 chars

        # Use 502 Bad Gateway for external API failures
        super().__init__(
            message=f"{service} API error: {message}",
            status_code=502,
            details=details,
            log_level=logging.ERROR
        )


# ============================================================================
# DATABASE ERRORS (500)
# ============================================================================

class DatabaseError(AudiobookException):
    """Raised when there is a database operation failure"""

    def __init__(self, message: str, operation: Optional[str] = None, table: Optional[str] = None):
        """
        Initialize database error

        Args:
            message: Error message
            operation: Database operation (e.g., "INSERT", "UPDATE", "DELETE")
            table: Table name
        """
        details = {}
        if operation is not None:
            details["operation"] = operation
        if table is not None:
            details["table"] = table

        super().__init__(
            message=message,
            status_code=500,
            details=details,
            log_level=logging.ERROR
        )


# ============================================================================
# DOWNLOAD ERRORS (400/500)
# ============================================================================

class DownloadError(AudiobookException):
    """Raised when there is an issue with downloading"""

    def __init__(
        self,
        message: str,
        download_id: Optional[int] = None,
        source: Optional[str] = None,
        retry_count: Optional[int] = None
    ):
        """
        Initialize download error

        Args:
            message: Error message
            download_id: Download ID
            source: Download source
            retry_count: Current retry count
        """
        details = {}
        if download_id is not None:
            details["download_id"] = download_id
        if source is not None:
            details["source"] = source
        if retry_count is not None:
            details["retry_count"] = retry_count

        super().__init__(
            message=message,
            status_code=500,
            details=details,
            log_level=logging.ERROR
        )


class QBittorrentError(AudiobookException):
    """Raised when there is an issue with qBittorrent client"""

    def __init__(self, message: str, operation: Optional[str] = None, torrent_hash: Optional[str] = None):
        """
        Initialize qBittorrent error

        Args:
            message: Error message
            operation: Operation that failed (e.g., "add_torrent", "get_status")
            torrent_hash: Torrent info hash
        """
        details = {}
        if operation is not None:
            details["operation"] = operation
        if torrent_hash is not None:
            details["torrent_hash"] = torrent_hash

        super().__init__(
            message=f"qBittorrent error: {message}",
            status_code=502,
            details=details,
            log_level=logging.ERROR
        )


class AudiobookshelfError(AudiobookException):
    """Raised when there is an issue with Audiobookshelf client"""

    def __init__(self, message: str, operation: Optional[str] = None, library_id: Optional[str] = None):
        """
        Initialize Audiobookshelf error

        Args:
            message: Error message
            operation: Operation that failed (e.g., "scan_library", "get_book")
            library_id: Library ID
        """
        details = {}
        if operation is not None:
            details["operation"] = operation
        if library_id is not None:
            details["library_id"] = library_id

        super().__init__(
            message=f"Audiobookshelf error: {message}",
            status_code=502,
            details=details,
            log_level=logging.ERROR
        )


class ProwlarrError(AudiobookException):
    """Raised when there is an issue with Prowlarr client"""

    def __init__(self, message: str, operation: Optional[str] = None, query: Optional[str] = None):
        """
        Initialize Prowlarr error

        Args:
            message: Error message
            operation: Operation that failed (e.g., "search", "get_indexers")
            query: Search query
        """
        details = {}
        if operation is not None:
            details["operation"] = operation
        if query is not None:
            details["query"] = query

        super().__init__(
            message=f"Prowlarr error: {message}",
            status_code=502,
            details=details,
            log_level=logging.ERROR
        )


# ============================================================================
# CONFLICT ERRORS (409)
# ============================================================================

class DuplicateResourceError(AudiobookException):
    """Raised when attempting to create a duplicate resource"""

    def __init__(self, resource_type: str, identifier: str, message: Optional[str] = None):
        """
        Initialize duplicate resource error

        Args:
            resource_type: Type of resource (e.g., "Book", "Series", "Author")
            identifier: Identifying value that conflicts
            message: Custom error message (optional)
        """
        if message is None:
            message = f"{resource_type} with identifier '{identifier}' already exists"

        super().__init__(
            message=message,
            status_code=409,
            details={
                "resource_type": resource_type,
                "identifier": identifier
            },
            log_level=logging.WARNING
        )


# ============================================================================
# RATE LIMIT ERRORS (429)
# ============================================================================

class RateLimitError(AudiobookException):
    """Raised when rate limit is exceeded for external service"""

    def __init__(self, service: str, retry_after: Optional[int] = None, message: Optional[str] = None):
        """
        Initialize rate limit error

        Args:
            service: Service name
            retry_after: Seconds to wait before retrying
            message: Custom error message (optional)
        """
        if message is None:
            message = f"Rate limit exceeded for {service}"
            if retry_after is not None:
                message += f". Retry after {retry_after} seconds"

        details = {"service": service}
        if retry_after is not None:
            details["retry_after"] = retry_after

        super().__init__(
            message=message,
            status_code=429,
            details=details,
            log_level=logging.WARNING
        )


# ============================================================================
# FILE SYSTEM ERRORS (500)
# ============================================================================

class FileSystemError(AudiobookException):
    """Raised when there is a file system operation error"""

    def __init__(self, message: str, path: Optional[str] = None, operation: Optional[str] = None):
        """
        Initialize file system error

        Args:
            message: Error message
            path: File or directory path
            operation: File operation (e.g., "read", "write", "delete")
        """
        details = {}
        if path is not None:
            details["path"] = path
        if operation is not None:
            details["operation"] = operation

        super().__init__(
            message=message,
            status_code=500,
            details=details,
            log_level=logging.ERROR
        )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def handle_exception(exc: Exception) -> Dict[str, Any]:
    """
    Convert any exception to a standardized error dictionary

    Args:
        exc: Exception to handle

    Returns:
        Dictionary with error details suitable for API response
    """
    if isinstance(exc, AudiobookException):
        return exc.to_dict()
    else:
        # Log unexpected exceptions
        logger.exception(f"Unhandled exception: {exc}")

        return {
            "error": exc.__class__.__name__,
            "message": str(exc),
            "details": {},
            "timestamp": datetime.utcnow().isoformat(),
            "status_code": 500
        }


def get_status_code(exc: Exception) -> int:
    """
    Get HTTP status code from exception

    Args:
        exc: Exception object

    Returns:
        HTTP status code (default: 500)
    """
    if isinstance(exc, AudiobookException):
        return exc.status_code
    else:
        return 500
