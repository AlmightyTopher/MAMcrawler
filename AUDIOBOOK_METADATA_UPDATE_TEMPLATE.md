# Audiobook Metadata Series Update - Reusable Template

## Overview
This template documents the proven process for updating series metadata in Audiobookshelf audiobook library to properly link books to their series.

## Prerequisites
- Audiobookshelf running and accessible at configured URL
- Valid API token for Audiobookshelf
- Books already downloaded and present in library filesystem
- Direct filesystem access to book folders
- Environment variables set: `ABS_URL`, `ABS_TOKEN`

## Step 1: Map Books to Series (Filesystem Discovery)

### Source of Truth
Book metadata is stored in individual JSON files on disk:
- Location: `[LIBRARY_PATH]/[BOOK_FOLDER]/metadata.json`
- Key field to update: `seriesName`

### Discovery Process
1. List all book folders in the library directory
2. For each folder, check for the existence of `metadata.json`
3. Read the `title` field from each metadata.json to identify books
4. Manually or programmatically create a mapping of book folders to series names

### Output
A mapping structure containing:
- Source folder name (as it exists on disk)
- Target series name (what should appear in Audiobookshelf)

Example structure (pseudo-code):
```
BOOKS_TO_UPDATE = [
    ('[FOLDER_NAME_1]', '[SERIES_NAME_1]'),
    ('[FOLDER_NAME_2]', '[SERIES_NAME_1]'),
    ('[FOLDER_NAME_3]', '[SERIES_NAME_2]'),
    ...
]
```

## Step 2: Update Metadata Files On Disk

### Tool
Python script using standard library:
- `pathlib.Path` for filesystem operations
- `json` module for reading/writing JSON

### Process
1. Iterate through each book folder in the mapping
2. For each folder:
   - Construct path: `[LIBRARY_PATH]/[FOLDER_NAME]/metadata.json`
   - Check if file exists
   - Open file in read-write mode with UTF-8 encoding
   - Load JSON content
   - Update the `seriesName` field with target series name
   - Write modified JSON back to disk
   - Create timestamped backup of original file

### Implementation Pattern
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

### Verification
After updating:
- Read metadata file and confirm `seriesName` field matches target value
- Verify all updated files have correct series names on disk

## Step 3: Push Updates via API (Optional but Recommended)

### API Endpoint
- **Method:** PATCH
- **Endpoint:** `/api/items/{item_id}/media`
- **Payload:** `{"metadata": {"seriesName": "[SERIES_NAME]"}}`

### Process
1. Get library ID via: `GET /api/libraries`
2. Index library items to map titles to IDs:
   - Call: `GET /api/libraries/{lib_id}/items?limit=500&offset={offset}`
   - Extract title and item ID from each response
   - Continue with pagination until desired item count reached
3. For each book found in library:
   - Send PATCH request with series name update
   - Capture response status (200 = success)

### Implementation Pattern
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

### Limitation
This approach only reaches items indexed in the first N pages. For massive libraries (100,000+ items), most books may not be found. Use this for targeted updates only.

## Step 4: Trigger Library Rescan

### API Endpoint
- **Method:** POST
- **Endpoint:** `/api/libraries/{lib_id}/scan`
- **Expected Response:** Status 200

### Purpose
Rescan tells Audiobookshelf to rebuild its database from all metadata.json files on disk, picking up any changes made directly to the filesystem.

### Implementation
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

### Timing
- Request returns immediately (status 200)
- Actual rescan runs in background on Audiobookshelf server
- Duration depends on library size (15 minutes to 1+ hour for large libraries)

## Step 5: Verification

### Verify Metadata on Disk
```bash
grep "seriesName" "[LIBRARY_PATH]/[FOLDER_NAME]/metadata.json"
```

Expected output: `"seriesName": "[EXPECTED_SERIES_NAME]"`

### Verify in API (After Rescan Completes)
1. Query library items for books by title or keyword
2. Check the `seriesName` field in returned metadata
3. Confirm it matches the target series name

### Implementation Pattern
```python
async def verify_updates():
    # Query library for books matching keywords
    # Extract title and seriesName from each result
    # Compare seriesName against target values
```

## Common Issues and Resolutions

### Issue: Books Not Found in API After Rescan
**Cause:** Library has 100,000+ items; books scattered beyond first N pages
**Resolution:** Trust filesystem updates are correct. Verify with grep on disk. Restart Audiobookshelf to force full reload from disk.

### Issue: Rescan Request Succeeds But Changes Don't Appear
**Cause:** Rescan may not process all folders or cache isn't invalidated
**Resolution:** Restart Audiobookshelf application completely to clear cache and force reload from disk.

### Issue: JSON Parse Errors When Reading/Writing Metadata
**Cause:** File encoding issues or malformed JSON
**Resolution:** Use UTF-8 encoding explicitly. Validate JSON before writing. Use try/except blocks around file operations.

## Data Flow

```
Filesystem (metadata.json files)
         ↓
    [Update with series names]
         ↓
Audiobookshelf API Scan Request
         ↓
Server rebuilds database from disk files
         ↓
Series metadata now available in API queries
```

## API Documentation Reference

### Libraries Endpoint
- `GET /api/libraries` - Get all libraries with IDs
- `POST /api/libraries/{id}/scan` - Trigger library rescan

### Items Endpoint
- `GET /api/libraries/{lib_id}/items?limit=500&offset={offset}` - Paginated item list
- `PATCH /api/items/{item_id}/media` - Update media metadata

### Required Headers
- `Authorization: Bearer {api_token}`

## Tools and Dependencies

### Required Packages
- `aiohttp` - Async HTTP requests for API calls
- `python-dotenv` - Environment variable loading
- Standard library: `json`, `pathlib`, `asyncio`

### Command Execution
```bash
pip install aiohttp python-dotenv
```

## Success Criteria

1. ✓ All target metadata.json files have `seriesName` field updated on disk
2. ✓ Backup files created before modifications
3. ✓ Library rescan API request returns status 200
4. ✓ Filesystem verification confirms series names are correct
5. ✓ (After restart if needed) API queries return updated series information

## Reusability Checklist

- [ ] Identify all books to update and their target series names
- [ ] Update `BOOKS_TO_UPDATE` mapping
- [ ] Verify library path is correct
- [ ] Confirm `ABS_URL` and `ABS_TOKEN` environment variables are set
- [ ] Run metadata update script
- [ ] Verify changes on disk with grep/cat
- [ ] Run API rescan request
- [ ] Wait for rescan to complete
- [ ] Query API to verify changes propagated
- [ ] If needed, restart Audiobookshelf and re-verify

## Notes

- This process modifies files on disk; backups are essential
- Rescan is asynchronous; monitor library in UI for completion
- For very large libraries (500K+ items), rescan may take 1+ hour
- Series names must be consistent across all books in same series
- API approach alone won't find all books if library is very large; filesystem approach is primary
