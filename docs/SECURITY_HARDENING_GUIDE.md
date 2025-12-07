# Security Hardening Guide for Production

**Version:** 1.0
**Date:** 2025-12-01
**Status:** Production Ready

This guide provides comprehensive security hardening procedures for deploying MAMcrawler in production environments.

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Secrets Management](#secrets-management)
3. [HTTPS/TLS Configuration](#httpstls-configuration)
4. [Authentication Hardening](#authentication-hardening)
5. [Authorization & Access Control](#authorization--access-control)
6. [Input Validation & Sanitization](#input-validation--sanitization)
7. [Audit Logging & Monitoring](#audit-logging--monitoring)
8. [Database Security](#database-security)
9. [Network Security](#network-security)
10. [API Security](#api-security)
11. [Regular Security Updates](#regular-security-updates)
12. [Incident Response](#incident-response)

---

## Pre-Deployment Checklist

Before deploying to production, verify all items:

### Critical Items (MUST COMPLETE)
- [ ] All credentials rotated and changed from defaults
- [ ] `.env` file removed from git history
- [ ] JWT_SECRET configured and not leaked anywhere
- [ ] SSL/TLS certificates provisioned and valid
- [ ] Database credentials set to strong, unique values
- [ ] API keys for all third-party services rotated
- [ ] CORS allowed origins restricted to known domains
- [ ] API key rotation policy documented
- [ ] Backup and recovery procedures tested
- [ ] Security audit completed and issues resolved

### High Priority Items
- [ ] HTTPS enforced for all external connections
- [ ] Brute force protection enabled
- [ ] Audit logging enabled and monitored
- [ ] Input sanitization enabled
- [ ] Rate limiting configured appropriately
- [ ] Error messages sanitized (no stack traces to clients)
- [ ] Security headers configured (HSTS, X-Frame-Options, etc.)
- [ ] Database backups encrypted and stored securely
- [ ] Monitoring and alerting configured
- [ ] Documentation updated with security procedures

### Medium Priority Items
- [ ] Dependency vulnerabilities scanned and addressed
- [ ] Load balancer/reverse proxy configured
- [ ] WAF (Web Application Firewall) rules configured
- [ ] Log aggregation and retention policies set
- [ ] Disaster recovery plan documented and tested
- [ ] Security team contact procedures documented
- [ ] Incident response runbook created

---

## Secrets Management

### 1. Environment Variables Setup

**Development Environment:**
```bash
# Create .env file (NEVER commit to git)
export ANTHROPIC_API_KEY="sk-..."
export PROWLARR_API_KEY="..."
export ABS_TOKEN="..."
export MAM_USERNAME="..."
export MAM_PASSWORD="..."
export QBITTORRENT_PASSWORD="..."
export POSTGRES_PASSWORD="..."
export JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
```

**Production Environment:**

Use environment-specific secrets management:

**Option 1: AWS Secrets Manager**
```python
# backend/config.py
import boto3

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='us-east-1')
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except Exception as e:
        logger.error(f"Failed to retrieve secret {secret_name}: {e}")
        raise
```

**Option 2: HashiCorp Vault**
```python
import hvac

def get_secret_from_vault(secret_path):
    client = hvac.Client(url=os.getenv("VAULT_ADDR"), token=os.getenv("VAULT_TOKEN"))
    response = client.secrets.kv.read_secret_version(path=secret_path)
    return response['data']['data']
```

**Option 3: Environment Variables Only (Least Flexible)**
```bash
# Set via deployment platform (Kubernetes, Heroku, Docker Compose, etc.)
export ANTHROPIC_API_KEY="..."  # Set by deployment platform
```

### 2. Secrets Rotation Policy

**Every 90 Days:**
- [ ] Rotate all API keys (MAM, Prowlarr, AudiobookShelf, Hardcover, Google Books)
- [ ] Rotate database password
- [ ] Rotate JWT_SECRET (invalidates existing tokens)
- [ ] Rotate qBittorrent password

**On Suspected Compromise:**
- [ ] Immediately rotate compromised credential
- [ ] Review access logs for unauthorized activity
- [ ] Reset any related accounts
- [ ] Update related systems

**Rotation Procedure:**
```bash
# 1. Generate new credential
NEW_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')

# 2. Update in secrets management system
aws secretsmanager update-secret --secret-id mamcrawler/api-key --secret-string "$NEW_KEY"

# 3. Update application (rolling deployment)
kubectl set env deployment/mamcrawler API_KEY="$NEW_KEY"

# 4. Monitor for errors
kubectl logs -f deployment/mamcrawler | grep -i error

# 5. Verify in monitoring dashboard
# Check that no auth errors spike

# 6. Update documentation
echo "API key rotated on $(date)" >> ROTATION_LOG.md
```

### 3. Secrets Storage

**NEVER Store:**
- ✗ In source code (including comments)
- ✗ In git history (use BFG repo-cleaner to remove)
- ✗ In docker images (use multi-stage builds)
- ✗ In logs or error messages
- ✗ In plaintext files (except .env, which is .gitignored)

**ALWAYS Store:**
- ✓ In environment variables
- ✓ In encrypted vaults (AWS Secrets Manager, HashiCorp Vault)
- ✓ In secrets management platform (Kubernetes Secrets, Docker Secrets)
- ✓ With restricted access (least privilege principle)

---

## HTTPS/TLS Configuration

### 1. Enable HTTPS Enforcement

```python
# backend/config.py
from backend.security import HTTPSEnforcer

ENFORCE_HTTPS = os.getenv("ENFORCE_HTTPS", "true").lower() == "true"
HTTPS_ENFORCER = HTTPSEnforcer(enforce=ENFORCE_HTTPS)

# All external API calls
class Settings(BaseSettings):
    QBITTORRENT_URL: str = "https://qbittorrent.example.com"  # Force HTTPS
    AUDIOBOOKSHELF_URL: str = "https://abs.example.com"
    PROWLARR_URL: str = "https://prowlarr.example.com"
```

### 2. SSL/TLS Certificate Setup

**Using Let's Encrypt (Recommended):**
```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --standalone -d mamcrawler.example.com

# Auto-renewal (runs daily)
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# Verify
sudo certbot certificates
```

**Certificate Paths:**
```
/etc/letsencrypt/live/mamcrawler.example.com/
├── cert.pem       # SSL certificate
├── chain.pem      # Certificate chain
├── fullchain.pem  # Full certificate chain (use this)
└── privkey.pem    # Private key
```

### 3. nginx Configuration

```nginx
# /etc/nginx/sites-available/mamcrawler
upstream mamcrawler {
    server localhost:8000;
}

server {
    # HTTP redirect
    listen 80;
    server_name mamcrawler.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    # HTTPS
    listen 443 ssl http2;
    server_name mamcrawler.example.com;

    # SSL Certificates
    ssl_certificate /etc/letsencrypt/live/mamcrawler.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mamcrawler.example.com/privkey.pem;

    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Proxy to FastAPI
    location / {
        proxy_pass http://mamcrawler;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. FastAPI Configuration

```python
# backend/main.py
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app = FastAPI()

# Redirect HTTP to HTTPS (if not behind reverse proxy)
if ENVIRONMENT == "production" and not BEHIND_PROXY:
    app.add_middleware(HTTPSRedirectMiddleware)

# Trust proxy headers when behind reverse proxy
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["mamcrawler.example.com", "www.mamcrawler.example.com"]
)
```

---

## Authentication Hardening

### 1. JWT Configuration

```python
# backend/config.py
JWT_ALGORITHM = "HS256"  # Use RS256 for better security in distributed systems
JWT_EXPIRATION_DELTA = timedelta(hours=1)  # Short-lived tokens
JWT_REFRESH_EXPIRATION_DELTA = timedelta(days=7)  # Longer refresh token

# Ensure JWT_SECRET is set
if not os.getenv("JWT_SECRET"):
    raise ValueError("JWT_SECRET environment variable must be set in production")

# Rotate JWT secret regularly
JWT_SECRET = os.getenv("JWT_SECRET")
if len(JWT_SECRET) < 32:
    raise ValueError("JWT_SECRET must be at least 32 characters")
```

### 2. Password Policy

```python
# backend/auth.py
class PasswordValidator:
    MIN_LENGTH = 12
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGITS = True
    REQUIRE_SPECIAL = True

    @staticmethod
    def validate(password: str) -> Tuple[bool, Optional[str]]:
        """Validate password meets security requirements."""
        if len(password) < PasswordValidator.MIN_LENGTH:
            return False, f"Password must be at least {PasswordValidator.MIN_LENGTH} characters"

        if PasswordValidator.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"

        if PasswordValidator.REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"

        if PasswordValidator.REQUIRE_DIGITS and not any(c.isdigit() for c in password):
            return False, "Password must contain at least one digit"

        if PasswordValidator.REQUIRE_SPECIAL and not any(c in "!@#$%^&*" for c in password):
            return False, "Password must contain at least one special character (!@#$%^&*)"

        return True, None
```

### 3. Brute Force Protection

```python
# backend/routes/auth.py
from backend.security import record_failed_attempt, record_successful_login, is_account_locked

@router.post("/login")
async def login(credentials: LoginRequest):
    # Check if account is locked
    is_locked, lock_msg = is_account_locked(credentials.username)
    if is_locked:
        logger.warning(f"Attempted login to locked account: {credentials.username}")
        raise HTTPException(status_code=429, detail=lock_msg)

    # Attempt authentication
    user = authenticate_user(credentials.username, credentials.password)
    if not user:
        # Record failure
        allow_retry, warning = record_failed_attempt(
            credentials.username,
            request.client.host,
            error_message="Invalid credentials"
        )

        if not allow_retry:
            raise HTTPException(status_code=429, detail="Account locked due to too many failed attempts")

        logger.warning(f"Failed login attempt: {credentials.username} from {request.client.host}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Record success
    record_successful_login(credentials.username, request.client.host)
    return generate_token(user.id)
```

---

## Authorization & Access Control

### 1. Role-Based Access Control (RBAC)

```python
# backend/models/user.py
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    READONLY = "readonly"

class User(Base):
    __tablename__ = "users"
    id: int = Column(Integer, primary_key=True)
    username: str = Column(String(255), unique=True)
    role: UserRole = Column(Enum(UserRole), default=UserRole.USER)
    is_active: bool = Column(Boolean, default=True)
```

### 2. Permission Decorators

```python
# backend/auth.py
from functools import wraps
from fastapi import HTTPException, status, Depends

def require_role(*roles: UserRole):
    """Decorator to require specific roles."""
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker

@router.delete("/users/{user_id}")
async def delete_user(user_id: int, current_user: User = Depends(require_role(UserRole.ADMIN))):
    # Only admin can delete users
    ...
```

---

## Input Validation & Sanitization

### 1. Enable Input Sanitization

```python
# backend/routes/books.py
from backend.security import sanitize_dict, sanitize_string

@router.post("/books")
async def create_book(book: BookCreate):
    # Sanitize input
    data = book.dict()
    data = sanitize_dict(data, "book_data")

    # Proceed with sanitized data
    db_book = Book(**data)
    db.add(db_book)
    db.commit()
    return db_book
```

### 2. Search Input Validation

```python
# backend/routes/search.py
@router.get("/search")
async def search(
    q: str = Query(..., min_length=1, max_length=255),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    # Pydantic validation + sanitization
    q_clean = sanitize_string(q, "search_query")

    # Perform search with sanitized input
    results = db.query(Book).filter(
        Book.title.ilike(f"%{q_clean}%")
    ).limit(limit).offset(offset).all()

    return results
```

---

## Audit Logging & Monitoring

### 1. Enable Audit Logging

```python
# backend/config.py
AUDIT_LOGGING_ENABLED = os.getenv("AUDIT_LOGGING_ENABLED", "true").lower() == "true"
AUDIT_LOG_LEVEL = os.getenv("AUDIT_LOG_LEVEL", "INFO")
```

### 2. Log Sensitive Operations

```python
# backend/routes/admin.py
from backend.security import AuditEventType, get_audit_logger

audit_logger = get_audit_logger()

@router.post("/admin/users/{user_id}/disable")
async def disable_user(user_id: int, current_user: User = Depends(require_role(UserRole.ADMIN))):
    user = db.query(User).get(user_id)
    user.is_active = False
    db.commit()

    # Log the action
    audit_logger.log_event(
        event_type=AuditEventType.CONFIG_CHANGED,
        user_id=current_user.id,
        username=current_user.username,
        resource=f"user:{user_id}",
        action="DISABLE",
        details={"previous_status": "active"}
    )

    return {"message": "User disabled"}
```

### 3. Monitor Audit Logs

```bash
# View recent audit events
tail -f logs/audit.log | grep -E "FAILURE|DENIED|LOCKED"

# Check for suspicious patterns
jq 'select(.event_type == "BRUTE_FORCE_ATTEMPT")' logs/audit.log

# Generate audit report
jq -s 'group_by(.event_type) | map({event_type: .[0].event_type, count: length})' logs/audit.log
```

---

## Database Security

### 1. PostgreSQL Security

```sql
-- Create dedicated database user with limited permissions
CREATE USER mamcrawler_user WITH PASSWORD 'strong_password_here';

-- Create database
CREATE DATABASE mamcrawler OWNER mamcrawler_user;

-- Restrict user permissions
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO mamcrawler_user;
GRANT CREATE ON SCHEMA public TO mamcrawler_user;

-- Restrict to specific tables
REVOKE ALL ON public.users FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE ON public.users TO mamcrawler_user;
GRANT SELECT ON public.books TO mamcrawler_user;

-- Enable SSL connections
ALTER SYSTEM SET ssl = on;
SELECT pg_reload_conf();
```

### 2. Connection Security

```python
# backend/database.py
DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    "?sslmode=require"  # Require SSL
)

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "sslmode": "require",
        "sslcert": "/path/to/client-cert.pem",
        "sslkey": "/path/to/client-key.pem",
        "sslrootcert": "/path/to/root-cert.pem",
    }
)
```

### 3. Backup Encryption

```bash
#!/bin/bash
# backup.sh - Encrypted database backup

BACKUP_FILE="mamcrawler_$(date +%Y%m%d_%H%M%S).sql.gz"
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY}"

# Backup and encrypt
pg_dump $DATABASE_URL | gzip | openssl enc -aes-256-cbc -salt -out "$BACKUP_FILE"

# Upload to secure storage
aws s3 cp "$BACKUP_FILE" "s3://mamcrawler-backups/"

# Cleanup local backup
shred -vfz -n 10 "$BACKUP_FILE"
```

---

## Network Security

### 1. Firewall Rules

```bash
# Allow only necessary ports
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP redirect
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow 5432/tcp from database_server_ip  # PostgreSQL (internal only)
sudo ufw enable
```

### 2. DDoS Protection

```nginx
# nginx configuration for DDoS protection
limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;

server {
    location / {
        limit_req zone=general burst=20 nodelay;
        ...
    }

    location /api/ {
        limit_req zone=api burst=60 nodelay;
        ...
    }
}
```

### 3. IP Whitelisting

```python
# backend/middleware/ip_whitelist.py
from fastapi.middleware.trustedhost import TrustedHostMiddleware

ALLOWED_IPS = os.getenv("ALLOWED_IPS", "").split(",")

@app.middleware("http")
async def ip_whitelist(request: Request, call_next):
    if ALLOWED_IPS and request.client.host not in ALLOWED_IPS:
        logger.warning(f"Blocked access from IP: {request.client.host}")
        return JSONResponse({"detail": "Access denied"}, status_code=403)
    return await call_next(request)
```

---

## API Security

### 1. API Rate Limiting

```python
# backend/config.py
RATE_LIMIT_ENABLED = True
RATE_LIMITS = {
    "general": "100/hour",
    "auth": "5/hour",      # Stricter for auth endpoints
    "search": "200/hour",
    "download": "50/hour",
}
```

### 2. API Key Rotation

```python
# backend/routes/admin.py
@router.post("/admin/api-keys/rotate")
async def rotate_api_key(current_user: User = Depends(require_role(UserRole.ADMIN))):
    """Rotate current user's API key."""
    new_key = secrets.token_urlsafe(32)

    # Store hashed key
    key_hash = hash_password(new_key)
    current_user.api_key_hash = key_hash
    current_user.api_key_rotated_at = datetime.utcnow()

    db.commit()

    audit_logger.log_event(
        event_type=AuditEventType.CONFIG_CHANGED,
        user_id=current_user.id,
        resource=f"api_key:{current_user.id}",
        action="ROTATE",
    )

    return {
        "message": "API key rotated",
        "new_key": new_key,  # Only shown once
        "expires_at": (datetime.utcnow() + timedelta(days=90)).isoformat()
    }
```

### 3. CORS Configuration

```python
# backend/main.py
from fastapi.middleware.cors import CORSMiddleware

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "https://mamcrawler.example.com").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

---

## Regular Security Updates

### 1. Dependency Scanning

```bash
# Check for known vulnerabilities
pip install pip-audit
pip-audit

# Or with safety
pip install safety
safety check

# Or with Snyk
snyk test
```

### 2. Automated Updates

```bash
# Update dependencies monthly
pip list --outdated
pip install --upgrade -r requirements.txt

# Test after updates
pytest tests/
```

### 3. Security Patches

```bash
# Apply critical patches immediately
sudo apt-get update
sudo apt-get upgrade

# Check for critical CVEs
apt-cache policy python3
```

---

## Incident Response

### 1. Suspected Breach Procedure

If you suspect a security breach:

1. **Immediate Actions (Next 30 minutes):**
   - [ ] Revoke compromised credentials
   - [ ] Isolate affected systems
   - [ ] Preserve logs and evidence
   - [ ] Notify security team

2. **Investigation (Next 24 hours):**
   - [ ] Review audit logs
   - [ ] Identify scope of compromise
   - [ ] Check for unauthorized access
   - [ ] Scan for malware

3. **Recovery (Next 72 hours):**
   - [ ] Rebuild compromised systems from clean backups
   - [ ] Rotate all credentials
   - [ ] Deploy security patches
   - [ ] Verify system integrity

4. **Communication (Ongoing):**
   - [ ] Notify affected users
   - [ ] Inform security researchers
   - [ ] Update status page
   - [ ] File incident report

### 2. Contact Information

```
Security Team: security@example.com
On-Call Engineer: +1-XXX-XXX-XXXX
Security Alert Channel: #security-incidents (Slack)
```

### 3. Post-Incident Review

After any security incident:

1. Conduct root cause analysis
2. Document lessons learned
3. Update security procedures
4. Implement preventive measures
5. Share findings with team

---

## Compliance Checklist

- [ ] GDPR compliance (if handling EU user data)
- [ ] HIPAA compliance (if handling health data)
- [ ] PCI DSS compliance (if handling payment data)
- [ ] SOC 2 Type II audit ready
- [ ] Regular penetration testing scheduled
- [ ] Security policy documented
- [ ] Incident response plan in place
- [ ] Data retention policy enforced
- [ ] User consent management implemented
- [ ] Privacy policy updated

---

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [CIS Controls](https://www.cisecurity.org/cis-controls)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [PostgreSQL Security](https://www.postgresql.org/docs/current/sql-syntax.html)

---

**Last Updated:** 2025-12-01
**Next Review:** 2025-03-01
**Approved By:** Security Team
