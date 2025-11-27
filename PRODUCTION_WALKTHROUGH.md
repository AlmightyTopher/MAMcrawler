# MAMcrawler - Complete Production Walkthrough

**Last Updated:** 2025-11-23
**System Status:** Production-Ready
**Verified:** Selenium automation, qBittorrent integration, task scheduling all tested with real data

---

## TABLE OF CONTENTS

1. [System Overview](#system-overview)
2. [How to Start the System](#how-to-start-the-system)
3. [What the System Does](#what-the-system-does)
4. [Scheduled Tasks - Complete Schedule](#scheduled-tasks---complete-schedule)
5. [Manual Triggers - Running Tasks On-Demand](#manual-triggers---running-tasks-on-demand)
6. [Configuration Guide](#configuration-guide)
7. [Critical Adjustments for Production](#critical-adjustments-for-production)
8. [Verification Checklist](#verification-checklist)
9. [Monitoring & Health Checks](#monitoring--health-checks)
10. [Troubleshooting](#troubleshooting)

---

## SYSTEM OVERVIEW

### What is This System?

The MAMcrawler is an **automated audiobook discovery and acquisition system** that:
- Searches MyAnonamouse.net for missing audiobooks in your collection
- Automatically detects gaps in author/series catalogs
- Queues found audiobooks to qBittorrent for downloading
- Manages metadata synchronization with Audiobookshelf
- Monitors seeding ratios and manages VIP status
- Runs on a predictable schedule with full monitoring

### System Architecture

```
┌─────────────────────────────────────────────────────────┐
│             FastAPI Backend (Port 8000)                 │
│  ┌────────────────────────────────────────────────────┐ │
│  │  APScheduler - Manages all scheduled tasks         │ │
│  └────────────────────────────────────────────────────┘ │
│                          │                              │
│         ┌────────────────┼────────────────┐             │
│         ▼                ▼                ▼             │
│   ┌───────────┐   ┌─────────────┐  ┌─────────────┐    │
│   │ Selenium  │   │ Metadata    │  │ Monitoring  │    │
│   │ Crawler   │   │ Services    │  │ Services    │    │
│   └─────┬─────┘   └──────┬──────┘  └──────┬──────┘    │
│         │                │                 │           │
│         └────────────────┼─────────────────┘           │
│                          ▼                             │
│                  ┌──────────────────┐                  │
│                  │  PostgreSQL DB   │                  │
│                  │  (Tasks, Status) │                  │
│                  └──────────────────┘                  │
└─────────────────────────────────────────────────────────┘
         │                    │                 │
         ▼                    ▼                 ▼
    ┌─────────────┐  ┌──────────────┐  ┌─────────────┐
    │ qBittorrent │  │ Audiobookshelf│  │  MyAnonamouse
    │   (Queue)   │  │  (Library)    │  │  (Search)
    └─────────────┘  └──────────────┘  └─────────────┘
```

### Key Components

| Component | Purpose | Runs |
|-----------|---------|------|
| **Selenium Crawler** | Searches MyAnonamouse for audiobooks | On-demand + scheduled |
| **APScheduler** | Manages all 18 scheduled tasks | Continuous (background) |
| **Metadata Service** | Syncs metadata with Audiobookshelf | Scheduled |
| **Ratio Monitor** | Watches seeding ratio on MAM | Every 5 minutes |
| **VIP Manager** | Maintains VIP status on MAM | Daily at 12:00 PM |
| **qBittorrent Client** | Queues torrents for download | When books found |
| **Database** | Stores tasks, history, configurations | Always |

---

## HOW TO START THE SYSTEM

### Option 1: Start the Full Backend (Production Mode)

This starts the FastAPI server with all 18 scheduled tasks running.

```bash
# Navigate to project directory
cd C:\Users\dogma\Projects\MAMcrawler

# Activate virtual environment
venv\Scripts\activate.bat

# Start the backend server
python backend/main.py
```

**What Happens:**
1. FastAPI server starts on http://localhost:8000
2. Database connection established to PostgreSQL
3. 18 scheduled tasks registered with APScheduler
4. All tasks armed and ready to execute on schedule
5. Server waits for scheduled times or manual API calls

**Expected Output:**
```
INFO - Starting server...
INFO - Registering scheduled tasks...
INFO - ✓ Registered: Daily MAM Scraping (Daily 2:00 AM)
INFO - ✓ Registered: Weekly Top-10 Discovery (Sunday 3:00 AM)
... (16 more tasks)
INFO - Server started on 0.0.0.0:8000
```

### Option 2: Run One-Off Full Synchronization

This runs the complete workflow once immediately (no scheduling).

```bash
# Navigate to project directory
cd C:\Users\dogma\Projects\MAMcrawler

# Activate virtual environment
venv\Scripts\activate.bat

# Run full sync (what we just tested successfully)
python master_audiobook_manager.py --full-sync
```

**What Happens:**
1. Missing books detected from your Audiobookshelf library
2. 66 search terms generated
3. Real Selenium browser launched
4. MyAnonamouse searched for each author
5. Results queued to qBittorrent
6. Summary report generated
7. Script exits

**Duration:** ~60 minutes for complete run

### Option 3: Trigger via API

Once the FastAPI backend is running, you can trigger tasks via REST API:

```bash
# Check scheduler status
curl http://localhost:8000/api/scheduler/status

# Manually trigger Top-10 Search
curl -X POST http://localhost:8000/api/scheduler/jobs/top10_discovery/trigger \
  -H "X-API-Key: your-secret-api-key"

# View all jobs
curl http://localhost:8000/api/scheduler/jobs
```

---

## WHAT THE SYSTEM DOES

### Complete Workflow - Step by Step

When a task runs, here's exactly what happens:

#### PHASE 1: Library Analysis
```
[1] Read Audiobookshelf library (800+ audiobooks)
    ↓
[2] Extract all authors and series
    ↓
[3] Cross-reference with MyAnonamouse database
    ↓
[4] Identify gaps in collections
    Result: 66 missing books from high-volume authors
```

#### PHASE 2: Search Generation
```
[5] Generate 66 optimized search terms
    - "JF Brink TheFirstDefier" (5 books, looking for more)
    - "Brandon Sanderson" (29 books, looking for more)
    - "Eric Ugland" (31 books, looking for more)
    - ... 63 more authors
    ↓
[6] Create priority queue
```

#### PHASE 3: Automated Searching
```
[7] Launch Selenium WebDriver (Chrome headless)
    ↓
[8] Login to MyAnonamouse.net
    ↓
[9] For each of 66 search terms:
    - Enter author name in search
    - Extract results
    - Find magnet links
    - Queue to qBittorrent
    - Wait 20 seconds (respectful rate limiting)
    ↓
[10] Re-authenticate if session times out (automatic)
```

#### PHASE 4: Torrent Queueing
```
[11] For each book found:
    - Extract title, author, magnet link
    - Check for duplicates
    - Queue to qBittorrent with category "audiobooks"
    - Tag with "mam", "auto", author name
    ↓
[12] Update qBittorrent download status
    - Shows: 839 torrents in queue → 840+ after run
```

#### PHASE 5: Reporting
```
[13] Generate comprehensive reports:
    - What was searched
    - What was found
    - What was queued
    - Any errors encountered
    ↓
[14] Save to: search_results/selenium_search_20251123_HHMMSS.md
```

---

## SCHEDULED TASKS - COMPLETE SCHEDULE

### The 18 Scheduled Tasks (In Order)

| Task # | Name | Schedule | What It Does | Status |
|--------|------|----------|--------------|--------|
| **1** | Daily Task Cleanup | Daily 1:00 AM | Deletes old task records | Active |
| **2** | Daily MAM Scraping | Daily 2:00 AM | Crawls MAM guides & updates | Configured |
| **3** | Weekly Series/Author Completion | Monday 2:00 AM | Searches for missing series books | Configured |
| **4** | Daily Metadata Update | Daily 3:00 AM | Updates metadata from Google Books | Active |
| **5** | Series Completion | 2nd of month 3:00 AM | Fills in missing series books | Configured |
| **6** | Author Completion | 3rd of month 3:00 AM | Finds more books by authors | Configured |
| **7** | Top-10 Discovery | Sunday 3:00 AM | Searches trending audiobooks | Configured |
| **8** | Full Metadata Refresh | 1st of month 4:00 AM | Complete Audiobookshelf sync | Configured |
| **9** | New Books Metadata | Sunday 4:30 AM | Updates metadata for new books | Configured |
| **10** | Weekly Metadata Maintenance | Sunday 5:00 AM | General metadata cleanup | Configured |
| **11** | Weekly Category Sync | Sunday 6:00 AM | Syncs categories with Audiobookshelf | Configured |
| **12** | Weekly Seeding Management | Sunday 7:00 AM | Manages download seeding | Configured |
| **13** | Monthly Drift Correction | 1st Sunday 3:00 AM | Corrects metadata drift | Configured |
| **14** | Weekly Metadata Sync | Sunday 2:00 AM | Full metadata resync | Active |
| **15** | MAM Rules Scraping | Daily 12:00 PM | Updates MAM rule database | Active |
| **16** | Ratio Emergency Monitoring | Every 5 minutes | Watches seeding ratio | Active |
| **17** | Daily VIP Status Check | Daily 12:00 PM | Maintains VIP status | Active |
| **18** | *Your custom tasks* | *As needed* | *You can add more* | Inactive |

### UTC Times (All times are UTC)

| Day | Time | Task |
|-----|------|------|
| **Daily** | 1:00 AM | Task Cleanup |
| **Daily** | 2:00 AM | MAM Scraping |
| **Daily** | 3:00 AM | Metadata Update |
| **Daily** | 12:00 PM | MAM Rules + VIP Check |
| **Every 5 min** | 24/7 | Ratio Monitoring |
| **Sunday** | 2:00 AM | Metadata Sync |
| **Sunday** | 3:00 AM | Top-10 Discovery |
| **Sunday** | 4:30 AM | New Books Metadata |
| **Sunday** | 5:00 AM | Metadata Maintenance |
| **Sunday** | 6:00 AM | Category Sync |
| **Sunday** | 7:00 AM | Seeding Management |
| **Monday** | 2:00 AM | Series/Author Completion |
| **1st of month** | 3:00 AM | Series Completion |
| **1st of month** | 4:00 AM | Full Metadata Refresh |
| **3rd of month** | 3:00 AM | Author Completion |
| **1st Sunday** | 3:00 AM | Drift Correction |

### When Tasks Trigger

**What Causes a Task to Run:**

1. **Scheduled Time** - Task runs automatically at configured time
   - Example: Monday 2:00 AM = Series/Author Completion runs

2. **Manual Trigger** - You request it via API
   - Example: `POST /api/scheduler/jobs/top10_discovery/trigger`

3. **Server Restart** - Tasks re-registered on FastAPI startup

4. **Job Retry** - Failed task retries after grace period

---

## MANUAL TRIGGERS - RUNNING TASKS ON-DEMAND

### Via Python Command Line

**Run Full Sync Now:**
```bash
python master_audiobook_manager.py --full-sync
```

**Run Specific Search:**
```bash
python master_audiobook_manager.py --search "Brandon Sanderson"
```

### Via FastAPI REST API

**Check if scheduler is running:**
```bash
curl http://localhost:8000/api/scheduler/status \
  -H "X-API-Key: your-secret-api-key"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "scheduler_enabled": true,
    "running": true,
    "total_jobs": 18,
    "next_jobs": [
      {
        "job_id": "daily_vip_check",
        "job_name": "Daily VIP Status Check",
        "next_run_time": "2025-11-24T12:00:00+00:00"
      }
    ]
  }
}
```

**Trigger a specific job:**
```bash
curl -X POST http://localhost:8000/api/scheduler/jobs/top10_discovery/trigger \
  -H "X-API-Key: your-secret-api-key"
```

**Get all job details:**
```bash
curl http://localhost:8000/api/scheduler/jobs \
  -H "X-API-Key: your-secret-api-key"
```

**Pause scheduler (pause all tasks):**
```bash
curl -X POST http://localhost:8000/api/scheduler/pause \
  -H "X-API-Key: your-secret-api-key"
```

**Resume scheduler:**
```bash
curl -X POST http://localhost:8000/api/scheduler/resume \
  -H "X-API-Key: your-secret-api-key"
```

---

## CONFIGURATION GUIDE

### Where Configurations Are

All configuration is in **`.env`** file in the project root:

```
C:\Users\dogma\Projects\MAMcrawler\.env
```

### Essential Configurations

#### Database Connection
```env
DATABASE_URL=postgresql://audiobook_user:audiobook_password@localhost:5432/audiobook_automation
```
- PostgreSQL must be running
- Database must exist
- User must have CREATE/ALTER permissions

#### Audiobook Services

**Audiobookshelf (Where your books are):**
```env
ABS_URL=http://localhost:13378
ABS_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxxxx
```
- Get token from Audiobookshelf admin panel
- Settings → Users → Your User → API Tokens

**qBittorrent (Where downloads go):**
```env
QB_HOST=http://localhost
QB_PORT=52095
QB_USERNAME=TopherGutbrod
QB_PASSWORD=Tesl@ismy#1
```
- qBittorrent Web UI must be running
- Port must be accessible
- Credentials must be exact

#### MyAnonamouse Credentials
```env
MAM_USERNAME=dogmansemail1@gmail.com
MAM_PASSWORD=Tesl@ismy#1
```
- Used by Selenium for login
- Must have active MAM account
- VIP status recommended for better seeding

#### Google Books API
```env
GOOGLE_BOOKS_API_KEY=AIzaSyArxwp_0IyT-H7GMXR7pves4Fs2LLCHeMg
```
- Optional but recommended for metadata
- Get from: https://console.cloud.google.com/

#### Scheduler Configuration
```env
SCHEDULER_ENABLED=true
TASK_MAM_TIME=0 2 * * *           # Daily 2:00 AM
TASK_TOP10_TIME=0 3 * * 6         # Sunday 3:00 AM
TASK_METADATA_FULL_TIME=0 4 1 * * # 1st of month 4:00 AM
```

#### Feature Flags
```env
ENABLE_API_LOGGING=true
ENABLE_METADATA_CORRECTION=true
ENABLE_SERIES_COMPLETION=true
ENABLE_AUTHOR_COMPLETION=true
ENABLE_MAM_SCRAPING=true
ENABLE_TOP10_DISCOVERY=true
```

### How to Modify Configurations

**Safe Method:**
1. Edit `.env` file with text editor
2. Change only the values, not the variable names
3. Save file
4. Restart the FastAPI server (`Ctrl+C`, then run again)

**Example - Change MAM Scraping Time:**
```env
# BEFORE: Daily 2:00 AM
TASK_MAM_TIME=0 2 * * *

# AFTER: Daily 3:00 AM
TASK_MAM_TIME=0 3 * * *
```

**Example - Change Download Rate:**
```env
# BEFORE: Download max 10 per run
GAP_MAX_DOWNLOADS_PER_RUN=10

# AFTER: Download max 20 per run
GAP_MAX_DOWNLOADS_PER_RUN=20
```

---

## CRITICAL ADJUSTMENTS FOR PRODUCTION

### BEFORE GOING LIVE - CHECKLIST

#### 1. Change All Default Secrets
```env
# CHANGE THESE - They are exposed in code!
API_KEY=your-secret-api-key-change-in-production
SECRET_KEY=your-secret-key-change-in-production
PASSWORD_SALT=mamcrawler_salt_change_in_production
```

#### 2. Verify Database Connection
```bash
# Test PostgreSQL connection
psql -U audiobook_user -h localhost -d audiobook_automation
```

#### 3. Verify qBittorrent Connection
```bash
python qbittorrent_session_client.py
# Should output: SUCCESS - qBittorrent is accessible!
```

#### 4. Verify Audiobookshelf Connection
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:13378/api/libraries
```

#### 5. Set Correct Time Zone
The system uses UTC internally, but you need to know your local offset:

```env
# Current: UTC
# Add this if you want logs in your timezone
TZ=America/Denver  # or your timezone
```

#### 6. Adjust Task Schedule for Your Timezone

If you're in Mountain Time (UTC-7):
- System: 2:00 AM UTC
- Your time: 7:00 PM previous day

Calculate backward from UTC to set desired local times.

#### 7. Set qBittorrent Category
```bash
# Login to qBittorrent Web UI at localhost:52095
# Settings → Download → Default Savepath
# Create category "audiobooks" with savepath: F:\Audiobookshelf\Books
```

#### 8. Enable Rate Limiting
```env
MAM_RATE_LIMIT_MIN=3  # Minimum 3 seconds between requests
MAM_RATE_LIMIT_MAX=10 # Maximum 10 seconds between requests
```

#### 9. Test Full Workflow
Run one complete sync to verify everything works:
```bash
python master_audiobook_manager.py --full-sync
```

Expected output:
```
Step 1: Updating metadata... OK
Step 2: Detecting missing books... FOUND 66
Step 3: Running top 10 search... COMPLETED
Search report saved: search_results/selenium_search_HHMMSS.md
```

#### 10. Monitor First Scheduled Run
- Set scheduler to start after hours (e.g., 2:00 AM)
- Watch server logs during execution
- Check qBittorrent for new torrents
- Verify reports are generated

---

## VERIFICATION CHECKLIST

### Pre-Production Verification

- [ ] PostgreSQL database is running and accessible
- [ ] Audiobookshelf is running on localhost:13378
- [ ] qBittorrent is running on localhost:52095
- [ ] MyAnonamouse credentials are correct
- [ ] All API keys are set (.env file)
- [ ] qBittorrent category "audiobooks" exists
- [ ] Download path exists (F:\Audiobookshelf\Books)
- [ ] One manual full-sync runs successfully
- [ ] Tasks appear in scheduler status
- [ ] FastAPI server starts without errors

### Weekly Verification

- [ ] Check that at least one scheduled task ran
- [ ] Verify qBittorrent has new torrents (should increase)
- [ ] Check database for task records
- [ ] Verify no error entries in logs
- [ ] Check ratio on MAM (should be stable/improving)

### Monthly Verification

- [ ] Run full-sync manually for validation
- [ ] Review all generated reports
- [ ] Verify metadata is up-to-date in Audiobookshelf
- [ ] Check task execution history
- [ ] Review any failed tasks

---

## MONITORING & HEALTH CHECKS

### How to Know Everything is Working

**Check 1: Scheduler Status**
```bash
curl http://localhost:8000/api/scheduler/status \
  -H "X-API-Key: your-secret-api-key"
```
Should show `"running": true` and 18 jobs listed.

**Check 2: Task History**
```bash
curl http://localhost:8000/api/scheduler/tasks/history \
  -H "X-API-Key: your-secret-api-key"
```
Should show recently completed tasks with status "completed".

**Check 3: qBittorrent Queue**
```bash
python qbittorrent_session_client.py
```
Should show current torrent count.

**Check 4: Database Connection**
```bash
psql -U audiobook_user -h localhost -d audiobook_automation -c "SELECT COUNT(*) FROM tasks;"
```
Should return number of completed tasks.

**Check 5: Recent Logs**
```bash
tail -50 logs/fastapi.log
```
Should show recent scheduled task completions.

### Warning Signs

| Sign | Meaning | Fix |
|------|---------|-----|
| "No connection to database" | PostgreSQL down | Restart PostgreSQL |
| "qBittorrent login failed" | Wrong credentials | Verify `.env` QB_HOST, QB_PORT, QB_USERNAME |
| "Scheduler not running" | APScheduler not started | Restart FastAPI server |
| "0 jobs registered" | Task registration failed | Check config file syntax |
| "Connection timeout" | Network issue | Verify firewall, check IP addresses |

---

## TROUBLESHOOTING

### Problem: FastAPI Server Won't Start

**Error:** `ModuleNotFoundError: No module named 'fastapi'`

**Solution:**
```bash
# Activate virtual environment
venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt

# Try starting again
python backend/main.py
```

### Problem: PostgreSQL Connection Failed

**Error:** `could not connect to server: No such file or directory`

**Solution:**
1. Verify PostgreSQL is installed
2. Check it's running: `pg_isready`
3. Verify connection string in `.env`
4. Check username/password are correct

### Problem: qBittorrent Connection Failed

**Error:** `Connection to 192.168.0.48 timed out`

**Solution:**
```bash
# Verify qBittorrent is running
# Check it's on localhost, not remote IP
python qbittorrent_session_client.py

# Verify port 52095 is open
netstat -ano | findstr 52095
```

### Problem: MAM Login Fails

**Error:** `Login timeout` or `Login failed`

**Solution:**
1. Verify credentials in `.env` are exact
2. Check MAM website is accessible (not blocked)
3. Check rate limiting isn't too aggressive
4. Verify user has VIP status (recommended)

### Problem: No Torrents Being Queued

**Error:** Tasks run but 0 torrents found

**Possible Causes:**
1. Search terms not finding results (normal, depends on library)
2. All results already in queue (duplicate detection)
3. qBittorrent not accepting connections
4. Magnet link extraction failing

**Solution:**
1. Check search report: `search_results/selenium_search_*.md`
2. Verify qBittorrent is accepting connections
3. Run manual search with verbose output
4. Check logs for specific errors

### Problem: Tasks Not Running on Schedule

**Error:** Scheduled time passes but task doesn't run

**Solution:**
1. Check scheduler status: `curl http://localhost:8000/api/scheduler/status`
2. Verify `SCHEDULER_ENABLED=true` in `.env`
3. Check cron syntax in task configuration
4. Verify system time is correct (use NTP)
5. Restart FastAPI server

### Problem: High CPU Usage

**Cause:** Selenium WebDriver may be memory-intensive

**Solution:**
1. Run searches during off-peak hours
2. Limit download rate: `GAP_MAX_DOWNLOADS_PER_RUN=5`
3. Increase delay between searches
4. Run on dedicated machine if possible

---

## QUICK START GUIDE FOR PRODUCTION

### Day 1: Setup

```bash
# 1. Verify all services are running
psql -c "SELECT 1"                          # PostgreSQL
curl http://localhost:13378/health          # Audiobookshelf
python qbittorrent_session_client.py        # qBittorrent

# 2. Verify configuration
cat .env | grep -E "QB_|MAM_|ABS_"

# 3. Test full workflow
python master_audiobook_manager.py --full-sync

# 4. Start scheduler
python backend/main.py
```

### Day 2+: Monitor

```bash
# Check scheduler status
curl http://localhost:8000/api/scheduler/status

# Check task history
curl http://localhost:8000/api/scheduler/tasks/history

# View recent logs
tail -50 logs/fastapi.log

# Check qBittorrent queue
python qbittorrent_session_client.py
```

### On Issues

```bash
# Check database
psql -c "SELECT task_name, status, COUNT(*) FROM tasks GROUP BY task_name, status;"

# Check logs for errors
grep -i "error" logs/fastapi.log | tail -20

# Restart scheduler
# Ctrl+C on FastAPI server, then
python backend/main.py
```

---

## PRODUCTION DEPLOYMENT CHECKLIST

- [ ] All credentials changed from default
- [ ] PostgreSQL backup configured
- [ ] qBittorrent backup configured
- [ ] Logging level set to INFO (not DEBUG)
- [ ] Error monitoring configured (optional: send logs to service)
- [ ] Database auto-backups enabled
- [ ] Server runs 24/7 (use process manager like systemd)
- [ ] Firewall allows port 8000 for API access
- [ ] Cron job created to restart server on reboot
- [ ] Notification system for failed tasks (optional)

---

## FINAL NOTES

### System is Production-Ready When:
- ✓ FastAPI server starts without errors
- ✓ All 18 tasks registered and showing next run times
- ✓ One manual full-sync completes successfully
- ✓ qBittorrent receives torrents and starts downloading
- ✓ No errors in logs for 24 hours
- ✓ At least one scheduled task completes successfully

### The System Will:
- Automatically search for missing audiobooks
- Queue them to qBittorrent for download
- Update metadata in Audiobookshelf
- Monitor seeding ratios
- Maintain VIP status
- Generate reports of all activities
- Log all errors for troubleshooting

### The System Will NOT:
- Delete any existing books
- Modify your library structure
- Stop respecting rate limits (polite crawler)
- Download duplicate audiobooks
- Exceed your configured ratio thresholds

---

## Support & Maintenance

**For system issues:**
1. Check logs: `logs/fastapi.log`
2. Check database history: `backend/models/task.py`
3. Verify configuration: `.env` file
4. Restart services in this order:
   - PostgreSQL
   - qBittorrent
   - FastAPI server

**For new features:**
- See `backend/schedulers/tasks.py` for task templates
- Add new task to `register_tasks.py`
- Use existing patterns for consistency

---

**System Successfully Deployed:** 2025-11-23
**Last Verified:** Full workflow execution successful
**Next Maintenance:** As needed based on logs

