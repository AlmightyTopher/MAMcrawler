"""
Global Exception Handler Middleware for MAMcrawler API

This middleware provides:
- Centralized exception handling for all endpoints
- Standardized error response formatting
- Request tracking with unique IDs
- Proper HTTP status code mapping
- Logging of all errors
- Error context preservation

All exceptions are converted to ErrorDetail format for consistent API responses.

Usage:
    Add to backend/main.py during app initialization:
    from backend.middleware.exceptions import add_exception_handlers
    add_exception_handlers(app)
"""

import logging
import traceback
from typing import Optional, Dict, Any
from uuid import uuid4
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError

from backend.errors import (
    ErrorDetail,
    ErrorCode,
    AppException,
    ValidationError as AppValidationError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    ConflictError,
    RateLimitError,
    InternalError,
    DatabaseError,
    ExternalAPIError,
    log_error
)

logger = logging.getLogger(__name__)


# ============================================================================
# Exception Handler Functions
# ============================================================================

def generate_request_id() -> str:
    """Generate unique request ID for tracking"""
    return f"req_{uuid4().hex[:12]}"


def create_error_response(
    error_code: ErrorCode,
    message: str,
    status_code: int,
    detail: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    include_traceback: bool = False,
    traceback_str: Optional[str] = None
) -> ErrorDetail:
    """
    Create standardized error response

    Args:
        error_code: ErrorCode enum value
        message: Human-readable message
        status_code: HTTP status code
        detail: Optional additional detail
        context: Optional debug context
        request_id: Request tracking ID
        include_traceback: Whether to include traceback in context
        traceback_str: Traceback string if available

    Returns:
        ErrorDetail model instance
    """
    context = context or {}

    # Add traceback to context if available and enabled
    if include_traceback and traceback_str:
        context["traceback"] = traceback_str

    return ErrorDetail(
        error=error_code.value,
        code=error_code.value.upper(),
        message=message,
        status_code=status_code,
        detail=detail,
        context=context if context else None,
        timestamp=datetime.utcnow().isoformat(),
        request_id=request_id
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handle custom AppException instances

    Converts AppException to standardized ErrorDetail response
    """
    request_id = request.state.request_id if hasattr(request.state, 'request_id') else generate_request_id()

    error_response = create_error_response(
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        detail=exc.detail_text,
        context=exc.context,
        request_id=request_id
    )

    # Log the error
    log_error(
        exc.error_code,
        exc.message,
        request_id=request_id,
        exc_info=False
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors from request body/query params

    Converts ValidationError to standardized ErrorDetail response with field details
    """
    request_id = request.state.request_id if hasattr(request.state, 'request_id') else generate_request_id()

    # Extract field errors
    errors = []
    for error in exc.errors():
        errors.append({
            "loc": list(error.get("loc", [])),
            "msg": error.get("msg", "Unknown error"),
            "type": error.get("type", "unknown")
        })

    context = {
        "validation_errors": errors,
        "error_count": len(errors)
    }

    error_response = create_error_response(
        error_code=ErrorCode.VALIDATION_ERROR,
        message="Request validation failed",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="One or more fields failed validation",
        context=context,
        request_id=request_id
    )

    # Log validation errors
    logger.warning(
        f"Validation error: {len(errors)} field(s) failed validation",
        extra={
            "request_id": request_id,
            "errors": errors,
            "path": request.url.path
        }
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump()
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException
) -> JSONResponse:
    """
    Handle generic HTTP exceptions (HTTPException from Starlette)

    Maps HTTP exceptions to appropriate ErrorCode and formats response
    """
    request_id = request.state.request_id if hasattr(request.state, 'request_id') else generate_request_id()

    # Determine error code based on status code
    error_code_map = {
        status.HTTP_400_BAD_REQUEST: ErrorCode.VALIDATION_ERROR,
        status.HTTP_401_UNAUTHORIZED: ErrorCode.UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN: ErrorCode.FORBIDDEN,
        status.HTTP_404_NOT_FOUND: ErrorCode.NOT_FOUND,
        status.HTTP_409_CONFLICT: ErrorCode.CONFLICT,
        status.HTTP_429_TOO_MANY_REQUESTS: ErrorCode.RATE_LIMIT_EXCEEDED,
        status.HTTP_500_INTERNAL_SERVER_ERROR: ErrorCode.INTERNAL_ERROR,
        status.HTTP_502_BAD_GATEWAY: ErrorCode.BAD_GATEWAY,
        status.HTTP_503_SERVICE_UNAVAILABLE: ErrorCode.SERVICE_UNAVAILABLE,
    }

    error_code = error_code_map.get(exc.status_code, ErrorCode.INTERNAL_ERROR)

    # Extract detail from exception
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)

    error_response = create_error_response(
        error_code=error_code,
        message=detail or f"HTTP {exc.status_code}",
        status_code=exc.status_code,
        request_id=request_id
    )

    # Log HTTP exceptions (except 404 which is common)
    if exc.status_code != status.HTTP_404_NOT_FOUND:
        log_error(
            error_code,
            f"HTTP {exc.status_code}: {detail}",
            request_id=request_id
        )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle all unexpected exceptions

    Logs full traceback and returns generic error response
    """
    request_id = request.state.request_id if hasattr(request.state, 'request_id') else generate_request_id()

    # Get traceback
    tb_str = traceback.format_exc()

    context = {
        "exception_type": exc.__class__.__name__,
    }

    error_response = create_error_response(
        error_code=ErrorCode.INTERNAL_ERROR,
        message="An unexpected error occurred",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error",
        context=context,
        request_id=request_id,
        include_traceback=True,
        traceback_str=tb_str
    )

    # Log the full exception with traceback
    logger.exception(
        f"Unhandled exception: {exc.__class__.__name__}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "exception_type": exc.__class__.__name__
        }
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump()
    )


# ============================================================================
# Request ID Middleware
# ============================================================================

from starlette.middleware.base import BaseHTTPMiddleware


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add unique request ID to each request

    Stores request_id in request.state for access in exception handlers
    """

    async def dispatch(self, request: Request, call_next):
        # Generate or extract request ID from header
        request_id = request.headers.get("X-Request-ID", generate_request_id())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ============================================================================
# Exception Handler Registration
# ============================================================================

def add_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers with the FastAPI app

    Should be called during app initialization:
        app = FastAPI()
        add_exception_handlers(app)

    Registers handlers for:
    - AppException (custom application exceptions)
    - RequestValidationError (Pydantic validation errors)
    - HTTPException (Starlette HTTP exceptions)
    - Exception (all unhandled exceptions)

    Also adds RequestIDMiddleware for request tracking
    """

    # Add RequestIDMiddleware first (runs first in middleware stack)
    app.add_middleware(RequestIDMiddleware)

    # Register exception handlers
    # Order matters: more specific handlers should come before general ones

    # 1. Custom application exceptions (AppException and subclasses)
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(AppValidationError, app_exception_handler)
    app.add_exception_handler(UnauthorizedError, app_exception_handler)
    app.add_exception_handler(ForbiddenError, app_exception_handler)
    app.add_exception_handler(NotFoundError, app_exception_handler)
    app.add_exception_handler(ConflictError, app_exception_handler)
    app.add_exception_handler(RateLimitError, app_exception_handler)
    app.add_exception_handler(InternalError, app_exception_handler)
    app.add_exception_handler(DatabaseError, app_exception_handler)
    app.add_exception_handler(ExternalAPIError, app_exception_handler)

    # 2. Pydantic validation errors
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    # 3. Generic HTTP exceptions
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # 4. All unhandled exceptions (catch-all)
    app.add_exception_handler(Exception, general_exception_handler)

    logger.info("Exception handlers registered successfully")


def test_exception_handlers() -> None:
    """
    Test exception handler registration and response formatting

    Usage:
        from backend.middleware.exceptions import test_exception_handlers
        test_exception_handlers()
    """
    # This would typically be called in a test
    import json

    test_cases = [
        {
            "name": "AppException",
            "exc": InternalError("Test error", "Test detail"),
            "expected_code": ErrorCode.INTERNAL_ERROR
        },
        {
            "name": "ValidationError",
            "exc": AppValidationError("Invalid input", "Field 'email' is required"),
            "expected_code": ErrorCode.VALIDATION_ERROR
        },
        {
            "name": "NotFoundError",
            "exc": NotFoundError("Book", "id=123"),
            "expected_code": ErrorCode.NOT_FOUND
        },
    ]

    print("Testing exception handlers...")
    for test_case in test_cases:
        exc = test_case["exc"]
        error_response = create_error_response(
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            detail=exc.detail_text,
            context=exc.context,
            request_id="test_req_123"
        )

        print(f"\n{test_case['name']}:")
        print(json.dumps(error_response.model_dump(), indent=2, default=str))

    print("\nException handler tests completed!")


if __name__ == "__main__":
    test_exception_handlers()
