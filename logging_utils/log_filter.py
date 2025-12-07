"""
Log filtering utilities for the unified logging system.

Provides tools for filtering and searching through log data.
"""

from typing import Dict, List, Any, Optional, Callable, Pattern
import re
from datetime import datetime, timedelta
from pathlib import Path


class LogFilter:
    """Filter and search log data"""

    def __init__(self):
        self.filters = []

    def add_filter(self, filter_func: Callable[[Dict[str, Any]], bool], name: str = None):
        """Add a filter function"""
        self.filters.append({
            'func': filter_func,
            'name': name or f"filter_{len(self.filters)}"
        })

    def filter_logs(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply all filters to log entries"""
        filtered_logs = logs
        for filter_info in self.filters:
            filtered_logs = [log for log in filtered_logs if filter_info['func'](log)]
        return filtered_logs

    @staticmethod
    def by_level(levels: List[str]) -> Callable[[Dict[str, Any]], bool]:
        """Filter by log level"""
        def filter_func(log: Dict[str, Any]) -> bool:
            return log.get('level', '').upper() in [l.upper() for l in levels]
        return filter_func

    @staticmethod
    def by_logger(loggers: List[str]) -> Callable[[Dict[str, Any]], bool]:
        """Filter by logger name"""
        def filter_func(log: Dict[str, Any]) -> bool:
            logger = log.get('logger', '')
            return any(logger.startswith(l) for l in loggers)
        return filter_func

    @staticmethod
    def by_time_range(start_time: datetime, end_time: datetime) -> Callable[[Dict[str, Any]], bool]:
        """Filter by time range"""
        def filter_func(log: Dict[str, Any]) -> bool:
            try:
                log_time = datetime.fromisoformat(log.get('timestamp', '').replace('Z', '+00:00'))
                return start_time <= log_time <= end_time
            except:
                return False
        return filter_func

    @staticmethod
    def by_message_pattern(pattern: str, case_sensitive: bool = False) -> Callable[[Dict[str, Any]], bool]:
        """Filter by message content pattern"""
        flags = 0 if case_sensitive else re.IGNORECASE
        compiled_pattern = re.compile(pattern, flags)

        def filter_func(log: Dict[str, Any]) -> bool:
            message = log.get('message', '')
            return bool(compiled_pattern.search(message))
        return filter_func

    @staticmethod
    def by_structured_data(key: str, value: Any) -> Callable[[Dict[str, Any]], bool]:
        """Filter by structured data"""
        def filter_func(log: Dict[str, Any]) -> bool:
            structured = log.get('structured_data', {})
            return structured.get(key) == value
        return filter_func

    @staticmethod
    def exclude_patterns(patterns: List[str]) -> Callable[[Dict[str, Any]], bool]:
        """Exclude logs matching patterns"""
        compiled_patterns = [re.compile(p, re.IGNORECASE) for p in patterns]

        def filter_func(log: Dict[str, Any]) -> bool:
            message = log.get('message', '')
            return not any(p.search(message) for p in compiled_patterns)
        return filter_func

    def clear_filters(self):
        """Clear all filters"""
        self.filters.clear()

    def get_active_filters(self) -> List[str]:
        """Get names of active filters"""
        return [f['name'] for f in self.filters]


class LogQuery:
    """Advanced log querying with fluent interface"""

    def __init__(self, logs: List[Dict[str, Any]]):
        self.logs = logs
        self.filters = []

    def level(self, *levels: str) -> 'LogQuery':
        """Filter by log level"""
        self.filters.append(LogFilter.by_level(list(levels)))
        return self

    def logger(self, *loggers: str) -> 'LogQuery':
        """Filter by logger name"""
        self.filters.append(LogFilter.by_logger(list(loggers)))
        return self

    def since(self, hours: int = None, days: int = None) -> 'LogQuery':
        """Filter by time range"""
        if hours:
            start_time = datetime.now() - timedelta(hours=hours)
        elif days:
            start_time = datetime.now() - timedelta(days=days)
        else:
            return self

        end_time = datetime.now()
        self.filters.append(LogFilter.by_time_range(start_time, end_time))
        return self

    def contains(self, pattern: str) -> 'LogQuery':
        """Filter by message content"""
        self.filters.append(LogFilter.by_message_pattern(pattern))
        return self

    def has_data(self, key: str, value: Any = None) -> 'LogQuery':
        """Filter by structured data"""
        if value is not None:
            self.filters.append(LogFilter.by_structured_data(key, value))
        else:
            # Just check if key exists
            def filter_func(log: Dict[str, Any]) -> bool:
                structured = log.get('structured_data', {})
                return key in structured
            self.filters.append(filter_func)
        return self

    def exclude(self, *patterns: str) -> 'LogQuery':
        """Exclude logs matching patterns"""
        self.filters.append(LogFilter.exclude_patterns(list(patterns)))
        return self

    def execute(self) -> List[Dict[str, Any]]:
        """Execute the query"""
        result = self.logs
        for filter_func in self.filters:
            result = [log for log in result if filter_func(log)]
        return result

    def count(self) -> int:
        """Get count of matching logs"""
        return len(self.execute())

    def first(self, n: int = 1) -> List[Dict[str, Any]]:
        """Get first N matching logs"""
        return self.execute()[:n]

    def last(self, n: int = 1) -> List[Dict[str, Any]]:
        """Get last N matching logs"""
        return self.execute()[-n:]