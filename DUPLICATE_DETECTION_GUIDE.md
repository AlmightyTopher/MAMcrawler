# Smart Duplicate Detection Guide

## 🎯 How It Works

The automated batch system now **intelligently skips audiobooks you already have** in Audiobookshelf!

### The Algorithm

1. **Connects to Audiobookshelf** at the start of each run
2. **Loads all existing audiobooks** from your library (your 836+ audiobooks)
3. **For each genre:**
   - Queries for audiobooks
   - Checks up to **top 100 results** (configurable)
   - Compares each audiobook title against existing library items
   - **Skips if duplicate** (already in Audiobookshelf)
   - **Selects if new** (not found)
   - Continues until **10 new books** found
4. **Adds only the NEW books** to qBittorrent

### Example Run

**Scenario:** Science Fiction genre has these results:

```
Top 100 Results from website:
#1  Project Hail Mary         -> Already have ✗ Skip
#2  Dune                       -> Already have ✗ Skip
#3  The Three-Body Problem     -> Already have ✗ Skip
#4  Ender's Game               -> New book! ✓ Select (1/10)
#5  Foundation                 -> Already have ✗ Skip
#6  Neuromancer                -> New book! ✓ Select (2/10)
#7  Snow Crash                 -> Already have ✗ Skip
#8  The Forever War            -> New book! ✓ Select (3/10)
... continues checking ...
#45 Seveneves                  -> New book! ✓ Select (10/10)
```

**Result:** Checked 45 books, skipped 35 duplicates, selected 10 NEW books!

## ⚙️ Configuration

### Current Settings

**`audiobook_auto_config.json`:**
```json
{
  "query_settings": {
    "top_n_per_genre": 10,         // Want 10 NEW books
    "max_check_limit": 100,        // Check up to top 100 to find them
    "skip_duplicates": true        // Enable duplicate detection
  }
}
```

### How to Adjust

#### Change Number of New Books

```json
{
  "query_settings": {
    "top_n_per_genre": 20,    // Changed: want 20 NEW books
    "max_check_limit": 100    // Still checks up to top 100
  }
}
```

#### Increase Check Limit

If you have LOTS of books already:

```json
{
  "query_settings": {
    "top_n_per_genre": 10,
    "max_check_limit": 200    // Check up to top 200 results
  }
}
```

**When to increase:**
- You have 500+ SciFi/Fantasy audiobooks already
- Finding fewer than 10 new books per genre
- Want to dig deeper into catalog

#### Disable Duplicate Detection

```json
{
  "query_settings": {
    "skip_duplicates": false    // Download top 10 regardless of duplicates
  }
}
```

**When to disable:**
- Testing the system
- Want to re-download everything
- qBittorrent not accessible

## 🔍 How Titles Are Matched

### Fuzzy Matching Logic

The system uses **smart fuzzy matching** to catch duplicates even if titles don't match exactly:

**Example Matches:**

| Website Result | Your Audiobookshelf Library | Match? |
|---------------|-------------------------|---------|
| `Project Hail Mary` | `Project Hail Mary (Unabridged)` | ✓ Yes |
| `The Expanse 1 - Leviathan Wakes` | `Leviathan Wakes - The Expanse Book 1` | ✓ Yes |
| `Dune` | `Frank Herbert - Dune` | ✓ Yes |
| `Foundation` | `Isaac Asimov - Foundation Series` | ✓ Yes |
| `Neuromancer` | `Neuromancer - William Gibson` | ✓ Yes |

### What Gets Cleaned

Before comparison, titles are cleaned:

1. **Remove audiobook markers:**
   - `(Unabridged)` → removed
   - `(Audiobook)` → removed
   - `Audiobook` → removed

2. **Remove file extensions:**
   - `.mp3`, `.m4b`, `.m4a`, `.flac` → removed

3. **Normalize whitespace:**
   - Multiple spaces → single space
   - Leading/trailing spaces → removed

4. **Case insensitive:**
   - `DUNE` matches `Dune` matches `dune`

### Match Criteria

Two titles are considered duplicates if:

1. **Substantial overlap:**
   - One title is contained in the other
   - OR one torrent name is contained in the other

2. **Similar length:**
   - Titles are within 60% of each other's length
   - Prevents false positives like "The Book" matching "The Book Series Complete Collection"

## 📊 Output & Reporting

### During Execution

**Log output:**
```
[FILTER] Finding 10 new books (checking up to top 100)
  [1] SKIP (duplicate): Project Hail Mary
  [2] SKIP (duplicate): Dune
  [3] SKIP (duplicate): The Three-Body Problem
  [4] SELECT (new): Ender's Game
  [5] SKIP (duplicate): Foundation
  [6] SELECT (new): Neuromancer
  ...
  [45] SELECT (new): Seveneves
[RESULT] Selected 10 new books (skipped 35 duplicates, checked 45 total)
```

### Final Report

**`batch_report_YYYYMMDD_HHMMSS.txt`:**
```
======================================================================
BATCH DOWNLOAD SUMMARY
======================================================================

Genres Processed:    2
Audiobooks Found:    200
Audiobooks Added:    20
Duplicates Skipped:  70
Other Skipped:       0
Errors:              0

----------------------------------------------------------------------
DUPLICATES SKIPPED (70 already in Audiobookshelf):
----------------------------------------------------------------------
  - [Science Fiction] Project Hail Mary
  - [Science Fiction] Dune
  - [Science Fiction] The Three-Body Problem
  - [Science Fiction] Foundation
  - [Fantasy] The Name of the Wind
  - [Fantasy] The Way of Kings
  ... and 64 more duplicates

----------------------------------------------------------------------
DOWNLOADS:
----------------------------------------------------------------------
  - [Science Fiction] Ender's Game
  - [Science Fiction] Neuromancer
  - [Science Fiction] Snow Crash
  ... (20 total new books)
```

## 🎯 Edge Cases Handled

### Case 1: Not Enough New Books

**Scenario:** Genre only has 5 new books in top 100

**What happens:**
- System checks all 100 results
- Finds 5 new books
- Skips 95 duplicates
- Adds the 5 new books (not 10)
- Logs: "Selected 5 new books (wanted 10, checked 100)"

**Solution:** Increase `max_check_limit` to 200 or wait for next week

### Case 2: All Duplicates

**Scenario:** All top 100 are already downloaded

**What happens:**
- System checks all 100 results
- Finds 0 new books
- Skips 100 duplicates
- Adds nothing for this genre
- Logs: "Selected 0 new books (wanted 10, checked 100)"

**This is GOOD!** Prevents re-downloading what you have.

### Case 3: Audiobookshelf Unreachable

**Scenario:** Audiobookshelf not running at 2am Friday, or incorrect credentials

**What happens:**
- Connection fails
- Logs: "Could not connect to Audiobookshelf - duplicate detection disabled"
- Falls back to simple top 10 (no duplicate checking)
- Downloads top 10 regardless (may include duplicates)

**Solution:** Keep Audiobookshelf running 24/7, or verify ABS_URL and ABS_TOKEN in .env file

### Case 4: Similar But Different Books

**Scenario:** "Foundation" vs "Foundation and Empire"

**What happens:**
- Smart length check prevents false positive
- "Foundation" (10 chars) vs "Foundation and Empire" (23 chars)
- Length ratio: 10/23 = 0.43 (below 0.6 threshold)
- **NOT considered duplicate** ✓

Both books are downloaded (correct behavior!)

## 🛠️ Troubleshooting

### Too Many Duplicates Being Downloaded

**Symptom:** Books you already have are being downloaded again

**Causes:**
1. Duplicate detection disabled
2. Audiobookshelf connection failed
3. Titles too different to match

**Solutions:**

1. **Check config:**
   ```json
   {
     "query_settings": {
       "skip_duplicates": true    // Make sure this is true
     }
   }
   ```

2. **Check Audiobookshelf connection:**
   ```bash
   # Verify credentials in .env
   cat .env | grep ABS_
   ```

3. **Review log:**
   ```bash
   # Check audiobook_auto.log for connection errors
   grep "Audiobookshelf" audiobook_auto.log
   ```

4. **Adjust matching threshold:**
   Edit `audiobook_auto_batch.py` line 223:
   ```python
   if len_ratio > 0.6:  # Try 0.5 for looser matching
   ```

### Books Being Skipped That You Don't Have

**Symptom:** New books marked as duplicates incorrectly

**Causes:**
1. Similar title to existing torrent
2. Matching threshold too loose

**Solutions:**

1. **Review duplicate list in report:**
   Check `batch_report_*.txt` → DUPLICATES SKIPPED section

2. **Manually verify:**
   Search your qBittorrent for the title

3. **Adjust matching threshold:**
   Edit `audiobook_auto_batch.py` line 223:
   ```python
   if len_ratio > 0.8:  # Try 0.8 for stricter matching
   ```

4. **Disable temporarily:**
   ```json
   {
     "query_settings": {
       "skip_duplicates": false
     }
   }
   ```

### Want to Re-Download Everything

**Scenario:** Reset your library, want fresh downloads

**Solution:**

```json
{
  "query_settings": {
    "skip_duplicates": false    // Disable duplicate detection
  }
}
```

Or remove torrents from qBittorrent before batch runs.

## 💡 Pro Tips

### 1. Review Duplicate Lists Weekly

Check `batch_report_*.txt` to see what was skipped:
- Confirms duplicate detection is working
- Shows you what books you already have
- Helps you understand your library coverage

### 2. Adjust max_check_limit Based on Library Size

**Small library (< 100 books):**
```json
"max_check_limit": 50    // Top 50 is enough
```

**Medium library (100-500 books):**
```json
"max_check_limit": 100   // Default is good
```

**Large library (500+ books):**
```json
"max_check_limit": 200   // Need to dig deeper
```

### 3. Use with Other Filters

Combine with other features:

```json
{
  "query_settings": {
    "skip_duplicates": true,
    "min_seeders": 5,              // Also require 5+ seeders
    "timespan_preference": "recent" // Prefer recent releases
  }
}
```

This ensures you get:
- New books you don't have
- With good seeder counts
- From recent uploads

### 4. Monitor Duplicate Rates

**Healthy duplicate rates:**
- **First month:** 10-30% duplicates (building library)
- **After 3 months:** 40-60% duplicates (good coverage)
- **After 6 months:** 70-90% duplicates (excellent coverage)

**If duplicates are low (<30%) after 6 months:**
- Increase `top_n_per_genre` to 20
- Add more genres to whitelist
- Increase `max_check_limit` to 200

## 📈 Expected Behavior Over Time

### Week 1: Fresh Start
```
Audiobooks Found:    200
Audiobooks Added:    20
Duplicates Skipped:  0    (nothing downloaded yet)
```

### Week 4: Building Library
```
Audiobooks Found:    200
Audiobooks Added:    18
Duplicates Skipped:  12   (6% duplicate rate - good!)
```

### Week 12: Established Library
```
Audiobooks Found:    200
Audiobooks Added:    10
Duplicates Skipped:  50   (25% duplicate rate - excellent!)
```

### Week 26: Mature Library
```
Audiobooks Found:    200
Audiobooks Added:    8
Duplicates Skipped:  140  (70% duplicate rate - amazing coverage!)
```

### Week 52: Comprehensive Collection
```
Audiobooks Found:    200
Audiobooks Added:    3
Duplicates Skipped:  175  (88% duplicate rate - you own almost everything!)
```

**This is PERFECT behavior!** It means:
- You have excellent library coverage
- System is working correctly
- Only downloading truly new releases
- Not wasting bandwidth on duplicates

---

## 🎊 Summary

**What you get:**
- ✅ Automatic duplicate detection
- ✅ Smart fuzzy title matching
- ✅ Checks up to top 100 results
- ✅ Always finds 10 NEW books (if available)
- ✅ Detailed duplicate reports
- ✅ No wasted downloads
- ✅ No ratio impact from duplicates

**Your Friday at 2am:**
1. System connects to Audiobookshelf
2. Loads your existing 836+ audiobooks from library
3. Queries Science Fiction and Fantasy
4. Checks each result against your library
5. Skips duplicates you already have
6. Selects only NEW books
7. Adds 10-20 new books to qBittorrent
8. Generates detailed report

**Wake up Saturday morning to:**
- Only NEW audiobooks
- Zero duplicates
- Detailed report showing what was skipped
- Perfect library management! 🎧📚
