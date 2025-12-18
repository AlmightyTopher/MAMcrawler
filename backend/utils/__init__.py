"""
Backend utilities package

Exports all error classes, logging functions, and helper utilities
for use throughout the audiobook management system.

Usage:
    from backend.utils import BookNotFoundError, get_logger, format_duration
    from backend.utils.errors import AudiobookException
    from backend.utils.log_config import setup_logging
    from backend.utils.helpers import calculate_metadata_completeness
"""

# ============================================================================
# ERROR CLASSES
# ============================================================================

from backend.utils.errors import (
    # Base exception
    AudiobookException,

    # Resource not found errors (404)
    BookNotFoundError,
    SeriesNotFoundError,
    AuthorNotFoundError,
    DownloadNotFoundError,

    # Validation errors (400)
    MetadataError,
    InvalidCredentialsError,

    # Scheduler errors (500)
    SchedulerError,

    # External API errors (502/503)
    ExternalAPIError,

    # Database errors (500)
    DatabaseError,

    # Download errors
    DownloadError,
    QBittorrentError,
    AudiobookshelfError,
    ProwlarrError,

    # Conflict errors (409)
    DuplicateResourceError,

    # Rate limit errors (429)
    RateLimitError,

    # File system errors (500)
    FileSystemError,

    # Helper functions
    handle_exception,
    get_status_code,
)


# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================

from backend.utils.log_config import (
    # Setup functions
    setup_logging,
    get_logger,
    setup_scheduler_logging,
    setup_access_logging,

    # Utility functions
    log_request,
    cleanup_old_logs,
    get_log_file_info,

    # Context managers
    LogContext,

    # Constants
    LOG_DIR,
    MAIN_LOG_FILE,
    ERROR_LOG_FILE,
    ACCESS_LOG_FILE,
    SCHEDULER_LOG_FILE,
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

from backend.utils.helpers import (
    # Time & duration formatting
    format_duration,
    parse_duration,
    get_timestamp_iso,
    format_timestamp,
    parse_timestamp,
    time_ago,

    # Metadata completeness
    calculate_metadata_completeness,
    get_missing_metadata_fields,

    # Magnet link & torrent parsing
    parse_magnet_link,
    validate_magnet_link,

    # File system operations
    sanitize_filename,
    get_file_size_mb,
    ensure_directory_exists,

    # List & collection utilities
    chunk_list,
    deduplicate_list,
    safe_get,

    # String utilities
    truncate_string,
    normalize_whitespace,
    extract_numbers,

    # Hash & checksum
    calculate_file_hash,
    calculate_string_hash,

    # Retry decorator
    retry_decorator,

    # Validation
    validate_isbn,
    validate_asin,
    validate_year,

    # Performance timing
    Timer,
)


# ============================================================================
# PACKAGE METADATA
# ============================================================================

__version__ = "1.0.0"
__author__ = "Audiobook Management System"
__all__ = [
    # Error classes
    "AudiobookException",
    "BookNotFoundError",
    "SeriesNotFoundError",
    "AuthorNotFoundError",
    "DownloadNotFoundError",
    "MetadataError",
    "InvalidCredentialsError",
    "SchedulerError",
    "ExternalAPIError",
    "DatabaseError",
    "DownloadError",
    "QBittorrentError",
    "AudiobookshelfError",
    "ProwlarrError",
    "DuplicateResourceError",
    "RateLimitError",
    "FileSystemError",
    "handle_exception",
    "get_status_code",

    # Logging
    "setup_logging",
    "get_logger",
    "setup_scheduler_logging",
    "setup_access_logging",
    "log_request",
    "cleanup_old_logs",
    "get_log_file_info",
    "LogContext",
    "LOG_DIR",
    "MAIN_LOG_FILE",
    "ERROR_LOG_FILE",
    "ACCESS_LOG_FILE",
    "SCHEDULER_LOG_FILE",

    # Helpers
    "format_duration",
    "parse_duration",
    "get_timestamp_iso",
    "format_timestamp",
    "parse_timestamp",
    "time_ago",
    "calculate_metadata_completeness",
    "get_missing_metadata_fields",
    "parse_magnet_link",
    "validate_magnet_link",
    "sanitize_filename",
    "get_file_size_mb",
    "ensure_directory_exists",
    "chunk_list",
    "deduplicate_list",
    "safe_get",
    "truncate_string",
    "normalize_whitespace",
    "extract_numbers",
    "calculate_file_hash",
    "calculate_string_hash",
    "retry_decorator",
    "validate_isbn",
    "validate_asin",
    "validate_year",
    "Timer",
]


# ============================================================================
# INITIALIZATION
# ============================================================================

# Log package initialization
logger = get_logger(__name__)
logger.debug(f"Backend utilities package initialized (v{__version__})")
