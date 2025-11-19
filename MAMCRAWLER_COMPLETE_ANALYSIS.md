# MAMcrawler Complete System Analysis

**Generated:** 2025-11-19
**Analyst:** Claude Code (Sonnet 4.5)
**Purpose:** Comprehensive forensic analysis for AI consumption and system understanding

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Phase 1: Architecture and Module Map](#phase-1-architecture-and-module-map)
3. [Phase 2: Audiobook Pipeline End-to-End](#phase-2-audiobook-pipeline-end-to-end)
4. [Phase 3: Metadata Enrichment and Goodreads](#phase-3-metadata-enrichment-and-goodreads)
5. [Phase 4: Validation, STT, and Duplicate Handling](#phase-4-validation-stt-and-duplicate-handling)
6. [Phase 5: Librarian, Seeding, and Compliance](#phase-5-librarian-seeding-and-compliance)
7. [Phase 6: Configuration Values and Knobs](#phase-6-configuration-values-and-knobs)
8. [Phase 7: Layered Model and Responsibility Boundaries](#phase-7-layered-model-and-responsibility-boundaries)
9. [Phase 8: Machine Readable Spec](#phase-8-machine-readable-spec)

---

## Executive Summary

MAMcrawler is a comprehensive audiobook acquisition and library management system that automates:

1. **Discovery** - Finding audiobooks on MyAnonamouse (MAM) private tracker
2. **Acquisition** - Downloading via qBittorrent with stealth behavior
3. **Enrichment** - Metadata enhancement from multiple providers (Google Books, Goodreads, Hardcover)
4. **Organization** - Integration with Audiobookshelf media server
5. **Completion** - Gap analysis for series and author collections
6. **Compliance** - Respecting MAM rules, ratio management, and seeding requirements

The system consists of 110+ Python files organized into standalone scripts, a backend API (FastAPI), and a frontend dashboard.

---

## Phase 1: Architecture and Module Map

### System at a Glance

```
USER/CRON/SCHEDULER
       ↓
┌─────────────────────────────────────────────────────────┐
│              ORCHESTRATION LAYER                        │
│  master_audiobook_manager.py, audiobook_auto_batch.py   │
│  backend/scheduler/, cron jobs                          │
└─────────────────────────────────────────────────────────┘
       ↓
┌─────────────────────────────────────────────────────────┐
│                CRAWLER LAYER                            │
│  stealth_audiobook_downloader.py                        │
│  audiobook_catalog_crawler.py                           │
│  stealth_mam_crawler.py, mam_crawler.py                 │
└─────────────────────────────────────────────────────────┘
       ↓
┌─────────────────────────────────────────────────────────┐
│              DOWNLOAD LAYER                             │
│  qBittorrent integration (qbittorrentapi)               │
│  Category: "Audiobooks", tags for tracking              │
└─────────────────────────────────────────────────────────┘
       ↓
┌─────────────────────────────────────────────────────────┐
│           METADATA ENRICHMENT LAYER                     │
│  audiobookshelf_metadata_sync.py                        │
│  unified_metadata_aggregator.py                         │
│  goodreads_api_client.py, goodreads_abs_scraper.py      │
└─────────────────────────────────────────────────────────┘
       ↓
┌─────────────────────────────────────────────────────────┐
│              VALIDATION LAYER                           │
│  audiobook_gap_analyzer.py                              │
│  validate_mam_compliance.py                             │
│  Duplicate detection (Audiobookshelf library check)     │
└─────────────────────────────────────────────────────────┘
       ↓
┌─────────────────────────────────────────────────────────┐
│              LIBRARIAN LAYER                            │
│  Audiobookshelf API integration                         │
│  Series linking, metadata updates                       │
│  Library organization and reporting                     │
└─────────────────────────────────────────────────────────┘
```

### Main Subsystems

#### 1. Crawler Subsystem

**Primary Modules:**
- `mam_crawler.py` (43KB) - Base passive crawler with authentication, rate limiting
- `stealth_mam_crawler.py` (21KB) - Human-like behavior simulation
- `stealth_audiobook_downloader.py` (26KB) - Production audiobook downloader
- `audiobook_catalog_crawler.py` - Genre/timespan discovery
- `comprehensive_guide_crawler.py` - Guide extraction for RAG

**Key Classes:**
- `MAMPassiveCrawler` - Base crawler with session management
- `StealthMAMAudiobookDownloader` - Stealth downloader with Audiobookshelf integration

**External Dependencies:**
- `crawl4ai` - Browser automation framework
- `aiohttp` - Async HTTP client
- `beautifulsoup4` / `lxml` - HTML parsing

#### 2. Metadata Enrichment Subsystem

**Primary Modules:**
- `audiobookshelf_metadata_sync.py` (50KB) - Main sync engine
- `unified_metadata_aggregator.py` (4KB) - Multi-provider aggregation
- `goodreads_api_client.py` (14KB) - Goodreads web scraping
- `goodreads_abs_scraper.py` (12KB) - ABS-Goodreads integration
- `dual_goodreads_scraper.py` (18KB) - Enhanced Goodreads scraping

**Key Classes:**
- `AudiobookshelfMetadataSync` - Orchestrates metadata updates
- `GoodreadsClient` - Goodreads web scraper with caching
- `GoodreadsABSScraper` - Scrapes and updates ABS

**External APIs:**
- Google Books API
- Goodreads (web scraping - API deprecated)
- Hardcover API
- Kindle API (via proxy)

#### 3. Gap Analysis Subsystem

**Primary Modules:**
- `audiobook_gap_analyzer.py` (33KB) - Main gap detection
- `master_audiobook_manager.py` (36KB) - Master orchestrator

**Key Classes:**
- `AudiobookGapAnalyzer` - Detects missing books in series/by author
- `MasterAudiobookManager` - Coordinates all operations

**Workflow:**
1. Scan Audiobookshelf library
2. Group by series and author
3. Query Goodreads for complete series lists
4. Identify gaps (missing sequence numbers)
5. Search MAM for missing books
6. Queue downloads to qBittorrent

#### 4. Batch Automation Subsystem

**Primary Modules:**
- `audiobook_auto_batch.py` (25KB) - Weekly batch processor
- `vip_status_manager.py` - VIP/bonus point management

**Key Classes:**
- `AutomatedAudiobookBatch` - Processes genres, filters duplicates, queues downloads
- `VIPStatusManager` - Maintains VIP status and spends bonus points

**Configuration:**
- `audiobook_auto_config.json` - Genre whitelist/blacklist, download settings

#### 5. Compliance Subsystem

**Primary Modules:**
- `validate_mam_compliance.py` (16KB) - Best practices validator

**Key Classes:**
- `MAMComplianceValidator` - Checks configuration against MAM rules

**Configuration:**
- `mam_automation_rules.json` - Seeding requirements, bonus point strategy

#### 6. Backend API Subsystem

**Location:** `backend/`

**Structure:**
```
backend/
├── config.py           # Centralized configuration (Pydantic)
├── main.py             # FastAPI app entry
├── models/             # SQLAlchemy models
│   ├── author.py
│   ├── book.py
│   ├── series.py
│   ├── download.py
│   └── ...
├── services/           # Business logic
│   ├── book_service.py
│   ├── download_service.py
│   ├── metadata_service.py
│   └── ...
├── routes/             # API endpoints
│   ├── books.py
│   ├── downloads.py
│   ├── gaps.py
│   ├── scheduler.py
│   └── ...
├── integrations/       # External service clients
│   ├── audiobookshelf.py
│   ├── qbittorrent.py
│   ├── google_books.py
│   └── prowlarr.py
├── modules/            # Feature modules
│   ├── metadata_correction.py
│   ├── series_completion.py
│   ├── author_completion.py
│   └── discovery.py
└── scheduler/          # APScheduler jobs
```

### Entry Points

| Entry Point | Description | Automation |
|-------------|-------------|------------|
| `master_audiobook_manager.py` | Main orchestrator CLI | Manual/Cron |
| `audiobook_auto_batch.py` | Weekly batch downloads | Scheduled |
| `stealth_audiobook_downloader.py` | Stealth download runner | Manual |
| `audiobook_gap_analyzer.py` | Gap analysis CLI | Cron |
| `audiobookshelf_metadata_sync.py` | Metadata sync runner | Scheduled |
| `validate_mam_compliance.py` | Compliance checker | Manual |
| `backend/main.py` | FastAPI server | Service |

---

## Phase 2: Audiobook Pipeline End-to-End

### How MAMcrawler Decides What to Look For

#### Category Codes (Audiobook Categories on MAM)

From `stealth_audiobook_downloader.py:46-49`:
```python
WHITELISTED_GENRES = {
    'Science Fiction': 'c47',
    'Fantasy': 'c41'
}
```

From `backend/config.py:140-151`:
```python
ENABLED_GENRES: list = [
    "Science Fiction",
    "Fantasy",
    "Mystery",
    "Thriller"
]

DISABLED_GENRES: list = [
    "Romance",
    "Erotica",
    "Self-Help"
]
```

#### Genre Selection Logic

**Whitelist Mode** (`audiobook_auto_batch.py:84-106`):
- Only process genres explicitly listed in `included_genres`
- All other genres are skipped

**Blacklist Mode** (`audiobook_auto_batch.py:108-124`):
- Process all genres except those in `excluded_genres`

#### Time Windows

From `stealth_audiobook_downloader.py:215-230`:
- Default: Last 7 days (`days_back=7`)
- Sort order: `tor[sortType]=snatchedDesc` (top snatched)

From `audiobook_auto_batch.py:126-137`:
- Configurable via `timespan_preference` in config
- Options: "recent", "new", "latest"

#### "Top N" Logic

From `audiobook_auto_batch.py:282-335`:
```python
def select_top_n(self, audiobooks: List[Dict], n: int, genre: str, abs_library=None):
    """Select top N NEW audiobooks (skips duplicates)."""
    max_check = self.config['query_settings'].get('max_check_limit', 100)
    # Checks up to 100 results to find N unique non-duplicates
```

Default: `top_n_per_genre` from config (typically 3-10 per genre)

### Crawler Session Behavior

#### Authentication Flow

From `mam_crawler.py:90-178`:

1. Check session validity (2-hour expiry)
2. If expired, POST to `/takelogin.php` with credentials
3. Validate response contains "logout" or "my account"
4. Store session cookies for subsequent requests

From `stealth_audiobook_downloader.py:308-402`:
- Uses JavaScript injection for form filling
- Simulates mouse movements before typing
- Random delays between keystrokes (600-2500ms)
- Waits 5 seconds after submit

#### Rate Limiting

From `mam_crawler.py:54-56`:
```python
self.min_delay = 3   # seconds
self.max_delay = 10  # seconds
```

From `stealth_audiobook_downloader.py:74-77`:
```python
self.min_delay = 15
self.max_delay = 45
self.scroll_delay = 3
self.read_delay = 8
```

From `backend/config.py:84-86`:
```python
MAM_RATE_LIMIT_MIN: int = 3
MAM_RATE_LIMIT_MAX: int = 10
MAM_MAX_PAGES_PER_SESSION: int = 50
```

#### Stealth Behavior

From `stealth_audiobook_downloader.py:270-306`:
- Mouse movement simulation (4 random movements)
- Smooth scrolling in 4-8 steps
- Random delays between actions (300-3000ms)
- Viewport randomization (6 common resolutions)
- User agent rotation (4 browser strings)

#### Session Termination

- Max 50 pages per session (`MAM_MAX_PAGES_PER_SESSION`)
- Max downloads per run (configurable, default 10)
- Keyboard interrupt saves state for resume

#### Error Handling

From `mam_crawler.py:107-111`:
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(Exception)
)
```

- 3 retry attempts with exponential backoff
- State persistence for resume (`crawler_state.json`, `stealth_audiobook_state.json`)

### Torrent Selection Criteria

#### Seed Thresholds

From `backend/config.py:110`:
```python
MAM_MIN_SEEDS: int = 1
```

From `audiobook_gap_analyzer.py:87`:
```python
'min_seeds': int(os.getenv('MAM_MIN_SEEDS', '1'))
```

#### Title Similarity Thresholds

From `audiobook_gap_analyzer.py:88`:
```python
'title_match_threshold': float(os.getenv('MAM_TITLE_MATCH_THRESHOLD', '0.7'))
```

Uses `SequenceMatcher` for fuzzy matching at 70% threshold.

#### Freeleech/VIP Handling

From `stealth_audiobook_downloader.py:486-509`:
```python
def should_download_torrent(self, torrent: Dict) -> tuple[bool, str]:
    # VIP torrents are always freeleech
    if torrent.get('is_vip', False):
        return True, "VIP torrent (freeleech)"

    # Freeleech torrents
    if torrent.get('is_freeleech', False):
        return True, "Freeleech torrent"

    # Large torrents warrant FL wedge usage
    if self.should_use_fl_wedge(size_text):
        return True, f"Large torrent ({size_text}) - using FL wedge"
```

FL wedge threshold: >1GB (`stealth_audiobook_downloader.py:533`)

#### Duplicate Handling in Search Results

From `audiobook_auto_batch.py:224-280`:
- Loads entire Audiobookshelf library
- Compares incoming title against all existing titles
- Uses substring matching and 60% length similarity
- Cleans titles (removes "unabridged", "audiobook", file extensions)

### Sending to qBittorrent

From `stealth_audiobook_downloader.py:538-575`:
```python
async def download_torrent(self, torrent: Dict) -> bool:
    category = "Audiobooks"
    tags = [torrent['genre'].lower().replace(' ', '_'), "mam_automated"]

    if torrent.get('is_vip'):
        tags.append("vip")
    if torrent.get('is_freeleech'):
        tags.append("freeleech")
    if self.should_use_fl_wedge(torrent.get('size', '')):
        tags.append("fl_wedge")

    self.qb_client.torrents_add(
        urls=[torrent_url],
        category=category,
        tags=tags,
        save_path=self.config.get('download_path', '')
    )
```

From `audiobook_auto_batch.py:337-408`:
- Category from config (`audiobook_auto_config.json`)
- Save path from config
- Supports dry-run mode

### Post-Download Flow

#### Filesystem Organization

Downloads go to qBittorrent's configured save path (typically organized by category):
```
/audiobooks/
├── Science Fiction/
├── Fantasy/
└── ...
```

Audiobookshelf monitors this directory and automatically imports new audiobooks.

#### Audiobookshelf Ingestion

The system relies on Audiobookshelf's folder watching feature:
1. qBittorrent downloads to watched folder
2. Audiobookshelf detects new files
3. Audiobookshelf creates library item
4. Metadata sync runs to enrich the item

#### State Updates

From `stealth_audiobook_downloader.py:599-615`:
```python
self.state['completed'].append({
    'title': torrent['title'],
    'url': torrent['url'],
    'genre': genre_name,
    'reason': reason,
    'added_at': datetime.now().isoformat()
})
```

State files:
- `stealth_audiobook_state.json` - Completed/failed/skipped torrents
- `gap_analyzer_state.json` - Completed searches
- `batch_stats_*.json` - Session statistics

---

## Phase 3: Metadata Enrichment and Goodreads

### Goodreads-Related Modules

#### 1. `goodreads_api_client.py`

**Purpose:** Web scraping client for Goodreads metadata verification

**Key Class:** `GoodreadsClient`

**How Scraping Works:**
- Since official API was deprecated, uses web scraping
- Searches via `https://www.goodreads.com/search`
- Parses HTML with BeautifulSoup

**Rate Limits:**
```python
RATE_LIMIT_DELAY = 0.2  # 5 requests/sec max
```

**Caching:**
```python
def __init__(self, cache_file: str = "goodreads_cache.json"):
    self.cache = self._load_cache()
```
- Cache key: `{title.lower()}|{author.lower()}`
- Persistent disk cache

**Fields Extracted** (from search results):
- `title` - Clean title without series info
- `author` - Author name
- `series_name` - Parsed from title pattern like "Book Title (Series Name, #1)"
- `series_position` - Book number in series
- `goodreads_url` - Link to book page

**Confidence Scoring:**
```python
def verify_metadata(self, audio_title, audio_author, audio_series, audio_sequence):
    # Returns (is_valid, confidence_score, goodreads_metadata)
    # Weights:
    # - Title matching: 50%
    # - Author matching: 40%
    # - Series matching: 5%
    # - Sequence matching: 5%
    # Threshold: 70% for validity
```

#### 2. `goodreads_abs_scraper.py`

**Purpose:** Scrape Goodreads and update Audiobookshelf library

**Key Classes:**
- `AudiobookShelfClient` - ABS API wrapper
- `GoodreadsScraper` - Stealth Goodreads scraper
- `GoodreadsABSScraper` - Orchestrator

**Interaction with Audiobookshelf:**
1. Get all libraries via `/api/libraries`
2. Get books via `/api/libraries/{id}/items`
3. For each book, search Goodreads
4. Update ABS via PATCH `/api/libraries/{lib_id}/items/{book_id}`

**Item Selection:**
- Processes ALL books in library sequentially
- No filtering by metadata completeness

**Write-back Fields:**
```python
metadata_update = {
    'metadata': {
        'rating': goodreads_data.get('goodreads_rating'),
        'ratingCount': goodreads_data.get('rating_count'),
        'reviewsCount': goodreads_data.get('review_count'),
        'goodreads_updated': datetime.now().isoformat()
    }
}
```

#### 3. `unified_metadata_aggregator.py`

**Purpose:** Aggregate metadata from multiple providers with weighted confidence

**Providers and Weights:**
```python
PROVIDERS = {
    "google": "https://www.googleapis.com/books/v1/volumes?q={q}+inauthor:{a}",
    "goodreads": "http://localhost:5555/goodreads/search?query={q}&author={a}",
    "kindle": "http://localhost:5555/kindle/us/search?query={q}&author={a}",
    "hardcover": "https://provider.vito0912.de/hardcover/en/book",
    "lubimyczytac": "http://localhost:3000/search?query={q}&author={a}",
    "audioteka": "http://localhost:3001/search?query={q}&author={a}"
}

WEIGHTS = {
    "google": 1.0,
    "hardcover": 0.9,
    "goodreads": 0.8,
    "kindle": 0.8,
    "audioteka": 0.7,
    "lubimyczytac": 0.6
}
```

**Conflict Resolution:**
```python
def merge(results):
    for f in FIELDS:
        vals = [r[f] for r in results if r.get(f)]
        if not vals: continue
        top = Counter(vals).most_common(1)[0][0]  # Most common value wins
        merged[f] = top
        # Confidence = sum of weights for providers that agree
```

### Pre-Download vs Post-Download Enrichment

#### PRE-DOWNLOAD Enrichment

**Where it happens:** `audiobook_gap_analyzer.py:415-480`

**Purpose:** Use Goodreads to identify missing books in series

```python
async def _get_series_from_goodreads(self, session, series_name, author):
    # Search for series on Goodreads
    # Parse results to find all books in series
    # Return (total_books, [{'title': ..., 'sequence': ...}, ...])
```

**What it does:**
- Queries Goodreads search for series name + author
- Parses titles for series patterns like "(Series Name, #1)"
- Returns complete list of books in series
- Used to calculate gaps before searching MAM

#### POST-DOWNLOAD Enrichment

**Where it happens:** `audiobookshelf_metadata_sync.py:568-675`

**Purpose:** Enrich existing library items with full metadata

**Provider Order:**
1. Google Books API (2 attempts)
2. Goodreads API (2 attempts)
3. Hardcover API (2 attempts)
4. Goodreads scraper fallback

```python
provider_order = ['google', 'goodreads', 'hardcover']

for provider in provider_order:
    for attempt in range(2):
        result = await self.query_provider(provider, title, author)
        if result:
            break
    if provider_data:
        break

# If all APIs fail, use Goodreads scraper fallback
if not provider_data:
    goodreads_scraper_data = await self.search_goodreads_audiobook(title, author)
```

### What Each Location Updates

#### Gap Analyzer (Pre-Download)

**Updates:** Nothing directly - only identifies gaps and searches MAM

**Uses Goodreads for:**
- Finding complete series lists
- Identifying missing sequence numbers

#### Audiobookshelf Metadata Sync (Post-Download)

**Updates:** Audiobookshelf item metadata via API

**Fields Updated** (`audiobookshelf_metadata_sync.py:454-508`):
```python
fields_to_update = {}
# Only update if new data is better or missing
if new_metadata.get('title') and not current_metadata.get('title'):
    fields_to_update['title'] = new_metadata['title']
if new_metadata.get('description') and len(new_desc) > len(current_desc) * 0.8:
    fields_to_update['description'] = new_desc
# Series is always updated if available
if new_metadata.get('series'):
    fields_to_update['series'] = normalized_series
```

#### Master Audiobook Manager

**Updates:** Calls `AudiobookshelfMetadataSync` to update library

```python
async def update_all_metadata(self):
    abs_sync = AudiobookshelfMetadataSync()
    await abs_sync.run()
```

### Goodreads Usage Summary

| Module | Stage | Purpose | Updates |
|--------|-------|---------|---------|
| `audiobook_gap_analyzer.py` | Pre-download | Series completion detection | Nothing (read-only) |
| `unified_metadata_aggregator.py` | Post-download | Multi-source aggregation | Returns merged data |
| `audiobookshelf_metadata_sync.py` | Post-download | Library enrichment | Audiobookshelf API |
| `goodreads_abs_scraper.py` | Post-download | Rating enrichment | Audiobookshelf API |
| `goodreads_api_client.py` | Both | Web scraping client | Local cache file |

### TODOs and Planned Logic

From `audiobook_gap_analyzer.py:482-490`:
```python
async def _identify_author_gaps(self):
    """Identify missing books by author using Goodreads."""
    # For now, we'll skip author gap analysis as it's more complex
    # and would require extensive Goodreads scraping for each author's
    # complete bibliography. This can be implemented in a future version.
    logger.info("  Author gap analysis - feature coming soon")
```

**Planned but not implemented:**
- Full author bibliography scraping
- Author completion logic (beyond just flagging high-volume authors)

---

## Phase 4: Validation, STT, and Duplicate Handling

### Duplicate Detection

#### Primary Implementation: `audiobook_auto_batch.py:224-280`

```python
def is_duplicate(self, audiobook: Dict, abs_library) -> bool:
    incoming_title = audiobook.get('title', '').lower()

    for book_item in abs_library:
        abs_title = metadata.get('title', '').lower()

        # Clean both titles
        clean_incoming = self._clean_title_for_comparison(incoming_title)
        clean_abs = self._clean_title_for_comparison(abs_title)

        # Check substring match
        if clean_incoming in clean_abs or clean_abs in clean_incoming:
            # Length similarity check (60%)
            len_ratio = min(len(clean_incoming), len(clean_abs)) / max(...)
            if len_ratio > 0.6:
                return True
```

**Title Cleaning** (`_clean_title_for_comparison`):
- Removes "(unabridged)", "(audiobook)", "audiobook"
- Removes file extensions (.mp3, .m4b, .m4a, .flac)
- Normalizes whitespace

#### Secondary Implementation: `stealth_audiobook_downloader.py:194-213`

Similar logic but simpler substring matching without length ratio check.

### Gap Analysis

#### Series Gap Detection: `audiobook_gap_analyzer.py:352-410`

**Input:** Audiobookshelf library + Goodreads series data

**Process:**
1. Group library books by series (key: `{series_name}|{author}`)
2. For each series with 3+ books:
   - Get owned sequence numbers
   - Query Goodreads for complete series
   - Find gaps in sequence (missing numbers between min and max)

**Output:**
```python
gap = {
    'type': 'series_gap',
    'title': title,
    'author': author,
    'series_name': series_name,
    'series_sequence': seq,
    'priority': 1,  # Series gaps are high priority
    'reason': f"Missing book {seq} in series {series_name}",
    'download_status': 'identified'
}
```

#### Author Gap Detection: `audiobook_gap_analyzer.py:482-490`

**Currently:** Stub only - logs "feature coming soon"

**Planned:** Query Goodreads for author's complete bibliography and identify missing books

### Confidence Scoring

#### Goodreads Verification: `goodreads_api_client.py:239-298`

```python
def verify_metadata(self, audio_title, audio_author, audio_series, audio_sequence):
    confidence = 0.0

    # Title matching (50% weight)
    title_similarity = self._calculate_similarity(audio_title, result.title)
    confidence += title_similarity * 0.5

    # Author matching (40% weight)
    author_similarity = self._calculate_similarity(audio_author, result.author)
    confidence += author_similarity * 0.4

    # Series matching (5% weight)
    if audio_series and result.series_name:
        if series_similarity >= 0.3:
            confidence += 0.05

    # Sequence matching (5% weight)
    if str(audio_sequence) == str(result.series_position):
        confidence += 0.05

    is_valid = confidence >= 0.7  # 70% threshold
    return is_valid, confidence, result
```

#### MAM Search Scoring: `audiobook_gap_analyzer.py:710-718`

```python
# Title match (70% weight)
title_match = SequenceMatcher(None, title.lower(), torrent_title.lower()).ratio()

# Author match (30% weight)
author_match = 1.0 if author.lower() in torrent_title.lower() else 0.5

score = (title_match * 0.7) + (author_match * 0.3)

if score >= self.config['title_match_threshold']:  # 0.7 default
    # Accept match
```

### Speech-to-Text (STT) Validation

**Status:** NOT IMPLEMENTED

After thorough code review, there is no STT-based audio validation in the current codebase. The system relies entirely on:
- Torrent metadata (title, author from MAM listing)
- Library metadata from Audiobookshelf
- External API enrichment (Google Books, Goodreads)

**Potential Future Implementation:**
- Use Whisper or similar STT to analyze audiobook intro
- Extract spoken title, author, narrator
- Fuzzy match against metadata
- Flag discrepancies for manual review

### Validation Outputs

The system produces the following validation states:

From `audiobook_gap_analyzer.py:829-832`:
```python
'gaps': [
    {
        'title': g['title'],
        'author': g['author'],
        'series': g.get('series_name'),
        'type': g['type'],
        'status': g['download_status']  # 'identified', 'found', 'not_found', 'queued', etc.
    }
]
```

Possible statuses:
- `identified` - Gap detected, not yet searched
- `found` - Torrent found on MAM
- `not_found` - No MAM results
- `queued` - Added to qBittorrent
- `skipped_duplicate` - Already in library
- `queue_failed` - qBittorrent error

---

## Phase 5: Librarian, Seeding, and Compliance

### Seeding Duration Rules

From `validate_mam_compliance.py:47-71`:
```python
def check_seeding_requirements(self):
    # These are enforced by MAM, not configurable
    results.append((
        "PASS",
        "Seeding Requirements",
        "72-hour minimum seeding enforced by MAM system"
    ))
```

**MAM Enforced:** 72-hour minimum seeding requirement (not configurable in automation)

**Implementation:** The system relies on qBittorrent's seeding behavior:
- Torrents remain in qBittorrent after completion
- MAM tracker enforces 72-hour minimum
- No explicit seeding duration management in code

### Ratio/Bonus Point Rules

From `validate_mam_compliance.py:198-263`:

```python
def check_bonus_point_strategy(self):
    current = self.rules['bonus_point_strategy']['current_status']

    # Check if bonus points capped
    if current['bonus_points'] >= current['bonus_points_cap']:
        # RECOMMEND: Trade 50,000-90,000 for upload credit

    # Check FL wedge count
    if current['fl_wedges'] > 100:
        # Use liberally

    # Check ratio
    if current['ratio'] >= 4.0:
        # EXCELLENT
    elif current['ratio'] >= 1.0:
        # Above minimum but close
    else:
        # BELOW MINIMUM - seed-only risk
```

### VIP/Freeleech Handling

From `stealth_audiobook_downloader.py:486-509`:
```python
def should_download_torrent(self, torrent):
    # Priority order:
    # 1. VIP torrents (always freeleech)
    if torrent.get('is_vip', False):
        return True, "VIP torrent (freeleech)"

    # 2. Freeleech torrents
    if torrent.get('is_freeleech', False):
        return True, "Freeleech torrent"

    # 3. Large torrents (use FL wedge)
    if self.should_use_fl_wedge(size_text):
        return True, f"Large torrent - using FL wedge"
```

From `validate_mam_compliance.py:96-143`:
```python
def check_download_strategy(self):
    # Check VIP torrent preference
    if config_dl.get('prefer_vip_torrents', False):
        # PASS - Prioritizing VIP torrents

    # Check freeleech preference
    if config_dl.get('prefer_freeleech', False):
        # PASS - Prioritizing freeleech

    # Check FL wedge usage
    if config_dl.get('use_freeleech_wedges', False):
        # PASS - Auto-applying FL wedges (110 available)
```

### VIP Status Maintenance

From `audiobook_auto_batch.py:583-627`:
```python
def maintain_vip_status(self):
    """
    Priority:
    1. Renew VIP if below 7 days remaining
    2. Reserve 1,250 points for 7-day VIP buffer
    3. Spend remaining points on upload credit
    """
    vip_manager = VIPStatusManager(logger=self.logger)
    result = vip_manager.check_and_maintain_vip(dry_run=dry_run)
```

### Compliance Rules Implementation Status

| Rule | Implemented | Location |
|------|-------------|----------|
| 72-hour seeding | MAM enforced | N/A (tracker) |
| VIP preference | Yes | `stealth_audiobook_downloader.py:486-509` |
| Freeleech preference | Yes | `stealth_audiobook_downloader.py:486-509` |
| FL wedge usage | Yes | `stealth_audiobook_downloader.py:511-533` |
| Bonus point spending | Yes | `vip_status_manager.py` |
| Ratio monitoring | Documented | `validate_mam_compliance.py:238-262` |
| Duplicate detection | Yes | `audiobook_auto_batch.py:224-280` |

### Audiobookshelf Integration

#### Metadata Application

From `audiobookshelf_metadata_sync.py:428-536`:
```python
def update_audiobookshelf_metadata_quality_preserved(self, item_id, new_metadata, current_metadata):
    """Update with quality preservation and idempotency."""

    # Quality preservation: only update if new data is better
    if new_metadata.get('description') and len(new_desc) > len(current_desc) * 0.8:
        fields_to_update['description'] = new_desc

    # Series is always updated if available (critical)
    if new_metadata.get('series'):
        normalized_series = self.normalize_series_name(new_metadata['series'])
        fields_to_update['series'] = normalized_series

    # Send PATCH request
    response = requests.patch(
        f"{self.abs_url}/api/items/{item_id}",
        json={'media': {'metadata': fields_to_update}}
    )
```

#### Torrent-Side Data

**Policy:** NEVER modify torrent-side data

The system only updates Audiobookshelf metadata via API. It does not:
- Rename downloaded files
- Modify torrent data
- Change folder structure

This ensures seeding integrity - the torrent content matches what peers expect.

---

## Phase 6: Configuration Values and Knobs

### Core Configuration Table

| Config Name | Value | File | Lines | Effect |
|-------------|-------|------|-------|--------|
| `MAM_RATE_LIMIT_MIN` | 3 | `backend/config.py` | 84 | Minimum seconds between MAM requests |
| `MAM_RATE_LIMIT_MAX` | 10 | `backend/config.py` | 85 | Maximum seconds between MAM requests |
| `MAM_MAX_PAGES_PER_SESSION` | 50 | `backend/config.py` | 86 | Max pages per crawl session |
| `MAM_MIN_SEEDS` | 1 | `backend/config.py` | 110 | Minimum seeders required |
| `MAM_TITLE_MATCH_THRESHOLD` | 0.7 | `backend/config.py` | 111 | 70% title similarity for match |
| `GAP_MAX_DOWNLOADS_PER_RUN` | 10 | `backend/config.py` | 107 | Max downloads per gap analysis |
| `GAP_SERIES_PRIORITY` | True | `backend/config.py` | 108 | Prioritize series gaps |
| `GAP_AUTHOR_PRIORITY` | True | `backend/config.py` | 109 | Prioritize author gaps |
| `GOOGLE_BOOKS_RATE_LIMIT` | 100 | `backend/config.py` | 77 | Requests per day |
| `ENABLED_GENRES` | [SF, Fantasy, Mystery, Thriller] | `backend/config.py` | 140-145 | Genres for top-10 |
| `DISABLED_GENRES` | [Romance, Erotica, Self-Help] | `backend/config.py` | 147-151 | Excluded genres |

### Stealth Crawler Settings

| Config Name | Value | File | Lines | Effect |
|-------------|-------|------|-------|--------|
| `min_delay` | 15 | `stealth_audiobook_downloader.py` | 74 | Min human delay (seconds) |
| `max_delay` | 45 | `stealth_audiobook_downloader.py` | 75 | Max human delay (seconds) |
| `scroll_delay` | 3 | `stealth_audiobook_downloader.py` | 76 | Scroll simulation delay |
| `read_delay` | 8 | `stealth_audiobook_downloader.py` | 77 | Page reading delay |
| Viewports | 6 sizes | `stealth_audiobook_downloader.py` | 80-83 | Random viewport selection |
| User agents | 4 strings | `stealth_audiobook_downloader.py` | 86-91 | User agent rotation |

### Goodreads Client Settings

| Config Name | Value | File | Lines | Effect |
|-------------|-------|------|-------|--------|
| `RATE_LIMIT_DELAY` | 0.2 | `goodreads_api_client.py` | 49 | 5 req/sec max |
| Cache file | `goodreads_cache.json` | `goodreads_api_client.py` | 51 | Persistent cache |

### Metadata Provider Weights

| Provider | Weight | File | Lines | Effect |
|----------|--------|------|-------|--------|
| Google | 1.0 | `unified_metadata_aggregator.py` | 22 | Highest trust |
| Hardcover | 0.9 | `unified_metadata_aggregator.py` | 22 | High trust |
| Goodreads | 0.8 | `unified_metadata_aggregator.py` | 22 | Good trust |
| Kindle | 0.8 | `unified_metadata_aggregator.py` | 22 | Good trust |
| Audioteka | 0.7 | `unified_metadata_aggregator.py` | 22 | Medium trust |
| Lubimyczytac | 0.6 | `unified_metadata_aggregator.py` | 22 | Lower trust |

### Batch Download Config (`audiobook_auto_config.json`)

| Setting | Typical Value | Effect |
|---------|---------------|--------|
| `query_settings.top_n_per_genre` | 3-10 | Books per genre per run |
| `query_settings.skip_duplicates` | true | Enable duplicate detection |
| `query_settings.max_check_limit` | 100 | Max results to check for duplicates |
| `query_settings.use_whitelist` | true | Whitelist vs blacklist mode |
| `query_settings.timespan_preference` | "recent" | Time window for searches |
| `download_settings.dry_run` | false | Test mode without downloading |
| `download_settings.auto_add_to_qbittorrent` | true | Auto-queue downloads |
| `download_settings.category` | "audiobooks-auto" | qBittorrent category |
| `download_settings.prefer_vip_torrents` | true | Prioritize VIP |
| `download_settings.prefer_freeleech` | true | Prioritize freeleech |
| `download_settings.use_freeleech_wedges` | true | Use FL wedges |
| `included_genres` | ["Science Fiction", "Fantasy"] | Whitelist genres |
| `excluded_genres` | ["Romance", "Erotica"] | Blacklist genres |

### Scheduler Times

| Task | Schedule | File | Lines |
|------|----------|------|-------|
| MAM Crawl | Daily 2:00 AM | `backend/config.py` | 95 |
| Top-10 Discovery | Sunday 3:00 AM | `backend/config.py` | 96 |
| Full Metadata Sync | 1st of month 4:00 AM | `backend/config.py` | 97 |
| New Metadata Sync | Sunday 4:30 AM | `backend/config.py` | 98 |
| Series Completion | 2nd of month 3:00 AM | `backend/config.py` | 99 |
| Author Completion | 3rd of month 3:00 AM | `backend/config.py` | 100 |
| Gap Analysis | Daily 1:00 AM | `backend/config.py` | 101 |

---

## Phase 7: Layered Model and Responsibility Boundaries

### Layer 1: CRAWLER

**Responsibility:** Acquire audiobook torrents from MyAnonamouse

**Modules:**
- `mam_crawler.py` - Base crawler class
- `stealth_mam_crawler.py` - Stealth behavior
- `stealth_audiobook_downloader.py` - Production downloader
- `audiobook_catalog_crawler.py` - Genre/timespan discovery

**Functions:**
- `MAMPassiveCrawler._login()` - Authentication
- `MAMPassiveCrawler.crawl_page()` - Single page crawl
- `StealthMAMAudiobookDownloader.crawl_genre_page()` - Genre search
- `StealthMAMAudiobookDownloader.authenticate()` - Stealth auth

**Inputs:**
- MAM credentials (env vars)
- Genre codes and timespans
- Search parameters

**Outputs:**
- Torrent metadata (title, URL, size, VIP/FL status)
- Session cookies
- State files for resume

**Metadata During Crawl:**
- Extracts title, author, size, VIP/FL status from HTML
- Does NOT perform external metadata enrichment
- Does NOT update any database

**What it MUST NEVER change:**
- Audiobookshelf library
- qBittorrent settings
- External metadata sources

### Layer 2: METADATA ENRICHMENT

**Responsibility:** Enhance audiobook metadata from external sources

**Modules:**
- `audiobookshelf_metadata_sync.py` - Main sync engine
- `unified_metadata_aggregator.py` - Multi-provider aggregation
- `goodreads_api_client.py` - Goodreads scraping
- `goodreads_abs_scraper.py` - ABS-Goodreads integration

**Functions:**
- `AudiobookshelfMetadataSync.process_book()` - Process single book
- `AudiobookshelfMetadataSync.query_provider()` - Query metadata API
- `get_metadata()` - Aggregate from all providers
- `GoodreadsClient.search_book()` - Search Goodreads

**Inputs:**
- Audiobookshelf library items
- Book title and author

**Outputs:**
- Enriched metadata (description, series, ISBN, genres)
- Confidence scores
- Cache files

**When Applied:** POST-DOWNLOAD only (after Audiobookshelf import)

**Fields Considered Provisional:**
- Series information (often missing or inconsistent)
- ISBN (not always in Google Books results)
- Genres (vary by source)

**What it MUST NEVER change:**
- Torrent files or structure
- MAM-side data
- qBittorrent configuration

### Layer 3: VALIDATION

**Responsibility:** Verify metadata correctness and detect gaps

**Modules:**
- `audiobook_gap_analyzer.py` - Gap detection
- `validate_mam_compliance.py` - Compliance checking
- Duplicate detection in `audiobook_auto_batch.py`

**Functions:**
- `AudiobookGapAnalyzer._identify_series_gaps()` - Find missing series books
- `AudiobookGapAnalyzer._is_title_owned()` - Duplicate check
- `MAMComplianceValidator.run_validation()` - Check all rules
- `GoodreadsClient.verify_metadata()` - Confidence scoring

**Inputs:**
- Audiobookshelf library
- Goodreads series data
- Configuration rules

**Outputs:**
- Gap reports (missing books)
- Compliance reports (pass/warn/fail)
- Confidence scores

**What Happens When Uncertain:**
- Gaps with low confidence are still reported
- Books without Goodreads match are flagged
- Compliance warnings generated for review

**What it MUST NEVER change:**
- Existing library metadata (read-only analysis)
- Automatic corrections without explicit approval

### Layer 4: LIBRARIAN

**Responsibility:** Maintain Audiobookshelf library state

**Modules:**
- `audiobookshelf_metadata_sync.py` - Metadata updates
- `master_audiobook_manager.py` - Orchestration

**Functions:**
- `AudiobookshelfMetadataSync.update_audiobookshelf_metadata_quality_preserved()` - Safe update
- `AudiobookshelfMetadataSync.process_series_linking()` - Series consistency
- `MasterAudiobookManager.update_all_metadata()` - Batch update

**Inputs:**
- Enriched metadata from Layer 2
- Audiobookshelf API credentials

**Outputs:**
- Updated Audiobookshelf items
- Series validation reports
- Sync statistics

**What Metadata It Can Change:**
- Title (only if missing)
- Author (only if missing)
- Description (if new is better/longer)
- Series name and number (always if available)
- ISBN, genres, tags (only if missing)
- Publisher, published year (only if missing)

**Torrent-Side Changes:** NEVER

The librarian only touches Audiobookshelf metadata via API. Downloaded files are never modified to preserve seeding integrity.

### Layer 5: SEEDING AND COMPLIANCE

**Responsibility:** Maintain good standing with MAM

**Modules:**
- `validate_mam_compliance.py` - Rule validation
- `vip_status_manager.py` - VIP/bonus management
- `stealth_audiobook_downloader.py` - Download rules

**Functions:**
- `MAMComplianceValidator.check_seeding_requirements()` - Seeding rules
- `MAMComplianceValidator.check_bonus_point_strategy()` - Point management
- `StealthMAMAudiobookDownloader.should_download_torrent()` - VIP/FL logic
- `AutomatedAudiobookBatch.maintain_vip_status()` - VIP renewal

**Inputs:**
- Configuration files (`mam_automation_rules.json`)
- Current account status (bonus points, ratio, VIP days)

**Outputs:**
- Compliance reports
- VIP renewal actions
- Upload credit purchases

**Implemented:**
- VIP/freeleech preference
- FL wedge usage for large torrents
- Bonus point spending
- Compliance validation

**Documented but NOT Implemented:**
- Automatic ratio monitoring
- Seeding duration tracking
- Upload credit alerts

**Planned as TODOs:**
- Dynamic ratio-based download decisions
- Automatic seeding extension for popular torrents

### Layer 6: ORCHESTRATION

**Responsibility:** Coordinate all layers and schedule jobs

**Modules:**
- `master_audiobook_manager.py` - Master controller
- `audiobook_auto_batch.py` - Batch processor
- `backend/scheduler/` - APScheduler jobs

**Entry Points:**

**Manual Scripts:**
- `master_audiobook_manager.py --full-sync`
- `master_audiobook_manager.py --update-metadata`
- `master_audiobook_manager.py --missing-books`
- `validate_mam_compliance.py`
- `stealth_audiobook_downloader.py`

**Scheduled Jobs:**
- `audiobook_auto_batch.py` - Weekly batch (cron)
- Backend scheduler tasks (APScheduler)

**Functions:**
- `MasterAudiobookManager.full_sync()` - Complete workflow
- `AutomatedAudiobookBatch.process_all_genres()` - Batch download
- APScheduler job definitions in `backend/scheduler/`

**Inputs:**
- Command-line arguments
- Configuration files
- Schedule times

**Outputs:**
- Execution reports
- Session statistics
- Log files

---

## Phase 8: Machine Readable Spec

```json
{
  "system_name": "MAMcrawler",
  "version": "1.0.0",
  "analysis_date": "2025-11-19",

  "subsystems": {
    "crawler": {
      "modules": [
        "mam_crawler.py",
        "stealth_mam_crawler.py",
        "stealth_audiobook_downloader.py",
        "audiobook_catalog_crawler.py",
        "comprehensive_guide_crawler.py"
      ],
      "key_functions": [
        "MAMPassiveCrawler._login",
        "MAMPassiveCrawler.crawl_page",
        "StealthMAMAudiobookDownloader.authenticate",
        "StealthMAMAudiobookDownloader.crawl_genre_page",
        "StealthMAMAudiobookDownloader.should_download_torrent"
      ],
      "config": {
        "category_whitelist": ["c47", "c41"],
        "genre_names": ["Science Fiction", "Fantasy"],
        "time_window_days": 7,
        "rate_limits": {
          "basic_min_delay": 3,
          "basic_max_delay": 10,
          "stealth_min_delay": 15,
          "stealth_max_delay": 45
        },
        "selection_rules": {
          "max_pages_per_session": 50,
          "min_seeders": 1,
          "title_match_threshold": 0.7,
          "prefer_vip": true,
          "prefer_freeleech": true,
          "fl_wedge_threshold_gb": 1.0
        }
      },
      "uses_goodreads": {
        "during_crawl": false,
        "for_enrichment": false,
        "for_selection": false,
        "notes": "Crawler only extracts MAM metadata, no external API calls"
      }
    },

    "metadata_enrichment": {
      "modules": [
        "audiobookshelf_metadata_sync.py",
        "unified_metadata_aggregator.py",
        "goodreads_api_client.py",
        "goodreads_abs_scraper.py",
        "dual_goodreads_scraper.py"
      ],
      "providers": [
        {
          "name": "google",
          "weight": 1.0,
          "endpoint": "https://www.googleapis.com/books/v1/volumes"
        },
        {
          "name": "hardcover",
          "weight": 0.9,
          "endpoint": "https://provider.vito0912.de/hardcover/en/book"
        },
        {
          "name": "goodreads",
          "weight": 0.8,
          "endpoint": "http://localhost:5555/goodreads/search"
        },
        {
          "name": "kindle",
          "weight": 0.8,
          "endpoint": "http://localhost:5555/kindle/us/search"
        }
      ],
      "fields_enriched": [
        "title",
        "author",
        "description",
        "series",
        "seriesNumber",
        "isbn",
        "publisher",
        "publishedYear",
        "genres",
        "tags"
      ],
      "when_applied": "post_download",
      "confidence_handling": {
        "method": "weighted_consensus",
        "threshold": 0.6,
        "fallback_order": ["google", "goodreads", "hardcover", "goodreads_scraper"]
      }
    },

    "validation": {
      "modules": [
        "audiobook_gap_analyzer.py",
        "validate_mam_compliance.py",
        "goodreads_api_client.py"
      ],
      "stt_used": false,
      "stt_roles": [],
      "stt_notes": "NOT IMPLEMENTED - no speech-to-text validation exists",
      "duplicate_detection": {
        "method": "title_substring_with_length_ratio",
        "threshold": 0.6,
        "title_cleaning": ["remove_unabridged", "remove_audiobook", "remove_extensions"]
      },
      "gap_detection": {
        "series_gaps": {
          "implemented": true,
          "method": "goodreads_series_query",
          "min_books_for_analysis": 3
        },
        "author_gaps": {
          "implemented": false,
          "status": "TODO",
          "notes": "Stub exists, logs 'feature coming soon'"
        }
      },
      "confidence_scoring": {
        "title_weight": 0.5,
        "author_weight": 0.4,
        "series_weight": 0.05,
        "sequence_weight": 0.05,
        "validity_threshold": 0.7
      },
      "outputs": [
        "identified",
        "found",
        "not_found",
        "queued",
        "skipped_duplicate",
        "queue_failed"
      ]
    },

    "librarian": {
      "modules": [
        "audiobookshelf_metadata_sync.py",
        "master_audiobook_manager.py"
      ],
      "audiobookshelf_integration": {
        "api_base": "/api",
        "endpoints_used": [
          "GET /api/libraries",
          "GET /api/libraries/{id}/items",
          "PATCH /api/items/{id}",
          "GET /api/items/{id}"
        ]
      },
      "what_metadata_it_can_change": [
        "title (only if missing)",
        "authorName (only if missing)",
        "description (if new is longer)",
        "series (always if available)",
        "seriesSequence (always if available)",
        "isbn (only if missing)",
        "genres (only if missing)",
        "tags (only if missing)",
        "publisher (only if missing)",
        "publishedYear (only if missing)"
      ],
      "torrent_side_changes": "never",
      "quality_preservation": {
        "enabled": true,
        "description_length_threshold": 0.8
      }
    },

    "seeding_compliance": {
      "modules": [
        "validate_mam_compliance.py",
        "vip_status_manager.py",
        "stealth_audiobook_downloader.py"
      ],
      "ratio_rules": {
        "minimum": 1.0,
        "warning_threshold": 2.0,
        "excellent_threshold": 4.0
      },
      "seeding_duration_rules": {
        "minimum_hours": 72,
        "enforced_by": "MAM tracker",
        "automated_tracking": false
      },
      "vip_handling": {
        "auto_renew": true,
        "buffer_days": 7,
        "buffer_points": 1250
      },
      "freeleech_handling": {
        "prefer_vip": true,
        "prefer_freeleech": true,
        "use_wedges": true,
        "wedge_threshold_gb": 1.0
      },
      "implemented": {
        "vip_preference": true,
        "freeleech_preference": true,
        "fl_wedge_usage": true,
        "bonus_point_spending": true,
        "compliance_validation": true,
        "ratio_monitoring": "documented_only",
        "seeding_duration_tracking": false
      }
    },

    "orchestration": {
      "entrypoints": [
        {
          "file": "master_audiobook_manager.py",
          "commands": ["--full-sync", "--update-metadata", "--missing-books", "--top-search"],
          "type": "manual"
        },
        {
          "file": "audiobook_auto_batch.py",
          "commands": ["--config", "--dry-run"],
          "type": "scheduled"
        },
        {
          "file": "stealth_audiobook_downloader.py",
          "commands": [],
          "type": "manual"
        },
        {
          "file": "audiobook_gap_analyzer.py",
          "commands": ["--analyze-only", "--max-downloads"],
          "type": "scheduled"
        },
        {
          "file": "backend/main.py",
          "commands": [],
          "type": "service"
        }
      ],
      "scheduled_jobs": [
        {
          "name": "MAM Crawl",
          "schedule": "0 2 * * *",
          "description": "Daily 2:00 AM"
        },
        {
          "name": "Top-10 Discovery",
          "schedule": "0 3 * * 6",
          "description": "Sunday 3:00 AM"
        },
        {
          "name": "Full Metadata Sync",
          "schedule": "0 4 1 * *",
          "description": "1st of month 4:00 AM"
        },
        {
          "name": "Gap Analysis",
          "schedule": "0 1 * * *",
          "description": "Daily 1:00 AM"
        }
      ],
      "manual_scripts": [
        "validate_mam_compliance.py",
        "goodreads_abs_scraper.py",
        "check_progress.py"
      ]
    }
  },

  "configs": [
    {
      "name": "MAM_RATE_LIMIT_MIN",
      "value": 3,
      "file": "backend/config.py",
      "lines": "84",
      "description": "Minimum seconds between MAM requests"
    },
    {
      "name": "MAM_RATE_LIMIT_MAX",
      "value": 10,
      "file": "backend/config.py",
      "lines": "85",
      "description": "Maximum seconds between MAM requests"
    },
    {
      "name": "MAM_MAX_PAGES_PER_SESSION",
      "value": 50,
      "file": "backend/config.py",
      "lines": "86",
      "description": "Maximum pages to crawl per session"
    },
    {
      "name": "MAM_MIN_SEEDS",
      "value": 1,
      "file": "backend/config.py",
      "lines": "110",
      "description": "Minimum seeders required for download"
    },
    {
      "name": "MAM_TITLE_MATCH_THRESHOLD",
      "value": 0.7,
      "file": "backend/config.py",
      "lines": "111",
      "description": "Minimum title similarity for match acceptance"
    },
    {
      "name": "GAP_MAX_DOWNLOADS_PER_RUN",
      "value": 10,
      "file": "backend/config.py",
      "lines": "107",
      "description": "Maximum downloads per gap analysis run"
    },
    {
      "name": "stealth_min_delay",
      "value": 15,
      "file": "stealth_audiobook_downloader.py",
      "lines": "74",
      "description": "Minimum human-like delay in stealth mode"
    },
    {
      "name": "stealth_max_delay",
      "value": 45,
      "file": "stealth_audiobook_downloader.py",
      "lines": "75",
      "description": "Maximum human-like delay in stealth mode"
    },
    {
      "name": "GOODREADS_RATE_LIMIT_DELAY",
      "value": 0.2,
      "file": "goodreads_api_client.py",
      "lines": "49",
      "description": "Seconds between Goodreads requests (5 req/sec)"
    },
    {
      "name": "provider_weights",
      "value": {"google": 1.0, "hardcover": 0.9, "goodreads": 0.8, "kindle": 0.8},
      "file": "unified_metadata_aggregator.py",
      "lines": "22",
      "description": "Trust weights for metadata providers"
    },
    {
      "name": "duplicate_length_ratio",
      "value": 0.6,
      "file": "audiobook_auto_batch.py",
      "lines": "252-253",
      "description": "Minimum title length similarity for duplicate detection"
    },
    {
      "name": "series_min_books",
      "value": 3,
      "file": "audiobook_gap_analyzer.py",
      "lines": "381-382",
      "description": "Minimum books in series before gap analysis"
    }
  ],

  "external_dependencies": {
    "apis": [
      {
        "name": "MyAnonamouse",
        "type": "private_tracker",
        "auth": "session_cookies",
        "rate_limit": "3-10 seconds"
      },
      {
        "name": "Audiobookshelf",
        "type": "media_server",
        "auth": "bearer_token",
        "rate_limit": "none"
      },
      {
        "name": "qBittorrent",
        "type": "torrent_client",
        "auth": "username_password",
        "rate_limit": "none"
      },
      {
        "name": "Google Books",
        "type": "public_api",
        "auth": "api_key",
        "rate_limit": "100/day"
      },
      {
        "name": "Goodreads",
        "type": "web_scraping",
        "auth": "none",
        "rate_limit": "5 req/sec"
      }
    ],
    "libraries": [
      "crawl4ai",
      "aiohttp",
      "beautifulsoup4",
      "lxml",
      "qbittorrentapi",
      "fastapi",
      "sqlalchemy",
      "pydantic",
      "apscheduler"
    ]
  },

  "data_flow": {
    "acquisition": [
      "User/Cron triggers orchestration",
      "Crawler authenticates with MAM",
      "Crawler searches genres with filters",
      "Crawler extracts torrent metadata",
      "Validator checks for duplicates",
      "Downloader adds to qBittorrent",
      "qBittorrent downloads to watched folder"
    ],
    "enrichment": [
      "Audiobookshelf detects new files",
      "Audiobookshelf creates library item",
      "Metadata sync queries external APIs",
      "Unified aggregator merges results",
      "Librarian updates Audiobookshelf metadata"
    ],
    "maintenance": [
      "Gap analyzer scans library",
      "Gap analyzer queries Goodreads for series",
      "Gap analyzer identifies missing books",
      "Gap analyzer searches MAM",
      "Downloader queues missing books",
      "Compliance validator checks rules"
    ]
  }
}
```

---

## Conclusion

MAMcrawler is a sophisticated audiobook automation system with clear separation of concerns across six layers. The system emphasizes:

1. **Stealth and Compliance** - Human-like behavior, rate limiting, VIP/freeleech preference
2. **Quality Preservation** - Only updates metadata when improvements are available
3. **Resume Capability** - State persistence for interrupted operations
4. **Multi-Source Enrichment** - Aggregates from multiple providers with weighted consensus
5. **Gap Detection** - Identifies missing series books using Goodreads data

**Key Limitations:**
- No STT-based audio validation
- Author gap analysis not implemented
- Ratio monitoring is documented but not automated
- Seeding duration tracking relies on MAM enforcement

**Recommended Extensions:**
- Implement Whisper-based STT for metadata verification
- Add author bibliography scraping for author gaps
- Build automated ratio monitoring with alerts
- Add seeding duration tracking per torrent

This analysis provides a complete ground truth for AI systems to understand, enforce, and extend MAMcrawler behavior.
