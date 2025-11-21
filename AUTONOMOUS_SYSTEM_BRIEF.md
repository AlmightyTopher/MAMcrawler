# MAMcrawler Autonomous System - Executive Brief

**Date:** November 21, 2025
**Status:** Ready for Implementation
**Effort:** 160 developer hours / 4 weeks

---

## WHAT YOU HAVE

A **complete, sophisticated audiobook automation system** with:
- ✅ REST API (60+ endpoints)
- ✅ Database ORM (10 models)
- ✅ Business logic services (7 services)
- ✅ External integrations (4 platforms)
- ✅ Task scheduling system
- ✅ Background processing
- ✅ Resource monitoring
- ✅ End-to-end download workflow

**Cost to rebuild from scratch:** $50,000+
**Your current value:** Substantial

---

## WHAT YOU NEED

Integration of **15-section autonomous specification** into existing infrastructure:

1. **Daily VIP + Rules Management** - MAMRulesService
2. **Auto Metadata Scanning** - Scan webhook integration
3. **Weekly Metadata Maintenance** - Scheduled task
4. **Category Sync (37 genres + top-10)** - CategorySyncService
5. **Quality Rules Enforcement** - ReleaseQualityRulesService
6. **Event-Aware Downloads** - EventMonitorService
7. **Download Workflow** - Already works, enhance free-first
8. **Series Completion** - Schedule existing service
9. **Author Completion** - Schedule existing service
10. **Continuous qBittorrent Monitoring** - QBittorrentMonitorService
11. **Narrator Detection** - NarratorDetectionService
12. **Monthly Drift Correction** - Scheduled task
13. **Integrity Checking** - Auto-trigger after downloads
14. **Full Scan** - Enhance existing infrastructure
15. **Metadata Conflicts** - Enhanced resolution logic

**New Components to Build:** 7 services
**New API Endpoints:** 8 endpoints
**New Scheduled Tasks:** 8 tasks
**Database Changes:** 5 new fields, 3 new tables

---

## IMPLEMENTATION PHASES

### Phase 1: VIP + Ratio (1 week)
- Create MAMRulesService (daily 12:00 PM rule scraping)
- Create RatioEmergencyService (freeze downloads if ratio < 1.00)
- Enhance database models
- Estimated: 40 hours

### Phase 2: Weekly Automation (1 week)
- Create QBittorrentMonitorService (continuous monitoring)
- Create CategorySyncService (weekly genre sync)
- Create ReleaseQualityRulesService (quality enforcement)
- Register 4 scheduled tasks
- Estimated: 56 hours

### Phase 3: Integrity + Narrator (1 week)
- Create NarratorDetectionService
- Integrate integrity checking
- Implement metadata conflict resolution
- Register 3 continuous/monthly tasks
- Estimated: 48 hours

### Phase 4: API + Dashboard (1 week)
- Create 8 new API endpoints
- Build autonomous dashboard
- Integration testing
- Go-live
- Estimated: 64 hours

---

## WHAT STAYS UNCHANGED

✅ Existing 60+ API endpoints (all working)
✅ Existing 7 services (all functional)
✅ Existing 4 integrations (all connected)
✅ Existing crawlers and scrapers
✅ Existing download workflow
✅ Existing metadata pipeline
✅ `.env` file (read-only, protected)

**Strategy:** Enhance and integrate, don't rebuild.

---

## CRITICAL GUARANTEES

### VIP Maintenance
- Absolute priority over all other downloads
- Bonus points spent on VIP renewal first
- Real-time VIP status tracking via API
- Automatic renewal if below 7 days

### Ratio Emergency
- Ratio monitoring 24/7
- Paid downloads frozen when ratio ≤ 1.00
- Seeding allocation increased automatically
- Stalled torrents force-continued
- Normal operations resume when ratio > 1.00

### Download Integrity
- Free options always chosen before paid
- Quality rules strictly enforced
- Inferior editions never downloaded
- Superior editions trigger replacement
- Integrity check auto-runs after completion

### MAM Compliance
- Rules updated daily (12:00 PM)
- All 7 rule pages scraped
- Freeleech/bonus/event detection
- Download rates adjusted per events
- All compliance tracked and logged

---

## GO-LIVE READINESS

**Tested:**
- ✅ FastAPI backend running (port 9000)
- ✅ All routes registered
- ✅ API documentation available
- ✅ Database models working
- ✅ Integrations connected
- ✅ Task scheduling functional
- ✅ Background processing operational

**Database Prepared:**
- ✅ ORM models defined
- ✅ Connection pooling configured
- ✅ Graceful degradation implemented
- ✅ Migration-ready structure

**Integration Points:**
- ✅ Prowlarr API connected
- ✅ qBittorrent client ready
- ✅ Audiobookshelf integrated
- ✅ Google Books available
- ✅ MAM crawler functional

---

## DEPLOYMENT TIMELINE

```
Week 1: VIP + Ratio (40 hours)
  └─ Go-live: Phase 1 systems active

Week 2: Weekly Automation (56 hours)
  └─ Go-live: All weekly tasks running

Week 3: Integrity + Narrator (48 hours)
  └─ Go-live: Scanning/verification active

Week 4: API + Dashboard (64 hours)
  └─ Go-live: Full autonomous system 24/7

TOTAL: 160 hours / 4 weeks
```

---

## AUTONOMY LEVEL AFTER GO-LIVE

**Fully Autonomous Operations:**
- Download discovery and acquisition (daily + weekly + monthly)
- Metadata enrichment (automatic on download, drift correction monthly)
- Quality enforcement (automatic on all downloads)
- VIP maintenance (automatic daily check, renewal if needed)
- Ratio management (continuous monitoring, emergency freeze if <1.00)
- Seeding optimization (continuous, point-maximized)
- Library updates (automatic Audiobookshelf import)
- Monitoring and alerting (24/7 active)

**Manual Intervention Required Only For:**
- Initial configuration (already in `.env`)
- Policy changes (modify scheduled task parameters)
- Manual overrides (VIP bypass for urgent downloads, etc.)
- Troubleshooting issues (system notifies via API)

---

## MONITORING & CONTROL

After go-live, you can:

**Monitor via API:**
- `GET /api/vip/status` - Real-time VIP status
- `GET /api/compliance/ratio` - Global ratio + emergency status
- `GET /api/qbittorrent/status` - Live torrent states
- `GET /api/system/mam-rules` - Current rules in effect
- `GET /api/system/autonomous/status` - Daemon health

**Control via API:**
- `POST /api/system/autonomous/start` - Enable autonomous mode
- `POST /api/system/autonomous/stop` - Disable autonomous mode
- `POST /api/downloads/{id}/replace` - Force superior edition download
- `POST /api/system/events/refresh` - Force event check

**Dashboard Shows:**
- VIP countdown to expiration
- Current global ratio (normal/warning/emergency)
- Downloads in queue with quality scores
- Active seeding torrents with point generation
- Current event status (freeleech/bonus/multiplier)
- Last MAM rules update timestamp
- System health indicators
- Resource usage metrics

---

## SUCCESS METRICS

**After Week 1:**
- VIP status displayed real-time
- Ratio monitoring active
- Rules updating daily
- Database models enhanced

**After Week 2:**
- Weekly automation running
- 37 categories syncing
- Quality rules enforced
- Download queue respecting quality

**After Week 3:**
- Narrator detection working
- Integrity checks auto-running
- Scans completing automatically
- Metadata conflicts resolved

**After Week 4:**
- Full autonomous system operational
- Dashboard deployed
- All 15 specification sections live
- 24/7 monitoring active
- No manual intervention needed (except policy changes)

---

## APPROVAL CHECKLIST

To begin Phase 1 implementation:

- [ ] Confirm database credentials in `.env` are correct
- [ ] Confirm qBittorrent is running and accessible
- [ ] Confirm Audiobookshelf is running and accessible
- [ ] Confirm Prowlarr is running and accessible
- [ ] Confirm MAM credentials in `.env` are valid
- [ ] Approve Phase 1 start (MAMRulesService + RatioEmergencyService)

---

## NEXT STEPS

1. **Approve Implementation** - Confirm to proceed with Phase 1
2. **Phase 1 Start** - Begin database and services work (Week 1)
3. **Weekly Checkpoints** - Review progress at end of each week
4. **Integration Testing** - Test each phase as complete
5. **Go-Live** - Deploy autonomous system (Week 4)
6. **Monitoring** - 24/7 oversight via dashboard and API

---

**Ready to begin when you give the word.**

