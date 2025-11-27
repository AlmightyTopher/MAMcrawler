"""
Verification Orchestrator Module
Coordinates all audiobook verification checks with retry logic and failure handling.

Verification Pipeline:
1. Narrator verification (fuzzy match)
2. Duration verification (tolerance check)
3. ISBN/ASIN verification (identifier validation)
4. Chapter verification (structure and count)

Failed items are auto-retried up to 3 times with exponential backoff.
Remaining failures are flagged for manual review.
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import time

from mamcrawler.verification.narrator_verifier import get_narrator_verifier
from mamcrawler.verification.duration_verifier import get_duration_verifier
from mamcrawler.verification.isbn_verifier import get_isbn_verifier
from mamcrawler.verification.chapter_verifier import get_chapter_verifier
from backend.logging.operation_logger import get_operation_logger

logger = logging.getLogger(__name__)


class VerificationOrchestrator:
    """Orchestrates complete verification workflow with retry logic"""

    def __init__(self, max_retries: int = 3):
        """
        Initialize verification orchestrator.

        Args:
            max_retries: Maximum retry attempts for failed verifications
        """
        self.max_retries = max_retries
        self.narrator_verifier = get_narrator_verifier()
        self.duration_verifier = get_duration_verifier()
        self.isbn_verifier = get_isbn_verifier()
        self.chapter_verifier = get_chapter_verifier()
        self.logger = get_operation_logger()

    def verify_audiobook(
        self,
        audio_path: Optional[str],
        metadata: Optional[Dict[str, Any]],
        title: str = "Unknown",
        author: str = "Unknown",
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Run complete verification pipeline for audiobook.

        Args:
            audio_path: Path to audio file (optional)
            metadata: metadata.json dict (optional)
            title: Audiobook title (for logging)
            author: Author name (for logging)
            retry_count: Current retry attempt number

        Returns:
            dict: Complete verification result with all checks
        """
        if not audio_path and not metadata:
            logger.error(f"No audio file or metadata provided for {title}")
            return self._failed_verification(
                title, author, "No audio file or metadata", retry_count
            )

        # Run all verifications
        narrator_result = self._verify_narrator(audio_path, metadata)
        duration_result = self._verify_duration(audio_path, metadata)
        isbn_result = self._verify_isbn(metadata)
        chapter_result = self._verify_chapters(audio_path, metadata, title)

        # Collect results
        all_checks = {
            'narrator': narrator_result,
            'duration': duration_result,
            'isbn': isbn_result,
            'chapters': chapter_result
        }

        # Determine overall pass/fail
        passed = all(check.get('match', check.get('valid', check.get('passed', False)))
                     for check in all_checks.values())

        # Identify failures for logging
        failures = [
            key for key, check in all_checks.items()
            if not check.get('match', check.get('valid', check.get('passed', False)))
        ]

        result = {
            'audiobook': title,
            'author': author,
            'passed': passed,
            'retry_count': retry_count,
            'checks': all_checks,
            'failures': failures,
            'timestamp': time.time()
        }

        # Log result
        self.logger.log_verification(
            title=title,
            author=author,
            passed=passed,
            failures=failures if failures else None,
            details={
                'narrator_confidence': narrator_result.get('confidence'),
                'duration_variance': duration_result.get('variance_percent'),
                'isbn_match': isbn_result.get('match'),
                'chapters': chapter_result.get('count')
            }
        )

        return result

    def _verify_narrator(self, audio_path: Optional[str], metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Run narrator verification"""
        try:
            return self.narrator_verifier.verify_audiobook(audio_path, metadata)
        except Exception as e:
            logger.error(f"Narrator verification failed: {e}")
            return {
                'match': False,
                'confidence': 0.0,
                'narrator_primary': None,
                'sources': [],
                'details': f'Verification error: {str(e)}'
            }

    def _verify_duration(self, audio_path: Optional[str], metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Run duration verification"""
        if not audio_path:
            return {
                'valid': True,  # Can't verify without audio file
                'actual_seconds': None,
                'expected_seconds': None,
                'variance_percent': None,
                'details': 'No audio file for duration verification'
            }

        try:
            return self.duration_verifier.verify_audiobook(audio_path, metadata)
        except Exception as e:
            logger.error(f"Duration verification failed: {e}")
            return {
                'valid': False,
                'actual_seconds': None,
                'expected_seconds': None,
                'variance_percent': None,
                'details': f'Verification error: {str(e)}'
            }

    def _verify_isbn(self, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Run ISBN/ASIN verification"""
        if not metadata:
            return {
                'valid': False,
                'match': False,
                'isbn': None,
                'details': 'No metadata provided'
            }

        try:
            return self.isbn_verifier.verify_audiobook(metadata)
        except Exception as e:
            logger.error(f"ISBN verification failed: {e}")
            return {
                'valid': False,
                'match': False,
                'isbn': None,
                'details': f'Verification error: {str(e)}'
            }

    def _verify_chapters(self, audio_path: Optional[str], metadata: Optional[Dict[str, Any]], title: str) -> Dict[str, Any]:
        """Run chapter verification"""
        if not audio_path:
            return {
                'passed': True,  # Can't verify without audio
                'structure_valid': True,
                'count': 0,
                'minimum_met': True,
                'details': 'No audio file for chapter verification'
            }

        try:
            is_single = self._is_single_track_audiobook(metadata)
            return self.chapter_verifier.verify_audiobook(audio_path, title, is_single)
        except Exception as e:
            logger.error(f"Chapter verification failed: {e}")
            return {
                'passed': False,
                'structure_valid': False,
                'count': 0,
                'minimum_met': False,
                'details': f'Verification error: {str(e)}'
            }

    def _is_single_track_audiobook(self, metadata: Optional[Dict[str, Any]]) -> bool:
        """Detect if audiobook is single-track (collection, short story, etc.)"""
        if not metadata:
            return False

        # Check for single-track indicators
        description = str(metadata.get('description', '')).lower()
        title = str(metadata.get('title', '')).lower()

        single_track_keywords = [
            'collection',
            'anthology',
            'short story',
            'single narration',
            'one volume'
        ]

        for keyword in single_track_keywords:
            if keyword in description or keyword in title:
                return True

        return False

    def retry_failed_verification(
        self,
        failed_result: Dict[str, Any],
        audio_path: Optional[str],
        metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Retry verification with exponential backoff.

        Args:
            failed_result: Result from previous verification attempt
            audio_path: Path to audio file
            metadata: metadata.json dict

        Returns:
            dict: New verification result
        """
        retry_count = failed_result.get('retry_count', 0) + 1

        if retry_count > self.max_retries:
            logger.warning(
                f"Max retries exceeded for {failed_result['audiobook']} "
                f"({retry_count}/{self.max_retries})"
            )
            return failed_result

        # Exponential backoff: 2^retry_count seconds
        wait_time = 2 ** retry_count
        logger.info(f"Retrying verification (attempt {retry_count}) after {wait_time}s...")
        time.sleep(wait_time)

        # Re-run verification
        return self.verify_audiobook(
            audio_path=audio_path,
            metadata=metadata,
            title=failed_result['audiobook'],
            author=failed_result['author'],
            retry_count=retry_count
        )

    def collect_failures(self, verification_results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Collect all failed verifications from batch results.

        Args:
            verification_results: List of verification results

        Returns:
            dict: Organized by failure type
        """
        failures = {
            'narrator': [],
            'duration': [],
            'isbn': [],
            'chapters': [],
            'complete_failures': []
        }

        for result in verification_results:
            if not result.get('passed'):
                # Complete failure
                failures['complete_failures'].append(result)

                # Specific failures
                for failure_type in result.get('failures', []):
                    if failure_type in failures:
                        failures[failure_type].append(result)

        return failures

    def generate_verification_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary report of verification batch.

        Args:
            results: List of verification results

        Returns:
            dict: Report with statistics and failure summary
        """
        passed_count = sum(1 for r in results if r.get('passed'))
        failed_count = len(results) - passed_count

        failures = self.collect_failures(results)

        report = {
            'total_verified': len(results),
            'passed': passed_count,
            'failed': failed_count,
            'pass_rate': passed_count / len(results) if results else 0,
            'failure_breakdown': {
                'narrator_failures': len(failures['narrator']),
                'duration_failures': len(failures['duration']),
                'isbn_failures': len(failures['isbn']),
                'chapter_failures': len(failures['chapters']),
                'complete_failures': len(failures['complete_failures'])
            },
            'items_for_manual_review': failures['complete_failures']
        }

        return report

    def _failed_verification(self, title: str, author: str, reason: str, retry_count: int) -> Dict[str, Any]:
        """Create failed verification result"""
        return {
            'audiobook': title,
            'author': author,
            'passed': False,
            'retry_count': retry_count,
            'checks': {},
            'failures': ['verification_failed'],
            'reason': reason
        }


# Singleton instance
_verification_orchestrator = None


def get_verification_orchestrator(max_retries: int = 3) -> VerificationOrchestrator:
    """Get VerificationOrchestrator instance"""
    global _verification_orchestrator
    if _verification_orchestrator is None:
        _verification_orchestrator = VerificationOrchestrator(max_retries)
    return _verification_orchestrator
