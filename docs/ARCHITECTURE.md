# System Architecture Documentation

**Version:** 1.0
**Created:** 2025-11-16
**Status:** Design Phase (Pre-Implementation)

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow Diagrams](#data-flow-diagrams)
4. [Workflow Diagrams](#workflow-diagrams)
5. [Module Interactions](#module-interactions)
6. [Technology Stack](#technology-stack)
7. [Deployment Architecture](#deployment-architecture)
8. [Security Architecture](#security-architecture)

---

## System Overview

The audiobook automation system is a unified backend that orchestrates multiple workflows for discovering, downloading, importing, and enriching audiobooks in an Audiobookshelf library.

**Core Responsibilities:**
1. Schedule and execute automated tasks (MAM scraping, metadata correction, series/author completion)
2. Provide REST API for user control and monitoring
3. Store all operational data in PostgreSQL
4. Integrate with external systems (Audiobookshelf, qBittorrent, Prowlarr, Google Books, Goodreads)
5. Track download progress and metadata quality
6. Log all failures for analytics

---

## Component Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND APPLICATION                          │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                         API LAYER (FastAPI)                              │
├──────────────────────────────────────────────────────────────────────────┤
│  Routes:                                                                  │
│  ├─ /api/author/search          → Author search + completion status      │
│  ├─ /api/series/search          → Series search + completion status      │
│  ├─ /api/books/missing          → List missing books (series/author)     │
│  ├─ /api/top10/weekly           → Weekly top-10 results                  │
│  ├─ /api/metadata/status        → Metadata completeness report           │
│  ├─ /api/trigger/rescan         → Manual Audiobookshelf rescan trigger   │
│  ├─ /api/trigger/rescrape       → Manual metadata rescrape trigger       │
│  ├─ /api/trigger/redownload     → Manual download retry trigger          │
│  └─ /api/system/stats           → System health + analytics              │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                    SCHEDULER LAYER (APScheduler)                         │
├──────────────────────────────────────────────────────────────────────────┤
│  Scheduled Tasks:                                                         │
│  ├─ Daily 2:00 AM      → MAM Scraping (stealth_mam_crawler.py)           │
│  ├─ Sunday 3:00 AM     → Weekly Genre Top-10 (MAM visual extraction)     │
│  ├─ 1st 4:00 AM        → Monthly Full Metadata Refresh (all books)       │
│  ├─ Sunday 4:30 AM     → Weekly New-Books Metadata Refresh               │
│  ├─ 2nd 3:00 AM        → Series Completion Scan (Goodreads source)       │
│  ├─ 3rd 3:00 AM        → Author Completion Scan (multi-source)           │
│  └─ Nightly 1:00 AM    → Download Retry Scheduling + History Cleanup     │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                    BUSINESS LOGIC LAYER (Task Handlers)                  │
├──────────────────────────────────────────────────────────────────────────┤
│  Task Modules:                                                            │
│  ├─ mam_scraper.py             → Call stealth_mam_crawler, log results   │
│  ├─ genre_top10.py             → Extract top-10 from MAM, queue to      │
│  │                                Prowlarr → qBittorrent                  │
│  ├─ metadata_corrector.py       → Google Books + Goodreads lookup        │
│  ├─ series_completer.py         → Find missing series books + download    │
│  ├─ author_completer.py         → Find missing author audiobooks +        │
│  │                                download                                │
│  ├─ download_manager.py         → Handle qBittorrent downloads + import   │
│  └─ task_logger.py              → Log all task executions + failures     │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                  INTEGRATION LAYER (External APIs)                       │
├──────────────────────────────────────────────────────────────────────────┤
│  API Clients:                                                             │
│  ├─ abs_client.py               → Audiobookshelf API                     │
│  │  ├─ List books               ├─ Get metadata                         │
│  │  ├─ Import books             └─ Update metadata                      │
│  │  └─ Scan library                                                      │
│  ├─ qbittorrent_client.py       → qBittorrent API                        │
│  │  ├─ Add torrents             ├─ Monitor downloads                    │
│  │  └─ Get download status       └─ Remove torrents                     │
│  ├─ prowlarr_client.py          → Prowlarr API                           │
│  │  ├─ Search for books         └─ Get magnet links                    │
│  ├─ googlebooks_client.py       → Google Books API                       │
│  │  ├─ Search by title          ├─ Lookup by ISBN                      │
│  │  └─ Get metadata                                                      │
│  ├─ goodreads_client.py         → Goodreads Scraper                      │
│  │  ├─ Get series list          ├─ Get author books                    │
│  │  └─ Get metadata             └─ Author search                        │
│  └─ mam_client.py               → MAM Scraper                            │
│     ├─ Search books             └─ Extract top-10 per genre             │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                    DATABASE LAYER (SQLAlchemy ORM)                       │
├──────────────────────────────────────────────────────────────────────────┤
│  Models & CRUD:                                                           │
│  ├─ models.py                  → SQLAlchemy ORM definitions              │
│  ├─ crud.py                    → Database operations                     │
│  ├─ database.py                → Session management                      │
│  └─ queries.py                 → Complex query builders                  │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│              PERSISTENCE LAYER (PostgreSQL Database)                     │
├──────────────────────────────────────────────────────────────────────────┤
│  Tables:                                                                  │
│  ├─ books                      ├─ downloads                             │
│  ├─ series                      ├─ tasks                                 │
│  ├─ authors                     ├─ failed_attempts                       │
│  ├─ missing_books              └─ metadata_corrections                   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagrams

### 1. Book Import Flow (Immediate Metadata Correction)

```
User Action: Import book to Audiobookshelf
        ↓
Audiobookshelf API Webhook / Event
        ↓
Backend receives import event
        ↓
Extract book metadata from ABS
        ↓
┌───────────────────────────────────────────┐
│ Metadata Correction Pipeline              │
│                                           │
│ 1. Query Google Books API                 │
│    ├─ If found: partial metadata          │
│    └─ If not found: continue to #2        │
│                                           │
│ 2. Query Goodreads scraper                │
│    ├─ If found: fill missing fields       │
│    └─ If not found: use partial result    │
│                                           │
│ 3. Store metadata source mapping          │
│    ("title": "GoogleBooks",               │
│     "author": "Goodreads", ...)           │
│                                           │
│ 4. Update book in PostgreSQL              │
│    with metadata_completeness_percent     │
└───────────────────────────────────────────┘
        ↓
Store correction history in PostgreSQL
        ↓
Return result to caller
```

### 2. Weekly Top-10 Download Flow

```
APScheduler triggers: Sunday 3:00 AM
        ↓
backend/tasks/top10.py:run()
        ↓
For each enabled genre in genre_settings:
        ↓
┌──────────────────────────────────────────────┐
│ MAM Top-10 Extraction                        │
│                                              │
│ 1. Visual scrape MAM for genre               │
│    (using existing scraper logic)            │
│                                              │
│ 2. Extract top 10 torrents                   │
│    (title, author, seeders, size)            │
│                                              │
│ 3. Query qBittorrent to filter               │
│    out already-downloading books             │
│                                              │
│ 4. For each new torrent:                     │
│    Query Prowlarr API for magnet link        │
└──────────────────────────────────────────────┘
        ↓
Send magnet links to Prowlarr
        ↓
Prowlarr adds to qBittorrent watch folder
        ↓
qBittorrent starts downloads
        ↓
Download Manager monitors qBittorrent
        ↓
When download completes:
    ├─ Import to Audiobookshelf
    ├─ Run metadata correction
    ├─ Log success to downloads table
    └─ Update missing_books status
        ↓
If download fails:
    ├─ Log failure to failed_attempts
    ├─ Schedule retry (next_retry timestamp)
    └─ Increment retry_count
```

### 3. Series Completion Flow

```
APScheduler triggers: 2nd at 3:00 AM
        ↓
backend/tasks/series_completion.py:run()
        ↓
Fetch all series from books table
        ↓
For each series with books_owned >= 1:
        ↓
┌─────────────────────────────────────────────┐
│ Goodreads Series Lookup                     │
│                                             │
│ 1. Query Goodreads for full series list     │
│ 2. Get all books in series + metadata       │
│ 3. Compare to library (books table)         │
│ 4. Identify missing books                   │
│ 5. Store in missing_books table             │
│    (reason_missing: "series_gap")           │
└─────────────────────────────────────────────┘
        ↓
Batch missing books into groups of 10
        ↓
For each batch:
        ↓
┌─────────────────────────────────────────────┐
│ Download Pipeline (MAM → Google → Goodreads)│
│                                             │
│ For each missing book:                      │
│                                             │
│ 1. Try MAM:                                 │
│    Search by title+author                   │
│    ├─ If found: get magnet                  │
│    └─ If not: go to #2                      │
│                                             │
│ 2. Try Google Books:                        │
│    Search by ISBN/title                     │
│    ├─ If found: search torrent sites        │
│    └─ If not: go to #3                      │
│                                             │
│ 3. Try Goodreads:                           │
│    Use book data from Goodreads             │
│    ├─ Extract ISBN                          │
│    └─ Search torrent sites                  │
└─────────────────────────────────────────────┘
        ↓
Queue downloads to downloads table
        ↓
Wait for Download Manager to complete
        ↓
When all downloads in batch complete:
    ├─ Import to Audiobookshelf
    ├─ Run series-linking pipeline
    ├─ Run metadata correction
    └─ Log completion in tasks table
```

### 4. Author Completion Flow

```
APScheduler triggers: 3rd at 3:00 AM
        ↓
backend/tasks/author_completion.py:run()
        ↓
Fetch all authors from books table
        ↓
For each author:
        ↓
┌─────────────────────────────────────────────┐
│ External Source Search (multi-source)       │
│                                             │
│ Query each source for all audiobooks:       │
│                                             │
│ 1. MAM search (author name)                 │
│ 2. Google Books (author ID)                 │
│ 3. Goodreads (author ID + "audiobooks")     │
│                                             │
│ Consolidate unique books from all sources   │
│ Store in authors table:                     │
│   total_audiobooks_external = count         │
└─────────────────────────────────────────────┘
        ↓
Compare to library (books table)
        ↓
Identify missing audiobooks
        ↓
Store in missing_books table
    (reason_missing: "author_gap")
        ↓
Queue downloads (same as Series Completion)
        ↓
Download Manager processes batch by batch
        ↓
When downloads complete:
    ├─ Import to Audiobookshelf
    ├─ Run metadata correction
    └─ Log completion
```

### 5. Download Retry Loop

```
APScheduler triggers: Nightly 1:00 AM
        ↓
backend/tasks/download_retry.py:run()
        ↓
Query downloads table:
    WHERE status = 'failed'
    AND next_retry <= NOW()
    AND retry_count < max_retries
        ↓
For each failed download:
        ↓
Try download again (MAM → Google → Goodreads)
        ↓
If successful:
    ├─ Update status = "downloading"
    ├─ Queue for import
    └─ Reset retry_count
        ↓
If still fails:
    ├─ Increment retry_count
    ├─ Calculate next_retry
    │  (exponential backoff: 1 day, 3 days, 7 days)
    ├─ If retry_count >= max_retries:
    │  ├─ status = "abandoned"
    │  └─ Log to failed_attempts table
    └─ Continue loop
```

---

## Workflow Diagrams

### 1. Daily MAM Scraping Workflow

```
Scheduler: Daily at 2:00 AM
    ↓
Invoke: backend/tasks/mam_scraper.py:run()
    ↓
Log task to tasks table (status: "running")
    ↓
Call: stealth_mam_crawler.py
    (existing script, unchanged)
    ↓
    ├─ Authenticate to MAM
    ├─ Apply stealth measures
    ├─ Rate limiting (3-10 sec delays)
    ├─ Crawl guides/forums/torrents
    └─ Save to guides_output/
    ↓
Parse output from scraper
    ↓
Store discovered books in books table
    (import_source: "mam_scraper")
    ↓
For each new book:
    └─ Trigger immediate metadata correction
      (by adding to metadata_corrector task queue)
    ↓
Log task completion to tasks table
    (status: "completed", items_processed, items_succeeded)
    ↓
Send notification (optional): "MAM scrape complete: X new books"
```

### 2. Metadata Correction Workflow

```
Trigger: Immediate (on book import) OR Scheduled (weekly/monthly)
    ↓
Invoke: backend/tasks/metadata_corrector.py:run(scope, books)
    ↓
For each book:
    ↓
    ┌─────────────────────────────────────────┐
    │ Attempt 1: Google Books API             │
    ├─────────────────────────────────────────┤
    │ Search by: ISBN → Title+Author → ASIN   │
    │ Fields retrieved: title, author,        │
    │  publisher, published_year, description │
    │                                         │
    │ Retry if: Timeout, rate limit hit       │
    │ Max retries: 2                          │
    │                                         │
    │ Result:                                 │
    │ ├─ full match (all fields found)        │
    │ ├─ partial match (some fields found)    │
    │ └─ no match                             │
    └─────────────────────────────────────────┘
         ↓
    ┌─────────────────────────────────────────┐
    │ Attempt 2: Goodreads Scraper            │
    ├─────────────────────────────────────────┤
    │ Triggered if: No match OR partial match │
    │                                         │
    │ Search by: Title+Author → ISBN          │
    │ Fields retrieved: series, series#,      │
    │  rating, author_bio, genres, similar    │
    │                                         │
    │ Retry if: Timeout, rate limit hit       │
    │ Max retries: 2                          │
    │                                         │
    │ Fill missing: If Google gave partial,   │
    │ Goodreads fills in the gaps             │
    └─────────────────────────────────────────┘
         ↓
    Store metadata_source mapping:
    {
        "title": "GoogleBooks",
        "author": "GoogleBooks",
        "series": "Goodreads",
        ...
    }
         ↓
    Update books table:
    ├─ All metadata fields
    ├─ metadata_completeness_percent
    ├─ last_metadata_update
    └─ metadata_source (JSONB)
         ↓
    Log correction history:
    for each changed field:
        INSERT INTO metadata_corrections
        (book_id, field, old_value, new_value, source, correction_date)
         ↓
    Increment metadata_completeness_percent
```

### 3. Download Processing Workflow

```
Download queued in downloads table
    ↓
Download Manager monitors qBittorrent
    ↓
┌──────────────────────────────────────┐
│ Download Monitoring                  │
│                                      │
│ Poll qBittorrent every 30 seconds:   │
│ ├─ Check status of all active hashes │
│ ├─ Update qbittorrent_status column  │
│ ├─ Track progress                    │
│ └─ Detect completion                 │
└──────────────────────────────────────┘
    ↓
When download 100% complete:
    ├─ Update status = "completed"
    ├─ Store abs_import_status = "pending"
    └─ Queue for Audiobookshelf import
    ↓
Import to Audiobookshelf:
    ├─ Get file from qBittorrent folder
    ├─ Call ABS import API
    ├─ Wait for import to complete
    ├─ Verify book appears in ABS
    └─ Update abs_import_status = "imported"
    ↓
Run metadata correction on imported book
    ↓
If series book: Run series-linking pipeline
    ├─ Update series table (books_owned++)
    ├─ Link book to series
    └─ Update completion_percentage
    ↓
If author book: Update authors table
    ├─ audiobooks_owned++
    └─ Update completion_percentage
    ↓
Log success to tasks table
    ↓
Update missing_books table:
    (if was missing)
    ├─ download_status = "completed"
    └─ book_id = newly_imported_book_id
```

---

## Module Interactions

### Request Processing Pipeline

```
HTTP Request
    ↓
FastAPI Router (@app.get/post)
    ↓
Input Validation (Pydantic models)
    ↓
Authentication (API key check)
    ↓
Authorization (user permissions)
    ↓
Handler Function (business logic)
    ├─ Query Database (CRUD operations)
    ├─ Call Integration Layer (external APIs)
    ├─ Log to PostgreSQL
    └─ Aggregate results
    ↓
Serialize Response (JSON)
    ↓
HTTP Response (200, 404, 500, etc.)
```

### Scheduled Task Execution

```
APScheduler tick every second
    ↓
Check if any task is due to run
    ↓
If task due:
    ├─ Create task record (status: "scheduled")
    ├─ Invoke task handler
    ├─ Update status = "running"
    ├─ Capture start time
    └─ Execute business logic
    ↓
Task Handler:
    ├─ Call Integration Layer (ABS, qBT, Prowlarr APIs)
    ├─ Process results
    ├─ Store in PostgreSQL
    ├─ Log progress
    └─ Return completion status
    ↓
Update task record:
    ├─ status = "completed" or "failed"
    ├─ actual_end time
    ├─ duration_seconds
    ├─ items_processed / items_succeeded / items_failed
    ├─ log_output
    └─ error_message (if failed)
    ↓
Log any failures to failed_attempts table
    ↓
Task complete; scheduler continues
```

---

## Technology Stack

### Backend Framework
- **FastAPI** (Python web framework)
  - Async request handling
  - Built-in API documentation (Swagger UI)
  - Pydantic validation
  - CORS support

### Task Scheduling
- **APScheduler** (Python scheduling library)
  - Cron-like scheduling (daily, weekly, monthly)
  - Timezone support
  - Persistent job store (PostgreSQL)
  - Error handling and retries

### Database
- **PostgreSQL** (relational database)
  - Transactions for data consistency
  - Indexes for performance
  - JSONB for flexible metadata storage
  - Views for complex queries

### ORM & Database Tools
- **SQLAlchemy** (Python ORM)
  - Model definitions
  - Query builder
  - Migration management (Alembic)

### External Integrations
- **requests** (HTTP client)
- **beautifulsoup4** (HTML parsing for scrapers)
- **selenium/playwright** (browser automation if needed)

### Authentication & Security
- **python-dotenv** (environment variable management)
- **bcrypt** (password hashing for future multi-user)
- **python-jose** (JWT tokens for future auth)

### Testing & Development
- **pytest** (unit testing)
- **pytest-asyncio** (async test support)
- **sqlalchemy-utils** (testing utilities)

---

## Deployment Architecture

### Local Deployment (Same Machine)

```
Machine: C:\Users\dogma\Projects\MAMcrawler

┌─────────────────────────────────────────────────────┐
│  Windows Services & Applications                    │
├─────────────────────────────────────────────────────┤
│  ├─ PostgreSQL Database (Port 5432)                 │
│  ├─ FastAPI Backend (Port 8000)                     │
│  ├─ Audiobookshelf (Port 13378)                     │
│  ├─ qBittorrent Web UI (Port 52095)                 │
│  └─ Prowlarr (Port 9696)                            │
├─────────────────────────────────────────────────────┤
│  ├─ stealth_mam_crawler.py (existing, called by     │
│  │                           backend)               │
│  ├─ goodreads_scraper.py (existing)                 │
│  ├─ googlebooks_api.py (existing)                   │
│  └─ [other existing scripts]                        │
└─────────────────────────────────────────────────────┘

Network Connectivity:
  ├─ PostgreSQL: localhost:5432
  ├─ FastAPI: localhost:8000 (REST API)
  ├─ Audiobookshelf: localhost:13378
  ├─ qBittorrent: 192.168.0.48:52095 (local network)
  ├─ Prowlarr: localhost:9696
  └─ External: MAM, Goodreads, Google Books (internet)
```

### Configuration Files

```
Project Root:
├─ .env                      # Credentials & config
├─ database_schema.sql       # PostgreSQL schema
└─ backend/
   ├─ main.py               # FastAPI app entry point
   ├─ config.py             # Settings from .env
   ├─ requirements.txt       # Python dependencies
   │
   ├─ routes/
   │  ├─ __init__.py
   │  ├─ authors.py          # /api/author/* endpoints
   │  ├─ series.py           # /api/series/* endpoints
   │  ├─ books.py            # /api/books/* endpoints
   │  ├─ tasks.py            # /api/trigger/* endpoints
   │  └─ system.py           # /api/system/* endpoints
   │
   ├─ tasks/
   │  ├─ __init__.py
   │  ├─ mam_scraper.py
   │  ├─ genre_top10.py
   │  ├─ metadata_corrector.py
   │  ├─ series_completer.py
   │  ├─ author_completer.py
   │  ├─ download_manager.py
   │  └─ scheduler.py        # APScheduler setup
   │
   ├─ integrations/
   │  ├─ __init__.py
   │  ├─ abs_client.py
   │  ├─ qbittorrent_client.py
   │  ├─ prowlarr_client.py
   │  ├─ googlebooks_client.py
   │  ├─ goodreads_client.py
   │  └─ mam_client.py
   │
   ├─ db/
   │  ├─ __init__.py
   │  ├─ models.py           # SQLAlchemy ORM models
   │  ├─ database.py         # Session management
   │  ├─ crud.py             # Database operations
   │  └─ queries.py          # Complex queries
   │
   ├─ modules/
   │  ├─ stealth_mam_crawler.py  (wrapper/symlink to existing)
   │  ├─ goodreads_scraper.py    (wrapper/symlink to existing)
   │  └─ [other existing scripts]
   │
   ├─ schemas/
   │  ├─ __init__.py
   │  ├─ books.py
   │  ├─ series.py
   │  ├─ authors.py
   │  └─ [Pydantic models]
   │
   └─ utils/
      ├─ __init__.py
      ├─ logger.py          # Logging setup
      ├─ exceptions.py      # Custom exceptions
      └─ helpers.py         # Utility functions
```

---

## Security Architecture

### API Security

```
Request comes in:
    ↓
Check HTTP headers for API key
    ├─ If missing: Return 401 Unauthorized
    └─ If present: Continue
    ↓
Validate API key against database
    ├─ If invalid: Return 403 Forbidden
    └─ If valid: Continue
    ↓
Log API call to api_logs table
    (endpoint, method, user_id, ip_address, response_code)
    ↓
Check user permissions
    ├─ Can they access this resource?
    ├─ Can they perform this action?
    └─ (future multi-user support)
    ↓
Process request
    ↓
Return response
```

### Credential Management

```
Sensitive credentials stored in .env:
├─ MAM_USERNAME
├─ MAM_PASSWORD
├─ PROWLARR_API_KEY
├─ ABS_TOKEN
├─ GOOGLE_BOOKS_API_KEY
└─ [others]

At runtime:
├─ Load from .env via python-dotenv
├─ Store in config.py (not in Git)
├─ Pass to integration clients
├─ Never log or expose in errors
└─ Use in headers/params as needed
```

### Data Protection

```
Database:
├─ Connection via localhost (local machine)
├─ Credentials in .env (not in code)
├─ Sensitive fields NOT stored (don't keep API keys in DB)
└─ Logs sanitized (no passwords in error messages)

Failed attempts table:
├─ Contains error details
├─ Sanitized to exclude credentials
├─ Permanent retention for analytics
└─ Access restricted to admin users
```

---

## Future Enhancements

### Multi-User Support
- Add `user_id` to all relevant tables
- Implement JWT authentication
- Per-user API credentials and rate limits
- Per-user library isolation
- Per-user scheduling preferences

### Advanced Features
- Web UI dashboard (React/Vue.js)
- Push notifications (Discord, email, mobile)
- Book ratings and reviews
- Reading progress tracking
- Advanced search (Elasticsearch)
- Machine learning recommendations
- Book cover art management
- Full-text search across book descriptions

### Performance Improvements
- Redis caching for frequently accessed data
- Batch operations for bulk updates
- Connection pooling for databases
- Async processing for long-running tasks
- Distributed task processing (Celery)

### Monitoring & Analytics
- Prometheus metrics export
- Grafana dashboards
- System health checks
- Performance profiling
- Cost analytics (bandwidth, storage)

---

**Document Version:** 1.0 (Design Phase)
**Last Updated:** 2025-11-16
**Status:** Ready for Phase 2 (FastAPI Implementation)
