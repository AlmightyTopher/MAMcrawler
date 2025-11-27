# Author Audiobook Search & Queue Workflow Template

## Overview
This template documents the successful workflow for searching audiobooks by author across multiple sources and queueing them to qBittorrent with proper categorization.

## Workflow Steps

### Step 1: Goodreads Author Search with Selenium
**Tool:** Selenium WebDriver (Chrome headless mode)
**Process:**
1. Initialize Chrome WebDriver with headless options
2. Navigate to Goodreads author search page
3. Execute pagination loop with configurable max pages
4. On each page:
   - Find all book entries using table row selector: `<tr itemtype="http://schema.org/Book">`
   - Extract title from nested structure: `<a class="bookTitle"><span itemprop="name">`
   - Use BeautifulSoup to parse page source
5. Navigate to next page using XPath: `//a[@rel='next']`
6. Extract all unique titles across all pages
7. Return set of titles for library comparison

**Key HTML Selectors Found:**
- Book rows: `soup.find_all('tr', {'itemtype': 'http://schema.org/Book'})`
- Title link: `book_row.find('a', {'class': 'bookTitle'})`
- Title text: `title_link.find('span', {'itemprop': 'name'}).get_text(strip=True)`
- Next page button: `"//a[@rel='next']"` via XPath

**Timing:** 2-second delays between page loads to avoid throttling

---

### Step 2: Library Comparison Against Audiobookshelf
**Tool:** Audiobookshelf API (async requests)
**Process:**
1. Authenticate with Audiobookshelf using API token from environment
2. Query library in paginated chunks (500 items per request)
3. Continue pagination until all items retrieved
4. Build complete library inventory (1608+ items typical)
5. For each found title:
   - Normalize titles (remove series numbers, punctuation, case conversion)
   - Compare against library using normalized matching
   - Identify missing titles not in library

**API Endpoint:** `/api/libraries/{libraryId}/items?offset={offset}&limit=500`

**Output:** List of titles confirmed missing from library

---

### Step 3: Prowlarr Search Integration
**Tool:** Prowlarr API v1
**Process:**
1. Query Prowlarr search endpoint with author name
2. Parse JSON response for:
   - `title` - full torrent name
   - `downloadUrl` - Prowlarr proxy download link
   - `seeders` - number of active seeders
   - `size` - torrent size in bytes
   - `indexer` - source indexer name
3. Filter results for usable torrents (those with downloadUrl)
4. Store complete metadata for each result

**API Endpoint:** `GET /api/v1/search?query={author_name}&type=search`

**Response Format:** Returns array of torrent objects with metadata

**Key Fields:**
- `downloadUrl`: Proxied download link through Prowlarr
- `protocol`: "torrent" or other protocol type
- `categories`: Array with id and name

---

### Step 4: Queue Torrents to qBittorrent with Category
**Tool:** qBittorrent Web API v2
**Process:**
1. Authenticate with qBittorrent:
   - `POST /api/v2/auth/login`
   - Send `username` and `password` as form data
   - Verify `HTTP 200` response
2. For each torrent from Prowlarr:
   - Download torrent file using `downloadUrl`
   - Extract binary content from response
   - Queue to qBittorrent:
     - `POST /api/v2/torrents/add`
     - Send multipart form with torrent file
     - Include form data: `category={audiobooks}` and `paused=False`
3. Verify response: `HTTP 200` or response text `'Ok.'`
4. Add 0.5-second delay between queue operations (rate limiting)
5. Track successful vs. failed queues

**API Endpoints:**
- Login: `POST /api/v2/auth/login`
- Add torrent: `POST /api/v2/torrents/add`
- Query category: `GET /api/v2/torrents/info?category={category_name}`

**Form Parameters:**
```
files: {torrent_file_bytes}
data: {
  'category': 'audiobooks',
  'paused': False
}
```

---

### Step 5: Verification of Category Assignment
**Tool:** qBittorrent Web API v2
**Process:**
1. Query torrents by category:
   - `GET /api/v2/torrents/info?category=audiobooks`
2. Parse JSON response for array of torrents
3. Verify fields:
   - `name` - torrent name
   - `state` - current state (queuedDL, stalledDL, downloading, etc.)
   - `category` - should equal category specified during add
4. Count total torrents in category
5. Display sample of recently added torrents with state

**Expected States:**
- `queuedDL` - queued, waiting for seeders
- `stalledDL` - stalled, no seeders available
- `downloading` - actively downloading
- `checkingResumeData` - verifying existing data

---

## Data Structures

### Author Search Result
```python
{
    'title': str,           # Book title
    'author': str,          # Author name
    'series': str,          # Series name (if applicable)
    'book_number': int      # Position in series (if applicable)
}
```

### Library Item
```python
{
    'id': str,
    'title': str,
    'author': str,
    'path': str
}
```

### Prowlarr Search Result
```python
{
    'title': str,
    'downloadUrl': str,     # Prowlarr proxy download URL
    'seeders': int,
    'size': int,            # Bytes
    'indexer': str,
    'guid': str,            # Direct link to torrent
    'categories': list      # Category objects
}
```

### qBittorrent Queue Item
```python
{
    'name': str,
    'category': str,
    'state': str,
    'size': int,
    'progress': float
}
```

---

## Environment Requirements

**From .env file (read-only):**
- `GOODREADS_EMAIL` - Email for Goodreads login (not used in successful workflow)
- `GOODREADS_PASSWORD` - Password for Goodreads login (not used in successful workflow)
- `ABS_URL` - Audiobookshelf URL (e.g., `http://localhost:13378`)
- `ABS_TOKEN` - Audiobookshelf API token
- `PROWLARR_URL` - Prowlarr URL (e.g., `http://localhost:9696`)
- `PROWLARR_API_KEY` - Prowlarr API key
- `QBITTORRENT_URL` - qBittorrent URL (e.g., `http://192.168.0.48:52095/`)
- `QBITTORRENT_USERNAME` - qBittorrent username
- `QBITTORRENT_PASSWORD` - qBittorrent password

**VPN Status:** Verify active with: `curl https://api.ipify.org?format=json`

---

## Python Libraries Required

```
selenium==4.x
beautifulsoup4==4.x
requests==2.x
aiohttp==3.x
python-dotenv==0.x
```

---

## Logging & Output

**Log Format:**
```
%(asctime)s - %(levelname)s - %(message)s
```

**Output Files (Optional):**
- JSON report with search results and queue status
- Log file with execution details
- Summary markdown document

---

## Error Handling Implemented

**Goodreads Parsing:**
- Missing title elements → skip row
- Pagination not found → stop page loop
- WebDriver errors → caught and logged, session closed in finally block

**API Calls:**
- HTTP status code checking (200 for success)
- Timeout handling (10-30 second timeouts)
- Response text parsing for edge cases

**qBittorrent Queuing:**
- Verify login before proceeding
- Check HTTP status or 'Ok.' text for successful add
- Handle invalid download URLs gracefully
- Rate limiting between requests

---

## Workflow Options Not Successful

**Methods that did NOT work and should not be used:**

1. **MAM Direct Search via requests library**
   - Returns 403 Forbidden even with VPN
   - Cannot authenticate without browser session
   - Does not work with MAM_ID cookie alone

2. **Selenium-based MAM login**
   - MAM login form elements vary or load dynamically
   - HTML structure not stable for scraping

3. **Goodreads login with Selenium**
   - Not necessary - author search is publicly accessible
   - Adds unnecessary complexity

4. **qBittorrent without category parameter**
   - Torrents added without category remain uncategorized
   - Category MUST be explicitly set during add operation

---

## Reusable Script Template

### Main Execution Function
```python
def run_author_search_workflow(author_name, library_library_id):
    """
    1. Search Goodreads for author
    2. Query Audiobookshelf library
    3. Compare and identify missing
    4. Search Prowlarr
    5. Queue to qBittorrent
    6. Verify category assignment
    """
    # Step 1: Goodreads search
    goodreads_results = search_goodreads_author(author_name)

    # Step 2: Library query
    library_items = query_abs_library(library_id)

    # Step 3: Compare
    missing_titles = identify_missing(goodreads_results, library_items)

    # Step 4: Prowlarr search
    prowlarr_results = search_prowlarr(author_name)

    # Step 5: Queue
    queued_count = queue_to_qbittorrent(prowlarr_results, category='audiobooks')

    # Step 6: Verify
    verify_audiobook_category()

    return {
        'found': len(goodreads_results),
        'missing': len(missing_titles),
        'queued': queued_count
    }
```

---

## Performance Notes

**Typical Timing:**
- Goodreads search (10+ pages): 60+ seconds
- Audiobookshelf library query: <1 second
- Library comparison: <1 second
- Prowlarr search: 1-2 seconds
- qBittorrent queue operations (10 items): 20 seconds
- Verification: <1 second
- **Total end-to-end: ~2 minutes**

**Rate Limiting Applied:**
- 2-second delays between Goodreads page loads
- 0.5-second delays between qBittorrent additions
- 30-second timeout on API calls

---

## Success Criteria

✓ Goodreads pagination captures all author pages
✓ Library comparison matches results accurately
✓ Prowlarr returns results with downloadUrl
✓ All torrents queue successfully to qBittorrent
✓ Torrents appear in specified category
✓ No authentication errors
✓ All steps complete in <3 minutes

---

## Notes for Future Use

- This workflow is author-agnostic - repeat for any author name
- Category name is configurable (tested with 'audiobooks')
- Goodreads max pages configurable (tested with 10-15 pages)
- Prowlarr results may vary based on configured indexers
- qBittorrent queue may show various states (queuedDL, stalledDL, etc.) - all are valid
- Results persist across sessions and will auto-import to library when downloads complete

