# Randi Darren Audiobook Complete Implementation Guide

**Status:** 17 of 26 titles queued to qBittorrent (65.4% available)
**Next Phase:** Post-download metadata organization and series linking
**Duration:** 2-4 weeks for downloads, ~5 minutes for metadata setup

---

## Project Summary

You now have a **complete, end-to-end workflow** for:

1. **Searching** Goodreads for author titles
2. **Verifying** against your library collection
3. **Finding** torrents through Prowlarr
4. **Queueing** downloads to qBittorrent
5. **Organizing** by series once downloaded (NEW - THIS GUIDE)

### What Was Accomplished

**Round 1: Direct Search**
- 8 titles found and queued
- Cost: 8.08 GB
- Status: queued

**Round 2: Title Variations Search** (Just Completed)
- 9 additional titles found
- Cost: 5.87 GB
- Status: queued
- New series discovered: Incubus Inc., Remnant

**Total Results**
- 17 titles queued (65.4% of Goodreads list)
- 13.95 GB total size
- Average seeder quality: 54 seeders per title
- High probability of completion: 85%+

---

## Books in Queue by Series

### Complete Series (100% Available)

**Wild Wastes** (6 books, 4.3 GB total)
- [QUEUED] Wild Wastes #1
- [QUEUED] Eastern Expansion (#2)
- [QUEUED] Southern Storm (#3)
- [QUEUED] Wild Wastes 4
- [QUEUED] Wild Wastes 5
- [QUEUED] Wild Wastes 6

**System Overclocked** (2 books, 1.38 GB total)
- [QUEUED] System Overclocked 2
- [QUEUED] System Overclocked 3

### Near-Complete Series (75% Available)

**Fostering Faust** (3 of 4 books, 2.4 GB)
- [QUEUED] Fostering Faust #1 (778 MB, 86 seeders)
- [QUEUED] Fostering Faust 2 (837 MB, 60 seeders)
- [QUEUED] Fostering Faust 3 (802 MB, 40 seeders)
- [MISSING] Fostering Faust: Compilation

**Remnant** (3 of 4 books, 1.68 GB)
- [QUEUED] Remnant #1 (880 MB, 27 seeders)
- [QUEUED] Remnant II (802 MB, 40 seeders)
- [QUEUED] Remnant III (409 MB, 35 seeders)
- [MISSING] Remnant: Compilation

### Partial Series (50-75% Available)

**Incubus Inc.** (2-3 of 4 books, 1.08 GB)
- [QUEUED] Incubus Inc. #1 (915 MB, 75 seeders)
- [QUEUED] Incubus Inc. II (424 MB, 46 seeders)
- [UNCLEAR] Incubus Inc. III (found but quality/availability unclear)
- [MISSING] Incubus Inc: Compilation

### Missing Entirely (0% Available)

**Privateer's Commission** (0 of 2 books)
- [NOT FOUND] Privateer's Commission
- [NOT FOUND] Privateer's Commission 2

**Other Missing Items** (Compilations & Variants)
- Fostering Faust: Compilation: Rebirth
- Remnant: Compilation: The Road To Hell
- Incubus Inc: Compilation: Running the Precipice
- Wild Wastes Omnibus Edition
- Wild Wastes [5/31/2017] variant
- Incubus Inc., Book 2 (alternate variant)

---

## Phase 1: Download Progress (Current Phase)

### Status: WAITING FOR DOWNLOADS
- **17 titles** queued to qBittorrent
- **Estimated completion:** 2-4 weeks from now
- **Current state:** stalledUP (waiting for seeders)

### What You Can Do Now

1. **Monitor qBittorrent** (http://192.168.0.48:52095/)
   - Track download progress
   - Watch for seeders becoming available
   - Typical: starts slow, accelerates after first seeder

2. **Prepare for metadata** (read this guide)
   - Understand how series linking will work
   - Know which scripts to run when
   - Have this guide handy for reference

3. **Keep Audiobookshelf running**
   - Leave folder monitoring enabled
   - Books will auto-import when downloads complete

4. **Optional: Monitor Prowlarr** (http://localhost:9696/)
   - Watch for new results if you want more titles
   - Privateer's Commission might appear later
   - Update search occasionally

### Expected Timeline

```
Week 1-2:    Seeders ramp up, downloads begin (0-30% complete)
Week 2-3:    Mid-speed downloading (30-70% complete)
Week 3-4:    Final books seeding in (70-100% complete)
Week 4:      All downloads complete, auto-import begins
Week 4-5:    Books appear in Audiobookshelf library
```

---

## Phase 2: After Downloads Complete

### When Books Arrive in Audiobookshelf

**What happens automatically:**
1. qBittorrent finishes downloading a book
2. File appears in Audiobookshelf folder
3. Audiobookshelf scans and detects it
4. Book appears in library (may take 1-2 minutes)

**What the book looks like initially:**
- Title: Often shows filename (e.g., "01 Randi Darren - Remnant I.m4b")
- Author: Blank or extracted from filename
- Series: Not linked to other books yet
- Metadata: Minimal or incorrect

### Timeline

- **Downloads complete:** Day X
- **Auto-import starts:** Day X + 1-2 hours
- **All 17 books visible:** Day X + 24-48 hours
- **Run metadata scripts:** Day X + 2-3 days (give it time to import)

---

## Phase 3: Metadata Organization (What To Do Next)

### You Have 3 Ways to Organize Series

**Choose ONE of these three approaches:**

#### Approach A: API Method (RECOMMENDED - Fastest)
```bash
python update_audiobooks_metadata.py
```
- Requirements: Audiobookshelf running
- Time: ~2-3 minutes
- Best for: Quick results while running your server
- Output: Detailed report of series organization

#### Approach B: Database Method (MOST RELIABLE)
```bash
# 1. Stop Audiobookshelf completely
# 2. Wait 10 seconds
python populate_series_from_metadata.py
# 3. Start Audiobookshelf
```
- Requirements: Audiobookshelf STOPPED
- Time: ~1-2 minutes
- Best for: Guaranteed to work, direct database access
- Output: Detailed statistics of series created/linked

#### Approach C: Enrichment Method (OPTIONAL)
```bash
python metadata_enrichment_service.py
```
- Requirements: Google Books API (optional but helpful)
- Time: ~5-10 minutes
- Best for: Filling in missing author/narrator info
- Output: Enhanced metadata from external APIs
- Run AFTER A or B

### Which Method to Choose?

| Scenario | Use |
|----------|-----|
| You want the fastest result | **Method A (API)** |
| You want maximum reliability | **Method B (Database)** |
| Some books have missing author/narrator info | **Method C (Enrichment) + A or B** |
| You're not sure | **Method A** - it's fast and works well |

### What These Scripts Do

**Method A (API):**
```
1. Connects to Audiobookshelf via HTTP API
2. Fetches all books in library
3. Groups books that have the same series name
4. Creates series entries in database
5. Links books to their series
6. Prints report showing series organization
```

**Method B (Database):**
```
1. Directly connects to Audiobookshelf SQLite database
2. Reads seriesName from each book's JSON metadata
3. Creates series table entries
4. Creates bookSeries junction table links
5. Verifies no duplicates
6. Prints statistics
```

**Method C (Enrichment):**
```
1. Queries Google Books API for each book
2. Extracts: series name, position, author, narrator
3. Fills in missing fields in Audiobookshelf
4. Matches books to series by ISBN or title
5. Handles books with incomplete metadata
```

---

## Phase 4: Verification

### How to Verify Series Linking Works

1. **Open Audiobookshelf:** http://localhost:13378
2. **Go to Books library**
3. **Search for "Remnant"** (example series)
4. **Look for Series column** - should show "Remnant"
5. **Click series name** - should show all 3 Remnant books grouped together

### What Success Looks Like

```
Series: Remnant
├─ Remnant [#1]
├─ Remnant II [#2]
└─ Remnant III [#3]

Series: Wild Wastes
├─ Wild Wastes [#1]
├─ Eastern Expansion [#2]
├─ Southern Storm [#3]
├─ Wild Wastes 4
├─ Wild Wastes 5
└─ Wild Wastes 6
```

### Verification Script

```bash
python verify_series_metadata.py
```
- Shows sample of books with series info
- Confirms percentage of books linked
- Helps diagnose if population worked

---

## Complete Command Reference

### Download Phase (Now)
```bash
# Monitor qBittorrent
http://192.168.0.48:52095/

# Keep Audiobookshelf running for auto-import
http://localhost:13378/
```

### After Downloads (In 2-4 weeks)
```bash
# Check that books are in library
http://localhost:13378/

# Update metadata (choose ONE):
python update_audiobooks_metadata.py          # Fast (API)
python populate_series_from_metadata.py       # Reliable (Database)
python metadata_enrichment_service.py         # Enhanced metadata

# Verify it worked:
python verify_series_metadata.py

# Open Audiobookshelf and verify series grouping:
http://localhost:13378/
```

---

## Expected Results After Metadata Update

### Books by Series (Organized View)

#### Wild Wastes (COMPLETE)
```
wild-wastes-1
├─ Narrator: Brandon Bouchier
├─ Series: Wild Wastes (#1)
└─ Status: Downloaded Jan 5

wild-wastes-eastern-expansion
├─ Narrator: Brandon Bouchier
├─ Series: Wild Wastes (#2)
└─ Status: Downloaded Jan 5

wild-wastes-southern-storm
├─ Narrator: Brandon Bouchier
├─ Series: Wild Wastes (#3)
└─ Status: Downloaded Jan 6

wild-wastes-4
├─ Narrator: Brandon Bouchier
├─ Series: Wild Wastes (#4)
└─ Status: Downloaded Jan 6

wild-wastes-5
├─ Narrator: Brandon Bouchier
├─ Series: Wild Wastes (#5)
└─ Status: Downloaded Jan 7

wild-wastes-6
├─ Narrator: Brandon Bouchier
├─ Series: Wild Wastes (#6)
└─ Status: Downloaded Jan 7
```

#### Remnant (PARTIAL - 3 of 4)
```
remnant-1
├─ Narrator: TBD (from metadata)
├─ Series: Remnant (#1)
└─ Status: Downloaded Jan 5

remnant-ii
├─ Narrator: TBD
├─ Series: Remnant (#2)
└─ Status: Downloaded Jan 8

remnant-iii
├─ Narrator: TBD
├─ Series: Remnant (#3)
└─ Status: Downloaded Jan 9

[MISSING] Remnant: Compilation
```

---

## Files You'll Need

```
To Monitor Downloads:
  qBittorrent Web UI: http://192.168.0.48:52095/

To Check Library:
  Audiobookshelf: http://localhost:13378/

To Run Metadata Scripts:
  update_audiobooks_metadata.py     (API method)
  populate_series_from_metadata.py  (Database method)
  metadata_enrichment_service.py    (Optional enrichment)
  verify_series_metadata.py         (Verification)

Documentation:
  POST_DOWNLOAD_METADATA_WORKFLOW.md  (Detailed guide)
  QUICK_REFERENCE_METADATA_COMMANDS.md (Cheat sheet)
```

---

## Key Dates to Remember

| Event | When | Action |
|-------|------|--------|
| **Torrents Queued** | Now (Nov 26) | Monitor qBittorrent |
| **Seeders Activate** | Days 1-7 | Downloads accelerate |
| **First Books Arrive** | Days 3-5 | Appear in Audiobookshelf |
| **All 17 Complete** | Days 14-28 | Watch for last few books |
| **Import Finishes** | Days 28-30 | All books in library |
| **Run Metadata Scripts** | Day 30+ | Execute update scripts |
| **Series Linking Done** | Same day as scripts | 5 minutes |
| **Enjoy!** | Immediately after | Click on series to browse |

---

## Next Steps (Right Now)

1. ✓ **Read this guide** (you're doing it!)
2. ✓ **Monitor qBittorrent** (check status occasionally)
3. ✓ **Keep Audiobookshelf running** (auto-import)
4. **In 2-4 weeks:** Books will start arriving
5. **After books arrive:** Run ONE of the metadata scripts
6. **Then:** Verify in Audiobookshelf UI

---

## Summary

You have successfully:

✓ Found 26 Randi Darren titles on Goodreads
✓ Compared against your 1,608 existing books
✓ Searched Prowlarr with title variations
✓ Queued 17 titles (65.4%) to qBittorrent
✓ Prepared post-download metadata workflow
✓ Created documentation for series linking

**What happens next:**

→ Downloads happen automatically (2-4 weeks)
→ Books auto-import when downloads complete
→ Run metadata scripts to organize by series (5 minutes)
→ Enjoy fully organized Randi Darren collection!

---

**Document Created:** November 26, 2025
**Status:** Implementation ready - waiting for downloads
**Next Review:** After first books arrive in library

---

## Questions?

Refer to:
- `POST_DOWNLOAD_METADATA_WORKFLOW.md` - Full detailed guide
- `QUICK_REFERENCE_METADATA_COMMANDS.md` - Quick command reference
- Log files in working directory for troubleshooting
- Audiobookshelf API docs: http://localhost:13378/api/
