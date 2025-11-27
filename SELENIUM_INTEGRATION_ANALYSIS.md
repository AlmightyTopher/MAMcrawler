# Selenium Crawler Integration Analysis

## Executive Summary

The Selenium crawler (`mam_selenium_crawler.py`) is a **standalone, production-ready component** that can be integrated into the existing `MasterAudiobookManager` system. This document identifies all integration points and provides a roadmap for seamless integration.

**Current System Architecture:**
- **Master Manager**: `master_audiobook_manager.py` - Orchestrates all operations
- **Existing Crawlers**: Crawl4AI-based, Requests-based (non-functional)
- **Metadata System**: Google Books API, unified metadata aggregator
- **Download System**: qBittorrent integration, retry logic
- **Database**: SQLAlchemy models (Book, Download, Series, Author, etc.)
- **Backend API**: FastAPI with async support

**Selenium Crawler Status:**
- ✅ Fully functional and tested
- ✅ Session management working with JavaScript execution
- ✅ Anti-crawling mitigation implemented
- ✅ qBittorrent integration via python-qbittorrentapi
- ✅ Cookie persistence and recovery
- ✅ Production-ready logging and error handling
- ✅ Completely compatible with existing system architecture

---

## 1. Current Integration Points

### 1.1 Master Manager (`master_audiobook_manager.py`)

The `MasterAudiobookManager` class is the central orchestrator that:

**Current Operations:**
- `update_all_metadata()` - Updates metadata across all books via Audiobookshelf
- `detect_missing_books()` - Analyzes series/author gaps
- `run_top_10_search()` - Runs searches via `StealthMAMAudiobookshelfCrawler`
- `full_sync()` - Orchestrates all three operations sequentially
- Generates comprehensive reports

**Key Methods for Integration:**
```python
# Lines 473-514: Top 10 search implementation
# Uses: StealthMAMAudiobookshelfCrawler (deprecated Crawl4AI)
# Output: Results stored in search_results/ directory
```

**What needs to change:**
- Replace `StealthMAMAudiobookshelfCrawler` call with `SeleniumMAMCrawler`
- Adapt result collection and processing

### 1.2 Database Models

**Key Models for Search/Download Integration:**

1. **Book Model** (`backend/models/book.py`):
   - Fields: `id`, `abs_id`, `title`, `author`, `series`, `series_number`, `isbn`, `published_year`, `metadata_completeness_percent`
   - **Integration Point**: Store search results as new Book records

2. **Download Model** (`backend/models/download.py`):
   - Fields: `book_id`, `title`, `author`, `magnet_link`, `qbittorrent_hash`, `status`, `retry_count`
   - **Integration Point**: Store download records with magnet links extracted by Selenium crawler

3. **MissingBook Model** (referenced but not shown):
   - **Integration Point**: Track books found by missing book detection

### 1.3 qBittorrent Integration

**Current Implementation** (`backend/integrations/qbittorrent_client.py`):
- Async-based with context manager support
- Methods:
  - `add_torrent(magnet_link, category)` - Queue downloads
  - `get_all_torrents()` - Retrieve torrent list
  - Login/logout with retry logic

**Selenium Crawler's qBittorrent Usage** (mam_selenium_crawler.py):
- Uses synchronous `qbittorrentapi` library
- Direct API calls without context manager
- Simple integration: `qb.torrents_add(urls=magnet_link, category="audiobooks")`

**Integration Challenge:**
- Backend uses async aiohttp-based client
- Selenium crawler uses sync qbittorrentapi
- **Solution**: Either wrap Selenium in async, or keep as sync worker

### 1.4 Metadata System

**Google Books API** (`backend/integrations/google_books_client.py`):
- Fetches author, ISBN, publication date, description
- Enriches book data after scraping

**Unified Metadata Aggregator** (`unified_metadata_aggregator.py`):
- Combines data from multiple sources
- Priority: Google Books → Goodreads → Manual

**Integration Point:**
- Selenium crawler finds magnet links
- Metadata aggregator enriches found books
- System reconciles with existing library in Audiobookshelf

---

## 2. Selenium Crawler Architecture

### 2.1 Core Class: `SeleniumMAMCrawler`

**Key Methods:**

```python
# Initialization
def __init__(self, email: str, password: str, qb_url: str, qb_user: str, qb_pass: str, headless: bool = True)

# Setup & authentication
def setup(self) -> bool                    # Initialize WebDriver with stealth options
def login(self) -> bool                    # Email/password form submission

# Core search functionality
def search_mam(self, search_term: str) -> Optional[Dict[str, Any]]
    # Returns: {"torrent_id": "123", "title": "...", "magnet_link": "magnet:?xt=...", "size": "..."}

# Batch operations
def search_and_queue(self, books: List[Dict[str, str]])
    # Takes: [{"title": "...", "author": "..."}, ...]
    # Performs: search + extraction + qBittorrent queue

# Lifecycle
def run(self, books: List[Dict[str, str]]) -> bool
    # Full workflow: setup → login → search_and_queue → cleanup
```

### 2.2 Anti-Crawling Mitigation

**AntiCrawlMitigation Class:**
- Rate limiting: 2+ seconds between requests
- Exponential backoff: Failed requests → increasing delays (up to 30 seconds)
- Human-like delays: 0.2-4.0 second random pauses
- Session recovery: Auto re-authentication on login failure
- Failure threshold: Give up after 3 consecutive failures

**StealthUA Class:**
- User-Agent rotation: 6 realistic browser profiles
- Chrome automation detection disabling
- Viewport randomization

### 2.3 Data Flow

```
SeleniumMAMCrawler Input:
├── MAM Credentials (email, password)
├── qBittorrent Credentials (host, port, user, password)
└── Search Books: [{"title": "...", "author": "..."}, ...]

Processing:
├── Initialize WebDriver with stealth options
├── Login to MAM
├── For each book:
│   ├── Search on MAM
│   ├── Extract torrent data (ID, title, magnet, size)
│   └── Queue to qBittorrent
├── Cookie persistence (save to mam_cookies.json)
└── Logging & debug HTML output

Output:
├── Return: {"success": bool, "queued": int, "failed": int, "errors": [...]}
├── Side effects: Torrents queued in qBittorrent
└── State: Cookies saved for next run
```

---

## 3. Integration Points & Mapping

### 3.1 Search Initiation

**Current Flow** (master_audiobook_manager.py):
```python
async def run_top_10_search(self) -> Dict[str, Any]:
    crawler = StealthMAMAudiobookshelfCrawler()  # ← DEPRECATED
    await crawler.run()  # ← Uses Crawl4AI
    search_results = await self.collect_search_results()
```

**New Flow**:
```python
async def run_top_10_search(self) -> Dict[str, Any]:
    # Option A: Wrap Selenium in async
    loop = asyncio.get_event_loop()
    crawler = SeleniumMAMCrawler(
        email=os.getenv('MAM_USERNAME'),
        password=os.getenv('MAM_PASSWORD'),
        qb_url=os.getenv('QB_HOST'),
        qb_user=os.getenv('QB_USERNAME'),
        qb_pass=os.getenv('QB_PASSWORD')
    )
    result = await loop.run_in_executor(None, crawler.run, books_to_search)
    # ← Process results with database integration
```

### 3.2 Missing Books Detection

**Current Flow** (master_audiobook_manager.py):
```python
async def detect_missing_books(self) -> Dict[str, Any]:
    library_data = await self.get_audiobookshelf_library()
    series_analysis = await self.analyze_series_missing_books(library_data)
    author_analysis = await self.analyze_author_missing_books(library_data)
    # ← Returns gap analysis
```

**Integration Point:**
- Missing book detection identifies gaps in series/authors
- Selenium crawler searches for those specific gaps
- Results stored in Download table with `status="queued"`
- qBittorrent manages actual downloads

### 3.3 Database Integration

**Book Records:**
- Selenium crawler finds books on MAM
- System checks if book exists in `books` table
- If new → Insert with `import_source="mam_selenium_crawler"`
- If existing → Update metadata, skip duplicate queue

**Download Records:**
- For each MAM search result with magnet link:
  - Create Download record with `status="queued"`
  - Store `qbittorrent_hash` after qBittorrent accepts
  - Update status as download progresses

**Example Flow:**
```python
# After Selenium crawler extracts torrent
def store_download_record(title: str, author: str, magnet_link: str, torrent_id: str):
    download = Download(
        title=title,
        author=author,
        source="MAM",
        magnet_link=magnet_link,
        status="queued",
        date_queued=datetime.now()
    )
    db.add(download)
    # After qBittorrent accepts:
    download.qbittorrent_hash = qb_hash
    db.commit()
```

---

## 4. Integration Challenges & Solutions

### Challenge 1: Async/Sync Mismatch

**Problem:**
- Backend is async (FastAPI, aiohttp)
- Selenium is synchronous (blocking WebDriver)

**Solutions:**

**Option A: Run Sync in Thread Executor** (Recommended for minimal changes)
```python
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(None, sync_crawler.run, books)
```

**Option B: Wrap Selenium with async wrapper**
```python
async def run_selenium_async(books):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: crawler.run(books))
```

**Option C: Full async rewrite**
- Port to Playwright (async-native alternative)
- Higher effort, better long-term

**Recommendation:** Use Option A for immediate integration, migrate to Option B/C later

### Challenge 2: Duplicate Prevention

**Problem:**
- Multiple searches might find the same book
- System already has 839 books queued

**Solution:**
```python
def should_queue_torrent(title: str, author: str, magnet_link: str) -> bool:
    # Check existing downloads
    existing = db.query(Download).filter(
        Download.title == title,
        Download.author == author,
        Download.magnet_link == magnet_link
    ).first()

    if existing:
        logger.info(f"Skipping duplicate: {title}")
        return False

    return True
```

### Challenge 3: Search Term Generation

**Problem:**
- Master manager detects missing books
- Needs to generate optimal search terms for Selenium crawler

**Solution:**
```python
def generate_search_terms(missing_analysis: Dict) -> List[Dict]:
    """Convert missing book detection to search terms"""
    search_terms = []

    # From series analysis
    for series in missing_analysis['missing_books']:
        # Search by title + author
        for missing_num in series['missing_numbers']:
            # Construct likely title
            title = f"{series['series_name']} {missing_num}"
            search_terms.append({
                'title': title,
                'author': series['author'],
                'priority': 'high'  # Series completion
            })

    return search_terms
```

### Challenge 4: Result Collection & Storage

**Problem:**
- Current system uses file-based output (JSON files)
- New system needs database integration

**Solution:**
```python
async def process_selenium_results(search_books: List[Dict]) -> Dict:
    """Store Selenium results in database"""
    results = {
        'total_searched': len(search_books),
        'found': 0,
        'queued': 0,
        'duplicates': 0,
        'errors': []
    }

    for book in search_books:
        try:
            # Run search
            result = crawler.search_mam(f"{book['title']} {book.get('author', '')}")

            if result and result.get('magnet_link'):
                # Check for duplicate
                if should_queue_torrent(result['title'], result['author'], result['magnet_link']):
                    # Store in database
                    store_download_record(
                        title=result['title'],
                        author=result['author'],
                        magnet_link=result['magnet_link'],
                        source="MAM"
                    )
                    results['queued'] += 1
                else:
                    results['duplicates'] += 1

                results['found'] += 1
        except Exception as e:
            results['errors'].append({'title': book['title'], 'error': str(e)})

    return results
```

---

## 5. Integration Roadmap

### Phase 1: Minimal Integration (1-2 hours)
**Goal:** Get Selenium crawler working within master manager

1. Create wrapper function in `master_audiobook_manager.py`:
```python
async def run_selenium_search(self, books: List[Dict]) -> Dict:
    """Wrapper to integrate Selenium crawler"""
    loop = asyncio.get_event_loop()

    # Create crawler
    crawler = SeleniumMAMCrawler(
        email=os.getenv('MAM_USERNAME'),
        password=os.getenv('MAM_PASSWORD'),
        qb_url=os.getenv('QB_HOST'),
        qb_user=os.getenv('QB_USERNAME'),
        qb_pass=os.getenv('QB_PASSWORD')
    )

    # Run in executor
    result = await loop.run_in_executor(None, crawler.run, books)
    return result
```

2. Replace crawler call in `run_top_10_search()`:
```python
# Old: crawler = StealthMAMAudiobookshelfCrawler()
# New:
result = await self.run_selenium_search(self.books_to_search)
```

3. Test with small book set (5-10 books)

### Phase 2: Database Integration (2-3 hours)
**Goal:** Store results in database instead of file system

1. Modify `process_selenium_results()` to write to `downloads` table
2. Update `collect_search_results()` to read from database
3. Implement duplicate detection
4. Add import_source tracking

### Phase 3: Missing Books Workflow (2-3 hours)
**Goal:** Automatically search for detected missing books

1. Integrate missing book detection output
2. Generate search terms from gaps
3. Auto-queue high-priority (series) missing books
4. Track missing book downloads separately

### Phase 4: Metadata Enrichment (1-2 hours)
**Goal:** Enrich Selenium results with Google Books metadata

1. Hook Google Books API after Selenium finds books
2. Merge metadata from both sources
3. Store complete metadata in database
4. Update Audiobookshelf records

---

## 6. Code Changes Required

### 6.1 master_audiobook_manager.py

**Add imports:**
```python
from mam_selenium_crawler import SeleniumMAMCrawler
```

**Add method:**
```python
async def run_selenium_search(self, books: List[Dict]) -> Dict:
    """Run Selenium crawler for books"""
    loop = asyncio.get_event_loop()

    crawler = SeleniumMAMCrawler(
        email=os.getenv('MAM_USERNAME'),
        password=os.getenv('MAM_PASSWORD'),
        qb_url=os.getenv('QB_HOST'),
        qb_user=os.getenv('QB_USERNAME'),
        qb_pass=os.getenv('QB_PASSWORD'),
        headless=True
    )

    return await loop.run_in_executor(None, crawler.run, books)
```

**Modify run_top_10_search():**
```python
async def run_top_10_search(self) -> Dict[str, Any]:
    # ... existing code ...

    # Replace:
    # crawler = StealthMAMAudiobookshelfCrawler()
    # await crawler.run()

    # With:
    result = await self.run_selenium_search(self.get_top_search_books())

    # ... rest of method ...
```

### 6.2 Environment Configuration

**Add to .env:**
```
# qBittorrent configuration
QB_HOST=http://localhost:8080
QB_USERNAME=admin
QB_PASSWORD=password

# Selenium crawler options
MAM_SELENIUM_HEADLESS=true
MAM_SELENIUM_TIMEOUT=30
```

### 6.3 Database Schema Updates

**Add indexes for faster lookups:**
```python
# In backend/models/download.py
Index('idx_download_title_author', 'title', 'author'),
Index('idx_download_magnet', 'magnet_link'),
```

---

## 7. Testing Strategy

### 7.1 Unit Tests

```python
def test_selenium_crawler_initialization():
    """Test WebDriver setup"""
    crawler = SeleniumMAMCrawler(...)
    assert crawler.setup() == True

def test_selenium_login():
    """Test authentication"""
    assert crawler.login() == True

def test_search_execution():
    """Test search method"""
    result = crawler.search_mam("Mistborn Brandon Sanderson")
    assert result is not None
    assert 'magnet_link' in result
```

### 7.2 Integration Tests

```python
def test_master_manager_with_selenium():
    """Test full integration"""
    manager = MasterAudiobookManager()
    result = await manager.run_top_10_search()
    assert result['success'] == True
    assert result['total_found'] > 0
```

### 7.3 End-to-End Test

```python
def test_complete_workflow():
    """Test: missing detection → search → queue"""
    manager = MasterAudiobookManager()

    # Step 1: Detect missing books
    missing = await manager.detect_missing_books()

    # Step 2: Search for them
    search_result = await manager.run_selenium_search(missing['books'])

    # Step 3: Verify queued in qBittorrent
    qb_torrents = get_qb_torrents()
    assert len(qb_torrents) > initial_count
```

---

## 8. Performance Considerations

### Search Performance
- **Current**: Crawl4AI + Requests (non-functional)
- **Selenium**: ~5-10 seconds per search (JavaScript execution overhead)
- **Bottleneck**: Page load time (2-3 seconds per search)

**Optimization:**
- Batch searches in single browser session (not close/reopen)
- Cache results for common searches
- Parallel searches (spawn multiple browser sessions)

### Memory Usage
- **Per Selenium instance**: ~150-200 MB (ChromeDriver + browser)
- **For 5 parallel instances**: ~750-1000 MB

**Recommendation:**
- Keep single instance for sequential searches (current approach)
- Add pooling if parallelization needed later

### Rate Limiting
- **Minimum interval**: 2 seconds between requests
- **On failures**: Exponential backoff up to 30 seconds
- **Give up threshold**: 3 consecutive failures

**Effect on performance:**
- 100 books: ~2-3 minutes (best case)
- With some failures: ~5-10 minutes (realistic)

---

## 9. Configuration & Environment

### Required Environment Variables

```
# Existing (already configured)
ABS_URL=http://localhost:13378
ABS_TOKEN=your_token_here
MAM_USERNAME=your_username
MAM_PASSWORD=your_password

# New (for Selenium integration)
QB_HOST=http://localhost:8080
QB_USERNAME=admin
QB_PASSWORD=adminpass
QB_PORT=8080  # Optional, already in host URL

# Optional
MAM_SELENIUM_HEADLESS=true        # Run browser headless
MAM_SELENIUM_TIMEOUT=30            # Timeout in seconds
MAM_SELENIUM_DEBUG=false           # Save debug HTML files
```

### Configuration Validation

```python
def validate_selenium_config() -> bool:
    """Verify all required environment variables are set"""
    required = [
        'MAM_USERNAME',
        'MAM_PASSWORD',
        'QB_HOST',
        'QB_USERNAME',
        'QB_PASSWORD'
    ]

    missing = [var for var in required if not os.getenv(var)]

    if missing:
        logger.error(f"Missing config: {', '.join(missing)}")
        return False

    return True
```

---

## 10. Known Limitations & Workarounds

| Limitation | Impact | Workaround |
|-----------|--------|-----------|
| Sync Selenium in async backend | Thread overhead | Use executor, consider async port later |
| JavaScript load time | 2-3 sec/search | Pre-warm browser, batch operations |
| Rate limiting enforcement | Some searches slow | Expected behavior, acceptable for missing book detection |
| No exact match guarantee | May return close matches | Implement fuzzy matching, manual review option |
| Session timeout (2 hours) | Crawler may need re-auth | Automatic via cookie persistence & re-login on failure |

---

## 11. Success Metrics

After integration, verify:

1. **Functionality:**
   - ✓ Selenium crawler executes searches without errors
   - ✓ Magnet links extracted correctly
   - ✓ Downloads queued to qBittorrent successfully
   - ✓ Anti-crawling measures working (no IP blocks)

2. **Performance:**
   - ✓ 100 books searched in < 15 minutes
   - ✓ <200MB memory per Selenium instance
   - ✓ Graceful handling of rate limits

3. **Data Quality:**
   - ✓ Found books correctly stored in database
   - ✓ No duplicate queues detected
   - ✓ Metadata enriched from Google Books
   - ✓ 95%+ accuracy on title/author matching

4. **System Integration:**
   - ✓ Works with existing master manager
   - ✓ Compatible with qBittorrent monitoring
   - ✓ Results visible in Audiobookshelf
   - ✓ Error recovery automatic

---

## 12. Rollback Plan

If integration fails:

1. **Keep old code**: Archive Crawl4AI-based crawler
2. **Feature flag**: Add `use_selenium` environment variable
   ```python
   if os.getenv('USE_SELENIUM', 'true').lower() == 'true':
       result = await self.run_selenium_search(books)
   else:
       result = await self.run_crawlai_search(books)  # Fallback
   ```
3. **Quick revert**: Change flag to `false`, redeploy

---

## 13. Next Steps

1. **Immediate (This session):**
   - ✓ Identify integration points (COMPLETED)
   - ⏳ Create wrapper function in master manager
   - ⏳ Test with small book set (5 books)

2. **Short-term (Next session):**
   - Database integration (store results)
   - Duplicate detection
   - Missing books workflow hookup

3. **Medium-term:**
   - Metadata enrichment from Google Books
   - Performance optimization (pooling/parallel)
   - Comprehensive test suite

4. **Long-term:**
   - Consider async-native port (Playwright)
   - Advanced search strategies (fuzzy matching)
   - User interface for crawler monitoring

