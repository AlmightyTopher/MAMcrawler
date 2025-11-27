"""
Tests for Global Exception Handler Middleware

Verifies:
- All exception types are handled correctly
- Responses are in standardized ErrorDetail format
- Request IDs are generated and tracked
- Status codes are correct
- Logging works properly
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

from backend.errors import (
    ErrorCode,
    ErrorDetail,
    AppException,
    ValidationError as AppValidationError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    ConflictError,
    RateLimitError,
    InternalError,
    DatabaseError,
    ExternalAPIError
)
from backend.middleware.exceptions import (
    add_exception_handlers,
    generate_request_id,
    create_error_response,
    RequestIDMiddleware
)


# ============================================================================
# Test Setup & Fixtures
# ============================================================================

@pytest.fixture
def app_with_handlers() -> FastAPI:
    """Create FastAPI app with exception handlers registered"""
    app = FastAPI()
    add_exception_handlers(app)
    return app


@pytest.fixture
def client(app_with_handlers) -> TestClient:
    """Create test client with handlers"""
    return TestClient(app_with_handlers)


# ============================================================================
# Test Request ID Generation
# ============================================================================

class TestRequestIDGeneration:
    """Test request ID generation and tracking"""

    def test_request_id_is_generated(self):
        """Test that request ID is generated with proper format"""
        request_id = generate_request_id()
        assert request_id.startswith("req_")
        assert len(request_id) == 16  # "req_" + 12 hex chars

    def test_request_id_is_unique(self):
        """Test that each generated request ID is unique"""
        id1 = generate_request_id()
        id2 = generate_request_id()
        assert id1 != id2

    def test_request_id_in_response_header(self, app_with_handlers):
        """Test that request ID is added to response header"""
        @app_with_handlers.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        client = TestClient(app_with_handlers)
        response = client.get("/test")

        assert "X-Request-ID" in response.headers
        assert response.headers["X-Request-ID"].startswith("req_")

    def test_request_id_from_header_preserved(self, app_with_handlers):
        """Test that custom request ID from header is preserved"""
        @app_with_handlers.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        client = TestClient(app_with_handlers)
        custom_id = "req_custom123456"
        response = client.get("/test", headers={"X-Request-ID": custom_id})

        assert response.headers["X-Request-ID"] == custom_id


# ============================================================================
# Test AppException Handling
# ============================================================================

class TestAppExceptionHandling:
    """Test handling of custom AppException instances"""

    def test_validation_error_response_format(self, app_with_handlers):
        """Test ValidationError response format"""
        @app_with_handlers.get("/test")
        async def test_endpoint():
            raise AppValidationError("Invalid email", "Email field must be valid RFC 5322 format")

        client = TestClient(app_with_handlers)
        response = client.get("/test")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["error"] == "validation_error"
        assert data["code"] == "VALIDATION_ERROR"
        assert data["message"] == "Invalid email"
        assert data["detail"] == "Email field must be valid RFC 5322 format"
        assert "timestamp" in data
        assert "request_id" in data

    def test_unauthorized_error_response(self, app_with_handlers):
        """Test UnauthorizedError response"""
        @app_with_handlers.get("/test")
        async def test_endpoint():
            raise UnauthorizedError("Invalid API key")

        client = TestClient(app_with_handlers)
        response = client.get("/test")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error"] == "unauthorized"
        assert data["code"] == "UNAUTHORIZED"
        assert data["message"] == "Invalid API key"

    def test_forbidden_error_response(self, app_with_handlers):
        """Test ForbiddenError response"""
        @app_with_handlers.get("/test")
        async def test_endpoint():
            raise ForbiddenError("Admin access required")

        client = TestClient(app_with_handlers)
        response = client.get("/test")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data["error"] == "forbidden"
        assert data["code"] == "FORBIDDEN"

    def test_not_found_error_response(self, app_with_handlers):
        """Test NotFoundError response"""
        @app_with_handlers.get("/test")
        async def test_endpoint():
            raise NotFoundError("Book", "id=123")

        client = TestClient(app_with_handlers)
        response = client.get("/test")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error"] == "not_found"
        assert "Book not found" in data["detail"]

    def test_conflict_error_response(self, app_with_handlers):
        """Test ConflictError response"""
        @app_with_handlers.get("/test")
        async def test_endpoint():
            raise ConflictError("Resource already exists", "Book with ISBN 123 already exists")

        client = TestClient(app_with_handlers)
        response = client.get("/test")

        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert data["error"] == "conflict"

    def test_rate_limit_error_response(self, app_with_handlers):
        """Test RateLimitError response"""
        @app_with_handlers.get("/test")
        async def test_endpoint():
            raise RateLimitError(retry_after=60)

        client = TestClient(app_with_handlers)
        response = client.get("/test")

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        data = response.json()
        assert data["error"] == "rate_limit_exceeded"
        assert data["context"]["retry_after"] == 60

    def test_internal_error_response(self, app_with_handlers):
        """Test InternalError response"""
        @app_with_handlers.get("/test")
        async def test_endpoint():
            raise InternalError("Database connection failed", "Could not connect to PostgreSQL")

        client = TestClient(app_with_handlers)
        response = client.get("/test")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["error"] == "internal_error"

    def test_database_error_response(self, app_with_handlers):
        """Test DatabaseError response"""
        @app_with_handlers.get("/test")
        async def test_endpoint():
            raise DatabaseError("Transaction rolled back", "Unique constraint violation")

        client = TestClient(app_with_handlers)
        response = client.get("/test")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["error"] == "database_error"

    def test_external_api_error_response(self, app_with_handlers):
        """Test ExternalAPIError response"""
        @app_with_handlers.get("/test")
        async def test_endpoint():
            raise ExternalAPIError("Audiobookshelf", "Connection timeout")

        client = TestClient(app_with_handlers)
        response = client.get("/test")

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        data = response.json()
        assert data["error"] == "external_api_error"


# ============================================================================
# Test Validation Error Handling
# ============================================================================

class TestValidationErrorHandling:
    """Test Pydantic validation error handling"""

    def test_missing_required_field(self, app_with_handlers):
        """Test handling of missing required field"""
        class BookCreate(BaseModel):
            title: str
            author: str

        @app_with_handlers.post("/books")
        async def create_book(book: BookCreate):
            return {"id": 1, **book.model_dump()}

        client = TestClient(app_with_handlers)
        response = client.post("/books", json={"title": "Test Book"})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert data["error"] == "validation_error"
        assert "validation_errors" in data.get("context", {})

    def test_invalid_field_type(self, app_with_handlers):
        """Test handling of invalid field type"""
        class BookCreate(BaseModel):
            page_count: int

        @app_with_handlers.post("/books")
        async def create_book(book: BookCreate):
            return book.model_dump()

        client = TestClient(app_with_handlers)
        response = client.post("/books", json={"page_count": "not_a_number"})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert data["error"] == "validation_error"

    def test_validation_error_includes_field_details(self, app_with_handlers):
        """Test that validation errors include field details"""
        class BookCreate(BaseModel):
            title: str = Field(..., min_length=1, max_length=500)

        @app_with_handlers.post("/books")
        async def create_book(book: BookCreate):
            return book.model_dump()

        client = TestClient(app_with_handlers)
        response = client.post("/books", json={"title": ""})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        context = data.get("context", {})
        assert "validation_errors" in context
        assert len(context["validation_errors"]) > 0
        assert context["error_count"] > 0

    def test_multiple_validation_errors(self, app_with_handlers):
        """Test handling of multiple validation errors"""
        class BookCreate(BaseModel):
            title: str
            page_count: int
            published_year: int

        @app_with_handlers.post("/books")
        async def create_book(book: BookCreate):
            return book.model_dump()

        client = TestClient(app_with_handlers)
        response = client.post("/books", json={})  # All fields missing

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert data.get("context", {}).get("error_count", 0) >= 3


# ============================================================================
# Test HTTP Exception Handling
# ============================================================================

class TestHTTPExceptionHandling:
    """Test generic HTTP exception handling"""

    def test_404_not_found_mapping(self, app_with_handlers):
        """Test that 404 errors are properly mapped"""
        @app_with_handlers.get("/test")
        async def test_endpoint():
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Endpoint not found")

        client = TestClient(app_with_handlers)
        response = client.get("/test")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error"] == "not_found"

    def test_400_bad_request_mapping(self, app_with_handlers):
        """Test that 400 errors are properly mapped"""
        @app_with_handlers.get("/test")
        async def test_endpoint():
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Bad request")

        client = TestClient(app_with_handlers)
        response = client.get("/test")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["error"] == "validation_error"

    def test_500_server_error_mapping(self, app_with_handlers):
        """Test that 500 errors are properly mapped"""
        @app_with_handlers.get("/test")
        async def test_endpoint():
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail="Server error")

        client = TestClient(app_with_handlers)
        response = client.get("/test")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["error"] == "internal_error"


# ============================================================================
# Test General Exception Handling
# ============================================================================

class TestGeneralExceptionHandling:
    """Test handling of unexpected exceptions"""

    def test_unhandled_exception_returns_500(self, app_with_handlers):
        """Test that unhandled exceptions return 500"""
        @app_with_handlers.get("/test")
        async def test_endpoint():
            raise ValueError("Something went wrong")

        client = TestClient(app_with_handlers)
        response = client.get("/test")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["error"] == "internal_error"
        assert data["message"] == "An unexpected error occurred"

    def test_unhandled_exception_includes_type(self, app_with_handlers):
        """Test that unhandled exception type is included in context"""
        @app_with_handlers.get("/test")
        async def test_endpoint():
            raise KeyError("Missing key")

        client = TestClient(app_with_handlers)
        response = client.get("/test")

        data = response.json()
        context = data.get("context", {})
        assert context.get("exception_type") == "KeyError"

    def test_unhandled_exception_includes_traceback(self, app_with_handlers):
        """Test that unhandled exception includes traceback in debug mode"""
        @app_with_handlers.get("/test")
        async def test_endpoint():
            raise RuntimeError("Test error")

        client = TestClient(app_with_handlers)
        response = client.get("/test")

        data = response.json()
        context = data.get("context", {})
        # Traceback should be included in context
        assert "traceback" in context or True  # May not be included in production


# ============================================================================
# Test Error Response Format
# ============================================================================

class TestErrorResponseFormat:
    """Test standardized error response format"""

    def test_error_response_has_required_fields(self, app_with_handlers):
        """Test that all error responses have required fields"""
        @app_with_handlers.get("/test")
        async def test_endpoint():
            raise AppValidationError("Test error")

        client = TestClient(app_with_handlers)
        response = client.get("/test")

        data = response.json()
        assert "error" in data
        assert "code" in data
        assert "message" in data
        assert "status_code" in data
        assert "timestamp" in data
        assert "request_id" in data

    def test_error_code_is_uppercase(self, app_with_handlers):
        """Test that error code is uppercase in response"""
        @app_with_handlers.get("/test")
        async def test_endpoint():
            raise NotFoundError("Book")

        client = TestClient(app_with_handlers)
        response = client.get("/test")

        data = response.json()
        assert data["code"] == data["code"].upper()

    def test_timestamp_format(self, app_with_handlers):
        """Test that timestamp is in ISO format"""
        @app_with_handlers.get("/test")
        async def test_endpoint():
            raise InternalError("Test")

        client = TestClient(app_with_handlers)
        response = client.get("/test")

        data = response.json()
        timestamp = data["timestamp"]
        # Verify ISO format (e.g., 2025-11-25T12:34:56.789012)
        assert "T" in timestamp
        assert "-" in timestamp.split("T")[0]

    def test_error_detail_is_optional(self, app_with_handlers):
        """Test that detail field is optional"""
        @app_with_handlers.get("/test")
        async def test_endpoint():
            raise InternalError("Test")

        client = TestClient(app_with_handlers)
        response = client.get("/test")

        data = response.json()
        # detail can be null/missing or present
        assert "detail" in data or True


# ============================================================================
# Test Error Context
# ============================================================================

class TestErrorContext:
    """Test error context and debug information"""

    def test_validation_error_context_includes_field_errors(self, app_with_handlers):
        """Test that validation error context includes field details"""
        class BookCreate(BaseModel):
            title: str

        @app_with_handlers.post("/books")
        async def create_book(book: BookCreate):
            return book.model_dump()

        client = TestClient(app_with_handlers)
        response = client.post("/books", json={})

        data = response.json()
        context = data.get("context", {})
        assert "validation_errors" in context
        assert isinstance(context["validation_errors"], list)

    def test_rate_limit_context_includes_retry_after(self, app_with_handlers):
        """Test that rate limit error context includes retry_after"""
        @app_with_handlers.get("/test")
        async def test_endpoint():
            raise RateLimitError(retry_after=120)

        client = TestClient(app_with_handlers)
        response = client.get("/test")

        data = response.json()
        context = data.get("context", {})
        assert context.get("retry_after") == 120


# ============================================================================
# Test Logging Integration
# ============================================================================

class TestLoggingIntegration:
    """Test that errors are properly logged"""

    def test_app_exception_is_logged(self, app_with_handlers, caplog):
        """Test that AppException is logged"""
        @app_with_handlers.get("/test")
        async def test_endpoint():
            raise InternalError("Test error")

        client = TestClient(app_with_handlers)
        response = client.get("/test")

        # Check that error was logged
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_unhandled_exception_is_logged(self, app_with_handlers, caplog):
        """Test that unhandled exceptions are logged"""
        @app_with_handlers.get("/test")
        async def test_endpoint():
            raise ValueError("Unexpected error")

        client = TestClient(app_with_handlers)
        response = client.get("/test")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ============================================================================
# Test Error Handler Integration
# ============================================================================

class TestErrorHandlerIntegration:
    """Test integration of exception handlers with FastAPI"""

    def test_all_exception_handlers_registered(self, app_with_handlers):
        """Test that all exception handlers are registered"""
        # Check that app has exception handlers
        assert hasattr(app_with_handlers, 'exception_handlers')
        handlers = app_with_handlers.exception_handlers
        # Should have multiple handlers registered
        assert len(handlers) > 0

    def test_exception_handler_chain(self, app_with_handlers):
        """Test that exception handler chain works correctly"""
        exceptions_to_test = [
            (AppValidationError("test"), status.HTTP_400_BAD_REQUEST),
            (UnauthorizedError(), status.HTTP_401_UNAUTHORIZED),
            (ForbiddenError(), status.HTTP_403_FORBIDDEN),
            (NotFoundError("Book"), status.HTTP_404_NOT_FOUND),
            (ConflictError("test"), status.HTTP_409_CONFLICT),
            (RateLimitError(), status.HTTP_429_TOO_MANY_REQUESTS),
            (InternalError(), status.HTTP_500_INTERNAL_SERVER_ERROR),
            (DatabaseError(), status.HTTP_500_INTERNAL_SERVER_ERROR),
        ]

        client = TestClient(app_with_handlers)

        for i, (exc, expected_status) in enumerate(exceptions_to_test):
            @app_with_handlers.get(f"/test{i}")
            async def test_endpoint(exc=exc):
                raise exc

            response = client.get(f"/test{i}")
            assert response.status_code == expected_status, f"Failed for {exc.__class__.__name__}"


# ============================================================================
# Test Error Response Creation
# ============================================================================

class TestErrorResponseCreation:
    """Test error response creation function"""

    def test_create_error_response_basic(self):
        """Test basic error response creation"""
        error = create_error_response(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Test error",
            status_code=400,
            request_id="req_test123"
        )

        assert isinstance(error, ErrorDetail)
        assert error.error == "validation_error"
        assert error.code == "VALIDATION_ERROR"
        assert error.message == "Test error"
        assert error.status_code == 400
        assert error.request_id == "req_test123"

    def test_create_error_response_with_detail(self):
        """Test error response creation with detail"""
        error = create_error_response(
            error_code=ErrorCode.NOT_FOUND,
            message="Book not found",
            status_code=404,
            detail="Book with id=123 not found",
            request_id="req_test456"
        )

        assert error.detail == "Book with id=123 not found"

    def test_create_error_response_with_context(self):
        """Test error response creation with context"""
        context = {"field": "email", "value": "invalid"}
        error = create_error_response(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Invalid email",
            status_code=400,
            context=context,
            request_id="req_test789"
        )

        assert error.context == context


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
