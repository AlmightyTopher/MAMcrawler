# Phase 2: Implementation Plan - Refactoring Monolithic Files

**Status:** PLANNING PHASE
**Date Created:** 2025-12-02
**Target Completion:** Sequential refactoring of 3 files (abs_client, qbittorrent_client, ratio_emergency_service)

## Overview

Phase 2 Implementation focuses on refactoring three monolithic client files (4,257 total LOC) to use the pattern modules created in Phase 1. The goal is to reduce code duplication, improve testability, and create focused, single-responsibility modules.

### Refactoring Goals

| Metric | Target |
|--------|--------|
| Code Reduction | 25-40% LOC decrease |
| Duplication Removal | 95%+ |
| Module Cohesion | High (single responsibility) |
| Test Coverage | Comprehensive |
| API Compatibility | 100% (no breaking changes) |

## Phase 2 Execution Strategy

### 3-Step Sequential Approach

1. **Step 1: Refactor QBittorrentClient** (smaller, fewer dependencies)
   - Baseline for authenticated client pattern
   - Unblocks later refactoring
   - Less complex than AbsClient

2. **Step 2: Refactor AbsClient** (larger, more complex)
   - Uses refactored QBittorrentClient patterns
   - Demonstrates scalability of patterns
   - More extensive testing

3. **Step 3: Integrate RatioEmergencyService** (highest level)
   - Depends on both clients being refactored
   - Activates previously stubbed functionality
   - Final integration layer

---

## STEP 1: QBittorrentClient Refactoring

**Current:** 1,333 LOC | **Target:** 965 LOC | **Reduction:** ~27%

### 1.1 Architecture Changes

#### Current Structure
```
QBittorrentClient
├── Session Management (_login, _logout, _ensure_session)
├── Custom Cookie Handling (SID extraction)
├── Core HTTP (_request with retry)
├── Torrent Management (add, get, pause, resume, delete)
├── Server Management
├── Category Management
├── RSS Management (~180 lines)
├── Bandwidth Management (~350 lines)
└── Error Handling & Logging
```

#### Target Structure
```
QBittorrentClient (inherits AuthenticatedAsyncClient)
├── Torrent Operations (add, get, pause, resume, delete)
├── Server Management
├── Category Management
├── BandwidthManager (extracted from bandwidth methods)
├── RSSManager (extracted from RSS methods)
└── Cookie Handler (custom SID handling isolated)
```

### 1.2 Refactoring Steps

#### Step 1.2.1: Inherit from AuthenticatedAsyncClient
**Removes:** ~200 LOC (session management, retry logic, core HTTP)
**Adds:** Access to pattern base class features

```python
# BEFORE
class QBittorrentClient:
    def __init__(self, base_url, username, password, timeout=30):
        self.base_url = base_url
        self.session = None
        self.auth = (username, password)
        self.timeout = ClientTimeout(total=timeout)

    async def _ensure_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                connector=aiohttp.TCPConnector(ssl=False)
            )
            await self._login()

    @retry(stop=stop_after_attempt(3), ...)
    async def _request(self, method, endpoint, **kwargs):
        # ... retry logic ...

# AFTER
class QBittorrentClient(AuthenticatedAsyncClient):
    def __init__(self, base_url, username, password, timeout=30):
        super().__init__(base_url, timeout)
        self.auth = (username, password)

    async def _ensure_session(self):
        await super()._ensure_session()
        if not self.auth_token:
            await self._login()  # Custom login logic
```

**Benefits:**
- ✅ Removes 200 LOC of duplicated session/retry code
- ✅ Inherits working authentication base
- ✅ Inherits tested error handling
- ✅ Gains `__aenter__`/`__aexit__` context manager support

#### Step 1.2.2: Extract Bandwidth Management to BandwidthManager
**Removes:** ~350 LOC from main class
**Creates:** `backend/integrations/qbittorrent_bandwidth_manager.py` (~200 LOC)

```python
# BEFORE (in QBittorrentClient)
async def set_global_download_limit(self, limit_kb):
    # FormData + POST + logging
    pass

async def get_global_download_limit(self):
    # GET + parsing + logging
    pass

async def set_torrent_download_limit(self, torrent_hash, limit_kb):
    # FormData + POST + logging
    pass
# ... repeated 6 more times ...

# AFTER (in separate BandwidthManager)
class BandwidthManager:
    async def set_global_download_limit(self, limit_kb):
        pass

    async def get_global_download_limit(self):
        pass

    # Generic helper methods
    async def _set_limit(self, endpoint, limit_kb):
        # Consolidated logic
        pass

    async def _get_limit(self, endpoint):
        # Consolidated logic
        pass
```

**Benefits:**
- ✅ Removes 350 LOC from main class
- ✅ ~150 LOC consolidated BandwidthManager handles all limit operations
- ✅ Net -200 LOC saving
- ✅ Clear separation of concerns

#### Step 1.2.3: Extract RSS Management to RSSManager
**Removes:** ~180 LOC from main class
**Creates:** `backend/integrations/qbittorrent_rss_manager.py` (~120 LOC)

```python
# BEFORE (in QBittorrentClient)
async def add_rss_feed(self, url, cookie_filter=None):
    pass

async def get_rss_items(self, feed_url):
    pass

async def set_rss_rule(self, rule_name, rule_config):
    pass
# ... repeated 6-8 more times ...

# AFTER (in separate RSSManager)
class RSSManager:
    async def add_feed(self, url, cookie_filter=None):
        pass

    async def get_items(self, feed_url):
        pass

    async def set_rule(self, rule_name, rule_config):
        pass
```

**Benefits:**
- ✅ Removes 180 LOC from main class
- ✅ RSSManager consolidates ~120 LOC
- ✅ Net -60 LOC saving
- ✅ RSS operations isolated for future enhancement

#### Step 1.2.4: Extract Custom Cookie Handling
**Removes:** ~30 LOC from core methods
**Creates:** `_CookieHandler` private class (~30 LOC)

```python
# BEFORE (inline in _request)
# Extract SID from Set-Cookie header
cookies_header = response.headers.get('Set-Cookie', '')
sid = re.search(r'SID=([^;]+)', cookies_header)
if sid:
    self.session.cookie_jar.update_cookies({'SID': sid.group(1)})

# AFTER (in _CookieHandler)
class _CookieHandler:
    @staticmethod
    def extract_sid(response_headers):
        cookies_header = response_headers.get('Set-Cookie', '')
        match = re.search(r'SID=([^;]+)', cookies_header)
        return match.group(1) if match else None
```

**Benefits:**
- ✅ Documents qBittorrent API quirk clearly
- ✅ Isolates custom logic for testing
- ✅ Makes core _request method cleaner

### 1.3 Files Changed/Created

| File | Change | Impact |
|------|--------|--------|
| `backend/integrations/qbittorrent_client.py` | Refactor - 1,333 → 750 LOC | Inherits AuthenticatedAsyncClient, removed duplication |
| `backend/integrations/qbittorrent_bandwidth_manager.py` | CREATE - 150 LOC | New focused module for bandwidth operations |
| `backend/integrations/qbittorrent_rss_manager.py` | CREATE - 120 LOC | New focused module for RSS operations |
| `backend/tests/integrations/test_qbittorrent_client.py` | UPDATE | New tests for refactored structure |

### 1.4 Testing Strategy

**What to test:**
1. ✅ All public methods still work identically (contract testing)
2. ✅ BandwidthManager operations (unit tests)
3. ✅ RSSManager operations (unit tests)
4. ✅ Cookie handling edge cases (unit tests)
5. ✅ Authentication flow (integration tests)
6. ✅ Error handling & retry logic (inherited from base)

**Test Coverage Goals:**
- Current coverage: ~85% (from existing qbittorrent tests if they exist)
- Target coverage: ~95%
- New test files: 3-4 files for new managers

### 1.5 Backwards Compatibility

**Methods preserved:**
- ✅ All public methods maintained with same signatures
- ✅ All return types unchanged
- ✅ All exceptions unchanged

**Migration path for users:**
```python
# OLD WAY (still works)
client = QBittorrentClient(base_url, username, password)
await client.set_global_download_limit(10000)

# NEW WAY (with context manager)
async with QBittorrentClient(base_url, username, password) as client:
    await client.set_global_download_limit(10000)
```

---

## STEP 2: AbsClient Refactoring

**Current:** 2,117 LOC | **Target:** 1,700 LOC | **Reduction:** ~20%

### 2.1 Architecture Changes

#### Current Structure
```
AudiobookshelfClient (2,117 lines - MONOLITHIC)
├── Session Management
├── Core HTTP (_request with retry)
├── Library Management (~200 lines)
├── Collections Management (~150 lines)
├── Playlists Management (~270 lines)
├── User Progress & Bookmarks (~160 lines)
├── User Management (~110 lines)
├── Backup Management (~120 lines)
├── RSS Feed Management (~60 lines)
├── API Key Management (~50 lines)
├── Notifications Management (~160 lines)
└── Email Management (~70 lines)
```

#### Target Structure (10 Focused Modules)
```
AudiobookshelfClient (inherits AuthenticatedAsyncClient)
├── LibraryManager (books, search, import, scan)
├── CollectionManager (CRUD + batch operations)
├── PlaylistManager (CRUD + batch operations + special)
├── ProgressManager (progress tracking, bookmarks, sessions)
├── UserManager (profile, settings, permissions)
├── BackupManager (backup operations)
├── NotificationManager (notifications, settings)
├── RSSManager (RSS feed operations)
├── APIKeyManager (API key operations)
└── EmailManager (email settings & tests)

+ Shared:
├── MetadataMapper for field transformations
└── Batch operations mixin for bulk updates
```

### 2.2 Refactoring Steps (Sequential)

#### Step 2.2.1: Create Domain-Specific Managers
**Creates:** 9 new manager modules (~1,800 LOC total)

Each manager encapsulates related operations:

```
backend/integrations/abs_managers/
├── __init__.py
├── library_manager.py (200 LOC) - Books, search, import, scan
├── collection_manager.py (150 LOC) - Collection CRUD + batch ops
├── playlist_manager.py (270 LOC) - Playlist CRUD + batch ops + special
├── progress_manager.py (160 LOC) - Progress, bookmarks, sessions
├── user_manager.py (110 LOC) - Profile, settings, permissions
├── backup_manager.py (120 LOC) - Backup operations
├── notification_manager.py (160 LOC) - Notifications + settings
├── rss_manager.py (60 LOC) - RSS feeds
├── api_key_manager.py (50 LOC) - API keys
└── email_manager.py (70 LOC) - Email settings & tests
```

**Pattern for each manager:**
```python
class LibraryManager:
    def __init__(self, client):
        self.client = client  # Reference to main client for _request()

    async def get_library_items(self, library_id, **kwargs):
        """Implement method using self.client._request()"""
        return await self.client._request("GET", f"/api/libraries/{library_id}/items", **kwargs)

    async def search_books(self, library_id, query):
        """Implement method using self.client._request()"""
        return await self.client._request(
            "GET",
            f"/api/libraries/{library_id}/items",
            params={"q": query}
        )
```

**Benefits:**
- ✅ Clear separation of concerns
- ✅ Each manager handles single domain
- ✅ Reusable across different ABS instances
- ✅ Easier testing (mock client reference)
- ✅ Easier to extend/modify specific domains

#### Step 2.2.2: Apply Batch Operations Mixin to Collection/Playlist Managers
**Simplifies:** ~80 LOC of batch method implementations

**Current pattern (repeated 4 times):**
```python
async def batch_add_to_collection(self, collection_id, item_ids):
    results = {"succeeded": [], "failed": []}
    for item_id in item_ids:
        try:
            await self.add_book_to_collection(collection_id, item_id)
            results["succeeded"].append(item_id)
        except AudiobookshelfError as e:
            results["failed"].append({"item_id": item_id, "error": str(e)})
    return results
```

**After BatchOperationsMixin:**
```python
# In CollectionManager
class CollectionManager(BatchOperationsMixin):
    async def add_to_collection(self, collection_id, item_id):
        return await self.client._request(
            "POST",
            f"/api/collections/{collection_id}/item/{item_id}"
        )

    async def batch_add_to_collection(self, collection_id, item_ids):
        return await self.batch_operation(
            items=item_ids,
            operation=lambda item_id: self.add_to_collection(collection_id, item_id),
            description=f"Adding {len(item_ids)} items to collection"
        )
```

**Benefits:**
- ✅ Removes 80 LOC of duplicated batch logic
- ✅ Consistent error handling across all batch operations
- ✅ Automatic aggregation of results
- ✅ Built-in logging and metrics

#### Step 2.2.3: Apply MetadataMapper to Metadata Updates
**Simplifies:** ~40 LOC in LibraryManager

**Current pattern:**
```python
async def update_book_metadata(self, library_id, book_id, metadata):
    # Manual field mapping and validation
    update_data = {
        "title": metadata.get("title"),
        "author": metadata.get("author"),
        "genres": metadata.get("genres", []),
        "datePublished": metadata.get("published_date"),
        "duration": int(metadata.get("duration", 0)),
    }
    # ... validation ...
    return await self.client._request(
        "PATCH",
        f"/api/libraries/{library_id}/items/{book_id}",
        json=update_data
    )
```

**After MetadataMapper:**
```python
# In LibraryManager.__init__
self.metadata_mapper = MetadataMapper({
    "title": FieldMapping("title"),
    "author": FieldMapping("author"),
    "genres": FieldMapping("genres", optional=True, default=[]),
    "datePublished": FieldMapping("published_date"),
    "duration": FieldMapping("duration", transform=int, optional=True, default=0),
})

async def update_book_metadata(self, library_id, book_id, metadata):
    update_data = self.metadata_mapper.transform(metadata)
    return await self.client._request(
        "PATCH",
        f"/api/libraries/{library_id}/items/{book_id}",
        json=update_data
    )
```

**Benefits:**
- ✅ Removes 40 LOC of manual mapping
- ✅ Declarative field transformations
- ✅ Built-in validation
- ✅ Easy to extend with new fields

#### Step 2.2.4: Apply Pagination Mixin to Library Queries
**Simplifies:** ~50 LOC in LibraryManager

**Current pattern:**
```python
async def get_library_items(self, library_id, limit=100, offset=0, **kwargs):
    all_items = []
    current_offset = offset

    while True:
        response = await self.client._request(
            "GET",
            f"/api/libraries/{library_id}/items",
            params={"limit": limit, "offset": current_offset, **kwargs}
        )

        items = response.get("results", [])
        if not items:
            break

        all_items.extend(items)

        if len(items) < limit:
            break

        current_offset += limit

    return all_items
```

**After PaginationMixin:**
```python
# In LibraryManager (mixin inheritance)
class LibraryManager(PaginationMixin):
    async def get_library_items(self, library_id, limit=100, offset=0, **kwargs):
        return await self.paginate(
            endpoint=f"/api/libraries/{library_id}/items",
            limit=limit,
            offset=offset,
            params=kwargs
        )
```

**Benefits:**
- ✅ Removes 50 LOC of pagination logic
- ✅ Automatic handling of multiple pages
- ✅ Consistent pagination across all clients
- ✅ Support for callback-based processing

#### Step 2.2.5: Inherit from AuthenticatedAsyncClient
**Removes:** ~200 LOC (session management, retry logic)

```python
# BEFORE
class AudiobookshelfClient:
    def __init__(self, base_url, token, timeout=30):
        self.base_url = base_url
        self.token = token
        self.session = None

    @retry(stop=stop_after_attempt(3), ...)
    async def _request(self, method, endpoint, **kwargs):
        # ... retry logic ...

# AFTER
class AudiobookshelfClient(AuthenticatedAsyncClient):
    def __init__(self, base_url, token, timeout=30):
        super().__init__(base_url, timeout)
        self.auth_token = token

    async def _build_headers(self):
        headers = await super()._build_headers()
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers
```

**Benefits:**
- ✅ Removes 200 LOC of duplicated code
- ✅ Inherits working retry logic
- ✅ Gains context manager support
- ✅ Consistent with qBittorrent refactoring

### 2.3 Files Changed/Created

| File | Change | Impact |
|------|--------|--------|
| `backend/integrations/abs_client.py` | Refactor - 2,117 → 800 LOC | Inherits AuthenticatedAsyncClient, orchestrates managers |
| `backend/integrations/abs_managers/__init__.py` | CREATE | Package init, exports all managers |
| `backend/integrations/abs_managers/library_manager.py` | CREATE - 200 LOC | Books, search, import, scan operations |
| `backend/integrations/abs_managers/collection_manager.py` | CREATE - 150 LOC | Collection CRUD + batch operations |
| `backend/integrations/abs_managers/playlist_manager.py` | CREATE - 270 LOC | Playlist CRUD + batch operations |
| `backend/integrations/abs_managers/progress_manager.py` | CREATE - 160 LOC | Progress tracking, bookmarks, sessions |
| `backend/integrations/abs_managers/user_manager.py` | CREATE - 110 LOC | User profile, settings, permissions |
| `backend/integrations/abs_managers/backup_manager.py` | CREATE - 120 LOC | Backup operations |
| `backend/integrations/abs_managers/notification_manager.py` | CREATE - 160 LOC | Notifications management |
| `backend/integrations/abs_managers/rss_manager.py` | CREATE - 60 LOC | RSS feed operations |
| `backend/integrations/abs_managers/api_key_manager.py` | CREATE - 50 LOC | API key operations |
| `backend/integrations/abs_managers/email_manager.py` | CREATE - 70 LOC | Email settings & tests |
| `backend/tests/integrations/test_abs_client.py` | UPDATE | Refactored tests for new structure |

### 2.4 Testing Strategy

**Contract Tests (ensuring compatibility):**
1. ✅ All public methods still work identically
2. ✅ All return types unchanged
3. ✅ All exceptions unchanged
4. ✅ Error messages consistent

**Unit Tests for Managers:**
1. ✅ LibraryManager - 15-20 tests
2. ✅ CollectionManager - 12-15 tests
3. ✅ PlaylistManager - 12-15 tests
4. ✅ ProgressManager - 10-12 tests
5. ✅ UserManager - 8-10 tests
6. ✅ BackupManager - 6-8 tests
7. ✅ NotificationManager - 6-8 tests
8. ✅ RSSManager - 4-6 tests
9. ✅ APIKeyManager - 4-6 tests
10. ✅ EmailManager - 4-6 tests

**Total new tests:** 80-105 tests

### 2.5 Backwards Compatibility

**Proxy methods on main client:**
```python
class AudiobookshelfClient(AuthenticatedAsyncClient):
    def __init__(self, base_url, token, timeout=30):
        super().__init__(base_url, timeout)
        self.auth_token = token
        self.libraries = LibraryManager(self)
        self.collections = CollectionManager(self)
        self.playlists = PlaylistManager(self)
        # ... etc ...

    # Backwards compatibility - proxy to managers
    async def get_library_items(self, *args, **kwargs):
        return await self.libraries.get_library_items(*args, **kwargs)

    async def create_collection(self, *args, **kwargs):
        return await self.collections.create(*args, **kwargs)

    # ... etc for all public methods ...
```

**Migration path for users:**
```python
# OLD WAY (still works)
client = AudiobookshelfClient(base_url, token)
books = await client.get_library_items(library_id)

# NEW WAY (more organized)
async with AudiobookshelfClient(base_url, token) as client:
    books = await client.libraries.get_library_items(library_id)
    await client.playlists.create_playlist("My Playlist")
```

---

## STEP 3: RatioEmergencyService Integration

**Current:** 807 LOC | **Target:** 920 LOC | **Change:** +113 LOC (adds functionality)

### 3.1 Architecture Changes

#### Current Issues
1. Multiple TODO stubs for qBittorrent integration (lines 527, 573, 619, 689, 720)
2. Placeholder implementations for torrent pause/resume
3. No actual point tracking
4. No actual recovery time calculation

#### Target Changes
1. ✅ Integrate actual refactored QBittorrentClient
2. ✅ Implement pause/resume/delete torrents
3. ✅ Implement point generation tracking
4. ✅ Implement recovery time estimation with real data

### 3.2 Refactoring Steps

#### Step 3.2.1: Integrate QBittorrentClient
**Adds:** ~50 LOC for proper integration

```python
# BEFORE
class RatioEmergencyService:
    def __init__(self, config):
        # TODO: integrate QBittorrentClient
        self.qb_client = None

    async def _pause_non_seeding_torrents(self):
        # TODO: Integrate with actual qBittorrent API
        logger.debug("SECTION 2: Pausing torrents...")
        return []

# AFTER
class RatioEmergencyService:
    def __init__(self, config, qb_client: QBittorrentClient):
        self.qb_client = qb_client
        self.config = config

    async def _pause_non_seeding_torrents(self):
        """Pause all torrents that aren't seeding."""
        logger.debug("SECTION 2: Pausing non-seeding torrents...")

        torrents = await self.qb_client.get_all_torrents(
            filter="downloading",
            hashes="all"
        )

        paused = await self.qb_client.batch_pause_torrents(
            [t["hash"] for t in torrents]
        )

        logger.info(f"Paused {len(paused)} torrents")
        return paused
```

**Benefits:**
- ✅ Actual qBittorrent integration
- ✅ Proper error handling
- ✅ Uses batch operations for efficiency
- ✅ Logging for monitoring

#### Step 3.2.2: Implement Torrent Control Methods
**Adds:** ~60 LOC (refactor from stubs)

```python
async def _unpause_all_seeding(self):
    """Resume all seeding torrents."""
    logger.debug("SECTION 3: Resuming seeding torrents...")

    torrents = await self.qb_client.get_all_torrents(
        filter="seeding",
        hashes="all"
    )

    resumed = await self.qb_client.batch_resume_torrents(
        [t["hash"] for t in torrents]
    )

    logger.info(f"Resumed {len(resumed)} torrents")
    return resumed
```

**Adds batch methods to QBittorrentClient:**
```python
# In QBittorrentClient
async def batch_pause_torrents(self, hashes):
    return await self.batch_operation(
        items=hashes,
        operation=lambda h: self.pause_torrent(h),
        description=f"Pausing {len(hashes)} torrents"
    )

async def batch_resume_torrents(self, hashes):
    return await self.batch_operation(
        items=hashes,
        operation=lambda h: self.resume_torrent(h),
        description=f"Resuming {len(hashes)} torrents"
    )
```

**Benefits:**
- ✅ Removes TODO stubs
- ✅ Uses batch operations
- ✅ Clear logging and tracking
- ✅ Proper error aggregation

#### Step 3.2.3: Implement Point Generation Tracking
**Adds:** ~80 LOC (replaces stub calculations)

```python
async def track_point_generation(self) -> Dict[str, Any]:
    """Track actual point earning vs spending."""
    logger.debug("SECTION 4: Tracking point generation...")

    if not self.qb_client:
        logger.warning("qBittorrent client not configured, skipping point tracking")
        return {"status": "skipped"}

    # Get current torrent stats
    server_state = await self.qb_client.get_server_state()
    current_dl = server_state.get("dl_info_data", 0)

    # Get last recorded stats
    last_record = self.db.query(RatioLog).order_by(
        RatioLog.created_at.desc()
    ).first()

    if not last_record:
        return {"status": "first_check"}

    # Calculate point generation
    data_since_check = (current_dl - last_record.data_downloaded) / (1024**3)  # Convert to GB
    points_earned = data_since_check * 1.5  # ABS earning rate

    # Get spending from downloads
    downloads = self.db.query(Download).filter(
        Download.created_at > last_record.created_at
    ).all()

    points_spent = sum(d.cost_points for d in downloads)
    net_points = points_earned - points_spent

    logger.info(
        f"Points earned: {points_earned:.2f} | "
        f"Points spent: {points_spent:.2f} | "
        f"Net: {net_points:.2f}"
    )

    return {
        "earned": points_earned,
        "spent": points_spent,
        "net": net_points,
        "data_downloaded_gb": data_since_check
    }
```

**Benefits:**
- ✅ Real point tracking using actual qBittorrent stats
- ✅ Compares with database records
- ✅ Accurate point calculations
- ✅ Clear logging of metrics

#### Step 3.2.4: Implement Recovery Time Calculation
**Adds:** ~60 LOC (replaces rough estimates)

```python
async def calculate_recovery_time(self) -> Dict[str, Any]:
    """Calculate estimated time to ratio recovery."""
    logger.debug("SECTION 5: Calculating recovery time...")

    if not self.qb_client:
        logger.warning("qBittorrent client not configured, skipping recovery calculation")
        return {"status": "unknown"}

    # Get current ratio
    current_ratio = await self._fetch_current_ratio()
    target_ratio = self.RATIO_RECOVERY  # 1.05

    if current_ratio >= target_ratio:
        return {
            "status": "already_recovered",
            "current_ratio": current_ratio,
            "target_ratio": target_ratio
        }

    # Get current data rates
    server_state = await self.qb_client.get_server_state()
    dl_rate = server_state.get("dl_info_speed", 0) / 1024**2  # Convert to MB/s
    ul_rate = server_state.get("up_info_speed", 0) / 1024**2

    if not dl_rate or not ul_rate:
        return {"status": "no_activity"}

    # Calculate recovery point needed (based on current downloaded)
    total_downloads = server_state.get("dl_info_data", 0) / 1024**3
    points_at_target = total_downloads * target_ratio
    points_needed = points_at_target - (total_downloads * current_ratio)

    # Estimate time based on current earning rate
    points_per_gb = 1.5  # ABS earning rate
    gb_needed = points_needed / points_per_gb

    # Estimate download time
    if dl_rate > 0:
        dl_hours_needed = (gb_needed * 1024) / (dl_rate * 3600)  # Convert to MB, then to hours
    else:
        dl_hours_needed = float('inf')

    # Add buffer for point spending
    buffer_hours = 2
    total_hours = max(dl_hours_needed + buffer_hours, 1)

    logger.info(
        f"Recovery estimate: {total_hours:.1f} hours | "
        f"Current ratio: {current_ratio:.3f} | "
        f"Target ratio: {target_ratio:.3f}"
    )

    return {
        "status": "estimated",
        "current_ratio": current_ratio,
        "target_ratio": target_ratio,
        "hours_to_recovery": total_hours,
        "gb_to_download": gb_needed,
        "current_dl_rate_mbps": dl_rate
    }
```

**Benefits:**
- ✅ Real recovery time estimates
- ✅ Based on actual download rates
- ✅ Accounts for point spending patterns
- ✅ Provides detailed recovery metrics

#### Step 3.2.5: Add Batch Control to QBittorrentClient
**Adds:** ~40 LOC to qbittorrent_client.py

```python
# In QBittorrentClient, add methods using BatchOperationsMixin
class QBittorrentClient(AuthenticatedAsyncClient, BatchOperationsMixin):

    async def batch_pause_torrents(self, hashes: List[str]) -> Dict[str, Any]:
        """Pause multiple torrents with batch error handling."""
        return await self.batch_operation(
            items=hashes,
            operation=lambda h: self.pause_torrent(h),
            description=f"Pausing {len(hashes)} torrents"
        )

    async def batch_resume_torrents(self, hashes: List[str]) -> Dict[str, Any]:
        """Resume multiple torrents with batch error handling."""
        return await self.batch_operation(
            items=hashes,
            operation=lambda h: self.resume_torrent(h),
            description=f"Resuming {len(hashes)} torrents"
        )
```

**Benefits:**
- ✅ Efficient batch operations
- ✅ Proper error aggregation
- ✅ Clear logging of results
- ✅ Reusable pattern for other batch operations

### 3.3 Files Changed/Created

| File | Change | Impact |
|------|--------|--------|
| `backend/integrations/ratio_emergency_service.py` | Refactor - 807 → 920 LOC | Adds actual implementations, removes stubs |
| `backend/integrations/qbittorrent_client.py` | Extend | Adds batch_pause_torrents, batch_resume_torrents |
| `backend/tests/integrations/test_ratio_emergency_service.py` | CREATE | Tests for new implementations |

### 3.4 Configuration Changes

**No breaking changes to existing config**

```python
# BEFORE
service = RatioEmergencyService(config)

# AFTER (with qBittorrent integration)
qb_client = QBittorrentClient(config["qbittorrent"]["url"], ...)
service = RatioEmergencyService(config, qb_client)
```

### 3.5 Integration with Scheduler

```python
# In background scheduler
async def monitor_ratio():
    """Run ratio check every 5 minutes."""
    qb_client = QBittorrentClient(config["qbittorrent"]["url"], ...)
    service = RatioEmergencyService(config, qb_client)

    async with qb_client:
        result = await service.check_ratio_status()

        if result.get("emergency_triggered"):
            logger.warning("RATIO EMERGENCY ACTIVATED!")
            metrics = await service.get_emergency_metrics()
            logger.info(f"Emergency metrics: {metrics}")

scheduler.add_job(
    monitor_ratio,
    'interval',
    minutes=5,
    id='ratio_monitor'
)
```

---

## Testing Strategy for Phase 2

### Unit Tests (Per Module)

**QBittorrentClient Tests (new/updated):**
- 15-20 tests for core client methods
- 8-12 tests for BandwidthManager
- 8-12 tests for RSSManager
- Total: ~35-44 tests

**AbsClient Tests (new/updated):**
- 20-25 tests for LibraryManager
- 15-18 tests for CollectionManager
- 15-18 tests for PlaylistManager
- 12-15 tests for ProgressManager
- 10-12 tests for UserManager
- 6-8 tests for other managers
- Total: ~88-106 tests

**RatioEmergencyService Tests (new/updated):**
- 8-10 tests for recovery time calculation
- 8-10 tests for point tracking
- 6-8 tests for torrent control
- Total: ~22-28 tests

### Integration Tests

**Phase 2 Integration Tests:**
- QBittorrent ↔ RatioEmergencyService
- ABS Client ↔ RatioEmergencyService
- Full workflow: Monitor → Detect → Act → Recover

### Contract Tests (Backwards Compatibility)

**For each refactored module:**
1. ✅ All public methods have same signatures
2. ✅ All methods return same types
3. ✅ All exceptions raised are unchanged
4. ✅ Error messages are consistent
5. ✅ Performance is comparable or better

### Performance Tests

**Metrics to track:**
1. Request latency (should be same or better)
2. Memory usage (should decrease with duplication removed)
3. Batch operation performance
4. Pagination performance

---

## Timeline & Phases

### Phase 2.1: QBittorrentClient Refactoring (Week 1)
1. ✅ Inherit from AuthenticatedAsyncClient
2. ✅ Extract BandwidthManager
3. ✅ Extract RSSManager
4. ✅ Write unit tests
5. ✅ Contract/backwards compatibility tests

### Phase 2.2: AbsClient Refactoring (Week 2-3)
1. ✅ Create all manager modules
2. ✅ Apply mixins (Batch, Pagination, MetadataMapper)
3. ✅ Inherit from AuthenticatedAsyncClient
4. ✅ Create proxy methods for backwards compatibility
5. ✅ Write unit tests
6. ✅ Contract/backwards compatibility tests

### Phase 2.3: RatioEmergencyService Integration (Week 3-4)
1. ✅ Integrate refactored QBittorrentClient
2. ✅ Implement actual torrent control
3. ✅ Implement point tracking
4. ✅ Implement recovery calculation
5. ✅ Write integration tests
6. ✅ Performance testing

### Phase 2.4: Final Testing & Deployment (Week 4-5)
1. ✅ Full integration tests
2. ✅ Performance benchmarking
3. ✅ Documentation updates
4. ✅ Deployment preparation

---

## Success Criteria

### Code Quality Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Total LOC (3 files) | 3,585 | 4,257 | To reduce by 672 |
| Duplication | <5% | ~25% | To remove ~19% |
| Module cohesion | High | Medium | To improve |
| Test coverage | >90% | ~85% | To improve |
| Max file size | <800 LOC | 2,117 LOC | To refactor |

### Functional Requirements

- ✅ All existing functionality preserved
- ✅ All public APIs backwards compatible
- ✅ All error handling maintained
- ✅ All logging levels and messages consistent
- ✅ New functionality in RatioEmergencyService implemented
- ✅ No breaking changes to dependent code

### Testing Requirements

- ✅ 100+ new unit tests created
- ✅ >90% code coverage for new modules
- ✅ All contract tests passing
- ✅ All integration tests passing
- ✅ All backwards compatibility tests passing

---

## Rollback Plan

If any step fails:

1. **Unit test failure** → Fix the specific manager/method
2. **Integration test failure** → Review manager integration points
3. **Backwards compatibility failure** → Implement proxy methods
4. **Performance regression** → Profile and optimize specific code paths

All changes are additive (new manager files) or refactoring (same functionality, different structure), so rollback is as simple as reverting files.

---

## Documentation Plan

1. ✅ Update README with new module structure
2. ✅ Create MANAGER_DOCUMENTATION.md for each manager
3. ✅ Create MIGRATION_GUIDE.md for developers
4. ✅ Update code comments and docstrings
5. ✅ Create architecture diagrams
6. ✅ Update API documentation

---

## Next Steps

**Immediate (Week 1):**
1. Review this implementation plan
2. Prepare QBittorrentClient refactoring
3. Set up test structure for QBittorrent managers
4. Begin Step 1: QBittorrentClient Refactoring

**Then (Weeks 2-3):**
5. Refactor AbsClient
6. Create 10 manager modules
7. Apply pattern mixins

**Finally (Weeks 3-4):**
8. Integrate RatioEmergencyService
9. Full system testing
10. Documentation

---

## Conclusion

Phase 2 Implementation will:
- ✅ Reduce 672 LOC (15.8% reduction)
- ✅ Remove ~95% of code duplication
- ✅ Create 13 focused, testable modules
- ✅ Apply all pattern modules from Phase 1
- ✅ Maintain 100% backwards compatibility
- ✅ Improve code maintainability significantly

All changes follow established patterns and best practices, ensuring a smooth transition from monolithic to modular architecture.
