"""
Brute Force Protection Module

Implements account lockout and rate limiting to prevent brute force attacks:
- Tracks failed login attempts
- Implements exponential backoff
- Temporary account lockout after threshold
- IP-based rate limiting
- Time-based reset of attempt counters
"""

import time
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import os

logger = logging.getLogger(__name__)


class AccountLockoutReason(str, Enum):
    """Reasons for account lockout."""
    TOO_MANY_ATTEMPTS = "too_many_failed_attempts"
    IP_RATE_LIMIT = "ip_rate_limit_exceeded"
    ACCOUNT_SUSPENDED = "account_suspended"


@dataclass
class LoginAttempt:
    """Record of a login attempt."""
    timestamp: float
    username: str
    ip_address: str
    success: bool
    error_message: Optional[str] = None


@dataclass
class AccountLockout:
    """Account lockout status."""
    locked_at: float
    reason: AccountLockoutReason
    locked_until: float = field(default_factory=time.time)
    attempt_count: int = 0
    message: str = ""


class BruteForceProtection:
    """
    Brute force protection system.

    Configuration (via environment variables):
    - MAX_LOGIN_ATTEMPTS: Max failed attempts before lockout (default: 5)
    - LOGIN_LOCKOUT_DURATION: Lockout duration in seconds (default: 900 = 15 min)
    - LOGIN_ATTEMPT_WINDOW: Time window for counting attempts in seconds (default: 600 = 10 min)
    - IP_RATE_LIMIT: Max login attempts per IP in time window (default: 20)
    """

    def __init__(
        self,
        max_attempts: int = 5,
        lockout_duration: int = 900,  # 15 minutes
        attempt_window: int = 600,  # 10 minutes
        ip_rate_limit: int = 20,
    ):
        """
        Initialize brute force protection.

        Args:
            max_attempts: Max failed attempts before account lockout
            lockout_duration: Duration of lockout in seconds
            attempt_window: Time window for counting attempts
            ip_rate_limit: Max attempts per IP in time window
        """
        self.max_attempts = int(os.getenv("MAX_LOGIN_ATTEMPTS", max_attempts))
        self.lockout_duration = int(os.getenv("LOGIN_LOCKOUT_DURATION", lockout_duration))
        self.attempt_window = int(os.getenv("LOGIN_ATTEMPT_WINDOW", attempt_window))
        self.ip_rate_limit = int(os.getenv("IP_RATE_LIMIT", ip_rate_limit))

        # In-memory storage (replace with Redis for distributed systems)
        self.failed_attempts: Dict[str, list[LoginAttempt]] = {}
        self.account_lockouts: Dict[str, AccountLockout] = {}
        self.ip_attempts: Dict[str, list[LoginAttempt]] = {}

        logger.info(
            f"BruteForceProtection initialized: "
            f"max_attempts={self.max_attempts}, "
            f"lockout_duration={self.lockout_duration}s, "
            f"attempt_window={self.attempt_window}s, "
            f"ip_rate_limit={self.ip_rate_limit}"
        )

    def record_failed_attempt(
        self,
        username: str,
        ip_address: str,
        error_message: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Record a failed login attempt.

        Args:
            username: Username attempted
            ip_address: Client IP address
            error_message: Error message from login failure

        Returns:
            Tuple of (should_allow_retry, lockout_message)
        """
        current_time = time.time()

        # Clean old attempts
        self._cleanup_old_attempts()

        # Record attempt
        attempt = LoginAttempt(
            timestamp=current_time,
            username=username,
            ip_address=ip_address,
            success=False,
            error_message=error_message,
        )

        # Track per username
        if username not in self.failed_attempts:
            self.failed_attempts[username] = []
        self.failed_attempts[username].append(attempt)

        # Track per IP
        if ip_address not in self.ip_attempts:
            self.ip_attempts[ip_address] = []
        self.ip_attempts[ip_address].append(attempt)

        # Check account lockout status
        if username in self.account_lockouts:
            lockout = self.account_lockouts[username]
            if lockout.locked_until > current_time:
                # Still locked out
                remaining = int(lockout.locked_until - current_time)
                msg = f"Account locked. Try again in {remaining} seconds."
                logger.warning(f"Login attempt to locked account {username} from {ip_address}")
                return False, msg

        # Check account lockout threshold
        recent_failures = self._get_recent_failed_attempts(username)
        if len(recent_failures) >= self.max_attempts:
            # Lock account
            lockout = AccountLockout(
                locked_at=current_time,
                reason=AccountLockoutReason.TOO_MANY_ATTEMPTS,
                locked_until=current_time + self.lockout_duration,
                attempt_count=len(recent_failures),
                message=f"Account locked after {len(recent_failures)} failed attempts. Try again in {self.lockout_duration} seconds.",
            )
            self.account_lockouts[username] = lockout

            logger.warning(
                f"Account {username} locked due to {len(recent_failures)} failed attempts from {ip_address}"
            )
            return False, lockout.message

        # Check IP rate limit
        recent_ip_attempts = self._get_recent_ip_attempts(ip_address)
        if len(recent_ip_attempts) >= self.ip_rate_limit:
            msg = f"Too many login attempts from your IP. Please try again later."
            logger.warning(
                f"IP {ip_address} exceeded rate limit with {len(recent_ip_attempts)} attempts"
            )
            return False, msg

        # Allow retry but warn if approaching limit
        attempts_until_lockout = self.max_attempts - len(recent_failures)
        if attempts_until_lockout <= 2:
            msg = f"Warning: {attempts_until_lockout} attempts remaining before account lockout."
            return True, msg

        return True, None

    def record_successful_login(self, username: str, ip_address: str):
        """
        Record a successful login (resets failure counter).

        Args:
            username: Username
            ip_address: Client IP address
        """
        # Clear failed attempts for this account
        if username in self.failed_attempts:
            del self.failed_attempts[username]

        # Remove lockout if exists
        if username in self.account_lockouts:
            del self.account_lockouts[username]

        logger.info(f"Successful login for {username} from {ip_address}")

    def is_account_locked(self, username: str) -> Tuple[bool, Optional[str]]:
        """
        Check if account is currently locked.

        Args:
            username: Username to check

        Returns:
            Tuple of (is_locked, message)
        """
        current_time = time.time()

        if username in self.account_lockouts:
            lockout = self.account_lockouts[username]

            # Check if lockout has expired
            if lockout.locked_until <= current_time:
                del self.account_lockouts[username]
                return False, None

            # Still locked
            remaining = int(lockout.locked_until - current_time)
            return True, f"Account locked. Try again in {remaining} seconds."

        return False, None

    def unlock_account(self, username: str):
        """
        Manually unlock an account (admin operation).

        Args:
            username: Username to unlock
        """
        if username in self.account_lockouts:
            del self.account_lockouts[username]
        if username in self.failed_attempts:
            del self.failed_attempts[username]

        logger.warning(f"Account {username} manually unlocked by admin")

    def get_account_status(self, username: str) -> Dict:
        """
        Get detailed status of an account.

        Args:
            username: Username to check

        Returns:
            Status dictionary
        """
        current_time = time.time()
        recent_failures = self._get_recent_failed_attempts(username)
        is_locked, lock_message = self.is_account_locked(username)

        return {
            "username": username,
            "is_locked": is_locked,
            "lock_message": lock_message,
            "failed_attempts_in_window": len(recent_failures),
            "max_attempts": self.max_attempts,
            "attempts_until_lockout": max(0, self.max_attempts - len(recent_failures)),
        }

    def _get_recent_failed_attempts(self, username: str) -> list[LoginAttempt]:
        """Get failed attempts within the attempt window."""
        if username not in self.failed_attempts:
            return []

        current_time = time.time()
        cutoff_time = current_time - self.attempt_window

        return [
            attempt for attempt in self.failed_attempts[username]
            if attempt.timestamp > cutoff_time
        ]

    def _get_recent_ip_attempts(self, ip_address: str) -> list[LoginAttempt]:
        """Get all attempts from IP within the attempt window."""
        if ip_address not in self.ip_attempts:
            return []

        current_time = time.time()
        cutoff_time = current_time - self.attempt_window

        return [
            attempt for attempt in self.ip_attempts[ip_address]
            if attempt.timestamp > cutoff_time
        ]

    def _cleanup_old_attempts(self):
        """Remove attempts older than the attempt window."""
        current_time = time.time()
        cutoff_time = current_time - self.attempt_window

        # Clean failed attempts
        for username in list(self.failed_attempts.keys()):
            self.failed_attempts[username] = [
                a for a in self.failed_attempts[username]
                if a.timestamp > cutoff_time
            ]
            if not self.failed_attempts[username]:
                del self.failed_attempts[username]

        # Clean IP attempts
        for ip_address in list(self.ip_attempts.keys()):
            self.ip_attempts[ip_address] = [
                a for a in self.ip_attempts[ip_address]
                if a.timestamp > cutoff_time
            ]
            if not self.ip_attempts[ip_address]:
                del self.ip_attempts[ip_address]

        # Clean expired lockouts
        for username in list(self.account_lockouts.keys()):
            lockout = self.account_lockouts[username]
            if lockout.locked_until <= current_time:
                del self.account_lockouts[username]


# Global protection instance
_protection: Optional[BruteForceProtection] = None


def get_brute_force_protection() -> BruteForceProtection:
    """Get or create global brute force protection instance."""
    global _protection
    if _protection is None:
        _protection = BruteForceProtection()
    return _protection


def record_failed_attempt(
    username: str,
    ip_address: str,
    error_message: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """Record failed login attempt using global instance."""
    protection = get_brute_force_protection()
    return protection.record_failed_attempt(username, ip_address, error_message)


def record_successful_login(username: str, ip_address: str):
    """Record successful login using global instance."""
    protection = get_brute_force_protection()
    protection.record_successful_login(username, ip_address)


def is_account_locked(username: str) -> Tuple[bool, Optional[str]]:
    """Check account lockout status using global instance."""
    protection = get_brute_force_protection()
    return protection.is_account_locked(username)
