# MAMcrawler - Audiobook Automation System Deployment Guide

**Week 1 Production Readiness - Complete Deployment Documentation**

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Development Environment Setup](#development-environment-setup)
3. [Quick Start - Development](#quick-start---development)
4. [Staging Deployment](#staging-deployment)
5. [Production Deployment](#production-deployment)
6. [Docker Deployment](#docker-deployment)
7. [Database Management](#database-management)
8. [Environment Configuration Reference](#environment-configuration-reference)
9. [Health Checks & Monitoring](#health-checks--monitoring)
10. [Troubleshooting Guide](#troubleshooting-guide)
11. [Rollback Procedures](#rollback-procedures)
12. [Security Checklist](#security-checklist)

---

## Prerequisites

### System Requirements

**Development & Staging:**
- OS: Linux (Ubuntu 20.04+), macOS, or Windows with WSL2
- Python: 3.11+
- RAM: 4GB minimum, 8GB recommended
- Disk: 20GB free (for dependencies, logs, database)

**Production:**
- OS: Linux (Ubuntu 22.04 LTS recommended)
- Python: 3.11+
- RAM: 8GB minimum, 16GB recommended
- Disk: 50GB free (for logs, archives, database backups)
- CPU: 4 cores minimum (2+ for worker processes)

### Required Software

```bash
# Linux (Ubuntu)
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev
sudo apt-get install -y postgresql postgresql-contrib postgresql-14-plpython3
sudo apt-get install -y nginx systemd-container curl wget git

# macOS
brew install python@3.11 postgresql nginx

# Windows - Install from official websites:
# - Python 3.11: https://www.python.org/downloads/
# - PostgreSQL 15+: https://www.postgresql.org/download/windows/
# - Git: https://git-scm.com/download/win
```

### External Services (Required)

1. **PostgreSQL 15+** - Database backend
2. **Audiobookshelf** - Audiobook library management
3. **qBittorrent** - Torrent client
4. **Prowlarr** - Indexer aggregation
5. **Google Books API** - Metadata enrichment
6. **MAM Account** - Torrent source (email/password)

### API Keys & Credentials

Create a credentials file with the following:

```env
# FastAPI Backend
API_KEY=generate_with_$(openssl rand -hex 32)
SECRET_KEY=generate_with_$(openssl rand -hex 32)
PASSWORD_SALT=generate_with_$(openssl rand -hex 32)

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/mamcrawler

# External Services
ABS_URL=http://audiobookshelf:13378
ABS_TOKEN=your_abs_token_here

QB_HOST=http://qbittorrent:8080
QB_USERNAME=admin
QB_PASSWORD=secure_password

PROWLARR_URL=http://prowlarr:9696
PROWLARR_API_KEY=your_prowlarr_api_key

GOOGLE_BOOKS_API_KEY=your_google_books_key

MAM_USERNAME=your_email@example.com
MAM_PASSWORD=your_mam_password
```

---

## Development Environment Setup

### 1. Clone Repository

```bash
git clone <repository-url> MAMcrawler
cd MAMcrawler
git checkout main
```

### 2. Create Virtual Environment

```bash
# Linux/macOS
python3.11 -m venv venv
source venv/bin/activate

# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1

# Windows Command Prompt
python -m venv venv
venv\Scripts\activate.bat
```

### 3. Install Dependencies

```bash
pip install --upgrade pip setuptools wheel
pip install -r backend/requirements.txt
pip install -r requirements_catalog.txt

# Development tools
pip install black flake8 mypy pytest pytest-asyncio pytest-cov
```

### 4. Setup Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install

# Run manually before committing
pre-commit run --all-files
```

### 5. Configure IDE

**VS Code (.vscode/settings.json):**
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length=100"],
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.python"
  }
}
```

**PyCharm:**
1. Preferences → Project → Python Interpreter
2. Select virtual environment from `venv/bin/python`
3. Enable Black formatter: Tools → Python Integrated Tools → Code formatter

### 6. Create .env File

```bash
cp .env.example .env
# Edit .env with your local development credentials
```

### 7. Verify Setup

```bash
# Test Python import
python -c "from fastapi import FastAPI; print('FastAPI OK')"

# Test database
python -c "from backend.config import get_settings; print('Config OK')"

# Run tests
pytest backend/tests -v --tb=short
```

---

## Quick Start - Development

### 1. Start Database

```bash
# PostgreSQL (if running locally)
# Linux:
sudo systemctl start postgresql

# macOS:
brew services start postgresql

# Or use Docker:
docker run -d \
  -e POSTGRES_PASSWORD=localdev \
  -e POSTGRES_DB=mamcrawler_dev \
  -p 5432:5432 \
  postgres:15-alpine
```

### 2. Initialize Database Schema

```bash
# Create database
createdb -U postgres mamcrawler_dev

# Run migrations
alembic upgrade head
```

### 3. Start FastAPI Backend

```bash
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

API available at: http://127.0.0.1:8000

Docs available at: http://127.0.0.1:8000/docs

### 4. Run Tests

```bash
# All tests
pytest backend/tests -v

# Specific test file
pytest backend/tests/test_config.py -v

# With coverage
pytest backend/tests --cov=backend --cov-report=html
```

### 5. Code Quality Checks

```bash
# Format code
black backend/

# Lint
flake8 backend/

# Type checking
mypy backend/

# Pre-commit (all checks)
pre-commit run --all-files
```

---

## Staging Deployment

### Environment: Remote Linux Server

**Server Specs:** Ubuntu 22.04 LTS, 4-8GB RAM, 30GB disk

### Step 1: Server Preparation

```bash
# SSH into server
ssh ubuntu@staging.example.com

# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev
sudo apt-get install -y postgresql postgresql-contrib nginx git curl wget

# Create application user
sudo useradd -m -s /bin/bash mamcrawler
sudo usermod -aG sudo mamcrawler
su - mamcrawler
```

### Step 2: Clone Application

```bash
cd /opt
sudo git clone <repository-url> mamcrawler
sudo chown -R mamcrawler:mamcrawler mamcrawler
cd mamcrawler
```

### Step 3: Setup Python Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
```

### Step 4: Database Setup

```bash
# Create PostgreSQL database
sudo -u postgres psql << EOF
CREATE DATABASE mamcrawler_staging;
CREATE USER mamcrawler_app WITH PASSWORD 'staging_password_change_me';
ALTER ROLE mamcrawler_app SET client_encoding TO 'utf8';
ALTER ROLE mamcrawler_app SET default_transaction_isolation TO 'read committed';
ALTER ROLE mamcrawler_app SET default_transaction_deferrable TO on;
ALTER ROLE mamcrawler_app SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE mamcrawler_staging TO mamcrawler_app;
EOF

# Run migrations
alembic upgrade head
```

### Step 5: Environment Configuration

```bash
# Create .env file
cat > /opt/mamcrawler/.env << 'EOF'
ENV=staging
DEBUG=False
API_DOCS=True
SECURITY_HEADERS=True

# Secrets (generate with: openssl rand -hex 32)
API_KEY=your_generated_api_key_here
SECRET_KEY=your_generated_secret_key_here
PASSWORD_SALT=your_generated_salt_here

# Database
DATABASE_URL=postgresql://mamcrawler_app:staging_password_change_me@localhost:5432/mamcrawler_staging

# API Configuration
APP_HOST=0.0.0.0
APP_PORT=8000
ALLOWED_ORIGINS=https://staging.example.com
ALLOWED_HOSTS=staging.example.com,localhost

# External Services (update with actual URLs)
ABS_URL=http://audiobookshelf-staging:13378
ABS_TOKEN=your_abs_token
QB_HOST=http://qbittorrent-staging:8080
QB_USERNAME=admin
QB_PASSWORD=change_me
PROWLARR_URL=http://prowlarr-staging:9696
PROWLARR_API_KEY=your_key

# Feature Flags
SCHEDULER_ENABLED=True
ENABLE_METADATA_CORRECTION=True
ENABLE_SERIES_COMPLETION=True
EOF

# Secure .env file
chmod 600 .env
```

### Step 6: Systemd Service Setup

```bash
# Create systemd service file
sudo tee /etc/systemd/system/mamcrawler.service > /dev/null << 'EOF'
[Unit]
Description=MAMcrawler Audiobook Automation API
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=notify
User=mamcrawler
WorkingDirectory=/opt/mamcrawler
Environment="PATH=/opt/mamcrawler/venv/bin"
EnvironmentFile=/opt/mamcrawler/.env
ExecStart=/opt/mamcrawler/venv/bin/uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --no-access-log
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable mamcrawler
sudo systemctl start mamcrawler

# Check status
sudo systemctl status mamcrawler
```

### Step 7: Nginx Reverse Proxy

```bash
# Create Nginx configuration
sudo tee /etc/nginx/sites-available/mamcrawler << 'EOF'
upstream mamcrawler_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name staging.example.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name staging.example.com;

    ssl_certificate /etc/letsencrypt/live/staging.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/staging.example.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=60r/m;
    limit_req zone=api burst=100 nodelay;

    location / {
        proxy_pass http://mamcrawler_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }

    location /health {
        access_log off;
        proxy_pass http://mamcrawler_backend;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/mamcrawler /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

### Step 8: SSL Certificate (Let's Encrypt)

```bash
# Install certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot certonly --nginx -d staging.example.com

# Setup auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

### Step 9: Verification

```bash
# Check API health
curl -k https://staging.example.com/health

# Check logs
sudo journalctl -u mamcrawler -f

# Run tests
source venv/bin/activate
pytest backend/tests -v
```

---

## Production Deployment

### Environment: Production Linux Server

**Server Specs:** Ubuntu 22.04 LTS, 8-16GB RAM, 50GB disk

### Step 1-4: Follow Staging Steps (1-4)

Use identical server preparation, cloning, Python environment, and database setup. Replace all "staging" references with "production".

### Step 5: Environment Configuration (Production)

```bash
# Create .env file with STRONG security
cat > /opt/mamcrawler/.env << 'EOF'
ENV=production
DEBUG=False
API_DOCS=False
SECURITY_HEADERS=True

# Secrets (MUST be strong: openssl rand -hex 32)
API_KEY=`openssl rand -hex 32`
SECRET_KEY=`openssl rand -hex 32`
PASSWORD_SALT=`openssl rand -hex 32`

# Database (Strong password, use secrets manager in production)
DATABASE_URL=postgresql://mamcrawler_app:production_strong_password_32_chars_min@localhost:5432/mamcrawler_prod

# API Configuration
APP_HOST=0.0.0.0
APP_PORT=8000
ALLOWED_ORIGINS=https://audiobook.example.com
ALLOWED_HOSTS=audiobook.example.com

# Scheduler
SCHEDULER_ENABLED=True
TASK_MAM_TIME=0 2 * * *
TASK_METADATA_TIME=0 1 * * *

# Data Retention
HISTORY_RETENTION_DAYS=90
FAILED_ATTEMPTS_RETENTION=permanent

# External Services (Production URLs)
ABS_URL=https://abs.internal.example.com
ABS_TOKEN=use_secrets_manager
QB_HOST=https://qbittorrent.internal.example.com
QB_USERNAME=use_secrets_manager
QB_PASSWORD=use_secrets_manager
PROWLARR_URL=https://prowlarr.internal.example.com
PROWLARR_API_KEY=use_secrets_manager
GOOGLE_BOOKS_API_KEY=use_secrets_manager

# Feature Flags (Conservative for production)
ENABLE_METADATA_CORRECTION=True
ENABLE_SERIES_COMPLETION=True
ENABLE_TOP10_DISCOVERY=True
GAP_ANALYSIS_ENABLED=True

# Genres (Conservative selection)
ENABLED_GENRES=Science Fiction,Fantasy,Mystery,Thriller
DISABLED_GENRES=Romance,Erotica,Adult

# Gap Analysis
GAP_MAX_DOWNLOADS_PER_RUN=10
GAP_SERIES_PRIORITY=True
GAP_AUTHOR_PRIORITY=True
MAM_MIN_SEEDS=5
MAM_TITLE_MATCH_THRESHOLD=0.90
EOF

chmod 600 .env
```

### Step 6: Systemd Service (Production Hardened)

```bash
sudo tee /etc/systemd/system/mamcrawler.service > /dev/null << 'EOF'
[Unit]
Description=MAMcrawler Audiobook Automation API (Production)
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=notify
User=mamcrawler
WorkingDirectory=/opt/mamcrawler
Environment="PATH=/opt/mamcrawler/venv/bin"
EnvironmentFile=/opt/mamcrawler/.env
PrivateTmp=yes
ProtectHome=yes
ProtectSystem=strict
ReadWritePaths=/opt/mamcrawler
NoNewPrivileges=true
ExecStart=/opt/mamcrawler/venv/bin/uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 8 \
    --worker-class uvicorn.workers.UvicornWorker \
    --no-access-log
Restart=on-failure
RestartSec=15
StandardOutput=journal
StandardError=journal
SyslogIdentifier=mamcrawler

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable mamcrawler
sudo systemctl start mamcrawler
```

### Step 7: Nginx (Production Hardened)

```bash
sudo tee /etc/nginx/sites-available/mamcrawler << 'EOF'
upstream mamcrawler_backend {
    least_conn;
    server 127.0.0.1:8000;
}

# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=60r/m;
limit_req_zone $binary_remote_addr zone=download_limit:10m rate=20r/h;
limit_req_zone $binary_remote_addr zone=health_limit:10m rate=100r/m;

server {
    listen 80;
    server_name audiobook.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name audiobook.example.com;

    ssl_certificate /etc/letsencrypt/live/audiobook.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/audiobook.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

    # Disable server tokens
    server_tokens off;

    # Access/Error logs
    access_log /var/log/nginx/mamcrawler_access.log combined;
    error_log /var/log/nginx/mamcrawler_error.log warn;

    # Health check endpoint (no rate limit)
    location /health {
        access_log off;
        proxy_pass http://mamcrawler_backend;
        limit_req zone=health_limit burst=50 nodelay;
    }

    # API routes with rate limiting
    location /api/ {
        limit_req zone=api_limit burst=100 nodelay;
        proxy_pass http://mamcrawler_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }

    # Download endpoint with stricter rate limiting
    location /api/downloads {
        limit_req zone=download_limit burst=20 nodelay;
        proxy_pass http://mamcrawler_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Default route
    location / {
        proxy_pass http://mamcrawler_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/mamcrawler /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### Step 8: Database Backups

```bash
# Create backup script
cat > /opt/mamcrawler/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/mamcrawler"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# PostgreSQL backup
pg_dump -U mamcrawler_app mamcrawler_prod | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete

echo "Backup completed: db_$DATE.sql.gz"
EOF

chmod +x /opt/mamcrawler/backup.sh

# Schedule daily at 3 AM
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/mamcrawler/backup.sh") | crontab -
```

### Step 9: Monitoring & Logging

```bash
# Configure log rotation
sudo tee /etc/logrotate.d/mamcrawler > /dev/null << 'EOF'
/var/log/mamcrawler/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 mamcrawler mamcrawler
    sharedscripts
    postrotate
        systemctl reload-or-restart mamcrawler > /dev/null 2>&1 || true
    endscript
}
EOF

# Create log directory
sudo mkdir -p /var/log/mamcrawler
sudo chown mamcrawler:mamcrawler /var/log/mamcrawler
sudo chmod 755 /var/log/mamcrawler
```

### Step 10: Final Security Hardening

```bash
# Firewall rules (if UFW enabled)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Fail2ban (for SSH brute-force protection)
sudo apt-get install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# SELinux (if applicable)
# sudo semanage fcontext -a -t admin_home_t "/opt/mamcrawler(/.*)?"
# sudo restorecon -Rv /opt/mamcrawler
```

---

## Docker Deployment

### Quick Start with Docker Compose

**File: docker-compose.yml (Production Configuration)**

```bash
docker-compose up -d --build
docker-compose logs -f mamcrawler
```

**Features:**
- PostgreSQL 15 container
- MAMcrawler API container
- Nginx reverse proxy
- Volume persistence for data, logs, backups
- Health checks on all services
- Resource limits for production stability

See `docker-compose.yml` in repository for complete configuration.

---

## Database Management

### Create Manual Backup

```bash
pg_dump -U mamcrawler_app mamcrawler_prod > backup_$(date +%Y%m%d_%H%M%S).sql
gzip backup_*.sql
```

### Restore from Backup

```bash
# Stop application
sudo systemctl stop mamcrawler

# Restore database
gunzip backup_*.sql.gz
psql -U mamcrawler_app mamcrawler_prod < backup_*.sql

# Restart application
sudo systemctl start mamcrawler
```

### Run Database Migrations

```bash
# Check current revision
alembic current

# Upgrade to latest
alembic upgrade head

# Downgrade one revision
alembic downgrade -1

# Generate new migration
alembic revision --autogenerate -m "description"
```

---

## Environment Configuration Reference

See `backend/config.py` for comprehensive Settings class with all configuration options.

**Key Categories:**
- API Configuration (host, port, docs, security headers)
- Database (URL, echo, pool size)
- Authentication (API key, secret, password salt)
- External Services (Audiobookshelf, qBittorrent, Prowlarr, Google Books, MAM)
- Features (metadata correction, series completion, gap analysis, top10 discovery)
- Scheduler (enabled, task times, retention policies)
- Genres (enabled/disabled lists)
- CORS (allowed origins, hosts)

---

## Health Checks & Monitoring

### Health Endpoints

All 4 endpoints return JSON with timestamp and component status:

```bash
# Overall health
curl https://audiobook.example.com/health

# Liveness (Kubernetes)
curl https://audiobook.example.com/health/live

# Readiness (Kubernetes)
curl https://audiobook.example.com/health/ready

# Deep diagnostics
curl https://audiobook.example.com/health/deep
```

### Expected Response

```json
{
  "status": "healthy",
  "timestamp": "2025-11-25T10:30:45Z",
  "services": {
    "database": "ok",
    "api": "running",
    "scheduler": "ok"
  }
}
```

### Container Health Check

Docker automatically runs `/health` endpoint every 30 seconds via HEALTHCHECK instruction in Dockerfile.

---

## Troubleshooting Guide

### Issue 1: Database Connection Failed

**Symptoms:** Error logs show "could not connect to server"

**Solutions:**
1. Verify PostgreSQL is running: `sudo systemctl status postgresql`
2. Check DATABASE_URL in .env: `psql "$DATABASE_URL" -c "SELECT 1"`
3. Verify credentials: `sudo -u postgres psql`
4. Check pg_hba.conf for authentication method

### Issue 2: High Memory Usage

**Symptoms:** Service OOM killed or slowness

**Solutions:**
1. Check memory: `free -h`
2. Monitor processes: `top -p $(pidof uvicorn)`
3. Reduce worker count in systemd service (--workers 4)
4. Check for memory leaks in logs
5. Increase server RAM if consistently high

### Issue 3: Slow API Responses

**Symptoms:** 502 Bad Gateway or timeout errors

**Solutions:**
1. Check system load: `uptime`
2. Monitor database queries: Enable DATABASE_ECHO=True in dev
3. Check Nginx logs: `sudo tail -f /var/log/nginx/mamcrawler_error.log`
4. Verify external service connectivity
5. Scale to multiple workers (--workers 8)

### Issue 4: Certificate Expiration

**Symptoms:** SSL certificate expired warning

**Solutions:**
1. Check certificate: `sudo openssl x509 -in /etc/letsencrypt/live/audiobook.example.com/cert.pem -text -noout | grep -A2 "Validity"`
2. Manual renewal: `sudo certbot renew --force-renewal`
3. Verify auto-renewal: `sudo systemctl status certbot.timer`

### Issue 5: Migrations Failed

**Symptoms:** "Target database is not up to date"

**Solutions:**
1. Check current state: `alembic current`
2. Check available migrations: `alembic branches`
3. Manually set stamp: `alembic stamp head` (if necessary)
4. Review migration file for errors
5. Rollback if needed: `alembic downgrade -1`

### Issue 6: Rate Limit Blocking Legitimate Traffic

**Symptoms:** "429 Too Many Requests" from normal users

**Solutions:**
1. Increase rate limit in backend/rate_limit.py
2. Check ALLOWED_ORIGINS in .env
3. Verify client isn't making concurrent requests
4. Use API key for higher limits (authenticated tier)
5. Whitelist IP addresses in Nginx if needed

---

## Rollback Procedures

### Normal Rollback (Recent Changes)

```bash
# 1. Check current version
git log --oneline -5

# 2. Checkout previous version
git checkout <commit-hash>
git pull origin main

# 3. Stop service
sudo systemctl stop mamcrawler

# 4. Downgrade database (if migrations changed)
alembic downgrade -1

# 5. Rebuild requirements
pip install -r backend/requirements.txt

# 6. Restart service
sudo systemctl start mamcrawler

# 7. Verify
curl https://audiobook.example.com/health
```

### Emergency Rollback (Database Issues)

```bash
# 1. Stop service immediately
sudo systemctl stop mamcrawler

# 2. Restore database from backup
gunzip backup_20251125_120000.sql.gz
psql -U mamcrawler_app mamcrawler_prod < backup_20251125_120000.sql

# 3. Reset migrations to match backup state
alembic stamp <matching-revision>

# 4. Checkout matching code version
git checkout <matching-commit>

# 5. Restart
sudo systemctl start mamcrawler
```

### Verify Rollback Success

```bash
# Check service is running
sudo systemctl status mamcrawler

# Check database connectivity
curl https://audiobook.example.com/health/ready

# Check logs for errors
sudo journalctl -u mamcrawler -n 50

# Check that data is accessible
curl https://audiobook.example.com/api/books
```

---

## Security Checklist

### Pre-Deployment Review

- [ ] All hardcoded secrets removed from code
- [ ] .env file created with strong passwords (32+ chars)
- [ ] .env file added to .gitignore (never commit)
- [ ] API_KEY, SECRET_KEY, PASSWORD_SALT set to unique values
- [ ] DATABASE_URL using strong password
- [ ] HTTPS certificate valid and configured
- [ ] Firewall rules configured (allow 80, 443, deny others)
- [ ] SSH key-based authentication enabled, password disabled
- [ ] Database backups configured and tested
- [ ] Log rotation configured
- [ ] Monitoring and alerting set up
- [ ] All dependencies up to date: `pip list --outdated`

### Post-Deployment Verification

- [ ] Health check responds 200: `curl https://audiobook.example.com/health`
- [ ] API docs disabled in production (API_DOCS=False)
- [ ] Debug mode disabled (DEBUG=False)
- [ ] Security headers present: `curl -I https://audiobook.example.com | grep -i "strict-transport"`
- [ ] Rate limiting working: `for i in {1..70}; do curl -s /dev/null & done; wait`
- [ ] HTTPS enforced (HTTP redirects to HTTPS)
- [ ] Logs being written and rotated
- [ ] Backups completing successfully
- [ ] External services (ABS, QB, etc.) connected and responding
- [ ] Database migrations current: `alembic current`
- [ ] All systemd services enabled and running

### Ongoing Maintenance

- [ ] Daily: Review logs for errors
- [ ] Weekly: Verify backups, check disk space
- [ ] Monthly: Update dependencies, patch OS
- [ ] Quarterly: Security audit, performance review
- [ ] Yearly: Full disaster recovery test

---

## Support & References

**Documentation:**
- Rate Limiting: See RATE_LIMITING_GUIDE.md
- Database Migrations: See DATABASE_MIGRATIONS_GUIDE.md
- Testing: See WEEK1_TEST_SUMMARY.md
- Configuration: See backend/config.py docstrings

**External Resources:**
- FastAPI: https://fastapi.tiangolo.com
- PostgreSQL: https://www.postgresql.org/docs
- Alembic: https://alembic.sqlalchemy.org
- Nginx: https://nginx.org/en/docs
- Docker: https://docs.docker.com

---

**Last Updated:** November 25, 2025

**Status:** ✅ Production Ready - Week 1 Hardening Complete

**Next:** Week 2 - API Endpoint Testing & Integration Tests
