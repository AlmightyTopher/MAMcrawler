# Database Documentation

**Database:** PostgreSQL
**Schema Version:** 1.0
**Created:** 2025-11-16

---

## Table of Contents

1. [Overview](#overview)
2. [Entity Relationship Diagram](#entity-relationship-diagram)
3. [Table Descriptions](#table-descriptions)
4. [Data Retention Policy](#data-retention-policy)
5. [Key Queries](#key-queries)
6. [Performance Considerations](#performance-considerations)

---

## Overview

The audiobook automation system uses a PostgreSQL database to:
- **Track all books** in Audiobookshelf library with metadata completeness
- **Monitor series completion** (missing books per series)
- **Monitor author completion** (missing audiobooks per author)
- **Queue downloads** with retry logic and source tracking
- **Log all tasks** (scheduled jobs, execution history, success/failure rates)
- **Maintain permanent failure tally** for analytics
- **Store metadata corrections** with source attribution

### Key Design Principles

- **1-month active history**: Tasks, metadata corrections, API logs deleted after 30 days
- **Permanent failure tally**: `failed_attempts` table never deleted (for analytics)
- **Metadata source tracking**: Each metadata field knows its source (GoogleBooks, Goodreads, Manual)
- **Retry logic**: Failed downloads automatically scheduled for retry with backoff
- **Multi-user ready**: `api_logs` and downloads include user_id for future expansion

---

## Entity Relationship Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                          CORE ENTITIES                               │
└──────────────────────────────────────────────────────────────────────┘

                               ┌─────────────┐
                               │   books     │
                               │─────────────│
                               │ id (PK)     │
                               │ abs_id      │◄─── Audiobookshelf ID
                               │ title       │
                               │ author      │
                               │ series      │
                               │ metadata... │
                               └──────┬──────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
           ┌────────▼────────┐ ┌──────▼──────┐ ┌──────▼────────┐
           │  missing_books  │ │  downloads  │ │ metadata_      │
           │─────────────────│ │─────────────│ │ corrections    │
           │ id (PK)         │ │ id (PK)     │ │─────────────────│
           │ book_id (FK)    │ │ book_id(FK) │ │ id (PK)        │
           │ series_id (FK)  │ │ status      │ │ book_id (FK)   │
           │ author_id (FK)  │ │ source      │ │ field_name     │
           │ reason_missing  │ │ retry_count │ │ old_value      │
           │ download_id(FK) │ │ qbt_hash    │ │ new_value      │
           └────────┬────────┘ │ abs_status  │ │ source         │
                    │          └─────────────┘ └────────────────┘
                    │
     ┌──────────────┴──────────────┐
     │                             │
┌────▼────────┐           ┌───────▼──────┐
│   series    │           │    authors   │
│─────────────│           │──────────────│
│ id (PK)     │           │ id (PK)      │
│ name        │           │ name         │
│ author      │           │ goodreads_id │
│ books_owned │           │ books_owned  │
│ books_miss. │           │ books_miss.  │
└─────────────┘           └──────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                      OPERATIONAL ENTITIES                            │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────┐         ┌─────────────────┐      ┌──────────────────┐
│    tasks     │         │ failed_attempts │      │   genre_settings │
│──────────────│         │─────────────────│      │──────────────────│
│ id (PK)      │         │ id (PK)         │      │ id (PK)          │
│ task_name    │         │ task_name       │      │ genre_name       │
│ status       │         │ item_id         │      │ enabled          │
│ start_time   │         │ reason          │      │ include_in_top10 │
│ end_time     │         │ attempt_count   │      │ last_top10_run   │
│ items_proc.  │         │ created_at      │      └──────────────────┘
└──────────────┘         └─────────────────┘

┌──────────────────────────────┐
│       api_logs               │
│──────────────────────────────│
│ id (PK)                      │
│ endpoint                     │
│ method                       │
│ response_code                │
│ user_id (future multi-user)  │
└──────────────────────────────┘
```

---

## Table Descriptions

### **1. books**

Stores all discovered and imported books with metadata completeness tracking.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| abs_id | VARCHAR | Audiobookshelf internal ID (UNIQUE) |
| title | VARCHAR | Book title |
| author | VARCHAR | Author name |
| series | VARCHAR | Series name |
| series_number | VARCHAR | Position in series (e.g., "3", "3.5") |
| isbn | VARCHAR | ISBN code |
| asin | VARCHAR | Amazon ASIN |
| publisher | VARCHAR | Publisher name |
| published_year | INT | Year published |
| duration_minutes | INT | Audiobook duration in minutes |
| description | TEXT | Book description |
| metadata_completeness_percent | INT | Percentage of metadata fields filled (0-100) |
| last_metadata_update | TIMESTAMP | When metadata was last updated |
| metadata_source | JSONB | Field → source mapping: `{"title": "GoogleBooks", "author": "Goodreads"}` |
| date_added | TIMESTAMP | When book was added to library |
| date_updated | TIMESTAMP | Last update timestamp |
| import_source | VARCHAR | How book was added: user_import, mam_scraper, series_completion, author_discovery |
| status | VARCHAR | active, duplicate, archived |

**Indexes:**
- `idx_abs_id`: Fast lookup by Audiobookshelf ID
- `idx_title`: Search by title
- `idx_author`: Search by author
- `idx_series`: Filter by series
- `idx_date_added`: Timeline queries

---

### **2. series**

Tracks all series in the library and monitors completion status.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| name | VARCHAR | Series name (UNIQUE) |
| author | VARCHAR | Series author |
| goodreads_id | VARCHAR | Goodreads series ID for lookups |
| total_books_in_series | INT | Total books in series (from Goodreads) |
| books_owned | INT | How many books we have |
| books_missing | INT | How many books are missing |
| completion_percentage | INT | Calculated: owned/total * 100 |
| last_completion_check | TIMESTAMP | When we last scanned for missing books |
| completion_status | VARCHAR | complete, partial, incomplete |
| date_created | TIMESTAMP | When series was discovered |
| date_updated | TIMESTAMP | Last update |

**Indexes:**
- `idx_name`: Search by series name
- `idx_goodreads_id`: Lookup by Goodreads ID
- `idx_completion_status`: Filter by completion status

---

### **3. authors**

Tracks all authors in the library and monitors external audiobook discovery.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| name | VARCHAR | Author name (UNIQUE) |
| goodreads_id | VARCHAR | Goodreads author ID |
| google_books_id | VARCHAR | Google Books author ID |
| mam_author_id | VARCHAR | MAM author ID |
| total_audiobooks_external | INT | All audiobooks found in external sources |
| audiobooks_owned | INT | How many we have in library |
| audiobooks_missing | INT | How many are missing |
| last_completion_check | TIMESTAMP | When we last scanned for missing audiobooks |
| completion_status | VARCHAR | complete, partial, incomplete |
| date_created | TIMESTAMP | When author was discovered |
| date_updated | TIMESTAMP | Last update |

**Indexes:**
- `idx_name`: Search by author name
- `idx_goodreads_id`: Lookup by Goodreads ID
- `idx_last_check`: Filter by recent checks

---

### **4. missing_books**

Identifies gaps in series/author completeness that should be downloaded.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| book_id | INT | Reference to books (FK) - NULL if not yet imported |
| series_id | INT | Which series it belongs to (FK) |
| author_id | INT | Which author it's by (FK) |
| title | VARCHAR | Book title |
| author_name | VARCHAR | Author name |
| series_name | VARCHAR | Series name |
| series_number | VARCHAR | Position in series |
| reason_missing | VARCHAR | series_gap or author_gap |
| isbn | VARCHAR | ISBN for searching |
| asin | VARCHAR | ASIN for searching |
| goodreads_id | VARCHAR | Goodreads ID for searching |
| identified_date | TIMESTAMP | When we discovered it was missing |
| download_status | VARCHAR | identified, queued, downloading, completed, failed |
| download_id | INT | Reference to downloads table (FK) |
| priority | INT | 1 = high, 2 = medium, 3 = low |

**Indexes:**
- `idx_series_id`: Find missing by series
- `idx_author_id`: Find missing by author
- `idx_download_status`: Find books that need downloading
- `idx_identified_date`: Timeline queries

---

### **5. downloads**

Tracks all download attempts with retry logic and qBittorrent integration.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| book_id | INT | Reference to books (FK) - only if already imported |
| missing_book_id | INT | Reference to missing_books (FK) |
| title | VARCHAR | Book title |
| author | VARCHAR | Author name |
| source | VARCHAR | MAM, GoogleBooks, Goodreads, Manual |
| magnet_link | TEXT | Magnet URI for torrent |
| torrent_url | TEXT | Direct torrent URL |
| qbittorrent_hash | VARCHAR | qBittorrent info hash |
| qbittorrent_status | VARCHAR | downloading, seeding, completed |
| status | VARCHAR | queued, downloading, completed, failed, abandoned |
| retry_count | INT | How many times we've retried |
| max_retries | INT | Maximum retry attempts (default: 3) |
| last_attempt | TIMESTAMP | When we last tried to download |
| next_retry | TIMESTAMP | When we'll retry next |
| abs_import_status | VARCHAR | pending, imported, import_failed |
| abs_import_error | TEXT | Error message if import failed |
| date_queued | TIMESTAMP | When download was queued |
| date_completed | TIMESTAMP | When download completed |

**Indexes:**
- `idx_book_id`: Find downloads by book
- `idx_status`: Find downloads needing attention
- `idx_source`: Filter by download source
- `idx_qbittorrent_hash`: Lookup by qBT hash
- `idx_next_retry`: Scheduling retries

---

### **6. tasks**

Execution history of all scheduled jobs and manually triggered tasks.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| task_name | VARCHAR | MAM, TOP10, METADATA_FULL, METADATA_NEW, SERIES, AUTHOR |
| scheduled_time | TIMESTAMP | When this task was scheduled to run |
| actual_start | TIMESTAMP | When it actually started |
| actual_end | TIMESTAMP | When it finished |
| duration_seconds | INT | How long it took |
| status | VARCHAR | scheduled, running, completed, failed |
| items_processed | INT | How many items the task processed |
| items_succeeded | INT | How many succeeded |
| items_failed | INT | How many failed |
| log_output | TEXT | Full log output |
| error_message | TEXT | Error message if failed |
| metadata | JSONB | Task-specific data (e.g., which genres for TOP10) |
| date_created | TIMESTAMP | Creation time |

**Indexes:**
- `idx_task_name`: Find tasks by type
- `idx_status`: Find running/failed tasks
- `idx_scheduled_time`: Timeline of scheduled tasks
- `idx_date_created`: Historical queries

**Retention:** Delete older than 30 days

---

### **7. failed_attempts**

PERMANENT tally of all failures (never deleted) for analytics and debugging.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| task_name | VARCHAR | Which task failed (MAM, TOP10, DOWNLOAD, METADATA, etc.) |
| item_id | INT | Which book/series/author failed |
| item_name | VARCHAR | Name of what failed |
| reason | VARCHAR | Why it failed |
| error_code | VARCHAR | Error code (e.g., "HTTP_404", "NO_RESULTS") |
| error_details | TEXT | Full error traceback |
| first_attempt | TIMESTAMP | When we first tried this item |
| last_attempt | TIMESTAMP | When we last tried |
| attempt_count | INT | How many times we've tried |
| metadata | JSONB | Additional context |
| created_at | TIMESTAMP | When this record was created |

**Indexes:**
- `idx_task_name`: Analytics by task type
- `idx_item_id`: Find all failures for an item
- `idx_last_attempt`: Recent failures
- `idx_attempt_count`: Find chronic failures (many attempts)

**Retention:** PERMANENT - never deleted

---

### **8. metadata_corrections**

History of all metadata changes with source attribution.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| book_id | INT | Which book was corrected (FK) |
| field_name | VARCHAR | title, author, series, published_year, etc. |
| old_value | TEXT | Previous value |
| new_value | TEXT | New value |
| source | VARCHAR | GoogleBooks, Goodreads, Manual, Auto-corrected |
| reason | VARCHAR | Why it was changed |
| correction_date | TIMESTAMP | When correction was made |
| corrected_by | VARCHAR | Username or 'system' |

**Indexes:**
- `idx_book_id`: Find all corrections for a book
- `idx_field_name`: Find corrections by field
- `idx_source`: Find corrections by source
- `idx_correction_date`: Timeline queries

**Retention:** Delete older than 30 days

---

### **9. genre_settings**

Configurable genres for the weekly top-10 feature.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| genre_name | VARCHAR | Genre name (UNIQUE) - e.g., "Science Fiction" |
| enabled | BOOLEAN | Whether genre is active |
| include_in_top10 | BOOLEAN | Whether to include in weekly top-10 |
| last_top10_run | TIMESTAMP | When we last ran top-10 for this genre |
| top10_count | INT | How many to fetch (default: 10) |
| created_at | TIMESTAMP | When genre was added |
| updated_at | TIMESTAMP | Last update |

**Initial Data (from `.env` config):**
- Science Fiction (enabled, include_in_top10)
- Fantasy (enabled, include_in_top10)
- Mystery (enabled, include_in_top10)
- Thriller (enabled, include_in_top10)
- Romance (disabled)
- Erotica (disabled)
- Self-Help (disabled)

---

### **10. api_logs** (Optional)

Logging of all API requests for debugging and analytics.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| endpoint | VARCHAR | API endpoint called (e.g., "/api/author/search") |
| method | VARCHAR | HTTP method (GET, POST, etc.) |
| request_body | TEXT | Request payload |
| response_code | INT | HTTP response code (200, 404, 500, etc.) |
| response_time_ms | INT | How long request took (milliseconds) |
| user_id | INT | Which user made request (future multi-user support) |
| ip_address | VARCHAR | Client IP address |
| created_at | TIMESTAMP | When request was made |

**Indexes:**
- `idx_endpoint`: Find requests to specific endpoints
- `idx_created_at`: Timeline queries
- `idx_user_id`: Find requests by user

**Retention:** Delete older than 30 days

---

## Data Retention Policy

### Active History (30-day retention)

The following tables are pruned monthly:

```sql
-- Delete tasks older than 30 days
DELETE FROM tasks WHERE date_created < CURRENT_TIMESTAMP - INTERVAL '30 days';

-- Delete metadata corrections older than 30 days
DELETE FROM metadata_corrections WHERE correction_date < CURRENT_TIMESTAMP - INTERVAL '30 days';

-- Delete API logs older than 30 days
DELETE FROM api_logs WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
```

**Implementation:** PostgreSQL CRON job (runs nightly)

### Permanent Storage

The `failed_attempts` table is NEVER pruned. It grows indefinitely and is used for:
- Analytics: Which tasks fail most often?
- Debugging: History of all failures for a specific item
- Trend analysis: Are we getting better or worse?

---

## Key Queries

### Find books with incomplete metadata

```sql
SELECT id, title, author, metadata_completeness_percent
FROM books
WHERE metadata_completeness_percent < 100
ORDER BY metadata_completeness_percent ASC;
```

### Get series completion summary

```sql
SELECT * FROM series_completion_summary
ORDER BY completion_percent ASC;
```

### Get author completion summary

```sql
SELECT * FROM author_completion_summary
ORDER BY completion_percent ASC;
```

### Find books waiting to be retried

```sql
SELECT id, title, author, source, retry_count, next_retry
FROM downloads
WHERE status = 'failed' AND next_retry <= CURRENT_TIMESTAMP
ORDER BY next_retry ASC
LIMIT 10;
```

### Get recent task execution history

```sql
SELECT task_name, status, scheduled_time, actual_start, duration_seconds, items_processed
FROM tasks
WHERE date_created > CURRENT_TIMESTAMP - INTERVAL '7 days'
ORDER BY date_created DESC;
```

### Find chronic failures (items that failed many times)

```sql
SELECT item_name, task_name, attempt_count, last_attempt
FROM failed_attempts
WHERE attempt_count > 5
ORDER BY attempt_count DESC;
```

---

## Performance Considerations

### Index Strategy

All tables include strategic indexes on:
- **Foreign keys** for fast joins
- **Status columns** for filtering (needed for task scheduling)
- **Timestamps** for timeline queries
- **Search columns** (name, title, author) for user searches

### Query Optimization

- Use `SELECT` specific columns, not `SELECT *`
- Join on indexed foreign keys
- Use `WHERE` clause to filter before joining
- Consider pagination for large result sets

### Capacity Planning

Expected data growth (per month):
- **books**: ~500 new (7,500 after 15 months)
- **series**: ~100 new (1,500 after 15 months)
- **authors**: ~50 new (750 after 15 months)
- **downloads**: ~2,000 new (30,000 after 15 months)
- **tasks**: ~180 scheduled + manual (2,700 after 15 months)
- **failed_attempts**: ~50-100 new per month (grows indefinitely)

### Backup Strategy

- Daily backups recommended
- Monthly export of `failed_attempts` table for analytics
- Test restore procedures monthly

---

## Views

### series_completion_summary

Shows all series with completion status:
- Series name, books owned/missing, completion percentage
- Useful for UI showing "which series should I complete?"

### author_completion_summary

Shows all authors with audiobook discovery status:
- Author name, audiobooks owned/missing, completion percentage
- Useful for UI showing "which authors have I read all of?"

### recent_failed_downloads

Shows recent failures in the past 30 days:
- Books that failed to download
- Retry count and when next retry is scheduled
- Useful for debugging and showing users "what went wrong?"

---

## Future Enhancements

- Add `user_id` to all tables for multi-user support
- Add `tags` table for user-defined book tagging
- Add `ratings` table for user book ratings
- Add `reading_progress` table to track audiobook progress
- Add `recommendations` table to suggest new books

---

**Version History:**
- 1.0: Initial schema (2025-11-16)
