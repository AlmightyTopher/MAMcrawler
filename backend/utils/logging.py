"""
Logging configuration for audiobook management system
Provides centralized logging setup with file rotation and structured output
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


# ============================================================================
# CONSTANTS
# ============================================================================

# Log directory (create if doesn't exist)
LOG_DIR = Path(r"C:\Users\dogma\Projects\MAMcrawler\logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Log file paths
MAIN_LOG_FILE = LOG_DIR / "audiobook_system.log"
ERROR_LOG_FILE = LOG_DIR / "error.log"
ACCESS_LOG_FILE = LOG_DIR / "access.log"
SCHEDULER_LOG_FILE = LOG_DIR / "scheduler.log"

# Log format strings
DETAILED_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)-30s | "
    "%(funcName)-20s | Line %(lineno)-4d | %(message)s"
)

SIMPLE_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"

JSON_FORMAT = (
    '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
    '"logger": "%(name)s", "function": "%(funcName)s", '
    '"line": %(lineno)d, "message": "%(message)s"}'
)

# Date format
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging(
    log_level_console: str = "INFO",
    log_level_file: str = "DEBUG",
    log_format: str = "detailed",
    enable_json_logs: bool = False,
    max_file_size_mb: int = 10,
    backup_count: int = 30
) -> None:
    """
    Configure logging for the entire application

    Sets up:
    - Console handler (INFO level by default)
    - File handler with rotation (DEBUG level by default)
    - Error-only file handler (ERROR level)
    - Structured/JSON logging (optional)

    Args:
        log_level_console: Console logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_level_file: File logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format style ("detailed", "simple", "json")
        enable_json_logs: Enable JSON-formatted logs to separate file
        max_file_size_mb: Maximum log file size in MB before rotation
        backup_count: Number of backup log files to keep (days for daily rotation)

    Example:
        >>> setup_logging(log_level_console="INFO", log_level_file="DEBUG")
        >>> logger = logging.getLogger(__name__)
        >>> logger.info("Application started")
    """

    # Convert string log levels to logging constants
    console_level = getattr(logging, log_level_console.upper(), logging.INFO)
    file_level = getattr(logging, log_level_file.upper(), logging.DEBUG)

    # Select format
    if log_format == "json":
        formatter = logging.Formatter(JSON_FORMAT, datefmt=DATE_FORMAT)
    elif log_format == "simple":
        formatter = logging.Formatter(SIMPLE_FORMAT, datefmt=DATE_FORMAT)
    else:  # detailed
        formatter = logging.Formatter(DETAILED_FORMAT, datefmt=DATE_FORMAT)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture everything, handlers will filter

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # ========================================================================
    # CONSOLE HANDLER
    # ========================================================================
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)

    # Add color support for console (if available)
    try:
        import colorlog
        color_formatter = colorlog.ColoredFormatter(
            "%(log_color)s" + SIMPLE_FORMAT,
            datefmt=DATE_FORMAT,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        console_handler.setFormatter(color_formatter)
    except ImportError:
        # colorlog not available, use standard formatter
        pass

    root_logger.addHandler(console_handler)

    # ========================================================================
    # MAIN FILE HANDLER (with daily rotation)
    # ========================================================================
    main_file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=MAIN_LOG_FILE,
        when="midnight",  # Rotate at midnight
        interval=1,  # Every 1 day
        backupCount=backup_count,  # Keep N days of logs
        encoding="utf-8"
    )
    main_file_handler.setLevel(file_level)
    main_file_handler.setFormatter(formatter)
    main_file_handler.suffix = "%Y-%m-%d"  # Append date to rotated files
    root_logger.addHandler(main_file_handler)

    # ========================================================================
    # ERROR FILE HANDLER (errors only, with daily rotation)
    # ========================================================================
    error_file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=ERROR_LOG_FILE,
        when="midnight",
        interval=1,
        backupCount=backup_count,
        encoding="utf-8"
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)
    error_file_handler.suffix = "%Y-%m-%d"
    root_logger.addHandler(error_file_handler)

    # ========================================================================
    # JSON FILE HANDLER (optional, for structured logs)
    # ========================================================================
    if enable_json_logs:
        json_log_file = LOG_DIR / "structured.log"
        json_formatter = logging.Formatter(JSON_FORMAT, datefmt=DATE_FORMAT)

        json_file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=json_log_file,
            when="midnight",
            interval=1,
            backupCount=backup_count,
            encoding="utf-8"
        )
        json_file_handler.setLevel(file_level)
        json_file_handler.setFormatter(json_formatter)
        json_file_handler.suffix = "%Y-%m-%d"
        root_logger.addHandler(json_file_handler)

    # ========================================================================
    # SUPPRESS NOISY THIRD-PARTY LOGGERS
    # ========================================================================
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("watchdog").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Log initialization
    root_logger.info("=" * 80)
    root_logger.info(f"Logging initialized - Console: {log_level_console}, File: {log_level_file}")
    root_logger.info(f"Log directory: {LOG_DIR}")
    root_logger.info(f"Main log: {MAIN_LOG_FILE}")
    root_logger.info(f"Error log: {ERROR_LOG_FILE}")
    root_logger.info("=" * 80)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Module started")
    """
    return logging.getLogger(name)


def setup_scheduler_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Setup dedicated logger for scheduler tasks

    Creates a separate log file for scheduler-specific events with
    daily rotation and 30-day retention.

    Args:
        log_level: Logging level for scheduler (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Logger instance for scheduler

    Example:
        >>> scheduler_logger = setup_scheduler_logging("DEBUG")
        >>> scheduler_logger.info("Task scheduled: METADATA_FULL at 02:00")
    """
    logger = logging.getLogger("scheduler")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.propagate = False  # Don't propagate to root logger

    # Remove existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(DETAILED_FORMAT, datefmt=DATE_FORMAT)

    # File handler with daily rotation
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=SCHEDULER_LOG_FILE,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y-%m-%d"
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(SIMPLE_FORMAT, datefmt=DATE_FORMAT))
    logger.addHandler(console_handler)

    logger.info("Scheduler logging initialized")
    return logger


def setup_access_logging() -> logging.Logger:
    """
    Setup dedicated logger for HTTP access logs

    Creates a separate log file for API request/response logging
    with daily rotation.

    Returns:
        Logger instance for access logs

    Example:
        >>> access_logger = setup_access_logging()
        >>> access_logger.info("GET /api/books/1 200 0.045s")
    """
    logger = logging.getLogger("access")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Remove existing handlers
    logger.handlers.clear()

    # Access log format (Apache-style)
    access_formatter = logging.Formatter(
        "%(asctime)s | %(message)s",
        datefmt=DATE_FORMAT
    )

    # File handler with daily rotation
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=ACCESS_LOG_FILE,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(access_formatter)
    file_handler.suffix = "%Y-%m-%d"
    logger.addHandler(file_handler)

    logger.info("Access logging initialized")
    return logger


def log_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user: Optional[str] = None
) -> None:
    """
    Log an HTTP request in access log

    Args:
        method: HTTP method (GET, POST, etc.)
        path: Request path
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        user: Username if authenticated (optional)

    Example:
        >>> log_request("GET", "/api/books/1", 200, 45.3, "admin")
    """
    access_logger = logging.getLogger("access")

    user_info = f" | User: {user}" if user else ""
    message = f"{method} {path} | Status: {status_code} | Duration: {duration_ms:.2f}ms{user_info}"

    access_logger.info(message)


def cleanup_old_logs(days_to_keep: int = 30) -> None:
    """
    Clean up log files older than specified days

    Args:
        days_to_keep: Number of days to keep logs (default: 30)

    Example:
        >>> cleanup_old_logs(days_to_keep=7)  # Keep only 7 days of logs
    """
    logger = get_logger(__name__)
    cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)

    deleted_count = 0
    for log_file in LOG_DIR.glob("*.log*"):
        # Skip current log files (without date suffix)
        if log_file.stem in ["audiobook_system", "error", "access", "scheduler", "structured"]:
            continue

        # Check file modification time
        if log_file.stat().st_mtime < cutoff_time:
            try:
                log_file.unlink()
                deleted_count += 1
                logger.debug(f"Deleted old log file: {log_file.name}")
            except Exception as e:
                logger.error(f"Failed to delete log file {log_file.name}: {e}")

    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} old log files (older than {days_to_keep} days)")


def get_log_file_info() -> dict:
    """
    Get information about current log files

    Returns:
        Dictionary with log file information

    Example:
        >>> info = get_log_file_info()
        >>> print(f"Main log size: {info['main_log']['size_mb']:.2f} MB")
    """
    def file_info(filepath: Path) -> dict:
        """Get file size and modification time"""
        if filepath.exists():
            stat = filepath.stat()
            return {
                "exists": True,
                "size_mb": stat.st_size / (1024 * 1024),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "path": str(filepath)
            }
        else:
            return {
                "exists": False,
                "size_mb": 0,
                "modified": None,
                "path": str(filepath)
            }

    return {
        "log_directory": str(LOG_DIR),
        "main_log": file_info(MAIN_LOG_FILE),
        "error_log": file_info(ERROR_LOG_FILE),
        "access_log": file_info(ACCESS_LOG_FILE),
        "scheduler_log": file_info(SCHEDULER_LOG_FILE)
    }


# ============================================================================
# CONTEXT MANAGERS
# ============================================================================

class LogContext:
    """
    Context manager for temporary logging level changes

    Example:
        >>> logger = get_logger(__name__)
        >>> with LogContext(logger, logging.DEBUG):
        ...     logger.debug("This will be logged even if normal level is INFO")
    """

    def __init__(self, logger: logging.Logger, level: int):
        """
        Initialize log context

        Args:
            logger: Logger instance
            level: Temporary logging level
        """
        self.logger = logger
        self.level = level
        self.old_level = None

    def __enter__(self):
        """Enter context - set new log level"""
        self.old_level = self.logger.level
        self.logger.setLevel(self.level)
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - restore old log level"""
        self.logger.setLevel(self.old_level)


# ============================================================================
# INITIALIZATION
# ============================================================================

# Auto-initialize logging when module is imported
# Can be disabled by setting environment variable DISABLE_AUTO_LOGGING=1
if os.getenv("DISABLE_AUTO_LOGGING") != "1":
    setup_logging()
