"""
Comprehensive Exception Handling Framework
Implements proper exception hierarchies, error patterns, and logging throughout the codebase.
"""

import logging
import asyncio
import traceback
import sys
import time
import functools
from typing import Any, Callable, Dict, List, Optional, Type, Union, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
import json
from datetime import datetime, timezone

# Configure logging
logger = logging.getLogger(__name__)

# Type hints
F = TypeVar('F', bound=Callable[..., Any])

class ErrorSeverity(Enum):
    """Error severity levels for proper categorization."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Categories for different types of errors."""
    SECURITY = "security"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    AUDIO_PROCESSING = "audio_processing"
    CRAWLING = "crawling"
    AUTHENTICATION = "authentication"
    API_INTEGRATION = "api_integration"
    VALIDATION = "validation"
    SYSTEM = "system"

@dataclass
class ErrorContext:
    """Context information for error tracking."""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    function_name: str = ""
    module_name: str = ""
    line_number: int = 0
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MAMException(Exception):
    """Base exception for all MAM crawler errors."""
    message: str
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    category: ErrorCategory = ErrorCategory.SYSTEM
    context: Optional[ErrorContext] = None
    cause: Optional[Exception] = None
    recovery_suggestion: Optional[str] = None
    
    def __post_init__(self):
        super().__init__(self.message)
        
        # Auto-populate context if not provided
        if self.context is None:
            frame = sys._getframe(2)  # Go back 2 frames to get the calling function
            self.context = ErrorContext(
                function_name=frame.f_code.co_name,
                module_name=frame.f_code.co_filename,
                line_number=frame.f_lineno
            )

class SecurityException(MAMException):
    """Exception for security-related errors."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, recovery_suggestion: Optional[str] = None):
        super().__init__(
            message=message,
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.SECURITY,
            context=context,
            recovery_suggestion=recovery_suggestion or "Review security configuration and credentials"
        )

class ConfigurationException(MAMException):
    """Exception for configuration-related errors."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, recovery_suggestion: Optional[str] = None):
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.CONFIGURATION,
            context=context,
            recovery_suggestion=recovery_suggestion or "Check configuration files and environment variables"
        )

class NetworkException(MAMException):
    """Exception for network-related errors."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, recovery_suggestion: Optional[str] = None):
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.NETWORK,
            context=context,
            recovery_suggestion=recovery_suggestion or "Check network connectivity and retry"
        )

class AuthenticationException(MAMException):
    """Exception for authentication-related errors."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, recovery_suggestion: Optional[str] = None):
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.AUTHENTICATION,
            context=context,
            recovery_suggestion=recovery_suggestion or "Verify credentials and authentication tokens"
        )

class AudioProcessingException(MAMException):
    """Exception for audio processing errors."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, recovery_suggestion: Optional[str] = None):
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.AUDIO_PROCESSING,
            context=context,
            recovery_suggestion=recovery_suggestion or "Check audio file format and integrity"
        )

class CrawlingException(MAMException):
    """Exception for web crawling errors."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, recovery_suggestion: Optional[str] = None):
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.CRAWLING,
            context=context,
            recovery_suggestion=recovery_suggestion or "Check URL accessibility and retry with different parameters"
        )

class ValidationException(MAMException):
    """Exception for validation errors."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, recovery_suggestion: Optional[str] = None):
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.VALIDATION,
            context=context,
            recovery_suggestion=recovery_suggestion or "Check input data format and constraints"
        )

class ErrorHandler:
    """Centralized error handling with logging and recovery."""
    
    def __init__(self, logger_name: str = "MAM_Crawler"):
        self.logger = logging.getLogger(logger_name)
        self.error_counts: Dict[str, int] = {}
        self.last_errors: List[Dict[str, Any]] = []
        self.max_error_history = 1000
    
    def log_error(self, error: Exception, context: Optional[ErrorContext] = None) -> Dict[str, Any]:
        """Log error with comprehensive context."""
        
        # Determine error type and severity
        if isinstance(error, MAMException):
            error_type = type(error).__name__
            severity = error.severity.value
            category = error.category.value
            message = error.message
            recovery = error.recovery_suggestion
            error_context = error.context or context
        else:
            error_type = type(error).__name__
            severity = "unknown"
            category = "system"
            message = str(error)
            recovery = "Contact support"
            error_context = context
        
        # Create error log entry
        error_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error_type': error_type,
            'severity': severity,
            'category': category,
            'message': message,
            'recovery_suggestion': recovery,
            'context': {
                'function_name': error_context.function_name if error_context else 'unknown',
                'module_name': error_context.module_name if error_context else 'unknown',
                'line_number': error_context.line_number if error_context else 0,
                'additional_data': error_context.additional_data if error_context else {}
            },
            'stack_trace': traceback.format_exc() if isinstance(error, Exception) else None
        }
        
        # Add to error history
        self.last_errors.append(error_entry)
        if len(self.last_errors) > self.max_error_history:
            self.last_errors = self.last_errors[-self.max_error_history:]
        
        # Update error counts
        error_key = f"{category}:{error_type}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Log based on severity
        log_message = f"[{severity.upper()}] {category}: {message}"
        if error_context:
            log_message += f" in {error_context.function_name} ({error_context.module_name}:{error_context.line_number})"
        
        if severity == "critical":
            self.logger.critical(log_message, exc_info=True)
        elif severity == "high":
            self.logger.error(log_message, exc_info=True)
        elif severity == "medium":
            self.logger.warning(log_message, exc_info=True)
        else:
            self.logger.info(log_message, exc_info=True)
        
        return error_entry
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent errors."""
        return {
            'total_errors': len(self.last_errors),
            'error_counts': self.error_counts,
            'recent_errors': self.last_errors[-10:],  # Last 10 errors
            'summary_timestamp': datetime.now(timezone.utc).isoformat()
        }

# Global error handler instance
_global_error_handler = ErrorHandler()

def handle_exceptions(logger_name: str = "MAM_Crawler", reraise: bool = True, 
                     fallback_return: Any = None):
    """Decorator for comprehensive exception handling."""
    error_handler = ErrorHandler(logger_name)
    
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Log the error
                error_handler.log_error(e)
                
                # Reraise or return fallback
                if reraise:
                    raise
                return fallback_return
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Log the error
                error_handler.log_error(e)
                
                # Reraise or return fallback
                if reraise:
                    raise
                return fallback_return
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper
    
    return decorator

@asynccontextmanager
async def exception_context(error_category: ErrorCategory = ErrorCategory.SYSTEM,
                          recovery_suggestion: Optional[str] = None):
    """Context manager for consistent exception handling."""
    try:
        yield
    except MAMException as e:
        # Already a MAM exception, just log and reraise
        _global_error_handler.log_error(e)
        raise
    except Exception as e:
        # Convert to MAM exception based on category
        context = ErrorContext(
            function_name=sys._getframe().f_back.f_code.co_name,
            module_name=sys._getframe().f_back.f_code.co_filename,
            line_number=sys._getframe().f_back.f_lineno
        )
        
        # Create appropriate exception based on category
        exception_map = {
            ErrorCategory.SECURITY: SecurityException,
            ErrorCategory.CONFIGURATION: ConfigurationException,
            ErrorCategory.NETWORK: NetworkException,
            ErrorCategory.AUTHENTICATION: AuthenticationException,
            ErrorCategory.AUDIO_PROCESSING: AudioProcessingException,
            ErrorCategory.CRAWLING: CrawlingException,
            ErrorCategory.VALIDATION: ValidationException,
        }
        
        ExceptionClass = exception_map.get(error_category, MAMException)
        mam_exception = ExceptionClass(
            message=f"{error_category.value.title()} error: {str(e)}",
            context=context,
            recovery_suggestion=recovery_suggestion,
            cause=e
        )
        
        # Log and raise
        _global_error_handler.log_error(mam_exception)
        raise mam_exception

def validate_input(data: Any, validation_rules: Dict[str, Any], 
                  error_message: str = "Input validation failed") -> None:
    """Validate input data with comprehensive error handling."""
    try:
        for field, rule in validation_rules.items():
            value = data.get(field) if isinstance(data, dict) else getattr(data, field, None)
            
            # Type validation
            if 'type' in rule:
                expected_type = rule['type']
                if not isinstance(value, expected_type):
                    raise ValidationException(
                        f"{field}: expected {expected_type.__name__}, got {type(value).__name__}",
                        recovery_suggestion=f"Ensure {field} is of type {expected_type.__name__}"
                    )
            
            # Required field validation
            if rule.get('required', False) and value is None:
                raise ValidationException(
                    f"{field}: required field is missing",
                    recovery_suggestion=f"Provide a value for the required field: {field}"
                )
            
            # String validation
            if isinstance(value, str):
                if 'min_length' in rule and len(value) < rule['min_length']:
                    raise ValidationException(
                        f"{field}: minimum length is {rule['min_length']}, got {len(value)}",
                        recovery_suggestion=f"Ensure {field} has at least {rule['min_length']} characters"
                    )
                if 'max_length' in rule and len(value) > rule['max_length']:
                    raise ValidationException(
                        f"{field}: maximum length is {rule['max_length']}, got {len(value)}",
                        recovery_suggestion=f"Ensure {field} has no more than {rule['max_length']} characters"
                    )
                if 'pattern' in rule and not rule['pattern'].match(value):
                    raise ValidationException(
                        f"{field}: does not match required pattern",
                        recovery_suggestion=f"Ensure {field} matches the required format"
                    )
            
            # Numeric validation
            if isinstance(value, (int, float)):
                if 'min_value' in rule and value < rule['min_value']:
                    raise ValidationException(
                        f"{field}: minimum value is {rule['min_value']}, got {value}",
                        recovery_suggestion=f"Ensure {field} is at least {rule['min_value']}"
                    )
                if 'max_value' in rule and value > rule['max_value']:
                    raise ValidationException(
                        f"{field}: maximum value is {rule['max_value']}, got {value}",
                        recovery_suggestion=f"Ensure {field} is no more than {rule['max_value']}"
                    )
    
    except ValidationException:
        raise
    except Exception as e:
        raise ValidationException(
            f"Validation error: {str(e)}",
            recovery_suggestion="Check input data format and constraints"
        )

class RetryableOperation:
    """Handles retry logic with exponential backoff and error handling."""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, 
                 max_delay: float = 60.0, backoff_multiplier: float = 2.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
    
    async def execute(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with retry logic."""
        last_exception = None
        
        for attempt in range(1, self.max_attempts + 1):
            try:
                if asyncio.iscoroutinefunction(operation):
                    return await operation(*args, **kwargs)
                else:
                    return operation(*args, **kwargs)
            
            except Exception as e:
                last_exception = e
                
                # Log the attempt
                _global_error_handler.log_error(e)
                
                # If this is the last attempt, raise the exception
                if attempt == self.max_attempts:
                    break
                
                # Calculate delay with exponential backoff
                delay = min(
                    self.base_delay * (self.backoff_multiplier ** (attempt - 1)),
                    self.max_delay
                )
                
                logger.info(f"Attempt {attempt} failed, retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)
        
        # All attempts failed
        raise last_exception

# Example usage functions
async def example_secure_operation():
    """Example of secure operation with proper exception handling."""
    try:
        async with exception_context(
            ErrorCategory.SECURITY,
            "Verify credentials and security configuration"
        ):
            # Simulate security-sensitive operation
            raise ValueError("Invalid security token")
            
    except SecurityException as e:
        logger.error(f"Security operation failed: {e.message}")
        # Handle security error appropriately
        return False

async def example_audio_processing():
    """Example of audio processing with exception handling."""
    try:
        async with exception_context(
            ErrorCategory.AUDIO_PROCESSING,
            "Check audio file format and integrity"
        ):
            # Simulate audio processing
            raise IOError("Cannot read audio file")
            
    except AudioProcessingException as e:
        logger.error(f"Audio processing failed: {e.message}")
        # Handle audio processing error
        return None

if __name__ == "__main__":
    # Example usage
    import asyncio
    
    async def main():
        # Test exception handling
        await example_secure_operation()
        await example_audio_processing()
        
        # Print error summary
        summary = _global_error_handler.get_error_summary()
        print(json.dumps(summary, indent=2))
    
    asyncio.run(main())