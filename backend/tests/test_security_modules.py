"""
Comprehensive Test Suite for Phase 1 Security Modules

Tests all security modules to ensure:
- Correct functionality
- Proper error handling
- Integration compatibility
- Configuration handling
"""

import pytest
import asyncio
import logging
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import time
import json

# Import security modules
from backend.security import (
    # HTTPS Enforcer
    HTTPSEnforcer,
    HTTPSEnforcementError,
    validate_url,
    enforce_url,
    get_secure_url,
    get_https_enforcer,

    # Input Sanitizer
    InputSanitizer,
    SanitizationError,
    sanitize_string,
    sanitize_path,
    sanitize_email,
    sanitize_dict,
    get_sanitizer,

    # Audit Logger
    AuditLogger,
    AuditEventType,
    get_audit_logger,

    # Brute Force Protection
    BruteForceProtection,
    AccountLockoutReason,
    record_failed_attempt,
    record_successful_login,
    is_account_locked,
    get_brute_force_protection,
)


class TestHTTPSEnforcer:
    """Test HTTPS Enforcer module"""

    def test_https_url_validation(self):
        """Test that HTTPS URLs pass validation"""
        enforcer = HTTPSEnforcer(enforce=True, allow_localhost=False)
        is_valid, error = enforcer.validate_url("https://api.example.com", "test")
        assert is_valid
        assert error is None

    def test_http_url_enforcement(self):
        """Test that HTTP URLs are rejected when enforcement enabled"""
        enforcer = HTTPSEnforcer(enforce=True, allow_localhost=False)
        is_valid, error = enforcer.validate_url("http://api.example.com", "test")
        assert not is_valid
        assert "HTTPS enforcement" in error

    def test_localhost_exception(self):
        """Test that localhost HTTP is allowed with exception"""
        enforcer = HTTPSEnforcer(enforce=True, allow_localhost=True)
        is_valid, error = enforcer.validate_url("http://localhost:8080", "test")
        assert is_valid
        assert error is None

    def test_enforce_url_raises_exception(self):
        """Test that enforce_url raises exception on policy violation"""
        enforcer = HTTPSEnforcer(enforce=True, allow_localhost=False)
        with pytest.raises(HTTPSEnforcementError):
            enforcer.enforce_url("http://api.example.com", "test")

    def test_enforce_url_passes(self):
        """Test that enforce_url returns URL when valid"""
        enforcer = HTTPSEnforcer(enforce=True, allow_localhost=False)
        url = enforcer.enforce_url("https://api.example.com", "test")
        assert url == "https://api.example.com"

    def test_upgrade_to_https(self):
        """Test automatic upgrade from HTTP to HTTPS"""
        enforcer = HTTPSEnforcer(enforce=True)
        upgraded = enforcer.upgrade_to_https("http://api.example.com")
        assert upgraded == "https://api.example.com"

    def test_development_mode(self):
        """Test development mode allows HTTP"""
        enforcer = HTTPSEnforcer(enforce=False)
        is_valid, error = enforcer.validate_url("http://api.example.com", "test")
        assert is_valid

    def test_global_enforcer(self):
        """Test global enforcer instance"""
        enforcer = get_https_enforcer()
        assert enforcer is not None
        assert isinstance(enforcer, HTTPSEnforcer)


class TestInputSanitizer:
    """Test Input Sanitizer module"""

    def test_xss_prevention_script_tags(self):
        """Test XSS prevention for script tags"""
        sanitizer = InputSanitizer(strict=False)
        malicious = "<script>alert('xss')</script>Hello"
        clean = sanitizer.sanitize_string(malicious, "test")
        assert "<script>" not in clean
        assert "Hello" in clean

    def test_xss_prevention_event_handlers(self):
        """Test XSS prevention for event handlers"""
        sanitizer = InputSanitizer(strict=False)
        malicious = '<img src="x" onerror="alert(1)">'
        clean = sanitizer.sanitize_string(malicious, "test")
        # Should be HTML escaped (not removed completely)
        assert "<img" not in clean or "&lt;img" in clean

    def test_xss_prevention_javascript_protocol(self):
        """Test XSS prevention for javascript: protocol"""
        sanitizer = InputSanitizer(strict=False)
        malicious = '<a href="javascript:alert(1)">click</a>'
        clean = sanitizer.sanitize_string(malicious, "test")
        # Should be HTML escaped (content still present but safe)
        assert "<a" not in clean or "&lt;a" in clean

    def test_path_traversal_prevention(self):
        """Test path traversal prevention"""
        sanitizer = InputSanitizer(strict=False)
        malicious = "../../etc/passwd"
        clean = sanitizer.sanitize_path(malicious, "test")
        assert ".." not in clean

    def test_email_validation(self):
        """Test email validation"""
        sanitizer = InputSanitizer(strict=True)

        # Valid email
        valid = sanitizer.sanitize_email("user@example.com", "email")
        assert valid == "user@example.com"

        # Invalid email
        with pytest.raises(SanitizationError):
            sanitizer.sanitize_email("not-an-email", "email")

    def test_null_byte_removal(self):
        """Test null byte removal"""
        sanitizer = InputSanitizer(strict=False)
        malicious = "hello\x00world"
        clean = sanitizer.sanitize_string(malicious, "test")
        assert "\x00" not in clean

    def test_length_limit(self):
        """Test maximum length enforcement"""
        sanitizer = InputSanitizer(strict=False)
        long_string = "a" * 15000
        clean = sanitizer.sanitize_string(long_string, "test")
        assert len(clean) <= 10000

    def test_sanitize_dict(self):
        """Test dictionary sanitization"""
        sanitizer = InputSanitizer(strict=False)
        data = {
            "name": "<script>alert(1)</script>John",
            "email": "user@example.com",
            "bio": "Developer"
        }
        clean = sanitizer.sanitize_dict(data, "test")
        assert "<script>" not in clean["name"]
        assert clean["email"] == "user@example.com"

    def test_global_sanitizer(self):
        """Test global sanitizer instance"""
        sanitizer = get_sanitizer(strict=False)
        assert sanitizer is not None
        assert isinstance(sanitizer, InputSanitizer)


class TestAuditLogger:
    """Test Audit Logger module"""

    def test_audit_logger_creation(self):
        """Test audit logger initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=tmpdir)
            assert logger is not None
            log_path = logger.get_log_path()
            assert "audit" in str(log_path)
            # Close logger to release file handle
            for handler in logger.logger.handlers:
                handler.close()
                logger.logger.removeHandler(handler)

    def test_log_authentication_success(self):
        """Test logging successful authentication"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=tmpdir)
            logger.log_authentication(
                username="user@example.com",
                ip_address="192.168.1.1",
                success=True
            )

            log_path = logger.get_log_path()
            with open(log_path, 'r') as f:
                log_content = f.read()
                assert "LOGIN_SUCCESS" in log_content
                assert "user@example.com" in log_content

            # Close logger to release file handle
            for handler in logger.logger.handlers:
                handler.close()
                logger.logger.removeHandler(handler)

    def test_log_authentication_failure(self):
        """Test logging failed authentication"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=tmpdir)
            logger.log_authentication(
                username="user@example.com",
                ip_address="192.168.1.1",
                success=False,
                error_message="Invalid credentials"
            )

            log_path = logger.get_log_path()
            with open(log_path, 'r') as f:
                log_content = f.read()
                assert "LOGIN_FAILURE" in log_content
                assert "Invalid credentials" in log_content

            # Close logger to release file handle
            for handler in logger.logger.handlers:
                handler.close()
                logger.logger.removeHandler(handler)

    def test_log_event_json_format(self):
        """Test that audit logs are valid JSON"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=tmpdir)
            logger.log_event(
                event_type=AuditEventType.SENSITIVE_DATA_READ,
                user_id="123",
                resource="book:456",
                action="READ"
            )

            log_path = logger.get_log_path()
            with open(log_path, 'r') as f:
                for line in f:
                    if line.strip():
                        # Should be valid JSON
                        event = json.loads(line)
                        assert "event_type" in event
                        assert event["event_type"] == "SENSITIVE_DATA_READ"

            # Close logger to release file handle
            for handler in logger.logger.handlers:
                handler.close()
                logger.logger.removeHandler(handler)

    def test_log_brute_force_attempt(self):
        """Test logging brute force attempts"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=tmpdir)
            logger.log_brute_force_attempt(
                username="user@example.com",
                ip_address="192.168.1.1",
                attempt_count=3
            )

            log_path = logger.get_log_path()
            with open(log_path, 'r') as f:
                log_content = f.read()
                assert "BRUTE_FORCE_ATTEMPT" in log_content

            # Close logger to release file handle
            for handler in logger.logger.handlers:
                handler.close()
                logger.logger.removeHandler(handler)

    def test_log_rate_limit_exceeded(self):
        """Test logging rate limit exceeded"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=tmpdir)
            logger.log_rate_limit_exceeded(
                ip_address="192.168.1.1",
                endpoint="/api/search",
                limit=100,
                current=101
            )

            log_path = logger.get_log_path()
            with open(log_path, 'r') as f:
                log_content = f.read()
                assert "API_RATE_LIMIT_EXCEEDED" in log_content

            # Close logger to release file handle
            for handler in logger.logger.handlers:
                handler.close()
                logger.logger.removeHandler(handler)

    def test_sensitive_data_hashing(self):
        """Test that sensitive data is hashed in logs"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=tmpdir)
            logger.log_config_change(
                username="admin@example.com",
                config_key="password",
                old_value="secret123",
                new_value="newsecret456"
            )

            log_path = logger.get_log_path()
            with open(log_path, 'r') as f:
                log_content = f.read()
                # Should not contain raw passwords
                assert "secret123" not in log_content
                assert "newsecret456" not in log_content
                # But should have hash values
                assert "value_hash" in log_content

            # Close logger to release file handle
            for handler in logger.logger.handlers:
                handler.close()
                logger.logger.removeHandler(handler)

    def test_global_audit_logger(self):
        """Test global audit logger instance"""
        logger = get_audit_logger()
        assert logger is not None
        assert isinstance(logger, AuditLogger)


class TestBruteForceProtection:
    """Test Brute Force Protection module"""

    def test_failed_attempt_recording(self):
        """Test recording failed login attempts"""
        protection = BruteForceProtection(max_attempts=5)

        allow, msg = protection.record_failed_attempt(
            "user@example.com",
            "192.168.1.1",
            "Invalid password"
        )

        assert allow is True
        assert msg is None

    def test_account_lockout_after_threshold(self):
        """Test account lockout after max attempts"""
        protection = BruteForceProtection(max_attempts=3)

        # Record 3 failed attempts
        for i in range(3):
            allow, msg = protection.record_failed_attempt(
                "user@example.com",
                "192.168.1.1"
            )
            # First 2 should allow, third should lock
            if i < 2:
                assert allow is True
            else:
                assert allow is False
                assert "locked" in msg.lower()

    def test_check_account_locked_status(self):
        """Test checking if account is locked"""
        protection = BruteForceProtection(max_attempts=2)

        # Record 2 failed attempts
        for i in range(2):
            protection.record_failed_attempt("user@example.com", "192.168.1.1")

        # Check locked status
        is_locked, msg = protection.is_account_locked("user@example.com")
        assert is_locked is True
        assert "remaining" in msg.lower() or "locked" in msg.lower()

    def test_successful_login_resets_counter(self):
        """Test that successful login resets failed attempts"""
        protection = BruteForceProtection(max_attempts=5)

        # Record 3 failed attempts
        for i in range(3):
            protection.record_failed_attempt("user@example.com", "192.168.1.1")

        # Record successful login
        protection.record_successful_login("user@example.com", "192.168.1.1")

        # Counter should be reset
        is_locked, msg = protection.is_account_locked("user@example.com")
        assert is_locked is False

    def test_ip_rate_limiting(self):
        """Test IP-based rate limiting"""
        # Note: ip_rate_limit works after recording, so limit=6 allows 5 attempts before blocking 6th
        protection = BruteForceProtection(ip_rate_limit=6, max_attempts=100)

        # Try to exceed IP rate limit
        for i in range(7):
            allow, msg = protection.record_failed_attempt(
                f"user{i}@example.com",
                "192.168.1.1"
            )

            if i < 5:
                # First 5 attempts from same IP should be allowed
                assert allow is True
            elif i == 5:
                # 6th attempt: we now have 5 recorded (not including current), 6th is being checked
                # After recording, we have [att0-att5], so get_recent=[att0-att5], len=6, 6 >= 6? True, block
                assert allow is False
                assert "IP" in msg or "rate" in msg.lower()
            else:
                # 7th attempt should also be blocked
                assert allow is False

    def test_lockout_expiration(self):
        """Test that lockout expires after duration"""
        protection = BruteForceProtection(
            max_attempts=2,
            lockout_duration=1  # 1 second for testing
        )

        # Record 2 failed attempts to lock account
        for i in range(2):
            protection.record_failed_attempt("user@example.com", "192.168.1.1")

        # Should be locked
        is_locked, _ = protection.is_account_locked("user@example.com")
        assert is_locked is True

        # Wait for lockout to expire
        time.sleep(1.1)

        # Should no longer be locked
        is_locked, _ = protection.is_account_locked("user@example.com")
        assert is_locked is False

    def test_get_account_status(self):
        """Test getting detailed account status"""
        protection = BruteForceProtection(max_attempts=5)

        # Record 2 failed attempts
        for i in range(2):
            protection.record_failed_attempt("user@example.com", "192.168.1.1")

        # Get status
        status = protection.get_account_status("user@example.com")

        assert status["username"] == "user@example.com"
        assert status["is_locked"] is False
        assert status["failed_attempts_in_window"] == 2
        assert status["attempts_until_lockout"] == 3

    def test_manual_account_unlock(self):
        """Test manual account unlock by admin"""
        protection = BruteForceProtection(max_attempts=2)

        # Lock account
        for i in range(2):
            protection.record_failed_attempt("user@example.com", "192.168.1.1")

        is_locked, _ = protection.is_account_locked("user@example.com")
        assert is_locked is True

        # Unlock manually
        protection.unlock_account("user@example.com")

        is_locked, _ = protection.is_account_locked("user@example.com")
        assert is_locked is False

    def test_global_protection_instance(self):
        """Test global brute force protection instance"""
        protection = get_brute_force_protection()
        assert protection is not None
        assert isinstance(protection, BruteForceProtection)


class TestModuleImports:
    """Test that all modules can be imported correctly"""

    def test_import_all_security_modules(self):
        """Test importing from security package"""
        from backend.security import (
            HTTPSEnforcer,
            InputSanitizer,
            AuditLogger,
            BruteForceProtection,
        )

        assert HTTPSEnforcer is not None
        assert InputSanitizer is not None
        assert AuditLogger is not None
        assert BruteForceProtection is not None

    def test_import_all_utility_functions(self):
        """Test importing utility functions"""
        from backend.security import (
            validate_url,
            enforce_url,
            get_secure_url,
            sanitize_string,
            sanitize_path,
            sanitize_email,
            sanitize_dict,
            get_audit_logger,
            record_failed_attempt,
            is_account_locked,
            record_successful_login,
        )

        assert callable(validate_url)
        assert callable(enforce_url)
        assert callable(sanitize_string)

    def test_import_enums_and_exceptions(self):
        """Test importing enums and exceptions"""
        from backend.security import (
            HTTPSEnforcementError,
            SanitizationError,
            AuditEventType,
            AccountLockoutReason,
        )

        assert issubclass(HTTPSEnforcementError, Exception)
        assert issubclass(SanitizationError, Exception)
        assert hasattr(AuditEventType, 'LOGIN_SUCCESS')
        assert hasattr(AccountLockoutReason, 'TOO_MANY_ATTEMPTS')


class TestIntegrationPatterns:
    """Test common integration patterns"""

    def test_pattern_sanitize_and_validate(self):
        """Test pattern: sanitize and validate user input"""
        from backend.security import sanitize_dict

        user_input = {
            "name": "<script>alert(1)</script>John",
            "email": "john@example.com",
            "bio": "Developer"
        }

        clean_data = sanitize_dict(user_input, "user_input")

        assert "<script>" not in clean_data["name"]
        assert clean_data["email"] == "john@example.com"
        assert clean_data["bio"] == "Developer"

    def test_pattern_login_with_brute_force(self):
        """Test pattern: login endpoint with brute force protection"""
        from backend.security import (
            is_account_locked,
            record_failed_attempt,
            record_successful_login
        )

        username = "user@example.com"
        ip = "192.168.1.1"

        # Check lockout
        is_locked, _ = is_account_locked(username)
        assert is_locked is False

        # Simulate failed login
        allow, _ = record_failed_attempt(username, ip)
        assert allow is True

        # Simulate successful login
        record_successful_login(username, ip)

        # Counter should be reset
        is_locked, _ = is_account_locked(username)
        assert is_locked is False

    def test_pattern_https_enforcement(self):
        """Test pattern: enforce HTTPS in integrations"""
        from backend.security import enforce_url, HTTPSEnforcementError

        # Development mode (allow localhost)
        enforcer_dev = HTTPSEnforcer(enforce=True, allow_localhost=True)
        url_dev = enforcer_dev.enforce_url("http://localhost:8080")
        assert url_dev == "http://localhost:8080"

        # Production mode (reject HTTP)
        enforcer_prod = HTTPSEnforcer(enforce=True, allow_localhost=False)
        with pytest.raises(HTTPSEnforcementError):
            enforcer_prod.enforce_url("http://api.example.com")


class TestErrorHandling:
    """Test error handling in security modules"""

    def test_https_enforcement_error_message(self):
        """Test HTTPS enforcement error messages are informative"""
        enforcer = HTTPSEnforcer(enforce=True, allow_localhost=False)
        try:
            enforcer.enforce_url("http://api.example.com", "test_service")
        except HTTPSEnforcementError as e:
            assert "HTTPS" in str(e)
            assert "test_service" in str(e)

    def test_sanitization_error_strict_mode(self):
        """Test sanitization errors in strict mode"""
        sanitizer = InputSanitizer(strict=True)

        with pytest.raises(SanitizationError):
            sanitizer.sanitize_email("not-an-email", "email")

    def test_brute_force_lock_message(self):
        """Test brute force lock messages"""
        protection = BruteForceProtection(max_attempts=1)

        protection.record_failed_attempt("user@example.com", "192.168.1.1")
        is_locked, msg = protection.is_account_locked("user@example.com")

        assert is_locked is True
        assert "locked" in msg.lower() or "try again" in msg.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
