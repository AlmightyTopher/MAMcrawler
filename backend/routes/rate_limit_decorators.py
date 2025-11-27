"""
Rate Limiting Decorator Application Guide

This module provides documentation and helper functions for applying rate limiting
decorators to all API endpoints.

Usage Pattern:
    from backend.rate_limit import limiter, get_rate_limit

    @app.get("/api/endpoint")
    @limiter.limit(get_rate_limit("authenticated"))
    async def my_endpoint(request: Request):
        return {"data": "..."}
"""

# Rate limit types and their limits
LIMITS = {
    "public": "10/minute",           # Health checks, public docs
    "authenticated": "60/minute",    # List, GET operations
    "admin": "1000/minute",          # Admin operations
    "download": "20/hour",           # Download queue operations
    "metadata": "30/minute",         # Metadata operations
    "search": "20/minute",           # Search operations
    "health": "100/minute",          # Health endpoints
    "upload": "5/minute",            # File uploads
}

# Endpoint classifications for reference
ENDPOINT_CLASSIFICATION = {
    # Books endpoints
    "list_books": "authenticated",
    "get_book": "authenticated",
    "create_book": "authenticated",
    "update_book": "authenticated",
    "delete_book": "authenticated",
    "search_books": "search",

    # Downloads endpoints
    "list_downloads": "authenticated",
    "get_download": "authenticated",
    "queue_download": "download",
    "update_download_status": "download",
    "mark_complete": "download",
    "retry_download": "download",
    "delete_download": "authenticated",

    # Series endpoints
    "list_series": "authenticated",
    "get_series": "authenticated",
    "create_series": "authenticated",
    "update_series": "authenticated",
    "delete_series": "authenticated",
    "get_series_stats": "authenticated",
    "get_completion_summary": "authenticated",

    # Authors endpoints
    "list_authors": "authenticated",
    "get_author": "authenticated",
    "create_author": "authenticated",
    "update_author": "authenticated",
    "delete_author": "authenticated",
    "get_author_stats": "authenticated",
    "toggle_favorite": "authenticated",

    # Metadata endpoints
    "correct_single_book": "metadata",
    "batch_correct_metadata": "metadata",
    "get_correction_history": "authenticated",
    "get_quality_status": "metadata",

    # Scheduler endpoints
    "get_status": "authenticated",
    "list_tasks": "authenticated",
    "trigger_task": "admin",
    "pause": "admin",
    "resume": "admin",
    "get_execution_history": "authenticated",

    # Gaps endpoints
    "analyze_gaps": "authenticated",
    "acquire_missing_book": "download",

    # System endpoints
    "health": "health",
    "liveness": "health",
    "readiness": "health",
    "get_stats": "authenticated",

    # Admin endpoints
    "login": "public",
    "list_users": "admin",
    "create_user": "admin",
    "delete_user": "admin",
    "change_password": "admin",
}


def get_limit_for_endpoint(endpoint_type: str) -> str:
    """Get rate limit for endpoint type"""
    return LIMITS.get(endpoint_type, LIMITS["authenticated"])
