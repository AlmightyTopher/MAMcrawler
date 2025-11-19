# MAMcrawler Codebase - Quick Reference

## What You're Working With

This is a **production-grade audiobook automation system**, far more sophisticated than the CLAUDE.md documentation suggests.

**Scale:** 107+ Python files (root) + 45+ backend service files  
**Database:** PostgreSQL with 10+ tables + views  
**API:** FastAPI REST service with APScheduler for automation  

---

## KEY FINDINGS FOR "LIBRARY GAP ANALYSIS" FEATURE

### What Already Exists

1. **Library Scanning** ✅
   - `stealth_audiobookshelf_crawler.py` - Retrieves all books from library
   - Connection to Audiobookshelf via REST API
   - Metadata extraction (title, author, series, ISBN, etc.)

2. **Gap Detection** ✅
   - `missing_books` table tracks identified gaps
   - `series` table tracks completion % (books_owned vs total_books_in_series)
   - `authors` table tracks author completeness
   - Goodreads integration for series info
   - Files: `api_series_populator.py`, `automated_series_populator.py`

3. **Download Queue** ✅
   - `downloads` table - full queue management
   - Status tracking: queued → downloading → completed → imported
   - Retry logic with exponential backoff
   - qBittorrent integration ready

4. **MAM Search** ✅
   - `stealth_audiobook_downloader.py` - searches MAM for specific titles
   - Category filters (Fantasy: 41, SciFi: 47)
   - Magnet link extraction
   - Rate limiting: 10-30 second delays

5. **Metadata Enrichment** ✅
   - Multiple providers: Google Books, Goodreads, Kindle, Hardcover, Audioteka, Lubimyczytac
   - Confidence scoring (HIGH, MEDIUM, LOW, UNMATCHED)
   - Fallback logic if primary source fails

6. **REST API** ✅
   - Full CRUD for books, series, authors, downloads
   - `/api/books`, `/api/downloads`, `/api/series`, `/api/authors`
   - `/api/scheduler/task` for manual job triggering

### What Needs Integration

**The Gap:** Gap detection works, but missing automatic end-to-end orchestration:

1. **Library Gap Analysis Workflow** - Needs orchestration logic to:
   - Scan library
   - Calculate completion % for each series/author
   - Identify which books are missing
   - Trigger search for each missing book
   - Queue matches for download
   - Monitor download progress
   - Import to Audiobookshelf when done

2. **Automatic MAM Search** - Needs:
   - Given a missing book title + author, search MAM
   - Extract magnet link from search results
   - Handle "no results found" scenario
   - De-duplicate search results

3. **Smart Queuing** - Needs:
   - Priority system (series gaps vs author gaps)
   - Quality filters (seed count, file size checks)
   - User filtering (option to skip certain categories)
   - Duplicate detection

---

## FILE LOCATIONS BY CATEGORY

### For Library Gap Analysis

```
Core Components:
├── stealth_audiobookshelf_crawler.py      ← Library scanning
├── api_series_populator.py                ← Series analysis
├── automated_series_populator.py          ← Series population
├── book_metadata_gatherer.py              ← Metadata collection
└── master_audiobook_manager.py            ← Orchestration template

Database:
├── backend/services/book_service.py       ← Book operations
├── backend/services/download_service.py   ← Queue management
└── database_schema.sql                    ← Schema reference

Search & Acquisition:
├── stealth_audiobook_downloader.py        ← MAM search
├── audiobook_auto_batch.py                ← Batch download
└── mam_audiobook_qbittorrent_downloader.py ← Torrent handling

Metadata:
├── unified_metadata_aggregator.py         ← Multi-provider
├── audiobookshelf_metadata_sync.py        ← ABS sync
└── metadata_enrichment_service.py         ← Scoring & enrichment
```

### REST API Routes

```
backend/routes/
├── books.py           ← Book management endpoints
├── downloads.py       ← Download queue endpoints
├── series.py          ← Series endpoints
├── authors.py         ← Author endpoints
├── metadata.py        ← Metadata endpoints
└── scheduler.py       ← Job scheduling endpoints
```

---

## DATABASE SCHEMA (Essential Tables)

### For Missing Book Detection

```sql
-- Track what's in the library
books: id, abs_id, title, author, series, series_number, 
       metadata_completeness_percent, status

-- Track series data
series: id, name, author, goodreads_id, total_books_in_series,
        books_owned, books_missing, completion_percentage

-- Track author data  
authors: id, name, goodreads_id, total_audiobooks_external,
         audiobooks_owned, audiobooks_missing

-- Track identified gaps
missing_books: id, series_id, author_id, title, author_name,
               series_name, series_number, reason_missing, 
               identified_date, download_status, priority

-- Track download queue
downloads: id, book_id, missing_book_id, source, magnet_link,
           status, retry_count, qbittorrent_hash, 
           abs_import_status
```

---

## CRITICAL CONFIGURATION

### Environment Variables Needed

```bash
# MAM Credentials
MAM_USERNAME=<your-username>
MAM_PASSWORD=<your-password>

# Audiobookshelf
ABS_URL=http://localhost:13378
ABS_TOKEN=<your-token>

# qBittorrent
QB_HOST=192.168.0.48
QB_PORT=52095
QB_USERNAME=<your-user>
QB_PASSWORD=<your-password>

# Google Books (for metadata)
GOOGLE_BOOKS_API_KEY=<your-key>

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/audiobook_automation
```

### Job Scheduling (from config.py)

```python
TASK_MAM_TIME = "0 2 * * *"           # Daily 2:00 AM
TASK_TOP10_TIME = "0 3 * * 6"         # Sunday 3:00 AM
TASK_METADATA_FULL_TIME = "0 4 1 * *" # 1st of month 4:00 AM
TASK_SERIES_TIME = "0 3 2 * *"        # 2nd of month 3:00 AM
TASK_AUTHOR_TIME = "0 3 3 * *"        # 3rd of month 3:00 AM
```

---

## HOW THINGS CURRENTLY WORK

### Example: Manual Series Gap Detection

```bash
python api_series_populator.py
```

This:
1. Scans Audiobookshelf library
2. Finds all series in library
3. Queries Goodreads for total books per series
4. Populates `series` table with books_owned vs total_books_in_series
5. Identifies gaps in `missing_books` table

### Example: Manual Download Addition

```bash
# Via database:
INSERT INTO downloads (title, author, source, magnet_link, status)
VALUES ('Book Title', 'Author Name', 'MAM', 'magnet:?xt=...', 'queued')

# Or via REST API:
POST /api/downloads
{
  "title": "Book Title",
  "author": "Author Name",
  "source": "MAM",
  "magnet_link": "magnet:?xt=...",
  "status": "queued"
}
```

Then qBittorrent monitor adds it to the client.

---

## WHAT THE NEW FEATURE SHOULD DO

**Missing Book Detection & Automated Acquisition Workflow:**

```
TRIGGER (manual or scheduled)
↓
[Scan Audiobookshelf Library]
  → Get all books with series/author info
↓
[Calculate Completion]
  → FOR each series:
    - Query Goodreads for total books
    - Count library books
    - Calculate gaps
  → FOR each author:
    - Query Goodreads for total audiobooks
    - Count library books
    - Calculate gaps
↓
[Identify Missing Books]
  → Update missing_books table
  → Mark high-priority gaps
↓
[Search for Torrents]
  → FOR each missing book:
    - Search MAM with title + author
    - Evaluate results (seeds, file size, etc.)
    - Extract magnet links
↓
[Queue Downloads]
  → Create download records
  → Set priorities (series > author)
  → Skip if download already in queue
↓
[Monitor & Import]
  → Track qBittorrent status
  → Auto-import to Audiobookshelf when done
  → Update metadata from Google Books
↓
[Complete]
  → Update series/author completion %
  → Log results to tasks table
```

---

## KEY INSIGHTS

1. **The architecture is ready** - All the pieces exist, just need orchestration
2. **Metadata is multi-source** - Falls back gracefully if primary source fails
3. **Everything is tracked** - All operations logged to tasks/failed_attempts tables
4. **Scheduled jobs are flexible** - APScheduler can run any workflow at any time
5. **Data is normalized** - Foreign keys maintain integrity across all operations
6. **Confidence scoring helps** - You know which metadata is reliable
7. **Retry logic is built-in** - Downloads can be re-attempted up to max_retries times

---

## WHAT'S NOT FULLY IMPLEMENTED YET

- **Intelligent MAM search** - Works but could be smarter about quality filtering
- **Auto-gap-filling orchestration** - Detection works, auto-queue needs work
- **Duplicate detection** - Could check if download already in queue
- **User preferences** - No "skip these genres" feature yet
- **VIP point tracking** - Exists but needs real MAM scraping

---

## ENTRY POINTS FOR DEVELOPMENT

### Start Here (in order):

1. **Understand the flow:**
   - Read `/home/user/MAMcrawler/master_audiobook_manager.py` (30 min)
   - Study `/home/user/MAMcrawler/database_schema.sql` (15 min)

2. **Review existing gap detection:**
   - `/home/user/MAMcrawler/api_series_populator.py` (20 min)
   - `/home/user/MAMcrawler/automated_series_populator.py` (20 min)

3. **Review existing download pipeline:**
   - `/home/user/MAMcrawler/stealth_audiobook_downloader.py` (20 min)
   - `/home/user/MAMcrawler/backend/services/download_service.py` (15 min)

4. **Plan orchestration:**
   - New file: `audiobook_gap_analyzer.py` (main orchestrator)
   - Integrate with existing components
   - Add REST endpoint at `/api/gaps/analyze-and-acquire`

5. **Test & deploy:**
   - Manual testing first
   - Add to scheduler for automated runs

---

## FILE LOCATIONS

- **Full Analysis:** `/home/user/MAMcrawler/CODEBASE_ANALYSIS.md` (991 lines)
- **This Quick Ref:** `/home/user/MAMcrawler/CODEBASE_QUICK_REFERENCE.md`
- **Database Schema:** `/home/user/MAMcrawler/database_schema.sql`
- **CLAUDE.md:** Original project documentation (may be outdated)

