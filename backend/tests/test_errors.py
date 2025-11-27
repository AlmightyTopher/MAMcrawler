"""
Unit tests for error handling framework

Tests:
- Error code enumeration
- Custom exception classes
- Error response formatting
"""

import pytest
from typing import Optional
from datetime import datetime

from backend.errors import (
    ErrorCode,
    AppException,
    ValidationError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    ConflictError,
    RateLimitError,
    InternalError,
    DatabaseError,
    ExternalAPIError
)


class TestErrorCodeEnum:
    """Test ErrorCode enumeration"""

    def test_error_codes_defined(self):
        """Test that error codes are properly defined"""
        assert hasattr(ErrorCode, "VALIDATION_ERROR")
        assert hasattr(ErrorCode, "UNAUTHORIZED")
        assert hasattr(ErrorCode, "NOT_FOUND")
        assert hasattr(ErrorCode, "CONFLICT")
        assert hasattr(ErrorCode, "RATE_LIMIT_EXCEEDED")
        assert hasattr(ErrorCode, "DATABASE_ERROR")
        assert hasattr(ErrorCode, "INTERNAL_ERROR")

    def test_error_code_values(self):
        """Test error code string values"""
        assert ErrorCode.VALIDATION_ERROR.value == "validation_error"
        assert ErrorCode.UNAUTHORIZED.value == "unauthorized"
        assert ErrorCode.NOT_FOUND.value == "not_found"
        assert ErrorCode.CONFLICT.value == "conflict"
        assert ErrorCode.RATE_LIMIT_EXCEEDED.value == "rate_limit_exceeded"
        assert ErrorCode.DATABASE_ERROR.value == "database_error"
        assert ErrorCode.INTERNAL_ERROR.value == "internal_error"

    def test_error_codes_are_strings(self):
        """Test that all error codes are string enum members"""
        for code in ErrorCode:
            assert isinstance(code.value, str)
            assert len(code.value) > 0

    def test_error_code_count(self):
        """Test that a reasonable number of error codes are defined"""
        error_codes = list(ErrorCode)
        # Should have at least 20 error codes
        assert len(error_codes) >= 20

    def test_error_codes_unique(self):
        """Test that all error codes have unique values"""
        codes = [code.value for code in ErrorCode]
        assert len(codes) == len(set(codes))


class TestValidationError:
    """Test ValidationError exception"""

    def test_validation_error_creation(self):
        """Test creating ValidationError"""
        exc = ValidationError(message="Invalid email format")
        assert exc.message == "Invalid email format"
        assert exc.status_code == 400

    def test_validation_error_status_code(self):
        """Test ValidationError has correct HTTP status code"""
        exc = ValidationError("Invalid data")
        # 400 Bad Request
        assert exc.status_code == 400

    def test_validation_error_is_exception(self):
        """Test ValidationError is an exception"""
        exc = ValidationError("Test error")
        assert isinstance(exc, Exception)


class TestUnauthorizedError:
    """Test UnauthorizedError exception"""

    def test_unauthorized_error_creation(self):
        """Test creating UnauthorizedError"""
        exc = UnauthorizedError(message="Invalid API key")
        assert exc.message == "Invalid API key"
        assert exc.status_code == 401

    def test_unauthorized_error_status_code(self):
        """Test UnauthorizedError has correct HTTP status code"""
        exc = UnauthorizedError("Missing token")
        # 401 Unauthorized
        assert exc.status_code == 401

    def test_unauthorized_error_is_exception(self):
        """Test UnauthorizedError is an exception"""
        exc = UnauthorizedError("Test error")
        assert isinstance(exc, Exception)


class TestForbiddenError:
    """Test ForbiddenError exception"""

    def test_forbidden_error_creation(self):
        """Test creating ForbiddenError"""
        exc = ForbiddenError(message="Insufficient permissions")
        assert exc.message == "Insufficient permissions"
        assert exc.status_code == 403

    def test_forbidden_error_status_code(self):
        """Test ForbiddenError has correct HTTP status code"""
        exc = ForbiddenError("Admin access required")
        # 403 Forbidden
        assert exc.status_code == 403

    def test_forbidden_error_is_exception(self):
        """Test ForbiddenError is an exception"""
        exc = ForbiddenError("Test forbidden")
        assert isinstance(exc, Exception)


class TestNotFoundError:
    """Test NotFoundError exception"""

    def test_not_found_error_creation(self):
        """Test creating NotFoundError"""
        exc = NotFoundError("User", "123")
        assert exc.status_code == 404
        assert "not found" in exc.message

    def test_not_found_error_status_code(self):
        """Test NotFoundError has correct HTTP status code"""
        exc = NotFoundError("Book")
        # 404 Not Found
        assert exc.status_code == 404

    def test_not_found_error_is_exception(self):
        """Test NotFoundError is an exception"""
        exc = NotFoundError("Resource")
        assert isinstance(exc, Exception)


class TestConflictError:
    """Test ConflictError exception"""

    def test_conflict_error_creation(self):
        """Test creating ConflictError"""
        exc = ConflictError(message="Email already exists")
        assert exc.message == "Email already exists"
        assert exc.status_code == 409

    def test_conflict_error_status_code(self):
        """Test ConflictError has correct HTTP status code"""
        exc = ConflictError("Duplicate entry")
        # 409 Conflict
        assert exc.status_code == 409

    def test_conflict_error_is_exception(self):
        """Test ConflictError is an exception"""
        exc = ConflictError("Resource conflict")
        assert isinstance(exc, Exception)


class TestRateLimitError:
    """Test RateLimitError exception"""

    def test_rate_limit_error_creation(self):
        """Test creating RateLimitError"""
        exc = RateLimitError(retry_after=60)
        assert exc.status_code == 429
        assert "Too many requests" in exc.message

    def test_rate_limit_error_status_code(self):
        """Test RateLimitError has correct HTTP status code"""
        exc = RateLimitError()
        # 429 Too Many Requests
        assert exc.status_code == 429

    def test_rate_limit_error_is_exception(self):
        """Test RateLimitError is an exception"""
        exc = RateLimitError(30)
        assert isinstance(exc, Exception)


class TestInternalError:
    """Test InternalError exception"""

    def test_internal_error_creation(self):
        """Test creating InternalError"""
        exc = InternalError(message="Unexpected error occurred")
        assert exc.message == "Unexpected error occurred"
        assert exc.status_code == 500

    def test_internal_error_status_code(self):
        """Test InternalError has correct HTTP status code"""
        exc = InternalError("Server error")
        # 500 Internal Server Error
        assert exc.status_code == 500

    def test_internal_error_is_exception(self):
        """Test InternalError is an exception"""
        exc = InternalError("Database connection failed")
        assert isinstance(exc, Exception)


class TestDatabaseError:
    """Test DatabaseError exception"""

    def test_database_error_creation(self):
        """Test creating DatabaseError"""
        exc = DatabaseError(message="Query execution failed")
        assert exc.message == "Query execution failed"
        assert exc.status_code == 500

    def test_database_error_status_code(self):
        """Test DatabaseError returns server error status"""
        exc = DatabaseError("Connection timeout")
        assert exc.status_code == 500

    def test_database_error_is_exception(self):
        """Test DatabaseError is an exception"""
        exc = DatabaseError("Query failed")
        assert isinstance(exc, Exception)


class TestExternalAPIError:
    """Test ExternalAPIError exception"""

    def test_external_api_error_creation(self):
        """Test creating ExternalAPIError"""
        exc = ExternalAPIError(message="Google Books API unavailable", api_name="Google Books")
        assert exc.message == "Google Books API unavailable"
        assert exc.status_code == 502

    def test_external_api_error_status_code(self):
        """Test ExternalAPIError returns bad gateway status"""
        exc = ExternalAPIError("MAM API timeout", "MAM")
        # 502 Bad Gateway
        assert exc.status_code == 502

    def test_external_api_error_is_exception(self):
        """Test ExternalAPIError is an exception"""
        exc = ExternalAPIError("Service unavailable", "Service")
        assert isinstance(exc, Exception)


class TestExceptionHierarchy:
    """Test exception hierarchy and inheritance"""

    def test_all_errors_are_exceptions(self):
        """Test that all custom errors are Python exceptions"""
        exceptions = [
            ValidationError("test"),
            UnauthorizedError("test"),
            ForbiddenError("test"),
            NotFoundError("test"),
            ConflictError("test"),
            RateLimitError(),
            InternalError("test"),
            DatabaseError("test"),
            ExternalAPIError("test", "service")
        ]
        for exc in exceptions:
            assert isinstance(exc, Exception)

    def test_all_exceptions_have_status_code(self):
        """Test that all exceptions have appropriate HTTP status codes"""
        exceptions = [
            (ValidationError("test"), 400),
            (UnauthorizedError("test"), 401),
            (ForbiddenError("test"), 403),
            (NotFoundError("test"), 404),
            (ConflictError("test"), 409),
            (RateLimitError(), 429),
            (InternalError("test"), 500),
            (DatabaseError("test"), 500),
            (ExternalAPIError("test", "service"), 502)
        ]
        for exc, expected_code in exceptions:
            assert exc.status_code == expected_code
            assert isinstance(exc.status_code, int)

    def test_all_exceptions_have_message(self):
        """Test that all exceptions have a message attribute"""
        exceptions = [
            ValidationError("validation failed"),
            UnauthorizedError("unauthorized access"),
            ForbiddenError("forbidden resource"),
            NotFoundError("resource"),
            ConflictError("conflict detected"),
            RateLimitError(),
            InternalError("internal error"),
            DatabaseError("database error"),
            ExternalAPIError("api error", "service")
        ]
        for exc in exceptions:
            assert hasattr(exc, "message")
            assert exc.message is not None
            assert len(exc.message) > 0
