# Frank Audiobook Hub Services Diagnosis Report

**Generated:** 2025-11-28T10:25:00Z
**Frank Location:** C:\Users\dogma\Projects\Frank
**Diagnosis Tool:** Claude Code Agent

---

## Executive Summary

**STATUS: PARTIAL SERVICE FAILURE**

- **Node.js API (Port 3000):** DOWN - Port shows LISTENING but connections refused
- **Python FastAPI (Port 8000):** UP - Responding normally to health checks
- **Overall Assessment:** Python service operational, Node.js service non-responsive

---

## Detailed Service Status

### 1. Node.js API Service (Port 3000)

**Current State:** FAILED / NON-RESPONSIVE

**Evidence:**
```
Port Status: TCP 0.0.0.0:3000 LISTENING (PID 27428)
Connection Test: Connection refused after 2239ms
Health Check: FAILED - curl returns "Could not connect to server"
```

**Symptoms:**
- Port 3000 appears in netstat as LISTENING
- Process ID 27428 is bound to the port
- All connection attempts are refused (both IPv4/IPv6)
- Node.js process exists (PID 27428 visible in tasklist)

**Likely Causes:**
1. Process crashed but port binding not released
2. Service started but crashed during initialization
3. Service listening but not accepting connections (initialization failure)
4. Firewall blocking localhost connections (unlikely but possible)

**Application Details:**
- Entry Point: `unified_api.js`
- Expected Endpoints:
  - `GET /health` - Health check with service status
  - `GET /` - Root endpoint with API documentation
  - Various `/organize`, `/requests`, `/sync`, `/series` endpoints
- Version: 0.1.0
- Node.js Version: v22.14.0
- NPM Version: 11.6.1

### 2. Python FastAPI Service (Port 8000)

**Current State:** OPERATIONAL

**Evidence:**
```
Port Status: TCP 0.0.0.0:8000 LISTENING (PID 3692)
Connection Test: SUCCESS - HTTP 200 OK
Health Check: PASSED - Returns "OK"
Response Time: <10ms
```

**Health Check Response:**
```
HTTP/1.1 200 OK
Content-Type: text/plain; charset=utf-8
Body: OK
```

**Application Details:**
- Entry Point: `audiobook-hub/app/main.py`
- Running on: 0.0.0.0:8000
- Python Version: 3.11.8
- Available Endpoints:
  - `GET /` - HTML dashboard
  - `GET /health` - Health check endpoint
  - `GET /docs` - Swagger API documentation
  - `GET /redoc` - ReDoc API documentation
  - Various `/api` endpoints
- Version: 0.1.0
- Environment: development

**Configuration:**
- Uses Pydantic settings with .env file support
- Environment prefix: `AUDIOBOOK_HUB_`
- Default port: 8000
- CORS: Enabled for localhost/127.0.0.1

---

## Port Analysis

| Port | Protocol | State | PID | Service | Status |
|------|----------|-------|-----|---------|--------|
| 3000 | TCP | LISTENING | 27428 | Node.js API | FAILED |
| 8000 | TCP | LISTENING | 3692 | Python FastAPI | OPERATIONAL |
| 8000 | TCP (IPv6) | LISTENING | 3692 | Python FastAPI | OPERATIONAL |
| 8000 | TCP (IPv6 ::1) | LISTENING | 16816 | Python FastAPI | OPERATIONAL |

**Additional Processes Found:**
- Multiple node.exe processes running (5 total)
- Multiple python.exe processes running (5+ total)
- PID 27428 is bound to port 3000 but not responding

---

## Log Analysis

**Log Directory:** C:\Users\dogma\Projects\Frank\logs
**Status:** Empty (no error logs found)

**Firebase Debug Log:** C:\Users\dogma\Projects\Frank\firebase-debug.log
**Content:** Firebase auth debug info (unrelated to service failure)
**Last Modified:** 2025-11-27 19:59

**Observation:** No recent error logs indicate:
- Services may not have logging configured for stdout/file
- Node.js service may have crashed before writing logs
- Log rotation may have cleared recent errors

---

## Configuration Analysis

### Node.js API Configuration

**Config File:** C:\Users\dogma\Projects\Frank\config.yaml (2080 bytes)
**Last Modified:** 2025-11-27 13:23

**Expected Configuration:**
- Server port: 3000 (default, configurable via config.yaml)
- Server host: 0.0.0.0 (default)
- CORS origin: * (default)
- Services: organizer, requests, sync, series, discord, homeassistant

**Dependencies:** (from package.json)
- express ^4.18.2
- cors ^2.8.5
- axios ^1.6.2
- better-sqlite3 ^9.2.2
- dotenv ^16.3.1
- morgan ^1.10.0

### Python FastAPI Configuration

**Config File:** audiobook-hub/.env.example (template only)
**Active Config:** Uses Pydantic settings with environment variables

**Current Settings:**
- Host: 0.0.0.0
- Port: 8000
- Environment: development
- Debug: false (default)
- Database: sqlite:///./audiobook_hub.db (default)

---

## Root Cause Analysis

### Node.js Service Failure

**Primary Issue:** Process exists but not accepting connections

**Possible Causes (ordered by likelihood):**

1. **Database Connection Failure** (HIGH)
   - better-sqlite3 dependency may fail to initialize
   - Database file permissions issue
   - Database file corruption

2. **Configuration Loading Error** (HIGH)
   - config.yaml parsing failure
   - Missing required environment variables
   - YAML syntax error

3. **Port Binding Race Condition** (MEDIUM)
   - Another process briefly held port 3000
   - Node.js bound port but crashed during initialization
   - Express app failed to start after port binding

4. **Dependency Module Error** (MEDIUM)
   - Native module (better-sqlite3) compilation issue
   - Missing node_modules or corrupted install
   - Version incompatibility with Node.js v22

5. **Service Initialization Crash** (MEDIUM)
   - One of the service constructors threw exception
   - Async initialization timeout
   - Unhandled promise rejection

**Evidence Supporting Database Issue:**
- Service uses better-sqlite3 (native module)
- No error logs written (crash before logger initialization)
- Port bound but connections refused (crash after bind, before listen)

---

## Recommended Restart Procedures

### OPTION 1: Quick Restart (Recommended First)

**Step 1: Stop Services Cleanly**

```bash
# Find and kill Node.js process on port 3000
tasklist | findstr "node.exe"
# Identify PID 27428 (or current PID on port 3000)

# Kill the process gracefully
taskkill /PID 27428 /T

# Optional: Kill Python service if needed
# netstat -ano | findstr ":8000"
# taskkill /PID 3692 /T
```

**Step 2: Restart Node.js API**

```bash
cd C:\Users\dogma\Projects\Frank

# Verify dependencies installed
npm install

# Start service (production mode)
npm start

# OR start service (development mode with auto-reload)
npm run dev
```

**Step 3: Verify Service Health**

```bash
# Wait 5-10 seconds for startup, then test
curl http://localhost:3000/health

# Expected response:
# {
#   "status": "healthy",
#   "timestamp": "2025-11-28T...",
#   "version": "0.1.0",
#   "services": {
#     "organizer": "active",
#     "requests": "active",
#     "sync": "active",
#     "series": "active",
#     "discord": "active",
#     "homeassistant": "active",
#     "database": "active"
#   }
# }
```

**Step 4: Test Basic Connectivity**

```bash
# Test root endpoint
curl http://localhost:3000/

# Expected: JSON response with API documentation

# Test Python service
curl http://localhost:8000/health

# Expected: "OK" or JSON health status
```

---

### OPTION 2: Full Service Restart (If Quick Restart Fails)

**Step 1: Clean Shutdown of All Services**

```bash
# Kill all node.exe processes (CAUTION: kills ALL Node.js apps)
taskkill /IM node.exe /F

# Optional: Kill all Python processes if needed
# taskkill /IM python.exe /F
```

**Step 2: Clear Process/Port Locks**

```bash
# Wait 5 seconds for ports to release
timeout /t 5

# Verify ports are free
netstat -ano | findstr ":3000"
netstat -ano | findstr ":8000"

# Expected: No output (ports free)
```

**Step 3: Check Configuration Files**

```bash
cd C:\Users\dogma\Projects\Frank

# Validate config.yaml syntax
node -e "const yaml = require('js-yaml'); const fs = require('fs'); try { yaml.load(fs.readFileSync('config.yaml', 'utf8')); console.log('Config valid'); } catch(e) { console.error('Config error:', e.message); }"

# Check for .env file in audiobook-hub
ls audiobook-hub/.env 2>/dev/null || echo "No .env file (using defaults)"
```

**Step 4: Reinstall Dependencies (If Configuration Valid)**

```bash
# Node.js API
cd C:\Users\dogma\Projects\Frank
rm -rf node_modules package-lock.json
npm install

# Python FastAPI
cd C:\Users\dogma\Projects\Frank\audiobook-hub
pip install -r requirements.txt --upgrade
```

**Step 5: Start Services with Verbose Logging**

```bash
# Terminal 1: Start Node.js API with debug output
cd C:\Users\dogma\Projects\Frank
set DEBUG=*
npm start

# Terminal 2: Start Python FastAPI with debug output
cd C:\Users\dogma\Projects\Frank\audiobook-hub
set AUDIOBOOK_HUB_DEBUG=true
set AUDIOBOOK_HUB_LOG_LEVEL=DEBUG
python -m app.main

# OR use uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
```

**Step 6: Monitor Startup Logs**

Watch console output for:
- Database connection errors
- Port binding failures
- Module import errors
- Configuration parsing errors
- Service initialization failures

---

### OPTION 3: Diagnostic Restart (For Troubleshooting)

**Step 1: Test Configuration in Isolation**

```bash
cd C:\Users\dogma\Projects\Frank

# Test config loading
node -e "
const yaml = require('js-yaml');
const fs = require('fs');
const config = yaml.load(fs.readFileSync('config.yaml', 'utf8'));
console.log('Config loaded:', JSON.stringify(config, null, 2));
"
```

**Step 2: Test Database Connectivity**

```bash
# Check if database file exists
ls data/*.db 2>/dev/null || echo "No database files found"

# Test SQLite connection
node -e "
const Database = require('better-sqlite3');
try {
  const db = new Database('./data/audiobook_hub.db');
  console.log('Database OK');
  db.close();
} catch(e) {
  console.error('Database error:', e.message);
}
"
```

**Step 3: Test Service Modules**

```bash
# Test service imports
node -e "
try {
  const Organizer = require('./services/organizer');
  const Requests = require('./services/requests');
  console.log('Services load OK');
} catch(e) {
  console.error('Service load error:', e.message);
}
"
```

**Step 4: Start with Minimal Configuration**

```bash
# Create minimal test server
node -e "
const express = require('express');
const app = express();
app.get('/health', (req, res) => res.json({ status: 'ok' }));
app.listen(3000, () => console.log('Test server on 3000'));
"

# Test in another terminal
curl http://localhost:3000/health
```

If minimal server works, issue is in service initialization.
If minimal server fails, issue is with Node.js/Express installation.

---

## Service Verification Checklist

After restart, verify all endpoints are responding:

### Node.js API (Port 3000)

```bash
# Health check (CRITICAL)
curl http://localhost:3000/health
# Expected: JSON with status "healthy" and all services "active"

# Root endpoint
curl http://localhost:3000/
# Expected: JSON with API documentation

# Organize endpoint
curl http://localhost:3000/organize/scan -X POST -H "Content-Type: application/json" -d "{}"
# Expected: Scan results or error message (not connection refused)

# Requests endpoint
curl http://localhost:3000/requests/list
# Expected: Request list or empty array (not connection refused)
```

### Python FastAPI (Port 8000)

```bash
# Health check (CRITICAL)
curl http://localhost:8000/health
# Expected: "OK" or JSON health status

# Root endpoint
curl http://localhost:8000/
# Expected: HTML dashboard page

# API docs
curl http://localhost:8000/docs
# Expected: HTML Swagger documentation

# API health endpoint
curl http://localhost:8000/api/health
# Expected: JSON with health status
```

---

## Common Issues and Solutions

### Issue 1: "Address already in use" Error

**Symptoms:**
```
Error: listen EADDRINUSE: address already in use :::3000
```

**Solution:**
```bash
# Find process using port
netstat -ano | findstr ":3000"

# Kill the process
taskkill /PID <PID> /F

# Restart service
npm start
```

---

### Issue 2: "Cannot find module" Error

**Symptoms:**
```
Error: Cannot find module 'better-sqlite3'
```

**Solution:**
```bash
# Reinstall dependencies
cd C:\Users\dogma\Projects\Frank
npm install

# If issue persists, rebuild native modules
npm rebuild better-sqlite3
```

---

### Issue 3: Database Connection Failures

**Symptoms:**
```
Error: unable to open database file
Error: database disk image is malformed
```

**Solution:**
```bash
# Check database file permissions
icacls data\audiobook_hub.db

# If corrupted, restore from backup or recreate
rm data/audiobook_hub.db
npm start  # Will recreate database
```

---

### Issue 4: Config YAML Parsing Error

**Symptoms:**
```
YAMLException: bad indentation of a mapping entry
```

**Solution:**
```bash
# Validate YAML syntax
node -e "const yaml=require('js-yaml'); const fs=require('fs'); yaml.load(fs.readFileSync('config.yaml', 'utf8'));"

# If invalid, fix indentation (use spaces, not tabs)
# Or restore from backup
```

---

### Issue 5: Python Service Not Starting

**Symptoms:**
```
ImportError: No module named 'fastapi'
ModuleNotFoundError: No module named 'app'
```

**Solution:**
```bash
# Check Python environment
python --version  # Should be 3.11+

# Reinstall dependencies
cd C:\Users\dogma\Projects\Frank\audiobook-hub
pip install -r requirements.txt

# Start with explicit path
python -m app.main
```

---

## Monitoring and Maintenance

### Real-Time Service Monitoring

**Create a monitoring script** (save as `C:\Users\dogma\Projects\Frank\monitor_services.bat`):

```batch
@echo off
:loop
echo ========================================
echo Service Health Check - %date% %time%
echo ========================================

echo.
echo Node.js API (Port 3000):
curl -s -m 2 http://localhost:3000/health || echo FAILED

echo.
echo Python FastAPI (Port 8000):
curl -s -m 2 http://localhost:8000/health || echo FAILED

echo.
echo Port Status:
netstat -ano | findstr ":3000.*LISTENING"
netstat -ano | findstr ":8000.*LISTENING"

echo.
timeout /t 30 /nobreak
goto loop
```

**Usage:**
```bash
# Run in separate terminal for continuous monitoring
C:\Users\dogma\Projects\Frank\monitor_services.bat
```

---

### Log Collection

**Enable detailed logging** in both services:

**Node.js API** (add to unified_api.js or use environment variable):
```bash
set DEBUG=express:*,better-sqlite3:*
set NODE_ENV=development
npm start > logs/nodejs_api.log 2>&1
```

**Python FastAPI** (add to .env in audiobook-hub/):
```bash
AUDIOBOOK_HUB_LOG_LEVEL=DEBUG
AUDIOBOOK_HUB_LOG_FORMAT=json
```

**View logs:**
```bash
# Node.js
tail -f C:\Users\dogma\Projects\Frank\logs\nodejs_api.log

# Python (if using uvicorn directly)
uvicorn app.main:app --log-level debug --access-log
```

---

## Integration Test Results Context

**Background:** This diagnosis was triggered by integration test failures showing:
- Frank API requests timing out
- Unable to connect to Frank coordinator hub
- Tests expecting Frank to be available on port 3000

**Current State Matches Test Failures:**
- Port 3000 not accepting connections: CONFIRMED
- Service non-responsive: CONFIRMED
- Python service operational: CONFIRMED (but tests may not be using it)

**Action Required:**
1. Restart Node.js API service (port 3000) using procedures above
2. Verify health endpoint responds
3. Re-run integration tests to confirm resolution

---

## Next Steps

### Immediate Actions (Required)

1. **Kill stuck Node.js process:**
   ```bash
   taskkill /PID 27428 /F
   ```

2. **Restart Node.js API with logging:**
   ```bash
   cd C:\Users\dogma\Projects\Frank
   npm start
   ```

3. **Verify health check:**
   ```bash
   curl http://localhost:3000/health
   ```

4. **Monitor startup logs** for errors

### Short-Term Actions (Recommended)

1. **Review and fix config.yaml** if startup fails
2. **Check database integrity** if database errors appear
3. **Reinstall node_modules** if module errors occur
4. **Enable persistent logging** to capture future crashes
5. **Re-run integration tests** from MAMcrawler to verify Frank connectivity

### Long-Term Actions (Recommended)

1. **Implement process monitoring** (PM2, systemd, or Windows Service)
2. **Add health check endpoint monitoring** (uptime-kuma, healthchecks.io)
3. **Configure log rotation** for both services
4. **Set up automatic restart** on crash
5. **Document startup dependencies** (config files, database, ports)
6. **Create systemd/Windows Service** for production deployment

---

## Service Architecture Reference

```
Frank Audiobook Hub
├── Node.js API (Port 3000) - COORDINATOR HUB
│   ├── Express REST API
│   ├── Service Orchestration Layer
│   ├── SQLite Database (better-sqlite3)
│   ├── Integration Services:
│   │   ├── OrganizerService (audiobook file organization)
│   │   ├── RequestService (request tracking)
│   │   ├── SyncService (multi-source sync)
│   │   ├── SeriesService (series tracking)
│   │   ├── DiscordIntegrationService
│   │   └── HAIntegrationService (Home Assistant)
│   └── Config: config.yaml
│
└── Python FastAPI (Port 8000) - METADATA & WEB UI
    ├── FastAPI REST API
    ├── Web Dashboard (HTML/CSS/JS)
    ├── Metadata Extraction Services
    ├── Organization Services
    ├── External API Clients:
    │   ├── AudiobookShelf
    │   ├── Hardcover
    │   └── Audible
    ├── SQLite/PostgreSQL Database (SQLModel)
    └── Config: .env with AUDIOBOOK_HUB_ prefix
```

**Key Observation:** Both services have separate databases and configurations.
Node.js service is the primary integration hub expected by other systems.

---

## Contact and Support

**Project Location:** C:\Users\dogma\Projects\Frank
**Documentation:**
- C:\Users\dogma\Projects\Frank\README.md
- C:\Users\dogma\Projects\Frank\COMPREHENSIVE_INSTALLATION_GUIDE.md
- C:\Users\dogma\Projects\Frank\INTEGRATION_ARCHITECTURE.md

**Dependencies:**
- Node.js: v22.14.0
- NPM: 11.6.1
- Python: 3.11.8

**Related Systems:**
- MAMcrawler integration tests (requires Frank API on port 3000)
- AudiobookShelf (optional integration)
- Hardcover.app (optional integration)

---

## Appendix A: Full Service Endpoints

### Node.js API Endpoints (Port 3000)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check with service status |
| GET | / | Root endpoint with API documentation |
| POST | /organize/scan | Scan audiobook directory |
| POST | /organize/plan | Create organization plan |
| POST | /organize/execute | Execute organization plan |
| GET | /organize/logs/:operationId | Get operation logs |
| POST | /organize/undo/:operationId | Undo organization operation |
| GET | /requests/search | Search for audiobooks |
| POST | /requests/create | Create new request |
| GET | /requests/list | List all requests |
| GET | /requests/:requestId | Get request details |
| PATCH | /requests/:requestId/status | Update request status |
| POST | /requests/:requestId/fulfill | Mark request as fulfilled |
| DELETE | /requests/:requestId | Delete request |
| GET | /requests/notifications | Get pending notifications |
| POST | /requests/notifications/:id/sent | Mark notification sent |
| POST | /sync/profiles | Create sync profile |
| GET | /sync/profiles | List sync profiles |
| PATCH | /sync/profiles/:profileId | Update sync profile |
| DELETE | /sync/profiles/:profileId | Delete sync profile |
| POST | /sync/start/:profileId | Start sync job |
| GET | /sync/jobs/:jobId | Get sync job status |
| POST | /sync/jobs/:jobId/cancel | Cancel sync job |

### Python FastAPI Endpoints (Port 8000)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | HTML dashboard homepage |
| GET | /health | Health check endpoint |
| GET | /docs | Swagger API documentation |
| GET | /redoc | ReDoc API documentation |
| GET | /dashboard | Dashboard page |
| GET | /organize | Organize library page |
| GET | /requests | Manage requests page |
| GET | /series | Find missing series page |
| GET | /admin | Admin panel page |
| GET | /api/* | API endpoints (see /docs) |

---

## Appendix B: Diagnostic Commands Summary

```bash
# Check port status
netstat -ano | findstr ":3000"
netstat -ano | findstr ":8000"

# Check running processes
tasklist | findstr "node.exe"
tasklist | findstr "python.exe"

# Test service health
curl http://localhost:3000/health
curl http://localhost:8000/health

# Kill processes
taskkill /PID <PID> /F
taskkill /IM node.exe /F

# Check Node.js/Python versions
node --version
npm --version
python --version

# Validate configuration
node -e "const yaml=require('js-yaml'); const fs=require('fs'); yaml.load(fs.readFileSync('config.yaml'));"

# Start services
cd C:\Users\dogma\Projects\Frank && npm start
cd C:\Users\dogma\Projects\Frank\audiobook-hub && python -m app.main

# View logs (if configured)
tail -f C:\Users\dogma\Projects\Frank\logs\nodejs_api.log
tail -f C:\Users\dogma\Projects\Frank\audiobook-hub\logs\app.log
```

---

**END OF DIAGNOSIS REPORT**
