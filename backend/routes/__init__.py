"""
Routes Package Initialization
Centralizes all API route imports and provides registration function
"""

from fastapi import FastAPI, Depends

from backend.routes import (
    books,
    series,
    authors,
    downloads,
    metadata,
    scheduler,
    system,
    gaps
)

# Import verify_api_key for authentication
from backend.main import verify_api_key


def include_all_routes(app: FastAPI) -> None:
    """
    Register all API routers with the FastAPI application

    This function should be called during application initialization to
    register all route handlers with proper prefixes, tags, and authentication.

    Args:
        app: FastAPI application instance

    Example:
        >>> from fastapi import FastAPI
        >>> from backend.routes import include_all_routes
        >>>
        >>> app = FastAPI()
        >>> include_all_routes(app)
    """

    # Books routes
    app.include_router(
        books.router,
        prefix="/api/books",
        tags=["Books"],
        dependencies=[Depends(verify_api_key)]
    )

    # Series routes
    app.include_router(
        series.router,
        prefix="/api/series",
        tags=["Series"],
        dependencies=[Depends(verify_api_key)]
    )

    # Authors routes
    app.include_router(
        authors.router,
        prefix="/api/authors",
        tags=["Authors"],
        dependencies=[Depends(verify_api_key)]
    )

    # Downloads routes
    app.include_router(
        downloads.router,
        prefix="/api/downloads",
        tags=["Downloads"],
        dependencies=[Depends(verify_api_key)]
    )

    # Metadata routes
    app.include_router(
        metadata.router,
        prefix="/api/metadata",
        tags=["Metadata"],
        dependencies=[Depends(verify_api_key)]
    )

    # Scheduler routes
    app.include_router(
        scheduler.router,
        prefix="/api/scheduler",
        tags=["Scheduler"],
        dependencies=[Depends(verify_api_key)]
    )

    # System routes (health check does not require auth)
    app.include_router(
        system.router,
        prefix="/api/system",
        tags=["System"]
        # Note: /health endpoint is public, other endpoints require auth
    )

    # Gap Analysis routes
    app.include_router(
        gaps.router,
        prefix="/api/gaps",
        tags=["Gap Analysis"],
        dependencies=[Depends(verify_api_key)]
    )


__all__ = [
    "include_all_routes",
    "books",
    "series",
    "authors",
    "downloads",
    "metadata",
    "scheduler",
    "system",
    "gaps"
]
