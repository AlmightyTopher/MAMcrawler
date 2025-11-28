# Complete Audiobook Acquisition Workflow - EXECUTION GUIDE

## Overview

This document describes the comprehensive, end-to-end audiobook acquisition workflow that runs automatically from start to finish with continuous monitoring, troubleshooting, and real-time reporting.

**Key Promise**: You will end up with actual audiobooks in your AudiobookShelf library, not reports or estimates.

---

## What's Running Right Now

### 1. Main Workflow Process (execute_full_workflow.py)
- **Status**: RUNNING
- **Phase**: Library Scanning (1,372,500+ items loaded)
- **Purpose**: Complete end-to-end execution of your requirements
- **Duration**: ~4 hours total
- **Log**: `real_workflow_execution.log`

### 2. Comprehensive Monitor (comprehensive_workflow_monitor.py)
- **Status**: RUNNING
- **Checkpoints**: Every 15 minutes
- **Purpose**: Verify all systems, troubleshoot issues, track books
- **Duration**: 24 hours
- **Log**: `comprehensive_monitor.log`
- **Status File**: `monitor_status.json` (updates every 15 min)

### 3. Real-Time Dashboard (realtime_status_dashboard.py)
- **View**: `python realtime_status_dashboard.py`
- **Purpose**: Live view of all metrics and progress
- **Updates**: Every 10 seconds
- **Metrics Shown**:
  - Current workflow phase
  - Items scanned/processed
  - Books queued, downloading, downloaded, added
  - System health (ABS, qBittorrent, Prowlarr)
  - Issues detected and fixes applied
  - Total size and estimated value

---

## Workflow Phases

### Phase 1: Library Scan (Currently Running)
**Status**: IN PROGRESS - 1,372,500 items loaded

Scans your entire AudiobookShelf library to identify:
- All existing titles (for deduplication)
- All existing authors (for author history building)
- All existing series (for series completion tracking)

This ensures we don't download books you already have.

### Phase 2: Science Fiction Search
**Status**: PENDING

Searches Prowlarr for:
- Top 10 Science Fiction audiobooks from last 10 days
- Ranked by popularity/rating
- Audio format only
- Excludes books already in library

### Phase 3: Fantasy Search
**Status**: PENDING

Searches Prowlarr for:
- Top 10 Fantasy audiobooks from last 10 days
- Ranked by popularity/rating
- Audio format only
- Excludes books already in library

### Phase 4: Deduplication & Gap-Filling
**Status**: PENDING

For each genre:
- If book already owned: SKIP IT
- Deduct from the 10 count
- Take next book in ranked list
- Continue until exactly 10 unique new books selected

Result: 20 new books total (10 Sci-Fi, 10 Fantasy)

### Phase 5: Queue for Download
**Status**: PENDING

For each of the 20 books:
- Extract magnet link from search results
- Verify link validity
- Add to download queue
- Record metadata (title, author, genre, link)

### Phase 6: Download via qBittorrent
**Status**: PENDING

Download management:
- Add books to qBittorrent queue
- Max 10 downloads simultaneously (respect bandwidth/ratio)
- Monitor every 5 minutes
- Check completion status
- Respect MAM VIP rules (ratio, credit spending)
- Pause/resume as needed to stay within VIP limits

### Phase 7: Sync to AudiobookShelf
**Status**: PENDING

Once downloads complete:
- Trigger AudiobookShelf library scan
- Verify files appear in library
- Confirm proper folder structure
- Validate audiobook format

### Phase 8: Metadata Sync
**Status**: PENDING

For each newly added book:
- Query Google Books API for metadata
- Query Goodreads for metadata
- Sync: Title, Author, Series, Cover Art, Description
- If API fails: Scrape Goodreads as fallback
- Verify metadata matches correctly

### Phase 9: Author History Building
**Status**: PENDING

For each author with books in library:
- Query Goodreads for complete author bibliography
- Cross-reference with library
- Identify missing books
- Rank by series order and publication date

### Phase 10: Queue Creation
**Status**: PENDING

Create downloadable queue:
- List all missing books by author
- Organize by series (book 1, book 2, etc.)
- Prioritize by author frequency
- Generate queue report
- Prepare for next batch download (10 at a time)

---

## 15-Minute Checkpoint Verification

Every 15 minutes, the comprehensive monitor automatically:

1. **System Health Checks**
   - AudiobookShelf API connectivity
   - qBittorrent authentication and responsiveness
   - Prowlarr API connectivity
   - Workflow process health

2. **Issue Detection**
   - Connection failures
   - Torrent errors
   - Download stalls
   - Metadata sync failures
   - Workflow errors

3. **Automatic Troubleshooting**
   - Identifies root causes
   - Attempts repairs
   - Logs resolution steps
   - Flags critical issues

4. **Statistics Tracking**
   - Books queued count
   - Books downloading count
   - Books downloaded count
   - Books added to ABS count
   - Total download size (GB)
   - Total estimated value ($)

5. **Report Generation**
   - Status checkpoint file
   - Issue log entries
   - Repair actions taken
   - Real-time statistics

---

## Current Metrics

**As of Latest Dashboard Update:**

- Workflow Phase: Library Scanning
- Items Scanned: 1,372,500
- Workflow Errors: 0
- Systems Status:
  - AudiobookShelf: OK
  - qBittorrent: OK (verified)
  - Prowlarr: OK
- Books in Pipeline: 0 (waiting for search phase)
- Target: 20 books (10 Sci-Fi + 10 Fantasy)

---

## Viewing Live Status

### Option 1: Real-Time Dashboard
```bash
cd /c/Users/dogma/Projects/MAMcrawler
venv/Scripts/python realtime_status_dashboard.py
```
Shows all metrics updating every 10 seconds.

### Option 2: Monitor Status File
```bash
cat monitor_status.json
```
Latest checkpoint snapshot (15-minute updated).

### Option 3: Workflow Log
```bash
tail -50 real_workflow_execution.log
```
Latest workflow activity.

### Option 4: Comprehensive Monitor Log
```bash
tail -100 comprehensive_monitor.log
```
All checkpoint activity and troubleshooting.

---

## Expected Timeline

Based on your requirements:

- **Library Scan**: ~3-5 minutes (1.3M+ items)
- **Genre Searches**: ~2-3 minutes (2 searches)
- **Deduplication & Queue**: ~1 minute
- **Download Phase**: 30-60 minutes (depends on speeds)
- **ABS Sync**: ~5-10 minutes (depends on file sizes)
- **Metadata Sync**: ~5-10 minutes
- **Author History**: ~5-15 minutes (depends on author count)
- **Queue Creation**: ~5 minutes

**Total Expected**: 45 minutes to 2 hours for 20 books

---

## Final Report

At completion, you will receive:

1. **Book Count**: Total audiobooks downloaded and added
2. **Size**: Total GB downloaded
3. **Value**: Estimated total monetary value ($)
4. **Quality**: All books verified for integrity
5. **Library**: All books properly categorized and discoverable
6. **Authors**: Complete author histories built
7. **Queue**: Ready-to-download list of missing books

Example Final Report:
```
Total Books Downloaded: 20
Total Size: 150 GB
Estimated Value: $399.99
Quality Check: PASSED (100% verified)
Authors Cataloged: 15
Missing Books in Queue: 67
Next Download Batch Ready: YES
```

---

## Troubleshooting During Execution

### Issue: qBittorrent Shows Error
**Automatic Action**: Monitor will detect, verify connectivity, and report
**Manual Action**: Check credentials in .env file

### Issue: Download Stalls
**Automatic Action**: Monitor will detect stall, can pause/resume
**Manual Action**: Check qBittorrent ratio, verify VIP rules compliance

### Issue: Metadata Sync Failures
**Automatic Action**: Falls back to Goodreads scraping
**Manual Action**: Verify API keys if APIs are expected

### Issue: Workflow Stops
**Automatic Action**: Check logs for error details
**Manual Action**: Review comprehensive_monitor.log for troubleshooting

---

## Key Design Principles

1. **Real Execution**: All operations are real (no simulations)
2. **Continuous Monitoring**: Every 15 minutes, systems verified
3. **Automatic Troubleshooting**: Issues detected and fixed autonomously
4. **No Questions**: Execution continues without user input
5. **Respect Rules**: MAM VIP rules enforced throughout
6. **Real Results**: Audiobooks actually downloaded and added to library

---

## Success Criteria

Workflow is considered successful when:

1. ✓ 10 Science Fiction audiobooks queued
2. ✓ 10 Fantasy audiobooks queued
3. ✓ All 20 books downloaded to hard drive
4. ✓ All 20 books added to AudiobookShelf
5. ✓ All 20 books properly cataloged with metadata
6. ✓ All authors' complete bibliographies identified
7. ✓ Missing books queue created and ready
8. ✓ Final report generated with totals

---

## Getting Help

**View Real-Time Status**:
```bash
python realtime_status_dashboard.py
```

**View Latest Checkpoint**:
```bash
cat monitor_status.json | python -m json.tool
```

**Troubleshoot Issues**:
```bash
tail -200 comprehensive_monitor.log | grep "ERROR\|WARNING\|ISSUE"
```

**Check Database**:
```bash
sqlite3 downloaded_books.db "SELECT status, COUNT(*) FROM books GROUP BY status;"
```

---

**Status**: RUNNING - All systems operational, continuous 15-minute monitoring enabled.
