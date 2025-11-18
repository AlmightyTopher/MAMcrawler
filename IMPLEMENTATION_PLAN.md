# Audiobook Automation System - Implementation Plan

**Status:** Awaiting final confirmation before coding
**Start Date:** 2025-11-16
**Tech Stack:** FastAPI + PostgreSQL + APScheduler

---

## Executive Summary

Extend existing audiobook automation system by:
1. Building unified FastAPI backend
2. Creating PostgreSQL database for orchestration
3. Wrapping existing scripts as importable modules
4. Automating 6 major workflows (MAM, Top-10, Metadata, Series, Authors, Monitoring)
5. Exposing 9 REST API endpoints for control + monitoring
6. Supporting future multi-user expansion

**All existing scripts retained and callable from backend.**

---

## Task Definitions & Confirmation Checklist

### **Task 1: MAM Scraping** ✓
```
Status: USE EXISTING CRAWLER UNCHANGED
Trigger: Daily at 2:00 AM (backend scheduler)
Script: stealth_mam_crawler.py (no modifications)
Output: Appends to existing guides_output/ directory
Logging: Task execution logged in PostgreSQL tasks table
Changes: None to script itself; backend only calls it
```
**Confirmation needed:** Keep script 100% unchanged? ✓

---

### **Task 2: Weekly Genre Top-10** ✓
```
Status: NEW FEATURE
Trigger: Sunday at 3:00 AM (backend scheduler)
Source: MAM visual scrape for each genre's top-10
Genres: User-provided list (you'll supply this)
Handoff: Send magnet links to Prowlarr (existing integration)
Download: qBittorrent downloads → Audiobookshelf imports
Retries: 3 attempts per failed download, then log + tally
Logging: All steps in PostgreSQL (downloads table, failed_attempts table)
```
**Confirmation needed:** Genres list + retry behavior? ✓

---

### **Task 3: Metadata Correction** ✓
```
Status: NEW FEATURE
Scheduling:
  - Monthly full library: 1st at 4:00 AM (all ~1,600 books)
  - Weekly new books: Sunday at 4:30 AM (past 7 days only)
  - Immediate: On book import event (triggered by ABS API)

Sources:
  1. Google Books API (primary)
  2. Goodreads scraper (secondary, fills gaps)

Logic:
  - Try Google Books first
  - If partial result, Goodreads fills missing fields
  - Track which source provided each field
  - 2 retries per source before giving up

Logging:
  - Track per-field metadata source in PostgreSQL
  - Log failures with reason codes
```
**Confirmation needed:** Per-field source tracking + partial-fill behavior? ✓

---

### **Task 4: Series Completion** ✓
```
Status: NEW FEATURE
Trigger: Monthly on 2nd at 3:00 AM (backend scheduler)

Process:
  1. Get all series from Audiobookshelf
  2. For each series where I own ≥1 book:
     - Query Goodreads for complete series list
     - Identify missing books in my library
     - Download missing books in batches of 10
  3. Auto-import to Audiobookshelf
  4. Run metadata correction pipeline
  5. Run series-linking pipeline

Download Priority: MAM → Google Books → Goodreads

Logging:
  - Track series completion status per series
  - Log each download attempt (success/failure)
  - Store missing book list in PostgreSQL
```
**Confirmation needed:** Batch size of 10 + series-linking trigger? ✓

---

### **Task 5: Author Completion** ✓
```
Status: NEW FEATURE
Trigger: Monthly on 3rd at 3:00 AM (backend scheduler)

Process:
  1. Get all authors from Audiobookshelf
  2. For each author, query external sources for all audiobooks:
     - MAM search
     - Google Books API
     - Goodreads scraper
  3. Compare to library; identify missing audiobooks
  4. Download missing audiobooks
  5. Auto-import to Audiobookshelf
  6. Run metadata correction pipeline

Download Priority: MAM → Google Books → Goodreads

Logging:
  - Track all audiobooks found per author
  - Log missing audiobooks per author
  - Permanent failed-attempt tally
  - Track which downloads succeeded/failed
```
**Confirmation needed:** All external sources or limit to top N authors? ✓

---

### **Task 6: Backend (FastAPI + PostgreSQL)** ✓
```
Status: BUILD NEW BACKEND
Framework: FastAPI
Database: PostgreSQL
Scheduler: APScheduler
Auth: API key (configurable)

Endpoints:
  GET  /api/author/search?name=<name>
    → Returns: matching authors, their books, missing audiobooks

  GET  /api/series/search?name=<name>
    → Returns: matching series, books owned, missing books

  GET  /api/books/missing?type=<series|author>&id=<id>
    → Returns: list of missing books for a series or author

  GET  /api/top10/weekly
    → Returns: last week's top-10 results (per genre)

  GET  /api/metadata/status
    → Returns: all books + metadata completeness (% complete per field)

  POST /api/trigger/rescan
    → Manually trigger Audiobookshelf rescan

  POST /api/trigger/rescrape
    → Manually trigger metadata rescrape for all books

  POST /api/trigger/redownload?book_id=<id>
    → Manually retry download for a specific book

  GET  /api/system/stats
    → Returns: system health, task history, failure rates

Integration:
  - qBittorrent API: Add torrents, monitor downloads
  - Audiobookshelf API: List books, import, scan, update metadata
  - Prowlarr API: Search, get magnet links
  - Google Books API: Metadata lookup
  - Goodreads API: Series data, metadata

Scheduling:
  - Daily 2:00 AM: MAM scrape
  - Sunday 3:00 AM: Genre top-10
  - 1st 4:00 AM: Full metadata refresh
  - Sunday 4:30 AM: New books metadata refresh
  - 2nd 3:00 AM: Series completion
  - 3rd 3:00 AM: Author completion

Machine: Same as Audiobookshelf + qBittorrent
```
**Confirmation needed:** All 9 endpoints + scheduling times correct? ✓

---

### **Task 7: PostgreSQL Database Schema** ✓
```
Status: DESIGN SCHEMA FIRST

Tables:
  1. books
     - id, abs_id, title, author, series, isbn, asin
     - metadata_completeness (%), last_metadata_update
     - metadata_source (JSON: field → source mapping)
     - date_added, date_updated

  2. series
     - id, name, author, total_books
     - books_owned, books_missing
     - last_completion_check, completion_status
     - goodreads_id

  3. authors
     - id, name
     - total_audiobooks_found, audiobooks_owned, audiobooks_missing
     - last_completion_check
     - external_ids (JSON: MAM, Google Books, Goodreads)

  4. missing_books
     - id, book_id, series_id, author_id
     - title, reason_missing (series_gap | author_gap)
     - identified_date, download_status

  5. downloads
     - id, book_id, source (MAM|Google|Goodreads), magnet_link
     - status (queued|downloading|completed|failed)
     - retry_count, last_attempt, next_retry
     - abs_import_status

  6. tasks
     - id, task_name (MAM|TOP10|METADATA_FULL|METADATA_NEW|SERIES|AUTHOR)
     - scheduled_time, actual_start, actual_end
     - status (scheduled|running|completed|failed)
     - log_output, error_message

  7. failed_attempts
     - id, task_name, item_id (book/series/author), reason
     - first_attempt, last_attempt, attempt_count
     - created_at (never deleted)

  8. metadata_corrections
     - id, book_id, field, old_value, new_value
     - source (GoogleBooks|Goodreads|Manual)
     - correction_date

History Retention:
  - Keep 1 month of active data (tasks, downloads, metadata_corrections)
  - Delete older entries after 30 days
  - KEEP FOREVER: failed_attempts (for analytics)
```
**Confirmation needed:** Schema structure + retention policy? ✓

---

### **Task 8: Architecture & Integration** ✓
```
Status: DOCUMENT THEN BUILD

Components:

  Backend (FastAPI)
    ├── Routes (/api/*)
    ├── Scheduler (APScheduler)
    ├── Database layer (SQLAlchemy)
    ├── Module wrappers
    └── Integration layer (ABS, qBT, Prowlarr APIs)

  Modules (wrapped, importable):
    ├── stealth_mam_crawler.py (unchanged)
    ├── goodreads_scraper.py (unchanged)
    ├── googlebooks_api.py (existing)
    └── [others as needed]

  Database Layer:
    ├── models.py (SQLAlchemy ORM)
    ├── database.py (session management)
    └── crud.py (create, read, update, delete operations)

  Scheduling:
    ├── scheduler.py (APScheduler setup)
    └── tasks.py (task definitions)

  Integrations:
    ├── abs_client.py (Audiobookshelf API)
    ├── qbittorrent_client.py (qBittorrent API)
    ├── prowlarr_client.py (Prowlarr API)
    └── metadata_sources.py (Google Books, Goodreads)

Data Flow:
  User Request
    ↓
  FastAPI Endpoint
    ↓
  Business Logic (module wrappers)
    ↓
  PostgreSQL Database
    ↓
  Response

Execution Flow (Scheduled Tasks):
  APScheduler Trigger
    ↓
  Task Handler
    ↓
  Module Wrapper (calls existing scripts)
    ↓
  API Integration Layer (ABS, qBT, Prowlarr)
    ↓
  PostgreSQL Logging
    ↓
  Completion/Retry Logic

Multi-User Support:
  - Add user_id to all relevant tables
  - Filter API responses by authenticated user
  - Isolate user credentials in PostgreSQL
  - Support future UI per-user views

Documentation:
  /docs/
  ├── ARCHITECTURE.md (component diagrams, data flows)
  ├── API_REFERENCE.md (endpoint docs, examples)
  ├── DATABASE.md (ER diagram, table descriptions)
  ├── DEPLOYMENT.md (setup instructions)
  ├── WORKFLOW.md (scheduled task flows)
  └── MODULE_GUIDE.md (how to use each module)
```
**Confirmation needed:** Multi-user architecture + documentation structure? ✓

---

## Implementation Phases

### **Phase 1: Database Design + Architecture** (No Code)
- [ ] Create PostgreSQL schema (SQL file)
- [ ] Create ER diagram (visual)
- [ ] Create architecture diagram (data flows, modules)
- [ ] Create API documentation template
- [ ] Create task scheduling flowchart

### **Phase 2: FastAPI Project Setup**
- [ ] Initialize FastAPI project structure
- [ ] Set up SQLAlchemy ORM models
- [ ] Set up database session management
- [ ] Create .env configuration template
- [ ] Set up API key authentication

### **Phase 3: Module Wrappers**
- [ ] Convert stealth_mam_crawler to importable module
- [ ] Convert goodreads_scraper to importable module
- [ ] Create Audiobookshelf API wrapper
- [ ] Create qBittorrent API wrapper
- [ ] Create Prowlarr API wrapper
- [ ] Create Google Books API wrapper

### **Phase 4: Scheduler + Task Handlers**
- [ ] Set up APScheduler
- [ ] Create task definitions (all 6 workflows)
- [ ] Create task logging to PostgreSQL
- [ ] Create retry logic + error handling
- [ ] Create immediate triggers (manual + event-based)

### **Phase 5: API Endpoints**
- [ ] Implement 9 endpoints (GET/POST as needed)
- [ ] Add input validation
- [ ] Add response schemas
- [ ] Add error handling
- [ ] Test all endpoints

### **Phase 6: Integration + Documentation**
- [ ] End-to-end testing
- [ ] Create deployment guide
- [ ] Create user guide
- [ ] Create troubleshooting guide
- [ ] Create architecture documentation

---

## User-Provided Information Needed

Before starting Phase 1, please provide:

1. **Genre List** (for weekly top-10 feature)
   ```
   Example: ["Fantasy", "Science Fiction", "Mystery", "Romance", ...]
   ```

2. **qBittorrent Credentials**
   ```
   - Host: (IP or hostname)
   - Port: (default 6881)
   - Username: (if auth enabled)
   - Password: (if auth enabled)
   ```

3. **Audiobookshelf Credentials**
   ```
   - Host: localhost or IP
   - Port: (default 13378)
   - API Token: (generate in ABS settings)
   ```

4. **Prowlarr Credentials**
   ```
   - Host: (IP or hostname)
   - Port: (default 9696)
   - API Key: (generate in Prowlarr settings)
   ```

5. **Google Books API Key**
   ```
   - API Key: (from Google Cloud Console)
   ```

6. **MAM Credentials** (already have from existing crawler)
   ```
   - Username
   - Password
   ```

---

## Confirmation Checklist

Before I write any code, please confirm:

- [ ] All 8 tasks understood correctly
- [ ] All scheduling times correct
- [ ] Database schema approach correct
- [ ] FastAPI + PostgreSQL + APScheduler stack approved
- [ ] API endpoints list complete
- [ ] Module wrapping approach (importable, called by backend)
- [ ] 6-phase implementation plan acceptable
- [ ] Ready to provide genre list + credentials

---

## Timeline Estimate

Assuming 8-hour workday:
- **Phase 1 (DB + Architecture):** 2-3 hours (documentation)
- **Phase 2 (FastAPI Setup):** 2-3 hours
- **Phase 3 (Module Wrappers):** 4-6 hours
- **Phase 4 (Scheduler):** 4-6 hours
- **Phase 5 (API Endpoints):** 4-6 hours
- **Phase 6 (Integration + Docs):** 4-6 hours

**Total: 20-30 hours (~3-4 days)**

---

## Ready to Proceed?

Once you confirm all items above and provide the required information, I will:

1. Design PostgreSQL schema
2. Create architecture diagrams
3. Create FastAPI project structure
4. Build all 6 workflows
5. Expose all 9 endpoints
6. Document everything

**Waiting for your final confirmation to begin.**
