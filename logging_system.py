"""
Unified Logging System for MAMcrawler

A comprehensive, structured logging framework that consolidates all logging approaches
across the MAMcrawler project. Provides centralized logging management with support for:

- Structured logging with JSON format
- Multiple output destinations (console, file, database, remote)
- Log levels and filtering
- Automatic log rotation and archiving
- Performance monitoring and metrics
- Distributed tracing support
- Log aggregation and analysis
- Security event logging

Author: Agent 9
"""

import os
import sys
import json
import logging
import logging.handlers
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import queue
import atexit
import weakref
from contextlib import contextmanager
import traceback
import inspect


# ============================================================================
# CONSTANTS AND CONFIGURATION
# ============================================================================

class LogLevel(Enum):
    """Standardized log levels"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL
    SECURITY = 60  # Custom level for security events
    PERFORMANCE = 25  # Custom level for performance metrics
    AUDIT = 35  # Custom level for audit trails


class LogDestination(Enum):
    """Supported log destinations"""
    CONSOLE = "console"
    FILE = "file"
    DATABASE = "database"
    REMOTE = "remote"
    SYSLOG = "syslog"
    CLOUDWATCH = "cloudwatch"
    ELASTICSEARCH = "elasticsearch"


@dataclass
class LogConfig:
    """Configuration for logging system"""
    level: str = "INFO"
    destinations: List[str] = None
    format: str = "structured"
    enable_json: bool = True
    enable_tracing: bool = False
    enable_metrics: bool = True
    max_file_size_mb: int = 10
    backup_count: int = 30
    log_directory: str = "logs"
    app_name: str = "MAMcrawler"
    environment: str = "development"

    def __post_init__(self):
        if self.destinations is None:
            self.destinations = ["console", "file"]


# ============================================================================
# LOG RECORD ENHANCEMENT
# ============================================================================

class StructuredLogRecord(logging.LogRecord):
    """Enhanced log record with structured data support"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.structured_data = getattr(self, 'structured_data', {})
        self.trace_id = getattr(self, 'trace_id', None)
        self.span_id = getattr(self, 'span_id', None)
        self.user_id = getattr(self, 'user_id', None)
        self.session_id = getattr(self, 'session_id', None)
        self.correlation_id = getattr(self, 'correlation_id', None)
        self.performance_data = getattr(self, 'performance_data', {})
        self.security_context = getattr(self, 'security_context', {})


class StructuredLogger(logging.Logger):
    """Enhanced logger with structured logging capabilities"""

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False,
             stacklevel=1, structured_data=None, **kwargs):
        """
        Enhanced _log method with structured data support
        """
        if extra is None:
            extra = {}

        # Add structured data to extra
        if structured_data:
            extra['structured_data'] = structured_data

        # Add any additional context from kwargs
        for key, value in kwargs.items():
            if key not in ['structured_data']:
                extra[key] = value

        super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel)


# ============================================================================
# CUSTOM FORMATTERS
# ============================================================================

class StructuredFormatter(logging.Formatter):
    """Formatter for structured JSON logging"""

    def __init__(self, include_extra=True):
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: StructuredLogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.thread,
            "thread_name": record.threadName,
        }

        # Add structured data if present
        if hasattr(record, 'structured_data') and record.structured_data:
            log_data["structured_data"] = record.structured_data

        # Add tracing information
        if hasattr(record, 'trace_id') and record.trace_id:
            log_data["trace_id"] = record.trace_id
        if hasattr(record, 'span_id') and record.span_id:
            log_data["span_id"] = record.span_id

        # Add user context
        if hasattr(record, 'user_id') and record.user_id:
            log_data["user_id"] = record.user_id
        if hasattr(record, 'session_id') and record.session_id:
            log_data["session_id"] = record.session_id
        if hasattr(record, 'correlation_id') and record.correlation_id:
            log_data["correlation_id"] = record.correlation_id

        # Add performance data
        if hasattr(record, 'performance_data') and record.performance_data:
            log_data["performance"] = record.performance_data

        # Add security context
        if hasattr(record, 'security_context') and record.security_context:
            log_data["security"] = record.security_context

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "Unknown",
                "message": str(record.exc_info[1]) if record.exc_info[1] else "",
                "traceback": self.formatException(record.exc_info)
            }

        # Include any extra fields if requested
        if self.include_extra and hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                             'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                             'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                             'thread', 'threadName', 'processName', 'process', 'message',
                             'structured_data', 'trace_id', 'span_id', 'user_id',
                             'session_id', 'correlation_id', 'performance_data',
                             'security_context']:
                    log_data[f"extra_{key}"] = value

        return json.dumps(log_data, default=str)


class ColoredConsoleFormatter(logging.Formatter):
    """Formatter with color support for console output"""

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'SECURITY': '\033[41m',   # Red background
        'PERFORMANCE': '\033[34m', # Blue
        'AUDIT': '\033[37m',      # White
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record):
        """Format with colors for console"""
        # Get the original formatted message
        message = super().format(record)

        # Add color if level name is recognized
        level_color = self.COLORS.get(record.levelname, '')
        reset_color = self.COLORS.get('RESET', '')

        return f"{level_color}{message}{reset_color}"


# ============================================================================
# CUSTOM HANDLERS
# ============================================================================

class AsyncLogHandler(logging.Handler):
    """Asynchronous log handler for improved performance"""

    def __init__(self, handler: logging.Handler, queue_size: int = 1000):
        super().__init__()
        self.handler = handler
        self.queue = queue.Queue(maxsize=queue_size)
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()
        self._shutdown = False

    def emit(self, record):
        """Emit log record asynchronously"""
        try:
            self.queue.put_nowait(record)
        except queue.Full:
            # If queue is full, log synchronously as fallback
            self.handler.emit(record)

    def _process_queue(self):
        """Process queued log records"""
        while not self._shutdown:
            try:
                record = self.queue.get(timeout=1)
                self.handler.emit(record)
                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception:
                # Prevent handler exceptions from crashing the thread
                pass

    def close(self):
        """Close handler and cleanup"""
        self._shutdown = True
        self.worker_thread.join(timeout=5)
        self.handler.close()
        super().close()


class DatabaseLogHandler(logging.Handler):
    """Handler for logging to database"""

    def __init__(self, connection_string: str, table_name: str = "logs"):
        super().__init__()
        self.connection_string = connection_string
        self.table_name = table_name
        self._init_db()

    def _init_db(self):
        """Initialize database table if it doesn't exist"""
        try:
            import sqlite3
            with sqlite3.connect(self.connection_string) as conn:
                conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        level TEXT NOT NULL,
                        logger TEXT NOT NULL,
                        message TEXT NOT NULL,
                        module TEXT,
                        function TEXT,
                        line INTEGER,
                        process INTEGER,
                        thread INTEGER,
                        thread_name TEXT,
                        structured_data TEXT,
                        trace_id TEXT,
                        span_id TEXT,
                        user_id TEXT,
                        session_id TEXT,
                        correlation_id TEXT,
                        performance_data TEXT,
                        security_context TEXT,
                        exception_data TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            print(f"Failed to initialize database logging: {e}")

    def emit(self, record: StructuredLogRecord):
        """Emit log record to database"""
        try:
            import sqlite3
            with sqlite3.connect(self.connection_string) as conn:
                log_data = {
                    'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                    'level': record.levelname,
                    'logger': record.name,
                    'message': record.getMessage(),
                    'module': record.module,
                    'function': record.funcName,
                    'line': record.lineno,
                    'process': record.process,
                    'thread': record.thread,
                    'thread_name': record.threadName,
                    'structured_data': json.dumps(getattr(record, 'structured_data', {})),
                    'trace_id': getattr(record, 'trace_id', None),
                    'span_id': getattr(record, 'span_id', None),
                    'user_id': getattr(record, 'user_id', None),
                    'session_id': getattr(record, 'session_id', None),
                    'correlation_id': getattr(record, 'correlation_id', None),
                    'performance_data': json.dumps(getattr(record, 'performance_data', {})),
                    'security_context': json.dumps(getattr(record, 'security_context', {})),
                    'exception_data': json.dumps({
                        'type': record.exc_info[0].__name__ if record.exc_info and record.exc_info[0] else None,
                        'message': str(record.exc_info[1]) if record.exc_info and record.exc_info[1] else None,
                        'traceback': self.format(record) if record.exc_info else None
                    }) if record.exc_info else None
                }

                columns = ', '.join(log_data.keys())
                placeholders = ', '.join(['?' for _ in log_data])
                values = list(log_data.values())

                conn.execute(f"""
                    INSERT INTO {self.table_name} ({columns})
                    VALUES ({placeholders})
                """, values)
                conn.commit()

        except Exception as e:
            # Fallback to stderr if database logging fails
            print(f"Database logging failed: {e}", file=sys.stderr)


class MetricsHandler(logging.Handler):
    """Handler for collecting performance metrics from logs"""

    def __init__(self):
        super().__init__()
        self.metrics = {}
        self._lock = threading.Lock()

    def emit(self, record: StructuredLogRecord):
        """Collect metrics from log records"""
        if hasattr(record, 'performance_data') and record.performance_data:
            with self._lock:
                for key, value in record.performance_data.items():
                    if key not in self.metrics:
                        self.metrics[key] = []
                    self.metrics[key].append({
                        'timestamp': record.created,
                        'value': value,
                        'logger': record.name,
                        'level': record.levelname
                    })

                    # Keep only last 1000 entries per metric
                    if len(self.metrics[key]) > 1000:
                        self.metrics[key] = self.metrics[key][-1000:]

    def get_metrics(self, metric_name: str = None) -> Dict:
        """Get collected metrics"""
        with self._lock:
            if metric_name:
                return {metric_name: self.metrics.get(metric_name, [])}
            return self.metrics.copy()

    def clear_metrics(self, metric_name: str = None):
        """Clear collected metrics"""
        with self._lock:
            if metric_name:
                self.metrics.pop(metric_name, None)
            else:
                self.metrics.clear()


# ============================================================================
# TRACING AND CONTEXT MANAGEMENT
# ============================================================================

class TraceContext:
    """Context manager for distributed tracing"""

    _current_trace = threading.local()
    _trace_counter = 0
    _span_counter = 0
    _lock = threading.Lock()

    @classmethod
    def start_trace(cls, name: str) -> str:
        """Start a new trace"""
        with cls._lock:
            cls._trace_counter += 1
            trace_id = f"trace_{cls._trace_counter}_{int(time.time())}"
        cls._current_trace.trace_id = trace_id
        cls._current_trace.trace_name = name
        cls._current_trace.spans = []
        return trace_id

    @classmethod
    def start_span(cls, name: str) -> str:
        """Start a new span within current trace"""
        if not hasattr(cls._current_trace, 'trace_id'):
            cls.start_trace("auto_generated")

        with cls._lock:
            cls._span_counter += 1
            span_id = f"span_{cls._span_counter}"

        span = {
            'id': span_id,
            'name': name,
            'start_time': time.time(),
            'parent_span': getattr(cls._current_trace, 'current_span', None)
        }

        cls._current_trace.spans.append(span)
        cls._current_trace.current_span = span_id
        return span_id

    @classmethod
    def end_span(cls, span_id: str = None):
        """End current or specified span"""
        if not hasattr(cls._current_trace, 'spans'):
            return

        target_span = span_id or getattr(cls._current_trace, 'current_span', None)
        if not target_span:
            return

        for span in reversed(cls._current_trace.spans):
            if span['id'] == target_span:
                span['end_time'] = time.time()
                span['duration'] = span['end_time'] - span['start_time']
                break

        # Restore parent span
        if cls._current_trace.spans:
            for span in reversed(cls._current_trace.spans):
                if span['id'] != target_span and span.get('end_time') is None:
                    cls._current_trace.current_span = span['id']
                    break
            else:
                cls._current_trace.current_span = None

    @classmethod
    def get_current_context(cls) -> Dict:
        """Get current trace context"""
        return {
            'trace_id': getattr(cls._current_trace, 'trace_id', None),
            'span_id': getattr(cls._current_trace, 'current_span', None),
            'trace_name': getattr(cls._current_trace, 'trace_name', None)
        }


@contextmanager
def trace_context(trace_name: str, span_name: str = None):
    """Context manager for tracing operations"""
    trace_id = TraceContext.start_trace(trace_name)
    span_id = TraceContext.start_span(span_name or trace_name)

    try:
        yield trace_id, span_id
    finally:
        TraceContext.end_span(span_id)


# ============================================================================
# MAIN LOGGING SYSTEM
# ============================================================================

class UnifiedLoggingSystem:
    """Main unified logging system manager"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.config = LogConfig()
            self.loggers = {}
            self.handlers = {}
            self.metrics_handler = MetricsHandler()
            self._shutdown_handlers = []
            self._initialized = True

            # Register cleanup
            atexit.register(self.shutdown)

    def configure(self, config: Union[LogConfig, Dict]):
        """Configure the logging system"""
        if isinstance(config, dict):
            config = LogConfig(**config)
        self.config = config

        # Set up logging
        self._setup_logging()

    def _setup_logging(self):
        """Set up logging based on configuration"""
        # Clear existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        # Set root logger level
        root_logger.setLevel(getattr(logging, self.config.level.upper(), logging.INFO))

        # Create formatters
        if self.config.format == "json" or self.config.enable_json:
            formatter = StructuredFormatter()
        else:
            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )

        # Set up destinations
        for destination in self.config.destinations:
            self._setup_destination(destination, formatter)

        # Add metrics handler
        if self.config.enable_metrics:
            root_logger.addHandler(self.metrics_handler)

        # Suppress noisy loggers
        self._suppress_noisy_loggers()

    def _setup_destination(self, destination: str, formatter: logging.Formatter):
        """Set up a specific log destination"""
        root_logger = logging.getLogger()

        if destination == "console":
            # Console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, self.config.level.upper(), logging.INFO))
            console_handler.setFormatter(formatter)

            # Add color support if available
            try:
                import colorlog
                color_formatter = colorlog.ColoredFormatter(
                    "%(log_color)s%(asctime)s | %(levelname)-8s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                    log_colors={
                        'DEBUG': 'cyan',
                        'INFO': 'green',
                        'WARNING': 'yellow',
                        'ERROR': 'red',
                        'CRITICAL': 'red,bg_white',
                    }
                )
                console_handler.setFormatter(color_formatter)
            except ImportError:
                pass

            root_logger.addHandler(console_handler)
            self.handlers['console'] = console_handler

        elif destination == "file":
            # File handler with rotation
            log_dir = Path(self.config.log_directory)
            log_dir.mkdir(parents=True, exist_ok=True)

            main_log_file = log_dir / f"{self.config.app_name.lower()}.log"
            error_log_file = log_dir / "error.log"

            # Main file handler
            main_handler = logging.handlers.TimedRotatingFileHandler(
                filename=main_log_file,
                when="midnight",
                interval=1,
                backupCount=self.config.backup_count,
                encoding="utf-8"
            )
            main_handler.setLevel(logging.DEBUG)
            main_handler.setFormatter(formatter)
            main_handler.suffix = "%Y-%m-%d"
            root_logger.addHandler(main_handler)

            # Error file handler
            error_handler = logging.handlers.TimedRotatingFileHandler(
                filename=error_log_file,
                when="midnight",
                interval=1,
                backupCount=self.config.backup_count,
                encoding="utf-8"
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            error_handler.suffix = "%Y-%m-%d"
            root_logger.addHandler(error_handler)

            self.handlers['file'] = main_handler
            self.handlers['error_file'] = error_handler

        elif destination == "database":
            # Database handler
            db_path = Path(self.config.log_directory) / f"{self.config.app_name.lower()}_logs.db"
            db_handler = DatabaseLogHandler(str(db_path))
            db_handler.setLevel(logging.DEBUG)
            root_logger.addHandler(db_handler)
            self.handlers['database'] = db_handler

    def _suppress_noisy_loggers(self):
        """Suppress noisy third-party loggers"""
        noisy_loggers = [
            'urllib3', 'requests', 'httpx', 'httpcore', 'asyncio',
            'watchdog', 'sqlalchemy.engine', 'websockets'
        ]

        for logger_name in noisy_loggers:
            logging.getLogger(logger_name).setLevel(logging.WARNING)

    def get_logger(self, name: str) -> StructuredLogger:
        """Get or create a structured logger"""
        if name not in self.loggers:
            logger = StructuredLogger(name)
            logger.setLevel(logging.DEBUG)  # Let handlers filter

            # Add trace context to all log records
            def makeRecord(self, name, level, fn, lno, msg, args, exc_info, func=None, extra=None, sinfo=None):
                rv = StructuredLogRecord(name, level, fn, lno, msg, args, exc_info, func, extra, sinfo)
                # Add current trace context
                context = TraceContext.get_current_context()
                if context['trace_id']:
                    rv.trace_id = context['trace_id']
                if context['span_id']:
                    rv.span_id = context['span_id']
                return rv

            logger.makeRecord = makeRecord.__get__(logger, StructuredLogger)
            self.loggers[name] = logger

        return self.loggers[name]

    def log_performance(self, operation: str, duration: float, metadata: Dict = None):
        """Log performance metric"""
        logger = self.get_logger("performance")
        extra = {
            'performance_data': {
                'operation': operation,
                'duration_ms': duration,
                **(metadata or {})
            }
        }
        logger.log(LogLevel.PERFORMANCE.value, f"Performance: {operation}", extra=extra)

    def log_security_event(self, event: str, severity: str = "INFO", context: Dict = None):
        """Log security event"""
        logger = self.get_logger("security")
        extra = {
            'security_context': {
                'event': event,
                'severity': severity,
                **(context or {})
            }
        }
        logger.log(LogLevel.SECURITY.value, f"Security: {event}", extra=extra)

    def log_audit(self, action: str, user: str = None, resource: str = None, details: Dict = None):
        """Log audit event"""
        logger = self.get_logger("audit")
        extra = {
            'structured_data': {
                'action': action,
                'user': user,
                'resource': resource,
                'timestamp': datetime.now().isoformat(),
                **(details or {})
            }
        }
        logger.log(LogLevel.AUDIT.value, f"Audit: {action}", extra=extra)

    def get_metrics(self) -> Dict:
        """Get collected performance metrics"""
        return self.metrics_handler.get_metrics()

    def clear_metrics(self):
        """Clear collected metrics"""
        self.metrics_handler.clear_metrics()

    def shutdown(self):
        """Shutdown logging system"""
        for handler in self._shutdown_handlers:
            try:
                handler()
            except Exception:
                pass

        # Close all handlers
        for handler in self.handlers.values():
            try:
                handler.close()
            except Exception:
                pass

        logging.shutdown()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Global instance
_logging_system = UnifiedLoggingSystem()

def configure_logging(config: Union[LogConfig, Dict] = None):
    """Configure the unified logging system"""
    if config is None:
        config = LogConfig()
    _logging_system.configure(config)

def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance"""
    return _logging_system.get_logger(name)

def log_performance(operation: str, duration: float, metadata: Dict = None):
    """Log performance metric"""
    _logging_system.log_performance(operation, duration, metadata)

def log_security_event(event: str, severity: str = "INFO", context: Dict = None):
    """Log security event"""
    _logging_system.log_security_event(event, severity, context)

def log_audit(action: str, user: str = None, resource: str = None, details: Dict = None):
    """Log audit event"""
    _logging_system.log_audit(action, user, resource, details)

@contextmanager
def performance_timer(operation: str, logger_name: str = None):
    """Context manager for timing operations"""
    start_time = time.time()
    try:
        yield
    finally:
        duration = (time.time() - start_time) * 1000  # Convert to milliseconds
        log_performance(operation, duration, {'logger': logger_name})

def trace_function(func: Callable) -> Callable:
    """Decorator to add tracing to functions"""
    def wrapper(*args, **kwargs):
        func_name = f"{func.__module__}.{func.__qualname__}"
        with trace_context(f"function_{func_name}"):
            return func(*args, **kwargs)
    return wrapper

# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================

# Add custom log levels
logging.addLevelName(LogLevel.SECURITY.value, "SECURITY")
logging.addLevelName(LogLevel.PERFORMANCE.value, "PERFORMANCE")
logging.addLevelName(LogLevel.AUDIT.value, "AUDIT")

# Auto-configure on import
configure_logging()