"""
Unit tests for mamcrawler.utils module.
"""

import unittest
from unittest.mock import patch, mock_open
from io import BytesIO
import tempfile
import os

from mamcrawler.utils import safe_read_markdown


def mock_open_bytes(data: bytes):
    """Return a mock open() that yields raw bytes like open(..., 'rb')."""
    return patch("builtins.open", return_value=BytesIO(data))


class TestSafeReadMarkdown(unittest.TestCase):
    """Test safe_read_markdown function."""

    def test_read_utf8_no_bom(self):
        """Test reading UTF-8 file without BOM."""
        content = "# Test Header\n\nContent here."
        with patch("builtins.open", mock_open(read_data=content.encode("utf-8"))):
            result = safe_read_markdown("test.md")
            self.assertEqual(result, content)

    def test_read_utf8_with_bom(self):
        """Test reading UTF-8 file with BOM."""
        content = "# Test Header\n\nContent here."
        bom_content = b"\xef\xbb\xbf" + content.encode("utf-8")
        with patch("builtins.open", mock_open(read_data=bom_content)):
            result = safe_read_markdown("test.md")
            self.assertEqual(result, content)

    def test_read_utf16_le_with_bom(self):
        """Test reading UTF-16 LE file with BOM."""
        content = "# Test Header\n\nContent here."
        bom_content = b"\xff\xfe" + content.encode("utf-16-le")
        with patch("builtins.open", mock_open(read_data=bom_content)):
            result = safe_read_markdown("test.md")
            self.assertEqual(result, content)

    def test_read_utf16_be_with_bom(self):
        """Test reading UTF-16 BE file with BOM."""
        content = "# Test Header\n\nContent here."
        bom_content = b"\xfe\xff" + content.encode("utf-16-be")
        with patch("builtins.open", mock_open(read_data=bom_content)):
            result = safe_read_markdown("test.md")
            self.assertEqual(result, content)

    def test_read_utf8_fallback_on_decode_error(self):
        """Test fallback to UTF-8 with errors='replace'."""
        # Create invalid UTF-8 bytes that will fail all decodings
        invalid_content = b"\xff\xfe\x00\x00# Test"
        with patch("builtins.open", mock_open(read_data=invalid_content)):
            result = safe_read_markdown("test.md")
            # Should use errors='replace' as last resort
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)

    def test_read_utf16_le_fallback(self):
        """Test fallback to UTF-16 LE."""
        utf16_le_bytes = b"\x80\x00"  # U+0080, invalid UTF-8
        expected = "\x80"

        with mock_open_bytes(utf16_le_bytes):
            result = safe_read_markdown("test.md")
            self.assertEqual(result, expected)

    def test_read_utf16_be_fallback(self):
        """Test fallback to UTF-16 BE."""
        utf16_be_bytes = b"\x00\xd8"  # U+00D8, invalid UTF-8, invalid UTF-16 LE
        expected = "\xd8"

        with mock_open_bytes(utf16_be_bytes):
            result = safe_read_markdown("test.md")
            self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
