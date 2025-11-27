"""
Middleware components for MAMcrawler API

Includes:
- Exception handling (exceptions.py) - NEW global exception handler
- Security headers (middleware_old.py) - LEGACY
- CORS configuration (middleware_old.py) - LEGACY
- Request tracking (exceptions.py) - NEW

This package imports from both the old middleware_old.py (for backward compatibility)
and the new middleware/ subdirectory (for new middleware components).
"""

# Import from the exceptions middleware (new)
from backend.middleware.exceptions import (
    add_exception_handlers,
    RequestIDMiddleware,
    app_exception_handler,
    validation_error_handler,
    http_exception_handler,
    general_exception_handler,
    generate_request_id,
    create_error_response
)

# Import from the old middleware_old.py for backward compatibility
# These are imported here so backend.main can still import from backend.middleware
from backend.middleware_old import (
    SecurityHeadersMiddleware,
    add_cors_middleware,
    verify_api_key,
    validate_file_upload,
    RequestLoggingMiddleware,
    setup_security_middleware
)

__all__ = [
    # New exception handlers
    "add_exception_handlers",
    "RequestIDMiddleware",
    "app_exception_handler",
    "validation_error_handler",
    "http_exception_handler",
    "general_exception_handler",
    "generate_request_id",
    "create_error_response",
    # Old middleware (backward compatibility)
    "SecurityHeadersMiddleware",
    "add_cors_middleware",
    "verify_api_key",
    "validate_file_upload",
    "RequestLoggingMiddleware",
    "setup_security_middleware",
]
