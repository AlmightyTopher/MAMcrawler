# Backend Modules

This directory contains wrapper modules that adapt existing project scripts for use by the FastAPI backend.

## Overview

The modules package provides async-compatible functions that:
- Integrate with FastAPI's dependency injection
- Use SQLAlchemy ORM for database operations
- Return structured result dictionaries
- Handle errors gracefully with comprehensive logging
- Track execution in the `tasks` table
- Support type hints for better IDE support

## Module Structure

```
backend/modules/
├── __init__.py                  # Package exports and metadata
├── mam_crawler.py              # MAM guide crawling wrapper
├── metadata_correction.py      # Metadata enrichment pipeline
├── series_completion.py        # Series gap discovery and download
├── author_completion.py        # Author catalog discovery
├── top10_discovery.py          # MAM top-10 genre scraping
└── README.md                   # This file
```

## Modules

### 1. MAM Crawler (`mam_crawler.py`)

Wrapper for `stealth_mam_crawler.py` - Scrapes MAM guides with human-like behavior.

**Functions:**

#### `crawl_mam_guides(db_session, config=None) -> Dict`
Execute MAM guide crawler with stealth behavior.

**Args:**
- `db_session`: SQLAlchemy database session
- `config`: Optional configuration dict
  - `max_guides`: Maximum guides to crawl (None = all)
  - `resume`: Resume from saved state (default: True)
  - `min_delay`: Min delay between requests (default: 10s)
  - `max_delay`: Max delay between requests (default: 30s)
  - `output_dir`: Output directory (default: guides_output)

**Returns:**
```python
{
    "guides_count": 42,
    "errors": 2,
    "timestamp": "2025-11-16T12:00:00",
    "guides_output_dir": "/path/to/guides_output",
    "failed_guides": [...]
}
```

#### `get_crawler_status() -> Dict`
Get current MAM crawler status from state file.

**Returns:**
```python
{
    "completed_count": 100,
    "failed_count": 5,
    "pending_count": 20,
    "last_run": "2025-11-16T10:00:00",
    "state_file_exists": True
}
```

#### `reset_crawler_state() -> Dict`
Reset crawler state to start fresh.

**Example:**
```python
from backend.database import get_db_context
from backend.modules import crawl_mam_guides

with get_db_context() as db:
    result = await crawl_mam_guides(db, config={"max_guides": 10})
    print(f"Crawled {result['guides_count']} guides")
```

---

### 2. Metadata Correction (`metadata_correction.py`)

Google Books → Goodreads metadata enrichment pipeline.

**Functions:**

#### `correct_book_metadata(book_id, db_session, force_refresh=False) -> Dict`
Correct and enrich metadata for a single book.

**Strategy:**
1. Query Google Books API for comprehensive metadata
2. Fall back to Goodreads if Google fails (TODO)
3. Update `book.metadata_source` with field→source mapping
4. Calculate and update `metadata_completeness_percent`
5. Create `MetadataCorrection` records for all changes

**Args:**
- `book_id`: Database ID of book to correct
- `db_session`: SQLAlchemy database session
- `force_refresh`: Force refresh even if recently updated

**Returns:**
```python
{
    "book_id": 123,
    "fields_updated": ["isbn", "publisher", "description"],
    "sources_used": ["GoogleBooks"],
    "completeness_before": 45,
    "completeness_after": 75,
    "errors": []
}
```

#### `correct_all_books(db_session, limit=None, filter_incomplete_only=True, batch_size=10) -> Dict`
Correct metadata for all books (or filtered subset).

**Args:**
- `db_session`: SQLAlchemy database session
- `limit`: Max books to process (None = all)
- `filter_incomplete_only`: Only process books with <100% completeness
- `batch_size`: Number of books to process in parallel

**Returns:**
```python
{
    "total_processed": 500,
    "succeeded": 480,
    "failed": 10,
    "skipped": 10,
    "total_fields_updated": 1250,
    "average_completeness_before": 52.3,
    "average_completeness_after": 78.6,
    "errors": [...]
}
```

**Example:**
```python
from backend.modules import correct_all_books

with get_db_context() as db:
    result = await correct_all_books(db, limit=100)
    print(f"Updated {result['succeeded']} books")
```

---

### 3. Series Completion (`series_completion.py`)

Series gap discovery and automatic download queueing.

**Functions:**

#### `find_missing_series_books(db_session, series_name=None) -> Dict`
Find missing books in all series (or specific series).

**Strategy:**
1. Get all series from library with ≥1 book
2. For each series, query Google Books for complete series
3. Identify books not in library
4. Create `MissingBook` records with `reason="series_gap"`

**Args:**
- `db_session`: SQLAlchemy database session
- `series_name`: Optional specific series to check (None = all)

**Returns:**
```python
{
    "series_checked": 45,
    "missing_books_found": 82,
    "series_with_gaps": 23,
    "missing_books": [...],
    "errors": []
}
```

#### `download_missing_series_books(db_session, batch_size=10, max_priority=None) -> Dict`
Queue downloads for missing series books.

**Strategy:**
1. Get pending missing books (status=pending, reason=series_gap)
2. Try Prowlarr search (MAM + other indexers)
3. Create `Download` records
4. Send to qBittorrent

**Args:**
- `db_session`: SQLAlchemy database session
- `batch_size`: Number of books to process (default: 10)
- `max_priority`: Only process books with priority >= this

**Returns:**
```python
{
    "download_queued_count": 10,
    "success_count": 8,
    "failed_count": 2,
    "skipped_count": 0,
    "errors": []
}
```

#### `import_and_correct_series(db_session) -> Dict`
Monitor completed downloads, import to Audiobookshelf, and correct metadata.

**Note:** Placeholder - requires full import pipeline implementation.

**Example:**
```python
from backend.modules import find_missing_series_books, download_missing_series_books

with get_db_context() as db:
    # Find gaps
    gaps = await find_missing_series_books(db)
    print(f"Found {gaps['missing_books_found']} missing books")

    # Queue downloads
    downloads = await download_missing_series_books(db, batch_size=10)
    print(f"Queued {downloads['download_queued_count']} downloads")
```

---

### 4. Author Completion (`author_completion.py`)

Author catalog discovery and automatic download queueing.

**Functions:**

#### `find_missing_author_books(db_session, author_name=None, min_books_threshold=2) -> Dict`
Find missing books by favorite authors.

**Strategy:**
1. Get authors with ≥ `min_books_threshold` books in library
2. Query Google Books for author's complete catalog
3. Identify books not in library
4. Create `MissingBook` records with `reason="author_gap"`

**Args:**
- `db_session`: SQLAlchemy database session
- `author_name`: Optional specific author to check (None = all)
- `min_books_threshold`: Min books to consider author a "favorite" (default: 2)

**Returns:**
```python
{
    "authors_checked": 120,
    "missing_books_found": 340,
    "authors_with_gaps": 85,
    "missing_books": [...],
    "errors": []
}
```

#### `download_missing_author_books(db_session, batch_size=10, max_priority=None) -> Dict`
Queue downloads for missing author books.

**Similar to `download_missing_series_books` but filters by `reason="author_gap"`.**

#### `import_and_correct_authors(db_session) -> Dict`
Monitor and import completed author downloads.

**Note:** Placeholder - requires full import pipeline implementation.

**Example:**
```python
from backend.modules import find_missing_author_books, download_missing_author_books

with get_db_context() as db:
    # Find missing books by favorite authors
    gaps = await find_missing_author_books(db, min_books_threshold=3)
    print(f"Found {gaps['missing_books_found']} missing books by {gaps['authors_with_gaps']} authors")

    # Queue top-priority downloads
    downloads = await download_missing_author_books(db, batch_size=5, max_priority=50)
    print(f"Queued {downloads['download_queued_count']} downloads")
```

---

### 5. Top 10 Discovery (`top10_discovery.py`)

MAM visual top-10 genre scraping and download queueing.

**Functions:**

#### `scrape_mam_top10(genre, db_session) -> Dict`
Scrape MAM's visual top-10 list for a specific genre.

**Strategy:**
1. Connect to MAM using stealth crawler auth
2. Navigate to top-10 page for genre
3. Extract torrent links and metadata
4. Return list of torrents

**Args:**
- `genre`: Genre to scrape (e.g., "Fiction", "Science Fiction")
- `db_session`: SQLAlchemy database session

**Returns:**
```python
{
    "genre": "Science Fiction",
    "books_found": 10,
    "books": [
        {
            "title": "Example Book",
            "author": "Example Author",
            "magnet_link": "magnet:?xt=...",
            "rank": 1
        },
        ...
    ],
    "timestamp": "2025-11-16T12:00:00",
    "errors": []
}
```

**Note:** Placeholder - requires MAM scraping implementation.

#### `queue_top10_downloads(genres_list, db_session, skip_existing=True) -> Dict`
Queue downloads for top-10 books across multiple genres.

**Args:**
- `genres_list`: List of genre names to scrape
- `db_session`: SQLAlchemy database session
- `skip_existing`: Skip books already in library (default: True)

**Returns:**
```python
{
    "genres_processed": 5,
    "total_books_found": 50,
    "queued_count": 35,
    "duplicates_skipped": 15,
    "errors": []
}
```

#### `get_available_genres() -> Dict`
Get list of available genres from MAM.

**Returns:**
```python
{
    "genres": ["Fiction", "Science Fiction", "Fantasy", ...],
    "genre_ids": {},  # Mapping to MAM category IDs
    "timestamp": "2025-11-16T12:00:00"
}
```

**Example:**
```python
from backend.modules import get_available_genres, queue_top10_downloads

# Get available genres
genres_result = await get_available_genres()
top_genres = genres_result["genres"][:5]

# Queue downloads for top 5 genres
with get_db_context() as db:
    result = await queue_top10_downloads(top_genres, db)
    print(f"Queued {result['queued_count']} books from {result['genres_processed']} genres")
```

---

## Error Handling

All functions follow a consistent error handling pattern:

1. **Try-catch at function level**: Catch all exceptions
2. **Graceful degradation**: Return error dict instead of raising
3. **Database rollback**: Rollback session on errors
4. **Error logging**: Log exceptions with full traceback
5. **Task tracking**: Update Task record status to "failed"

**Example error response:**
```python
{
    "guides_count": 0,
    "errors": 1,
    "timestamp": "2025-11-16T12:00:00",
    "guides_output_dir": "",
    "failed_guides": [],
    "error": "MAM_USERNAME not set in environment"
}
```

## Type Hints

All functions use type hints for better IDE support:

```python
async def crawl_mam_guides(
    db_session: Session,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    ...
```

## Database Session Management

All functions expect a SQLAlchemy `Session` object:

```python
from backend.database import get_db_context

# Context manager (recommended)
with get_db_context() as db:
    result = await crawl_mam_guides(db)

# FastAPI dependency injection
from fastapi import Depends
from backend.database import get_db

@app.post("/crawl")
async def crawl_endpoint(db: Session = Depends(get_db)):
    result = await crawl_mam_guides(db)
    return result
```

## Task Tracking

All long-running operations create `Task` records:

```python
task = Task(
    task_name="MAM_CRAWLER",
    scheduled_time=datetime.now(),
    actual_start=datetime.now(),
    status="running",
    metadata={"config": config}
)
db_session.add(task)
db_session.commit()

# ... execute work ...

task.status = "completed"
task.actual_end = datetime.now()
task.items_processed = 100
task.items_succeeded = 95
task.items_failed = 5
db_session.commit()
```

## Testing

Test modules using pytest with async support:

```python
import pytest
from backend.database import get_db_context
from backend.modules import crawl_mam_guides

@pytest.mark.asyncio
async def test_crawl_mam_guides():
    with get_db_context() as db:
        result = await crawl_mam_guides(db, config={"max_guides": 1})
        assert result["guides_count"] >= 0
        assert "errors" in result
```

## Dependencies

Module dependencies:
- `sqlalchemy` - ORM and database operations
- `httpx` or `aiohttp` - Async HTTP clients
- `beautifulsoup4` - HTML parsing (for scraping)
- `crawl4ai` - MAM crawler framework
- Existing integrations: `google_books_client`, `qbittorrent_client`, etc.

## Future Enhancements

1. **Goodreads Integration**: Add Goodreads API client and fallback logic
2. **Prowlarr Integration**: Implement Prowlarr search for download sources
3. **MAM Top-10 Scraping**: Complete implementation with stealth behavior
4. **Import Pipeline**: Full automated import to Audiobookshelf
5. **Batch Processing**: Parallel processing with asyncio.gather()
6. **Retry Logic**: Exponential backoff for failed operations
7. **Rate Limiting**: Global rate limiter across all modules

## Contributing

When adding new modules:

1. Follow the established pattern (async functions, typed returns)
2. Include comprehensive docstrings
3. Handle errors gracefully
4. Create Task records for tracking
5. Add type hints
6. Update `__init__.py` exports
7. Update this README
