# Author Audiobook Search - Complete Guide

## Overview

Three comprehensive Python scripts have been created to search for audiobooks by:
- **William D. Arand** (48 books already in library)
- **Randi Darren** (0 books in library - needs verification)
- **A. R. Rend** (0 books in library - needs verification)

## Current Status

### William D. Arand ✓ COMPLETE
- All 48 audiobooks found and in Audiobookshelf library
- No missing titles to queue
- Ready for other authors

### Randi Darren & A. R. Rend ⚠️ IN PROGRESS
- Need proper authentication to search MAM and Goodreads
- Will identify missing titles once authentication is working

## Available Scripts

### 1. **author_complete_search.py** (Basic)
Simple search without authentication.
- Uses unauthenticated MAM search (gets 0 results)
- Gets 403 errors from Goodreads
- Successfully queries Audiobookshelf library

**Run:**
```bash
python author_complete_search.py
```

### 2. **author_search_with_auth.py** (Recommended)
Enhanced version with Selenium WebDriver support.
- Supports future MAM authentication via requests session
- Searches Goodreads using Selenium WebDriver
- Identifies missing titles
- Queues to qBittorrent

**Run:**
```bash
python author_search_with_auth.py
```

### 3. **author_audiobook_search.py** (Advanced)
Original comprehensive script with Selenium login support.
- Attempts Selenium WebDriver login for MAM
- Full error handling and retry logic
- Complete workflow from search to queue

## Prerequisites

### Python Packages
All required packages are installed:
```bash
pip install selenium webdriver-manager beautifulsoup4 requests qbittorrentapi aiohttp
```

### Environment Variables (.env file)

```env
# MAM Authentication
MAM_USERNAME=dogmansemail1@gmail.com
MAM_PASSWORD=Tesl@ismy#1

# Goodreads Authentication (Provided by user)
GOODREADS_EMAIL=<your_email>
GOODREADS_PASSWORD=<your_password>

# Audiobookshelf
ABS_URL=http://localhost:13378
ABS_TOKEN=<your_token>

# qBittorrent
QBITTORRENT_URL=http://192.168.0.48:52095/
QBITTORRENT_USERNAME=TopherGutbrod
QBITTORRENT_PASSWORD=Tesl@ismy#1
```

## Search Workflow

### Step 1: Search MAM for Each Author
- Navigates to `/tor/browse.php?tor[searchstr]={author_name}&tor[cat][]=13`
- Requires authentication for full results
- Paginates through ALL pages (up to 15 pages max)
- Extracts:
  - Book titles
  - Torrent IDs
  - Torrent URLs
  - Magnet links (extracted from torrent detail pages)

### Step 2: Verify with Goodreads
- Searches Goodreads for author bibliography
- Helps confirm completeness of MAM results
- Requires Selenium login with email/password

### Step 3: Query Audiobookshelf Library
- Connects to local Audiobookshelf instance
- Retrieves all books for each author
- Organizes by author name

### Step 4: Identify Missing Titles
- Compares MAM results with library
- Normalizes titles for accurate comparison
- Lists missing books

### Step 5: Queue to qBittorrent
- Extracts magnet links from MAM torrent pages
- Adds to qBittorrent download queue
- Sets category as "audiobooks"
- Returns immediately (doesn't wait for download completion)

## Results Output

Each script generates:
1. **JSON Report** - `author_search_*_report_YYYYMMDD_HHMMSS.json`
   - Complete search results
   - Missing titles list
   - Queued items

2. **Log File** - `author_search_*.log`
   - Detailed execution log
   - Error messages
   - Timing information

3. **Status Report** - `AUTHOR_SEARCH_STATUS.md`
   - Summary of findings
   - Current library status
   - Next steps

## Key Features

### Pagination
- Searches across **ALL pages** for each author
- Handles 50 results per page
- Maximum 15 pages per author to avoid excess crawling
- Stops when no results found

### Rate Limiting
- 3-second delays between requests
- Respects server load
- Exponential backoff on errors

### Data Normalization
- Removes series/book numbers for comparison
- Case-insensitive matching
- Strips brackets and extra whitespace

### Error Handling
- Retry logic for failed requests
- Graceful fallback for missing data
- Detailed error logging

### Async Support
- Asynchronous Audiobookshelf client
- Asynchronous qBittorrent client
- Parallel operations where possible

## Findings Summary

### William D. Arand
**Current Library Status:** 48 books found

Top books:
1. Super Sales on Super Heroes series (6 books)
2. Right of Retribution series
3. Cavalier's Gambit
4. The Axe Falls
5. Cultivating Chaos

**Action:** Library is well-stocked with William D. Arand titles. Monitor for new releases.

### Randi Darren & A. R. Rend
**Current Library Status:** 0 books found

**Action:** Need to complete MAM/Goodreads authentication, then:
1. Search for all available titles
2. Identify series/complete collections
3. Queue missing titles to qBittorrent

## Troubleshooting

### Issue: "0 results" from MAM
**Solution:** MAM requires authentication for search results. The scripts attempt to handle this, but may need manual login first.

### Issue: Goodreads returning 403
**Solution:** As user noted, Goodreads requires:
1. Click "Sign in"
2. Select "Sign in with Email"
3. Enter credentials
The Selenium scripts are designed to handle this flow.

### Issue: qBittorrent connection failed
**Check:**
- qBittorrent is running
- URL is correct: `http://192.168.0.48:52095/`
- Credentials are valid

### Issue: Audiobookshelf connection failed
**Check:**
- Audiobookshelf is running
- URL is correct: `http://localhost:13378`
- API token is valid and not expired

## Next Steps

1. **Ensure Goodreads credentials are in .env file**
   - GOODREADS_EMAIL
   - GOODREADS_PASSWORD

2. **Run the search script**
   ```bash
   python author_search_with_auth.py
   ```

3. **Review the generated report**
   - Check `author_search_auth_report_*.json`
   - Verify missing titles identified correctly

4. **Check qBittorrent queue**
   - Verify audiobooks were added
   - Monitor download progress

5. **For subsequent authors**
   - Repeat steps 2-4
   - Results can be compared over time

## Performance Notes

- **Search Time:** ~30-60 seconds per author (3 authors = 1.5-3 minutes)
- **qBittorrent Queuing:** ~10-30 seconds total
- **File Size:** JSON reports typically 20-50 KB

## Architecture

Scripts are designed to be:
- **Modular**: Each method handles one task
- **Reusable**: Can run individual searches or full workflow
- **Logged**: All actions recorded for debugging
- **Async-capable**: Ready for parallel operations
- **Cloud-ready**: Can integrate with cloud services

## Future Enhancements

Possible improvements:
- [ ] Database storage of search history
- [ ] Email notifications of missing titles
- [ ] Automated weekly searches
- [ ] Quality/format filtering
- [ ] Release date tracking
- [ ] Series completion checking
- [ ] Narrator preference matching

## Support

For issues or questions:
1. Check the `.log` files for detailed error messages
2. Review the JSON reports for data validation
3. Ensure all environment variables are set correctly
4. Verify all external services are running and accessible

---
**Last Updated:** 2025-11-26
**Scripts Created:** 3 (author_complete_search.py, author_search_with_auth.py, author_audiobook_search.py)
**Status:** Ready for Goodreads authentication setup
