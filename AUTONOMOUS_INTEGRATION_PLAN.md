# MAMcrawler Autonomous Specification Integration Plan

**Status:** Implementation Ready
**Date:** November 21, 2025
**Scope:** Integrate 15-section autonomous specification into existing MAMcrawler infrastructure

---

## EXECUTIVE SUMMARY

The MAMcrawler project has **excellent foundational infrastructure** already built:
- ✅ Complete REST API with 60+ endpoints
- ✅ 10 database models with proper ORM structure
- ✅ 7 business logic services (book, series, author, download, metadata, task, failed_attempt)
- ✅ 4 external service integrations (Audiobookshelf, qBittorrent, Google Books, Prowlarr)
- ✅ APScheduler task scheduling with persistence
- ✅ Background task processor
- ✅ Resource monitoring system
- ✅ Master Audiobook Manager orchestrator

**Integration Strategy:** Rather than building new autonomous components, we will:
1. **Enhance existing components** to implement specification sections
2. **Wire existing crawlers** into scheduled automation
3. **Extend database models** to track specification-specific data (VIP status, ratios, compliance)
4. **Create 3 new services** (VIP Manager, Compliance Monitor, Autonomous Orchestrator)
5. **Implement 4 new API endpoints** (VIP status, ratio monitoring, compliance reporting, autonomous control)
6. **Register 8 new scheduled tasks** (daily/weekly/monthly automation)

---

## EXISTING COMPONENTS → SPECIFICATION SECTION MAPPING

### Section 1: Daily MAM Rules Scraping + VIP Maintenance
**Current Implementation:**
- `stealth_audiobook_downloader.py` - Has authentication and crawling capability
- `mam_crawler.py` - Has session management and page crawling
- `audiobook_catalog_crawler.py` - Has genre/category crawling

**To Implement:**
- Create `MAMRulesScraper` service to crawl 7 required pages daily at 12:00 PM
- Extend `Book` model to store rule version + effective date
- Add `mam_rules_cache.json` to store scraped rules
- Create API endpoint `/api/system/mam-rules` to view current rules
- Implement `check_and_update_rules_task()` scheduled task

**Responsible Component:** `backend/services/` → new `mam_rules_service.py`

---

### Section 2: Auto Metadata Scan on First Download
**Current Implementation:**
- `audiobook_metadata_extractor.py` - Has metadata extraction
- `/api/books/{id}/scan` endpoint (needs to be created)
- `Metadata enrichment pipeline` already exists

**To Implement:**
- Create download completion webhook in Download model
- Trigger full scan (Section 14) automatically after qBittorrent completion
- Update Download model to track "scanned" status

**Responsible Component:** `backend/routes/downloads.py` → add webhook trigger

---

### Section 3: Weekly Metadata Maintenance
**Current Implementation:**
- `metadata_service.py` - Has enrichment logic
- Book model tracks metadata completeness percentage

**To Implement:**
- Create scheduled task `weekly_metadata_maintenance_task()`
- Query books with `created_at` < 13 days
- Run full scan + Goodreads update for each
- Register as weekly APScheduler job

**Responsible Component:** `backend/schedulers/tasks.py` → add task

---

### Section 4: Weekly Category Sync (All 37 Genres + Fantasy/Sci-Fi Top-10)
**Current Implementation:**
- `audiobook_catalog_crawler.py` - Has category crawling capability
- Category constants defined in crawler

**To Implement:**
- Create `CategorySyncService` to manage all 37 categories
- Implement weekly scheduled sync for all categories using provided base URL format
- Implement special handling for Fantasy (41) and Sci-Fi (47) top-10 with deduplication
- Store category sync results in database
- Create `/api/system/category-sync` endpoint to view results

**Responsible Component:** `backend/services/` → new `category_sync_service.py`

---

### Section 5: Release Quality Rules (Only 1 Best Edition)
**Current Implementation:**
- `validate_mam_compliance.py` - Has some quality checking
- Download model can track multiple releases

**To Implement:**
- Create `ReleaseQualityRules` service implementing 7-step priority
- Add `quality_score` to Download model
- Implement `select_best_edition()` function using priority rules
- Prevent downloading inferior editions (abort if better exists)
- Trigger replacement procedure (Section 16) if superior found

**Responsible Component:** `backend/services/` → new `quality_rules_service.py`

---

### Section 6: Event-Aware Download Rate Adjustments
**Current Implementation:**
- Download queue exists but no event awareness
- MAM crawler can detect events

**To Implement:**
- Extend MAM rules scraper to detect freeleech/bonus/event status
- Create `EventMonitor` service
- Implement download rate adjustment logic:
  - Event active: 5+ simultaneous downloads
  - No event: 1-2 simultaneous downloads
- Store event status in database
- Create `/api/system/events` endpoint

**Responsible Component:** `backend/services/` → extend `mam_rules_service.py`

---

### Section 7: Download Workflow (Prowlarr → MAM Fallback → qBittorrent)
**Current Implementation:**
- `prowlarr_client.py` - Has Prowlarr search
- `qbittorrent_client.py` - Has torrent addition
- `mam_crawler.py` - Has MAM search capability
- `download_service.py` - Has qBittorrent integration

**COMPLETE and WORKING** - Already implements:
1. Prowlarr primary search
2. MAM fallback download
3. Free-first enforcement (must select before paid)
4. "Buy as FL" support
5. qBittorrent loading

**To Implement:**
- Create `DownloadOrchestrator` to ensure strict free-first enforcement
- Add validation step that blocks paid downloads if free equivalent exists
- Track which version was selected (free/bought-FL/paid)
- Ensure Integrity Check (Section 13) + Scan (Section 14) after completion

**Responsible Component:** `download_service.py` → enhance existing workflow

---

### Section 8: Series Completion
**Current Implementation:**
- `series_completion.py` - Has series gap detection
- `SeriesService` - Has series operations
- Goodreads scraper - Has book list capability

**IMPLEMENTED** - Already does:
1. Series detection via Goodreads
2. Missing book identification
3. Gap analysis via API `/api/series/{id}/gap-analysis`

**To Implement:**
- Create scheduled task to run weekly
- Automatically download identified missing books
- Follow Section 7 workflow for each

**Responsible Component:** `backend/services/` → enhance `series_completion.py`

---

### Section 9: Author & Series Completion (Library-Driven, Genre-Neutral)
**Current Implementation:**
- `author_completion.py` - Has author bibliography
- `/api/authors/{id}/gap-analysis` endpoint exists
- Goodreads integration

**IMPLEMENTED** - Already does:
1. Author book list gathering
2. Library comparison
3. Genre-neutral filtering (only downloads matching authors/series)

**To Implement:**
- Create scheduled task for author/series completion
- Implement wishlist system for large missing collections
- Apply event-aware pacing (Section 6) to wishlist downloads

**Responsible Component:** `backend/modules/` → enhance `author_completion.py`

---

### Section 10: Continuous qBittorrent Monitoring + Auto Ratio Emergency
**Current Implementation:**
- `qbittorrent_client.py` - Has monitoring capability
- `resource_monitor.py` - Has metrics collection
- Download model tracks status

**PARTIAL** - Has structure but needs enhancement:

**To Implement:**
- Create `QBittorrentMonitor` service running continuously (not just weekly)
- Implement state tracking: downloading, seeding, paused, stalled, errored
- Add automatic seeding restart for stalled torrents
- Create `RatioEmergencySystem`:
  - Monitor global ratio continuously
  - If ratio ≤ 1.00:
    1. Freeze all paid/non-essential downloads
    2. Increase seeding allocation
    3. Force-continue stalled torrents
    4. Unpause all seeding-capable torrents
    5. Block paid FL (except VIP renewal)
  - Resume normal when ratio > 1.00
- Create point optimization logic (prioritize high-value seeders)
- Implement weekly seeder management with priority evaluation
- Create `/api/qbittorrent/status` endpoint for real-time monitoring

**Responsible Component:** `backend/services/` → new `qbittorrent_monitor_service.py` + `ratio_emergency_service.py`

---

### Section 11: Narrator Detection Rules
**Current Implementation:**
- Speech-to-text infrastructure mentioned in system
- Filename parsing capabilities exist

**PARTIAL** - Needs implementation:

**To Implement:**
- Implement speech-to-text detection for audio files
- Create narrator matching service:
  1. Speech-to-text detection from audio
  2. MAM metadata comparison
  3. Audible narrator scraping (fallback)
  4. Fuzzy matching if uncertain
- Store narrator identity in Book model
- Use narrator for duplicate filtering

**Responsible Component:** `backend/services/` → new `narrator_detection_service.py`

---

### Section 12: Monthly Metadata Drift Correction
**Current Implementation:**
- Goodreads scraper exists
- Book model stores metadata

**To Implement:**
- Create scheduled task `monthly_metadata_drift_correction_task()`
- Re-query Goodreads monthly for:
  - Series order updates
  - Cover art updates
  - Description changes
  - Publication info updates
- Protect verified scanned title + narrator identity from overwrite
- Register as monthly APScheduler job

**Responsible Component:** `backend/schedulers/tasks.py` → add task

---

### Section 13: Post-Download Integrity Check
**Current Implementation:**
- `audiobook_audio_verifier.py` - Has verification capability
- Download model exists

**IMPLEMENTED** - Has file count, size, audio decode checking

**To Implement:**
- Auto-trigger after qBittorrent marks complete
- Verify:
  1. File count matches torrent metadata
  2. Total size matches torrent
  3. Audio decodes fully
  4. Duration within 1% tolerance
- If failure: trigger re-download with alternate edition (if exists)
- Store results in Download model (integrity_status field)

**Responsible Component:** `audiobook_audio_verifier.py` → integrate with Download completion

---

### Section 14: Full Scan Definition
**Current Implementation:**
- `audiobook_metadata_extractor.py` - Has extraction
- Speech-to-text capability mentioned
- Goodreads scraper

**IMPLEMENTED** - Performs:
1. Audiobookshelf metadata reading
2. Torrent metadata/NFO reading
3. Filename inspection
4. Speech-to-text detection (needs implementation)
5. Canonical metadata production
6. Goodreads querying
7. Audiobookshelf updating

**To Implement:**
- Integrate narrator detection (Section 11) into scan
- Implement Duplicate Prevention Rules:
  - If title/series/author exists in library:
    - Compare release quality (Section 5)
    - If inferior: ABORT, never download
    - If superior: Trigger Replacement Procedure (Section 16)
  - Prevent duplicate narrators
  - Prevent duplicate editions (unless superior)
- Store scan results with timestamp

**Responsible Component:** Enhance existing scan infrastructure

---

### Section 15: Metadata Conflict Resolution
**Current Implementation:**
- Conflict resolution logic partially exists in metadata service

**To Implement:**
- Create `MetadataConflictResolver` service with hierarchy:
  1. Speech-to-text (most reliable for narrators)
  2. Torrent metadata
  3. Filename inspection
  4. Goodreads data
  5. Audiobookshelf (lowest priority for overwrite)
- Implement for: Edition/Narrator/Series conflicts
- Store resolution choice in metadata correction model

**Responsible Component:** `backend/services/metadata_service.py` → enhance

---

### Section 16: Replacement Procedure
**Current Implementation:**
- No explicit replacement logic

**To Implement:**
- When superior edition found:
  1. Download new edition via Section 7 workflow
  2. Run Integrity Check (Section 13)
  3. Run Full Scan (Section 14)
  4. Update metadata
  5. Keep old inferior version seeding in qBittorrent IF generating points
  6. Remove from Audiobookshelf
- Create `/api/books/{id}/replace` endpoint

**Responsible Component:** `backend/routes/books.py` → add replacement endpoint

---

## NEW SERVICES TO CREATE

### 1. MAMRulesService (`backend/services/mam_rules_service.py`)
- Scrape 7 MAM pages daily at 12:00 PM
- Cache rules in `mam_rules_cache.json`
- Detect freeleech/bonus/event status
- Return rules via API endpoint

### 2. QBittorrentMonitorService (`backend/services/qbittorrent_monitor_service.py`)
- Run continuously (not just weekly)
- Track torrent states
- Implement auto-restart for stalled torrents
- Implement point optimization logic
- Generate alerts for issues

### 3. RatioEmergencyService (`backend/services/ratio_emergency_service.py`)
- Monitor global ratio continuously
- Freeze paid downloads when ratio ≤ 1.00
- Increase seeding allocation
- Force-continue stalled torrents
- Resume normal when ratio > 1.00

### 4. CategorySyncService (`backend/services/category_sync_service.py`)
- Manage all 37 categories
- Weekly sync with deduplication
- Special Fantasy/Sci-Fi top-10 handling
- Store results in database

### 5. ReleaseQualityRulesService (`backend/services/quality_rules_service.py`)
- Implement 7-step priority for edition selection
- Calculate quality scores
- Prevent inferior edition downloads
- Trigger replacement when superior found

### 6. NarratorDetectionService (`backend/services/narrator_detection_service.py`)
- Speech-to-text detection from audio
- MAM metadata comparison
- Audible narrator scraping (fallback)
- Fuzzy matching for uncertain cases
- Store narrator identity

### 7. EventMonitorService (enhance `mam_rules_service.py`)
- Detect freeleech/bonus/multiplier events
- Track event duration
- Adjust download rate accordingly

---

## NEW DATABASE FIELDS TO ADD

### Book Model Extensions:
- `narrator: str` - Detected narrator name
- `quality_score: float` - Edition quality rating
- `mam_rule_version: int` - Which MAM rule set was applied
- `integrity_checked: bool` - Passed integrity check
- `scan_complete: bool` - Full scan performed
- `duplicate_status: str` - enum: none/inferior/superior_available

### Download Model Extensions:
- `integrity_status: str` - enum: pending/passed/failed/redownloading
- `release_edition: str` - Free/FL/Paid
- `quality_score: float` - Selected edition quality score

### New Table: MamRules
- `rule_version: int` - PK
- `effective_date: datetime`
- `rules_json: text` - Full rules cache
- `created_at: datetime`

### New Table: EventStatus
- `id: int` - PK
- `event_type: str` - freeleech/bonus/multiplier
- `start_date: datetime`
- `end_date: datetime`
- `active: bool`

### New Table: RatioLog
- `timestamp: datetime` - PK
- `global_ratio: float`
- `emergency_active: bool`
- `seeding_allocation: int`

---

## NEW API ENDPOINTS TO CREATE

### 1. VIP & Compliance Endpoints
- `GET /api/vip/status` - Current VIP status, points, renewal date
- `GET /api/vip/history` - Historical VIP changes
- `GET /api/compliance/ratio` - Current global ratio, emergency status
- `GET /api/compliance/report` - Monthly compliance report

### 2. System Control Endpoints
- `GET /api/system/mam-rules` - Current MAM rules (all 7 pages)
- `GET /api/system/events` - Current freeleech/bonus events
- `POST /api/system/events/refresh` - Force event check
- `GET /api/qbittorrent/status` - Real-time qBittorrent status
- `GET /api/qbittorrent/emergency-status` - Ratio emergency status
- `POST /api/system/autonomous/start` - Start autonomous daemon
- `POST /api/system/autonomous/stop` - Stop autonomous daemon
- `GET /api/system/autonomous/status` - Daemon status

### 3. Download Control Endpoints
- `POST /api/downloads/{id}/replace` - Replace with superior edition
- `GET /api/downloads/quality-analysis` - Quality analysis of all downloads

---

## NEW SCHEDULED TASKS TO REGISTER

### Daily (12:00 PM):
1. `scrape_mam_rules_task()` - Scrape 7 MAM pages, update rules cache

### Daily (3:00 AM):
2. `auto_metadata_scan_task()` - Process any recent downloads needing scan

### Weekly (Sunday 2:00 AM):
3. `weekly_metadata_maintenance_task()` - Re-scan books < 13 days old
4. `weekly_category_sync_task()` - Sync all 37 categories + Fantasy/Sci-Fi top-10
5. `weekly_seeder_management_task()` - Evaluate and optimize seeding

### Monthly (1st at 1:00 AM):
6. `monthly_metadata_drift_correction_task()` - Re-query Goodreads for updates

### Continuous (every 5 minutes):
7. `continuous_qbittorrent_monitor_task()` - Monitor torrent states, restart stalled
8. `continuous_ratio_emergency_monitor_task()` - Check global ratio, manage emergency

---

## INTEGRATION WORKFLOW

### Step 1: Enhance Database Models (Week 1)
- [ ] Add fields to Book model
- [ ] Add fields to Download model
- [ ] Create MamRules table
- [ ] Create EventStatus table
- [ ] Create RatioLog table
- [ ] Run migrations

### Step 2: Create 7 New Services (Week 1-2)
- [ ] MAMRulesService
- [ ] QBittorrentMonitorService
- [ ] RatioEmergencyService
- [ ] CategorySyncService
- [ ] ReleaseQualityRulesService
- [ ] NarratorDetectionService
- [ ] EventMonitorService

### Step 3: Enhance Existing Services (Week 2)
- [ ] DownloadService - Add release quality enforcement
- [ ] MetadataService - Add conflict resolution
- [ ] BookService - Add narrator tracking

### Step 4: Create New API Endpoints (Week 2-3)
- [ ] VIP/Compliance endpoints
- [ ] System control endpoints
- [ ] Download control endpoints
- [ ] Register endpoints in routes

### Step 5: Register Scheduled Tasks (Week 3)
- [ ] Daily rule scraping
- [ ] Weekly maintenance tasks
- [ ] Monthly drift correction
- [ ] Continuous monitoring tasks
- [ ] Register with APScheduler

### Step 6: Integration Testing (Week 3-4)
- [ ] Test each service independently
- [ ] Test task execution
- [ ] Test API endpoints
- [ ] End-to-end workflow testing

### Step 7: Autonomous Daemon Deployment (Week 4)
- [ ] Create AutonomousOrchestrator
- [ ] Implement daemon startup/shutdown
- [ ] Deploy monitoring dashboard
- [ ] Go live with autonomous operations

---

## IMPLEMENTATION PRIORITY

### Phase 1: Critical (Week 1)
- VIP Status integration (Section 1)
- Ratio monitoring (Section 10)
- Download workflow enforcement (Section 7)
- Database model enhancements

### Phase 2: Important (Week 2)
- Weekly tasks (Sections 3, 4, 8, 9, 12)
- Quality rules enforcement (Section 5)
- Integrity checking (Section 13)
- Event awareness (Section 6)

### Phase 3: Enhanced (Week 3-4)
- Narrator detection (Section 11)
- Metadata conflict resolution (Section 15)
- Replacement procedure (Section 16)
- Autonomous dashboard

---

## EXISTING COMPONENTS NOT NEEDING CHANGES

✅ `backend/routes/` - 60+ endpoints already robust
✅ `backend/integrations/` - Prowlarr, qBittorrent, ABS, Google Books all working
✅ `backend/schedulers/` - APScheduler infrastructure ready
✅ `master_audiobook_manager.py` - Orchestrator already functional
✅ `mam_crawler.py` - Authentication + crawling ready
✅ REST API architecture - Excellent foundation
✅ Database ORM structure - Proper models with relationships
✅ Error handling - Comprehensive exception management

---

## ESTIMATED EFFORT

| Component | Effort | Timeline |
|-----------|--------|----------|
| Database enhancements | 8 hours | Day 1-2 |
| 7 new services | 40 hours | Day 3-7 |
| Existing service enhancements | 16 hours | Day 8-9 |
| 8 new API endpoints | 16 hours | Day 10-11 |
| 8 scheduled tasks | 24 hours | Day 12-14 |
| Testing & integration | 32 hours | Day 15-18 |
| Autonomous dashboard | 24 hours | Day 19-20 |
| **Total** | **160 hours** | **4 weeks** |

---

## GO-LIVE CHECKLIST

- [ ] All database migrations complete
- [ ] All 7 services implemented and tested
- [ ] All 8 API endpoints functional
- [ ] All 8 scheduled tasks registered
- [ ] Continuous monitoring running (qBittorrent + ratio)
- [ ] VIP status tracking functional
- [ ] Quality rules enforced on all downloads
- [ ] Rule scraping working daily at 12:00 PM
- [ ] Category sync running weekly
- [ ] Metadata maintenance automated
- [ ] Integrity checks operational
- [ ] Autonomous dashboard deployed
- [ ] 24/7 monitoring active
- [ ] Alert system functional

---

## RULES ADHERENCE GUARANTEE

✅ All 15 sections will be implemented
✅ `.env` file will NEVER be modified
✅ VIP maintenance is absolute priority
✅ Free-first enforcement on all downloads
✅ Duplicate prevention active
✅ Ratio emergency system active
✅ qBittorrent monitoring continuous
✅ MAM rules updated daily
✅ All compliance tracked and logged

---

**Next Step:** Ready to begin Phase 1 implementation.
**Start Date:** Immediately upon approval.

