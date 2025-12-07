# Security Quick Reference Guide

**Phase 1 Implementation Quick Guide**

---

## Quick Integration Checklist

### 1. HTTPS Enforcement (2 minutes)
```python
from backend.security import enforce_url

# Before making external API call
url = enforce_url("http://api.example.com")  # Raises if not HTTPS (production)

# Or upgrade automatically
from backend.security import get_secure_url
url = get_secure_url("http://api.example.com")
```

### 2. Input Sanitization (2 minutes)
```python
from backend.security import sanitize_string, sanitize_dict

# In your route handler
@router.post("/search")
async def search(q: str):
    q_clean = sanitize_string(q, "search_query")
    # Use q_clean for database query
```

### 3. Audit Logging (2 minutes)
```python
from backend.security import AuditEventType, get_audit_logger

audit_logger = get_audit_logger()

# Log authentication attempt
audit_logger.log_authentication(
    username="user@example.com",
    ip_address=request.client.host,
    success=True
)
```

### 4. Brute Force Protection (2 minutes)
```python
from backend.security import record_failed_attempt, is_account_locked

# Check lockout status
is_locked, msg = is_account_locked("user@example.com")
if is_locked:
    raise HTTPException(status_code=429, detail=msg)

# Record failed attempt
allow_retry, warning = record_failed_attempt("user@example.com", "192.168.1.1")
if not allow_retry:
    raise HTTPException(status_code=429)
```

---

## Environment Variables Quick Setup

```bash
# Security Configuration
export ENFORCE_HTTPS=true
export MAX_LOGIN_ATTEMPTS=5
export LOGIN_LOCKOUT_DURATION=900
export AUDIT_LOGGING_ENABLED=true
export JWT_SECRET=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')

# For Development Only
export ALLOW_LOCALHOST_HTTP=true
export DEBUG_AUDIT=true
```

---

## Common Patterns

### Pattern 1: Sanitize and Validate User Input
```python
from backend.security import sanitize_dict

@router.post("/books")
async def create_book(book: BookCreate):
    # Sanitize all input
    data = sanitize_dict(book.dict(), "book_data")

    # Use sanitized data
    db_book = Book(**data)
    db.add(db_book)
    db.commit()
```

### Pattern 2: Log Sensitive Operations
```python
from backend.security import AuditEventType

@router.delete("/admin/users/{user_id}")
async def delete_user(user_id: int, current_user: User = Depends(get_current_user)):
    user = db.query(User).get(user_id)
    db.delete(user)
    db.commit()

    # Log the action
    audit_logger.log_event(
        event_type=AuditEventType.SENSITIVE_DATA_DELETED,
        user_id=current_user.id,
        resource=f"user:{user_id}",
        action="DELETE"
    )
```

### Pattern 3: Protect Login Endpoint
```python
from backend.security import (
    record_failed_attempt,
    record_successful_login,
    is_account_locked
)

@router.post("/login")
async def login(credentials: LoginRequest, request: Request):
    # Check lockout
    is_locked, msg = is_account_locked(credentials.username)
    if is_locked:
        raise HTTPException(status_code=429, detail=msg)

    # Authenticate
    user = authenticate_user(credentials.username, credentials.password)
    if not user:
        allow_retry, _ = record_failed_attempt(
            credentials.username,
            request.client.host
        )
        if not allow_retry:
            raise HTTPException(status_code=429, detail="Account locked")
        raise HTTPException(status_code=401)

    # Success
    record_successful_login(credentials.username, request.client.host)
    return {"token": generate_token(user.id)}
```

### Pattern 4: Enforce HTTPS in Integrations
```python
from backend.security import enforce_url

class MyIntegrationClient:
    def __init__(self, base_url: str):
        self.base_url = enforce_url(base_url, "my_integration")
        # HTTPS guaranteed in production
```

---

## Log Files

### Audit Log Location
```
logs/audit.log
```

### View Recent Audit Events
```bash
# Last 20 events
tail -20 logs/audit.log

# Failed logins only
grep "LOGIN_FAILURE" logs/audit.log

# Specific user
grep "username:.*user@example.com" logs/audit.log

# Pretty print (if using jq)
cat logs/audit.log | jq '.'
```

---

## Configuration Quick Reference

| Setting | Env Variable | Default | Description |
|---------|--------------|---------|-------------|
| HTTPS Enforcement | ENFORCE_HTTPS | true | Require HTTPS for external APIs |
| Localhost Exception | ALLOW_LOCALHOST_HTTP | false | Allow http://localhost (dev only) |
| Max Login Attempts | MAX_LOGIN_ATTEMPTS | 5 | Failed attempts before lockout |
| Lockout Duration | LOGIN_LOCKOUT_DURATION | 900 | Lockout time in seconds (15 min) |
| Attempt Window | LOGIN_ATTEMPT_WINDOW | 600 | Time window for counting attempts (10 min) |
| IP Rate Limit | IP_RATE_LIMIT | 20 | Max attempts per IP per window |
| Audit Logging | AUDIT_LOGGING_ENABLED | true | Enable audit log tracking |
| Audit Log Level | AUDIT_LOG_LEVEL | INFO | Logging level (DEBUG, INFO, WARNING) |
| JWT Secret | JWT_SECRET | - | MUST SET - use secrets module |

---

## Troubleshooting

### HTTPS Enforcement Error
**Error:** `HTTPSEnforcementError: HTTPS enforcement enabled`
**Solution:**
```bash
# Development: Allow localhost HTTP
export ALLOW_LOCALHOST_HTTP=true

# Production: Use HTTPS URLs
# Change: http://api.example.com → https://api.example.com
```

### Input Sanitization Too Strict
**Issue:** Legitimate input being rejected
**Solution:** Use standard mode (logs warning instead of raising)
```python
from backend.security import get_sanitizer

sanitizer = get_sanitizer(strict=False)  # Default
result = sanitizer.sanitize_string(input_value)
```

### Account Locked
**Error:** "Account locked. Try again in X seconds"
**Solution:** Wait for lockout duration to expire, or admin unlock:
```python
from backend.security import get_brute_force_protection

protection = get_brute_force_protection()
protection.unlock_account("user@example.com")
```

### Audit Log Not Being Written
**Issue:** No audit.log file created
**Solution:** Check directory permissions
```bash
# Ensure logs/ directory exists and is writable
mkdir -p logs/
chmod 755 logs/

# Enable debug to see logging
export DEBUG_AUDIT=true
```

---

## Testing Security Modules

### Test HTTPS Enforcement
```bash
python -c "
from backend.security import enforce_url, HTTPSEnforcementError
try:
    enforce_url('http://api.example.com')
except HTTPSEnforcementError:
    print('✓ HTTPS enforcement working')
"
```

### Test Input Sanitization
```bash
python -c "
from backend.security import sanitize_string
xss = '<script>alert(1)</script>'
clean = sanitize_string(xss, 'test')
assert '<script>' not in clean
print('✓ XSS prevention working')
"
```

### Test Brute Force Protection
```bash
python -c "
from backend.security import record_failed_attempt, is_account_locked
for i in range(5):
    allow, msg = record_failed_attempt('testuser', '192.168.1.1')
is_locked, msg = is_account_locked('testuser')
assert is_locked
print('✓ Brute force protection working')
"
```

---

## Next: Phase 2

Ready to proceed to Phase 2 (Code Quality)?

See: [PHASE_2_CODE_QUALITY.md](PHASE_2_CODE_QUALITY.md) (when created)

Key items for Phase 2:
1. Split monolithic files (abs_client.py, ratio_emergency_service.py)
2. Standardize error handling (exceptions vs dicts)
3. Add resource cleanup (finally blocks)
4. Implement dependency injection
5. Consolidate workflow executors

---

**Last Updated:** 2025-12-01
**Status:** Phase 1 Complete - Ready for Integration
