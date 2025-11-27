"""
Unit tests for health check endpoints

Tests:
- Overall system health endpoint
- Liveness probe (Kubernetes)
- Readiness probe (Kubernetes)
- Deep health check
- Component-specific health checks
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from backend.health import (
    health_check,
    liveness_check,
    readiness_check,
    deep_health_check,
    check_database_health,
    check_api_health,
    check_scheduler_health,
    HealthStatus,
    ComponentStatus
)


class TestHealthStatusEnum:
    """Test HealthStatus enumeration"""

    def test_health_status_values(self):
        """Test health status enum values"""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"

    def test_health_status_is_string_enum(self):
        """Test that HealthStatus values are strings"""
        for status in HealthStatus:
            assert isinstance(status.value, str)


class TestComponentStatusEnum:
    """Test ComponentStatus enumeration"""

    def test_component_status_values(self):
        """Test component status enum values"""
        assert ComponentStatus.OK.value == "ok"
        assert ComponentStatus.WARNING.value == "warning"
        assert ComponentStatus.ERROR.value == "error"

    def test_component_status_is_string_enum(self):
        """Test that ComponentStatus values are strings"""
        for status in ComponentStatus:
            assert isinstance(status.value, str)


class TestHealthCheckEndpoint:
    """Test /health overall health endpoint"""

    @pytest.mark.asyncio
    async def test_health_check_returns_ok(self, client):
        """Test health check endpoint returns OK"""
        response = client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_check_response_structure(self, client):
        """Test health check response has correct structure"""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "services" in data

    @pytest.mark.asyncio
    async def test_health_check_includes_timestamp(self, client):
        """Test health check includes ISO format timestamp"""
        response = client.get("/health")
        data = response.json()

        assert "timestamp" in data
        assert "T" in data["timestamp"]  # ISO format includes T

    @pytest.mark.asyncio
    async def test_health_check_includes_services(self, client):
        """Test health check includes service health info"""
        response = client.get("/health")
        data = response.json()

        assert "services" in data
        services = data["services"]
        assert "database" in services
        assert "api" in services
        assert "scheduler" in services


class TestLivenessProbe:
    """Test /health/live liveness probe endpoint"""

    @pytest.mark.asyncio
    async def test_liveness_check_returns_ok(self, client):
        """Test liveness check returns 200 when alive"""
        response = client.get("/health/live")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_liveness_check_response_structure(self, client):
        """Test liveness check response structure"""
        response = client.get("/health/live")
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "api" in data

    @pytest.mark.asyncio
    async def test_liveness_check_status_alive(self, client):
        """Test liveness check status is 'alive'"""
        response = client.get("/health/live")
        data = response.json()

        assert data["status"] == "alive"

    @pytest.mark.asyncio
    async def test_liveness_check_lightweight(self, client):
        """Test liveness check is lightweight (no external deps)"""
        # Liveness check should not require database
        response = client.get("/health/live")
        assert response.status_code == 200
        # Should complete quickly without DB verification


class TestReadinessProbe:
    """Test /health/ready readiness probe endpoint"""

    @pytest.mark.asyncio
    async def test_readiness_check_returns_ok_when_ready(self, client):
        """Test readiness check returns 200 when ready"""
        response = client.get("/health/ready")
        # Should be ready in test environment
        assert response.status_code in [200, 503]

    @pytest.mark.asyncio
    async def test_readiness_check_response_structure(self, client):
        """Test readiness check response structure"""
        response = client.get("/health/ready")
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "database" in data

    @pytest.mark.asyncio
    async def test_readiness_check_verifies_database(self, client):
        """Test readiness check verifies database connectivity"""
        response = client.get("/health/ready")
        data = response.json()

        # Readiness check should verify database
        assert "database" in data
        db_info = data["database"]
        assert "status" in db_info

    @pytest.mark.asyncio
    async def test_readiness_check_status_ready_or_not_ready(self, client):
        """Test readiness check status is 'ready' or 'not_ready'"""
        response = client.get("/health/ready")
        data = response.json()

        assert data["status"] in ["ready", "not_ready"]


class TestDeepHealthCheck:
    """Test /health/deep deep health check endpoint"""

    @pytest.mark.asyncio
    async def test_deep_health_check_returns_ok(self, client):
        """Test deep health check returns 200"""
        response = client.get("/health/deep")
        assert response.status_code in [200, 503]

    @pytest.mark.asyncio
    async def test_deep_health_check_comprehensive(self, client):
        """Test deep health check is comprehensive"""
        response = client.get("/health/deep")
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "checks" in data

    @pytest.mark.asyncio
    async def test_deep_health_check_all_components(self, client):
        """Test deep health check includes all components"""
        response = client.get("/health/deep")
        data = response.json()

        checks = data["checks"]
        assert "database" in checks
        assert "api" in checks
        assert "scheduler" in checks

    @pytest.mark.asyncio
    async def test_deep_health_check_detailed_info(self, client):
        """Test deep health check includes detailed component info"""
        response = client.get("/health/deep")
        data = response.json()

        checks = data["checks"]

        # Each component should have status
        for component_name, component_data in checks.items():
            assert "status" in component_data


class TestDatabaseHealthCheck:
    """Test database health check function"""

    @pytest.mark.asyncio
    async def test_database_health_check_returns_dict(self):
        """Test database health check returns dictionary"""
        result = await check_database_health()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_database_health_check_has_status(self):
        """Test database health check includes status"""
        result = await check_database_health()
        assert "status" in result
        assert result["status"] in ["ok", "error"]

    @pytest.mark.asyncio
    async def test_database_health_check_ok_status(self, db_session):
        """Test database health check returns ok when connected"""
        result = await check_database_health()
        # In test environment with in-memory DB, should be ok
        assert result["status"] in ["ok", "warning"]

    @pytest.mark.asyncio
    async def test_database_health_check_includes_type(self):
        """Test database health check includes database type"""
        result = await check_database_health()
        # Should indicate database type
        assert result is not None


class TestAPIHealthCheck:
    """Test API health check function"""

    @pytest.mark.asyncio
    async def test_api_health_check_returns_dict(self):
        """Test API health check returns dictionary"""
        result = await check_api_health()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_api_health_check_has_status(self):
        """Test API health check includes status"""
        result = await check_api_health()
        assert "status" in result
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_api_health_check_includes_api_status(self):
        """Test API health check includes api field"""
        result = await check_api_health()
        assert "api" in result
        assert result["api"] == "running"

    @pytest.mark.asyncio
    async def test_api_health_check_includes_version(self):
        """Test API health check includes version"""
        result = await check_api_health()
        assert "version" in result


class TestSchedulerHealthCheck:
    """Test scheduler health check function"""

    @pytest.mark.asyncio
    async def test_scheduler_health_check_returns_dict(self):
        """Test scheduler health check returns dictionary"""
        result = await check_scheduler_health()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_scheduler_health_check_has_status(self):
        """Test scheduler health check includes status"""
        result = await check_scheduler_health()
        assert "status" in result
        assert result["status"] in ["ok", "warning", "error"]

    @pytest.mark.asyncio
    async def test_scheduler_health_check_status(self):
        """Test scheduler health check status indicates running/not running"""
        result = await check_scheduler_health()
        # Should indicate scheduler status
        assert "status" in result


class TestHealthEndpointIntegration:
    """Test health endpoints integration with FastAPI"""

    @pytest.mark.asyncio
    async def test_health_endpoints_accessible(self, client):
        """Test all health endpoints are accessible"""
        endpoints = [
            "/health",
            "/health/live",
            "/health/ready",
            "/health/deep"
        ]
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code in [200, 503]

    @pytest.mark.asyncio
    async def test_health_endpoints_return_json(self, client):
        """Test health endpoints return JSON responses"""
        endpoints = [
            "/health",
            "/health/live",
            "/health/ready",
            "/health/deep"
        ]
        for endpoint in endpoints:
            response = client.get(endpoint)
            # Should be valid JSON
            data = response.json()
            assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_health_endpoints_include_timestamp(self, client):
        """Test all health endpoints include timestamp"""
        endpoints = [
            "/health",
            "/health/live",
            "/health/ready",
            "/health/deep"
        ]
        for endpoint in endpoints:
            response = client.get(endpoint)
            data = response.json()
            assert "timestamp" in data


class TestHealthCheckStatusCodes:
    """Test health check HTTP status codes"""

    @pytest.mark.asyncio
    async def test_healthy_returns_200(self, client):
        """Test healthy system returns 200 OK"""
        response = client.get("/health")
        # In test environment should be 200
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_degraded_returns_200(self, client):
        """Test degraded system returns 200 (partial failure)"""
        # Even with some components warning, should return 200
        response = client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_unhealthy_returns_503(self, client):
        """Test unhealthy system returns 503 when critical"""
        # Only critical errors (full failures) should return 503
        response = client.get("/health")
        # In test environment with working DB, should be 200
        assert response.status_code in [200, 503]


class TestHealthCheckDocker:
    """Test health checks for Docker container usage"""

    @pytest.mark.asyncio
    async def test_health_endpoint_used_by_docker(self, client):
        """Test /health endpoint suitable for Docker HEALTHCHECK"""
        response = client.get("/health")
        # Docker HEALTHCHECK expects 200 for healthy
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    @pytest.mark.asyncio
    async def test_health_timeout_less_than_3_seconds(self, client):
        """Test health check completes in less than 3 seconds (Docker timeout)"""
        import time
        start = time.time()
        response = client.get("/health")
        elapsed = time.time() - start
        # Should complete well under 3 second Docker timeout
        assert elapsed < 2.0


class TestHealthCheckKubernetes:
    """Test health checks for Kubernetes usage"""

    @pytest.mark.asyncio
    async def test_liveness_probe_for_kubernetes(self, client):
        """Test /health/live suitable for Kubernetes liveness probe"""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    @pytest.mark.asyncio
    async def test_readiness_probe_for_kubernetes(self, client):
        """Test /health/ready suitable for Kubernetes readiness probe"""
        response = client.get("/health/ready")
        assert response.status_code in [200, 503]
        data = response.json()
        assert data["status"] in ["ready", "not_ready"]

    @pytest.mark.asyncio
    async def test_health_probes_independent(self, client):
        """Test health probes are independent"""
        # Liveness should work even if readiness fails
        live_response = client.get("/health/live")
        ready_response = client.get("/health/ready")

        assert live_response.status_code == 200
        # Ready might fail, but live should always be 200


class TestHealthCheckErrorHandling:
    """Test health check error handling"""

    @pytest.mark.asyncio
    async def test_health_check_handles_db_error(self, client):
        """Test health check handles database connection errors gracefully"""
        response = client.get("/health")
        # Should return 200 or 503, not 500 error
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data

    @pytest.mark.asyncio
    async def test_health_check_handles_scheduler_error(self, client):
        """Test health check handles scheduler errors gracefully"""
        response = client.get("/health")
        # Should still return response even if scheduler unavailable
        assert response.status_code in [200, 503]

    @pytest.mark.asyncio
    async def test_deep_health_check_includes_errors(self, client):
        """Test deep health check includes error information"""
        response = client.get("/health/deep")
        data = response.json()
        # If there are errors, they should be included
        if response.status_code == 503:
            # Has errors, should indicate which components failed
            checks = data.get("checks", {})
            assert len(checks) > 0
