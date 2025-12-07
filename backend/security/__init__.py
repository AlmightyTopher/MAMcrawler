"""
Security Module

Provides comprehensive security utilities:
- HTTPS enforcement for external APIs
- Input sanitization and validation
- Audit logging for sensitive operations
- Brute force protection with account lockout
"""

from .https_enforcer import (
    HTTPSEnforcer,
    HTTPSEnforcementError,
    get_https_enforcer,
    validate_url,
    enforce_url,
    get_secure_url,
)

from .input_sanitizer import (
    InputSanitizer,
    SanitizationError,
    get_sanitizer,
    sanitize_string,
    sanitize_path,
    sanitize_email,
    sanitize_dict,
)

from .audit_logger import (
    AuditLogger,
    AuditEventType,
    get_audit_logger,
    audit_log,
)

from .brute_force_protection import (
    BruteForceProtection,
    AccountLockoutReason,
    LoginAttempt,
    AccountLockout,
    get_brute_force_protection,
    record_failed_attempt,
    record_successful_login,
    is_account_locked,
)

__all__ = [
    # HTTPS Enforcement
    "HTTPSEnforcer",
    "HTTPSEnforcementError",
    "get_https_enforcer",
    "validate_url",
    "enforce_url",
    "get_secure_url",
    # Input Sanitization
    "InputSanitizer",
    "SanitizationError",
    "get_sanitizer",
    "sanitize_string",
    "sanitize_path",
    "sanitize_email",
    "sanitize_dict",
    # Audit Logging
    "AuditLogger",
    "AuditEventType",
    "get_audit_logger",
    "audit_log",
    # Brute Force Protection
    "BruteForceProtection",
    "AccountLockoutReason",
    "LoginAttempt",
    "AccountLockout",
    "get_brute_force_protection",
    "record_failed_attempt",
    "record_successful_login",
    "is_account_locked",
]
