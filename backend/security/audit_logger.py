"""
Audit Logging Module

Provides comprehensive audit trail for sensitive operations:
- Authentication attempts (success/failure)
- Authorization decisions
- Sensitive data access
- Configuration changes
- Database modifications (CRUD operations on sensitive records)
"""

import logging
import json
from typing import Any, Dict, Optional
from datetime import datetime
from enum import Enum
from pathlib import Path
import hashlib
from functools import wraps
import os


class AuditEventType(str, Enum):
    """Types of audit events to track."""
    # Authentication events
    LOGIN_ATTEMPT = "LOGIN_ATTEMPT"
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILURE = "LOGIN_FAILURE"
    LOGOUT = "LOGOUT"
    API_KEY_USED = "API_KEY_USED"
    JWT_TOKEN_GENERATED = "JWT_TOKEN_GENERATED"
    JWT_TOKEN_VALIDATED = "JWT_TOKEN_VALIDATED"
    JWT_TOKEN_EXPIRED = "JWT_TOKEN_EXPIRED"

    # Authorization events
    AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"
    PERMISSION_DENIED = "PERMISSION_DENIED"

    # Data access events
    SENSITIVE_DATA_READ = "SENSITIVE_DATA_READ"
    SENSITIVE_DATA_WRITTEN = "SENSITIVE_DATA_WRITTEN"
    SENSITIVE_DATA_DELETED = "SENSITIVE_DATA_DELETED"
    CONFIG_CHANGED = "CONFIG_CHANGED"

    # API events
    API_RATE_LIMIT_EXCEEDED = "API_RATE_LIMIT_EXCEEDED"
    API_CALL_FAILED = "API_CALL_FAILED"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"

    # Security events
    BRUTE_FORCE_ATTEMPT = "BRUTE_FORCE_ATTEMPT"
    SUSPICIOUS_INPUT = "SUSPICIOUS_INPUT"
    HTTPS_ENFORCEMENT_VIOLATION = "HTTPS_ENFORCEMENT_VIOLATION"

    # System events
    SYSTEM_ERROR = "SYSTEM_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"


class AuditLogger:
    """
    Audit logger for tracking sensitive operations.

    Features:
    - Structured logging in JSON format
    - Separate audit log file
    - Event classification by type
    - Contextual information (user, IP, timestamp)
    - Sensitive data masking
    """

    def __init__(self, log_dir: str = "logs"):
        """
        Initialize audit logger.

        Args:
            log_dir: Directory to store audit logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Create separate audit logger
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)

        # Create file handler for audit log
        audit_log_path = self.log_dir / "audit.log"
        handler = logging.FileHandler(audit_log_path, encoding="utf-8")
        handler.setLevel(logging.INFO)

        # Create JSON formatter
        formatter = logging.Formatter(
            '%(message)s',
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)

        # Remove existing handlers to avoid duplicates
        self.logger.handlers = []
        self.logger.addHandler(handler)

        # Also log to console in debug mode
        if os.getenv("DEBUG_AUDIT", "").lower() == "true":
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        status: str = "SUCCESS",
        details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ):
        """
        Log an audit event.

        Args:
            event_type: Type of event (AuditEventType enum)
            user_id: User ID (if applicable)
            username: Username (if applicable)
            ip_address: Client IP address (if applicable)
            resource: Resource affected (e.g., "book:12345")
            action: Action performed (e.g., "READ", "WRITE", "DELETE")
            status: Event status (SUCCESS, FAILURE, PARTIAL)
            details: Additional context (dict)
            error_message: Error message if applicable
        """
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type.value,
            "status": status,
            "user_id": user_id,
            "username": username,
            "ip_address": ip_address,
            "resource": resource,
            "action": action,
            "details": details or {},
            "error_message": error_message,
        }

        # Remove None values to keep log clean
        event = {k: v for k, v in event.items() if v is not None}

        # Log as JSON
        self.logger.info(json.dumps(event, default=str))

    def log_authentication(
        self,
        username: str,
        ip_address: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ):
        """Log authentication attempt."""
        event_type = (
            AuditEventType.LOGIN_SUCCESS if success
            else AuditEventType.LOGIN_FAILURE
        )
        status = "SUCCESS" if success else "FAILURE"

        self.log_event(
            event_type=event_type,
            username=username,
            ip_address=ip_address,
            status=status,
            error_message=error_message,
        )

    def log_authorization_denied(
        self,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        resource: Optional[str] = None,
        reason: Optional[str] = None,
    ):
        """Log authorization denial."""
        self.log_event(
            event_type=AuditEventType.AUTHORIZATION_DENIED,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            resource=resource,
            status="FAILURE",
            details={"reason": reason},
        )

    def log_sensitive_data_access(
        self,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        resource: str = "unknown",
        action: str = "READ",
        field_count: int = 1,
    ):
        """Log access to sensitive data."""
        self.log_event(
            event_type=AuditEventType.SENSITIVE_DATA_READ,
            user_id=user_id,
            username=username,
            resource=resource,
            action=action,
            details={"field_count": field_count},
        )

    def log_config_change(
        self,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        config_key: str = "unknown",
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
    ):
        """Log configuration change."""
        self.log_event(
            event_type=AuditEventType.CONFIG_CHANGED,
            user_id=user_id,
            username=username,
            resource=f"config:{config_key}",
            action="MODIFY",
            details={
                "config_key": config_key,
                "old_value_hash": self._hash_value(old_value),
                "new_value_hash": self._hash_value(new_value),
            },
        )

    def log_rate_limit_exceeded(
        self,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        endpoint: Optional[str] = None,
        limit: int = 0,
        current: int = 0,
    ):
        """Log rate limit exceeded."""
        self.log_event(
            event_type=AuditEventType.API_RATE_LIMIT_EXCEEDED,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            resource=endpoint,
            status="FAILURE",
            details={"limit": limit, "current_count": current},
        )

    def log_brute_force_attempt(
        self,
        username: str,
        ip_address: Optional[str] = None,
        attempt_count: int = 1,
    ):
        """Log potential brute force attack."""
        self.log_event(
            event_type=AuditEventType.BRUTE_FORCE_ATTEMPT,
            username=username,
            ip_address=ip_address,
            status="FAILURE",
            details={"attempt_count": attempt_count},
        )

    def log_https_violation(
        self,
        ip_address: Optional[str] = None,
        resource: Optional[str] = None,
        protocol: str = "http",
    ):
        """Log HTTPS enforcement violation."""
        self.log_event(
            event_type=AuditEventType.HTTPS_ENFORCEMENT_VIOLATION,
            ip_address=ip_address,
            resource=resource,
            status="FAILURE",
            details={"used_protocol": protocol},
        )

    @staticmethod
    def _hash_value(value: Optional[str]) -> Optional[str]:
        """Hash sensitive values for log storage (PII protection)."""
        if value is None:
            return None
        if len(value) > 50:
            # For long values, hash them to prevent storing PII
            return hashlib.sha256(value.encode()).hexdigest()[:16]
        # For short values, still hash for consistency
        return hashlib.sha256(value.encode()).hexdigest()[:16]

    def get_log_path(self) -> Path:
        """Get path to audit log file."""
        return self.log_dir / "audit.log"


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def audit_log(
    event_type: AuditEventType,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    resource: Optional[str] = None,
):
    """
    Decorator to automatically log function calls.

    Usage:
        @audit_log(AuditEventType.SENSITIVE_DATA_READ, resource="user_profiles")
        async def get_user_profile(user_id: int):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_audit_logger()
            try:
                result = await func(*args, **kwargs)
                logger.log_event(
                    event_type=event_type,
                    user_id=user_id,
                    username=username,
                    resource=resource,
                    status="SUCCESS",
                )
                return result
            except Exception as e:
                logger.log_event(
                    event_type=event_type,
                    user_id=user_id,
                    username=username,
                    resource=resource,
                    status="FAILURE",
                    error_message=str(e),
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_audit_logger()
            try:
                result = func(*args, **kwargs)
                logger.log_event(
                    event_type=event_type,
                    user_id=user_id,
                    username=username,
                    resource=resource,
                    status="SUCCESS",
                )
                return result
            except Exception as e:
                logger.log_event(
                    event_type=event_type,
                    user_id=user_id,
                    username=username,
                    resource=resource,
                    status="FAILURE",
                    error_message=str(e),
                )
                raise

        # Return async or sync wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


import asyncio  # Import at end to avoid circular dependency
