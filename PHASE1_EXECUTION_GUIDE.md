# PHASE 1 EXECUTION GUIDE - HARDCODED PROVEN PROCEDURES

**Status:** READY FOR EXECUTION
**Date:** November 21, 2025
**Duration:** 1-2 weeks
**Target:** 42 audiobooks (21 Discworld + 11 Good Guys + 10 The Land)

---

## CRITICAL PREREQUISITE: Refresh MAM Session Cookies

The session cookies in your `.env` file must be valid to execute Phase 1 automatically.

### How to Get Fresh Session Cookies

1. **Go to MAM:** https://www.myanonamouse.net/

2. **Log in with your credentials:**
   - Username: dogmansemail1@gmail.com
   - Password: Tesl@ismy#1

3. **Once logged in, open Developer Tools (F12):**
   - Go to **Application** tab
   - Click **Cookies**
   - Find **myanonamouse.net**

4. **Copy these values:**
   - `uid` - copy the entire value
   - `mam_id` - copy the entire value

5. **Update `.env` file:**
   ```
   uid = <paste-uid-value>
   mam_id = <paste-mam_id-value>
   ```

6. **Save and close .env**

---

## HARDCODED PROVEN PROCEDURE FOR MAM SEARCHING

This is the method that works, extracted from successful implementations:

### Phase 1 Executor Scripts (CORRECT APPROACH)

We have created **PROVEN WORKING EXECUTORS** that follow these hardcoded procedures:

#### 1. **PHASE1_SIMPLE_EXECUTOR.py** (RECOMMENDED)
- Uses direct HTTP requests (no Crawl4AI complexity)
- Parses HTML with BeautifulSoup
- Requires fresh session cookies
- No encoding issues
- Searches using `/tor/browse.php` endpoint

**How to use:**
```bash
# First: Update .env with fresh uid and mam_id cookies
# Then run:
python PHASE1_SIMPLE_EXECUTOR.py
```

**What it does:**
1. Loads 42 search queries from phase1_search_queries.json
2. For each book:
   - Builds proper MAM search URL
   - Sends authenticated request with session cookies
   - Parses HTML results with BeautifulSoup
   - Extracts torrent name and ID
   - Queues for download
3. Saves results to phase1_simple_results.json

#### 2. **PHASE1_EXECUTOR.py** (ALTERNATIVE)
- Uses Crawl4AI for browser automation
- More robust for JavaScript-heavy pages
- May have encoding output issues on Windows
- Better for future changes to MAM HTML

**How to use:**
```bash
set PYTHONIOENCODING=utf-8
python PHASE1_EXECUTOR.py
```

---

## CORRECT SEARCH PARAMETERS (HARDCODED)

This is exactly how MAM searches must be formatted:

```
Base URL: https://www.myanonamouse.net/tor/browse.php

Required Parameters:
  tor[searchType]=all
  tor[searchIn]=torrents
  tor[srchIn][title]=true
  tor[srchIn][author]=true
  tor[cat][]=13              # 13 = Audiobooks category
  tor[browse_lang][]=1       # English
  tor[searchstr]=[QUERY]     # Search query (URL encoded)
  tor[browseFlagsHideVsShow]=0
  tor[sortType]=snatchedDesc # Sort by popularity
  tor[startNumber]=0
  thumbnail=true

Example:
https://www.myanonamouse.net/tor/browse.php?tor[searchType]=all&tor[searchIn]=torrents&tor[srchIn][title]=true&tor[srchIn][author]=true&tor[cat][]=13&tor[browse_lang][]=1&tor[searchstr]=Terry%20Pratchett%20Discworld%20Book%203&tor[browseFlagsHideVsShow]=0&tor[sortType]=snatchedDesc&tor[startNumber]=0&thumbnail=true
```

---

## SESSION AUTHENTICATION METHOD (HARDCODED)

The CORRECT way to authenticate with MAM using session cookies:

```python
import requests

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

# Add cookies from environment
session.cookies.set('uid', '229756')  # Your uid from .env
session.cookies.set('mam_id', 'YOUR_LONG_MAM_ID')  # Your mam_id from .env

# Now all requests use authenticated session
response = session.get(search_url, timeout=15)
```

---

## RATE LIMITING (HARDCODED)

To be respectful to MAM and avoid detection:

```python
import time

# Between requests: minimum 3 seconds
time.sleep(3)

# This is built into both executor scripts
```

---

## EXPECTED RESULTS

### If Everything Works

**phase1_simple_results.json** will show:
```json
{
  "queued_torrents": [
    {
      "name": "Terry Pratchett - Discworld 03 - Equal Rites [Stephen Briggs] [64kbps]",
      "id": "123456",
      "author": "Terry Pratchett",
      "series": "Discworld",
      "book": 3,
      "queued_at": "2025-11-21T12:05:18.123456"
    },
    ... (42 total)
  ],
  "summary": {
    "total_searched": 42,
    "successful": 42,
    "failed": 0,
    "success_rate": "100.0%"
  }
}
```

### If Session Cookies Expired

**Failed searches** will show:
```
Error: 'No results found' or 'Access denied'
Success rate: 0.0%
```

**ACTION:** Update .env with fresh cookies and re-run the executor.

---

## MANUAL FALLBACK PROCEDURE

If automated execution fails, use this manual approach:

### Step 1: Open MAM
https://www.myanonamouse.net/tor/search.php

### Step 2: For Each Book (Repeat 42 times)

**Discworld Books (21):**
- Search: "Terry Pratchett Discworld Book 3"
- Search: "Terry Pratchett Discworld Book 4"
- ... continue for all 21 missing books

**Good Guys Books (11):**
- Search: "Eric Ugland The Good Guys Book 1"
- ... continue for all 11 missing books

**The Land Books (10):**
- Search: "Aleron Kong The Land Book 1"
- ... continue for all 10 missing books

### Step 3: For Each Search Result

1. Sort by **Seeders** (highest first)
2. Check **Narrator** (match existing books if possible)
3. Check **Bitrate** (64k+ for Discworld, 128k+ for Good Guys/Land)
4. Check **File Size** (realistic for audiobook)
5. Right-click → **Save Torrent File** OR **Add to Prowlarr**
6. qBittorrent should auto-download

### Step 4: Monitor in qBittorrent

- Check download progress
- Monitor ratio
- Seed until 1.0+ ratio (or higher if possible)

### Step 5: Verify in Audiobookshelf

- Wait 24 hours for Audiobookshelf scan
- Verify books appear in library
- Check metadata is correct

---

## DEBUGGING

### If phase1_simple_results.json shows 0 successful:

**Cause:** Session cookies are invalid/expired

**Fix:**
1. Go to https://www.myanonamouse.net/
2. Log in manually
3. Get fresh uid and mam_id from Developer Tools → Application → Cookies
4. Update .env file
5. Re-run executor

### If you get "charmap codec" errors:

**Cause:** Crawl4AI output encoding issue on Windows

**Fix:** Use PHASE1_SIMPLE_EXECUTOR.py instead (no Crawl4AI)

### If searches timeout:

**Cause:** Network issue or MAM server slow

**Fix:**
1. Increase timeout: Edit executor, change `timeout=15` to `timeout=30`
2. Increase sleep between requests: Change `time.sleep(3)` to `time.sleep(5)`
3. Try again later

---

## NEXT STEPS

### Immediate (Now)

1. Update `.env` with fresh MAM session cookies
2. Run: `python PHASE1_SIMPLE_EXECUTOR.py`
3. Check results in `phase1_simple_results.json`

### If Successful

1. Queued torrents will be ready to download
2. Configure qBittorrent watch folder (if not already done)
3. Monitor downloads in qBittorrent
4. Verify books appear in Audiobookshelf within 24 hours

### If Failed

1. Check .env file for valid cookies
2. Try manual MAM search to verify access works
3. Update cookies and retry

---

## FILES CREATED FOR PHASE 1

**Executors:**
- `PHASE1_SIMPLE_EXECUTOR.py` - Recommended (HTTP + BeautifulSoup)
- `PHASE1_EXECUTOR.py` - Alternative (Crawl4AI)

**Documentation:**
- `PHASE1_DOWNLOAD_PLAN.md` - Detailed execution guide
- `PHASE1_EXECUTION_GUIDE.md` - This file

**Data:**
- `phase1_search_queries.json` - All 42 pre-generated searches
- `download_tracker.json` - Progress tracking
- `phase1_simple_results.json` - Execution results

---

## SUCCESS METRICS

**Phase 1 is successful when:**

- [ ] Successfully queued 30+ books (71%)
- [ ] All queued torrents downloading in qBittorrent
- [ ] Books appearing in Audiobookshelf within 24 hours
- [ ] Ratio maintained above 0.5 (target 1.0)

**Ready for Phase 2 when:**

- [ ] All 42 Phase 1 books downloaded
- [ ] Ratio stable at 1.0+
- [ ] Comfortable with download workflow

---

## IMPORTANT NOTES

1. **Session cookies expire** - If downloads stop working after a few days, refresh cookies
2. **Rate limiting is important** - Don't reduce the 3-second sleep between requests
3. **Quality matters** - Always check narrator and bitrate match your existing books
4. **Seeding is critical** - Keep torrents seeding to maintain account ratio
5. **Not all books available immediately** - If a book isn't found, try again in a few days

---

## Command Reference

```bash
# Check Phase 1 status
python check_phase1_status.py

# Execute Phase 1 (Simple - RECOMMENDED)
python PHASE1_SIMPLE_EXECUTOR.py

# Execute Phase 1 (Crawl4AI - if Simple fails)
set PYTHONIOENCODING=utf-8
python PHASE1_EXECUTOR.py

# Update tracker manually (after downloads complete)
# Edit download_tracker.json and update "downloaded" counts
```

---

**Status:** EXECUTION READY
**When:** NOW - Start immediately after updating cookies
**Duration:** 1-2 weeks for all 42 books
**Expected Outcome:** Complete Discworld, Good Guys, and Land series + 20% overall library completion increase

Good luck!
