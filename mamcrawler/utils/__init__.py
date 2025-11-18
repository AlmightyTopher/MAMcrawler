"""Utility functions."""

import os
from .sanitize import sanitize_filename, anonymize_content


def safe_read_markdown(path: str) -> str:
    """
    Safely read a markdown file, handling various encodings and BOMs.

    Args:
        path: Path to the markdown file

    Returns:
        The file content as a string, decoded properly
    """
    with open(path, "rb") as f:
        raw_bytes = f.read()

    # Check for BOM and decode accordingly
    if raw_bytes.startswith(b"\xef\xbb\xbf"):  # UTF-8 BOM
        return raw_bytes[3:].decode("utf-8")
    elif raw_bytes.startswith(b"\xff\xfe"):  # UTF-16 LE BOM
        return raw_bytes[2:].decode("utf-16-le")
    elif raw_bytes.startswith(b"\xfe\xff"):  # UTF-16 BE BOM
        return raw_bytes[2:].decode("utf-16-be")
    else:
        # Try UTF-8 first
        try:
            return raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            # Fallback to UTF-16 LE
            try:
                return raw_bytes.decode("utf-16-le")
            except UnicodeDecodeError:
                # Fallback to UTF-16 BE
                try:
                    return raw_bytes.decode("utf-16-be")
                except UnicodeDecodeError:
                    # Last resort: use errors='replace' to avoid crashes
                    return raw_bytes.decode("utf-8", errors="replace")


__all__ = ["sanitize_filename", "anonymize_content", "safe_read_markdown"]
