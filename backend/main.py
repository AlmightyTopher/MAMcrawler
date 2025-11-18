"""
FastAPI Application Entry Point for Audiobook Automation System

This module provides the main FastAPI application with:
- CORS middleware configuration
- API authentication via API key
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
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from backend.config import get_settings
from backend.database import init_db, close_db

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
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# ============================================================================
# Middleware Configuration
# ============================================================================

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to log all HTTP requests

    Args:
        request: Incoming HTTP request
        call_next: Next middleware/handler in chain

    Returns:
        Response from next handler
    """
    if settings.ENABLE_API_LOGGING:
        start_time = datetime.utcnow()

        # Log request
        logger.info(f"Request: {request.method} {request.url.path}")

        # Process request
        response = await call_next(request)

        # Log response
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"Response: {request.method} {request.url.path} "
            f"Status={response.status_code} Duration={duration:.3f}s"
        )

        return response
    else:
        return await call_next(request)


@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    """
    Centralized error handling middleware
    Catches all unhandled exceptions and returns proper JSON responses

    Args:
        request: Incoming HTTP request
        call_next: Next middleware/handler in chain

    Returns:
        Response with error details if exception occurs
    """
    try:
        return await call_next(request)
    except HTTPException:
        # Re-raise HTTP exceptions (already handled)
        raise
    except Exception as e:
        logger.error(
            f"Unhandled exception in {request.method} {request.url.path}: {e}",
            exc_info=True
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "error": str(e) if settings.DEBUG else "An unexpected error occurred",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


# ============================================================================
# Authentication
# ============================================================================

# API Key header security scheme
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verify API key from Authorization header

    Args:
        api_key: API key from Authorization header

    Returns:
        Validated API key

    Raises:
        HTTPException: If API key is invalid or missing
    """
    if not api_key:
        logger.warning("API request missing Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key in Authorization header",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    # Extract key from "Bearer <key>" or just "<key>"
    key = api_key.replace("Bearer ", "").strip()

    # Validate against configured API key
    if key != settings.API_KEY:
        logger.warning(f"Invalid API key attempted: {key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    return key


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
        "docs": "/docs",
        "health": "/health",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get(
    "/health/detailed",
    tags=["System"],
    summary="Detailed health check",
    description="Returns detailed health status including database and scheduler",
    dependencies=[Depends(verify_api_key)]
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
    logger.info(f"API Documentation available at: http://localhost:8000/docs")
    logger.info(f"Alternative docs available at: http://localhost:8000/redoc")

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
