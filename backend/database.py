"""
Database connection and session management
Handles SQLAlchemy ORM setup and database session lifecycle
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
import logging

from backend.config import get_settings

# Create declarative base for ORM models
Base = declarative_base()

# Get settings
settings = get_settings()

# Configure logging
logger = logging.getLogger(__name__)

# Prepare connection arguments based on database type
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite://"):
    connect_args = {"timeout": 10}

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,  # Verify connections before using them
    connect_args=connect_args,
    poolclass=NullPool  # Don't use connection pooling
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Session:
    """
    FastAPI dependency for getting a database session
    Usage:
        def my_endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions
    Usage:
        with get_db_context() as db:
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database (create all tables)
    Should be called once on application startup
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def close_db():
    """
    Close database connection
    Should be called on application shutdown
    """
    engine.dispose()
    logger.info("Database connection closed")
