"""
Pytest configuration and fixtures for MAMcrawler backend tests

This module provides:
- FastAPI test client setup
- Database session fixtures
- Mock settings configuration
- Common test data factories
- Authentication fixtures

Usage:
    pytest backend/tests -v
    pytest backend/tests --cov=backend --cov-report=html
    pytest backend/tests -k "test_health"
"""

import os
import pytest
import asyncio
from typing import Generator, AsyncGenerator, Optional
from unittest.mock import MagicMock, patch, AsyncMock

# Note: pytest-mock is installed but provides 'mocker' fixture automatically

# FastAPI and database imports
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Application imports
from backend.main import app, create_scheduler
from backend.config import Settings
from backend.database import Base, get_db
from backend.errors import ErrorCode


# ============================================================================
# Database Setup
# ============================================================================

# Use SQLite in-memory for testing (fast, isolated, no external dependencies)
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
TEST_ASYNC_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """
    Create event loop for async tests

    Scope: session - single loop for all async tests
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_settings() -> Settings:
    """
    Create test-specific settings with safe defaults

    Returns:
        Settings: Test configuration with in-memory database and no external services
    """
    settings = Settings(
        # Database
        DATABASE_URL=TEST_SQLALCHEMY_DATABASE_URL,
        DATABASE_ECHO=False,

        # API
        DEBUG=True,
        API_DOCS=True,
        SECURITY_HEADERS=True,

        # Authentication (test values)
        API_KEY="test-api-key-12345",
        SECRET_KEY="test-secret-key-12345",
        PASSWORD_SALT="test-salt-12345",

        # External services (disabled for testing)
        ABS_URL="http://localhost:13378",
        ABS_TOKEN="",
        PROWLARR_URL="http://localhost:9696",
        PROWLARR_API_KEY="",
        GOOGLE_BOOKS_API_KEY="",
        QB_PASSWORD="",

        # Features
        SCHEDULER_ENABLED=False,  # Disable scheduler in tests

        # MAM (test credentials - not real)
        MAM_USERNAME="test_user",
        MAM_PASSWORD="test_password",
    )
    return settings


@pytest.fixture(scope="function")
def db_engine():
    """
    Create SQLAlchemy engine for testing

    Yields:
        Engine: In-memory SQLite engine
    """
    engine = create_engine(
        TEST_SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """
    Create database session for tests

    Yields:
        Session: SQLAlchemy session connected to test database
    """
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()

    yield session

    session.close()


@pytest.fixture(scope="function")
async def async_db_engine():
    """
    Create async SQLAlchemy engine for testing async database operations

    Yields:
        AsyncEngine: In-memory SQLite async engine
    """
    engine = create_async_engine(
        TEST_ASYNC_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False}
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def async_db_session(async_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create async database session for tests

    Yields:
        AsyncSession: SQLAlchemy async session
    """
    AsyncSessionLocal = async_sessionmaker(
        async_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    async with AsyncSessionLocal() as session:
        yield session


# ============================================================================
# FastAPI Test Client
# ============================================================================

@pytest.fixture(scope="function")
def client(test_settings, db_session) -> TestClient:
    """
    Create FastAPI test client with mocked settings and database

    Args:
        test_settings: Test configuration
        db_session: Test database session

    Returns:
        TestClient: FastAPI test client ready for requests
    """
    # Override settings
    with patch("backend.config.get_settings", return_value=test_settings):
        # Override database dependency
        def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        # Create client
        test_client = TestClient(app)

        yield test_client

        # Cleanup
        app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def authenticated_headers(test_settings) -> dict:
    """
    Create HTTP headers with API key authentication

    Args:
        test_settings: Test configuration with API_KEY

    Returns:
        dict: Headers with X-API-Key for authenticated requests
    """
    return {
        "X-API-Key": test_settings.API_KEY,
        "Content-Type": "application/json"
    }


# ============================================================================
# Authentication & Security Fixtures
# ============================================================================

@pytest.fixture
def jwt_token() -> str:
    """
    Create a valid JWT token for testing

    Returns:
        str: Valid JWT token
    """
    from backend.auth import generate_token

    payload = {
        "sub": "test_user",
        "email": "test@example.com",
        "iat": 1234567890
    }
    return generate_token(payload)


@pytest.fixture
def auth_headers(jwt_token) -> dict:
    """
    Create HTTP headers with JWT authentication

    Args:
        jwt_token: Valid JWT token

    Returns:
        dict: Headers with Authorization Bearer token
    """
    return {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }


# ============================================================================
# Mock Data Factories
# ============================================================================

@pytest.fixture
def book_data() -> dict:
    """
    Create sample book data for testing

    Returns:
        dict: Book object with required fields
    """
    return {
        "title": "Test Book Title",
        "author": "Test Author",
        "isbn": "978-0-134-68599-1",
        "published_date": "2023-01-01",
        "description": "A test book description",
        "genres": ["Science Fiction", "Adventure"],
        "page_count": 300,
        "language": "en"
    }


@pytest.fixture
def download_data() -> dict:
    """
    Create sample download/torrent data for testing

    Returns:
        dict: Download object with required fields
    """
    return {
        "title": "Test Audiobook",
        "magnet_link": "magnet:?xt=urn:btih:1234567890abcdef",
        "seeds": 10,
        "leeches": 5,
        "source": "MAM",
        "quality": "320kbps"
    }


@pytest.fixture
def user_data() -> dict:
    """
    Create sample user data for testing

    Returns:
        dict: User object with required fields
    """
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test User"
    }


# ============================================================================
# Mock External Services
# ============================================================================

@pytest.fixture
def mock_abs_client():
    """
    Create mocked Audiobookshelf client

    Returns:
        MagicMock: Mocked ABS client
    """
    return MagicMock()


@pytest.fixture
def mock_qbittorrent_client():
    """
    Create mocked qBittorrent client

    Returns:
        MagicMock: Mocked qBittorrent client
    """
    return MagicMock()


@pytest.fixture
def mock_mam_crawler():
    """
    Create mocked MAM crawler

    Returns:
        AsyncMock: Mocked MAM crawler
    """
    return AsyncMock()


@pytest.fixture
def mock_http_client():
    """
    Create mocked HTTP client for external API calls

    Returns:
        AsyncMock: Mocked HTTP client
    """
    return AsyncMock()


# ============================================================================
# Request Context Fixtures
# ============================================================================

@pytest.fixture
def mock_request():
    """
    Create mocked FastAPI request

    Returns:
        MagicMock: Mocked request object
    """
    request = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers = {"user-agent": "pytest"}
    request.method = "GET"
    request.url.path = "/test"
    return request


# ============================================================================
# Async Test Helpers
# ============================================================================

@pytest.fixture
def async_mock_db():
    """
    Create mocked async database session

    Returns:
        AsyncMock: Mocked AsyncSession
    """
    return AsyncMock(spec=AsyncSession)


# ============================================================================
# Pytest Markers
# ============================================================================

def pytest_configure(config):
    """
    Register custom pytest markers
    """
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "async: marks tests as async tests"
    )


# ============================================================================
# Test Environment Setup
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """
    Setup test environment before running tests

    - Disable external service dependencies
    - Set test environment variable
    """
    os.environ["ENV"] = "testing"
    os.environ["DEBUG"] = "true"

    yield

    # Cleanup
    if "ENV" in os.environ:
        del os.environ["ENV"]
    if "DEBUG" in os.environ:
        del os.environ["DEBUG"]


# ============================================================================
# Cleanup Utilities
# ============================================================================

@pytest.fixture(scope="function", autouse=True)
def reset_app_state():
    """
    Reset application state between tests

    Ensures tests don't affect each other through global state
    """
    yield

    # Clear any dependency overrides
    app.dependency_overrides.clear()
