# MAMcrawler Codebase Comprehensive Analysis

**Analysis Date:** November 18, 2025  
**Codebase Scale:** 107+ Python files across root directory + extensive backend service layer  
**Architecture:** Hybrid (distributed crawlers + centralized FastAPI REST API with PostgreSQL)

---

## EXECUTIVE SUMMARY

The MAMcrawler project is a **production-grade audiobook automation system** that goes far beyond the documentation in CLAUDE.md. It implements:

1. **Multiple acquisition pipelines** - MAM torrent search, qBittorrent downloads, Google Books API, Goodreads integration
2. **Full library scanning** - Audiobookshelf integration with automatic library scanning
3. **Missing book detection** - Series completion analysis and gap identification  
4. **Metadata enrichment** - Multi-provider metadata aggregation (Google Books, Goodreads, Kindle, multiple local providers)
5. **REST API backend** - FastAPI-based service with scheduled jobs and comprehensive data tracking
6. **Database persistence** - PostgreSQL schema with books, series, authors, downloads, tasks, and failed attempts
7. **Advanced features** - VIP status management, fuzzy matching, metadata correction, batch automation

---

## PART 1: ALL PYTHON FILES & THEIR PURPOSES

### A. Core Crawler Infrastructure (13 files)

| File | Purpose |
|------|---------|
| `mam_crawler.py` | Original basic MAM crawler with authentication, rate limiting, guide extraction |
| `mam_crawler_config.py` | Configuration procedures, allowed paths, CSS extraction schemas |
| `stealth_mam_crawler.py` | Advanced stealth crawler with human-like delays (10-30s), viewport randomization, state persistence |
| `comprehensive_guide_crawler.py` | Extracts all guides from `/guides/` into individual markdown files |
| `stealth_mam_form_crawler.py` | Forum crawler for extracting qBittorrent settings discussions |
| `stealth_mam_form_crawler_v2.py` | Enhanced version of forum crawler |
| `stealth_mam_forum_crawler.py` | Advanced forum crawling with pagination |
| `stealth_audiobookshelf_crawler.py` | Searches MAM for Audiobookshelf-related content, handles pagination |
| `run_mam_crawler.py` | Entry point script that prompts for credentials |
| `check_progress.py` | Progress monitoring utility |
| `debug_mam_page.py` | Debugging utility for MAM page parsing |
| `xml_parser.py` | Robust XML parsing for apply_diff operations |
| `test_mam_crawler.py` | Unit tests for crawler functionality |

### B. Audiobook Acquisition & Download (8 files)

| File | Purpose |
|------|---------|
| `mam_audiobook_qbittorrent_downloader.py` | Downloads top 10 audiobooks from MAM Fantasy/SciFi, adds to qBittorrent |
| `stealth_audiobook_downloader.py` | Enhanced downloader with Audiobookshelf integration, human-like behavior, stealth parameters |
| `enhanced_mam_audiobook_qbittorrent.py` | Advanced qBittorrent integration with enhanced features |
| `mam_audiobook_downloader.py` | Legacy downloader implementation |
| `final_working_downloader.py` | Production-ready downloader |
| `hybrid_audiobook_downloader.py` | Combines multiple download strategies |
| `audiobook_auto_batch.py` | Automated weekly batch downloader for multiple genres |
| `audiobook_catalog_crawler.py` | Crawls external audiobook catalog site (Azure-hosted), extracts genres/timespans |

### C. Library & Metadata Scanning (11 files)

| File | Purpose |
|------|---------|
| `stealth_audiobookshelf_crawler.py` | Scans Audiobookshelf library for existing books |
| `audiobookshelf_metadata_sync.py` | Syncs Audiobookshelf metadata with Google Books, handles series linking |
| `update_audiobooks_metadata.py` | Batch metadata update utility |
| `book_metadata_gatherer.py` | Gathers metadata from multiple sources |
| `audiobook_metadata_extractor.py` | Extracts metadata from parsed content |
| `audiobook_metadata_corrector.py` | Corrects malformed metadata |
| `metadata_enrichment_service.py` | Service layer for metadata enrichment with confidence scoring |
| `unified_metadata_aggregator.py` | Aggregates metadata from multiple providers, applies weighting |
| `goodreads_api_client.py` | Goodreads API integration |
| `goodreads_abs_scraper.py` | Scrapes Goodreads for audiobook data |
| `dual_goodreads_scraper.py` | Dual scraping mode for Goodreads |

### D. Series & Author Management (13 files)

| File | Purpose |
|------|---------|
| `populate_book_series.py` | Populates series information in database |
| `populate_series_array.py` | Populates array of series data |
| `populate_abs_series_db.py` | Populates Audiobookshelf series from database |
| `populate_series_from_metadata.py` | Extracts series from metadata sources |
| `automated_series_populator.py` | Automated series population with validation |
| `simple_series_populator.py` | Simple series population utility |
| `correct_series_populator.py` | Corrects series data using fuzzy matching |
| `unified_series_populator.py` | Unified series population from all sources |
| `fix_series_from_subtitles.py` | Extracts series from subtitle fields |
| `fix_series_sequence_from_title.py` | Parses series sequence from book titles |
| `cleanup_subtitle_fields.py` | Cleans up subtitle/series field pollution |
| `create_abs_series.py` | Creates series in Audiobookshelf |
| `verify_series_metadata.py` | Validates series metadata correctness |

### E. Fuzzy Matching & Correction (6 files)

| File | Purpose |
|------|---------|
| `simple_fuzzy_corrector.py` | Basic fuzzy matching for book/series names |
| `auto_fuzzy_corrector.py` | Automatic fuzzy correction engine |
| `search_validated_corrector.py` | Fuzzy correction with search validation |
| `direct_audio_corrector.py` | Direct audio-specific corrections |
| `audiobook_query.py` | Query interface with fuzzy search |
| `local_search.py` | Local database search with fuzzy matching |

### F. VIP Status & Points Management (2 files)

| File | Purpose |
|------|---------|
| `vip_status_manager.py` | VIP status maintenance, renewal, bonus point allocation |
| `test_vip_integration.py` | VIP integration tests |

### G. Database & Metadata Tracking (6 files)

| File | Purpose |
|------|---------|
| `database.py` | SQLite CRUD operations for RAG system (files, chunks) |
| `database_schema.sql` | PostgreSQL schema for audiobook automation (books, series, authors, downloads, tasks, failures) |
| `clean_malformed_metadata.py` | Cleans corrupt metadata records |
| `fix_db_and_populate_series.py` | Database repair and series population |
| `fix_metadata_placement.py` | Fixes metadata field placement issues |
| `update_from_verification.py` | Updates database from verification results |

### H. Automation & Scheduling (10 files)

| File | Purpose |
|------|---------|
| `full_automation.py` | Full end-to-end automation workflow |
| `safe_automation.py` | Safety-checked automation |
| `minimal_automation.py` | Minimal automated workflow |
| `automated_dual_scrape.py` | Dual scraping automation |
| `run_series_automation.py` | Series-focused automation runner |
| `master_audiobook_manager.py` | Master controller for all audiobook operations |
| `audiobook_auto_batch.py` | Batch automation for weekly downloads |
| `audiobook_catalog_test_runner.py` | Test runner for catalog operations |
| `e2e_test_framework.py` | End-to-end testing framework |
| `just_populate.py` | Simple population runner |

### I. Verification & Validation (8 files)

| File | Purpose |
|------|---------|
| `audiobook_audio_verifier.py` | Verifies audio file quality/integrity |
| `verify_implementation.py` | Verifies implementation completeness |
| `verify_series_metadata.py` | Validates series metadata |
| `verify_all_uncertain_books.py` | Verifies uncertain/unmatched books |
| `test_single_book_verification.py` | Single book verification test |
| `verify_option_b.py` | Specific option validation |
| `validate_mam_compliance.py` | Validates MAM ToS compliance |
| `validate_qbittorrent_config.py` | Validates qBittorrent configuration |

### J. Testing & Diagnostics (15 files)

| File | Purpose |
|------|---------|
| `test_filter_validation.py` | Tests genre/filter validation |
| `test_abs_integration.py` | Audiobookshelf integration tests |
| `test_actual_ips.py` | IP-based tests |
| `test_qb_connection.py` | qBittorrent connection tests |
| `test_master_manager.py` | Master manager tests |
| `phase6_integration_tests.py` | Phase 6 comprehensive integration tests |
| `diagnostic_abs.py` | Audiobookshelf diagnostics |
| `comprehensive_debug.py` | Comprehensive debugging utility |
| `simple_debug.py` | Simple debugging utility |
| `simple_proxy_test.py` | Proxy configuration tests |
| `prepare_audio_verification.py` | Preparation for audio verification |
| `check_vpn_connection.py` | VPN connectivity diagnostics |
| `vpn_proxy_diagnostic.py` | VPN and proxy diagnostics |
| `verify_wireguard.py` | WireGuard VPN verification |
| `protonvpn_diagnostic.py` | ProtonVPN-specific diagnostics |

### K. RAG System (Original - 3 files)

| File | Purpose |
|------|---------|
| `ingest.py` | RAG indexing pipeline (FAISS + SQLite) |
| `ingest_all.py` | Batch RAG ingestion |
| `cli.py` | RAG query interface with Claude API |
| `watcher.py` | File system monitor for auto-reindexing |

### L. Backend API & Services (45+ files in /backend)

**Backend Structure:**
```
backend/
├── main.py                           # FastAPI application entry point
├── config.py                         # Configuration management (Pydantic settings)
├── database.py                       # Database models and initialization
├── models/                           # SQLAlchemy ORM models
│   ├── book.py
│   ├── download.py
│   ├── series.py
│   ├── author.py
│   ├── task.py
│   └── ...
├── services/                         # Business logic layer
│   ├── book_service.py               # Book CRUD and operations
│   ├── download_service.py           # Download queue management
│   ├── series_service.py             # Series completion tracking
│   ├── author_service.py             # Author statistics
│   ├── metadata_service.py           # Metadata enrichment
│   ├── task_service.py               # Task scheduling
│   └── failed_attempt_service.py     # Failure tracking
├── routes/                           # API endpoints
│   ├── books.py                      # Book endpoints
│   ├── downloads.py                  # Download endpoints
│   ├── series.py                     # Series endpoints
│   ├── authors.py                    # Author endpoints
│   ├── metadata.py                   # Metadata endpoints
│   ├── scheduler.py                  # Scheduler endpoints
│   └── system.py                     # System health endpoints
├── integrations/                     # External service clients
│   ├── abs_client.py                 # Audiobookshelf API client
│   ├── qbittorrent_client.py         # qBittorrent API client
│   ├── google_books_client.py        # Google Books API
│   └── prowlarr_client.py            # Prowlarr integration
└── utils/                            # Utility functions
    ├── logging.py
    ├── schemas.py
    └── ...
```

### M. Miscellaneous Utilities (5 files)

| File | Purpose |
|------|---------|
| `api_series_populator.py` | Series population via API |
| `setup_audiobook_crawler.py` | Setup utility for crawler |
| `scrape_guides.py` | Guide scraping utility |
| `run_dual_scraper.py` | Dual scraper runner |
| `prepare_audio_verification.py` | Audio verification preparation |

---

## PART 2: DOWNLOAD/ACQUISITION PIPELINE

### Current Capabilities

The system supports multiple acquisition sources:

#### 1. **MAM Torrent Downloads**
- **Direct Search:** `stealth_audiobook_downloader.py` searches MAM for Fantasy/SciFi audiobooks
- **Batch Downloads:** `audiobook_auto_batch.py` downloads top N results per genre
- **Manual Specification:** Can queue specific torrent titles via database

**Implementation Details:**
- Uses `AsyncWebCrawler` from Crawl4AI for stealth browsing
- Login via `/takelogin.php` with username/password (env vars)
- Searches via `/tor/browse.php` with category filters (41=Fantasy, 47=SciFi)
- Extracts magnet links from search results
- Rate limiting: 10-30 second delays between requests

#### 2. **qBittorrent Integration**
- **Client Library:** `backend/integrations/qbittorrent_client.py`
- **Direct API:** Uses qBittorrent Web API v2
- **Connection Details:**
  - Host: `QB_HOST` (default: 192.168.0.48)
  - Port: `QB_PORT` (default: 52095)
  - Authentication: username/password via env vars
- **Operations:**
  - Add torrents via magnet link or torrent file
  - Monitor torrent status
  - Set category/tags
  - Track download progress

#### 3. **Google Books API**
- **Key Components:**
  - `google_books_client.py` in backend
  - `unified_metadata_aggregator.py` for multi-provider aggregation
- **Capabilities:**
  - ISBN-based book lookup
  - Series detection
  - Author matching
  - Cover image retrieval
- **Rate Limiting:** Default 100 requests/day

#### 4. **Goodreads Integration**
- **Components:**
  - `goodreads_api_client.py`
  - `goodreads_abs_scraper.py`
  - `dual_goodreads_scraper.py`
- **Capabilities:**
  - Series completion detection
  - Author discography
  - Book rating/popularity data
  - Can scrape via web or API

#### 5. **External Catalog Sources**
- **Audiobook Catalog Crawler:** Queries `mango-mushroom-0d3dde80f.azurestaticapps.net/`
- **Multiple Providers:** Hardcover, Lubimyczytac, Audioteka (local mock services available)

### Download Queue Management

**Database Storage:**
```sql
CREATE TABLE downloads (
    id SERIAL PRIMARY KEY,
    book_id INT REFERENCES books(id),
    missing_book_id INT REFERENCES missing_books(id),
    
    source VARCHAR(100),           -- MAM, GoogleBooks, Goodreads, Manual
    magnet_link TEXT,
    torrent_url TEXT,
    
    qbittorrent_hash VARCHAR(255),
    qbittorrent_status VARCHAR(100),
    
    status VARCHAR(100),           -- queued, downloading, completed, failed
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    last_attempt TIMESTAMP,
    next_retry TIMESTAMP,
    
    abs_import_status VARCHAR(100),  -- pending, imported, import_failed
    date_queued TIMESTAMP,
    date_completed TIMESTAMP
);
```

**Download Service:**
- `backend/services/download_service.py`
- **Operations:**
  - Create download records
  - Track qBittorrent hash mapping
  - Implement retry logic (exponential backoff)
  - Monitor completion and import status
  - Handle failed downloads

### Automation Workflows

**Full Automation Pipeline:**
1. Scan Audiobookshelf library → get existing books
2. Identify series/author gaps via Goodreads
3. Queue missing books for download
4. Search MAM for torrents
5. Add to qBittorrent queue
6. Monitor downloads
7. Import into Audiobookshelf when complete
8. Update metadata

**Weekly Batch Process:**
- Triggered via scheduler (TASK_TOP10_TIME in config)
- Fetches top 10 audiobooks per whitelisted genre
- Filters test/dummy entries
- Adds to qBittorrent
- Logs results

---

## PART 3: LIBRARY SCANNING FUNCTIONALITY

### Audiobookshelf Integration

**Client Implementation:** `backend/integrations/abs_client.py`
- Async context manager pattern
- Authentication via Bearer token
- Retry logic with exponential backoff
- Methods for:
  - Get all library items
  - Get book by ID
  - Search library
  - Update book metadata
  - Create series
  - List series

### Library Scanning Workflows

#### 1. **Full Library Scan**
**File:** `stealth_audiobookshelf_crawler.py`
- Connects to Audiobookshelf server via REST API
- Retrieves all library items (books)
- Extracts metadata: title, author, series, ISBN, ASIN
- Stores in database for analysis

#### 2. **Series Completion Analysis**
**Files:** `api_series_populator.py`, `automated_series_populator.py`
- For each book's series (identified via subtitle or metadata)
- Query Goodreads for total books in series
- Compare library count vs. expected count
- Identify missing book numbers
- **Database Storage:**
```sql
CREATE TABLE series (
    name VARCHAR(500) NOT NULL UNIQUE,
    author VARCHAR(500),
    goodreads_id VARCHAR(255),
    total_books_in_series INT,
    books_owned INT,
    books_missing INT,
    completion_percentage INT,
    last_completion_check TIMESTAMP,
    completion_status VARCHAR(100)  -- complete, partial, incomplete
);
```

#### 3. **Author Completeness Analysis**
**Files:** Search for author-related scripts in list above
- Track all authors in library
- Query external sources for total audiobooks by author
- Calculate missing count
- **Database Storage:**
```sql
CREATE TABLE authors (
    name VARCHAR(500) NOT NULL UNIQUE,
    goodreads_id VARCHAR(255),
    total_audiobooks_external INT,
    audiobooks_owned INT,
    audiobooks_missing INT,
    last_completion_check TIMESTAMP,
    completion_status VARCHAR(100)  -- complete, partial, incomplete
);
```

#### 4. **Missing Books Identification**
**Key Table:**
```sql
CREATE TABLE missing_books (
    id SERIAL PRIMARY KEY,
    series_id INT REFERENCES series(id),
    author_id INT REFERENCES authors(id),
    
    title VARCHAR(500),
    author_name VARCHAR(500),
    series_name VARCHAR(500),
    series_number VARCHAR(50),
    
    reason_missing VARCHAR(100),  -- series_gap, author_gap
    isbn VARCHAR(50),
    asin VARCHAR(50),
    goodreads_id VARCHAR(255),
    
    identified_date TIMESTAMP,
    download_status VARCHAR(100),  -- identified, queued, downloading, completed
    priority INT  -- 1=high, 2=medium, 3=low
);
```

#### 5. **Metadata Sync**
**File:** `audiobookshelf_metadata_sync.py`
- After download completion and import to Audiobookshelf
- Query Google Books for book details
- Populate: series, author, narrator, description, genres
- Update series information in Audiobookshelf
- Handle series linking

### Library Scanning Entry Points

1. **Manual Scan:**
   ```bash
   python master_audiobook_manager.py --full-sync
   ```

2. **Series Analysis:**
   ```bash
   python master_audiobook_manager.py --missing-books
   ```

3. **Scheduled (via REST API):**
   - POST `/api/scheduler/task` with task_name="SERIES"
   - Automatically calculates gaps

---

## PART 4: METADATA SOURCES

### Integrated Metadata Providers

**Provider Hierarchy (from `unified_metadata_aggregator.py`):**

```python
PROVIDERS = {
    "google": "https://www.googleapis.com/books/v1/volumes?q={q}+inauthor:{a}",
    "goodreads": "http://localhost:5555/goodreads/search?query={q}&author={a}",
    "kindle": "http://localhost:5555/kindle/us/search?query={q}&author={a}",
    "hardcover": "https://provider.vito0912.de/hardcover/en/book",
    "lubimyczytac": "http://localhost:3000/search?query={q}&author={a}",  # Polish audiobooks
    "audioteka": "http://localhost:3001/search?query={q}&author={a}"      # Polish audiobooks
}

WEIGHTS = {
    "google": 1.0,
    "hardcover": 0.9,
    "goodreads": 0.8,
    "kindle": 0.8,
    "audioteka": 0.7,
    "lubimyczytac": 0.6
}
```

### Metadata Fields Extracted

```python
FIELDS = [
    "title",        # Book title
    "author",       # Author name
    "series",       # Series name
    "year",         # Publication year
    "isbn",         # ISBN-10/13
    "cover",        # Cover image URL
    "language",     # Language code
    "genres",       # Genre tags
    "description"   # Full description
]
```

### Fallback & Retry Logic

**Primary Provider:** Google Books (with 2 retry attempts)
**Fallback Chain:**
1. Hardcover.io
2. Goodreads
3. Kindle Store
4. Audioteka
5. Lubimyczytac

If primary fails, automatically tries fallbacks in order.

### Metadata Confidence Scoring

**From `metadata_enrichment_service.py`:**
```python
class MatchConfidence(Enum):
    HIGH = "high"          # Series + author + year match
    MEDIUM = "medium"      # 2 of 3 match
    LOW = "low"            # 1 of 3 match
    UNMATCHED = "unmatched"
```

**Enrichment Statistics Tracked:**
- Total books processed
- High/medium/low confidence matches
- Unmatched books
- Series identified
- Unique series count
- Author populations
- Narrator populations

---

## PART 5: CONFIGURATION

### Environment Variables

**Critical Settings** (from `backend/config.py`):

```ini
# API Configuration
API_TITLE=Audiobook Automation System API
API_VERSION=1.0.0
DEBUG=false

# Database
DATABASE_URL=postgresql://audiobook_user:audiobook_password@localhost:5432/audiobook_automation

# Authentication
API_KEY=your-secret-api-key-change-in-production
SECRET_KEY=your-secret-key-change-in-production

# Audiobookshelf
ABS_URL=http://localhost:13378
ABS_TOKEN=<your-abs-token>

# qBittorrent
QB_HOST=192.168.0.48
QB_PORT=52095
QB_USERNAME=TopherGutbrod
QB_PASSWORD=<your-password>

# Google Books
GOOGLE_BOOKS_API_KEY=<your-google-books-key>

# MAM Credentials
MAM_USERNAME=<your-mam-username>
MAM_PASSWORD=<your-mam-password>

# Scheduler Times (cron format)
TASK_MAM_TIME=0 2 * * *           # Daily 2:00 AM
TASK_TOP10_TIME=0 3 * * 6         # Sunday 3:00 AM
TASK_METADATA_FULL_TIME=0 4 1 * * # 1st of month 4:00 AM
```

### Configuration Files

**JSON Config Files:**
- `audiobook_auto_config.json` - Batch downloader settings (genres, top N, whitelist/blacklist)
- `catalog_cache/genres.json` - Cached genre list
- `catalog_cache/timespans.json` - Cached timespan filters

### Backend Configuration

Uses Pydantic `BaseSettings` with environment variable binding:
- `backend/config.py` - Central settings
- Supports `.env` file loading via `python-dotenv`
- Runtime settings via environment variables
- Defaults for local development

---

## PART 6: DATABASE SCHEMA

### PostgreSQL Schema (Comprehensive)

**Core Tables:**

1. **books** - All discovered/imported books
   - `abs_id` (unique) - Audiobookshelf ID
   - `title, author, series, series_number`
   - `isbn, asin, publisher, published_year, duration_minutes`
   - `metadata_completeness_percent, last_metadata_update`
   - `metadata_source` (JSONB) - tracks which provider gave which field
   - `status` - active, duplicate, archived
   - Indexes: abs_id, title, author, series, date_added

2. **series** - Series metadata and completion tracking
   - `name, author, goodreads_id, total_books_in_series`
   - `books_owned, books_missing, completion_percentage`
   - `completion_status` - complete, partial, incomplete
   - Indexes: name, goodreads_id, completion_status

3. **authors** - Author metadata and statistics
   - `name, goodreads_id, google_books_id, mam_author_id`
   - `total_audiobooks_external, audiobooks_owned, audiobooks_missing`
   - `completion_status`
   - Indexes: name, goodreads_id, last_completion_check

4. **missing_books** - Identified gaps
   - `series_id, author_id` (foreign keys)
   - `reason_missing` - series_gap or author_gap
   - `download_status` - identified, queued, downloading, completed, failed
   - `priority` - 1=high, 2=medium, 3=low
   - Indexes: series_id, author_id, download_status, identified_date

5. **downloads** - Download queue and tracking
   - `book_id, missing_book_id` (foreign keys)
   - `source` - MAM, GoogleBooks, Goodreads, Manual
   - `magnet_link, torrent_url`
   - `qbittorrent_hash, qbittorrent_status`
   - `status` - queued, downloading, completed, failed, abandoned
   - `retry_count, max_retries, last_attempt, next_retry`
   - `abs_import_status, abs_import_error`
   - Indexes: book_id, status, source, qbittorrent_hash, date_queued, next_retry

6. **tasks** - Execution history of scheduled jobs
   - `task_name` - MAM, TOP10, METADATA_FULL, METADATA_NEW, SERIES, AUTHOR
   - `scheduled_time, actual_start, actual_end, duration_seconds`
   - `status` - scheduled, running, completed, failed
   - `items_processed, items_succeeded, items_failed`
   - `log_output, error_message`
   - `metadata` (JSONB) - task-specific data
   - Indexes: task_name, status, scheduled_time, date_created

7. **failed_attempts** - PERMANENT tally (never deleted)
   - `task_name`
   - `item_id, item_name`
   - `reason, error_code, error_details`
   - `first_attempt, last_attempt, attempt_count`
   - `metadata` (JSONB)
   - Indexes: task_name, item_id, last_attempt, attempt_count

8. **metadata_corrections** - 30-day history of metadata changes
   - `book_id` (foreign key)
   - `field_name` - title, author, series, etc.
   - `old_value, new_value`
   - `source` - GoogleBooks, Goodreads, Manual, Auto-corrected
   - `reason, corrected_by, correction_date`

9. **genre_settings** - Configurable genres for weekly top-10
   - `genre_name` (unique)
   - `enabled, include_in_top10`
   - `top10_count` (per-genre override)

10. **api_logs** - Optional API request logging (30-day retention)
    - `endpoint, method, request_body, response_code, response_time_ms`
    - `user_id, ip_address`

### Views

**Useful Views:**
- `series_completion_summary` - Current series status
- `author_completion_summary` - Current author status  
- `recent_failed_downloads` - Last 30 days of failures

### Data Retention Policy

- **Active Tables:** books, series, authors, downloads, missing_books (permanent)
- **1-Month Retention:** tasks, metadata_corrections, api_logs (deleted nightly)
- **Permanent Retention:** failed_attempts (never deleted, for analytics)

---

## PART 7: INTEGRATION POINTS

### 1. **Audiobookshelf Integration**

**Client:** `backend/integrations/abs_client.py`

**Capabilities:**
- Get all library items (with pagination)
- Get book by ID
- Search library
- Update book metadata (series, author, genres, etc.)
- Create/update series
- List series
- Upload library items
- Get progress (for watching/listening)

**REST Endpoints:**
- `/api/audiobook/[id]` - Get book details
- `/api/library/[id]/items` - List library items
- `/api/series/[id]` - Get series details
- `/api/search` - Search library

### 2. **qBittorrent Integration**

**Client:** `backend/integrations/qbittorrent_client.py`

**Capabilities:**
- Login/logout
- Add torrent (magnet or file)
- Get all torrents
- Get torrent by hash
- Remove torrent
- Pause/resume/delete torrents
- Set category/tags
- Get server state/stats

**Endpoints:**
- `/api/v2/auth/login` - Authentication
- `/api/v2/torrents/add` - Add new torrent
- `/api/v2/torrents/info` - List torrents
- `/api/v2/torrents/properties` - Get torrent details

### 3. **Google Books API**

**Usage:** Search for books by title/author, extract metadata

```python
BASE_URL = "https://www.googleapis.com/books/v1"
ENDPOINT = f"{BASE_URL}/volumes?q={title}+inauthor:{author}"
```

**Response Fields:**
- volumeInfo.title
- volumeInfo.authors[]
- volumeInfo.seriesInfo
- volumeInfo.isbn
- volumeInfo.publishedDate
- volumeInfo.imageLinks
- volumeInfo.description

### 4. **Goodreads Integration**

**Options:**
- Direct API (if available)
- Web scraping via Crawl4AI
- Local mock service (for testing)

**Data Points:**
- Series membership
- Series position
- Author complete works
- Book ratings

### 5. **Prowlarr Integration** (Stub)

**File:** `backend/integrations/prowlarr_client.py`

**Purpose:** Indexer management and torrent search

**Planned Endpoints:**
- GET `/api/v1/indexer` - List indexers
- POST `/api/v1/search/immediate` - Trigger search
- GET `/api/v1/release` - Get search results

---

## PART 8: EXISTING ACQUISITION/DOWNLOAD FUNCTIONALITY

### What's Currently Implemented

✅ **Search & Torrent Discovery**
- MAM search by category (Fantasy: 41, SciFi: 47)
- Manual title search
- Browse functionality

✅ **Download Queuing**
- Database-backed download queue
- Magnet link extraction
- Torrent file handling
- Priority/ordering support

✅ **qBittorrent Automation**
- Add torrents via magnet or URL
- Category tagging
- Monitor download status
- Track completion

✅ **Library Integration**
- Audiobookshelf API integration
- Metadata updates
- Series creation
- Import completed downloads

✅ **Metadata Enrichment**
- Google Books lookup
- Goodreads integration
- Confidence scoring
- Fallback providers

✅ **Scheduling**
- APScheduler-based job scheduling
- Cron expression support
- Task persistence
- Failure tracking

### What's Partially Implemented

⚠️ **Top-10 Discovery**
- External catalog crawler exists
- Weekly batch process framework exists
- May need refinement for MAM-specific "top 10"

⚠️ **Series Completion**
- Goodreads parsing exists
- Comparison logic exists
- May need fine-tuning for accuracy

⚠️ **VIP Point Management**
- Status checker exists
- Renewal logic stubbed
- Needs real MAM scraping for stats

### What's NOT Yet Implemented

❌ **Missing Book Detection with Automatic Queuing**
- Detection logic: YES (missing_books table populated)
- Auto-queuing to download: NEEDS IMPLEMENTATION
- Gap filling engine: NEEDS IMPLEMENTATION
- **Current Status:** Architecture ready, orchestration needed

---

## ARCHITECTURE DIAGRAMS

### High-Level Data Flow

```
Audiobookshelf Library
        ↓
[Scan & Metadata Sync]
        ↓
Database: books, series, authors
        ↓
[Completion Analysis]
        ↓
Database: missing_books (identified gaps)
        ↓
[Search & Queue]
        ↓
MAM Crawler → [Search for torrent] → magnet links
        ↓
Database: downloads (queued)
        ↓
qBittorrent → [Add torrent] → monitoring
        ↓
[Track completion]
        ↓
Audiobookshelf → [Auto-import] → library updated
        ↓
[Update metadata]
        ↓
Metadata enrichment (Google Books, Goodreads)
```

### REST API Architecture

```
FastAPI Server (main.py)
├── Authentication (API Key)
├── Middleware (CORS, error handling)
├── Routes
│   ├── /api/books         [books.py]
│   ├── /api/downloads     [downloads.py]
│   ├── /api/series        [series.py]
│   ├── /api/authors       [authors.py]
│   ├── /api/metadata      [metadata.py]
│   ├── /api/scheduler     [scheduler.py]
│   └── /api/system        [system.py]
├── Services (business logic)
│   ├── BookService
│   ├── DownloadService
│   ├── SeriesService
│   ├── AuthorService
│   ├── MetadataService
│   ├── TaskService
│   └── FailedAttemptService
├── Integrations
│   ├── AudiobookshelfClient
│   ├── QBittorrentClient
│   ├── GoogleBooksClient
│   └── ProwlarrClient
└── Database
    └── PostgreSQL (SQLAlchemy ORM)
        ├── books
        ├── series
        ├── authors
        ├── downloads
        ├── tasks
        ├── failed_attempts
        └── ...
```

### Scheduler & Automation

```
APScheduler (async)
├── Jobs persisted in PostgreSQL
├── Scheduled Tasks
│   ├── TASK_MAM (daily 2 AM)        → Search/download
│   ├── TASK_TOP10 (Sun 3 AM)        → Weekly batch
│   ├── TASK_METADATA_FULL (1st 4 AM) → Full refresh
│   ├── TASK_METADATA_NEW (Sun 4:30)  → New book refresh
│   ├── TASK_SERIES (2nd 3 AM)       → Series analysis
│   └── TASK_AUTHOR (3rd 3 AM)       → Author analysis
└── Task Execution
    ├── TaskService tracks progress
    ├── FailedAttemptService logs failures
    └── Results stored in tasks table
```

---

## SUMMARY: CAPABILITIES BY SUBSYSTEM

| Subsystem | Status | Files | Key Features |
|-----------|--------|-------|--------------|
| **MAM Crawler** | ✅ Mature | 13 | Stealth browsing, rate limiting, multiple crawl types |
| **Download Pipeline** | ⚠️ Ready (needs orchestration) | 8 | MAM search, qBittorrent integration, queue management |
| **Library Scanning** | ✅ Implemented | 11 | ABS integration, series/author analysis, gap detection |
| **Metadata Enrichment** | ✅ Implemented | 11 | Multi-provider aggregation, confidence scoring, fallback logic |
| **Series/Author Mgmt** | ✅ Implemented | 13 | Population, fuzzy matching, verification |
| **VIP Management** | ⚠️ Partial | 2 | Status tracking, renewal logic (needs MAM scraping) |
| **REST API** | ✅ Complete | 45+ | Full CRUD, scheduling, monitoring |
| **Database** | ✅ Complete | 2 | PostgreSQL schema, comprehensive tracking |
| **Scheduling** | ✅ Implemented | APScheduler | Cron-based jobs, failure tracking |
| **RAG System** | ✅ Original | 3 | FAISS indexing, Claude API queries |

---

## KEY FILES FOR "LIBRARY GAP ANALYSIS & AUTOMATED ACQUISITION"

**If planning a new feature for automatic gap detection and acquisition:**

1. **Study These First:**
   - `master_audiobook_manager.py` - Orchestration pattern
   - `backend/services/download_service.py` - Queue management
   - `stealth_audiobook_downloader.py` - MAM search pattern
   - `database_schema.sql` - Data model

2. **Integration Points:**
   - `backend/routes/downloads.py` - API endpoints
   - `backend/routes/scheduler.py` - Job scheduling
   - `stealth_audiobookshelf_crawler.py` - Library scanning
   - `populated_book_series.py` - Gap detection

3. **Configuration:**
   - `backend/config.py` - Settings management
   - Environment variables (MAM_*, QB_*, ABS_*)

---

## DEPENDENCIES & REQUIREMENTS

**Critical External Services:**
- PostgreSQL (database)
- Audiobookshelf instance (library management)
- qBittorrent instance (torrent downloads)
- Google Books API (metadata)
- Goodreads (series data)

**Python Libraries (estimated):**
- FastAPI + Uvicorn
- SQLAlchemy + psycopg2
- Crawl4AI + aiohttp
- APScheduler
- Pydantic
- sentence-transformers (RAG)
- faiss-cpu (RAG)
- qbittorrentapi
- requests
- BeautifulSoup4
- python-dotenv

---

END OF ANALYSIS
