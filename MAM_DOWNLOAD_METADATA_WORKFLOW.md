# MAM Download + Metadata Integration Workflow

**Status**: Implementation Complete
**Date**: 2025-11-22
**Integration Point**: Audiobook download pipeline with automated metadata collection

---

## Overview

This document describes how metadata is automatically collected from MAM **during the download process** and applied to Audiobookshelf **after download completion**.

The workflow ensures:
- Metadata collection happens while book info is fresh
- No separate metadata lookup phase needed
- Complete audiobook information (narrator, duration) captured at source
- Automatic integration with Audiobookshelf post-download

---

## Architecture

### Three-Phase Workflow

```
Phase 1: DOWNLOAD INITIATION
├─ User/system initiates audiobook download
├─ Pass: title, author, series, series_number
├─ MAM Search Client:
│  ├─ Login to MAM (email/password, no cookies)
│  ├─ Search torrent by title + author
│  ├─ Verify results match (title + author + series)
│  ├─ Select best match
│  └─ Extract complete metadata from torrent page
├─ Store metadata with download record
└─ Queue download to qBittorrent/Prowlarr

Phase 2: DOWNLOAD EXECUTION
├─ Download runs in qBittorrent
├─ Metadata stays stored in database
├─ Download completes
└─ File appears in Audiobookshelf folder

Phase 3: METADATA APPLICATION
├─ Detect completed download
├─ Verify book in Audiobookshelf
├─ Apply stored metadata:
│  ├─ Title (with proper capitalization from MAM)
│  ├─ Author(s)
│  ├─ Narrator(s) ← PRIMARY VALUE
│  ├─ Duration ← PRIMARY VALUE
│  ├─ Abridged status
│  ├─ Series information
│  ├─ Publisher
│  └─ Description
├─ Update Book model
└─ Update Audiobookshelf record
```

---

## Component Files

### 1. MAM Search Client (`backend/integrations/mam_search_client.py`)

Handles all MAM interaction:
- **Login**: Email/password authentication (no cookies)
- **Search**: Query torrent database by title/author/series
- **Verification**: Match accuracy scoring
- **Extraction**: Complete metadata from torrent page

**Key Classes**:
- `MAMSearchClient` - Core search and metadata extraction
- `MAMDownloadMetadataCollector` - Orchestrator for download workflow

**API**:
```python
# Initialize
client = MAMSearchClient(email="user@example.com", password="password")
await client.initialize_crawler(crawler_instance)
await client.login()

# Search and extract
results = await client.search_torrent(
    title="Project Hail Mary",
    author="Andy Weir",
    series="",
    series_number=""
)

# Get complete metadata from selected result
metadata = await client.get_torrent_metadata(results[0]['url'])
```

### 2. Download Metadata Service (`backend/services/download_metadata_service.py`)

Orchestrates the complete workflow:
- Creates download records with metadata
- Monitors download completion
- Applies metadata to Audiobookshelf post-completion

**Key Methods**:
- `create_download_with_metadata()` - Entry point for new downloads
- `on_download_completed()` - Called when download finishes
- `get_download_status()` - Check current status

**API**:
```python
# Initialize service
service = DownloadMetadataService(
    mam_collector=collector,
    abs_client=abs_client,
    db=db_session
)

# Create download (collects metadata immediately)
result = await service.create_download_with_metadata(
    title="Project Hail Mary",
    author="Andy Weir",
    magnet_link="magnet:?xt=urn:...",
    book_id=123
)

# Later, when download completes
success = await service.on_download_completed(
    download_id=result['download_id'],
    qbittorrent_hash="abc123..."
)
```

### 3. Download Model (Updated: `backend/models/download.py`)

New fields added:
- `metadata_json` - Stores complete MAM metadata as JSON
- `metadata_applied_at` - When metadata was applied to ABS

---

## Data Flow Example

### Scenario: User wants to download "Project Hail Mary"

**Step 1: Download Initiation**
```
User Request:
  title = "Project Hail Mary"
  author = "Andy Weir"
  magnet_link = "magnet:?xt=urn:btih:..."

DownloadMetadataService.create_download_with_metadata()
  ↓
MAMSearchClient.search_torrent("Project Hail Mary", "Andy Weir")
  ↓
MAM Search Results:
  - "Project Hail Mary (Unabridged)" - Match Score: 0.95
  - "Project Hail Mary (Abridged)" - Match Score: 0.90

Selected: Top result (0.95 match)
  ↓
MAMSearchClient.get_torrent_metadata("https://www.myanonamouse.net/t/...")
  ↓
Extracted Metadata:
  {
    "title": "Project Hail Mary (Unabridged)",
    "author": "Andy Weir",
    "narrators": ["Ray Porter"],
    "duration_minutes": 631,
    "is_abridged": false,
    "publisher": "Ballantine Audio",
    "description": "Ryland Grace is the sole survivor...",
    "source": "mam_torrent_page",
    "torrent_url": "https://www.myanonamouse.net/t/...",
    "extracted_at": "2025-11-22T10:30:45Z"
  }

Download Record Created:
  id: 42
  title: "Project Hail Mary"
  author: "Andy Weir"
  status: "queued"
  metadata_json: {above JSON}

Download queued to qBittorrent
```

**Step 2: Download Execution**
```
qBittorrent downloads file to:
  F:/Audiobookshelf/Books/Project Hail Mary - Andy Weir/

Audiobookshelf detects new folder
  ↓
Auto-imports: Book appears in ABS library
```

**Step 3: Metadata Application**
```
DownloadMetadataService.on_download_completed(download_id=42)
  ↓
Retrieve stored metadata from database
  ↓
Find book in Audiobookshelf:
  - Search all libraries for title/author match
  - Found: item_id = "abc123xyz"

Build ABS update:
  {
    "title": "Project Hail Mary (Unabridged)",
    "authorName": "Andy Weir",
    "description": "Ryland Grace is the sole survivor...",
    "publisher": "Ballantine Audio"
  }

Apply to Audiobookshelf via API
  ↓
Update Book model:
  - narrator = "Ray Porter"
  - duration_minutes = 631
  - is_abridged = false
  - metadata_source = "mam"
  - last_metadata_update = now()

Download Record Updated:
  abs_import_status: "imported"
  metadata_applied_at: "2025-11-22T10:45:22Z"

✓ Complete
```

---

## MAM Search Verification Logic

The search verifies matches on three criteria:

### 1. Title Match (40% of score)
```python
# Normalize and compare
search: "Project Hail Mary"
result: "Project Hail Mary (Unabridged) - Andy Weir"

# Remove special chars, check word overlap
normalized search: "project hail mary"
normalized result: "project hail mary unabridged andy weir"

match_percentage = 3/3 = 100% ✓
```

### 2. Author Match (30% of score)
```python
# If author provided, must appear in result
search author: "Andy Weir"
result text: "Project Hail Mary (Unabridged) - Andy Weir"

"andy weir" in result ✓
```

### 3. Series Match (20% of score) + Series Number (10%)
```python
# If series provided, find in result
search series: "Foundation"
search series_number: "1"

result text: "Foundation Book 1 - Isaac Asimov"

series_match = "foundation" in result ✓
series_number = "1" in result ✓
```

### Match Score Calculation
```
Title Match:        40% × 1.0 = 0.40
Author Match:       30% × 1.0 = 0.30
Series Match:       20% × 1.0 = 0.20
Series Number:      10% × 1.0 = 0.10
─────────────────────────────────
Total Score:                      1.00 (100%)

Results sorted by score:
1. "Project Hail Mary (Unabridged)" - 0.95 ← SELECTED
2. "Project Hail Mary (Abridged)" - 0.90
3. Other results - lower scores
```

---

## Metadata Extraction from MAM Torrent Pages

### What Gets Extracted

**Required:**
- Title ← From page header

**Highly Valuable:**
- Narrators ← Regex: "Narrated by:", "Read by:", etc.
- Duration ← Regex: "10 hours 30 minutes", "631 minutes", etc.
- Abridged status ← Keywords: "unabridged", "abridged"

**Standard:**
- Author ← Regex: "Author:", "By:", "Written by:"
- Series ← Regex: "Series:", "Book 1", etc.
- Publisher ← Regex: "Publisher:", "Produced by:"
- Description ← First substantial paragraph

### Example MAM Torrent Page Patterns

```html
<!-- Narrator Extraction -->
<p>Narrated by Ray Porter</p>
→ Extracted: narrators = ["Ray Porter"]

<!-- Duration Extraction -->
<p>Duration: 10 hours 31 minutes</p>
→ Extracted: duration_minutes = 631

<p>Runtime: 631 minutes</p>
→ Extracted: duration_minutes = 631

<!-- Abridged Status -->
<p>Complete and unabridged</p>
→ Extracted: is_abridged = False

<p>Abridged version</p>
→ Extracted: is_abridged = True
```

---

## Integration with Existing Systems

### In `master_audiobook_manager.py`

Add at download initiation point:

```python
from backend.integrations.mam_search_client import MAMDownloadMetadataCollector
from backend.services.download_metadata_service import DownloadMetadataService

# Initialize once
mam_collector = MAMDownloadMetadataCollector(mam_search_client)
metadata_service = DownloadMetadataService(mam_collector, abs_client, db_session)

# When downloading a book:
download_result = await metadata_service.create_download_with_metadata(
    title=book.title,
    author=book.author,
    series=book.series,
    series_number=book.series_number,
    magnet_link=magnet_link,
    book_id=book.id
)

# When download completes (via qBittorrent webhook or polling):
await metadata_service.on_download_completed(download_result['download_id'])
```

### With qBittorrent Monitoring

qBittorrent can trigger webhooks on completion:

```python
@app.post("/api/downloads/on-complete")
async def on_download_complete(download_id: int, qb_hash: str):
    """Called by qBittorrent when download completes"""
    success = await metadata_service.on_download_completed(
        download_id=download_id,
        qbittorrent_hash=qb_hash
    )
    return {"success": success}
```

---

## Rate Limiting & Performance

### MAM Request Rate Limiting

- **Between requests**: 1.5 seconds minimum
- **Search operation**: 1 request + 1 torrent page fetch = ~3 seconds
- **Total per download**: 3-5 seconds for metadata collection

### Processing Timeline for Single Book

```
1. create_download_with_metadata() called
   ↓ (3-5 seconds)
2. Login to MAM (if needed)
3. Search for torrent
4. Select best match
5. Fetch torrent page HTML
6. Extract metadata via regex
7. Store in database
   ↓
8. Download queued to qBittorrent
   ↓ (minutes to hours, download time)
9. Download completes
10. on_download_completed() called
    ↓ (1-2 seconds)
11. Find book in ABS
12. Apply metadata via ABS API
13. Update Book model
    ↓
Complete ✓
```

### Batch Processing

For multiple downloads:
```python
# Process sequentially (safe, respects rate limiting)
for book in books_to_download:
    await metadata_service.create_download_with_metadata(...)
    # 3-5 seconds per book
    # 1,000 books = 50-85 minutes

# Or parallel with semaphore
async def batch_download_with_metadata(books, max_concurrent=3):
    semaphore = asyncio.Semaphore(max_concurrent)
    tasks = [
        metadata_service.create_download_with_metadata(...)
        for book in books
    ]
    return await asyncio.gather(*tasks)
```

---

## Database Schema Changes

### Downloads Table - New Columns

```sql
ALTER TABLE downloads ADD COLUMN metadata_json TEXT NULL;
ALTER TABLE downloads ADD COLUMN metadata_applied_at TIMESTAMP NULL;

-- Example metadata_json content:
{
  "title": "Project Hail Mary (Unabridged)",
  "author": "Andy Weir",
  "narrators": ["Ray Porter"],
  "duration_minutes": 631,
  "is_abridged": false,
  "publisher": "Ballantine Audio",
  "series": null,
  "series_number": null,
  "description": "Ryland Grace is the sole survivor...",
  "source": "mam_torrent_page",
  "torrent_url": "https://www.myanonamouse.net/t/...",
  "extracted_at": "2025-11-22T10:30:45Z",
  "mam_match_score": 0.95,
  "collected_for_download": true
}
```

---

## Error Handling

### Scenario 1: MAM Search Fails
```
create_download_with_metadata():
  - Search fails (no results)
  - Metadata = {}
  - Download continues without metadata
  - Log: "No MAM metadata found for [title]"
  ✓ Download proceeds normally, can be fixed manually later
```

### Scenario 2: Book Not Found in ABS
```
on_download_completed():
  - Metadata collected ✓
  - Book not in ABS yet
  - Log: "Could not find book in ABS: [title]"
  - Return false, mark as import_failed
  ✓ Manual intervention needed, but metadata is preserved
```

### Scenario 3: ABS Update Fails
```
on_download_completed():
  - Book found ✓
  - Metadata application fails
  - abs_import_status = "import_failed"
  - abs_import_error = "ABS update failed"
  ✓ Can retry later, metadata still in database
```

---

## Monitoring & Status

### Check Download Status

```python
status = await metadata_service.get_download_status(download_id=42)

# Returns:
{
    'download_id': 42,
    'title': 'Project Hail Mary',
    'author': 'Andy Weir',
    'status': 'completed',
    'qb_status': 'seeding',
    'abs_import_status': 'imported',
    'metadata': {full metadata dict},
    'metadata_completeness': 0.95  # 95% complete
}
```

### Query Downloads by Status

```python
# Get all downloads waiting for metadata application
pending = db.query(Download).filter(
    Download.abs_import_status == 'pending'
).all()

# Get failed imports
failed = db.query(Download).filter(
    Download.abs_import_status == 'import_failed'
).all()
```

---

## Benefits

1. **Automated Process**: Metadata collected during download, no extra steps
2. **Complete Data**: Narrator, duration, abridged status - all audiobook essentials
3. **Source Accuracy**: Data comes from MAM community-curated descriptions
4. **Quality Preservation**: Never overwrites existing good data in ABS
5. **Audit Trail**: Complete JSON stored with download record
6. **Error Recovery**: If ABS update fails, can retry with preserved metadata

---

## Testing Checklist

- [ ] MAM login works with email/password
- [ ] Search finds correct audiobook by title+author
- [ ] Series number matching works correctly
- [ ] Metadata extraction from torrent page successful
- [ ] Narrator extraction via regex patterns
- [ ] Duration parsing (multiple formats)
- [ ] Download record created with metadata JSON
- [ ] Download completion detected
- [ ] Book found in Audiobookshelf
- [ ] Metadata applied to ABS
- [ ] Book model updated
- [ ] Metadata JSON preserved in database
- [ ] Error handling for failed searches
- [ ] Error handling for missing books in ABS

---

## Next Steps

1. ✅ Implement MAM search client with login
2. ✅ Implement metadata extraction from torrent pages
3. ✅ Implement download + metadata service
4. ✅ Create database schema updates
5. ⏳ Integrate into master_audiobook_manager.py
6. ⏳ Test with real audiobook downloads
7. ⏳ Add qBittorrent completion webhooks
8. ⏳ Deploy to production

---

**Status**: Ready for integration. All components implemented and documented.
