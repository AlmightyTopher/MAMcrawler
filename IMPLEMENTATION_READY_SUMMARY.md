# MAMcrawler Autonomous Implementation - Ready for Execution

**Status:** ✅ READY TO IMPLEMENT
**Date:** November 21, 2025
**Previous Work:** Complete infrastructure audit + integration planning

---

## WHAT EXISTS (DON'T REBUILD)

Your project already has all the foundational infrastructure built. We will **integrate into what exists** rather than creating duplicates.

### ✅ CORE INFRASTRUCTURE (Already Working)
- FastAPI REST API with 60+ endpoints
- 10 database ORM models with proper relationships
- 7 business logic services (book, series, author, download, metadata, task, failed_attempt)
- 4 external integrations (Audiobookshelf, qBittorrent, Google Books, Prowlarr)
- APScheduler task scheduling with database persistence
- Background task processor
- Resource monitoring system
- Master Audiobook Manager orchestrator

### ✅ DOWNLOAD WORKFLOW (Section 7 - Already Works)
- Prowlarr search client (`prowlarr_client.py`)
- MAM crawler with authentication (`mam_crawler.py`)
- qBittorrent integration (`qbittorrent_client.py`)
- Download service with retry logic (`download_service.py`)
- **Free-first enforcement ready to be implemented**

### ✅ CRAWLING INFRASTRUCTURE (Ready to Schedule)
- Stealth audiobook downloader (human-like behavior)
- Category crawler (genre/timespan discovery)
- Series completion crawler
- Author completion crawler
- **All ready to be automated with scheduling**

### ✅ METADATA PIPELINE (Ready to Integrate)
- Goodreads scraper
- Google Books integration
- Audio verification (`audiobook_audio_verifier.py`)
- Metadata extraction and conflict resolution
- **All ready to be triggered automatically**

### ⚠️ PARTIALLY IMPLEMENTED
- VIP Status Manager exists but missing MAM API integration
- qBittorrent monitoring exists but runs weekly (needs continuous)
- Ratio tracking structure exists but not fully automated
- **All need enhancement, not rebuilding**

---

## WHAT TO BUILD (4 Phases)

### **PHASE 1: VIP PRIORITY + RATIO EMERGENCY (Week 1)**

**Create 2 New Services:**

1. **MAMRulesService** (`backend/services/mam_rules_service.py`)
   - Daily scrape at 12:00 PM of 7 MAM pages
   - Cache rules in database
   - Detect freeleech/bonus/event status
   - Purpose: Implement Section 1 (Daily MAM Rules Scraping)

2. **RatioEmergencyService** (`backend/services/ratio_emergency_service.py`)
   - Monitor global ratio continuously
   - When ratio ≤ 1.00:
     - Freeze paid downloads
     - Increase seeding allocation
     - Force-continue stalled torrents
   - When ratio > 1.00: Resume normal downloads
   - Purpose: Implement Section 10 (Auto Ratio Emergency)

**Enhance Existing Models:**
- `Book` model: Add `narrator`, `quality_score`, `mam_rule_version`
- `Download` model: Add `integrity_status`, `release_edition`, `quality_score`
- New tables: `MamRules`, `EventStatus`, `RatioLog`

**Estimated Effort:** 40 hours
**Timeline:** 5 days (intensive)

---

### **PHASE 2: WEEKLY AUTOMATION + QUALITY ENFORCEMENT (Week 2)**

**Create 4 New Services:**

3. **QBittorrentMonitorService** (`backend/services/qbittorrent_monitor_service.py`)
   - Run **continuously** (every 5 minutes, not weekly)
   - Track all torrent states (downloading, seeding, stalled, errored)
   - Auto-restart stalled torrents
   - Implement point optimization logic (prioritize high-value seeders)
   - Purpose: Implement Section 10 (Continuous Monitoring) + point maximization

4. **CategorySyncService** (`backend/services/category_sync_service.py`)
   - Manage all 37 audiobook categories
   - Weekly sync using provided base URL format
   - Special handling for Fantasy (41) and Sci-Fi (47) top-10
   - Automatic download of missing titles
   - Purpose: Implement Section 4 (Weekly Category Sync)

5. **ReleaseQualityRulesService** (`backend/services/quality_rules_service.py`)
   - Implement 7-step quality priority rules
   - Calculate quality scores for each release
   - Prevent downloading inferior editions
   - Trigger replacement when superior found
   - Purpose: Implement Section 5 (Quality Rules)

6. **EventMonitorService** (enhance `mam_rules_service.py`)
   - Detect freeleech/bonus/multiplier events
   - Adjust download rate dynamically
   - Purpose: Implement Section 6 (Event-Aware Rate Adjustment)

**Register 4 New Scheduled Tasks:**
- Weekly metadata maintenance (books < 13 days old)
- Weekly category sync (all 37 genres + top-10)
- Weekly seeder management (evaluate point generation)
- Weekly series/author completion

**Estimated Effort:** 56 hours
**Timeline:** 7 days

---

### **PHASE 3: INTEGRITY + NARRATOR DETECTION (Week 3)**

**Create 1 New Service:**

7. **NarratorDetectionService** (`backend/services/narrator_detection_service.py`)
   - Speech-to-text detection from audio files
   - MAM metadata comparison for narrator
   - Audible narrator scraping (fallback)
   - Fuzzy matching for uncertain cases
   - Store narrator identity in Book model
   - Purpose: Implement Section 11 (Narrator Detection)

**Enhance Existing Infrastructure:**
- Integrate integrity checking into download completion
- Auto-trigger full scan (Section 14) after download
- Implement Duplicate Prevention Rules in scan
- Implement Metadata Conflict Resolution (Section 15)
- Implement Replacement Procedure (Section 16)

**Register 3 New Scheduled Tasks:**
- Auto metadata scan on first download (webhook-based)
- Monthly metadata drift correction (re-query Goodreads)
- Continuous integrity checking

**Estimated Effort:** 48 hours
**Timeline:** 6 days

---

### **PHASE 4: API + DASHBOARD + GO-LIVE (Week 4)**

**Create 8 New API Endpoints:**

VIP/Compliance:
- `GET /api/vip/status` - Current VIP, points, renewal date
- `GET /api/compliance/ratio` - Global ratio, emergency status
- `GET /api/compliance/report` - Monthly compliance report

System Control:
- `GET /api/system/mam-rules` - Current rules (all 7 pages)
- `GET /api/system/events` - Current events (freeleech/bonus)
- `GET /api/qbittorrent/status` - Real-time qBittorrent status
- `POST /api/system/autonomous/start` - Start autonomous daemon
- `POST /api/system/autonomous/stop` - Stop autonomous daemon

**Create Autonomous Dashboard:**
- Real-time VIP status display
- Ratio emergency indicator
- Download queue with quality scores
- Seeding statistics
- Event tracking
- Rules version and effective date

**Estimated Effort:** 64 hours
**Timeline:** 8 days

---

## IMPLEMENTATION SEQUENCE

```
Week 1 (Phase 1):
│
├─ Day 1-2: Database migrations + model enhancements
├─ Day 3-5: MAMRulesService + RatioEmergencyService
└─ Deploy: Both services tested and operational

Week 2 (Phase 2):
│
├─ Day 6-8: QBittorrentMonitorService + CategorySyncService
├─ Day 9-11: ReleaseQualityRulesService + EventMonitorService
├─ Day 12: Register 4 scheduled tasks
└─ Deploy: All weekly automation operational

Week 3 (Phase 3):
│
├─ Day 13-15: NarratorDetectionService
├─ Day 16-17: Enhance scanning + integrity
├─ Day 18: Register 3 continuous tasks
└─ Deploy: Scan + Integrity + Narrator working

Week 4 (Phase 4):
│
├─ Day 19-20: Create 8 API endpoints
├─ Day 21-22: Build autonomous dashboard
├─ Day 23: Integration testing
└─ Day 24: Go-live + monitoring

TOTAL: 4 weeks (160 hours estimated developer time)
```

---

## SPECIFICATION SECTIONS MAPPING

| Section | Title | Status | Implementation |
|---------|-------|--------|-----------------|
| 1 | Daily MAM Rules Scraping + VIP | Phase 1 | MAMRulesService (daily 12:00 PM) |
| 2 | Auto Metadata Scan on First Download | Phase 3 | Webhook + Full Scan integration |
| 3 | Weekly Metadata Maintenance | Phase 2 | Scheduled task (weekly) |
| 4 | Weekly Category Sync (37 genres + top-10) | Phase 2 | CategorySyncService |
| 5 | Release Quality Rules | Phase 2 | ReleaseQualityRulesService |
| 6 | Event-Aware Download Rate | Phase 2 | EventMonitorService |
| 7 | Download Workflow (Prowlarr → MAM → qBT) | **EXISTS** | Enhance free-first enforcement |
| 8 | Series Completion | Phase 2 | Scheduled task (existing service) |
| 9 | Author & Series Completion | Phase 2 | Scheduled task (existing service) |
| 10 | Continuous qBittorrent Monitoring + Ratio Emergency | Phase 1-2 | QBittorrentMonitorService + RatioEmergencyService |
| 11 | Narrator Detection | Phase 3 | NarratorDetectionService |
| 12 | Monthly Metadata Drift | Phase 3 | Scheduled task (monthly) |
| 13 | Post-Download Integrity Check | Phase 3 | Auto-triggered after completion |
| 14 | Full Scan Definition | Phase 3 | Enhanced existing scan |
| 15 | Metadata Conflict Resolution | Phase 3 | Enhanced metadata service |
| 16 | Replacement Procedure | Phase 3 | Enhanced book service |

---

## CRITICAL REQUIREMENTS ADHERENCE

✅ **VIP Maintenance Absolute Priority**
- RatioEmergencyService ensures paid downloads blocked if VIP at risk
- MAMRulesService tracks VIP renewal needs
- API endpoint shows VIP status real-time

✅ **Free-First Enforcement**
- Download workflow must check for free/FL before paid
- Quality rules don't override free-first rule
- Implement in DownloadService.validate_release_selection()

✅ **Duplicate Prevention**
- Scan prevents downloading inferior editions
- Narrator detection prevents duplicate narrators
- Quality score comparison prevents duplicate editions

✅ **.env File Protection**
- System reads from `.env` but NEVER modifies it
- All credentials sourced from existing `.env`
- No auto-writing of sensitive data

✅ **Specification Rules Obedience**
- All 15 sections will be fully implemented
- No modifications to existing working systems
- Integration only, no replacement of functional code

---

## SUCCESS CRITERIA

**Phase 1 Success:**
- [ ] VIP status tracking operational
- [ ] Ratio emergency system active
- [ ] MAM rules updating daily
- [ ] Database models extended
- [ ] All tests passing

**Phase 2 Success:**
- [ ] Weekly category sync running
- [ ] Quality rules enforced
- [ ] qBittorrent monitoring continuous
- [ ] All weekly tasks scheduled
- [ ] Download queue respecting quality

**Phase 3 Success:**
- [ ] Narrator detection working
- [ ] Integrity checks auto-triggered
- [ ] Full scans working
- [ ] Metadata conflicts resolved
- [ ] Replacement procedure operational

**Phase 4 Success:**
- [ ] All 8 API endpoints functional
- [ ] Dashboard deployed and operational
- [ ] Autonomous daemon running 24/7
- [ ] Monitoring alerts working
- [ ] All specification sections implemented

---

## READY TO PROCEED

**All prerequisites met:**
- ✅ Project audit complete
- ✅ Existing infrastructure documented
- ✅ Integration plan created
- ✅ Database schema defined
- ✅ Service architecture designed
- ✅ Scheduled tasks identified
- ✅ API endpoints specified

**Next Step:** Await approval to begin Phase 1 implementation.

---

**Estimated Timeline:** 4 weeks (full-time development)
**Go-Live Date:** Week 4 completion
**Ongoing Maintenance:** Autonomous system runs 24/7 after deployment

