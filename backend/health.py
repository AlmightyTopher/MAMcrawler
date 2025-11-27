"""
Health Check Endpoints for Audiobook Automation System

This module provides health check endpoints that monitor system status:
- /health - Overall system health
- /health/live - Liveness probe (is app running?)
- /health/ready - Readiness probe (is app ready for requests?)

Used by:
- Docker HEALTHCHECK instructions
- Kubernetes probes
- Monitoring systems
- Load balancers
"""

from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
import logging

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


class HealthStatus(str, Enum):
    """Health check status values"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentStatus(str, Enum):
    """Individual component status"""
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


async def check_database_health(connection=None) -> Dict[str, Any]:
    """
    Check database connectivity and health

    Args:
        connection: Optional database connection

    Returns:
        Dictionary with database health status
    """
    try:
        from backend.database import engine

        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()

        return {
            "status": ComponentStatus.OK.value,
            "database": "connected",
            "type": "postgresql"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            "status": ComponentStatus.ERROR.value,
            "database": "disconnected",
            "error": str(e)
        }


async def check_api_health() -> Dict[str, Any]:
    """
    Check API server health

    Returns:
        Dictionary with API health status
    """
    try:
        return {
            "status": ComponentStatus.OK.value,
            "api": "running",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"API health check failed: {str(e)}")
        return {
            "status": ComponentStatus.ERROR.value,
            "api": "error",
            "error": str(e)
        }


async def check_scheduler_health() -> Dict[str, Any]:
    """
    Check background scheduler health

    Returns:
        Dictionary with scheduler health status
    """
    try:
        from backend.main import scheduler

        if scheduler and scheduler.running:
            return {
                "status": ComponentStatus.OK.value,
                "scheduler": "running",
                "jobs": len(scheduler.get_jobs())
            }
        else:
            return {
                "status": ComponentStatus.WARNING.value,
                "scheduler": "not running",
                "warning": "Scheduler not initialized"
            }
    except Exception as e:
        logger.warning(f"Scheduler health check warning: {str(e)}")
        return {
            "status": ComponentStatus.WARNING.value,
            "scheduler": "unavailable",
            "error": str(e)
        }


@router.get("", response_class=JSONResponse)
async def health_check(request: Request) -> Dict[str, Any]:
    """
    Overall system health check endpoint

    Returns:
    - 200: System is healthy and ready
    - 503: System is unhealthy

    Response includes:
    - status: overall health (healthy/degraded/unhealthy)
    - timestamp: ISO format timestamp
    - uptime: seconds since startup
    - services: individual service health status
    """
    db_health = await check_database_health()
    api_health = await check_api_health()
    scheduler_health = await check_scheduler_health()

    # Determine overall status
    statuses = [
        db_health.get("status"),
        api_health.get("status"),
        scheduler_health.get("status")
    ]

    if ComponentStatus.ERROR.value in statuses:
        overall_status = HealthStatus.UNHEALTHY.value
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    elif ComponentStatus.WARNING.value in statuses:
        overall_status = HealthStatus.DEGRADED.value
        http_status = status.HTTP_200_OK
    else:
        overall_status = HealthStatus.HEALTHY.value
        http_status = status.HTTP_200_OK

    response = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": db_health,
            "api": api_health,
            "scheduler": scheduler_health
        }
    }

    return JSONResponse(content=response, status_code=http_status)


@router.get("/live", response_class=JSONResponse)
async def liveness_check(request: Request) -> Dict[str, Any]:
    """
    Liveness probe endpoint

    Kubernetes calls this to determine if the container is still running.
    Returns:
    - 200: Container is alive
    - 503: Container should be restarted

    This is a lightweight check that doesn't verify external dependencies.
    """
    try:
        api_health = await check_api_health()

        response = {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat(),
            "api": api_health
        }

        return JSONResponse(content=response, status_code=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Liveness check failed: {str(e)}")
        return JSONResponse(
            content={
                "status": "dead",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@router.get("/ready", response_class=JSONResponse)
async def readiness_check(request: Request) -> Dict[str, Any]:
    """
    Readiness probe endpoint

    Kubernetes calls this to determine if the container is ready to accept traffic.
    Returns:
    - 200: Container is ready
    - 503: Container is not ready

    This check verifies critical dependencies like database connectivity.
    """
    try:
        db_health = await check_database_health()

        # Container is only "ready" if database is accessible
        is_ready = db_health.get("status") == ComponentStatus.OK.value

        response = {
            "status": "ready" if is_ready else "not_ready",
            "timestamp": datetime.utcnow().isoformat(),
            "database": db_health
        }

        http_status = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

        return JSONResponse(content=response, status_code=http_status)
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return JSONResponse(
            content={
                "status": "not_ready",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@router.get("/deep", response_class=JSONResponse)
async def deep_health_check(request: Request) -> Dict[str, Any]:
    """
    Deep health check endpoint

    Comprehensive health check that tests all systems and services.
    Returns detailed information about each component.

    Returns:
    - 200: All systems healthy
    - 503: One or more systems unhealthy
    """
    try:
        db_health = await check_database_health()
        api_health = await check_api_health()
        scheduler_health = await check_scheduler_health()

        # Calculate overall status
        statuses = [
            db_health.get("status"),
            api_health.get("status"),
            scheduler_health.get("status")
        ]

        if ComponentStatus.ERROR.value in statuses:
            overall = HealthStatus.UNHEALTHY.value
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        elif ComponentStatus.WARNING.value in statuses:
            overall = HealthStatus.DEGRADED.value
            http_status = status.HTTP_200_OK
        else:
            overall = HealthStatus.HEALTHY.value
            http_status = status.HTTP_200_OK

        response = {
            "status": overall,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": db_health,
                "api": api_health,
                "scheduler": scheduler_health
            }
        }

        return JSONResponse(content=response, status_code=http_status)
    except Exception as e:
        logger.error(f"Deep health check failed: {str(e)}")
        return JSONResponse(
            content={
                "status": HealthStatus.UNHEALTHY.value,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )
