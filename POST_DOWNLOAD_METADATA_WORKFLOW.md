# Post-Download Metadata & Series Linking Workflow

**Purpose:** After Randi Darren audiobooks finish downloading and import into Audiobookshelf, automatically update metadata and link them into proper series groupings so you can click on a series name and see all books in that series.

**Timeline:** Run these steps after downloads complete and auto-import to Audiobookshelf

---

## Overview of Available Tools

Your codebase has THREE primary systems for metadata management:

### 1. **Database-Level Series Population** (`populate_series_from_metadata.py`)
- **What it does:** Reads series info directly from book metadata in Audiobookshelf database
- **How it works:** Queries the SQLite database and creates series/book links
- **Requirement:** Audiobookshelf MUST be stopped (database cannot be locked)
- **Best for:** Bulk operations after metadata is already correct in books

### 2. **API-Level Metadata Updates** (`update_audiobooks_metadata.py`)
- **What it does:** Fetches all books via Audiobookshelf API, groups by series, updates metadata
- **How it works:** Uses async HTTP API calls to Audiobookshelf
- **Requirement:** Audiobookshelf must be RUNNING
- **Best for:** Direct updates and API-based series population

### 3. **Metadata Enrichment Service** (`metadata_enrichment_service.py`)
- **What it does:** Enriches metadata using Google Books API and ISBN lookups
- **How it works:** Queries external APIs for missing series/author/narrator info
- **Requirement:** Google Books API key (optional but improves accuracy)
- **Best for:** Filling in missing metadata fields for incomplete book records

---

## Step-by-Step Workflow for Randi Darren Books

### Phase 1: Wait for Downloads & Import (Automated)

**What happens:**
1. qBittorrent downloads the 17 queued Randi Darren audiobooks
2. Files auto-import to Audiobookshelf when download completes
3. Audiobookshelf scans folder and indexes the new audiobooks
4. Books appear in your library with basic metadata (filename-based)

**Timeline:** 2-4 weeks depending on seeder availability
**Status:** Monitor qBittorrent for download progress

---

### Phase 2: Verify Books in Library (Manual Check)

**What to do:**
1. Open Audiobookshelf: http://localhost:13378
2. Go to Books library
3. Search for "Randi Darren" or browse authors
4. Verify all 17 books appear (may take some time after download)

**What you'll see:**
- Books listed but metadata may be incomplete or incorrect
- Series names may not be linked together yet
- Titles may show filenames instead of proper titles

---

### Phase 3A: Option 1 - API-Based Update (Recommended for Quick Results)

**Use this if:** You want to update metadata immediately while Audiobookshelf is running

**Command:**
```bash
python update_audiobooks_metadata.py
```

**What it does:**
1. Connects to Audiobookshelf API (must be running)
2. Fetches all books from your library
3. Groups books by existing series metadata
4. Updates each book with proper metadata fields
5. Creates series groupings in the database
6. Generates detailed report showing series organization

**Time:** ~2-3 minutes for full library

**Output:**
```
AUDIOBOOK METADATA UPDATE WITH SERIES LINKING
================================================
Audiobookshelf URL: http://localhost:13378
Database: sqlite:///C:\...

Total Books: 1700+
Books with Series: 1200+
Found X series:
  - Randi Darren Remnant: 3 books
  - Randi Darren Incubus Inc: 2-3 books
  - Randi Darren Wild Wastes: 6 books
  ... etc
```

**Expected result:** Books grouped by series in database, but you may need to verify the series linking is correct

---

### Phase 3B: Option 2 - Database-Level Population (Most Reliable)

**Use this if:** You prefer direct database operations and want maximum control

**Steps:**

1. **Stop Audiobookshelf completely:**
   ```bash
   # Close the Audiobookshelf window or service
   # Wait 10 seconds for database to unlock
   ```

2. **Run the populator:**
   ```bash
   python populate_series_from_metadata.py
   ```

3. **What it does:**
   - Connects to Audiobookshelf SQLite database
   - Reads `seriesName` and `seriesSequence` from each book's metadata JSON
   - Creates series records in the database
   - Links books to series via `bookSeries` junction table
   - Generates detailed statistics

4. **Expected output:**
   ```
   ================================================================================
   AUDIOBOOKSHELF SERIES POPULATOR (METADATA-BASED)
   ================================================================================
   Connected to database successfully
   Found 1700+ books in library

   Step 1: Extracting series from book metadata...
   Found 1250 books with series data
   Found 47 unique series names

   Step 2: Creating series and linking books...
   Processing: Randi Darren Remnant (3 books)
   Processing: Randi Darren Incubus Inc (2 books)
   Processing: Randi Darren Wild Wastes (6 books)
   ...

   ================================================================================
   POPULATION COMPLETE
   ================================================================================
   Total books in library:     1700
   Books with series data:     1250
   Unique series found:        47
   Series created:             35
   Series already existed:     12
   Books linked to series:     1250
   Books already linked:       0
   Errors encountered:         0
   ```

5. **Start Audiobookshelf again**

6. **Result:** Open Audiobookshelf and all Randi Darren books should now be grouped by series!

---

### Phase 3C: Option 3 - Metadata Enrichment (For Missing Data)

**Use this if:** Some books have incomplete metadata (missing authors, narrators, descriptions)

**Command:**
```bash
python metadata_enrichment_service.py
```

**What it does:**
1. Queries Google Books API for each book title
2. Extracts: series name, book position, author, narrator, description
3. Fills in missing fields in Audiobookshelf
4. Matches books to series based on ISBN or title similarity
5. Generates enrichment report

**Prerequisites:**
- Google Books API (free tier is sufficient)
- API key in environment variable (optional)

**When to use:**
- After Phase 3A or 3B, to enhance metadata
- When some books have missing author/narrator info
- To add descriptions from Google Books

---

## Key Metadata Fields Used by Audiobookshelf

When updating books, these fields control series linking:

```json
{
  "title": "Remnant",                          // Book title
  "author": "Randi Darren",                    // Author name
  "series": "Remnant",                         // Series name (THIS is what groups books)
  "seriesSequence": "1",                       // Position in series (1, 2, 3, etc.)
  "narrator": "Michael Kramer",                // Narrator name
  "published": "2020",                         // Year
  "publishedYear": 2020,
  "description": "Book description...",        // Full description
  "genres": ["Science Fiction", "Fantasy"],    // Tags/categories
  "tags": [],                                  // Custom tags
  "language": "en",
  "publisher": "Self-Published"
}
```

**Critical for Series Linking:**
- `series` - Must match exactly across all books in series
- `seriesSequence` - Should be in order (1, 2, 3... or 1.0, 1.5, 2.0 for sub-series)

---

## Expected Series Structure (After Metadata Update)

Based on your Goodreads research, here's what you should see:

### Fully Queued Series (100% Available)

**Wild Wastes** (6 books)
- Wild Wastes #1
- Eastern Expansion (#2)
- Southern Storm (#3)
- Wild Wastes 4
- Wild Wastes 5
- Wild Wastes 6

**System Overclocked** (2 books)
- System Overclocked 2
- System Overclocked 3

### Partially Queued Series

**Fostering Faust** (3 of 4 books)
- Fostering Faust #1 [QUEUED]
- Fostering Faust 2 [QUEUED]
- Fostering Faust 3 [QUEUED]
- ~~Fostering Faust: Compilation~~ [NOT AVAILABLE]

**Remnant** (3 of 4 books)
- Remnant #1 [QUEUED]
- Remnant II #2 [QUEUED]
- Remnant III #3 [QUEUED]
- ~~Remnant: Compilation~~ [NOT AVAILABLE]

**Incubus Inc.** (2-3 of 4 books)
- Incubus Inc. #1 [QUEUED]
- Incubus Inc. II #2 [QUEUED]
- ~~Incubus Inc. III~~ [UNCLEAR - may be included as variation]
- ~~Incubus Inc: Compilation~~ [NOT AVAILABLE]

### Still Missing

**Privateer's Commission** (0 of 2 books)
- ~~Privateer's Commission~~
- ~~Privateer's Commission 2~~

---

## Handling Metadata from Torrents

### Problem: Torrent Files Have Poor Metadata

Audiobooks from torrents often have:
- Missing series information
- Wrong titles (filenames like "01 Randi Darren - Remnant I.m4b")
- Missing narrator information
- No descriptions

### Solution: Metadata Sources (in order of priority)

1. **Goodreads** (what we used to find titles)
   - Search: "Randi Darren Remnant"
   - Extract: Exact title, series name, series position

2. **Google Books** (free API)
   - Searches by ISBN if available
   - Fills in: Description, publisher, publication year

3. **Goodreads API** (optional, requires API key)
   - Gets: Series info, exact book ordering
   - Gets: Narrator information (if available)

4. **Manual Correction** (as backup)
   - Use Audiobookshelf UI to edit individual books
   - Click book → Edit → Update series/author/narrator

---

## Workflow Execution Script (Recommended)

For convenience, here's the recommended order:

```bash
# Step 1: Wait for downloads (monitor qBittorrent)
# [Check qBittorrent status - should show 17 audiobooks downloading]

# Step 2: Verify imports (wait 24-48 hours after downloads complete)
# Open Audiobookshelf and check Books library

# Step 3: Update metadata (choose ONE option below)

# Option A: API-based (keep Audiobookshelf running)
python update_audiobooks_metadata.py

# Option B: Database-based (stop Audiobookshelf first)
# - Stop Audiobookshelf
# - Wait 10 seconds
python populate_series_from_metadata.py
# - Start Audiobookshelf

# Option C: Enrich metadata (optional - run after A or B)
python metadata_enrichment_service.py

# Step 4: Verify series linking
# Open http://localhost:13378
# Search for "Remnant" or "Incubus" to see grouped series
```

---

## Verifying Series Linking Works

### In Audiobookshelf UI:

1. **Go to Books library**
2. **Look for Series column** or click on author
3. **Click on a series name** (e.g., "Remnant")
4. **Should show:** All books in that series listed together
5. **Can sort by:** Series name or book position

### What success looks like:

```
Series: Remnant
├─ Remnant (#1) - Downloaded 2025-12-01
├─ Remnant II (#2) - Downloaded 2025-12-05
└─ Remnant III (#3) - Downloaded 2025-12-10

Series: Wild Wastes
├─ Wild Wastes (#1) - Downloaded 2025-12-02
├─ Eastern Expansion (#2) - Downloaded 2025-12-02
├─ Southern Storm (#3) - Downloaded 2025-12-03
├─ Wild Wastes 4 - Downloaded 2025-12-03
├─ Wild Wastes 5 - Downloaded 2025-12-04
└─ Wild Wastes 6 - Downloaded 2025-12-04
```

---

## Troubleshooting

### Series aren't showing up in Audiobookshelf UI

**Check:**
1. Did you run `populate_series_from_metadata.py` or `update_audiobooks_metadata.py`?
2. Are you looking in the right library? (Books library, not Podcasts)
3. Try refreshing browser or restarting Audiobookshelf

**Fix:**
1. Re-run the metadata update script
2. Check the log file for errors
3. Manually verify a book has `series` field set via Edit Book

### Books aren't showing series field when you click "Edit"

**Cause:** Metadata didn't update properly

**Fix:**
1. Click book → Edit
2. Manually type in Series field: "Remnant"
3. Manually set series sequence: "1" or "2" etc.
4. Click Save
5. Re-run population script to sync other books

### Some books have wrong titles (showing filenames)

**Fix using API method:**
```bash
python update_audiobooks_metadata.py
# This extracts titles from metadata JSON and updates them
```

**Fix manually:**
1. Click book → Edit Book
2. Update Title field with correct title
3. Click Save
4. Re-run scripts to sync

---

## After Series Linking is Complete

### Next Steps:

1. **Verify all 17 books are properly linked to series**
2. **Add any missing metadata:**
   - Narrator names
   - Descriptions
   - Cover art (can drag-drop images)

3. **Mark series as "Completed" if desired:**
   - Some apps show completion badges
   - Track which series you've fully downloaded

4. **Enjoy!** - Click on series to see all books in order

---

## Timeline Summary

| Phase | Action | Time | Status |
|-------|--------|------|--------|
| **1** | Downloads complete | 2-4 weeks | Passive (qBittorrent handles) |
| **2** | Verify in Audiobookshelf | 24-48 hours after | Manual check |
| **3** | Update metadata | ~5 minutes | `update_audiobooks_metadata.py` OR `populate_series_from_metadata.py` |
| **4** | Verify series | 5 minutes | Check UI in browser |
| **5** | Done! | --- | Enjoy organized library |

---

## Additional Resources

**Files in your codebase:**
- `populate_series_from_metadata.py` - Database method
- `update_audiobooks_metadata.py` - API method
- `metadata_enrichment_service.py` - Enrichment method
- `verify_series_metadata.py` - Check if series are populated

**Audiobookshelf Documentation:**
- Web UI: http://localhost:13378
- API: http://localhost:13378/api/
- Metadata fields: `media.metadata.*`

**Goodreads (for manual reference):**
- Used during initial search to find titles
- Can reference if series info is unclear

---

## Final Notes

The metadata workflow is **fully automated** - you don't need to manually update anything if you run the scripts. The scripts handle:

✓ Reading existing book metadata from torrents
✓ Grouping books by series name
✓ Populating series information in database
✓ Creating book-to-series links
✓ Generating verification reports

You just need to:
1. Wait for downloads to complete (passive)
2. Run one command when ready
3. Verify results in UI (2 minutes)

---

**Document Generated:** 2025-11-26
**For:** Randi Darren audiobook series organization
**Status:** Ready to implement after downloads complete
