"""
FastAPI Application Entry Point for Audiobook Automation System

This module provides the main FastAPI application with:
- CORS middleware configuration with strict security policies
- API authentication via API key and JWT tokens
- Security headers and middleware
- Health check endpoints
- Database lifecycle management
- APScheduler integration
- Centralized error handling
- Router registration for all API endpoints

Author: Audiobook Automation System
Version: 1.0.0
"""

import logging
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Security, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from backend.config import get_settings
from backend.database import init_db, close_db
from backend.middleware import setup_security_middleware, verify_api_key
from backend.auth import hash_password, verify_password, generate_token, verify_token, sanitize_input

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/fastapi.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Import routers and utilities
try:
    from backend.routes import include_all_routes
    from backend.utils import setup_logging
    ROUTES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Routes not available yet: {e}")
    ROUTES_AVAILABLE = False

# Get application settings
settings = get_settings()

# Initialize APScheduler (global instance)
scheduler: Optional[AsyncIOScheduler] = None


def create_scheduler() -> AsyncIOScheduler:
    """
    Create and configure APScheduler instance

    Returns:
        AsyncIOScheduler: Configured scheduler instance
    """
    jobstores = {
        'default': SQLAlchemyJobStore(url=settings.DATABASE_URL)
    }

    executors = {
        'default': ThreadPoolExecutor(max_workers=10)
    }

    job_defaults = {
        'coalesce': True,  # Combine missed runs into one
        'max_instances': 1,  # Only one instance of each job at a time
        'misfire_grace_time': 3600  # Jobs can start up to 1 hour late
    }

    return AsyncIOScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone='UTC'
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager
    Handles startup and shutdown events

    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info("=" * 80)
    logger.info(f"Starting {settings.API_TITLE} v{settings.API_VERSION}")
    logger.info("=" * 80)

    try:
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized successfully")

        # Start scheduler if enabled
        if settings.SCHEDULER_ENABLED:
            global scheduler
            logger.info("Starting APScheduler...")
            scheduler = create_scheduler()
            scheduler.start()
            logger.info(f"APScheduler started with {len(scheduler.get_jobs())} jobs")
        else:
            logger.info("APScheduler disabled in configuration")

        logger.info("Application startup complete")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Error during application startup: {e}", exc_info=True)
        raise

    # Application is running
    yield

    # Shutdown
    logger.info("=" * 80)
    logger.info("Shutting down application...")
    logger.info("=" * 80)

    try:
        # Stop scheduler
        if scheduler and scheduler.running:
            logger.info("Stopping APScheduler...")
            scheduler.shutdown(wait=True)
            logger.info("APScheduler stopped")

        # Close database connections
        logger.info("Closing database connections...")
        close_db()
        logger.info("Database connections closed")

        logger.info("Application shutdown complete")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Error during application shutdown: {e}", exc_info=True)


# Create FastAPI application
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.API_DOCS else None,
    redoc_url="/redoc" if settings.API_DOCS else None,
    openapi_url="/openapi.json" if settings.API_DOCS else None
)


# ============================================================================
# Security Middleware Configuration
# ============================================================================

# Set up security middleware
setup_security_middleware(app)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """
    Middleware to add security headers to all responses
    
    Args:
        request: Incoming HTTP request
        call_next: Next middleware/handler in chain
        
    Returns:
        Response with security headers
    """
    response = await call_next(request)
    
    # Add security headers
    if settings.SECURITY_HEADERS:
        headers = response.headers
        
        # X-Content-Type-Options - prevents MIME sniffing
        headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options - prevents clickjacking
        headers["X-Frame-Options"] = "DENY"
        
        # X-XSS-Protection - enables browser XSS filter
        headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer-Policy - controls referrer information
        headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # HSTS - forces HTTPS connections
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Remove server information
        headers.pop("server", None)
    
    return response


@app.middleware("http")
async def input_validation_middleware(request: Request, call_next):
    """
    Middleware to validate and sanitize user input
    
    Args:
        request: Incoming HTTP request
        call_next: Next middleware/handler in chain
        
    Returns:
        Response from next handler
    """
    # Check for unusual request patterns that might indicate an attack
    path = request.url.path
    
    # Check for path traversal attempts
    if ".." in path or "//" in path:
        logger.warning(f"Blocked potentially malicious path: {path}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Invalid request path"}
        )
    
    # Process the request normally
    return await call_next(request)


# ============================================================================
# Authentication
# ============================================================================

# API Key header security scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# JWT bearer token scheme (for future implementation)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",  # This would be the login endpoint
    auto_error=False   # Don't automatically fail if token is missing
)


async def verify_api_key_security(api_key: str = Security(api_key_header)) -> str:
    """
    Enhanced API key verification from X-API-Key header
    
    Args:
        api_key: API key from X-API-Key header
        
    Returns:
        Validated API key
        
    Raises:
        HTTPException: If API key is invalid or missing
    """
    if not api_key:
        logger.warning("API request missing X-API-Key header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key in X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    # Sanitize the API key
    sanitized_key = sanitize_input(api_key)
    
    # Validate against configured API key
    if sanitized_key != settings.API_KEY:
        logger.warning(f"Invalid API key attempted")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    return sanitized_key


async def verify_jwt_token(token: str = Security(oauth2_scheme)) -> Optional[Dict]:
    """
    Verify JWT token from Authorization header
    
    Args:
        token: JWT token from Authorization: Bearer header
        
    Returns:
        Token payload if valid, None otherwise
    """
    if not token:
        return None
    
    try:
        # Remove "Bearer " prefix if present
        if token.startswith("Bearer "):
            token = token[7:]
        
        # Verify token and get payload
        payload = verify_token(token)
        return payload
    except Exception as e:
        logger.error(f"JWT token verification error: {e}")
        return None


def get_current_user_id(token_payload: Optional[Dict] = Depends(verify_jwt_token)) -> Optional[str]:
    """
    Get the current user ID from a verified JWT token
    
    Args:
        token_payload: Verified token payload
        
    Returns:
        User ID if token is valid, None otherwise
    """
    if token_payload:
        return token_payload.get("sub")
    return None


# ============================================================================
# Health Check Endpoints
# ============================================================================

@app.get(
    "/health",
    tags=["System"],
    summary="Health check endpoint",
    description="Returns application health status and current timestamp",
    response_description="Health status information"
)
async def health_check():
    """
    Health check endpoint for monitoring and load balancers
    
    Returns:
        dict: Health status with timestamp
    """
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.API_VERSION,
        "service": settings.API_TITLE
    }


@app.get(
    "/",
    tags=["System"],
    summary="Root endpoint",
    description="Returns API information and available endpoints"
)
async def root():
    """
    Root endpoint with API information
    
    Returns:
        dict: API metadata and links
    """
    return {
        "name": settings.API_TITLE,
        "version": settings.API_VERSION,
        "description": settings.API_DESCRIPTION,
        "docs": "/docs" if settings.API_DOCS else None,
        "health": "/health",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get(
    "/health/detailed",
    tags=["System"],
    summary="Detailed health check",
    description="Returns detailed health status including database and scheduler",
    dependencies=[Depends(verify_api_key_security)]
)
async def detailed_health_check():
    """
    Detailed health check with system component status
    Requires API key authentication
    
    Returns:
        dict: Detailed health information
    """
    health_data = {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.API_VERSION,
        "components": {}
    }

    # Check database
    try:
        from backend.database import engine
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        health_data["components"]["database"] = {
            "status": "ok",
            "url": settings.DATABASE_URL.split("@")[-1]  # Hide credentials
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_data["components"]["database"] = {
            "status": "error",
            "error": str(e)
        }
        health_data["status"] = "degraded"

    # Check scheduler
    if settings.SCHEDULER_ENABLED:
        try:
            if scheduler and scheduler.running:
                job_count = len(scheduler.get_jobs())
                health_data["components"]["scheduler"] = {
                    "status": "ok",
                    "running": True,
                    "job_count": job_count
                }
            else:
                health_data["components"]["scheduler"] = {
                    "status": "error",
                    "running": False
                }
                health_data["status"] = "degraded"
        except Exception as e:
            logger.error(f"Scheduler health check failed: {e}")
            health_data["components"]["scheduler"] = {
                "status": "error",
                "error": str(e)
            }
            health_data["status"] = "degraded"
    else:
        health_data["components"]["scheduler"] = {
            "status": "disabled"
        }

    return health_data


# ============================================================================
# Router Registration (Phase 5)
# ============================================================================

# Register all API routers (if available)
if ROUTES_AVAILABLE:
    try:
        logger.info("Registering API routes...")
        include_all_routes(app)
        logger.info("API routes registered successfully")
    except Exception as e:
        logger.error(f"Error registering API routes: {e}", exc_info=True)
else:
    logger.warning("API routes not available - routes module not imported")


# ============================================================================
# Application Info
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Uvicorn server...")
    logger.info(f"API Documentation available at: http://localhost:8000/docs" if settings.API_DOCS else "API documentation disabled")
    
    # Set environment variables for secure logging
    import os
    os.environ["PYTHONHASHSEED"] = "random"  # Randomized hash seed for security
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"  # Don't write .pyc files
    
    uvicorn.run(
        "backend.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG and settings.DEV_TOOLS,
        log_level="info",
        access_log=True,  # Enable access logging
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout"
                },
                "file": {
                    "formatter": "default",
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": "logs/app.log",
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 5
                }
            },
            "root": {
                "level": "INFO",
                "handlers": ["default", "file"]
            }
        }
    )