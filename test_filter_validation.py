#!/usr/bin/env python3
"""
Test/Dummy Entry Filter Validation Script
Demonstrates and validates the filtering logic for test, dummy, and spam entries.
"""

import sys
import re
from typing import List, Tuple

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class TestEntryFilter:
    """Filters out test, dummy, and spam entries from torrent results."""
    
    # Patterns that indicate test/dummy/spam entries
    TEST_PATTERNS = [
        r'\b(test|demo|sample|dummy|test[_\s-]?file|example|sample[_\s-]?file)\b',
        r'\b(test[_\s-]?(audiobook|book|torrent|download)|demo[_\s-]?(audiobook|book|torrent))\b',
        r'\b(lorem|ipsum|placeholder|fake|fake[_\s-]?book|test[_\s-]?content)\b',
        r'\b(test[_\s-]?(series|collection|volume|part)|sample[_\s-]?(collection|series))\b',
        r'\b(automated[_\s-]?test|bot[_\s-]?test|spider[_\s-]?test|crawler[_\s-]?test)\b',
        r'\b(debug[_\s-]?(test|file)|debug[_\s-]?(content|torrent)|dev[_\s-]?test)\b',
        r'\b(check[_\s-]?this|test[_\s-]?upload|upload[_\s-]?test|test[_\s-]?upload)\b',
        r'\b(noise|garbage|spam[_\s-]?(file|content)|random[_\s-]?data)\b',
        r'\b(qa[_\s-]?test|quality[_\s-]?assurance|test[_\s-]?qa|qa[_\s-]?(file|test))\b',
        r'\b(site[_\s-]?test|site[_\s-]?check|test[_\s-]?site|check[_\s-]?site)\b'
    ]
    
    # Suspicious title patterns
    SUSPICIOUS_PATTERNS = [
        r'^[0-9a-f]{32,}$',  # Pure hex hashes
        r'^[0-9]+$',  # Pure numbers
        r'^[^a-zA-Z0-9\s]*$',  # Only special characters
        r'\b\d{8,}\b',  # Very long numbers
        r'\b(test|demo)\s*[0-9]+\b',  # Test + numbers
    ]
    
    # Minimum quality thresholds
    MIN_TITLE_LENGTH = 10
    MAX_TITLE_LENGTH = 200
    MIN_SNATCHED_COUNT = 0  # Allow new torrents
    MIN_FILE_SIZE_MB = 50   # At least 50MB for a meaningful audiobook
    
    def __init__(self):
        self.test_regex = re.compile('|'.join(self.TEST_PATTERNS), re.IGNORECASE)
        self.suspicious_regex = re.compile('|'.join(self.SUSPICIOUS_PATTERNS), re.IGNORECASE)
    
    def is_test_entry(self, title: str, size_text: str = "", snatched_text: str = "") -> tuple[bool, str]:
        """
        Check if a torrent entry is a test/dummy entry.
        
        Returns:
            tuple: (is_test, reason)
        """
        title_lower = title.lower().strip()
        
        # Check against test patterns
        if self.test_regex.search(title_lower):
            return True, "Contains test/demo/dummy patterns"
        
        # Check suspicious patterns
        if self.suspicious_regex.search(title):
            return True, "Suspicious title pattern"
        
        # Title length checks
        if len(title.strip()) < self.MIN_TITLE_LENGTH:
            return True, f"Title too short (min {self.MIN_TITLE_LENGTH} chars)"
        
        if len(title.strip()) > self.MAX_TITLE_LENGTH:
            return True, f"Title too long (max {self.MAX_TITLE_LENGTH} chars)"
        
        # Check for excessive special characters or repeated patterns
        if title.count('!') > 3 or title.count('?') > 3:
            return True, "Excessive punctuation marks"
        
        # Check for excessive whitespace or unusual characters
        if title.count('  ') > 0 or any(ord(c) > 127 for c in title):
            return True, "Unusual whitespace or characters"
        
        # Parse and validate size
        if not self._is_valid_size(size_text):
            return True, "Invalid or suspicious file size"
        
        # Parse and validate snatched count
        if not self._is_valid_snatched_count(snatched_text):
            return True, "Invalid snatched count"
        
        return False, "Genuine entry"
    
    def _is_valid_size(self, size_text: str) -> bool:
        """Validate file size is reasonable for an audiobook."""
        if not size_text or size_text.strip() == "":
            return False
        
        try:
            # Parse size (e.g., "2.5 GB", "500 MB", "1.2 TB")
            size_parts = size_text.strip().split()
            if len(size_parts) != 2:
                return False
            
            value = float(size_parts[0])
            unit = size_parts[1].upper()
            
            # Convert to MB for comparison
            if unit == 'GB':
                mb_size = value * 1024
            elif unit == 'MB':
                mb_size = value
            elif unit == 'TB':
                mb_size = value * 1024 * 1024
            else:
                return False
            
            # Check if size is within reasonable bounds
            if mb_size < self.MIN_FILE_SIZE_MB:
                return False
            
            if mb_size > 50000:  # 50GB seems excessive for audiobooks
                return False
            
            return True
            
        except (ValueError, IndexError):
            return False
    
    def _is_valid_snatched_count(self, snatched_text: str) -> bool:
        """Validate snatched count is reasonable."""
        if not snatched_text or snatched_text.strip() == "":
            return True  # Allow empty snatched counts (new torrents)
        
        try:
            # Remove commas and extract number
            snatched_clean = snatched_text.strip().replace(',', '')
            
            # Handle various formats
            if snatched_clean.lower() == 'n/a' or snatched_clean == '-':
                return True
            
            snatched_count = int(snatched_clean)
            
            # Allow reasonable range (0 to 50000)
            return 0 <= snatched_count <= 50000
            
        except (ValueError, AttributeError):
            return False


def test_filter_functionality():
    """Test the filter with various examples."""
    filter_instance = TestEntryFilter()
    
    # Test cases: (title, size, snatched, expected_result)
    test_cases = [
        # Genuine audiobook titles
        ("The Hobbit by J.R.R. Tolkien", "1.2 GB", "1,250", True),
        ("Dune by Frank Herbert", "850 MB", "2,100", True),
        ("Harry Potter and the Sorcerer's Stone", "2.5 GB", "5,600", True),
        ("Foundation by Isaac Asimov", "1.1 GB", "890", True),
        
        # Test/dummy entries that should be filtered
        ("Test audiobook download", "500 MB", "5", False),
        ("Demo torrent - sample file", "200 MB", "1", False),
        ("dummy book test content", "100 MB", "0", False),
        ("Example audiobook - test upload", "1.5 GB", "12", False),
        ("Test series Volume 1", "800 MB", "3", False),
        
        # Suspicious patterns
        ("1234567890123456789012345678901234567890", "1.0 GB", "5", False),
        ("!!!???!!!specialchars!!!", "500 MB", "2", False),
        ("                          ", "1.0 GB", "1", False),
        
        # Invalid sizes
        ("Good Book Title", "0 MB", "10", False),
        ("Another Title", "0.01 MB", "15", False),
        ("Large Title", "100 GB", "3", False),
        
        # Short titles
        ("Hi", "1.0 GB", "5", False),
        ("Test", "500 MB", "2", False),
        
        # VIP and freeleech (should pass)
        ("The Lord of the Rings (VIP)", "3.2 GB", "8,500", True),
        ("FreeLeech Fantasy Novel", "1.8 GB", "1,200", True),
    ]
    
    print("Testing Test/Dummy Entry Filter:")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for title, size, snatched, expected_genuine in test_cases:
        is_test, reason = filter_instance.is_test_entry(title, size, snatched)
        actual_genuine = not is_test
        
        status = "PASS" if actual_genuine == expected_genuine else "FAIL"
        result_type = "GENUINE" if actual_genuine else "FILTERED"
        
        print(f"{status} | {result_type:8} | {reason:30} | {title[:50]}")
        
        if actual_genuine == expected_genuine:
            passed += 1
        else:
            failed += 1
    
    print("=" * 80)
    print(f"Test Results: {passed} passed, {failed} failed")
    print(f"Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    return failed == 0


def demonstrate_filter_categories():
    """Demonstrate different categories of filtering."""
    filter_instance = TestEntryFilter()
    
    print("\nFilter Categories Demonstration:")
    print("=" * 80)
    
    categories = {
        "Direct Test Words": [
            "test audiobook",
            "demo book",
            "sample file",
            "dummy content",
            "example upload"
        ],
        "Suspicious Patterns": [
            "1234567890123456789012345678901234567890",
            "!!!???!!!",
            "          ",
            "99999999"
        ],
        "Invalid Sizes": [
            ("Book Title", "0 MB"),
            ("Another Title", "0.01 MB"),
            ("Large Book", "100 GB")
        ],
        "Short Titles": [
            "Hi",
            "Test",
            "A",
            "Ok"
        ],
        "Genuine Titles (Should Pass)": [
            ("The Hobbit", "1.2 GB"),
            ("Dune by Frank Herbert", "850 MB"),
            ("Harry Potter Series", "2.5 GB")
        ]
    }
    
    for category, items in categories.items():
        print(f"\n{category}:")
        print("-" * 40)
        
        for item in items:
            if isinstance(item, tuple):
                title, size = item
                snatched = "100"
            else:
                title = item
                size = "1.0 GB"
                snatched = "50"
            
            is_test, reason = filter_instance.is_test_entry(title, size, snatched)
            result = "FILTERED" if is_test else "GENUINE"
            
            print(f"  {result:8} | {reason:25} | {title[:40]}")


if __name__ == "__main__":
    print("Test/Dummy Entry Filter Validation")
    print("=" * 80)
    
    # Run functionality tests
    success = test_filter_functionality()
    
    # Demonstrate filtering categories
    demonstrate_filter_categories()
    
    print("\n" + "=" * 80)
    if success:
        print("Filter validation completed successfully!")
        print("The filter correctly identifies test/dummy entries")
        print("Ready for production use in audiobook downloader")
    else:
        print("Filter validation failed!")
        print("Review the test cases above")
    
    print("=" * 80)