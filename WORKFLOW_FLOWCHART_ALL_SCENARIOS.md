# AudiobookShelf Best Practices Workflow - Complete Flowchart with All Scenarios

**Document**: Complete Scenario Flowcharts
**Status**: All 14 Phases with Decision Points
**Scope**: Audiobooks Only

---

## 1. MASTER WORKFLOW OVERVIEW (High Level)

```
START
  ↓
┌─────────────────────────────────────┐
│ PHASE 1: LIBRARY SCAN               │
│ - Get library data from ABS         │
│ - Count existing books              │
│ - Identify gaps                     │
└─────────────────────────────────────┘
  ↓
  Library found? ──NO──→ EXIT (FAIL: No library access)
  ↓ YES
┌─────────────────────────────────────┐
│ PHASE 2: SCIENCE FICTION SEARCH     │
│ - Query Google Books API            │
│ - Get 10 sci-fi audiobooks          │
└─────────────────────────────────────┘
  ↓
  Books found? ──NO──→ Continue (search failed)
  ↓ YES
┌─────────────────────────────────────┐
│ PHASE 3: FANTASY SEARCH             │
│ - Query Google Books API            │
│ - Get 10 fantasy audiobooks         │
└─────────────────────────────────────┘
  ↓
  Books found? ──NO──→ Continue (search failed)
  ↓ YES
┌─────────────────────────────────────┐
│ PHASE 4: QUEUE FOR DOWNLOAD         │
│ - Combine sci-fi + fantasy lists    │
│ - Query MAM for torrents            │
│ - Get magnet links                  │
└─────────────────────────────────────┘
  ↓
  Magnets found? ──NO──→ EXIT (FAIL: No torrents available)
  ↓ YES
┌─────────────────────────────────────┐
│ PHASE 5: QBITTORRENT DOWNLOAD       │
│ - Add magnets to qBittorrent        │
│ - Queue downloads (max 10)          │
└─────────────────────────────────────┘
  ↓
  Torrents added? ──NO──→ Continue (qBit unavailable)
  ↓ YES
┌─────────────────────────────────────┐
│ PHASE 6: MONITOR DOWNLOADS          │
│ - Wait for completion               │
│ - Check status periodically         │
│ - Timeout: 24 hours max             │
└─────────────────────────────────────┘
  ↓
  Downloads complete? ──NO──→ Continue (timeout)
  ↓ YES
┌─────────────────────────────────────┐
│ PHASE 7: SYNC TO AUDIOBOOKSHELF     │
│ - Trigger library scan              │
│ - Import new files                  │
│ - Create book records               │
└─────────────────────────────────────┘
  ↓
  Sync complete? ──NO──→ Continue (API timeout)
  ↓ YES
┌─────────────────────────────────────┐
│ PHASE 7+: WRITE ID3 METADATA        │
│ (Enhancement 2A)                    │
│ - Extract metadata from folders     │
│ - Write ID3 tags to MP3 files       │
│ - Support multiple formats          │
└─────────────────────────────────────┘
  ↓
  Tags written? ──NO──→ Continue (no audio files found)
  ↓ YES
┌─────────────────────────────────────┐
│ PHASE 8: SYNC METADATA              │
│ - Fetch metadata from ABS API       │
│ - Update book records               │
│ - Refresh cache                     │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ PHASE 8B: QUALITY VALIDATION        │
│ - Check author coverage             │
│ - Check narrator coverage           │
│ - Generate baseline metrics         │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ PHASE 8C: STANDARDIZATION           │
│ - Format titles                     │
│ - Clean author names                │
│ - Normalize genres                  │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ PHASE 8D: NARRATOR DETECTION        │
│ - Pattern match existing metadata   │
│ - Extract from folder names         │
│ - Parse from book titles            │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ PHASE 8E: NARRATOR POPULATION       │
│ - Query Google Books API            │
│ - 6-pattern matching for narrators  │
│ - Update missing narrators          │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ PHASE 8F: QUALITY RECHECK           │
│ - Post-population metrics           │
│ - Compare with baseline             │
│ - Generate improvement report       │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ PHASE 9: BUILD AUTHOR HISTORY       │
│ - Aggregate author books            │
│ - Count per-author totals           │
│ - Identify top authors              │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ PHASE 10: CREATE MISSING QUEUE      │
│ - Analyze author complete series    │
│ - Find missing books                │
│ - Rank by author popularity         │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ PHASE 11: GENERATE FINAL REPORT     │
│ (Enhancement 2C)                    │
│ - Library statistics                │
│ - Estimated value                   │
│ - Top authors analysis              │
│ - Per-user progress metrics         │
│ - Missing books queue               │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ PHASE 12: AUTOMATED BACKUP          │
│ (Enhancement 2B)                    │
│ - Trigger backup API                │
│ - Validate backup success           │
│ - Rotate old backups                │
└─────────────────────────────────────┘
  ↓
SUCCESS: Workflow Complete
  ↓
END
```

---

## 2. DETAILED SCENARIO FLOWCHARTS

### SCENARIO 1: Successful Full Workflow Execution

```
START
  ↓
PHASE 1: LIBRARY SCAN
  ├─ Connect to ABS API ────→ SUCCESS
  ├─ Fetch library data ─────→ Books: 500
  ├─ Identify current state ─→ Gaps found
  └─ Return library stats ───→ Continue
  ↓
PHASE 2: SCI-FI SEARCH
  ├─ Query Google Books ─────→ Results: 15
  ├─ Filter audiobooks ──────→ Valid: 10
  └─ Build list ─────────────→ Continue
  ↓
PHASE 3: FANTASY SEARCH
  ├─ Query Google Books ─────→ Results: 12
  ├─ Filter audiobooks ──────→ Valid: 10
  └─ Build list ─────────────→ Continue
  ↓
PHASE 4: QUEUE FOR DOWNLOAD
  ├─ Combine lists ──────────→ Total: 20 books
  ├─ Search MAM for each ────→ Found: 18 torrents
  └─ Extract magnets ────────→ Ready: 18
  ↓
PHASE 5: QBITTORRENT DOWNLOAD
  ├─ Connect to qBit ────────→ SUCCESS
  ├─ Add magnets (max 10) ───→ Added: 10
  ├─ Check status ───────────→ Queued
  └─ Start download ─────────→ 0% → Download
  ↓
PHASE 6: MONITOR DOWNLOADS
  ├─ Check every 5 min ──────→ Progress: 10%
  ├─ Update status ──────────→ Progress: 50%
  ├─ Wait for completion ────→ Progress: 100%
  └─ Verify files ───────────→ All complete
  ↓
PHASE 7: SYNC TO AUDIOBOOKSHELF
  ├─ Trigger library scan ───→ Scanning...
  ├─ Import 10 new files ────→ Success
  ├─ Create book records ────→ 10 created
  └─ Get book objects ───────→ Continue
  ↓
PHASE 7+: WRITE ID3 METADATA
  ├─ Locate audio files ─────→ Found: 10
  ├─ Read folder structure ──→ Extracting...
  ├─ Parse narrators ────────→ Found: 8
  └─ Write ID3 tags ─────────→ Written: 10
  ↓
PHASE 8: SYNC METADATA
  ├─ Fetch from ABS API ─────→ 10 books
  ├─ Update records ─────────→ Complete
  └─ Refresh cache ──────────→ Done
  ↓
PHASE 8B: QUALITY VALIDATION
  ├─ Check authors ──────────→ 100% coverage
  ├─ Check narrators ────────→ 80% coverage
  └─ Generate metrics ───────→ Report created
  ↓
PHASE 8C: STANDARDIZATION
  ├─ Format titles ──────────→ Complete
  ├─ Clean authors ──────────→ Complete
  └─ Normalize genres ───────→ Complete
  ↓
PHASE 8D: NARRATOR DETECTION
  ├─ Pattern match ──────────→ Found: 2 narrators
  ├─ Folder parsing ─────────→ Found: 6 narrators
  └─ Total detected ─────────→ 8 narrators
  ↓
PHASE 8E: NARRATOR POPULATION
  ├─ Query Google Books ─────→ 2 missing narrators
  ├─ API calls (6 patterns) ─→ Found: 2
  └─ Update records ─────────→ 100% populated
  ↓
PHASE 8F: QUALITY RECHECK
  ├─ Post-population check ──→ 100% author coverage
  ├─ Compare baseline ───────→ +20% narrator coverage
  └─ Generate report ────────→ Improvement: +2 narrators
  ↓
PHASE 9: BUILD AUTHOR HISTORY
  ├─ Aggregate books ────────→ 500 authors
  ├─ Count per author ───────→ 1-15 books/author
  └─ Identify top 5 ─────────→ Top authors found
  ↓
PHASE 10: CREATE MISSING QUEUE
  ├─ Find complete series ───→ 50 series complete
  ├─ Identify missing books ─→ 25 missing books
  └─ Rank by popularity ─────→ Queue created
  ↓
PHASE 11: GENERATE FINAL REPORT
  ├─ Library stats ──────────→ 510 books, 500 authors
  ├─ Estimated value ────────→ $14,025
  ├─ Top authors analysis ───→ 5 authors listed
  ├─ User progress (2C) ─────→ 2 users with metrics
  ├─ Missing books queue ────→ 25 candidates
  └─ Save report ────────────→ JSON file created
  ↓
PHASE 12: AUTOMATED BACKUP
  ├─ Trigger backup ─────────→ API called
  ├─ Wait for completion ────→ Backup created
  ├─ Validate backup ────────→ Size: 500MB ✓
  ├─ Rotation check ─────────→ Keep: 11, Delete: 0
  └─ Complete ───────────────→ Backup verified
  ↓
SUCCESS: All phases complete
  ↓
Report: workflow_final_report.json
Backup: backup_2025-11-27_220000.tar.gz
  ↓
END
```

---

### SCENARIO 2: Library Scan Fails (Phase 1 Failure)

```
START
  ↓
PHASE 1: LIBRARY SCAN
  ├─ Connect to ABS API ─────→ TIMEOUT
  │                           (No network or ABS down)
  ├─ Retry 3 times ──────────→ Still failing
  └─ Return error ───────────→ FAILURE
  ↓
DECISION: Continue workflow?
  ├─ NO ─→ EXIT with error message
  │        "Cannot access AudiobookShelf - workflow cannot continue"
  │
  └─ YES ─→ Continue with cached data (if available)
            Or skip to Phase 7+ onwards
  ↓
IF CACHE AVAILABLE:
  ├─ Use cached library data ─→ Proceed with Phases 2-3
  ├─ But no access to new books
  └─ Only ID3/Metadata operations possible
  ↓
IF NO CACHE:
  ├─ Skip all download phases
  ├─ Cannot proceed past Phase 1
  └─ EXIT (Workflow cannot continue)
  ↓
END (FAILURE)
```

---

### SCENARIO 3: No Books Found in Search (Phase 2-3 Failure)

```
START
  ↓
PHASE 1: LIBRARY SCAN ──→ SUCCESS
  ↓
PHASE 2: SCI-FI SEARCH
  ├─ Query Google Books ─────→ No results
  │                           (Search too specific or no matches)
  ├─ Adjust search params ───→ Retry with broader terms
  ├─ Retry count: 0/3 ───────→ Try again
  │
  ├─ Results found? ─────────→ NO
  └─ Log warning ────────────→ "No sci-fi books found"
  ↓
DECISION: Continue to Phase 3?
  ├─ YES ─→ Proceed to fantasy search
  └─ NO ──→ Can skip to Phase 7+ (no downloads)
  ↓
PHASE 3: FANTASY SEARCH
  ├─ Query Google Books ─────→ Results found: 8 books
  ├─ Filter audiobooks ──────→ Valid: 8
  └─ Continue ───────────────→ Proceed
  ↓
PHASE 4: QUEUE FOR DOWNLOAD
  ├─ Combine lists ──────────→ Total: 8 books (only fantasy)
  ├─ Search MAM ─────────────→ Found: 6 torrents
  └─ Extract magnets ────────→ Ready: 6
  ↓
Continue with Phase 5+ as normal
  ↓
RESULT: Workflow completes with partial data
  - Only fantasy audiobooks acquired
  - No sci-fi audiobooks
  - All other phases proceed normally
  ↓
END (PARTIAL SUCCESS)
```

---

### SCENARIO 4: No Torrents Available on MAM (Phase 4 Failure)

```
START
  ↓
PHASE 1-3: SCAN & SEARCH ──→ SUCCESS
  │ Found: 20 audiobooks
  ↓
PHASE 4: QUEUE FOR DOWNLOAD
  ├─ Search MAM for each ────→ Book 1: Not found
  ├─ Continue searching ─────→ Book 2: Not found
  ├─ Continue all 20 books ──→ Found: 0 torrents
  │
  ├─ ERROR: No magnets found
  └─ Log failure ────────────→ "No MAM torrents available"
  ↓
DECISION: Continue workflow?
  ├─ NO ─→ EXIT
  │        "Cannot continue without downloads"
  │
  └─ YES ─→ Skip to Phase 7+ (ID3/Metadata operations only)
            No files to import
  ↓
IF CONTINUE:
  ├─ Skip Phase 5 (qBit) ────→ No downloads to queue
  ├─ Skip Phase 6 (Monitor) ─→ No downloads to monitor
  ├─ Skip Phase 7 (Sync) ────→ No new files to import
  ├─ Phase 8+ still run ─────→ Metadata operations on existing library
  │
  └─ Result: Report generated with no new books added
  ↓
REPORT OUTPUT:
  - Books targeted: 20
  - Torrents added: 0
  - New imports: 0
  - Library unchanged
  ↓
END (FAILURE - No new content)
```

---

### SCENARIO 5: qBittorrent Unavailable (Phase 5 Failure)

```
START
  ↓
PHASE 1-4: SCAN, SEARCH, QUEUE ──→ SUCCESS
  │ Magnets ready: 10
  ↓
PHASE 5: QBITTORRENT DOWNLOAD
  ├─ Connect to qBit ────────→ CONNECTION REFUSED
  │                           (qBit not running or port wrong)
  ├─ Retry connection ───────→ Still failing
  └─ Log error ──────────────→ "Cannot connect to qBittorrent"
  ↓
DECISION: Continue workflow?
  ├─ NO ─→ EXIT immediately
  │        Cannot proceed without downloads
  │
  └─ YES ─→ Continue (but skip download phases)
  ↓
IF CONTINUE:
  ├─ Document magnet links ──→ Log to file
  ├─ Skip Phase 5 ───────────→ No downloads added
  ├─ Skip Phase 6 ───────────→ No downloads to monitor
  ├─ Skip Phase 7 ───────────→ No new files to sync
  ├─ Phase 8+ still run ─────→ Metadata operations proceed
  │
  └─ Result: Workflow continues with metadata only
  ↓
REPORT OUTPUT:
  - Books targeted: 10
  - Torrents added: 0
  - Note: "qBittorrent unavailable - magnets documented for manual addition"
  - Magnet file: magnets_2025-11-27.txt
  ↓
RECOMMENDATION:
  - User should manually add magnets to qBit
  - Re-run Phase 5-7 after qBit is running
  ↓
END (PARTIAL - qBit Error)
```

---

### SCENARIO 6: Download Timeout (Phase 6 Timeout)

```
START
  ↓
PHASE 1-5: SCAN, SEARCH, QUEUE, DOWNLOAD ──→ SUCCESS
  │ Downloads started: 10
  ├─ Progress after 1 hour: 20%
  ├─ Progress after 4 hours: 45%
  ├─ Progress after 12 hours: 75%
  └─ Progress after 24 hours: Still 75%
  ↓
PHASE 6: MONITOR DOWNLOADS
  ├─ Check status interval: 5 minutes
  ├─ Timeout threshold: 24 hours
  ├─ After 24 hours: TIMEOUT
  │
  └─ Decision:
     ├─ Completed: 7 downloads (70%)
     ├─ In progress: 3 downloads (30%)
     └─ Action: Stop waiting
  ↓
DECISION: Continue to Phase 7?
  ├─ YES ─→ Sync only completed downloads (7)
  │         Skip incomplete (3)
  │
  └─ NO ──→ Wait longer for remaining downloads
            Or exit and retry
  ↓
IF CONTINUE WITH COMPLETED:
  ├─ PHASE 7: Sync completed files
  │ ├─ Trigger library scan ──→ Imports 7 files
  │ ├─ Skip missing 3 ────────→ Not available yet
  │ └─ Continue normally ─────→ Phase 8+
  │
  ├─ Incomplete files:
  │ ├─ Still downloading in background
  │ ├─ User can manually trigger Phase 7 later
  │ └─ When ready, scan will pick up remaining files
  │
  └─ Report includes note:
     "3/10 downloads incomplete after timeout"
  ↓
RESULT: Partial workflow completion
  - 7 books imported successfully
  - 3 books available for import later
  - Workflow proceeds with available data
  ↓
END (PARTIAL SUCCESS)
```

---

### SCENARIO 7: AudiobookShelf Sync Fails (Phase 7 Failure)

```
START
  ↓
PHASE 1-6: All successful
  │ Downloads complete: 10 files ready
  ↓
PHASE 7: SYNC TO AUDIOBOOKSHELF
  ├─ Connect to ABS API ─────→ TIMEOUT
  ├─ Trigger library scan ───→ FAILED
  └─ Log error ──────────────→ "ABS library scan failed"
  ↓
DECISION: Continue?
  ├─ NO ─→ EXIT
  │        Files downloaded but not imported
  │
  └─ YES ─→ Proceed to Phase 8+ with cached data
            Metadata operations only
  ↓
IF CONTINUE:
  ├─ PHASE 7+: ID3 writing ──→ Proceed (writes to files)
  │ ├─ Finds audio files ─────→ Found (not synced yet)
  │ ├─ Extracts metadata ─────→ Success
  │ └─ Writes ID3 tags ───────→ Success
  │
  ├─ PHASE 8: Skip metadata sync ─→ No ABS access
  │
  ├─ PHASE 8B-8F: Skip ──────→ Need ABS library data
  │
  ├─ PHASE 9-10: Skip ───────→ Need book data
  │
  └─ PHASE 11: Report ───────→ Shows failure
     └─ Note: "Library import failed - files remain in download directory"
  ↓
RESULT: Partial completion
  - Downloads complete ✓
  - ID3 tags written ✓
  - ABS not updated ✗
  - Files awaiting manual import
  ↓
USER ACTION REQUIRED:
  - Restart AudiobookShelf or check API
  - Trigger library scan manually in ABS UI
  - Re-run workflow Phase 7 onwards
  ↓
END (FAILURE - Requires manual intervention)
```

---

### SCENARIO 8: Metadata Sync Issues (Phase 8 Failure)

```
START
  ↓
PHASE 1-7: All successful
  │ Books synced to ABS: 10
  ↓
PHASE 8: SYNC METADATA
  ├─ Fetch from ABS API ─────→ PARTIAL RESPONSE
  │ ├─ Books returned: 8/10
  │ ├─ Missing data: 2 books
  │ └─ Continue with available
  │
  ├─ Update records ─────────→ 8 successful
  ├─ 2 books skipped ────────→ Logged as errors
  └─ Continue to Phase 8B ───→ Proceed
  ↓
PHASE 8B: QUALITY VALIDATION
  ├─ Check authors (8 books) ─→ 100% coverage
  ├─ Check narrators (8 books) → 75% coverage
  │                             (2 missing)
  └─ Generate metrics ───────→ Based on 8 books
  ↓
PHASE 8C-8D: STANDARDIZATION & DETECTION ──→ Proceed normally
  ↓
PHASE 8E: NARRATOR POPULATION
  ├─ Target 2 missing narrators
  ├─ Query Google Books ─────→ Found 1/2
  └─ Update records ─────────→ 75% → 87.5% coverage
  ↓
PHASE 8F: QUALITY RECHECK
  ├─ Post-population ────────→ 87.5% narrator coverage
  ├─ Compare baseline ───────→ +12.5% improvement
  └─ Report: "Partial success due to incomplete metadata sync"
  ↓
Continue to Phase 9-12
  ↓
RESULT: Workflow continues with partial data
  - 2 books have incomplete metadata
  - But operations proceed on 8 complete books
  - Report notes the incomplete data
  ↓
USER ACTION RECOMMENDED:
  - Check why 2 books didn't sync
  - Verify ABS library status
  - Consider manual update for 2 incomplete books
  ↓
END (PARTIAL SUCCESS)
```

---

### SCENARIO 9: No Narrators Found (Phase 8E Failure)

```
START
  ↓
PHASE 1-8D: All successful
  │ Books ready: 10
  │ Narrators already detected: 2/10 (20%)
  ↓
PHASE 8E: NARRATOR POPULATION
  ├─ Missing narrators: 8/10
  ├─ Query Google Books API ─→ 6-pattern matching
  │ ├─ Pattern 1 (Title): No results
  │ ├─ Pattern 2 (Author+Book): No results
  │ ├─ Pattern 3 (Phrase): No results
  │ ├─ Pattern 4 (Search): No results
  │ ├─ Pattern 5 (Catalog): No results
  │ └─ Pattern 6 (Metadata): No results
  │
  ├─ Result: Found 0/8 narrators
  └─ Log: "No additional narrators found via Google Books"
  ↓
DECISION:
  ├─ Continue to Phase 8F? ──→ YES (always continue)
  ├─ Phase 8F will report ───→ No improvement
  └─ Continue to Phase 9-12 ─→ Normal flow
  ↓
PHASE 8F: QUALITY RECHECK
  ├─ Baseline: 2/10 narrators (20%)
  ├─ Post-population: 2/10 (20%)
  ├─ Improvement: 0% ────────→ No progress
  └─ Report: "Narrator detection via Google Books unsuccessful"
  ↓
PHASE 9-12: Proceed normally
  │ With existing metadata (2 narrators)
  ↓
RESULT: Workflow completes with low narrator coverage
  - 20% narrator coverage maintained
  - No external data sources found narrators
  - Manual narrator entry may be required
  ↓
RECOMMENDATION:
  - User can manually add narrators in ABS UI
  - Or add to folder names for ID3 tag writing
  - Future re-runs may pick up manual entries
  ↓
END (SUCCESS - No improvement possible)
```

---

### SCENARIO 10: Author History Building Issues (Phase 9 Failure)

```
START
  ↓
PHASE 1-8F: All successful
  │ Library state: 510 books
  ↓
PHASE 9: BUILD AUTHOR HISTORY
  ├─ Aggregate by author ────→ Processing...
  ├─ Count totals ───────────→ 85% complete
  ├─ API timeout ────────────→ FAILURE
  │
  ├─ Partial results:
  │ ├─ Authors processed: 425/500
  │ ├─ Authors pending: 75
  │ └─ Top 5 identified (partial)
  │
  └─ Decision:
     ├─ Use partial results? ─→ YES
     └─ Continue to Phase 10 ─→ Proceed
  ↓
PHASE 10: CREATE MISSING QUEUE
  ├─ Use partial author data ─→ 425 authors
  ├─ Analyze complete series ─→ 40 complete series
  ├─ Find missing books ─────→ 20 candidates
  └─ Rank by popularity ─────→ Based on 425 authors
  ↓
Note: 75 authors not included (partial data)
  ├─ Missing opportunities ──→ Unknown
  └─ User should re-run later
  ↓
PHASE 11: GENERATE REPORT
  ├─ Library stats ──────────→ 510 books (correct)
  ├─ Top authors ────────────→ 5 identified (may be incomplete)
  ├─ Missing books queue ────→ 20 candidates (partial)
  └─ Report note: "Author history partially incomplete - 425/500 authors processed"
  ↓
PHASE 12: Backup ──→ Proceeds normally
  ↓
RESULT: Workflow completes with partial author data
  - Report generated
  - May miss some author completions
  - Backup taken with current state
  ↓
USER ACTION:
  - Re-run workflow to complete author analysis
  - Or manually check missing authors (75 pending)
  ↓
END (PARTIAL SUCCESS)
```

---

### SCENARIO 11: Backup API Unavailable (Phase 12 Failure)

```
START
  ↓
PHASE 1-11: All successful
  │ Report generated: workflow_final_report.json
  ↓
PHASE 12: AUTOMATED BACKUP
  ├─ Connect to ABS Backup API ─→ NOT FOUND (404)
  │                               (Endpoint not available)
  ├─ OR: API timeout ────────────→ No response
  │
  └─ Decision:
     ├─ Retry 3 times? ─────→ Still failing
     └─ Log error ──────────→ "Backup API unavailable"
  ↓
DECISION: Exit or continue?
  ├─ NO ─→ EXIT with error
  │        "Backup failed - manual backup recommended"
  │
  └─ YES ─→ Continue (non-critical failure)
            Log warning and complete workflow
  ↓
IF CONTINUE:
  ├─ Skip backup ────────────→ No automatic backup created
  ├─ Complete workflow ──────→ All other phases done
  │
  └─ Report:
     └─ Note: "Automated backup unavailable"
        "User should perform manual backup"
  ↓
RESULT: Workflow completes WITHOUT backup
  - All data operations successful
  - Report generated
  - NO BACKUP CREATED ⚠️
  - Data at risk if ABS fails before next backup
  ↓
USER ACTION REQUIRED:
  - Manually backup AudiobookShelf database
  - Verify backup API configuration
  - Check server logs for issues
  - Consider re-running workflow when backup API available
  ↓
END (PARTIAL - No backup)
```

---

### SCENARIO 12: Backup Validation Fails (Phase 12 - Size Check)

```
START
  ↓
PHASE 1-11: All successful
  ↓
PHASE 12: AUTOMATED BACKUP
  ├─ Trigger backup API ─────→ SUCCESS
  ├─ Backup file created ────→ backup_2025-11-27.tar.gz
  ├─ Check file size ────────→ 512 KB (TOO SMALL!)
  │                           Threshold: 1 MB
  │
  ├─ Decision:
  │ ├─ Size < 1 MB = Failed validation
  │ └─ Log error: "Backup too small - possible incomplete backup"
  │
  └─ Status: BACKUP FAILED
  ↓
DECISION:
  ├─ NO ─→ EXIT with error
  │        "Backup validation failed"
  │
  └─ YES ─→ Continue (accept risk)
            Log warning, complete workflow
  ↓
IF CONTINUE:
  ├─ Skip rotation ──────────→ Don't process invalid backup
  ├─ Keep problematic backup ─→ For manual review
  │
  └─ Report:
     └─ Note: "Backup validation failed - 512 KB (min: 1 MB)"
        "Backup may be incomplete"
  ↓
RESULT: Workflow completes, backup questionable
  - Workflow finished
  - Backup file exists but may be invalid
  - Rotation skipped (don't trust backup)
  - NO VALID BACKUP PROTECTION
  ↓
USER ACTION REQUIRED:
  - Investigate why backup is so small
  - Check AudiobookShelf logs
  - Verify database size vs backup size
  - Perform manual backup if needed
  - Troubleshoot backup process
  ↓
END (FAILURE - Invalid backup)
```

---

### SCENARIO 13: No Users Found (Phase 2C Issue)

```
START
  ↓
PHASE 1-11: Proceeding normally
  ↓
PHASE 11: GENERATE FINAL REPORT (with Enhancement 2C)
  ├─ Call get_per_user_metrics() ───→ Fetching users...
  ├─ Query /api/users endpoint ─────→ 404 NOT FOUND
  │                                   OR: Empty response []
  │
  ├─ No users found ─────────────────→ 0 users
  └─ Log warning: "Users endpoint unavailable or no users configured"
  ↓
DECISION: Continue report generation?
  ├─ YES ─→ Generate report WITHOUT per-user metrics
  └─ NO ──→ Skip Phase 11 (not recommended)
  ↓
IF CONTINUE:
  ├─ Report sections included:
  │ ├─ Library statistics ─────→ ✓ Included
  │ ├─ Estimated value ───────→ ✓ Included
  │ ├─ Top authors ───────────→ ✓ Included
  │ ├─ Missing books queue ───→ ✓ Included
  │ └─ Per-user metrics ──────→ ✗ SKIPPED
  │                              (No users available)
  │
  └─ Report note:
     └─ "User progress tracking unavailable - no users configured in AudiobookShelf"
  ↓
RESULT: Report generated without per-user section
  - All other metrics present
  - User progress section missing
  - Workflow continues normally
  ↓
USER ACTION:
  - Configure users in AudiobookShelf
  - Re-run workflow to populate per-user metrics
  - Or verify that users API is accessible
  ↓
END (PARTIAL SUCCESS)
```

---

### SCENARIO 14: Complete Workflow Failure (Cascade)

```
START
  ↓
PHASE 1: LIBRARY SCAN
  └─ FAILURE: Cannot connect to AudiobookShelf
  ↓
DECISION: Continue?
  └─ NO (Cannot proceed without library)
  ↓
IMMEDIATE EXIT:
  ├─ Error message: "Cannot access AudiobookShelf library"
  ├─ No backup attempted
  ├─ No report generated
  │
  └─ Log file: error_2025-11-27.log
     └─ Contains: Connection failure details
  ↓
WORKFLOW STATE: INCOMPLETE
  ├─ Phases executed: 0/14
  ├─ Books downloaded: 0
  ├─ Books imported: 0
  ├─ Library unchanged
  └─ No backup created
  ↓
USER ACTION REQUIRED: CRITICAL
  1. Check AudiobookShelf is running
  2. Verify network connectivity
  3. Check ABS_URL and ABS_TOKEN in .env
  4. Review logs for detailed error
  5. Re-run workflow when issues resolved
  ↓
ERROR RECOVERY OPTIONS:
  ├─ Option 1: Fix ABS and restart
  ├─ Option 2: Check network connectivity
  ├─ Option 3: Verify .env configuration
  ├─ Option 4: Check firewall/ports
  └─ Option 5: Review AudiobookShelf logs
  ↓
END (CRITICAL FAILURE)
```

---

## 3. DECISION TREE MATRIX

| Phase | Success | Partial | Failure | Continue? | Impact |
|-------|---------|---------|---------|-----------|--------|
| 1: Library Scan | Proceed | Use cache | STOP | No | Critical |
| 2: Sci-Fi Search | Proceed | Use found | Continue | Yes | Medium |
| 3: Fantasy Search | Proceed | Use found | Continue | Yes | Medium |
| 4: Queue | Proceed | Partial | STOP | No | Critical |
| 5: qBit | Proceed | Skip | STOP | No | Critical |
| 6: Monitor | Proceed | Timeout | Continue | Yes | Medium |
| 7: Sync | Proceed | Skip metadata | Continue | Yes | High |
| 7+: ID3 Tags | Proceed | Partial | Continue | Yes | Low |
| 8: Metadata | Proceed | Partial | Continue | Yes | Low |
| 8B-8F: Quality | Proceed | Partial | Continue | Yes | Low |
| 9: Author History | Proceed | Partial | Continue | Yes | Low |
| 10: Missing Queue | Proceed | Partial | Continue | Yes | Low |
| 11: Report | Proceed | Partial | Continue | Yes | Low |
| 12: Backup | Proceed | Fail validation | Continue | Yes | High |

**Key**:
- **STOP**: Workflow cannot continue, exit immediately
- **Continue**: Proceed to next phase despite failure
- **Impact**: How critical to overall operation

---

## 4. ERROR HANDLING DECISION FLOW

```
Phase Execution
  ↓
Try Operation
  ├─ SUCCESS ────────────→ Continue to next phase
  │
  ├─ ERROR ──────────────→ Log error message
  │                        ↓
  │                        Determine Severity:
  │                        │
  │                        ├─ CRITICAL ──→ Can we continue?
  │                        │               ├─ NO → STOP workflow
  │                        │               └─ YES → Use fallback, continue
  │                        │
  │                        ├─ HIGH ──────→ Usually continue with partial data
  │                        │
  │                        └─ LOW ───────→ Log warning, proceed normally
  │
  └─ TIMEOUT ────────────→ Can we retry?
                            ├─ YES → Retry up to 3 times
                            │        Then decide above
                            └─ NO → Log and handle as error above
```

---

## 5. RECOVERY SCENARIOS

### Recovery 1: Re-run Failed Phase

```
Workflow Failed at Phase 7: Library Sync
  ↓
User fixes issue (e.g., restart ABS)
  ↓
Option A: Re-run entire workflow
  └─ Safest: starts from beginning, idempotent
  ↓
Option B: Re-run from Phase 7
  ├─ Skips completed phases
  ├─ Requires manual state tracking
  └─ Not currently supported (full re-run recommended)
```

### Recovery 2: Manual Intervention Between Phases

```
Workflow paused at Phase 5 (downloads incomplete)
  ↓
User manually:
  1. Waits for downloads to complete in qBit
  2. Checks files in download directory
  3. Manually triggers Phase 7 library scan in ABS UI
  ↓
Re-run workflow from Phase 7+:
  1. Skips Phases 1-6
  2. Starts at Phase 7 (Sync to ABS)
  3. Imports manually downloaded files
  4. Continues metadata operations
  ↓
Result: Files imported, metadata operations applied
```

### Recovery 3: Backup and Restore

```
Workflow creates bad data in ABS
  ↓
User has backup from Phase 12
  ↓
Options:
  1. Restore from backup ─→ Rollback to pre-workflow state
  2. Manual data cleanup ─→ Fix specific issues
  3. Re-run workflow ─────→ Try again
  ↓
Phase 12 backup ensures recovery capability
```

---

## 6. PARALLEL EXECUTION (NOT IMPLEMENTED - SEQUENTIAL ONLY)

Current implementation: **SEQUENTIAL ONLY**

```
Phase 1 → Phase 2 → Phase 3 → ... → Phase 12
```

Future enhancement could enable:

```
PHASE 2 (Sci-Fi Search) ──┐
                           ├─→ Phase 4 (Queue)
PHASE 3 (Fantasy Search) ──┘
```

But currently:
- Phases execute one at a time
- Each phase must complete before next starts
- Total execution time: ~30-60 minutes depending on downloads

---

## 7. IDEMPOTENCY ANALYSIS

| Phase | Idempotent? | Note |
|-------|-------------|------|
| 1: Library Scan | YES | Read-only operation |
| 2-3: Search | YES | Query-only operation |
| 4: Queue | YES | Only aggregates, doesn't download |
| 5: Add to qBit | NO | Adds torrents multiple times |
| 6: Monitor | YES | Read-only monitoring |
| 7: Sync to ABS | MOSTLY | May create duplicate books if run twice |
| 7+: ID3 Tags | YES | Can re-write same tags safely |
| 8-12: Metadata ops | YES | Update operations are safe to repeat |

**Recommendation**: Only phases 5, 7 may cause issues if run multiple times. Re-run full workflow only when previous run failed.

---

## 8. COMPLETE EXECUTION TIMELINE

```
START: 2025-11-27 21:00:00
  ↓
Phase 1: Library Scan (1 min) ──────→ 21:01:00
Phase 2: Sci-Fi Search (1 min) ─────→ 21:02:00
Phase 3: Fantasy Search (1 min) ────→ 21:03:00
Phase 4: Queue Books (2 min) ───────→ 21:05:00
Phase 5: Add to qBit (1 min) ───────→ 21:06:00
  ↓
Phase 6: Monitor Downloads ─────────→ (24 hours worst case)
  │                                   Average: 2-4 hours
  ↓
Phase 6 Complete: ~23:00:00 (assuming 2 hours)
  ↓
Phase 7: Sync to ABS (5 min) ───────→ 23:05:00
Phase 7+: Write ID3 Tags (3 min) ───→ 23:08:00
Phase 8-8F: Metadata Ops (5 min) ───→ 23:13:00
Phase 9: Author History (2 min) ────→ 23:15:00
Phase 10: Missing Queue (2 min) ────→ 23:17:00
Phase 11: Report (2 min) ───────────→ 23:19:00
Phase 12: Backup (5 min) ───────────→ 23:24:00
  ↓
END: 23:24:00 (with 2-hour downloads)
Total time: ~2.5 hours
```

---

## 9. SUMMARY: KEY DECISION POINTS

```
DECISION POINT 1: Library Accessible?
  ├─ NO → EXIT (Critical failure)
  └─ YES → Continue to Phase 2

DECISION POINT 2: Books Found in Search?
  ├─ NO → Continue anyway (might find in other search)
  └─ YES → Queue them

DECISION POINT 3: Torrents Available?
  ├─ NO → EXIT (No downloads possible)
  └─ YES → Queue for download

DECISION POINT 4: qBittorrent Connected?
  ├─ NO → Skip downloads, continue with metadata
  └─ YES → Download

DECISION POINT 5: Downloads Complete?
  ├─ NO → Timeout after 24h, sync available files
  └─ YES → Sync all

DECISION POINT 6: Library Sync Success?
  ├─ NO → Skip metadata sync, continue with ID3
  └─ YES → Proceed normally

DECISION POINT 7: Continue to Backup?
  ├─ NO → Exit (data unprotected)
  └─ YES → Always backup at end

DECISION POINT 8: Backup Valid?
  ├─ NO → Log warning, continue (data may be unprotected)
  └─ YES → Complete successfully
```

---

**End of Complete Flowchart Documentation**

All 14 phases covered with decision trees, error scenarios, and recovery paths.
