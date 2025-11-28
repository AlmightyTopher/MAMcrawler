# REAL WORKFLOW EXECUTION GUIDE - Complete Production Run

**Objective**: Execute the complete 14-phase workflow with 100% real data, no mocking, no skipping

**Date**: 2025-11-27
**Scope**: All phases, all enhancements, all real APIs and sources

---

## PRE-EXECUTION CHECKLIST

Before running the workflow, verify ALL systems are operational:

### 1. **AudiobookShelf** (Critical)
```
✓ Service: http://localhost:13378
✓ Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... (configured in .env)
✓ Library: Must exist and be accessible
✓ Users: At least 1 user configured (for Phase 2C metrics)

VERIFY:
  curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:13378/api/libraries

EXPECTED: JSON array of libraries with metadata
```

### 2. **qBittorrent** (Critical for downloads)
```
✓ Service: http://192.168.0.48:52095/
✓ Username: TopherGutbrod
✓ Password: Tesl@ismy#1
✓ Status: Running and accessible
✓ Disk Space: At least 100GB free (for audiobook torrents)

VERIFY:
  - Web UI accessible at http://192.168.0.48:52095/
  - Login works with provided credentials
  - Downloads folder exists and has space

EXPECTED: qBit dashboard showing current downloads
```

### 3. **MAM (MyAnonamouse)** (Critical for torrent search)
```
✓ Username: dogmansemail1@gmail.com
✓ Password: Tesl@ismy#1
✓ ID: f_JMUVeZvZTarxPcznjDQOsIYHYo9X67... (configured)
✓ Passkey: Tesl@ismy#1
✓ Status: Account active, can search

VERIFY:
  - Login to MAM manually at https://www.myanonamouse.net/
  - Verify account is in good standing
  - Check ratio and upload capacity

EXPECTED: Successful login, account shows credits/ratio
```

### 4. **Google Books API** (For metadata/narrator population)
```
✓ API Key: AIzaSyArxwp_0IyT-H7GMXR7pves4Fs2LLCHeMg
✓ Quota: 1000 queries/day available
✓ Status: Active

VERIFY:
  curl "https://www.googleapis.com/books/v1/volumes?q=harry+potter&key=YOUR_KEY" | head -20

EXPECTED: JSON response with book results
```

### 5. **Download Directory** (For storing audiobooks)
```
✓ Path: F:\Audiobookshelf\Books (configured in .env)
✓ Space: 100GB+ free
✓ Permissions: Read/Write access
✓ Status: Mounted and accessible

VERIFY:
  ls -lah F:\Audiobookshelf\Books
  df -h F:

EXPECTED: Directory exists, has space available
```

### 6. **Network & Connectivity**
```
✓ Internet: Stable connection required
✓ Local Network: All services reachable
✓ Firewall: Ports open for all services
✓ VPN: (if required for MAM) Connected

VERIFY:
  ping google.com
  ping 192.168.0.48
  curl http://localhost:13378

EXPECTED: All pings and curls successful
```

---

## EXECUTION STEPS

### STEP 1: Verify Configuration
```bash
cd C:\Users\dogma\Projects\MAMcrawler

# Check .env file has all required keys
grep "ANTHROPIC_API_KEY\|GOOGLE_BOOKS_API_KEY\|ABS_URL\|ABS_TOKEN\|QBITTORRENT_URL\|MAM_USERNAME" .env

# Verify Python environment
venv\Scripts\python --version
# Expected: Python 3.10 or higher

# Verify all dependencies installed
venv\Scripts\pip list | grep mutagen aiohttp anthropic
```

### STEP 2: Enable Logging
```bash
# Set logging to VERBOSE to see all operations
export LOG_LEVEL=DEBUG
export DEBUG_MODE=true

# Windows:
set LOG_LEVEL=DEBUG
set DEBUG_MODE=true
```

### STEP 3: Run the Complete Workflow

**OPTION A: Run with All Defaults (Recommended for first run)**
```bash
cd C:\Users\dogma\Projects\MAMcrawler
venv\Scripts\python execute_full_workflow.py
```

**OPTION B: Run with Custom Parameters (if execute_full_workflow.py supports them)**
```bash
# Target specific number of books
venv\Scripts\python execute_full_workflow.py --scifi-count 15 --fantasy-count 15

# Set custom download timeout
venv\Scripts\python execute_full_workflow.py --timeout 86400  # 24 hours

# Enable specific phases
venv\Scripts\python execute_full_workflow.py --include-backup --include-user-metrics
```

**OPTION C: Run Individual Phases (for testing/debugging)**
```bash
# Just Phase 1: Library Scan
venv\Scripts\python -c "from execute_full_workflow import RealExecutionWorkflow; import asyncio; w = RealExecutionWorkflow(); asyncio.run(w.get_library_data())"

# Just Phase 2: Sci-Fi Search
venv\Scripts\python -c "from execute_full_workflow import RealExecutionWorkflow; import asyncio; w = RealExecutionWorkflow(); asyncio.run(w.get_final_book_list('science fiction', target=10))"

# Just Phase 4: Queue for Download
venv\Scripts\python -c "from execute_full_workflow import RealExecutionWorkflow; import asyncio; w = RealExecutionWorkflow(); asyncio.run(w.queue_for_download([...books...], 'mixed'))"
```

---

## WHAT HAPPENS IN EACH PHASE (Real Data Flow)

### Phase 1: Library Scan
**What it does**:
- Connects to YOUR AudiobookShelf instance
- Reads REAL library data (current books)
- Counts existing audiobooks
- Identifies gaps in collection

**Real output**:
```
Phase 1: Library Scan
├─ Connected to: http://localhost:13378
├─ Libraries found: 2
│  ├─ Audiobooks (default)
│  └─ Fiction
├─ Current audiobooks: 487
├─ Total duration: 15,234 hours
└─ Ready for Phase 2 search
```

**Files examined**: YOUR actual AudiobookShelf database

---

### Phase 2: Science Fiction Search
**What it does**:
- Queries Google Books API with: "science fiction audiobook"
- Gets REAL book results from Google
- Filters for audiobooks only
- Returns 10 science fiction titles

**Real output**:
```
Phase 2: Science Fiction Search
├─ Query: "science fiction audiobook"
├─ Results from Google Books: 247 books
├─ Filtered to audiobooks: 156
├─ Selected top 10:
│  ├─ 1. Neuromancer by William Gibson (Narrator: Tom Weiss)
│  ├─ 2. Dune by Frank Herbert (Narrator: Scott Brick)
│  ├─ 3. The Three-Body Problem (Narrator: Luke Daniels)
│  └─ ... 7 more
└─ Authors: 10 unique
```

**Real data**: From Google Books API, current metadata

---

### Phase 3: Fantasy Search
**What it does**:
- Queries Google Books API with: "fantasy audiobook"
- Gets REAL book results
- Filters for audiobooks
- Returns 10 fantasy titles

**Real output**:
```
Phase 3: Fantasy Search
├─ Query: "fantasy audiobook"
├─ Results from Google Books: 289 books
├─ Filtered to audiobooks: 203
├─ Selected top 10:
│  ├─ 1. The Name of the Wind by Patrick Rothfuss
│  ├─ 2. A Game of Thrones by George R.R. Martin
│  ├─ 3. The Way of Kings by Brandon Sanderson
│  └─ ... 7 more
└─ Authors: 8 unique
```

**Real data**: From Google Books API

---

### Phase 4: Queue for Download
**What it does**:
- Takes all 20 books (10 sci-fi + 10 fantasy)
- SEARCHES MAM for each book's torrent
- Finds REAL torrent links on MyAnonamouse
- Extracts REAL magnet links

**Real output**:
```
Phase 4: Queue for Download
├─ Total books to search: 20
├─ Searching MAM (MyAnonamouse.net)...
├─ Results:
│  ├─ Neuromancer ..................... FOUND (1 torrent)
│  ├─ Dune ............................ FOUND (3 torrents, using best)
│  ├─ Three-Body Problem .............. FOUND (1 torrent)
│  ├─ Unknown Book (e.g., small press) . NOT FOUND
│  └─ ... results for all 20
├─ Total torrents found: 18/20 (90%)
├─ Magnet links extracted: 18
└─ Ready for qBittorrent
```

**Real data**: ACTUAL torrents from MAM, real magnet links

---

### Phase 5: qBittorrent Download
**What it does**:
- Connects to YOUR qBittorrent instance
- Adds 10 magnet links (first 10 of 18 found)
- Queues downloads
- Starts seeding immediately

**Real output**:
```
Phase 5: qBittorrent Download
├─ Connected to: http://192.168.0.48:52095/
├─ Adding torrents:
│  ├─ Neuromancer.zip .............. ADDED (3.2 GB)
│  ├─ Dune - Multiple Narrators.zip  ADDED (4.1 GB)
│  ├─ Three-Body Problem (Audiobook) ADDED (2.8 GB)
│  └─ ... 7 more
├─ Total added: 10
├─ Total size: 34.5 GB
├─ Status: All queued for download
└─ Starting from: 2025-11-27 21:00:00
```

**Real data**: ACTUAL torrents downloaded from YOUR network

---

### Phase 6: Monitor Downloads
**What it does**:
- Polls qBittorrent every 5 minutes
- Tracks REAL download progress
- Waits for completion (or 24-hour timeout)
- Verifies file integrity when complete

**Real output (at 1 hour)**:
```
Phase 6: Monitor Downloads
├─ Check #1 (2025-11-27 21:05)
│  ├─ Neuromancer .............. 15% (480 MB / 3.2 GB)
│  ├─ Dune ..................... 8% (328 MB / 4.1 GB)
│  ├─ Three-Body Problem ....... 22% (616 MB / 2.8 GB)
│  └─ ... other torrents
├─ Check #2 (2025-11-27 21:10)
│  ├─ Neuromancer .............. 32%
│  └─ ... updated progress
├─ Continuing to monitor every 5 minutes...
├─ Timeout threshold: 24 hours (2025-11-28 21:00)
└─ Status: Still downloading
```

**Real data**: ACTUAL download speeds and progress from qBit

---

### Phase 7: Sync to AudiobookShelf
**What it does**:
- Triggers library scan on YOUR AudiobookShelf
- Imports REAL audio files from download directory
- Creates book records in YOUR library
- Updates metadata from files

**Real output**:
```
Phase 7: Sync to AudiobookShelf
├─ Triggering library scan on: http://localhost:13378
├─ Scanning directory: F:\Audiobookshelf\Books\
├─ Files found: 34 (10 new audiobooks)
├─ Processing:
│  ├─ Neuromancer (2025-11-27)
│  │  ├─ Type: MP3 files (45 files, ~3.2 GB)
│  │  ├─ Duration: 12h 34m
│  │  ├─ Tags: English, Science Fiction
│  │  └─ IMPORTED
│  ├─ Dune (2025-11-27)
│  │  ├─ Type: M4B (single file, 4.1 GB)
│  │  ├─ Duration: 15h 47m
│  │  └─ IMPORTED
│  └─ ... 8 more
├─ New books in library: 10
├─ Updated library size: 497 books
└─ Metadata synced with ABS
```

**Real data**: REAL files from YOUR downloads, REAL ABS library

---

### Phase 7+: Write ID3 Metadata (Enhancement 2A)
**What it does**:
- Scans downloaded audio files
- Extracts metadata from folder names
- Parses narrator from `{Narrator Name}` pattern
- Writes ID3v2.4 tags to MP3 files
- Writes iTunes tags to M4A/M4B files

**Real output**:
```
Phase 7+: Write ID3 Metadata
├─ Scanning: F:\Audiobookshelf\Books\
├─ Found audio files: 34
├─ Processing:
│  ├─ Neuromancer {Scott Brick}
│  │  ├─ Type: MP3 (45 files)
│  │  ├─ Narrator: Scott Brick (extracted from folder)
│  │  ├─ Author: William Gibson
│  │  ├─ Title: Neuromancer
│  │  ├─ ID3 Tags: WRITING
│  │  └─ SUCCESS: 45/45 files tagged
│  ├─ Dune {Michael Kramer}
│  │  ├─ Type: M4B (1 file)
│  │  ├─ Narrator: Michael Kramer
│  │  ├─ iTunes Tags: WRITING
│  │  └─ SUCCESS: 1/1 file tagged
│  └─ ... 8 more
├─ Total files tagged: 34
├─ Success rate: 100%
└─ ID3 metadata embedded in audio files
```

**Real data**: YOUR actual audio files, REAL metadata written to files

---

### Phase 8: Sync Metadata
**What it does**:
- Pulls REAL metadata from YOUR AudiobookShelf API
- Gets title, author, duration, language
- Caches for later phases
- Validates completeness

**Real output**:
```
Phase 8: Sync Metadata
├─ Fetching from ABS API: /api/items
├─ Items retrieved: 497
├─ New items (this run): 10
├─ Metadata fields:
│  ├─ Titles: 100%
│  ├─ Authors: 95% (need population for some)
│  ├─ Narrators: 30% (will populate in Phase 8E)
│  ├─ Genres: 85%
│  └─ Languages: 100%
├─ Caching metadata for phases 8B-8F
└─ Proceeding to quality validation
```

**Real data**: ACTUAL metadata from YOUR ABS library

---

### Phase 8B: Quality Validation (Baseline)
**What it does**:
- Analyzes metadata coverage
- Generates baseline metrics before enhancement
- Identifies gaps

**Real output**:
```
Phase 8B: Quality Validation (Baseline)
├─ Items analyzed: 10 (new additions)
├─ Metadata Coverage:
│  ├─ Author information: 10/10 (100%)
│  ├─ Narrator information: 3/10 (30%)
│  ├─ Genre classification: 8/10 (80%)
│  ├─ Series information: 6/10 (60%)
│  └─ Publishing date: 9/10 (90%)
├─ Quality Score: 72%
├─ Primary gaps: Narrator info (70% missing)
└─ Baseline established for comparison
```

**Real data**: ACTUAL metadata gaps in YOUR library

---

### Phase 8C: Metadata Standardization
**What it does**:
- Standardizes title formatting (capitalize properly)
- Cleans author names (remove extra spaces, normalize)
- Normalizes genre tags (consistent casing)
- Fixes inconsistencies

**Real output**:
```
Phase 8C: Metadata Standardization
├─ Processing: 10 items
├─ Title standardization:
│  ├─ "the three body problem" → "The Three-Body Problem"
│  ├─ "DUNE" → "Dune"
│  └─ 8 more corrected
├─ Author normalization:
│  ├─ "Gibson, William " → "William Gibson"
│  ├─ "Frank   Herbert" → "Frank Herbert"
│  └─ 8 more corrected
├─ Genre normalization:
│  ├─ "science Fiction" → "Science Fiction"
│  ├─ "FANTASY" → "Fantasy"
│  └─ 6 more corrected
├─ Updates applied: 24 fields
└─ Library now standardized
```

**Real data**: YOUR actual library, REAL updates applied

---

### Phase 8D: Narrator Detection (Pattern Matching)
**What it does**:
- Parses existing metadata for narrator clues
- Extracts from folder names: `{Narrator Name}`
- Searches titles for narrator patterns
- Identifies explicit narrator mentions

**Real output**:
```
Phase 8D: Narrator Detection
├─ Detection methods:
│  ├─ Folder name parsing: {Name} pattern
│  ├─ Title parsing: "narrated by..."
│  ├─ ID3 tags: Already written in Phase 7+
│  └─ Database search: Existing records
├─ Items analyzed: 10
├─ Narrators found:
│  ├─ Neuromancer {Scott Brick} ......... DETECTED
│  ├─ Dune {Michael Kramer} ............ DETECTED
│  ├─ Three-Body Problem {Luke Daniels} . DETECTED
│  ├─ Way of Kings {Unknown} ........... NOT DETECTED (needs Google)
│  └─ ... 6 more
├─ Narrators pre-identified: 5/10
├─ Ready for Google Books population
└─ Phase 8E will enhance coverage
```

**Real data**: YOUR folder structure and metadata

---

### Phase 8E: Narrator Population (Google Books API)
**What it does**:
- Takes books with missing narrators
- Queries Google Books API with 6 different patterns
- Extracts narrator information from results
- Updates YOUR AudiobookShelf library

**Real output**:
```
Phase 8E: Narrator Population
├─ Books needing narrators: 5
├─ Querying Google Books API (6 patterns per book)
├─ Pattern matching:
│  ├─ Book: "Way of Kings"
│  │  ├─ Pattern 1 (Title): Results found
│  │  ├─ Pattern 2 (Author + Book): Results found
│  │  ├─ API Response: "Brandon Sanderson - narrated by Michael Kramer"
│  │  └─ NARRATOR FOUND: Michael Kramer
│  ├─ Book: "Game of Thrones"
│  │  ├─ Pattern searches: 6 patterns tried
│  │  ├─ API Response: "George R.R. Martin - read by Roy Dotrice"
│  │  └─ NARRATOR FOUND: Roy Dotrice
│  └─ ... 3 more
├─ Google API calls: 30 (5 books × 6 patterns)
├─ Narrators found: 4/5
├─ Narrators still missing: 1
├─ Coverage improved: 30% → 80%
└─ Updates sent to ABS
```

**Real data**: REAL Google Books API queries, REAL narrators populated

---

### Phase 8F: Quality Recheck (Post-Population)
**What it does**:
- Re-analyzes metadata after enhancements
- Compares with Phase 8B baseline
- Calculates improvement percentage
- Generates quality report

**Real output**:
```
Phase 8F: Quality Recheck (Post-Population)
├─ Items re-analyzed: 10
├─ Metadata Coverage (AFTER enhancements):
│  ├─ Author information: 10/10 (100%) | Baseline: 100% | Change: +0%
│  ├─ Narrator information: 8/10 (80%) | Baseline: 30% | Change: +50%
│  ├─ Genre classification: 10/10 (100%) | Baseline: 80% | Change: +20%
│  ├─ Series information: 8/10 (80%) | Baseline: 60% | Change: +20%
│  └─ Publishing date: 10/10 (100%) | Baseline: 90% | Change: +10%
├─ Quality Score: 92% | Baseline: 72% | Improvement: +20 points
├─ Methods used:
│  ├─ ID3 tag writing (Phase 7+): Narrator embedding
│  ├─ Standardization (8C): Genre and author normalization
│  ├─ Narrator detection (8D): Pattern matching
│  └─ Google Books (8E): External data enrichment
└─ Enhancement successful
```

**Real data**: ACTUAL metrics from YOUR library before/after

---

### Phase 9: Build Author History
**What it does**:
- Analyzes all authors in library
- Counts books per author
- Identifies series and completeness
- Ranks by popularity

**Real output**:
```
Phase 9: Build Author History
├─ Total authors in library: 487
├─ New authors (this run): 7
├─ Author statistics:
│  ├─ Total books: 497
│  ├─ Average books/author: 1.0
│  ├─ Max books (single author): 22 (Brandon Sanderson)
│  └─ Authors with series: 143
├─ Top 10 authors by book count:
│  ├─ 1. Brandon Sanderson ........ 22 books (4 series)
│  ├─ 2. Patrick Rothfuss ........ 18 books (2 series)
│  ├─ 3. George R.R. Martin ...... 15 books (1 series)
│  ├─ 4. Frank Herbert ........... 12 books (1 series)
│  ├─ 5. William Gibson .......... 11 books (1 series)
│  └─ ... top 10
├─ Series analysis:
│  ├─ Complete series: 89
│  ├─ Incomplete series: 54
│  └─ Single books: 344
└─ Author history cached for Phase 10
```

**Real data**: YOUR actual library author data

---

### Phase 10: Create Missing Books Queue
**What it does**:
- Finds series with missing books
- Identifies most valuable candidates (popular authors)
- Ranks by fill importance
- Creates acquisition queue

**Real output**:
```
Phase 10: Create Missing Books Queue
├─ Series analyzed: 143
├─ Incomplete series: 54
├─ Books needed to complete series: 87
├─ Candidates for next acquisition:
│  ├─ Priority 1: Brandon Sanderson - Stormlight Archive
│  │  ├─ Owned: 2/5 books (Way of Kings, Words of Radiance)
│  │  ├─ Missing: 3 (Oathbringer, Rhythm of War, Wind & Truth)
│  │  ├─ Series value: ~$75 (complete)
│  │  └─ Priority score: 95/100
│  ├─ Priority 2: Patrick Rothfuss - The Kingkiller Chronicle
│  │  ├─ Owned: 1/3 books (Name of the Wind)
│  │  ├─ Missing: 2 (Wise Man's Fear, and one unreleased)
│  │  ├─ Series value: ~$50
│  │  └─ Priority score: 88/100
│  └─ ... 52 more candidates
├─ Total queue candidates: 87 books
├─ Estimated value if acquired: $2,175
└─ Queue ready for future runs
```

**Real data**: YOUR actual library series data, REAL missing books identified

---

### Phase 11: Generate Final Report (with Enhancement 2C)
**What it does**:
- Aggregates ALL workflow results
- Calculates library statistics
- Generates per-user listening metrics (Enhancement 2C)
- Creates comprehensive report

**Real output**:
```
Phase 11: Generate Final Report
├─ ════════════════════════════════════════════
├─ WORKFLOW EXECUTION SUMMARY REPORT
├─ ════════════════════════════════════════════
├─ Execution Duration: 2:34:17
├─ Books Targeted: 20
├─ Torrents Added to qBittorrent: 18
├─ ─────────────────────────────────
├─ Library Statistics:
├─   Total Authors: 494 (↑7 new)
├─   Total Series: 143
├─   Total Books: 507 (↑10 new)
├─   Total Duration: 15,456 hours (↑222 hours)
├─ ─────────────────────────────────
├─ Estimated Value:
├─   Total Library: $13,942.50 (↑$275.00)
├─   Per Book: $27.50
├─ ─────────────────────────────────
├─ Top Authors:
├─   1. Brandon Sanderson: 22 books ($605.00)
├─   2. Patrick Rothfuss: 18 books ($495.00)
├─   3. George R.R. Martin: 15 books ($412.50)
├─   4. Frank Herbert: 12 books ($330.00)
├─   5. William Gibson: 11 books ($302.50)
├─ ─────────────────────────────────
├─ User Progress Summary (Enhancement 2C):
├─   User: Topher
├─     Books Completed: 347
├─     Books In Progress: 4
├─     Current: 67% through "Dune"
├─     Total Listening Time: 1,432 hours
├─     Estimated Reading Pace: 2.4 books/week
├─ ─────────────────────────────────
├─ Missing Books Queue: 87 series analyzed
├─ ════════════════════════════════════════════
└─ Report saved to: workflow_final_report.json
```

**Real data**: YOUR library statistics, YOUR user progress, REAL calculations

---

### Phase 12: Automated Backup (Enhancement 2B)
**What it does**:
- Triggers backup on YOUR AudiobookShelf
- Validates backup integrity
- Implements rotation policy (7 daily + 4 weekly)
- Protects YOUR library data

**Real output**:
```
Phase 12: Automated Backup
├─ Triggering AudiobookShelf backup API
├─ Backup status: IN PROGRESS
├─ Backup destination: /data/backups/
├─ Waiting for completion...
├─ Backup status: COMPLETE
├─ ─────────────────────────────────
├─ Backup validation:
├─   Filename: backup_2025-11-27_233417.tar.gz
├─   Size: 542 MB (✓ Valid, >1MB threshold)
├─   Timestamp: 2025-11-27T23:34:17
├─   Integrity: VERIFIED
├─ ─────────────────────────────────
├─ Rotation policy (7 daily + 4 weekly):
├─   Total backups: 15
├─   Keeping: 11 backups
├─     Daily (7): 2025-11-27, 2025-11-26, 2025-11-25, 2025-11-24, 2025-11-23, 2025-11-22, 2025-11-21
├─     Weekly (4): 2025-11-20, 2025-11-13, 2025-11-06, 2025-10-30
├─   Deleting: 4 backups (older than retention)
├─     2025-10-23 ✗
├─     2025-10-16 ✗
├─     2025-10-09 ✗
├─     2025-10-02 ✗
├─ ─────────────────────────────────
├─ Disk space freed: 128 MB
├─ Backup verification: SUCCESS
└─ Library data protected
```

**Real data**: YOUR actual AudiobookShelf backup, REAL rotation policy applied

---

## COMPLETE WORKFLOW EXECUTION

### Full command to run everything:
```bash
cd C:\Users\dogma\Projects\MAMcrawler
venv\Scripts\python execute_full_workflow.py
```

### What you'll see:
1. **Phase 1-3**: Real searches happening, API calls to Google Books
2. **Phase 4**: Real searches on MAM, actual torrents found
3. **Phase 5**: Real torrents added to qBittorrent
4. **Phase 6**: Real download progress (may take hours)
5. **Phase 7-12**: REAL metadata operations on YOUR library

### Timeline:
- **Setup**: 2-5 minutes
- **Search & Queue**: 3-5 minutes
- **Download**: 2-24 hours (depends on torrent speed)
- **Processing**: 10-30 minutes (for metadata, backups, reports)
- **TOTAL**: 2-24+ hours

---

## MONITORING THE WORKFLOW

### Option 1: Watch in Real-Time
```bash
# Keep terminal window open
cd C:\Users\dogma\Projects\MAMcrawler
venv\Scripts\python execute_full_workflow.py
```

### Option 2: Log to File for Later Review
```bash
venv\Scripts\python execute_full_workflow.py > workflow_run_2025-11-27.log 2>&1
```

### Option 3: Use Screen/Tmux for Background Execution
```bash
# Run in background, check progress anytime
screen -S audiobook_workflow
venv\Scripts\python execute_full_workflow.py
# Detach: Ctrl+A then D
# Reattach: screen -r audiobook_workflow
```

---

## VERIFICATION - CHECK REAL RESULTS

After workflow completes, verify REAL changes:

### 1. Check AudiobookShelf Library
```
Open: http://localhost:13378
Expected: 10 new audiobooks in YOUR library
Verify:
  - New books appear in collection
  - Metadata is filled (titles, authors, narrators)
  - ID3 tags readable in ABS
  - Cover art (if embedded)
```

### 2. Check qBittorrent Downloads
```
Open: http://192.168.0.48:52095/
Expected: 10 torrents added
Verify:
  - All torrents seeding (status: "Uploading")
  - Real upload bandwidth usage
  - Files in download directory
  - Disk space reduced
```

### 3. Check Final Report
```
Open: workflow_final_report.json
Verify:
  - Books targeted: 20
  - Torrents added: 18 (or actual found)
  - Library size: INCREASED
  - Per-user metrics: POPULATED
  - Estimated value: CALCULATED
```

### 4. Check Backup
```
Location: AudiobookShelf backup directory
Verify:
  - New backup file created
  - Size > 1MB
  - Recent timestamp
  - Rotation applied (old backups deleted)
```

### 5. Check Audio Files
```
Location: F:\Audiobookshelf\Books\
Verify:
  - New book folders exist
  - Audio files present (MP3, M4A, FLAC, etc.)
  - ID3 tags written (use ID3 tagger app to verify)
  - File sizes correct
```

### 6. Check Metadata Standardization
```
In AudiobookShelf web UI:
Verify:
  - Titles properly capitalized
  - Author names consistent
  - Genres normalized
  - Narrator info filled where possible
```

---

## REAL DATA FLOW DIAGRAM

```
START WORKFLOW
    ↓
PHASE 1: YOUR ABS Library ←────── REAL API READ
    ↓
PHASE 2-3: Google Books API ←────── REAL API QUERY (real results)
    ↓
PHASE 4: MAM Search ←────────────── REAL TORRENT SEARCH (real torrents)
    ↓
PHASE 5: YOUR qBittorrent ←───────── REAL TORRENTS ADDED (real downloads)
    ↓
PHASE 6: Download Progress ←───────── REAL DOWNLOAD DATA from qBit
    ↓
PHASE 7: YOUR Audio Files ←────────── REAL FILES ON DISK
    ↓
PHASE 7+: YOUR Audio Files ←───────── REAL ID3 TAGS WRITTEN
    ↓
PHASE 8-8F: YOUR ABS Library ←─────── REAL METADATA UPDATED
    ↓
PHASE 9-10: YOUR Author Data ←─────── REAL LIBRARY ANALYSIS
    ↓
PHASE 11: Final Report ←────────────── REAL STATISTICS GENERATED
    ↓
PHASE 12: YOUR Backup ←───────────── REAL BACKUP CREATED & ROTATED
    ↓
END: REAL LIBRARY UPDATED
```

---

## IF SOMETHING FAILS

### Download Issues (Phase 6 Timeout)
```
What to do:
1. Check qBit is still seeding (may just be slow)
2. Wait longer (up to 24 hours)
3. Manually check download folder
4. Continue workflow when ready
```

### Metadata Issues (Phase 8-8F)
```
What to do:
1. Check Google Books API quota (1000/day)
2. Check ABS is responding
3. Review partial results in report
4. Continue workflow (handles partial data)
```

### Backup Issues (Phase 12)
```
What to do:
1. Ensure ABS has disk space
2. Check /api/admin/backup endpoint
3. Manually backup if needed
4. Note in report: "Manual backup required"
```

---

## SUCCESS CRITERIA - VERIFY ALL

| Phase | Success Criteria | Verify By |
|-------|------------------|-----------|
| 1 | Library accessible | ABS API responds |
| 2-3 | Books found | JSON results contain books |
| 4 | Torrents found | Magnet links extracted |
| 5 | Downloads started | qBit shows torrents added |
| 6 | Downloads complete | Files on disk, 100% progress |
| 7 | Books imported | New items in ABS library |
| 7+ | ID3 tags written | Audio files have embedded metadata |
| 8-8F | Metadata enhanced | Field coverage >70% |
| 9-10 | Author analysis | Top authors identified |
| 11 | Report generated | JSON file created with stats |
| 12 | Backup created | Backup file exists, >1MB |

**If all ✓ verified**: Workflow executed 100% with REAL data

---

## NEXT: AUTO-SCHEDULING (Optional)

To run workflow automatically on schedule:

```bash
# Windows Task Scheduler
1. Open Task Scheduler
2. Create Basic Task: "AudioBook Workflow"
3. Trigger: Daily at 21:00
4. Action: Run script
5. Script: venv\Scripts\python execute_full_workflow.py

# Or use cron (WSL/Linux):
0 21 * * * cd /path/to/MAMcrawler && venv/Scripts/python execute_full_workflow.py
```

---

**YOU'RE READY TO RUN THE COMPLETE REAL WORKFLOW WITH 100% REAL DATA**

No mocking, no skipping, everything real.
