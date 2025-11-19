# Gap Analysis & Automated Acquisition - Implementation Roadmap

## Overview

This document provides specific code locations, function signatures, and integration points for building the "Library Gap Analysis and Automated Acquisition" feature.

The feature has three main phases:
1. **Analysis** - Detect gaps in library
2. **Search** - Find missing books on MAM
3. **Acquisition** - Download and import

---

## PHASE 1: ANALYSIS (Gap Detection)

### Existing Components to Integrate

#### 1.1 Library Scanning
**File:** `/home/user/MAMcrawler/stealth_audiobookshelf_crawler.py`
**Key Method:** `StealthMAMAudiobookshelfCrawler.get_library()`

```python
# Returns: List[Dict] with all books in library
books = await crawler.get_library()
# Each book: {
#     "abs_id": "id123",
#     "title": "Book Title",
#     "author": "Author Name",
#     "series": "Series Name",
#     "seriesSequence": "1",
#     "isbn": "123456789"
# }
```

**Integration Point:**
```python
# In new audiobook_gap_analyzer.py:
from stealth_audiobookshelf_crawler import StealthMAMAudiobookshelfCrawler

crawler = StealthMAMAudiobookshelfCrawler()
await crawler.authenticate()
library_books = await crawler.get_library()
```

#### 1.2 Series Analysis
**File:** `/home/user/MAMcrawler/api_series_populator.py`
**Key Method:** Goodreads series lookup

```python
# Gets total books in series from Goodreads
# Need to extract and adapt series counting logic

# Pseudocode:
for book in library_books:
    if book.get("series"):
        total_in_series = query_goodreads_series(book["series"])
        books_owned = count_books_in_series(library_books, book["series"])
        gaps = total_in_series - books_owned
        missing_numbers = find_missing_sequence_numbers(library_books, book["series"])
```

**Key Files:**
- `goodreads_api_client.py` - Goodreads API wrapper
- `goodreads_abs_scraper.py` - Web scraping alternative
- `book_metadata_gatherer.py` - Metadata collection utilities

#### 1.3 Store Gaps in Database
**File:** `/home/user/MAMcrawler/backend/services/book_service.py`
**Methods to use:**

```python
from backend.services.book_service import BookService
from backend.services.series_service import SeriesService

# Create series record
SeriesService.create_or_update_series(
    db=db,
    name="Series Name",
    author="Author Name",
    goodreads_id="123",
    total_books=10,
    books_owned=7,
    books_missing=3,
    completion_status="incomplete"
)

# Store missing books
from backend.models.missing_book import MissingBook
missing_book = MissingBook(
    series_id=series.id,
    author_id=None,
    title="Missing Book Title",
    series_name="Series Name",
    series_number="8",
    reason_missing="series_gap",
    priority=1  # high
)
db.add(missing_book)
db.commit()
```

**Database Location:** `/home/user/MAMcrawler/database_schema.sql` (see tables: series, authors, missing_books)

---

## PHASE 2: SEARCH (Find Missing Books on MAM)

### Existing Components to Integrate

#### 2.1 MAM Search
**File:** `/home/user/MAMcrawler/stealth_audiobook_downloader.py`
**Key Method:** `StealthMAMAudiobookDownloader.search_audiobooks(query, genre)`

```python
async def search_for_book(title, author):
    """
    Search MAM for a specific book
    Returns: magnet link or None
    """
    downloader = StealthMAMAudiobookDownloader()
    await downloader.authenticate()
    
    # Build search query
    query = f"{title} {author}"
    
    # Search with genre filter (or all categories)
    results = await downloader.search_audiobooks(query, genre=None)
    
    # Parse results for best match
    # Filter by: seed count, quality, file size
    best_result = filter_and_rank_results(results, title, author)
    
    return best_result.get("magnet_link") if best_result else None
```

**Integration Code:**
```python
from stealth_audiobook_downloader import StealthMAMAudiobookDownloader

downloader = StealthMAMAudiobookDownloader()
await downloader.authenticate()

for missing_book in missing_books:
    search_query = f"{missing_book.title} {missing_book.author_name}"
    results = await downloader.search_audiobooks(
        query=search_query,
        genre=None  # Search all categories
    )
    
    # Evaluate results
    best_magnet = select_best_result(results, missing_book)
    if best_magnet:
        missing_book.search_result = best_magnet
```

#### 2.2 Result Filtering & Ranking
**Create new function in gap analyzer:**

```python
def filter_and_rank_results(results, title, author):
    """
    Rank results by:
    1. Title/author match score (fuzzy)
    2. Seed count (higher is better)
    3. File size (within acceptable range)
    4. Upload date (more recent is better)
    """
    from difflib import SequenceMatcher
    
    ranked = []
    for result in results:
        title_match = SequenceMatcher(None, title.lower(), 
                                     result["title"].lower()).ratio()
        seed_score = min(result.get("seeds", 0) / 100, 1.0)
        
        score = (title_match * 0.5) + (seed_score * 0.5)
        ranked.append((score, result))
    
    return sorted(ranked, reverse=True)[0][1] if ranked else None
```

**Existing Utilities:**
- `/home/user/MAMcrawler/simple_fuzzy_corrector.py` - Fuzzy matching
- `/home/user/MAMcrawler/local_search.py` - Local search utilities

#### 2.3 Handle No Results
```python
# If search returns no results:
missing_book.download_status = "no_torrent_found"
missing_book.notes = f"No results for: {title} by {author}"

# Log failure
FailedAttemptService.log_failure(
    db=db,
    task_name="MISSING_BOOK_SEARCH",
    item_id=missing_book.id,
    item_name=missing_book.title,
    reason="no_torrent_found",
    error_details=f"Search query: {title} {author}"
)
```

---

## PHASE 3: ACQUISITION (Download & Import)

### Existing Components to Integrate

#### 3.1 Queue Download
**File:** `/home/user/MAMcrawler/backend/services/download_service.py`

```python
from backend.services.download_service import DownloadService

# Create download record
download = DownloadService.create_download(
    db=db,
    book_id=None,  # or book.id if book exists
    source="MAM",
    title=missing_book.title,
    author=missing_book.author_name,
    magnet_link=magnet_link,
    missing_book_id=missing_book.id
)

if download["success"]:
    download_id = download["download_id"]
    # Update missing_book status
    missing_book.download_status = "queued"
    missing_book.download_id = download_id
    db.commit()
```

#### 3.2 Add to qBittorrent
**File:** `/home/user/MAMcrawler/backend/integrations/qbittorrent_client.py`

```python
from backend.integrations.qbittorrent_client import QBittorrentClient

async with QBittorrentClient(
    base_url=os.getenv('QB_HOST'),
    username=os.getenv('QB_USERNAME'),
    password=os.getenv('QB_PASSWORD')
) as qb_client:
    
    # Add torrent
    result = await qb_client.add_torrent(
        magnet_link=magnet_link,
        category="audiobooks",
        tags=["automated", "gap-filler", missing_book.series_name or ""]
    )
    
    if result:
        # Store qBittorrent hash
        download.qbittorrent_hash = result.get("hash")
        download.qbittorrent_status = "downloading"
        db.commit()
    else:
        download.status = "failed"
        download.error = "Failed to add to qBittorrent"
```

#### 3.3 Monitor Download
**File:** `/home/user/MAMcrawler/backend/services/download_service.py`

```python
async def monitor_downloads(db: Session):
    """Poll qBittorrent for completion"""
    
    from backend.integrations.qbittorrent_client import QBittorrentClient
    
    async with QBittorrentClient(...) as qb_client:
        # Get all active downloads
        active_downloads = db.query(Download).filter(
            Download.status.in_(["queued", "downloading"])
        ).all()
        
        for download in active_downloads:
            # Get torrent status from qBittorrent
            torrent = await qb_client.get_torrent_by_hash(
                download.qbittorrent_hash
            )
            
            if torrent:
                download.qbittorrent_status = torrent["state"]
                
                if torrent["state"] == "uploading":
                    download.status = "completed"
                    download.date_completed = datetime.now()
                    
                    # Queue for import
                    trigger_import_to_abs(download)
            else:
                # Torrent not found - may have been removed
                download.status = "abandoned"
        
        db.commit()
```

#### 3.4 Auto-Import to Audiobookshelf
**File:** `/home/user/MAMcrawler/audiobookshelf_metadata_sync.py`

```python
async def import_completed_download(download):
    """
    When torrent completes, import to Audiobookshelf
    """
    from stealth_audiobookshelf_crawler import StealthMAMAudiobookshelfCrawler
    
    crawler = StealthMAMAudiobookshelfCrawler()
    await crawler.authenticate()
    
    # Scan Audiobookshelf library to find newly added files
    # (ABS auto-scans, we just need to detect)
    
    new_books = await crawler.get_library()
    
    # Match against download record
    for book in new_books:
        if matches_download(book, download):
            # Found! Update download status
            download.abs_import_status = "imported"
            download.status = "completed"
            
            # Update missing_book
            if download.missing_book_id:
                missing_book = db.query(MissingBook).get(
                    download.missing_book_id
                )
                missing_book.download_status = "completed"
            
            return True
    
    return False
```

---

## IMPLEMENTATION ARCHITECTURE

### New File: `audiobook_gap_analyzer.py`

```python
#!/usr/bin/env python3
"""
Audiobook Gap Analysis & Automated Acquisition System
Orchestrates the full workflow: detect → search → queue → download → import
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from stealth_audiobookshelf_crawler import StealthMAMAudiobookshelfCrawler
from stealth_audiobook_downloader import StealthMAMAudiobookDownloader
from goodreads_api_client import GoodreadsClient
from backend.services.book_service import BookService
from backend.services.download_service import DownloadService
from backend.integrations.qbittorrent_client import QBittorrentClient
from backend.integrations.abs_client import AudiobookshelfClient

class AudiobookGapAnalyzer:
    """Main orchestrator for gap analysis workflow"""
    
    def __init__(self):
        self.abs_crawler = StealthMAMAudiobookshelfCrawler()
        self.mam_downloader = StealthMAMAudiobookDownloader()
        self.goodreads = GoodreadsClient()
        self.logger = self._setup_logging()
        self.stats = {
            'started_at': datetime.now(),
            'library_books': 0,
            'gaps_identified': 0,
            'torrents_found': 0,
            'downloads_queued': 0,
            'errors': []
        }
    
    async def run_full_analysis(self) -> Dict[str, Any]:
        """Execute complete gap analysis and acquisition workflow"""
        
        try:
            # Phase 1: Analyze gaps
            gaps = await self.analyze_library_gaps()
            self.stats['gaps_identified'] = len(gaps)
            
            # Phase 2: Search for missing books
            search_results = await self.search_missing_books(gaps)
            self.stats['torrents_found'] = len(search_results)
            
            # Phase 3: Queue downloads
            queued = await self.queue_downloads(search_results)
            self.stats['downloads_queued'] = len(queued)
            
            return {
                'success': True,
                'stats': self.stats,
                'gaps': gaps,
                'downloads_queued': queued
            }
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            self.stats['errors'].append(str(e))
            return {'success': False, 'error': str(e)}
    
    async def analyze_library_gaps(self) -> List[Dict]:
        """Phase 1: Detect gaps in existing library"""
        # Implementation details...
        pass
    
    async def search_missing_books(self, gaps) -> List[Dict]:
        """Phase 2: Search MAM for missing books"""
        # Implementation details...
        pass
    
    async def queue_downloads(self, results) -> List[Dict]:
        """Phase 3: Queue found books for download"""
        # Implementation details...
        pass

if __name__ == "__main__":
    analyzer = AudiobookGapAnalyzer()
    result = asyncio.run(analyzer.run_full_analysis())
    print(result)
```

### REST API Endpoint: Add to `backend/routes/downloads.py`

```python
@router.post("/api/gaps/analyze-and-acquire")
async def analyze_and_acquire_gaps(
    series_priority: bool = True,
    max_downloads: int = 10,
    db: Session = Depends(get_db)
):
    """
    Analyze library for gaps and queue missing books for download
    
    Args:
        series_priority: Prioritize series gaps over author gaps
        max_downloads: Maximum downloads to queue in this run
    
    Returns:
        {
            "gaps_identified": 5,
            "downloads_queued": 3,
            "gaps": [...],
            "downloads": [...]
        }
    """
    from audiobook_gap_analyzer import AudiobookGapAnalyzer
    
    analyzer = AudiobookGapAnalyzer()
    result = await analyzer.run_full_analysis()
    
    return result
```

### Scheduler Integration: Add to `backend/routes/scheduler.py`

```python
# Add new task type
SCHEDULED_TASKS = {
    "GAPS": {
        "description": "Analyze gaps and queue downloads",
        "runner": "audiobook_gap_analyzer.AudiobookGapAnalyzer.run_full_analysis",
        "default_time": "0 1 * * *"  # Daily 1:00 AM
    },
    ...
}
```

---

## KEY FUNCTIONS TO IMPLEMENT

### 1. Calculate Completion %
```python
def calculate_series_completion(
    library_books: List[Dict],
    series_name: str,
    total_in_series: int
) -> Dict:
    """Calculate series completion percentage"""
    owned = sum(1 for b in library_books if b.get("series") == series_name)
    completion_pct = (owned / total_in_series * 100) if total_in_series else 0
    missing_count = total_in_series - owned
    
    return {
        "owned": owned,
        "total": total_in_series,
        "missing": missing_count,
        "completion_percent": completion_pct
    }
```

### 2. Find Missing Sequence Numbers
```python
def find_missing_sequence_numbers(
    library_books: List[Dict],
    series_name: str,
    total_in_series: int
) -> List[int]:
    """Identify which book numbers are missing from series"""
    owned_numbers = set()
    for book in library_books:
        if book.get("series") == series_name:
            seq = book.get("seriesSequence", "").strip()
            if seq and seq.isdigit():
                owned_numbers.add(int(seq))
    
    missing = [n for n in range(1, total_in_series + 1) 
               if n not in owned_numbers]
    return missing
```

### 3. Duplicate Detection
```python
def is_already_queued(
    db: Session,
    title: str,
    author: str
) -> bool:
    """Check if book is already in download queue"""
    existing = db.query(Download).filter(
        Download.title.ilike(f"%{title}%"),
        Download.author.ilike(f"%{author}%"),
        Download.status.in_(["queued", "downloading"])
    ).first()
    return existing is not None
```

---

## TESTING STRATEGY

### Unit Tests
```python
# test_gap_analyzer.py
def test_calculate_series_completion():
    library = [
        {"title": "Book 1", "series": "Series A", "seriesSequence": "1"},
        {"title": "Book 2", "series": "Series A", "seriesSequence": "2"},
    ]
    result = calculate_series_completion(library, "Series A", 5)
    assert result["completion_percent"] == 40.0
    assert result["missing"] == 3

def test_find_missing_sequence():
    library = [
        {"series": "Series A", "seriesSequence": "1"},
        {"series": "Series A", "seriesSequence": "3"},
    ]
    missing = find_missing_sequence_numbers(library, "Series A", 5)
    assert missing == [2, 4, 5]
```

### Integration Tests
```python
# test_gap_analyzer_integration.py
@pytest.mark.asyncio
async def test_full_analysis_workflow():
    analyzer = AudiobookGapAnalyzer()
    result = await analyzer.run_full_analysis()
    
    assert result["success"]
    assert result["stats"]["gaps_identified"] > 0
    assert "downloads_queued" in result
```

---

## CONFIGURATION

Add to `backend/config.py`:

```python
# Gap Analysis Settings
GAP_ANALYSIS_ENABLED: bool = True
GAP_ANALYSIS_SCHEDULE: str = "0 1 * * *"  # Daily 1:00 AM
GAP_ANALYSIS_MAX_DOWNLOADS_PER_RUN: int = 10
GAP_ANALYSIS_SERIES_PRIORITY: bool = True
GAP_ANALYSIS_AUTHOR_PRIORITY: bool = False

# MAM Search Quality Filters
MAM_MIN_SEEDS: int = 1
MAM_MIN_FILE_SIZE_MB: int = 100
MAM_MAX_FILE_SIZE_GB: int = 50
```

---

## DEPENDENCIES (add to requirements.txt if missing)

```
# Ensure these are installed:
SQLAlchemy
aiohttp
crawl4ai
qbittorrentapi
python-dotenv
requests
beautifulsoup4
tenacity
apscheduler
fastapi
pydantic
```

---

## NEXT STEPS

1. Create `audiobook_gap_analyzer.py` with core orchestration logic
2. Implement gap detection (Phase 1)
3. Implement MAM search (Phase 2)
4. Implement download queuing (Phase 3)
5. Add REST API endpoint for manual triggering
6. Add scheduler task for automation
7. Write and run integration tests
8. Monitor production runs and refine

---

## REFERENCES

- Full Architecture: `/home/user/MAMcrawler/CODEBASE_ANALYSIS.md`
- Quick Reference: `/home/user/MAMcrawler/CODEBASE_QUICK_REFERENCE.md`
- Database Schema: `/home/user/MAMcrawler/database_schema.sql`
- Example Orchestrator: `/home/user/MAMcrawler/master_audiobook_manager.py`

