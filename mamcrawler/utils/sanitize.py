"""
Sanitization and anonymization utilities.
"""

import re
from typing import Optional


def sanitize_filename(title: str, max_length: int = 100) -> str:
    """
    Convert title to valid filename.

    Args:
        title: The title to convert
        max_length: Maximum filename length

    Returns:
        Safe filename string
    """
    # Remove special characters that are invalid in filenames
    filename = re.sub(r'[<>:"/\\|?*]', '', title)
    # Replace whitespace with underscores
    filename = re.sub(r'\s+', '_', filename)
    # Limit length
    return filename[:max_length]


def anonymize_content(content: str, max_length: Optional[int] = 5000) -> str:
    """
    Remove PII from content.

    Args:
        content: The content to anonymize
        max_length: Maximum content length (None for no limit)

    Returns:
        Anonymized content string
    """
    # Remove email addresses
    content = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        '[EMAIL]',
        content
    )
    # Remove potential usernames
    content = re.sub(
        r'\buser[_-]\w+\b',
        '[USER]',
        content,
        flags=re.IGNORECASE
    )

    # Limit content length if specified
    if max_length and len(content) > max_length:
        content = content[:max_length]

    return content


def clean_whitespace(text: str) -> str:
    """
    Clean up excessive whitespace in text.

    Args:
        text: The text to clean

    Returns:
        Cleaned text
    """
    # Remove excessive newlines
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    return text.strip()
