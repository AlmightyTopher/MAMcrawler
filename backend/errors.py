"""
Standardized Error Handling for Audiobook Automation API

This module provides:
- Custom exception classes for specific error scenarios
- Standardized error response format
- Error code enumeration
- Global exception handler integration

All API errors follow this format:
{
    "error": "error_code",
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "status_code": 400,
    "detail": "Additional context",
    "timestamp": "2025-11-25T12:34:56.789012",
    "request_id": "unique-request-id"
}
"""

from enum import Enum
from typing import Optional, Any, Dict
from fastapi import HTTPException, status
from pydantic import BaseModel
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """
    Enumeration of all error codes used in the API
    Format: snake_case for code values
    """

    # ============================================================================
    # Client Errors (4xx)
    # ============================================================================

    # 400 - Bad Request
    VALIDATION_ERROR = "validation_error"
    INVALID_INPUT = "invalid_input"
    MALFORMED_REQUEST = "malformed_request"
    MISSING_FIELD = "missing_field"

    # 401 - Unauthorized
    UNAUTHORIZED = "unauthorized"
    INVALID_CREDENTIALS = "invalid_credentials"
    INVALID_TOKEN = "invalid_token"
    TOKEN_EXPIRED = "token_expired"
    NO_AUTHENTICATION = "no_authentication"

    # 403 - Forbidden
    FORBIDDEN = "forbidden"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"
    ACCESS_DENIED = "access_denied"

    # 404 - Not Found
    NOT_FOUND = "not_found"
    RESOURCE_NOT_FOUND = "resource_not_found"
    ENDPOINT_NOT_FOUND = "endpoint_not_found"

    # 409 - Conflict
    CONFLICT = "conflict"
    DUPLICATE_RESOURCE = "duplicate_resource"
    RESOURCE_EXISTS = "resource_exists"

    # 429 - Too Many Requests
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    TOO_MANY_REQUESTS = "too_many_requests"

    # 422 - Unprocessable Entity
    UNPROCESSABLE_ENTITY = "unprocessable_entity"

    # ============================================================================
    # Server Errors (5xx)
    # ============================================================================

    # 500 - Internal Server Error
    INTERNAL_ERROR = "internal_error"
    INTERNAL_SERVER_ERROR = "internal_server_error"
    UNKNOWN_ERROR = "unknown_error"

    # 502 - Bad Gateway
    BAD_GATEWAY = "bad_gateway"
    UPSTREAM_ERROR = "upstream_error"

    # 503 - Service Unavailable
    SERVICE_UNAVAILABLE = "service_unavailable"
    MAINTENANCE = "maintenance"

    # ============================================================================
    # Application-Specific Errors
    # ============================================================================

    # Database errors
    DATABASE_ERROR = "database_error"
    DATABASE_CONNECTION_ERROR = "database_connection_error"
    TRANSACTION_FAILED = "transaction_failed"

    # External API errors
    EXTERNAL_API_ERROR = "external_api_error"
    AUDIOBOOKSHELF_ERROR = "audiobookshelf_error"
    QBITTORRENT_ERROR = "qbittorrent_error"
    MAM_CRAWL_ERROR = "mam_crawl_error"

    # Processing errors
    PROCESSING_ERROR = "processing_error"
    DOWNLOAD_FAILED = "download_failed"
    METADATA_ERROR = "metadata_error"
    ASYNC_TASK_FAILED = "async_task_failed"


class ErrorDetail(BaseModel):
    """
    Standardized error response model
    Returned by all error endpoints
    """

    error: str  # Error code (e.g., "validation_error")
    code: str  # Uppercase code (e.g., "VALIDATION_ERROR")
    message: str  # Human-readable message
    status_code: int  # HTTP status code
    detail: Optional[str] = None  # Additional context
    context: Optional[Dict[str, Any]] = None  # Debug context (omitted in production)
    timestamp: str  # ISO format timestamp
    request_id: Optional[str] = None  # Request tracking ID

    class Config:
        schema_extra = {
            "example": {
                "error": "validation_error",
                "code": "VALIDATION_ERROR",
                "message": "Invalid input provided",
                "status_code": 400,
                "detail": "Field 'email' is required",
                "timestamp": "2025-11-25T12:34:56.789012",
                "request_id": "req_12345abcde"
            }
        }


class AppException(HTTPException):
    """
    Base application exception for all custom errors

    Usage:
        raise AppException(
            code=ErrorCode.VALIDATION_ERROR,
            message="Invalid email format",
            status_code=400,
            detail="Email must be valid RFC 5322 format"
        )
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int,
        detail: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.error_code = code
        self.message = message
        self.detail_text = detail
        self.context = context
        self.status_code = status_code

        # Format error detail for HTTPException
        self.detail = {
            "code": code.value,
            "message": message,
            "status_code": status_code,
            "detail": detail,
            "context": context
        }

        super().__init__(status_code=status_code, detail=self.detail)

    def to_error_detail(self, request_id: Optional[str] = None) -> ErrorDetail:
        """Convert to ErrorDetail response model"""
        return ErrorDetail(
            error=self.error_code.value,
            code=self.error_code.value.upper(),
            message=self.message,
            status_code=self.status_code,
            detail=self.detail_text,
            context=self.context,
            timestamp=datetime.utcnow().isoformat(),
            request_id=request_id
        )


# ============================================================================
# Specific Exception Classes
# ============================================================================

class ValidationError(AppException):
    """Raised when input validation fails"""

    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=message or "Validation failed",
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class UnauthorizedError(AppException):
    """Raised when authentication fails"""

    def __init__(self, message: str = "Unauthorized", detail: Optional[str] = None):
        super().__init__(
            code=ErrorCode.UNAUTHORIZED,
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail or "Authentication required"
        )


class ForbiddenError(AppException):
    """Raised when user lacks permission"""

    def __init__(self, message: str = "Forbidden", detail: Optional[str] = None):
        super().__init__(
            code=ErrorCode.FORBIDDEN,
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail or "Insufficient permissions"
        )


class NotFoundError(AppException):
    """Raised when resource doesn't exist"""

    def __init__(self, resource: str, identifier: str = ""):
        detail = f"{resource} not found"
        if identifier:
            detail += f": {identifier}"

        super().__init__(
            code=ErrorCode.NOT_FOUND,
            message="Resource not found",
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class ConflictError(AppException):
    """Raised when resource already exists"""

    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(
            code=ErrorCode.CONFLICT,
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )


class RateLimitError(AppException):
    """Raised when rate limit exceeded"""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message="Too many requests",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Please retry after {retry_after} seconds",
            context={"retry_after": retry_after}
        )


class InternalError(AppException):
    """Raised for unexpected server errors"""

    def __init__(self, message: str = "Internal server error", detail: Optional[str] = None):
        super().__init__(
            code=ErrorCode.INTERNAL_ERROR,
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


class DatabaseError(AppException):
    """Raised for database operation failures"""

    def __init__(self, message: str = "Database error", detail: Optional[str] = None):
        super().__init__(
            code=ErrorCode.DATABASE_ERROR,
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


class ExternalAPIError(AppException):
    """Raised when external API call fails"""

    def __init__(self, api_name: str, message: str = "External API error"):
        super().__init__(
            code=ErrorCode.EXTERNAL_API_ERROR,
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{api_name} API request failed"
        )


# ============================================================================
# Error Handling Utilities
# ============================================================================

def create_error_response(
    error_code: ErrorCode,
    message: str,
    status_code: int,
    detail: Optional[str] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized error response dictionary

    Args:
        error_code: ErrorCode enum value
        message: Human-readable message
        status_code: HTTP status code
        detail: Optional additional detail
        request_id: Optional request tracking ID

    Returns:
        Dictionary with standardized error format
    """
    return {
        "error": error_code.value,
        "code": error_code.value.upper(),
        "message": message,
        "status_code": status_code,
        "detail": detail,
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": request_id
    }


def log_error(
    error_code: ErrorCode,
    message: str,
    request_id: Optional[str] = None,
    exc_info: bool = False
) -> None:
    """
    Log an error with standardized format

    Args:
        error_code: ErrorCode enum value
        message: Message to log
        request_id: Optional request ID for tracking
        exc_info: Whether to include exception traceback
    """
    log_message = f"[{error_code.value}] {message}"
    if request_id:
        log_message += f" (request_id={request_id})"

    if exc_info:
        logger.exception(log_message)
    else:
        logger.error(log_message)
