"""
ISBN/ASIN Verification Module
Validates audiobook matches authoritative catalog using ISBN or ASIN identifiers.
Provides lookup and cross-referencing capabilities.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ISBNVerifier:
    """Verifies audiobook identifiers and catalog matches"""

    def __init__(self):
        """Initialize ISBN verifier"""
        # TODO: Add ASIN database or API integration
        pass

    def extract_isbn_from_metadata(self, metadata: Dict[str, Any]) -> Optional[str]:
        """
        Extract ISBN from metadata.json object.

        Args:
            metadata: Dictionary from metadata.json

        Returns:
            str: ISBN/ASIN string, or None if not found
        """
        # Check common ISBN field names
        isbn_fields = [
            'isbn', 'ISBN',
            'asin', 'ASIN',
            'identifier', 'Identifier',
            'isbn13', 'ISBN13',
            'isbn10', 'ISBN10'
        ]

        for field in isbn_fields:
            if field in metadata:
                identifier = metadata[field]
                if isinstance(identifier, str) and identifier.strip():
                    isbn_clean = identifier.strip().replace('-', '')
                    if self._is_valid_isbn_or_asin(isbn_clean):
                        logger.info(f"Extracted {field}: {isbn_clean}")
                        return isbn_clean

        logger.debug("No ISBN/ASIN found in metadata")
        return None

    def _is_valid_isbn_or_asin(self, identifier: str) -> bool:
        """
        Basic validation that identifier looks like ISBN or ASIN.

        Args:
            identifier: ISBN or ASIN string

        Returns:
            bool: True if looks valid
        """
        identifier = identifier.strip()

        # ISBN-10: 10 digits
        if len(identifier) == 10 and identifier.isdigit():
            return True

        # ISBN-13: 13 digits starting with 978 or 979
        if len(identifier) == 13 and identifier.isdigit():
            if identifier.startswith(('978', '979')):
                return True

        # ASIN: 10 alphanumeric characters (common for audiobooks)
        if len(identifier) == 10 and identifier.isalnum():
            return True

        return False

    def lookup_audible_edition(self, asin: str) -> Optional[Dict[str, Any]]:
        """
        Lookup audiobook on Audible by ASIN.

        Args:
            asin: Amazon ASIN identifier

        Returns:
            dict: Edition information if found, or None
        """
        # TODO: Implement Audible API lookup
        # This would require Audible API access
        logger.debug(f"Audible lookup not yet implemented for ASIN: {asin}")
        return None

    def verify_identifier_match(self, isbn1: Optional[str], isbn2: Optional[str]) -> Dict[str, Any]:
        """
        Verify two ISBN/ASIN identifiers match.

        Args:
            isbn1: First identifier
            isbn2: Second identifier

        Returns:
            dict: {
                'valid': bool,
                'match': bool,
                'isbn1': str,
                'isbn2': str,
                'details': str
            }
        """
        # If only one identifier available, consider valid
        if not isbn1 and not isbn2:
            return {
                'valid': False,
                'match': False,
                'isbn1': None,
                'isbn2': None,
                'details': 'No ISBN/ASIN available'
            }

        if not isbn1 or not isbn2:
            return {
                'valid': True,  # Single source, no conflict
                'match': True,
                'isbn1': isbn1,
                'isbn2': isbn2,
                'details': 'Only one identifier available'
            }

        # Both available - compare
        is_match = (isbn1 == isbn2)

        return {
            'valid': is_match,
            'match': is_match,
            'isbn1': isbn1,
            'isbn2': isbn2,
            'details': (
                f"Identifiers {'match' if is_match else 'do not match'}: "
                f"{isbn1} vs {isbn2}"
            )
        }

    def verify_audiobook(self, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Complete ISBN/ASIN verification for audiobook.

        Args:
            metadata: metadata.json dict

        Returns:
            dict: Verification result
        """
        if not metadata:
            return {
                'valid': False,
                'match': False,
                'isbn': None,
                'asin': None,
                'details': 'No metadata available'
            }

        # Extract ISBN/ASIN from metadata
        isbn = self.extract_isbn_from_metadata(metadata)

        # Try to lookup on Audible if ASIN available
        audible_data = None
        if isbn and self._is_valid_isbn_or_asin(isbn) and len(isbn) == 10 and isbn.isalnum():
            # Likely an ASIN
            audible_data = self.lookup_audible_edition(isbn)

        return {
            'valid': isbn is not None,
            'match': audible_data is not None if isbn else False,
            'isbn': isbn,
            'asin': isbn if isbn and len(isbn) == 10 else None,
            'audible_data': audible_data,
            'details': (
                f"ISBN/ASIN: {isbn or 'Not found'} | "
                f"Audible match: {'Found' if audible_data else 'Not verified'}"
            )
        }


# Singleton instance
_isbn_verifier = None


def get_isbn_verifier() -> ISBNVerifier:
    """Get ISBNVerifier instance"""
    global _isbn_verifier
    if _isbn_verifier is None:
        _isbn_verifier = ISBNVerifier()
    return _isbn_verifier
