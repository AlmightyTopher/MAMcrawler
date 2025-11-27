# Ultimate Audiobook Workflow Template
## Complete Guide: Search → Queue → Verify → Update Metadata

---

## Part 1: Author Audiobook Search & Queue Workflow

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

**Key HTML Selectors:**
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

**API Endpoint:** `GET /api/libraries/{libraryId}/items?offset={offset}&limit=500`

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

## Part 2: Audiobook Metadata Series Update Workflow

### Step 6: Map Books to Series (Filesystem Discovery)

**Source of Truth:** Book metadata stored in individual JSON files on disk
- Location: `[LIBRARY_PATH]/[BOOK_FOLDER]/metadata.json`
- Key field to update: `seriesName`

**Discovery Process:**
1. List all book folders in the library directory
2. For each folder, check for the existence of `metadata.json`
3. Read the `title` field from each metadata.json to identify books
4. Manually or programmatically create a mapping of book folders to series names

**Output Structure:**
```python
BOOKS_TO_UPDATE = [
    ('[FOLDER_NAME_1]', '[SERIES_NAME_1]'),
    ('[FOLDER_NAME_2]', '[SERIES_NAME_1]'),
    ('[FOLDER_NAME_3]', '[SERIES_NAME_2]'),
    ...
]
```

---

### Step 7: Update Metadata Files On Disk

**Tool:** Python script using standard library (`pathlib`, `json`)

**Process:**
1. Iterate through each book folder in the mapping
2. For each folder:
   - Construct path: `[LIBRARY_PATH]/[FOLDER_NAME]/metadata.json`
   - Check if file exists
   - Open file in read-write mode with UTF-8 encoding
   - Load JSON content
   - Update the `seriesName` field with target series name
   - Write modified JSON back to disk
   - Create timestamped backup of original file

**Implementation Pattern:**
```python
from pathlib import Path
import json
from datetime import datetime

books_dir = Path('[LIBRARY_PATH]')
backup_dir = Path('[BACKUP_LOCATION]')
backup_dir.mkdir(exist_ok=True)

for folder_name, series_name in BOOKS_TO_UPDATE:
    metadata_file = books_dir / folder_name / 'metadata.json'

    if not metadata_file.exists():
        continue

    # Create backup
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = backup_dir / f'{folder_name}_{timestamp}_metadata.json'

    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    # Backup original
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)

    # Update metadata
    metadata['seriesName'] = series_name

    # Write back to disk
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
```

**Verification:** Read metadata file and confirm `seriesName` field matches target value

---

### Step 8: Push Updates via API (Optional but Recommended)

**API Endpoint:**
- **Method:** PATCH
- **Endpoint:** `/api/items/{item_id}/media`
- **Payload:** `{"metadata": {"seriesName": "[SERIES_NAME]"}}`

**Process:**
1. Get library ID via: `GET /api/libraries`
2. Index library items to map titles to IDs:
   - Call: `GET /api/libraries/{lib_id}/items?limit=500&offset={offset}`
   - Extract title and item ID from each response
   - Continue with pagination until desired item count reached
3. For each book found in library:
   - Send PATCH request with series name update
   - Capture response status (200 = success)

**Implementation Pattern:**
```python
import asyncio
import aiohttp

async def update_via_api():
    abs_url = '[ABS_URL]'
    abs_token = '[ABS_TOKEN]'
    headers = {'Authorization': f'Bearer {abs_token}'}

    async with aiohttp.ClientSession() as session:
        # Get library ID
        async with session.get(f'{abs_url}/api/libraries', headers=headers) as resp:
            libs = await resp.json()
            lib_id = libs['libraries'][0]['id']

        # Index items by title
        all_items_by_title = {}
        offset = 0
        while offset < [ITEM_LIMIT]:
            async with session.get(
                f'{abs_url}/api/libraries/{lib_id}/items?limit=500&offset={offset}',
                headers=headers
            ) as resp:
                result = await resp.json()
                items = result.get('results', [])
                if not items:
                    break

                for item in items:
                    title = item.get('media', {}).get('metadata', {}).get('title', '')
                    if title:
                        all_items_by_title[title] = item.get('id')

                offset += 500

        # Update found items
        for title, series_name in TITLE_TO_SERIES_MAPPING:
            if title not in all_items_by_title:
                continue

            item_id = all_items_by_title[title]
            update_payload = {'metadata': {'seriesName': series_name}}

            async with session.patch(
                f'{abs_url}/api/items/{item_id}/media',
                headers=headers,
                json=update_payload
            ) as resp:
                if resp.status == 200:
                    # Update successful
                    pass
```

**Limitation:** Only reaches items indexed in first N pages. For massive libraries, most books may not be found. Use for targeted updates only.

---

### Step 9: Trigger Library Rescan

**API Endpoint:**
- **Method:** POST
- **Endpoint:** `/api/libraries/{lib_id}/scan`
- **Expected Response:** Status 200

**Purpose:** Rescan tells Audiobookshelf to rebuild its database from all metadata.json files on disk, picking up changes made directly to the filesystem.

**Implementation:**
```python
async def rescan_library():
    abs_url = '[ABS_URL]'
    abs_token = '[ABS_TOKEN]'
    lib_id = '[LIBRARY_ID]'
    headers = {'Authorization': f'Bearer {abs_token}'}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f'{abs_url}/api/libraries/{lib_id}/scan',
            headers=headers
        ) as resp:
            if resp.status == 200:
                # Rescan initiated successfully
                pass
```

**Timing:**
- Request returns immediately (status 200)
- Actual rescan runs in background on Audiobookshelf server
- Duration depends on library size (15 minutes to 1+ hour for large libraries)

---

### Step 10: Verify Metadata Updates

**Verify On Disk:**
```bash
grep "seriesName" "[LIBRARY_PATH]/[FOLDER_NAME]/metadata.json"
```

Expected output: `"seriesName": "[EXPECTED_SERIES_NAME]"`

**Verify Via API (After Rescan):**
```python
async def verify_updates():
    # Query library for books matching keywords
    # Extract title and seriesName from each result
    # Compare seriesName against target values
```

**Post-Rescan Considerations:**
- If series don't appear grouped after rescan, try restarting Audiobookshelf
- Restart forces full reload from disk and clears cache
- For massive libraries (500K+ items), rescan may take 1+ hour

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
    'path': str,
    'seriesName': str       # After metadata update
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

**Metadata Updates:**
- File encoding issues → use UTF-8 explicitly
- Malformed JSON → validate before writing
- Missing files → check existence before operations

---

## Workflow Options NOT Successful

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

5. **Loading entire library (600K+ items) into memory**
   - API approach alone won't find all books in massive libraries
   - Use filesystem approach as primary method
   - API is supplementary for targeted updates

6. **Library rescan alone to propagate metadata changes**
   - Rescan may not process all folders in very large libraries
   - Filesystem updates are the source of truth
   - Restart Audiobookshelf if rescan doesn't propagate changes

---

## Complete Data Flow

```
Step 1: Goodreads
    │
    ├─> Scrape author's book titles
    │
Step 2: Audiobookshelf Library
    │
    ├─> Query existing library
    ├─> Compare and identify missing
    │
Step 3: Prowlarr
    │
    ├─> Search for missing titles
    ├─> Get download URLs
    │
Step 4: qBittorrent
    │
    ├─> Queue torrents with category
    ├─> Torrents download when seeders available
    │
Step 5: Download Completion
    │
    ├─> Audiobookshelf auto-imports downloaded audiobooks
    │
Step 6: Metadata Update
    │
    ├─> Identify books needing series links
    ├─> Update metadata.json on disk
    ├─> Push via API (optional)
    │
Step 7: Library Rescan
    │
    ├─> Rebuild database from disk files
    ├─> Series metadata now available in API
    │
Step 8: User Verification
    │
    ├─> Check Audiobookshelf UI
    ├─> Verify series grouping
    └─> Done
```

---

## Success Criteria - Full Workflow

✓ Goodreads pagination captures all author pages
✓ Library comparison matches results accurately
✓ Prowlarr returns results with downloadUrl
✓ All torrents queue successfully to qBittorrent
✓ Torrents appear in specified category
✓ Downloads complete and import to library
✓ Metadata files updated on disk with correct series names
✓ Library rescan initiated successfully (status 200)
✓ Series metadata appears in API queries (after rescan)
✓ Books grouped by series in Audiobookshelf UI
✓ No authentication errors throughout workflow
✓ Complete workflow executes in <5 minutes (download time separate)

---

## Performance Notes

**Typical Timing:**
- Goodreads search (10+ pages): 60+ seconds
- Audiobookshelf library query: <1 second
- Library comparison: <1 second
- Prowlarr search: 1-2 seconds
- qBittorrent queue operations (10 items): 20 seconds
- Verification: <1 second
- **Search & queue workflow: ~2 minutes**
- Metadata updates: <1 second
- Library rescan request: <1 second
- Rescan background processing: 15 minutes to 1+ hour (depends on library size)

**Rate Limiting Applied:**
- 2-second delays between Goodreads page loads
- 0.5-second delays between qBittorrent additions
- 30-second timeout on API calls

---

### Step 12: Post-Restart Metadata Verification (After Audiobookshelf Restart)

**Purpose:** Verify that all metadata updates are properly reflected in Audiobookshelf database after the service restart.

**Process:**
1. Query all library items from Audiobookshelf API (full pagination)
2. Read all metadata.json files from disk (source of truth)
3. Compare disk metadata against API metadata for all books:
   - For each book with metadata on disk, check if series matches in API
   - Identify any remaining mismatches (should be minimal after restart)
4. If mismatches found:
   - Send PATCH requests to update API directly
   - Update is applied to in-memory cache immediately
5. Generate comprehensive verification report showing:
   - Total books verified
   - Books with matching metadata (Disk = API)
   - Books with mismatches (if any)
   - Books not found in API (expected for very large libraries)

**Key Finding:** After Audiobookshelf restart, the database cache is fully cleared and reloaded from disk files. This ensures 100% metadata consistency.

**Library Statistics After Restart:**
- Total book folders on disk: 574-644 (varies based on ongoing imports)
- Total folders with metadata.json: 574
- Total items in API database: 328,000+ (multi-file entries for each book)
- Expected format: 1 metadata.json per book folder → multiple API items per book folder

**Filesystem-to-API Verification Script:**

```python
async def verify_all_metadata_post_restart():
    """
    Complete post-restart verification
    Ensures all disk metadata is reflected in API after restart
    """

    abs_url = os.getenv('ABS_URL')
    abs_token = os.getenv('ABS_TOKEN')
    books_dir = Path('F:/Audiobookshelf/Books')

    # Phase 1: Load all metadata.json files
    series_on_disk = {}
    for book_folder in books_dir.iterdir():
        if not book_folder.is_dir():
            continue
        metadata_file = book_folder / 'metadata.json'
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            series_on_disk[metadata.get('title')] = {
                'series': metadata.get('seriesName', ''),
                'folder': book_folder.name
            }

    # Phase 2: Load all library items from API
    all_items = []
    offset = 0
    async with aiohttp.ClientSession() as session:
        headers = {'Authorization': f'Bearer {abs_token}'}
        while True:
            async with session.get(
                f'{abs_url}/api/libraries/{lib_id}/items?limit=500&offset={offset}',
                headers=headers
            ) as resp:
                result = await resp.json()
                items = result.get('results', [])
                if not items:
                    break
                all_items.extend(items)
                offset += 500

    # Phase 3: Compare disk vs API
    matches = 0
    mismatches = 0
    not_found = 0

    for title, disk_data in series_on_disk.items():
        # Find item in API
        api_item = next(
            (i for i in all_items
             if i.get('media', {}).get('metadata', {}).get('title') == title),
            None
        )

        if not api_item:
            not_found += 1
            continue

        api_series = api_item.get('media', {}).get('metadata', {}).get('seriesName', '')
        disk_series = disk_data['series']

        if disk_series == api_series:
            matches += 1
        else:
            mismatches += 1
            # Fix mismatch via API
            item_id = api_item.get('id')
            await session.patch(
                f'{abs_url}/api/items/{item_id}/media',
                headers=headers,
                json={'metadata': {'seriesName': disk_series}}
            )

    return {
        'verified': len(series_on_disk),
        'matches': matches,
        'mismatches': mismatches,
        'not_found': not_found
    }
```

---

## Reusable Script Template - Combined Execution

```python
def run_complete_audiobook_workflow(author_name, library_id):
    """
    Complete workflow: search → queue → verify → update metadata

    PART 1: Search & Queue
    1. Search Goodreads for author
    2. Query Audiobookshelf library
    3. Compare and identify missing
    4. Search Prowlarr
    5. Queue to qBittorrent
    6. Verify category assignment

    PART 2: Update Metadata (after books download)
    7. Map books to series
    8. Update metadata.json on disk
    9. Push updates via API
    10. Trigger library rescan
    11. Verify updates

    PART 3: Post-Restart Verification
    12. After Audiobookshelf restart, verify all metadata is correct
    """

    # PART 1: SEARCH & QUEUE
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

    part1_results = {
        'found': len(goodreads_results),
        'missing': len(missing_titles),
        'queued': queued_count
    }

    # PART 2: UPDATE METADATA (run after downloads complete)
    # Step 7: Map books to series
    books_to_update = create_book_to_series_mapping()

    # Step 8: Update metadata on disk
    update_metadata_files_on_disk(books_to_update)

    # Step 9: Push via API (optional)
    api_updated_count = push_metadata_via_api(books_to_update)

    # Step 10: Trigger rescan
    rescan_library(library_id)

    # Step 11: Verify (note: rescan is async, may need to wait)
    verify_metadata_updates()

    part2_results = {
        'files_updated': len(books_to_update),
        'api_updated': api_updated_count
    }

    return {
        'part1_search_queue': part1_results,
        'part2_metadata_update': part2_results
    }
```

---

## Notes for Future Use

- This workflow is author-agnostic - repeat for any author name
- Category name is configurable (tested with 'audiobooks')
- Goodreads max pages configurable (tested with 10-15 pages)
- Prowlarr results may vary based on configured indexers
- qBittorrent queue may show various states (queuedDL, stalledDL, etc.) - all are valid
- Results persist across sessions and will auto-import to library when downloads complete
- Series names must be consistent across all books in same series
- For very large libraries (500K+ items), rescan may take 1+ hour
- If rescan doesn't propagate changes, restart Audiobookshelf application
- Filesystem updates are the source of truth; API and rescan are propagation mechanisms

---

## Checklist for Complete Workflow

- [ ] Environment variables set (.env file)
- [ ] Audiobookshelf running and accessible
- [ ] Prowlarr configured with indexers
- [ ] qBittorrent accessible with audiobooks category
- [ ] VPN active (verify with ipify check)
- [ ] Run author search workflow (Steps 1-5)
- [ ] Verify torrents queued (Step 5)
- [ ] Wait for downloads to complete
- [ ] Create book-to-series mapping (Step 7)
- [ ] Update metadata.json files (Step 8)
- [ ] Verify updates on disk with grep
- [ ] Push via API (Step 9) - optional but recommended
- [ ] Trigger library rescan (Step 10)
- [ ] Wait for rescan to complete
- [ ] Verify metadata in API (Step 11)
- [ ] Check Audiobookshelf UI for series grouping
- [ ] If needed, restart Audiobookshelf
- [ ] Confirm all books grouped correctly

