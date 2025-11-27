"""
Operation Logger Module
Tracks all audiobook automation operations with append-only logging.

Categories:
- acquisitions: New audiobooks obtained from sources
- verification: Audiobook verification results (narrator, duration, ISBN, chapters)
- processing: Audio file processing (normalization, merging, chapters)
- enrichment: Metadata enrichment from external sources
- repairs: Repair attempts and replacements
- monitoring: Daily monitoring task results
- failures: Unresolved issues requiring manual intervention
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from backend.config import get_config


class OperationLogger:
    """Manages append-only logging for all operations"""

    def __init__(self):
        self.config = get_config()
        self.logs_dir = Path(self.config.LOGS_DIR)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Category directories
        self.categories = {
            'acquisitions': 'acquisitions.md',
            'verification': 'verification.md',
            'processing': 'processing.md',
            'enrichment': 'enrichment.md',
            'repairs': 'repairs.md',
            'monitoring': 'monitoring.md',
            'failures': 'failures.md'
        }

    def _get_log_file(self, category: str) -> Path:
        """Get path to log file for category, creating daily directory structure"""
        date_dir = self.logs_dir / datetime.now().strftime('%Y-%m-%d')
        date_dir.mkdir(parents=True, exist_ok=True)
        return date_dir / self.categories.get(category, f"{category}.md")

    def _log_entry(self, category: str, entry: str) -> None:
        """Append entry to category log (append-only)"""
        log_file = self._get_log_file(category)

        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(entry + '\n')
        except Exception as e:
            logging.error(f"Failed to write to {category} log: {e}")

    def log_acquisition(self, title: str, author: str, source: str, status: str, details: Optional[Dict] = None) -> None:
        """
        Log audiobook acquisition event.

        Args:
            title: Audiobook title
            author: Author name
            source: Acquisition source (prowlarr, manual, etc.)
            status: Status (new, duplicate, failed, queued)
            details: Additional metadata
        """
        entry = f"[{datetime.now().isoformat()}] {status.upper()} | {title} by {author} | Source: {source}"
        if details:
            entry += f" | {json.dumps(details)}"

        self._log_entry('acquisitions', entry)

    def log_verification(self, title: str, author: str, passed: bool, failures: Optional[List[str]] = None, details: Optional[Dict] = None) -> None:
        """
        Log audiobook verification result.

        Args:
            title: Audiobook title
            author: Author name
            passed: True if all verifications passed
            failures: List of failed verification items
            details: Additional verification data
        """
        status = "PASSED" if passed else "FAILED"
        entry = f"[{datetime.now().isoformat()}] {status} | {title} by {author}"

        if failures:
            entry += f" | Failed checks: {', '.join(failures)}"

        if details:
            entry += f" | {json.dumps(details)}"

        self._log_entry('verification', entry)

    def log_processing(self, title: str, author: str, step: str, completed: bool, details: Optional[Dict] = None) -> None:
        """
        Log audio processing step.

        Args:
            title: Audiobook title
            author: Author name
            step: Processing step (normalize, merge, chapters, rename)
            completed: True if step successful
            details: Processing metrics
        """
        status = "COMPLETED" if completed else "FAILED"
        entry = f"[{datetime.now().isoformat()}] {status} | {title} by {author} | Step: {step}"

        if details:
            entry += f" | {json.dumps(details)}"

        self._log_entry('processing', entry)

    def log_enrichment(self, title: str, author: str, fields_added: List[str], sources: List[str], details: Optional[Dict] = None) -> None:
        """
        Log metadata enrichment event.

        Args:
            title: Audiobook title
            author: Author name
            fields_added: List of metadata fields enriched
            sources: List of sources used (audible, goodreads, openlibrary)
            details: Enrichment data
        """
        entry = f"[{datetime.now().isoformat()}] ENRICHED | {title} by {author}"
        entry += f" | Fields: {', '.join(fields_added)}"
        entry += f" | Sources: {', '.join(sources)}"

        if details:
            entry += f" | {json.dumps(details)}"

        self._log_entry('enrichment', entry)

    def log_repair(self, title: str, author: str, reason: str, result: str, details: Optional[Dict] = None) -> None:
        """
        Log repair attempt and result.

        Args:
            title: Audiobook title
            author: Author name
            reason: Reason for repair (narrator mismatch, duration out of range, etc.)
            result: Result (replaced, fixed, skipped, failed)
            details: Repair data (old vs new file, replacement source, etc.)
        """
        entry = f"[{datetime.now().isoformat()}] {result.upper()} | {title} by {author}"
        entry += f" | Reason: {reason}"

        if details:
            entry += f" | {json.dumps(details)}"

        self._log_entry('repairs', entry)

    def log_failure(self, title: str, author: str, reason: str, retry_count: int = 0, details: Optional[Dict] = None) -> None:
        """
        Log unresolved failure requiring manual review.

        Args:
            title: Audiobook title
            author: Author name
            reason: Failure reason
            retry_count: Number of retry attempts
            details: Failure details
        """
        entry = f"[{datetime.now().isoformat()}] UNRESOLVED | {title} by {author}"
        entry += f" | Reason: {reason}"
        entry += f" | Retries: {retry_count}"

        if details:
            entry += f" | {json.dumps(details)}"

        self._log_entry('failures', entry)

    def log_monitoring(self, task_name: str, completed: bool, items_found: int, items_queued: int, details: Optional[Dict] = None) -> None:
        """
        Log daily monitoring task result.

        Args:
            task_name: Monitoring task (author releases, series continuation, etc.)
            completed: True if task successful
            items_found: Number of items discovered
            items_queued: Number of items queued for download
            details: Task results
        """
        status = "COMPLETED" if completed else "FAILED"
        entry = f"[{datetime.now().isoformat()}] {status} | {task_name}"
        entry += f" | Found: {items_found} | Queued: {items_queued}"

        if details:
            entry += f" | {json.dumps(details)}"

        self._log_entry('monitoring', entry)

    def get_todays_log(self, category: str) -> str:
        """
        Get contents of today's log file for a category.

        Args:
            category: Log category

        Returns:
            str: Log contents
        """
        log_file = self._get_log_file(category)

        if not log_file.exists():
            return ""

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logging.error(f"Failed to read {category} log: {e}")
            return ""

    def get_category_summary(self, category: str) -> Dict[str, Any]:
        """
        Generate summary statistics for a category's today's logs.

        Args:
            category: Log category

        Returns:
            dict: Summary with line count, status counts, etc.
        """
        log_content = self.get_todays_log(category)

        if not log_content:
            return {
                'category': category,
                'total_entries': 0,
                'status_breakdown': {}
            }

        lines = log_content.strip().split('\n')
        status_counts = {}

        for line in lines:
            # Extract status from log line
            if 'PASSED' in line:
                status_counts['passed'] = status_counts.get('passed', 0) + 1
            elif 'FAILED' in line:
                status_counts['failed'] = status_counts.get('failed', 0) + 1
            elif 'COMPLETED' in line:
                status_counts['completed'] = status_counts.get('completed', 0) + 1
            elif 'NEW' in line:
                status_counts['new'] = status_counts.get('new', 0) + 1
            elif 'UNRESOLVED' in line:
                status_counts['unresolved'] = status_counts.get('unresolved', 0) + 1

        return {
            'category': category,
            'total_entries': len(lines),
            'status_breakdown': status_counts
        }


# Singleton instance
_operation_logger = None


def get_operation_logger() -> OperationLogger:
    """Get or create OperationLogger instance (singleton pattern)"""
    global _operation_logger
    if _operation_logger is None:
        _operation_logger = OperationLogger()
    return _operation_logger
