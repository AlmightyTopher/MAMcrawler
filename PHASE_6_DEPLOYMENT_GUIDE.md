# Phase 6 Deployment Guide

**Date**: November 16, 2025
**Status**: PRODUCTION DEPLOYMENT READY
**Target Environment**: Docker + PostgreSQL

---

## Quick Start (5 Minutes)

### Development Mode (SQLite)
```bash
# 1. Install dependencies
pip install -r backend/requirements.txt

# 2. Configure environment (.env already exists)
# DATABASE_URL=sqlite:///./audiobook_automation.db (already set)

# 3. Initialize database
python -c "from backend.database import init_db; init_db()"

# 4. Run FastAPI application
python backend/main.py

# 5. Access API
# Browser: http://localhost:8000/docs
# Health: http://localhost:8000/health
```

### Production Mode (PostgreSQL)

#### Step 1: PostgreSQL Setup
```bash
# Install PostgreSQL 14+ or use Docker
docker run -d \
  --name audiobook-db \
  -e POSTGRES_USER=audiobook_user \
  -e POSTGRES_PASSWORD=secure_password \
  -e POSTGRES_DB=audiobook_automation \
  -p 5432:5432 \
  postgres:15-alpine
```

#### Step 2: Update .env Configuration
```env
# Database (change from SQLite to PostgreSQL)
DATABASE_URL=postgresql://audiobook_user:secure_password@localhost:5432/audiobook_automation

# API Key (change this!)
API_KEY=your-production-api-key-here-change-me

# External Services (verify all configured)
ABS_URL=http://your-audiobookshelf-host:13378
ABS_TOKEN=your-jwt-token-here
QB_HOST=your-qbittorrent-host
QB_PORT=52095
PROWLARR_URL=http://your-prowlarr:9696
GOOGLE_BOOKS_API_KEY=your-api-key
```

#### Step 3: Install Dependencies
```bash
pip install -r backend/requirements.txt
```

#### Step 4: Initialize Database
```bash
python -c "from backend.database import init_db; init_db()"
```

#### Step 5: Run with Gunicorn
```bash
# Install production server
pip install gunicorn

# Run with multiple workers
gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.main:app --bind 0.0.0.0:8000
```

---

## Docker Deployment

### Option 1: Docker Compose (Recommended)

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: audiobook_user
      POSTGRES_PASSWORD: ${DB_PASSWORD:-secure_password}
      POSTGRES_DB: audiobook_automation
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U audiobook_user -d audiobook_automation"]
      interval: 10s
      timeout: 5s
      retries: 5

  # FastAPI Application
  api:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: postgresql://audiobook_user:${DB_PASSWORD:-secure_password}@db:5432/audiobook_automation
      API_KEY: ${API_KEY}
      ABS_URL: ${ABS_URL}
      ABS_TOKEN: ${ABS_TOKEN}
      QB_HOST: ${QB_HOST}
      QB_PORT: ${QB_PORT}
      GOOGLE_BOOKS_API_KEY: ${GOOGLE_BOOKS_API_KEY}
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
      - ./guides_output:/app/guides_output
    command: gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.main:app --bind 0.0.0.0:8000

volumes:
  postgres_data:

networks:
  default:
    name: audiobook-network
```

Create `.env.production`:
```env
DB_PASSWORD=your-secure-password
API_KEY=your-production-api-key
ABS_URL=http://audiobookshelf:13378
ABS_TOKEN=your-token
QB_HOST=qbittorrent-host
QB_PORT=52095
GOOGLE_BOOKS_API_KEY=your-key
```

Deploy:
```bash
# Copy and configure environment
cp .env.example .env.production

# Start all services
docker-compose -f docker-compose.yml up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

### Option 2: Standalone Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "backend.main:app", "--bind", "0.0.0.0:8000"]
```

Build and run:
```bash
# Build image
docker build -t audiobook-system:latest .

# Run container
docker run -d \
  --name audiobook-api \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@db:5432/audiobook_automation" \
  -e API_KEY="your-api-key" \
  --network audiobook-network \
  audiobook-system:latest
```

---

## Configuration Reference

### Environment Variables (Critical)

```env
# Database
DATABASE_URL=postgresql://user:password@host:5432/database

# API Security
API_KEY=your-secret-api-key-here

# Audiobookshelf
ABS_URL=http://localhost:13378
ABS_TOKEN=eyJhbGciOiJIUzI1NiIsInR...
ABS_TIMEOUT=30

# qBittorrent
QB_HOST=192.168.0.48
QB_PORT=52095
QB_USERNAME=TopherGutbrod
QB_PASSWORD=your-password
QB_TIMEOUT=30

# Prowlarr
PROWLARR_URL=http://localhost:9696
PROWLARR_API_KEY=your-api-key

# Google Books
GOOGLE_BOOKS_API_KEY=your-api-key

# MAM Crawler
MAM_USERNAME=your-email
MAM_PASSWORD=your-password
```

### Optional Configuration

```env
# Scheduler
SCHEDULER_ENABLED=true
TASK_MAM_TIME="0 2 * * *"           # Daily 2:00 AM
TASK_TOP10_TIME="0 3 * * 6"         # Sunday 3:00 AM
TASK_SERIES_TIME="0 3 2 * *"        # 2nd of month

# Features
ENABLE_METADATA_CORRECTION=true
ENABLE_SERIES_COMPLETION=true
ENABLE_AUTHOR_COMPLETION=true
ENABLE_TOP10_DISCOVERY=true

# Data Retention
HISTORY_RETENTION_DAYS=30
FAILED_ATTEMPTS_RETENTION=permanent
```

---

## Running the Application

### Local Development
```bash
# With auto-reload
pip install watchfiles
uvicorn backend.main:app --reload --port 8000

# Or direct Python
python backend/main.py
```

### Production with Gunicorn
```bash
# Single worker (debugging)
gunicorn -w 1 backend.main:app

# Multiple workers (production)
gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.main:app

# With logging and socket
gunicorn -w 4 \
  -k uvicorn.workers.UvicornWorker \
  -b unix:/tmp/audiobook.sock \
  -a 100 \
  --access-logfile - \
  --error-logfile - \
  backend.main:app
```

### With systemd (Linux)

Create `/etc/systemd/system/audiobook-api.service`:

```ini
[Unit]
Description=Audiobook Automation API
After=network.target postgresql.service

[Service]
Type=notify
User=audiobook
WorkingDirectory=/opt/audiobook-system
Environment="PATH=/opt/audiobook-system/venv/bin"
ExecStart=/opt/audiobook-system/venv/bin/gunicorn \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    -b 127.0.0.1:8000 \
    backend.main:app
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable audiobook-api
sudo systemctl start audiobook-api
sudo systemctl status audiobook-api
```

---

## Reverse Proxy Setup

### Nginx Configuration

```nginx
upstream audiobook_api {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name audiobook.example.com;

    client_max_body_size 100M;

    location / {
        proxy_pass http://audiobook_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;

        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /static/ {
        alias /opt/audiobook-system/static/;
        expires 30d;
    }
}
```

### Apache Configuration

```apache
<VirtualHost *:80>
    ServerName audiobook.example.com

    ProxyRequests Off
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/

    <Location />
        Order allow,deny
        Allow from all
    </Location>

    ErrorLog ${APACHE_LOG_DIR}/audiobook_error.log
    CustomLog ${APACHE_LOG_DIR}/audiobook_access.log combined
</VirtualHost>
```

---

## Monitoring & Health Checks

### Health Check Endpoint
```bash
# Check application status
curl http://localhost:8000/health

# Response:
# {"status": "ok", "timestamp": "2025-11-16T..."}
```

### API Endpoints for Monitoring
```bash
# System statistics
curl -H "Authorization: your-api-key" http://localhost:8000/api/system/stats

# Scheduler status
curl -H "Authorization: your-api-key" http://localhost:8000/api/scheduler/status

# Database health (implied through normal operations)
```

### Docker Health Checks

Add to docker-compose.yml:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 3s
  retries: 3
  start_period: 40s
```

---

## Backup & Recovery

### Database Backup (PostgreSQL)

```bash
# Backup
pg_dump -U audiobook_user audiobook_automation > backup.sql

# Restore
psql -U audiobook_user audiobook_automation < backup.sql

# Docker backup
docker exec audiobook-db pg_dump -U audiobook_user audiobook_automation > backup.sql
```

### Application Files Backup

```bash
# Backup configuration and logs
tar -czf audiobook-system-backup.tar.gz \
  .env \
  logs/ \
  guides_output/

# Backup with database (Docker)
docker exec audiobook-db pg_dump -U audiobook_user audiobook_automation | \
  gzip > database-backup.sql.gz
```

---

## Troubleshooting

### Application won't start

1. **Check logs**:
   ```bash
   # Docker
   docker logs audiobook-api

   # Direct
   tail -f logs/audiobook_system.log
   tail -f logs/error.log
   ```

2. **Database connection error**:
   ```bash
   # Verify DATABASE_URL
   python -c "from backend.database import engine; print(engine.url)"

   # Test connection
   psql postgresql://user:pass@host/database
   ```

3. **Port already in use**:
   ```bash
   # Find process using port 8000
   lsof -i :8000

   # Or use different port
   python backend/main.py --port 8001
   ```

### External API connection issues

1. **Audiobookshelf**:
   ```bash
   # Test connection
   curl http://localhost:13378/api/ping

   # Verify token validity
   curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:13378/api/libraries
   ```

2. **qBittorrent**:
   ```bash
   # Test login
   curl -X POST http://192.168.0.48:52095/api/v2/auth/login \
     -d "username=user&password=pass"
   ```

3. **Prowlarr**:
   ```bash
   # Test API key
   curl -H "X-Api-Key: YOUR_KEY" http://localhost:9696/api/v1/indexer
   ```

### Performance issues

1. **Database**:
   ```bash
   # Check slow queries
   # PostgreSQL: enable log_min_duration_statement
   # SQLite: use EXPLAIN QUERY PLAN
   ```

2. **Application**:
   ```bash
   # Profile with py-spy
   pip install py-spy
   py-spy record -o profile.svg -- python backend/main.py
   ```

3. **Memory usage**:
   ```bash
   # Monitor with resource monitoring tools
   docker stats audiobook-api
   ```

---

## Performance Tuning

### Database
- Enable connection pooling (SQLAlchemy configured)
- Create indexes on frequently queried fields
- Regular VACUUM (PostgreSQL)
- Monitor query performance

### Application
- Use uvicorn workers appropriately (CPU cores * 2 + 1)
- Enable caching where applicable
- Optimize ORM queries (avoid N+1)
- Use async/await throughout

### System
- Use SSD for database storage
- Allocate sufficient RAM (minimum 2GB)
- Configure appropriate swap
- Monitor CPU and I/O

---

## Security Checklist

- [ ] Change API_KEY in .env to strong random value
- [ ] Use HTTPS in production (reverse proxy with SSL)
- [ ] Secure database password
- [ ] Restrict database access to application only
- [ ] Use environment-specific .env files
- [ ] Never commit .env to version control
- [ ] Enable firewall rules
- [ ] Keep dependencies updated
- [ ] Set up log monitoring/alerting
- [ ] Regular security audits

---

## Deployment Verification

After deployment, verify:

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. API authentication
curl -H "Authorization: wrong-key" http://localhost:8000/api/books
# Should return 401 Unauthorized

curl -H "Authorization: correct-api-key" http://localhost:8000/api/books
# Should return books or empty list

# 3. Database connectivity
# Check logs for any connection errors

# 4. External API connectivity
curl -H "Authorization: correct-api-key" http://localhost:8000/api/system/stats
# Should show system information
```

---

## Maintenance

### Regular Tasks
- Monitor logs for errors
- Check database performance
- Update dependencies quarterly
- Backup database weekly
- Review and archive old logs

### Scheduled Tasks
- MAM scraping: Daily 2:00 AM
- Metadata correction: 1st of month 4:00 AM
- Series completion: 2nd of month 3:00 AM
- Author completion: 3rd of month 3:00 AM
- Cleanup old records: Daily 1:00 AM

### Updates
```bash
# Update dependencies
pip install --upgrade -r backend/requirements.txt

# Restart application
# Docker: docker-compose restart api
# Systemd: sudo systemctl restart audiobook-api
```

---

## Next Steps

1. ✅ Phase 6 Integration Testing Complete
2. ⏭️ Docker containerization
3. ⏭️ Production deployment
4. ⏭️ Monitoring setup (Prometheus/Grafana)
5. ⏭️ User documentation

---

**Deployment Guide**: Production-ready
**Last Updated**: November 16, 2025
**Version**: 1.0.0
