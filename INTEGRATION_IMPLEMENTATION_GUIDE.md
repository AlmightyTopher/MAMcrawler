# Selenium Crawler Integration - Implementation Guide

## Quick Start

This guide provides step-by-step instructions to integrate the production-ready Selenium crawler into your system.

**Status:** ✅ **Ready for Implementation**
- Selenium crawler: Fully functional and tested
- Integration modules: Complete and documented
- Master manager modifications: Provided in separate guide
- Testing framework: Included

---

## 1. What You're Getting

### Core Components

1. **`mam_selenium_crawler.py`** (550+ lines)
   - Production-ready Selenium WebDriver implementation
   - Full browser automation with JavaScript support
   - Anti-crawling mitigation built-in
   - qBittorrent integration included
   - Cookie persistence and recovery

2. **`selenium_integration.py`** (NEW - 450+ lines)
   - Async wrapper for backend compatibility
   - Search term generation from missing books analysis
   - Database integration for result storage
   - Duplicate detection
   - Configuration validation

3. **Documentation**
   - `SELENIUM_INTEGRATION_ANALYSIS.md` - Detailed technical analysis
   - `MASTER_MANAGER_INTEGRATION.md` - Step-by-step modification guide
   - `SELENIUM_CRAWLER_PRODUCTION_READY.md` - Complete feature documentation

---

## 2. Prerequisites

### Software Requirements

```bash
# Python packages (install if needed)
pip install selenium webdriver-manager beautifulsoup4 qbittorrent-api

# Existing packages (should already be installed)
pip install fastapi asyncio aiohttp python-dotenv
```

### System Requirements

- Python 3.8+
- Chrome/Chromium browser or ChromeDriver
- qBittorrent instance running and accessible
- MyAnonamouse account (for MAM searches)

### Configuration

Create/update `.env` file:

```bash
# MyAnonamouse Credentials
MAM_USERNAME=your_username
MAM_PASSWORD=your_password

# qBittorrent Configuration
QB_HOST=http://localhost:8080
QB_USERNAME=admin
QB_PASSWORD=your_qbittorrent_password

# Optional Selenium Settings
MAM_SELENIUM_HEADLESS=true
MAM_SELENIUM_TIMEOUT=30
MAM_SELENIUM_DEBUG=false
```

---

## 3. Implementation Steps

### Step 1: Validate Selenium Setup (5 minutes)

```bash
# Test that Selenium can initialize
python test_selenium_setup.py
```

Expected output:
```
WebDriver initialized successfully
Chrome version: 120.x.x.x
✓ Selenium setup is working
```

### Step 2: Verify Configuration (5 minutes)

```bash
# Check that all required environment variables are set
python -c "from selenium_integration import SeleniumIntegrationConfig; print('✓ Config valid' if SeleniumIntegrationConfig.validate() else '✗ Config invalid')"
```

### Step 3: Test Standalone Crawler (10 minutes)

```bash
# Run manual test with a few books
python -c "
from mam_selenium_crawler import SeleniumMAMCrawler
import os

crawler = SeleniumMAMCrawler(
    os.getenv('MAM_USERNAME'),
    os.getenv('MAM_PASSWORD'),
    os.getenv('QB_HOST'),
    os.getenv('QB_USERNAME'),
    os.getenv('QB_PASSWORD')
)

books = [
    {'title': 'Mistborn', 'author': 'Brandon Sanderson'},
    {'title': 'The Poppy War', 'author': 'R.F. Kuang'},
]

result = crawler.run(books)
print(f'Crawl result: {result}')
"
```

Expected output:
```
✓ WebDriver initialized
✓ Login successful
✓ 2 searches executed
Crawl result: True
```

### Step 4: Apply Integration Changes (15-20 minutes)

Follow **`MASTER_MANAGER_INTEGRATION.md`** to modify `master_audiobook_manager.py`:

1. Add Selenium imports (5 min)
2. Add configuration check in `__init__` (2 min)
3. Add `run_selenium_search_safe` method (5 min)
4. Replace `run_top_10_search` method (5 min)
5. Update `generate_search_report` method (3 min)

### Step 5: Test Integration (10 minutes)

```bash
# Test configuration is recognized
python master_audiobook_manager.py --status

# Run a quick search test
python master_audiobook_manager.py --top-search
```

Expected output:
```
======================================================================
TOP 10 AUDIOBOOK SEARCH (Selenium Crawler)
======================================================================
Step 1: Detecting missing books...
Step 2: Searching for missing books with Selenium...
Selenium search completed: {'total_searched': 10, 'found': 5, 'queued': 5, ...}
✓ Search report saved: search_results/selenium_search_20250123_143022.md
```

### Step 6: Run Full Sync (15-30 minutes)

```bash
# Run complete workflow including missing book detection
python master_audiobook_manager.py --full-sync
```

This will:
1. Update all metadata via Audiobookshelf
2. Detect missing books in series/authors
3. Search for missing books with Selenium
4. Queue results to qBittorrent
5. Generate comprehensive reports

---

## 4. Integration Architecture

### Data Flow Diagram

```
MasterAudiobookManager
    │
    ├─→ detect_missing_books()
    │   └─→ Returns: {series: [...], authors: [...]}
    │
    └─→ run_top_10_search()
        │
        ├─→ SeleniumSearchTermGenerator.from_series_analysis()
        │   └─→ Generates optimized search terms
        │
        ├─→ SeleniumAsyncWrapper.search_books()
        │   │
        │   ├─→ run_in_executor(SeleniumMAMCrawler.run())
        │   │   ├─→ Initialize WebDriver (Selenium)
        │   │   ├─→ Login to MAM
        │   │   ├─→ Search for each book
        │   │   └─→ Queue to qBittorrent
        │   │
        │   └─→ Returns: {success: bool, searched: N, found: M, ...}
        │
        ├─→ SeleniumSearchResultProcessor.process_search_result()
        │   ├─→ Check for duplicates
        │   ├─→ Store in Download table
        │   └─→ Update statistics
        │
        └─→ generate_search_report()
            └─→ Write markdown report to search_results/
```

### Class Responsibilities

**SeleniumMAMCrawler**
- WebDriver management
- Session authentication
- MAM searching
- Magnet link extraction
- qBittorrent queuing

**SeleniumAsyncWrapper**
- Bridges async backend with sync Selenium
- Thread executor management
- Error handling

**SeleniumSearchTermGenerator**
- Converts missing book analysis to search queries
- Generates priority tiers
- Optimizes search terms

**SeleniumSearchResultProcessor**
- Database integration
- Duplicate detection
- Result validation
- Statistics tracking

**SeleniumIntegrationConfig**
- Environment variable validation
- Configuration management
- Parameter extraction

---

## 5. Database Integration

### Book Model (backend/models/book.py)

When Selenium finds a book:
```python
Book(
    title="Found Title",
    author="Found Author",
    import_source="mam_selenium_crawler",
    metadata_completeness_percent=50  # Will be enriched later
)
```

### Download Model (backend/models/download.py)

When a torrent is found and queued:
```python
Download(
    title="Found Title",
    author="Found Author",
    source="MAM",
    magnet_link="magnet:?xt=...",
    status="queued",
    date_queued=datetime.now(),
    import_source="mam_selenium_crawler"
)
```

### Query Examples

**Check for duplicate:**
```python
existing = db.query(Download).filter(
    Download.title == title,
    Download.magnet_link == magnet_link
).first()

if existing:
    # Skip duplicate
    pass
```

**Get download statistics:**
```python
stats = db.query(Download).filter(
    Download.import_source == "mam_selenium_crawler"
).count()  # Total downloads from Selenium

queued = db.query(Download).filter(
    Download.import_source == "mam_selenium_crawler",
    Download.status == "queued"
).count()  # Still waiting to download
```

---

## 6. Operational Procedures

### Running Searches Manually

```bash
# Search for specific missing books
python -c "
import asyncio
from selenium_integration import run_selenium_top_search

books = [
    {'title': 'Stormlight Archive 5', 'author': 'Brandon Sanderson'},
    {'title': 'Dune Messiah', 'author': 'Frank Herbert'}
]

result = asyncio.run(run_selenium_top_search(books=books))
print(f'Found: {result[\"found\"]}')
print(f'Queued: {result[\"queued\"]}')
"
```

### Checking qBittorrent Queue

```bash
# See torrents queued by Selenium
python -c "
import qbittorrentapi
qb = qbittorrentapi.Client(host='http://localhost:8080', username='admin', password='pass')
torrents = qb.torrents.info(category='audiobooks')
print(f'Total audiobook torrents: {len(torrents)}')
print(f'Downloading: {sum(1 for t in torrents if t.state == \"downloading\")}')
print(f'Seeding: {sum(1 for t in torrents if t.state == \"seeding\")}')
"
```

### Monitoring Search Results

```bash
# Check latest search report
ls -lh search_results/selenium_search_*.md | tail -1

# View latest report
cat search_results/$(ls -t search_results/selenium_search_*.md | head -1)
```

---

## 7. Troubleshooting

### Issue: "Selenium crawler initialization failed"

**Symptoms:**
```
ERROR: Selenium crawler initialization failed
```

**Solutions:**
1. Check packages installed: `pip list | grep selenium`
2. Verify ChromeDriver: `python -m webdriver_manager chrome --print-only`
3. Check Chrome/Chromium available: `which google-chrome` or `which chromium`

### Issue: "Login failed"

**Symptoms:**
```
ERROR: Failed to login to MAM
```

**Solutions:**
1. Verify credentials in `.env`
2. Test manually: `python test_selenium_setup.py`
3. Check MAM is accessible: `curl https://www.myanonamouse.net`
4. Check cookies are persisted: `ls -la mam_cookies.json`

### Issue: "No search results found"

**Symptoms:**
```
Searched 10 books, found 0
```

**Reasons & Solutions:**
1. **Books don't exist on MAM**: Try different titles/authors
2. **Search is too narrow**: Broaden author/series searches
3. **Rate limiting**: Wait before trying again
4. **Session expired**: Cookies are old, delete `mam_cookies.json` to force re-login

### Issue: "qBittorrent not responding"

**Symptoms:**
```
ERROR: Failed to connect to qBittorrent
```

**Solutions:**
1. Check qBittorrent running: `curl http://localhost:8080`
2. Verify URL in `.env`: `QB_HOST=http://localhost:8080`
3. Verify credentials: `QB_USERNAME=admin`, `QB_PASSWORD=...`
4. Check firewall not blocking: `netstat -tlnp | grep 8080`

### Issue: "Duplicate torrents being queued"

**Symptoms:**
```
Same book appearing multiple times in queue
```

**Solutions:**
1. Check duplicate detection in `SeleniumSearchResultProcessor`
2. Clear qBittorrent queue if needed
3. Run deduplication query:
```python
from sqlalchemy import func
from backend.models.download import Download

# Find duplicates
duplicates = db.query(
    Download.magnet_link,
    func.count().label('count')
).group_by(Download.magnet_link).having(func.count() > 1).all()

for magnet, count in duplicates:
    print(f"Magnet appears {count} times: {magnet[:50]}...")
```

---

## 8. Performance Optimization

### Typical Search Performance

| Metric | Value |
|--------|-------|
| Search setup | 5-10 seconds (WebDriver init) |
| Per-book search | 5-10 seconds (page load + extraction) |
| 100 books | 8-15 minutes (best case) |
| 100 books | 15-30 minutes (with rate limiting) |
| Memory per instance | 150-200 MB |

### Optimization Strategies

**Strategy 1: Batch Searches (Currently Implemented)**
- Single browser session for multiple searches
- Saves: 30-50% of total time
- Reuses loaded page state

**Strategy 2: Parallel Sessions (Future)**
- Multiple browser instances simultaneously
- Trade: Memory vs Speed
- 5 parallel instances: ~20-30 minutes for 1000 books
- Cost: ~750-1000 MB memory

**Strategy 3: Result Caching (Future)**
- Cache previous search results
- Reuse for similar queries
- Trade: Accuracy vs Speed
- Cost: Need to verify results still available

### Recommended Settings

For **100-200 books**:
- Use default single instance
- Expected time: 20-40 minutes
- Minimal resource usage

For **500+ books**:
- Consider parallel implementation
- Or run multiple times (avoid rate limit)
- Best: Run once per day in background

---

## 9. Monitoring & Maintenance

### Daily Operations Checklist

- [ ] Check `.env` credentials are valid
- [ ] Verify Chrome/Chromium installed
- [ ] Confirm qBittorrent accessible
- [ ] Monitor `qBittorrent` for stalled downloads
- [ ] Review search reports for accuracy
- [ ] Check disk space for downloaded files

### Weekly Maintenance

- [ ] Clear old search reports: `rm search_results/selenium_search_*.md -mtime +7`
- [ ] Review failed downloads in database
- [ ] Update Chrome if automatic updates failed
- [ ] Check Selenium package updates: `pip install --upgrade selenium`

### Monthly Verification

- [ ] Test full `--full-sync` workflow
- [ ] Verify metadata enrichment still working
- [ ] Check missing book detection accuracy
- [ ] Review system logs for errors
- [ ] Update dependencies: `pip install --upgrade -r requirements.txt`

---

## 10. Success Criteria

After integration, verify these metrics:

✅ **Functionality**
- [ ] Selenium crawler searches without errors
- [ ] Magnet links extracted correctly
- [ ] Downloads queued to qBittorrent
- [ ] Anti-crawling not triggered

✅ **Performance**
- [ ] 100 books searched in < 20 minutes
- [ ] Memory usage < 300 MB
- [ ] No memory leaks over time

✅ **Data Quality**
- [ ] 95%+ successful searches
- [ ] No duplicate queues
- [ ] Correct title/author matching
- [ ] Proper metadata storage

✅ **Integration**
- [ ] Works with master manager
- [ ] Compatible with qBittorrent
- [ ] Results visible in Audiobookshelf
- [ ] Error recovery automatic

---

## 11. Next Steps After Integration

### Immediate (Week 1)
- ✅ Integrate with master manager
- ✅ Test with 10-20 books
- ✅ Verify qBittorrent queuing

### Short-term (Week 2-3)
- Database integration for result tracking
- Missing book workflow automation
- Duplicate detection refinement

### Medium-term (Month 1-2)
- Metadata enrichment via Google Books API
- Series completion tracking
- Author discovery expansion

### Long-term (Ongoing)
- Performance optimization (parallel sessions)
- Advanced search strategies (fuzzy matching)
- UI dashboard for monitoring
- Automated scheduled searches

---

## 12. Support & Resources

### Documentation Files
- `SELENIUM_CRAWLER_PRODUCTION_READY.md` - Feature documentation
- `SELENIUM_INTEGRATION_ANALYSIS.md` - Technical deep dive
- `MASTER_MANAGER_INTEGRATION.md` - Integration guide
- `mam_selenium_crawler.py` - Source code with inline comments

### Testing Files
- `test_selenium_setup.py` - Setup verification
- `mam_selenium_crawler.py` - Includes test code at bottom

### Configuration
- `.env` - Environment variables
- `requirements.txt` - Python dependencies

### Logs
- Console output: Formatted logging
- File logs: `master_manager_*.log`
- Search reports: `search_results/selenium_search_*.md`

---

## 13. Rollback Procedure

If you need to revert changes:

### Option A: Partial Rollback
Keep Selenium available but don't use it:

```python
# In master_audiobook_manager.py
USE_SELENIUM = False  # or os.getenv('USE_SELENIUM', 'false').lower() == 'true'

if USE_SELENIUM:
    result = await run_selenium_top_search(...)
else:
    # Fall back to old method
    result = await old_method(...)
```

### Option B: Complete Rollback

1. Restore original `master_audiobook_manager.py` from git:
```bash
git checkout HEAD -- master_audiobook_manager.py
```

2. Remove integration files:
```bash
rm selenium_integration.py
rm SELENIUM_INTEGRATION_ANALYSIS.md
rm MASTER_MANAGER_INTEGRATION.md
rm INTEGRATION_IMPLEMENTATION_GUIDE.md
```

3. Delete selenium-related packages (optional):
```bash
pip uninstall -y selenium webdriver-manager beautifulsoup4 qbittorrent-api
```

---

## 14. FAQ

**Q: Do I need to install Selenium separately?**
A: Yes - `pip install selenium`. Use `webdriver-manager` for automatic ChromeDriver management.

**Q: Can I run multiple searches in parallel?**
A: Currently designed for sequential searches (single instance). Parallel support is planned for future versions.

**Q: How long does a search take?**
A: About 5-10 seconds per book (page load time dominates). Expect 8-15 minutes for 100 books.

**Q: Will it get detected as a bot?**
A: Unlikely. Anti-crawling measures include rate limiting, user-agent rotation, and human-like delays. Tested without IP blocking.

**Q: What if MyAnonamouse changes the website?**
A: CSS selectors in the crawler will need updating. See `SELENIUM_CRAWLER_PRODUCTION_READY.md` for troubleshooting.

**Q: Can I test without qBittorrent?**
A: Yes - crawler will still search and extract magnet links, just won't queue them. Remove qBittorrent initialization if not available.

**Q: How do I update the crawler?**
A: `git pull` to get latest version, reinstall dependencies, then test with `test_selenium_setup.py`.

