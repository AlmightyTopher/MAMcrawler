"""
Utility helper functions for audiobook management system
Provides reusable functions for formatting, parsing, validation, and common operations
"""

import re
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable, TypeVar
from functools import wraps
import logging


logger = logging.getLogger(__name__)


T = TypeVar('T')


# ============================================================================
# TIME & DURATION FORMATTING
# ============================================================================

def format_duration(seconds: int) -> str:
    """
    Convert seconds to human-readable duration format

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string (e.g., "1h 23m 45s", "45m 30s", "23s")

    Examples:
        >>> format_duration(3665)
        '1h 1m 5s'
        >>> format_duration(90)
        '1m 30s'
        >>> format_duration(45)
        '45s'
        >>> format_duration(0)
        '0s'
    """
    if seconds < 0:
        return "0s"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:  # Always show seconds if nothing else
        parts.append(f"{secs}s")

    return " ".join(parts)


def parse_duration(duration_str: str) -> int:
    """
    Parse human-readable duration to seconds

    Args:
        duration_str: Duration string (e.g., "1h 30m", "45m", "2h 15m 30s")

    Returns:
        Duration in seconds

    Examples:
        >>> parse_duration("1h 30m")
        5400
        >>> parse_duration("45m")
        2700
        >>> parse_duration("2h 15m 30s")
        8130
    """
    duration_str = duration_str.lower().strip()
    total_seconds = 0

    # Extract hours
    hours_match = re.search(r'(\d+)\s*h', duration_str)
    if hours_match:
        total_seconds += int(hours_match.group(1)) * 3600

    # Extract minutes
    minutes_match = re.search(r'(\d+)\s*m', duration_str)
    if minutes_match:
        total_seconds += int(minutes_match.group(1)) * 60

    # Extract seconds
    seconds_match = re.search(r'(\d+)\s*s', duration_str)
    if seconds_match:
        total_seconds += int(seconds_match.group(1))

    return total_seconds


def get_timestamp_iso() -> str:
    """
    Get current timestamp in ISO 8601 format

    Returns:
        ISO 8601 formatted timestamp string

    Example:
        >>> get_timestamp_iso()
        '2025-11-16T10:30:45.123456'
    """
    return datetime.utcnow().isoformat()


def format_timestamp(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime object to string

    Args:
        dt: Datetime object
        format_str: Format string (default: "%Y-%m-%d %H:%M:%S")

    Returns:
        Formatted timestamp string

    Example:
        >>> dt = datetime(2025, 11, 16, 10, 30, 45)
        >>> format_timestamp(dt)
        '2025-11-16 10:30:45'
    """
    return dt.strftime(format_str)


def parse_timestamp(timestamp_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    Parse timestamp string to datetime object

    Args:
        timestamp_str: Timestamp string
        format_str: Format string (default: "%Y-%m-%d %H:%M:%S")

    Returns:
        Datetime object

    Example:
        >>> parse_timestamp("2025-11-16 10:30:45")
        datetime.datetime(2025, 11, 16, 10, 30, 45)
    """
    return datetime.strptime(timestamp_str, format_str)


def time_ago(dt: datetime) -> str:
    """
    Get human-readable time ago string from datetime

    Args:
        dt: Datetime object

    Returns:
        Human-readable time ago string

    Examples:
        >>> from datetime import datetime, timedelta
        >>> time_ago(datetime.utcnow() - timedelta(seconds=30))
        '30 seconds ago'
        >>> time_ago(datetime.utcnow() - timedelta(minutes=5))
        '5 minutes ago'
        >>> time_ago(datetime.utcnow() - timedelta(hours=2))
        '2 hours ago'
    """
    now = datetime.utcnow()
    diff = now - dt

    seconds = diff.total_seconds()

    if seconds < 60:
        return f"{int(seconds)} seconds ago"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    elif seconds < 31536000:
        months = int(seconds / 2592000)
        return f"{months} month{'s' if months != 1 else ''} ago"
    else:
        years = int(seconds / 31536000)
        return f"{years} year{'s' if years != 1 else ''} ago"


# ============================================================================
# METADATA COMPLETENESS CALCULATION
# ============================================================================

def calculate_metadata_completeness(book_dict: Dict[str, Any]) -> int:
    """
    Calculate metadata completeness percentage for a book

    Evaluates presence of key metadata fields and returns a score from 0-100.

    Weights:
    - Essential fields (title, author): 40% (20% each)
    - Important fields (series, publisher, published_year, isbn, asin): 40% (8% each)
    - Optional fields (description, duration_minutes): 20% (10% each)

    Args:
        book_dict: Dictionary containing book metadata fields

    Returns:
        Completeness percentage (0-100)

    Example:
        >>> book = {
        ...     "title": "The Hobbit",
        ...     "author": "J.R.R. Tolkien",
        ...     "series": "Middle Earth",
        ...     "isbn": "9780547928227",
        ...     "published_year": 1937,
        ...     "description": "A fantasy adventure novel"
        ... }
        >>> calculate_metadata_completeness(book)
        78
    """
    score = 0.0

    # Essential fields (40% total)
    essential_fields = {
        "title": 20,
        "author": 20
    }

    # Important fields (40% total)
    important_fields = {
        "series": 8,
        "publisher": 8,
        "published_year": 8,
        "isbn": 8,
        "asin": 8
    }

    # Optional fields (20% total)
    optional_fields = {
        "description": 10,
        "duration_minutes": 10
    }

    # Check essential fields
    for field, weight in essential_fields.items():
        if book_dict.get(field):
            score += weight

    # Check important fields
    for field, weight in important_fields.items():
        if book_dict.get(field):
            score += weight

    # Check optional fields
    for field, weight in optional_fields.items():
        if book_dict.get(field):
            score += weight

    return int(score)


def get_missing_metadata_fields(book_dict: Dict[str, Any]) -> List[str]:
    """
    Get list of missing metadata fields for a book

    Args:
        book_dict: Dictionary containing book metadata fields

    Returns:
        List of missing field names

    Example:
        >>> book = {"title": "The Hobbit", "author": "J.R.R. Tolkien"}
        >>> get_missing_metadata_fields(book)
        ['series', 'publisher', 'published_year', 'isbn', 'asin', 'description', 'duration_minutes']
    """
    all_fields = [
        "title", "author", "series", "publisher", "published_year",
        "isbn", "asin", "description", "duration_minutes"
    ]

    missing_fields = []
    for field in all_fields:
        if not book_dict.get(field):
            missing_fields.append(field)

    return missing_fields


# ============================================================================
# MAGNET LINK & TORRENT PARSING
# ============================================================================

def parse_magnet_link(magnet: str) -> Optional[str]:
    """
    Extract info hash from magnet link

    Args:
        magnet: Magnet link string

    Returns:
        Info hash (40-character hex string) or None if invalid

    Examples:
        >>> parse_magnet_link("magnet:?xt=urn:btih:abc123def456&dn=MyBook")
        'abc123def456'
        >>> parse_magnet_link("invalid")
        None
    """
    if not magnet or not magnet.startswith("magnet:"):
        return None

    # Extract info hash using regex
    match = re.search(r'xt=urn:btih:([a-fA-F0-9]{40})', magnet)
    if match:
        return match.group(1).lower()

    return None


def validate_magnet_link(magnet: str) -> bool:
    """
    Validate magnet link format

    Args:
        magnet: Magnet link string

    Returns:
        True if valid, False otherwise

    Example:
        >>> validate_magnet_link("magnet:?xt=urn:btih:abc123def456...")
        True
        >>> validate_magnet_link("invalid")
        False
    """
    return parse_magnet_link(magnet) is not None


# ============================================================================
# FILE SYSTEM OPERATIONS
# ============================================================================

def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Convert string to safe filename by removing/replacing invalid characters

    Args:
        filename: Original filename
        max_length: Maximum filename length (default: 255)

    Returns:
        Sanitized filename string

    Examples:
        >>> sanitize_filename("My Book: The Story")
        'My_Book_The_Story'
        >>> sanitize_filename("Book/Title?")
        'Book_Title'
        >>> sanitize_filename("A" * 300, max_length=255)
        'A' * 255
    """
    # Replace invalid characters with underscore
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    sanitized = re.sub(invalid_chars, '_', filename)

    # Replace multiple underscores with single underscore
    sanitized = re.sub(r'_+', '_', sanitized)

    # Remove leading/trailing whitespace and underscores
    sanitized = sanitized.strip().strip('_')

    # Truncate to max length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    # Ensure not empty
    if not sanitized:
        sanitized = "unnamed"

    return sanitized


def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in megabytes

    Args:
        file_path: Path to file

    Returns:
        File size in MB (rounded to 2 decimal places)

    Example:
        >>> get_file_size_mb("C:/path/to/audiobook.m4b")
        245.67
    """
    try:
        path = Path(file_path)
        if path.exists() and path.is_file():
            size_bytes = path.stat().st_size
            size_mb = size_bytes / (1024 * 1024)
            return round(size_mb, 2)
        else:
            return 0.0
    except Exception as e:
        logger.error(f"Error getting file size for {file_path}: {e}")
        return 0.0


def ensure_directory_exists(directory_path: str) -> bool:
    """
    Ensure directory exists, create if it doesn't

    Args:
        directory_path: Path to directory

    Returns:
        True if directory exists or was created, False on error

    Example:
        >>> ensure_directory_exists("C:/path/to/logs")
        True
    """
    try:
        path = Path(directory_path)
        path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory_path}: {e}")
        return False


# ============================================================================
# LIST & COLLECTION UTILITIES
# ============================================================================

def chunk_list(items: List[T], chunk_size: int) -> List[List[T]]:
    """
    Split list into chunks of specified size

    Args:
        items: List to chunk
        chunk_size: Maximum size of each chunk

    Returns:
        List of chunks (each chunk is a list)

    Examples:
        >>> chunk_list([1, 2, 3, 4, 5, 6, 7], 3)
        [[1, 2, 3], [4, 5, 6], [7]]
        >>> chunk_list([], 5)
        []
    """
    if chunk_size <= 0:
        raise ValueError("Chunk size must be positive")

    chunks = []
    for i in range(0, len(items), chunk_size):
        chunks.append(items[i:i + chunk_size])

    return chunks


def deduplicate_list(items: List[T], key: Optional[Callable[[T], Any]] = None) -> List[T]:
    """
    Remove duplicates from list while preserving order

    Args:
        items: List to deduplicate
        key: Optional function to extract comparison key from items

    Returns:
        Deduplicated list

    Examples:
        >>> deduplicate_list([1, 2, 2, 3, 1, 4])
        [1, 2, 3, 4]
        >>> deduplicate_list([{"id": 1}, {"id": 2}, {"id": 1}], key=lambda x: x["id"])
        [{'id': 1}, {'id': 2}]
    """
    seen = set()
    result = []

    for item in items:
        item_key = key(item) if key else item

        if item_key not in seen:
            seen.add(item_key)
            result.append(item)

    return result


def safe_get(dictionary: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """
    Safely get nested dictionary value with default

    Args:
        dictionary: Dictionary to search
        *keys: Keys to traverse (nested)
        default: Default value if key not found

    Returns:
        Value at keys path or default

    Examples:
        >>> data = {"user": {"profile": {"name": "John"}}}
        >>> safe_get(data, "user", "profile", "name")
        'John'
        >>> safe_get(data, "user", "settings", "theme", default="dark")
        'dark'
    """
    current = dictionary

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default

    return current


# ============================================================================
# STRING UTILITIES
# ============================================================================

def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate string to maximum length with suffix

    Args:
        text: String to truncate
        max_length: Maximum length (including suffix)
        suffix: Suffix to append if truncated (default: "...")

    Returns:
        Truncated string

    Examples:
        >>> truncate_string("This is a very long string", 15)
        'This is a ve...'
        >>> truncate_string("Short", 10)
        'Short'
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in string (collapse multiple spaces, trim)

    Args:
        text: String to normalize

    Returns:
        Normalized string

    Examples:
        >>> normalize_whitespace("  Too   many    spaces  ")
        'Too many spaces'
        >>> normalize_whitespace("Line1\\n\\n\\nLine2")
        'Line1 Line2'
    """
    # Replace all whitespace with single space
    normalized = re.sub(r'\s+', ' ', text)

    # Trim leading/trailing whitespace
    return normalized.strip()


def extract_numbers(text: str) -> List[int]:
    """
    Extract all numbers from string

    Args:
        text: String to extract numbers from

    Returns:
        List of integers found in string

    Examples:
        >>> extract_numbers("Book 1, Book 2, and Book 3")
        [1, 2, 3]
        >>> extract_numbers("ISBN: 9780547928227")
        [9780547928227]
    """
    return [int(match) for match in re.findall(r'\d+', text)]


# ============================================================================
# HASH & CHECKSUM
# ============================================================================

def calculate_file_hash(file_path: str, algorithm: str = "md5") -> Optional[str]:
    """
    Calculate file hash using specified algorithm

    Args:
        file_path: Path to file
        algorithm: Hash algorithm (md5, sha1, sha256)

    Returns:
        Hex digest of file hash or None on error

    Example:
        >>> calculate_file_hash("C:/path/to/file.txt", "md5")
        'a1b2c3d4e5f6...'
    """
    try:
        hash_func = hashlib.new(algorithm)
        path = Path(file_path)

        with path.open('rb') as f:
            while chunk := f.read(8192):
                hash_func.update(chunk)

        return hash_func.hexdigest()

    except Exception as e:
        logger.error(f"Error calculating hash for {file_path}: {e}")
        return None


def calculate_string_hash(text: str, algorithm: str = "md5") -> str:
    """
    Calculate hash of string

    Args:
        text: String to hash
        algorithm: Hash algorithm (md5, sha1, sha256)

    Returns:
        Hex digest of string hash

    Example:
        >>> calculate_string_hash("Hello World", "md5")
        'b10a8db164e0754105b7a99be72e3fe5'
    """
    hash_func = hashlib.new(algorithm)
    hash_func.update(text.encode('utf-8'))
    return hash_func.hexdigest()


# ============================================================================
# RETRY DECORATOR
# ============================================================================

def retry_decorator(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Decorator to retry function on exception with exponential backoff

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        backoff_factor: Backoff multiplier for each retry (default: 2.0)
        exceptions: Tuple of exceptions to catch (default: (Exception,))
        on_retry: Optional callback function called on each retry

    Returns:
        Decorated function

    Example:
        >>> @retry_decorator(max_retries=3, backoff_factor=2.0)
        ... def unreliable_function():
        ...     # Function that might fail
        ...     pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            retry_count = 0
            delay = 1.0

            while retry_count <= max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retry_count += 1

                    if retry_count > max_retries:
                        logger.error(f"{func.__name__} failed after {max_retries} retries: {e}")
                        raise

                    # Call retry callback if provided
                    if on_retry:
                        on_retry(e, retry_count)

                    logger.warning(
                        f"{func.__name__} failed (attempt {retry_count}/{max_retries}), "
                        f"retrying in {delay:.1f}s: {e}"
                    )

                    time.sleep(delay)
                    delay *= backoff_factor

        return wrapper
    return decorator


# ============================================================================
# VALIDATION
# ============================================================================

def validate_isbn(isbn: str) -> bool:
    """
    Validate ISBN-10 or ISBN-13 format

    Args:
        isbn: ISBN string

    Returns:
        True if valid ISBN, False otherwise

    Examples:
        >>> validate_isbn("9780547928227")
        True
        >>> validate_isbn("0547928220")
        True
        >>> validate_isbn("invalid")
        False
    """
    # Remove hyphens and spaces
    isbn = isbn.replace('-', '').replace(' ', '')

    # Check length
    if len(isbn) not in [10, 13]:
        return False

    # Check if all characters are digits (except last char of ISBN-10 can be X)
    if len(isbn) == 10:
        if not (isbn[:-1].isdigit() and (isbn[-1].isdigit() or isbn[-1].upper() == 'X')):
            return False
    else:
        if not isbn.isdigit():
            return False

    return True


def validate_asin(asin: str) -> bool:
    """
    Validate Amazon Standard Identification Number (ASIN) format

    Args:
        asin: ASIN string

    Returns:
        True if valid ASIN, False otherwise

    Example:
        >>> validate_asin("B007978NPG")
        True
        >>> validate_asin("invalid")
        False
    """
    # ASIN is 10 characters, alphanumeric
    return bool(re.match(r'^[A-Z0-9]{10}$', asin))


def validate_year(year: int) -> bool:
    """
    Validate publication year

    Args:
        year: Year as integer

    Returns:
        True if valid year (1000-current year+5), False otherwise

    Examples:
        >>> validate_year(2025)
        True
        >>> validate_year(1500)
        True
        >>> validate_year(3000)
        False
    """
    current_year = datetime.now().year
    return 1000 <= year <= current_year + 5


# ============================================================================
# PERFORMANCE TIMING
# ============================================================================

class Timer:
    """
    Context manager for timing code execution

    Example:
        >>> with Timer() as t:
        ...     # Code to time
        ...     pass
        >>> print(f"Execution time: {t.elapsed:.2f}s")
    """

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.elapsed = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self.elapsed = self.end_time - self.start_time
