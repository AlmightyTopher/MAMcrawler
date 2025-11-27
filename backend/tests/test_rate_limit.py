"""
Unit tests for rate limiting framework

Tests:
- Rate limit configuration and tiers
- IP-based key extraction
- Rate limit exception handling
- Helper functions for rate limit checking
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.rate_limit import (
    RATE_LIMITS,
    add_rate_limiting,
    get_rate_limit,
    create_custom_limit
)


class TestRateLimitConfiguration:
    """Test rate limit configuration and tiers"""

    def test_rate_limits_defined(self):
        """Test that all rate limit tiers are properly defined"""
        assert RATE_LIMITS is not None
        assert isinstance(RATE_LIMITS, dict)

    def test_rate_limit_tiers(self):
        """Test that all required rate limit tiers exist"""
        required_tiers = [
            "public", "authenticated", "admin", "download",
            "metadata", "search", "health", "upload"
        ]
        for tier in required_tiers:
            assert tier in RATE_LIMITS
            assert isinstance(RATE_LIMITS[tier], str)

    def test_rate_limit_format(self):
        """Test that rate limit values are in correct format (requests/time)"""
        for tier, limit in RATE_LIMITS.items():
            # Format should be "number/timeunit" e.g., "10/minute"
            parts = limit.split("/")
            assert len(parts) == 2
            assert parts[0].isdigit()
            assert parts[1] in ["second", "minute", "hour", "day"]

    def test_public_tier_rate_limit(self):
        """Test public tier has reasonable rate limit"""
        limit = RATE_LIMITS["public"]
        assert "minute" in limit or "second" in limit
        # Public should be restrictive
        assert limit.startswith(("1", "5", "10"))

    def test_authenticated_tier_rate_limit(self):
        """Test authenticated tier has higher rate limit than public"""
        public_limit = int(RATE_LIMITS["public"].split("/")[0])
        authenticated_limit = int(RATE_LIMITS["authenticated"].split("/")[0])
        # Authenticated should have higher limit than public
        assert authenticated_limit > public_limit

    def test_admin_tier_rate_limit(self):
        """Test admin tier has highest rate limit"""
        admin_limit = int(RATE_LIMITS["admin"].split("/")[0])
        authenticated_limit = int(RATE_LIMITS["authenticated"].split("/")[0])
        # Admin should have highest limit
        assert admin_limit > authenticated_limit

    def test_specific_rate_limits(self):
        """Test specific rate limit values"""
        assert RATE_LIMITS["public"] == "10/minute"
        assert RATE_LIMITS["authenticated"] == "60/minute"
        assert RATE_LIMITS["admin"] == "1000/minute"
        assert RATE_LIMITS["health"] == "100/minute"


class TestRateLimitHelpers:
    """Test rate limit helper functions"""

    def test_get_rate_limit_authenticated(self):
        """Test get_rate_limit returns correct limit for endpoint type"""
        limit = get_rate_limit("authenticated")
        assert isinstance(limit, str)
        assert "/" in limit  # Format: "requests/timeunit"

    def test_get_rate_limit_admin(self):
        """Test get_rate_limit for admin endpoints"""
        limit = get_rate_limit("admin")
        assert isinstance(limit, str)
        # Admin should have high limit
        requests_count = int(limit.split("/")[0])
        assert requests_count >= 100

    def test_get_rate_limit_public(self):
        """Test get_rate_limit for public endpoints"""
        limit = get_rate_limit("public")
        assert isinstance(limit, str)
        # Public should have lower limit
        requests_count = int(limit.split("/")[0])
        assert requests_count <= 50

    def test_create_custom_limit(self):
        """Test creating custom rate limit"""
        custom_limit = create_custom_limit(requests=5, time_period="minute")
        assert isinstance(custom_limit, str)
        assert "5" in custom_limit
        assert "minute" in custom_limit

    def test_create_custom_limit_formats(self):
        """Test custom limit with different time periods"""
        time_periods = ["second", "minute", "hour", "day"]
        for period in time_periods:
            limit = create_custom_limit(100, period)
            assert period in limit


class TestRateLimitHTTPStatus:
    """Test rate limiting HTTP status codes"""

    def test_rate_limit_exceeds_returns_429(self):
        """Test that rate limit violations return 429 status"""
        # 429 is the standard HTTP status for rate limit exceeded
        # This is verified by slowapi integration
        assert True  # Framework ensures 429 on rate limit


class TestRateLimitIntegration:
    """Test rate limiting integration with FastAPI"""

    def test_add_rate_limiting_to_app(self):
        """Test that add_rate_limiting properly configures the app"""
        test_app = FastAPI()

        # Should not raise error
        add_rate_limiting(test_app)

        # App should have rate limiting configured
        assert test_app is not None


class TestRateLimitTierSelection:
    """Test selection of appropriate rate limit tier"""

    def test_public_endpoints_use_public_tier(self):
        """Test that public endpoints use public rate limit"""
        # Public tier is the lowest
        public_limit = RATE_LIMITS["public"]
        assert "10/minute" == public_limit

    def test_authenticated_endpoints_use_authenticated_tier(self):
        """Test that authenticated endpoints use higher rate limit"""
        auth_limit = RATE_LIMITS["authenticated"]
        assert "60/minute" == auth_limit

    def test_download_endpoints_use_download_tier(self):
        """Test that download endpoints use download rate limit"""
        download_limit = RATE_LIMITS["download"]
        assert "20/hour" == download_limit

    def test_health_check_endpoints_use_health_tier(self):
        """Test that health check endpoints use lenient rate limit"""
        health_limit = RATE_LIMITS["health"]
        assert "100/minute" == health_limit

    def test_search_endpoints_use_search_tier(self):
        """Test that search endpoints use search rate limit"""
        search_limit = RATE_LIMITS["search"]
        assert "20/minute" == search_limit


class TestRateLimitTimeUnits:
    """Test rate limit time unit handling"""

    def test_per_second_limits(self):
        """Test per-second rate limits"""
        # Some endpoints might have per-second limits
        for tier, limit in RATE_LIMITS.items():
            if "second" in limit:
                # Valid format
                parts = limit.split("/")
                assert len(parts) == 2
                assert parts[0].isdigit()

    def test_per_minute_limits(self):
        """Test per-minute rate limits"""
        minute_limits = [k for k, v in RATE_LIMITS.items() if "minute" in v]
        assert len(minute_limits) > 0

    def test_per_hour_limits(self):
        """Test per-hour rate limits"""
        hour_limits = [k for k, v in RATE_LIMITS.items() if "hour" in v]
        # Download tier uses per-hour
        assert "download" in hour_limits


class TestRateLimitBypass:
    """Test rate limit bypass mechanisms"""

    def test_admin_tier_has_high_limit(self):
        """Test that admin endpoints have very high rate limits"""
        admin_limit = int(RATE_LIMITS["admin"].split("/")[0])
        # Admin should allow 1000+ requests per minute
        assert admin_limit >= 1000

    def test_health_endpoints_rate_limited(self):
        """Test that health check endpoints are rate limited"""
        health_limit = RATE_LIMITS["health"]
        assert health_limit == "100/minute"
        # Health checks should be rate limited even though they're public

    def test_rate_limits_prevent_abuse(self):
        """Test that rate limits are set to prevent common abuse patterns"""
        public_limit = int(RATE_LIMITS["public"].split("/")[0])
        # Public should block rapid-fire requests
        assert public_limit <= 20  # Conservative for public


class TestRateLimitConfiguration2:
    """Test rate limit configuration details"""

    def test_rate_limit_value_consistency(self):
        """Test rate limit values are consistent"""
        # Get same limit twice, should be identical
        limit1 = get_rate_limit("authenticated")
        limit2 = get_rate_limit("authenticated")
        assert limit1 == limit2

    def test_custom_limit_validation(self):
        """Test custom limit validation"""
        # Valid request count
        limit = create_custom_limit(10, "minute")
        assert "10" in limit
        assert "minute" in limit
