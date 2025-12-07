"""
Input Sanitization Utility

Provides comprehensive input validation and sanitization to prevent:
- XSS (Cross-Site Scripting) attacks
- SQL Injection (though SQLAlchemy ORM provides protection)
- Command Injection
- Path Traversal
- Unicode/encoding attacks
"""

import logging
import re
from typing import Optional, List, Any
from html import escape as html_escape
from pathlib import Path
import unicodedata

logger = logging.getLogger(__name__)


class SanitizationError(Exception):
    """Raised when sanitization fails or detects malicious input."""
    pass


class InputSanitizer:
    """
    Comprehensive input sanitization for user-provided data.

    Handles:
    - HTML/XSS sanitization
    - Path traversal prevention
    - SQL keyword detection
    - Command injection prevention
    - Unicode normalization
    """

    # Dangerous patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",  # Script tags
        r"javascript:",  # JavaScript protocol
        r"on\w+\s*=",  # Event handlers
        r"<iframe",  # iFrame injection
        r"<embed",  # Embed injection
    ]

    PATH_TRAVERSAL_PATTERNS = [
        r"\.\.[\\/]",  # Parent directory references
        r"~",  # Home directory
        r"\$\{",  # Variable injection
    ]

    SQL_KEYWORDS = {
        "select", "insert", "update", "delete", "drop", "create",
        "alter", "exec", "execute", "union", "or", "and", "--", "/*", "*/"
    }

    def __init__(self, strict: bool = False):
        """
        Initialize sanitizer.

        Args:
            strict: If True, raise exceptions on suspicious input
                   If False, log warnings and clean input
        """
        self.strict = strict
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for performance."""
        self.xss_regex = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.XSS_PATTERNS]
        self.path_traversal_regex = [re.compile(p) for p in self.PATH_TRAVERSAL_PATTERNS]

    def sanitize_string(self, value: str, field_name: str = "input") -> str:
        """
        Sanitize a string value.

        Args:
            value: String to sanitize
            field_name: Name of field (for logging)

        Returns:
            Sanitized string

        Raises:
            SanitizationError: If strict mode and suspicious input detected
        """
        if not isinstance(value, str):
            if self.strict:
                raise SanitizationError(f"{field_name} must be a string")
            return str(value)

        # Remove null bytes
        value = value.replace("\x00", "")

        # Normalize unicode (decompose combined characters)
        value = unicodedata.normalize("NFKD", value)

        # Check for XSS patterns
        for pattern in self.xss_regex:
            if pattern.search(value):
                msg = f"Potential XSS detected in {field_name}"
                logger.warning(msg)
                if self.strict:
                    raise SanitizationError(msg)
                # Clean by HTML escaping
                value = html_escape(value)

        # Limit length (prevent buffer overflow type attacks)
        max_length = 10000
        if len(value) > max_length:
            msg = f"{field_name} exceeds maximum length of {max_length}"
            logger.warning(msg)
            if self.strict:
                raise SanitizationError(msg)
            value = value[:max_length]

        return value

    def sanitize_path(self, path: str, field_name: str = "path") -> str:
        """
        Sanitize file path to prevent path traversal.

        Args:
            path: Path to sanitize
            field_name: Name of field (for logging)

        Returns:
            Sanitized path

        Raises:
            SanitizationError: If strict mode and suspicious input detected
        """
        # Check for path traversal patterns
        for pattern in self.path_traversal_regex:
            if pattern.search(path):
                msg = f"Potential path traversal detected in {field_name}: {path}"
                logger.warning(msg)
                if self.strict:
                    raise SanitizationError(msg)

        # Resolve to absolute path and ensure it's safe
        try:
            resolved = Path(path).resolve()
            return str(resolved)
        except Exception as e:
            msg = f"Invalid path in {field_name}: {str(e)}"
            logger.warning(msg)
            if self.strict:
                raise SanitizationError(msg)
            return path

    def sanitize_sql_input(self, value: str, field_name: str = "input") -> str:
        """
        Detect potential SQL injection attempts.

        Note: This is defensive in depth. SQLAlchemy ORM provides
        primary protection via parameterized queries.

        Args:
            value: String to check
            field_name: Name of field (for logging)

        Returns:
            Original string if safe

        Raises:
            SanitizationError: If suspicious SQL detected in strict mode
        """
        value_lower = value.lower().strip()

        # Check for SQL keywords (simple heuristic)
        words = re.findall(r"\w+", value_lower)
        dangerous_words = [w for w in words if w in self.SQL_KEYWORDS]

        if dangerous_words:
            msg = f"Potential SQL injection in {field_name}: found keywords {dangerous_words}"
            logger.warning(msg)
            if self.strict:
                raise SanitizationError(msg)

        return value

    def sanitize_command_input(self, value: str, field_name: str = "input") -> str:
        """
        Prevent shell command injection.

        Args:
            value: String to sanitize
            field_name: Name of field (for logging)

        Returns:
            Sanitized string

        Raises:
            SanitizationError: If suspicious command detected in strict mode
        """
        dangerous_chars = [";", "|", "&", "$", "`", "(", ")", "<", ">"]

        for char in dangerous_chars:
            if char in value:
                msg = f"Dangerous character '{char}' in {field_name}"
                logger.warning(msg)
                if self.strict:
                    raise SanitizationError(msg)
                # Remove dangerous characters
                value = value.replace(char, "")

        return value

    def sanitize_email(self, email: str, field_name: str = "email") -> str:
        """
        Sanitize and validate email address.

        Args:
            email: Email to sanitize
            field_name: Name of field (for logging)

        Returns:
            Sanitized email

        Raises:
            SanitizationError: If invalid email format
        """
        # Basic email validation regex
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        if not re.match(email_pattern, email):
            msg = f"Invalid email format in {field_name}: {email}"
            logger.warning(msg)
            if self.strict:
                raise SanitizationError(msg)

        return email.lower()

    def sanitize_dict(self, data: dict, field_name: str = "data") -> dict:
        """
        Sanitize all string values in a dictionary.

        Args:
            data: Dictionary to sanitize
            field_name: Name of field (for logging)

        Returns:
            Dictionary with sanitized string values
        """
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = self.sanitize_string(value, f"{field_name}.{key}")
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_dict(value, f"{field_name}.{key}")
            elif isinstance(value, list):
                sanitized[key] = [
                    self.sanitize_string(v, f"{field_name}.{key}[]")
                    if isinstance(v, str) else v
                    for v in value
                ]
            else:
                sanitized[key] = value

        return sanitized


# Global sanitizer instances
_standard_sanitizer: Optional[InputSanitizer] = None
_strict_sanitizer: Optional[InputSanitizer] = None


def get_sanitizer(strict: bool = False) -> InputSanitizer:
    """Get or create global sanitizer instance."""
    global _standard_sanitizer, _strict_sanitizer

    if strict:
        if _strict_sanitizer is None:
            _strict_sanitizer = InputSanitizer(strict=True)
        return _strict_sanitizer
    else:
        if _standard_sanitizer is None:
            _standard_sanitizer = InputSanitizer(strict=False)
        return _standard_sanitizer


def sanitize_string(value: str, field_name: str = "input", strict: bool = False) -> str:
    """Sanitize string using global sanitizer."""
    sanitizer = get_sanitizer(strict=strict)
    return sanitizer.sanitize_string(value, field_name)


def sanitize_path(path: str, field_name: str = "path", strict: bool = False) -> str:
    """Sanitize path using global sanitizer."""
    sanitizer = get_sanitizer(strict=strict)
    return sanitizer.sanitize_path(path, field_name)


def sanitize_email(email: str, field_name: str = "email", strict: bool = False) -> str:
    """Sanitize email using global sanitizer."""
    sanitizer = get_sanitizer(strict=strict)
    return sanitizer.sanitize_email(email, field_name)


def sanitize_dict(data: dict, field_name: str = "data", strict: bool = False) -> dict:
    """Sanitize dictionary using global sanitizer."""
    sanitizer = get_sanitizer(strict=strict)
    return sanitizer.sanitize_dict(data, field_name)
