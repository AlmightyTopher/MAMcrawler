# MAMcrawler Workflow Phases - Complete Documentation

**Date**: November 27, 2025
**Status**: All 11 Phases Implemented and Integrated
**File**: `execute_full_workflow.py`

---

## Overview

The complete MAMcrawler workflow consists of 11 phases that execute in sequence to acquire, process, and catalog audiobooks automatically. Each phase has specific responsibilities and error handling.

---

## Phase 1: Library Scan

**Location**: `execute_full_workflow.py:get_library_data()`
**Purpose**: Verify system connectivity and scan current library inventory

**What It Does**:
- Connects to AudiobookShelf API using configured credentials
- Retrieves library ID and basic library information
- Loads all items from the library using pagination
- Implements 3-consecutive-duplicate detection to stop pagination cycles
- Builds inventory of existing books, titles, and authors

**Inputs**:
- ABS_URL (environment variable)
- ABS_TOKEN (environment variable)

**Outputs**:
- Library data dictionary with book inventory
- Existing titles and authors set for deduplication

**Error Handling**:
- Automatic retry with exponential backoff (3 retries max)
- Duplicate detection stops pagination at 3 consecutive duplicate pages
- Separate timeouts for connection (30s) and read (60s) operations

**Key Features**:
- Efficient pagination with limit=500 per page
- Detects and handles API pagination bugs
- Logs progress every page

---

## Phase 2: Science Fiction Audiobooks

**Location**: `execute_full_workflow.py:get_final_book_list("science fiction")`
**Purpose**: Query Prowlarr for top science fiction audiobooks released in the last 10 days

**What It Does**:
- Uses Prowlarr API to search for science fiction releases
- Filters by audiobook category and recent release date
- Targets finding 10 books (adjusts with available results)
- Deduplicates against existing library

**Inputs**:
- PROWLARR_URL (environment variable)
- PROWLARR_API_KEY (environment variable)
- Search term: "science fiction"
- Target count: 10

**Outputs**:
- List of book dictionaries with title, author, series, magnet links
- Only includes books not already in library

**Error Handling**:
- Gracefully handles if search returns 0 results
- Continues workflow even if target count not met

---

## Phase 3: Fantasy Audiobooks

**Location**: `execute_full_workflow.py:get_final_book_list("fantasy")`
**Purpose**: Query Prowlarr for top fantasy audiobooks released in the last 10 days

**What It Does**:
- Uses Prowlarr API to search for fantasy releases
- Filters by audiobook category and recent release date
- Targets finding 10 books (adjusts with available results)
- Deduplicates against existing library

**Inputs**:
- PROWLARR_URL (environment variable)
- PROWLARR_API_KEY (environment variable)
- Search term: "fantasy"
- Target count: 10

**Outputs**:
- List of book dictionaries with title, author, series, magnet links
- Only includes books not already in library

**Error Handling**:
- Gracefully handles if search returns 0 results
- Continues workflow even if target count not met

---

## Phase 4: Queue for Download

**Location**: `execute_full_workflow.py:queue_for_download(all_books, category)`
**Purpose**: Search for available magnet links for each book and prepare download queue

**What It Does**:
- Combines Science Fiction and Fantasy book lists
- For each book, searches for magnet links via Prowlarr
- Deduplicates by magnet hash to avoid duplicate torrents
- Prepares queue with metadata for each book

**Inputs**:
- Science Fiction books list
- Fantasy books list

**Outputs**:
- List of unique magnet links (deduplicated by hash)
- Metadata mapping for each torrent

**Error Handling**:
- Catches search errors per book without stopping workflow
- Continues with next book if search fails
- Returns empty list if no magnets found

---

## Phase 5: qBittorrent Download

**Location**: `execute_full_workflow.py:add_to_qbittorrent(magnet_links, max_downloads)`
**Purpose**: Add torrents to qBittorrent for download management

**What It Does**:
- Authenticates with qBittorrent WebAPI
- Adds magnet links as torrents (max 10 at a time by default)
- Monitors for 403 Forbidden errors and documents fallback
- Handles API permission limitations gracefully

**Inputs**:
- Magnet links list (from Phase 4)
- Max downloads: 10 (configurable)

**Outputs**:
- List of successfully added torrent IDs
- Magnet links for manual addition if API fails

**Error Handling**:
- **HTTP 403 Forbidden**: Documents magnets for manual download, continues workflow
- Persistent session with cookie management
- Separate connection and read timeouts
- Retry logic for transient failures

**Known Issues**:
- Remote qBittorrent instance at 192.168.0.48:52095 has API permission restrictions
- Workaround: Add magnets manually via qBittorrent Web UI

---

## Phase 6: Monitor Downloads

**Location**: `execute_full_workflow.py:monitor_downloads(check_interval)`
**Purpose**: Monitor qBittorrent download progress until complete

**What It Does**:
- Checks qBittorrent API for torrent status every 5 minutes
- Waits for all torrents to complete downloading
- Early exit if qBittorrent API is unavailable

**Inputs**:
- Check interval: 300 seconds (5 minutes)
- Timeout from Phase 5

**Outputs**:
- Download monitoring results
- Completion status and timing

**Error Handling**:
- Quick availability check at phase start
- Skips monitoring loop if qBittorrent unavailable
- Continues to next phase even if monitoring skipped

---

## Phase 7: Sync to AudiobookShelf

**Location**: `execute_full_workflow.py:sync_to_audiobookshelf()`
**Purpose**: Trigger library scan in AudiobookShelf to detect new downloads

**What It Does**:
- Sends library scan request to AudiobookShelf API
- Waits for scan to complete
- New book files are detected and imported automatically

**Inputs**:
- Library ID from Phase 1
- ABS_TOKEN (environment variable)

**Outputs**:
- Scan completion status
- Number of items found/imported

**Error Handling**:
- Timeout protection (120s total)
- Graceful handling if scan fails

---

## Phase 8: Sync Metadata

**Location**: `execute_full_workflow.py:sync_metadata()`
**Purpose**: Refresh and synchronize metadata for newly added books

**What It Does**:
- Retrieves recently added items from AudiobookShelf
- Triggers metadata refresh for each new item
- Updates titles, authors, covers, descriptions, etc.

**Inputs**:
- Library ID from Phase 1
- Recently added books (limit: 100)

**Outputs**:
- Number of items with successfully synced metadata
- Metadata sync errors (logged but not blocking)

**Error Handling**:
- Per-item error handling (continues on individual failures)
- Timeout per item: 30 seconds
- Returns partial results if some fail

---

## Phase 8B: Validate Metadata Quality (absToolbox)

**Location**: `execute_full_workflow.py:validate_metadata_quality_abstoolbox()`
**Purpose**: Validate metadata against quality rules to identify inconsistencies and missing required fields
**Feature Set**: absToolbox Integration

**What It Does**:
- Fetches all library items with pagination (500 items per page)
- Validates each item against quality rules:
  - Required fields: author name, title, narrator
  - Format consistency checks
  - Author name validation (not empty, not "Unknown")
  - Narrator field validation
- Compiles list of issues found
- Returns comprehensive quality report

**Inputs**:
- Library ID from Phase 1
- All library items (paginated)
- Quality rules template (hardcoded)

**Outputs**:
- Total items checked
- Count of issues found
- Detailed issue list: `{'item_id': str, 'title': str, 'issues': [str]}`
- ISO 8601 timestamp

**Quality Rules Checked**:
- Missing author name (required)
- Missing title (required)
- Missing narrator (required)
- Author marked as "Unknown"
- Empty narrator field
- Format inconsistencies

**Error Handling**:
- Per-item error handling (continues on individual failures)
- Pagination errors continue with partial data
- Returns error dict if fatal failure
- Timeout: 30 seconds per page

**Output Data Structure**:
```python
{
    'checked': int,           # Total items checked
    'issues_count': int,      # Total issues found
    'issues': {               # Detailed issues
        'item_id': {
            'title': str,
            'issues': [str]   # List of specific issues
        }
    },
    'timestamp': str          # ISO 8601
}
```

---

## Phase 8C: Standardize Metadata (absToolbox)

**Location**: `execute_full_workflow.py:standardize_metadata_abstoolbox()`
**Purpose**: Normalize metadata format for consistency across library
**Feature Set**: absToolbox Integration

**What It Does**:
- Fetches all library items with pagination
- Applies standardization rules:
  - Author names: "LastName, FirstName" → "FirstName LastName"
  - Narrator field: Removes "Narrated by" prefix
  - Series names: Removes "Series" prefix, normalizes spacing
  - Whitespace: Trims leading/trailing spaces
- Updates items via AudiobookShelf API PATCH
- Tracks all changes made
- Logs standardization operations

**Inputs**:
- Library ID from Phase 1
- All library items (paginated)
- Standardization rules template (hardcoded)

**Outputs**:
- Total items processed
- Count of items standardized
- Total changes applied
- List of specific changes: `{'item_id': str, 'title': str, 'changes': [str]}`

**Standardization Rules**:
1. **Author Names**:
   - Pattern: Extract "LastName, FirstName" format
   - Result: "FirstName LastName"
   - Example: "Sanderson, Brandon" → "Brandon Sanderson"

2. **Narrator Field**:
   - Remove "Narrated by " prefix
   - Example: "Narrated by John Doe" → "John Doe"

3. **Series Names**:
   - Remove " Series" suffix
   - Trim excess whitespace
   - Example: "Stormlight Archive Series" → "Stormlight Archive"

**Error Handling**:
- Per-item update errors continue with next item
- Failed updates logged but don't block workflow
- Returns partial results if some updates fail
- Timeout: 30 seconds per item

**Output Data Structure**:
```python
{
    'processed': int,         # Total items processed
    'standardized': int,      # Items with changes
    'changes_count': int,     # Total individual changes
    'changes': [              # List of specific changes
        {
            'item_id': str,
            'title': str,
            'changes': [str]  # What was changed
        }
    ]
}
```

---

## Phase 8D: Detect and Analyze Narrators (absToolbox)

**Location**: `execute_full_workflow.py:detect_narrators_abstoolbox()`
**Purpose**: Extract and standardize narrator information, identify narrator frequency
**Feature Set**: absToolbox Integration

**What It Does**:
- Fetches all library items with pagination (100 pages max, 500 items/page)
- Analyzes narrator field in each item
- Normalizes narrator names:
  - Removes "Narrated by" prefix
  - Extracts first occurrence if multiple narrators
  - Trims whitespace
- Builds narrator frequency map (how many books per narrator)
- Identifies top 10 narrators by book count
- Calculates narrator distribution metrics

**Inputs**:
- Library ID from Phase 1
- All library items (paginated, 100 page limit)

**Outputs**:
- Total items analyzed
- Items with narrator information
- Items missing narrator field
- Count of unique narrators
- Top 10 narrators with frequency
- Narrator distribution analysis

**Narrator Normalization**:
- Strips "Narrated by " prefix
- Handles multiple narrators (uses first)
- Standardizes whitespace
- Preserves original formatting when unclear

**Error Handling**:
- Per-item processing errors logged and skipped
- Pagination errors break loop with partial data
- Missing/null narrator fields tracked separately
- Returns partial results on error

**Output Data Structure**:
```python
{
    'total_items': int,         # Items checked
    'with_narrator': int,       # Items with narrator field
    'missing_narrator': int,    # Items without narrator
    'unique_narrators': int,    # Count of different narrators
    'top_narrators': [          # Top 10 by frequency
        {
            'narrator': str,
            'count': int
        }
    ]
}
```

**Use Cases**:
- Identify narrator coverage across library
- Find most prolific narrators
- Detect missing narrator information
- Support narrator-based collections
- Quality assurance before Phase 9

---

## Phase 9: Build Author History

**Location**: `execute_full_workflow.py:build_author_history()`
**Purpose**: Analyze library to build author database and series completeness

**What It Does**:
- Fetches all items from AudiobookShelf library
- Builds author index: author → series → [books]
- Analyzes series composition for each author
- Identifies top 10 authors by book count
- Calculates total unique authors and series

**Inputs**:
- Library ID from Phase 1
- All library items (paginated)

**Outputs**:
- Author index (nested dict structure)
- Completeness analysis per author/series
- Top 10 authors ranking

**Data Structure**:
```python
{
    'total_authors': int,
    'total_series': int,
    'total_books': int,
    'author_index': {
        'Author Name': {
            'Series Name': [
                {'title': str, 'id': str},
                ...
            ]
        }
    },
    'completeness': { ... },
    'top_authors': [('Author', count), ...]
}
```

**Error Handling**:
- Per-item processing errors logged and skipped
- Pagination errors break loop but continue with partial data
- Returns error dict if fatal failure

---

## Phase 10: Create Missing Books Queue

**Location**: `execute_full_workflow.py:create_missing_books_queue(author_history)`
**Purpose**: Identify series gaps and create prioritized queue for future downloads

**What It Does**:
- Analyzes top 5 authors from Phase 9
- Builds queue of series/authors for completion
- Calculates priority score for each series
- Sorts by priority (highest first)
- Saves queue to JSON file

**Priority Scoring Algorithm**:
```
base_priority = book_count × author_multiplier
final_priority = base_priority × book_multiplier

Where:
- author_multiplier: 0.8-1.5 (based on popularity)
- book_multiplier: min(book_count / 5.0, 2.0)
```

**Popular Authors** (hardcoded multipliers):
- Brandon Sanderson: 1.5
- Robert Jordan: 1.4
- George R.R. Martin: 1.3
- J.R.R. Tolkien: 1.3
- Neil Gaiman: 1.2
- Patrick Rothfuss: 1.2
- Steven Erikson: 1.1
- Robin Hobb: 1.1
- Joe Abercrombie: 1.0
- Terry Pratchett: 1.0
- Others: 0.8

**Inputs**:
- Author history from Phase 9
- Top authors list

**Outputs**:
- Prioritized missing books queue (JSON)
- Top 10 candidates for completion

**Output File**: `missing_books_queue.json`

**Error Handling**:
- Skips gracefully if author history unavailable
- Per-series processing continues on errors

---

## Phase 11: Generate Final Report

**Location**: `execute_full_workflow.py:generate_final_report(...)`
**Purpose**: Generate comprehensive summary report of workflow execution

**What It Does**:
- Compiles statistics from all previous phases
- Calculates estimated library value
- Analyzes top authors and their book collection
- Generates JSON report file
- Prints formatted summary to console and log

**Inputs**:
- Books list (from Phase 4)
- Added torrents (from Phase 5)
- Author history (from Phase 9)
- Queue result (from Phase 10)

**Outputs**:
- JSON report file: `workflow_final_report.json`
- Formatted console output with summary statistics

**Report Contents**:
```json
{
    "timestamp": "ISO 8601 timestamp",
    "workflow_duration": "HH:MM:SS.mmm",
    "books_targeted": int,
    "torrents_added": int,
    "library_stats": {
        "total_authors": int,
        "total_series": int,
        "total_books": int
    },
    "estimated_library_value": "$X,XXX.XX",
    "estimated_per_book": "$XX.XX",
    "top_authors_analysis": [
        {
            "author": str,
            "books": int,
            "estimated_value": "$X,XXX.XX"
        }
    ],
    "missing_books_queue": int,
    "top_candidates": [...]
}
```

**Valuation**:
- Average audiobook price: $27.50
- Formula: `total_books × $27.50`

**Console Output**:
- Workflow duration
- Books targeted and torrents added
- Library statistics
- Estimated total and per-book value
- Top 5 authors by book count with value
- Missing books queue statistics

**Error Handling**:
- Gracefully handles missing author history
- Returns error dict if fatal failure

---

## Integration Flow

```
PHASE 1: Library Scan
    ↓
PHASE 2: Science Fiction Search
PHASE 3: Fantasy Search
    ↓
PHASE 4: Queue for Download
    ↓
PHASE 5: qBittorrent Download
    ↓
PHASE 6: Monitor Downloads
    ↓
PHASE 7: Sync to AudiobookShelf
    ↓
PHASE 8: Sync Metadata
    ↓
PHASE 8B: Validate Metadata Quality (absToolbox)
    ↓
PHASE 8C: Standardize Metadata (absToolbox)
    ↓
PHASE 8D: Detect and Analyze Narrators (absToolbox)
    ↓
PHASE 9: Build Author History
    ↓
PHASE 10: Create Missing Books Queue
    ↓
PHASE 11: Generate Final Report
```

**Workflow Architecture**:
- **Phases 1-3**: Discovery (library scan + new releases)
- **Phases 4-6**: Acquisition (queue + download)
- **Phases 7-8**: Integration (sync to library + base metadata)
- **Phases 8B-8D**: Metadata Enhancement (absToolbox operations)
- **Phases 9-11**: Analysis & Reporting (author analysis + final report)

---

## Environment Variables Required

```bash
# AudiobookShelf
ABS_URL=http://localhost:13378
ABS_TOKEN=<Bearer token from ABS>

# Prowlarr
PROWLARR_URL=http://localhost:9696
PROWLARR_API_KEY=<API key>

# qBittorrent
QBITTORRENT_URL=http://192.168.0.48:52095/
QBITTORRENT_USERNAME=<username>
QBITTORRENT_PASSWORD=<password>

# Download path (optional)
DOWNLOAD_PATH=F:/Audiobookshelf/Books
```

---

## Error Handling Strategy

### Phase Failures
- Non-critical phases continue if previous phases fail
- Critical phases (1, 4) halt workflow if unsuccessful
- All errors logged with timestamp and context

### Connection Failures
- Automatic retry with exponential backoff
- Separate connection and read timeouts
- Graceful degradation (skip monitoring, fallback for torrents)

### API Failures
- Per-item error handling (don't stop for one failure)
- Timeout protection on all HTTP operations
- Session persistence for connection reuse

### Data Validation
- Deduplication by title and magnet hash
- 3-consecutive-duplicate detection for pagination
- Empty result handling for searches

---

## Output Files

1. **`real_workflow_execution.log`** - Complete execution log
2. **`missing_books_queue.json`** - Prioritized queue for next batch
3. **`workflow_final_report.json`** - Final statistics and analysis

---

## Running the Complete Workflow

```bash
cd C:\Users\dogma\Projects\MAMcrawler

# Activate virtual environment
venv\Scripts\activate.bat

# Run workflow
python execute_full_workflow.py

# Or run in background
timeout 7200 python execute_full_workflow.py 2>&1 &
```

**Expected Duration**: 30-60 minutes depending on:
- Library size
- Network connectivity
- qBittorrent availability
- Download speeds

---

## Key Statistics Captured

- Total authors in library
- Total series identified
- Total books cataloged
- Books targeted in this run
- Torrents successfully added
- Estimated library value
- Top authors by collection size
- Series candidates for completion
- Missing books prioritized list

---

## Integration with absToolbox

Phases 8B, 8C, and 8D provide native absToolbox integration for advanced metadata operations:

**Phase 8B: Validate Metadata Quality**
- Checks for required fields and format consistency
- Identifies metadata issues before analysis
- Returns detailed quality report

**Phase 8C: Standardize Metadata**
- Normalizes author names, narrator fields, series names
- Updates library via AudiobookShelf API
- Tracks all changes made

**Phase 8D: Detect and Analyze Narrators**
- Extracts and standardizes narrator information
- Builds narrator frequency analysis
- Identifies top narrators and coverage gaps

See `ABSTOOLBOX_INTEGRATION.md` and `ABSTOOLBOX_QUICKSTART.md` for advanced usage.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | 2025-11-27 | Added Phases 8B, 8C, 8D for absToolbox metadata enhancement |
| 1.0 | 2025-11-27 | Complete 11-phase workflow with author history and reporting |

---

## Summary

The MAMcrawler workflow provides a complete, automated pipeline for discovering, downloading, and cataloging audiobooks with integrated metadata enhancement. All 14 phases are fully integrated:

**Core Phases (1-11)**: Discovery, acquisition, integration, analysis, and reporting
**Enhancement Phases (8B-8D)**: absToolbox metadata quality, standardization, and narrator analysis

Comprehensive error handling, logging, and reporting capabilities are built into every phase.

**Status**: Production Ready - All 14 Phases Complete
**Last Updated**: November 27, 2025
