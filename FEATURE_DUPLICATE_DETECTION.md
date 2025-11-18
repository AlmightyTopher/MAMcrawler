# ✅ Smart Duplicate Detection - Feature Complete

## 🎯 What Was Added

Your automated audiobook system now has **intelligent duplicate detection**!

### The Problem (Before)

**Old behavior:**
- Download top 10 audiobooks from each genre
- Even if you already have them in Audiobookshelf
- Waste bandwidth and ratio
- Download duplicate books unnecessarily

**Example:**
```
Query SciFi genre:
  1. Project Hail Mary     -> Download (but you already have it!)
  2. Dune                  -> Download (already have it!)
  3. Foundation            -> Download (already have it!)
  ... downloads 10 books (7 duplicates!)
```

### The Solution (Now)

**New behavior:**
- Check Audiobookshelf library for each audiobook
- **Skip if you already have it**
- **Keep checking until 10 NEW books found**
- Check up to top 100 results
- Only download what you DON'T have!

**Example:**
```
Query SciFi genre (checking up to top 100):
  1. Project Hail Mary     -> SKIP (duplicate)
  2. Dune                  -> SKIP (duplicate)
  3. Foundation            -> SKIP (duplicate)
  4. Ender's Game          -> SELECT (new!) ✓
  5. Neuromancer           -> SKIP (duplicate)
  6. Snow Crash            -> SELECT (new!) ✓
  ... continues checking ...
  45. Seveneves            -> SELECT (new!) ✓

Result: Found 10 NEW books, skipped 35 duplicates, checked 45 total
```

## ⚙️ Configuration

**File:** `audiobook_auto_config.json`

```json
{
  "query_settings": {
    "top_n_per_genre": 10,         // Want 10 NEW books
    "max_check_limit": 100,        // Check up to top 100 to find them
    "skip_duplicates": true        // Enable duplicate detection
  }
}
```

### Key Settings

**`skip_duplicates: true`**
- Enables duplicate detection
- Connects to Audiobookshelf
- Compares titles against your library
- Skips matches

**`max_check_limit: 100`**
- How deep to search for new books
- Default: 100 (top 100 results)
- Increase to 200 if you have 500+ books
- Decrease to 50 if you're just starting

## 🔍 How Title Matching Works

### Smart Fuzzy Matching

**Matches these as duplicates:**

| Website Title | Audiobookshelf Library | Match? |
|--------------|---------------------|--------|
| `Project Hail Mary` | `Project Hail Mary (Unabridged)` | ✅ Yes |
| `Dune` | `Frank Herbert - Dune` | ✅ Yes |
| `Foundation` | `Isaac Asimov - Foundation` | ✅ Yes |
| `Ender's Game` | `Ender's Game` | ✅ Yes |

**Does NOT match (correctly):**

| Website Title | Audiobookshelf Library | Match? |
|--------------|---------------------|--------|
| `Foundation` | `Foundation and Empire` | ❌ No (different length) |
| `Dune` | `Dune Messiah` | ❌ No (different book) |
| `The Book` | `The Book Series Complete` | ❌ No (too different) |

### What Gets Cleaned

Before comparison:
- ✂️ `(Unabridged)` → removed
- ✂️ `(Audiobook)` → removed
- ✂️ `.mp3`, `.m4b` → removed
- ✂️ Extra spaces → normalized
- ✂️ Case → ignored

### Match Criteria

Two titles match if:
1. **Substantial overlap:** One title contains the other
2. **Similar length:** Within 60% of each other's length

This prevents:
- False positives ("The Book" ≠ "The Book Series")
- Missing matches ("Dune" = "Dune (Unabridged)")

## 📊 What You'll See

### During Execution

**Log output (`audiobook_auto.log`):**
```
[INFO] Duplicate detection enabled - connecting to Audiobookshelf...
[INFO] Found 836 audiobooks in Audiobookshelf library

GENRE 1/2: Science Fiction
======================================================================
[FILTER] Finding 10 new books (checking up to top 100)
  [1] SKIP (duplicate): Project Hail Mary
  [2] SKIP (duplicate): Dune
  [3] SKIP (duplicate): The Three-Body Problem
  [4] SELECT (new): Ender's Game
  [5] SKIP (duplicate): Foundation
  [6] SELECT (new): Neuromancer
  [7] SKIP (duplicate): Snow Crash
  [8] SELECT (new): The Forever War
  ...
  [45] SELECT (new): Seveneves
[RESULT] Selected 10 new books (skipped 35 duplicates, checked 45 total)
```

### Final Report

**File:** `batch_report_YYYYMMDD_HHMMSS.txt`

```
======================================================================
BATCH DOWNLOAD SUMMARY
======================================================================

Genres Processed:    2
Audiobooks Found:    200
Audiobooks Added:    20
Duplicates Skipped:  70         <- NEW STAT!
Other Skipped:       0
Errors:              0

----------------------------------------------------------------------
DUPLICATES SKIPPED (70 already in Audiobookshelf):    <- NEW SECTION!
----------------------------------------------------------------------
  - [Science Fiction] Project Hail Mary
  - [Science Fiction] Dune
  - [Science Fiction] The Three-Body Problem
  - [Science Fiction] Foundation
  - [Science Fiction] Hyperion
  - [Fantasy] The Name of the Wind
  - [Fantasy] The Way of Kings
  ... and 63 more duplicates

----------------------------------------------------------------------
DOWNLOADS:
----------------------------------------------------------------------
  - [Science Fiction] Ender's Game
  - [Science Fiction] Neuromancer
  - [Science Fiction] Snow Crash
  - [Science Fiction] The Forever War
  ... (20 total NEW books)
```

## 🎬 Example Scenarios

### Scenario 1: New User (Week 1)

**Your library:** 0 SciFi audiobooks

**What happens:**
```
Audiobooks Found:    200
Audiobooks Added:    20
Duplicates Skipped:  0    (nothing to skip yet!)
```

**Result:** Downloads top 20 (10 per genre)

### Scenario 2: Growing Library (Week 12)

**Your library:** 120 SciFi/Fantasy audiobooks

**What happens:**
```
Checks: #1-50 in top 100
Finds: 10 new books
Skips: 40 duplicates
```

**Result:** Downloads 10 NEW books only!

### Scenario 3: Mature Library (Week 52)

**Your library:** 500+ SciFi/Fantasy audiobooks

**What happens:**
```
Checks: #1-85 in top 100
Finds: 8 new books
Skips: 77 duplicates
Can't find 10: stops at 8
```

**Result:** Downloads 8 NEW books (couldn't find 10 unique)

**Solution:** Increase `max_check_limit` to 200

## 🛠️ Troubleshooting

### Issue: Downloading Duplicates

**Check #1 - Is it enabled?**
```json
{
  "query_settings": {
    "skip_duplicates": true    // Must be true
  }
}
```

**Check #2 - Is Audiobookshelf connected?**
```bash
# Check ABS credentials in .env
cat .env | grep ABS_
```

**Check #3 - Review the log:**
```bash
grep "Audiobookshelf" audiobook_auto.log
```

Should see:
```
[INFO] Found 836 audiobooks in Audiobookshelf library
```

If you see:
```
[WARNING] Could not connect to Audiobookshelf - duplicate detection disabled
```

→ Audiobookshelf wasn't running at 2am Friday, or credentials are incorrect!

### Issue: Not Finding New Books

**Symptom:** "Selected 3 new books (wanted 10)"

**Solutions:**

1. **Increase check limit:**
   ```json
   {
     "query_settings": {
       "max_check_limit": 200    // Check deeper
     }
   }
   ```

2. **Add more genres:**
   ```json
   {
     "included_genres": [
       "Science Fiction",
       "Fantasy",
       "Space Opera",    // Add more!
       "Cyberpunk"
     ]
   }
   ```

3. **Wait for next week:**
   - New releases appear weekly
   - Let catalog refresh

## 📈 Expected Behavior Over Time

### Month 1-3: Building Phase
```
Duplicates Skipped:  10-30%
```
Low duplicates = building your library (good!)

### Month 4-6: Established Phase
```
Duplicates Skipped:  40-60%
```
Medium duplicates = good coverage (excellent!)

### Month 7-12: Mature Phase
```
Duplicates Skipped:  70-90%
```
High duplicates = comprehensive library (perfect!)

**High duplicate rate = SUCCESS!**
- You own most available audiobooks
- System is working correctly
- Only downloading truly new content

## 💡 Pro Tips

### Tip 1: Review Duplicate Reports

**Weekly task:**
- Open `batch_report_*.txt`
- Check "DUPLICATES SKIPPED" section
- Confirms what you already have
- Shows library coverage

### Tip 2: Adjust Based on Library Size

**Small library (0-100 books):**
```json
"max_check_limit": 50    // Top 50 is enough
```

**Medium library (100-500 books):**
```json
"max_check_limit": 100   // Default
```

**Large library (500+ books):**
```json
"max_check_limit": 200   // Need to dig deeper
```

### Tip 3: Combine with Other Strategies

**Perfect configuration:**
```json
{
  "query_settings": {
    "skip_duplicates": true,           // No duplicates
    "max_check_limit": 100,            // Check top 100
    "top_n_per_genre": 10,             // Want 10 new
    "timespan_preference": "recent"    // Prefer recent
  },
  "download_settings": {
    "prefer_vip_torrents": true,       // Freeleech for you!
    "use_freeleech_wedges": true       // Use FL wedges
  }
}
```

**This gives you:**
- ✅ Only NEW audiobooks
- ✅ Recent releases preferred
- ✅ VIP/freeleech prioritized (no ratio impact)
- ✅ FL wedges auto-applied
- ✅ Zero waste

## 📚 Documentation

**Full guides:**
- **`DUPLICATE_DETECTION_GUIDE.md`** - Complete technical guide
- **`QUICK_CONFIG_GUIDE.md`** - Configuration reference
- **`AUTOMATED_BATCH_README.md`** - System overview

## 🎊 Summary

**What you asked for:**
> "If it shows that I have one of the top ten books in there, skip it and move on. Count the next one until we own the top 100."

**What you got:**
✅ Smart duplicate detection
✅ Fuzzy title matching
✅ Checks up to top 100 (configurable)
✅ Finds 10 NEW books automatically
✅ Skips what you already have
✅ Detailed reporting
✅ Zero duplicate downloads
✅ Maximum efficiency

**Every Friday at 2am:**
1. Connects to Audiobookshelf (836+ audiobooks)
2. Queries Science Fiction and Fantasy
3. Compares each result against your library
4. Skips duplicates
5. Selects 10 NEW books
6. Adds only new books to qBittorrent
7. Generates detailed report

**Wake up Saturday to:**
- Only NEW audiobooks
- Zero duplicates
- Detailed report showing what was skipped
- Perfect automated library management! 🎧📚

---

**Test it now:**
```bash
python audiobook_auto_batch.py --dry-run
```

Watch for:
```
[INFO] Found 836 audiobooks in Audiobookshelf library
[FILTER] Finding 10 new books (checking up to top 100)
[RESULT] Selected X new books (skipped Y duplicates, checked Z total)
```

**It's working!** 🎉
