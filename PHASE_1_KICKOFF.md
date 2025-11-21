# PHASE 1 IMPLEMENTATION KICKOFF

**Phase:** 1 (VIP Maintenance + Ratio Emergency)
**Duration:** 1 week (40 hours)
**Timeline:** Days 1-5
**Status:** Awaiting approval

---

## PHASE 1 OBJECTIVE

Establish VIP priority and ratio monitoring as the foundational autonomous systems.

**Deliverables:**
1. MAMRulesService - Daily rule scraping at 12:00 PM (Section 1)
2. RatioEmergencyService - Ratio < 1.00 freeze mechanism (Section 10)
3. Enhanced database models (VIP/ratio/narrator tracking)
4. API endpoints for VIP and compliance status

---

## PHASE 1 ARCHITECTURE

### Service 1: MAMRulesService

**Location:** `backend/services/mam_rules_service.py`

**Responsibilities:**
- Scrape 7 MAM pages daily at 12:00 PM:
  1. `https://www.myanonamouse.net/rules.php`
  2. `https://www.myanonamouse.net/faq.php`
  3. `https://www.myanonamouse.net/f/b/18`
  4. `https://www.myanonamouse.net/f/b/78`
  5. `https://www.myanonamouse.net/guides/`
  6. `https://www.myanonamouse.net/updateNotes.php`
  7. `https://www.myanonamouse.net/api/list.php`

**Key Methods:**
```python
class MAMRulesService:
    async def scrape_rules_daily() -> dict
    async def get_current_rules() -> dict
    async def check_freeleech_status() -> bool
    async def check_bonus_event() -> bool
    async def check_multiplier_event() -> bool
    async def get_vip_requirements() -> dict
    async def cache_rules(rules_dict) -> None
```

**Implementation Details:**
- Use `stealth_audiobook_downloader.py` authentication
- Cache rules in `mam_rules_cache.json`
- Store version in new `MamRules` database table
- Return rules via API endpoint `/api/system/mam-rules`

---

### Service 2: RatioEmergencyService

**Location:** `backend/services/ratio_emergency_service.py`

**Responsibilities:**
- Monitor global ratio continuously
- Detect when ratio drops to/below 1.00
- Trigger emergency freeze on paid downloads
- Manage seeding allocation adjustments

**Key Methods:**
```python
class RatioEmergencyService:
    async def check_ratio_continuous() -> float
    async def trigger_emergency_freeze() -> None
    async def release_emergency_freeze() -> None
    async def increase_seeding_allocation() -> None
    async def force_continue_stalled_torrents() -> None
    async def is_emergency_active() -> bool
    async def get_current_ratio() -> float
    async def validate_download_allowed(is_paid: bool, is_vip_critical: bool) -> bool
```

**Implementation Details:**
- Query MAM API for current ratio (use `mam_crawler.py`)
- Check every 5 minutes
- When ratio ≤ 1.00:
  - Set `emergency_active = True`
  - Block all paid downloads (except VIP renewal)
  - Increase qBittorrent upload slots
  - Query qBittorrent for stalled torrents
  - Force-continue via qBittorrent API
- When ratio > 1.00:
  - Set `emergency_active = False`
  - Resume normal download behavior
- Store ratio history in `RatioLog` table
- Return status via API endpoint `/api/compliance/ratio`

---

## PHASE 1 DATABASE CHANGES

### Extend Book Model

```python
class Book(Base):
    # Existing fields...

    # New Phase 1 fields:
    narrator: str = Column(String(255), nullable=True)
    quality_score: float = Column(Float, nullable=True)
    mam_rule_version: int = Column(Integer, nullable=True)
    duplicate_status: str = Column(String(50), default="none")  # none/inferior/superior_available
```

### Extend Download Model

```python
class Download(Base):
    # Existing fields...

    # New Phase 1 fields:
    integrity_status: str = Column(String(50), default="pending")  # pending/passed/failed/redownloading
    release_edition: str = Column(String(50))  # Free/FL/Paid
    quality_score: float = Column(Float, nullable=True)
```

### Create MamRules Table

```python
class MamRules(Base):
    __tablename__ = "mam_rules"

    rule_version: int = Column(Integer, primary_key=True)
    effective_date: datetime = Column(DateTime, default=datetime.utcnow)
    rules_json: str = Column(Text)  # Full JSON cache of all 7 pages
    freeleech_active: bool = Column(Boolean, default=False)
    bonus_event_active: bool = Column(Boolean, default=False)
    multiplier_active: bool = Column(Boolean, default=False)
    event_details: str = Column(Text, nullable=True)  # JSON with event info
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
```

### Create RatioLog Table

```python
class RatioLog(Base):
    __tablename__ = "ratio_log"

    id: int = Column(Integer, primary_key=True)
    timestamp: datetime = Column(DateTime, default=datetime.utcnow, index=True)
    global_ratio: float = Column(Float)
    emergency_active: bool = Column(Boolean, default=False)
    seeding_allocation: int = Column(Integer, default=0)
```

### Create EventStatus Table

```python
class EventStatus(Base):
    __tablename__ = "event_status"

    id: int = Column(Integer, primary_key=True)
    event_type: str = Column(String(50))  # freeleech/bonus/multiplier
    start_date: datetime = Column(DateTime)
    end_date: datetime = Column(DateTime)
    active: bool = Column(Boolean, default=True)
    description: str = Column(Text, nullable=True)
```

---

## PHASE 1 API ENDPOINTS

### 1. Get VIP Status

```
GET /api/vip/status
Response:
{
  "vip_active": true,
  "days_until_expiry": 45,
  "total_points": 2500,
  "points_per_day": 25,
  "renewal_threshold": 2000,
  "status": "healthy" | "warning" | "critical",
  "last_updated": "2025-11-21T12:30:00Z"
}
```

### 2. Get Compliance Status

```
GET /api/compliance/ratio
Response:
{
  "global_ratio": 1.85,
  "emergency_active": false,
  "download_frozen": false,
  "seeding_allocation": 10,
  "stalled_torrents": 0,
  "status": "normal" | "warning" | "emergency",
  "last_updated": "2025-11-21T12:35:00Z"
}
```

### 3. Get MAM Rules

```
GET /api/system/mam-rules
Response:
{
  "rule_version": 1,
  "effective_date": "2025-11-21T12:00:00Z",
  "freeleech_active": false,
  "bonus_event_active": true,
  "multiplier_active": false,
  "event_details": {...},
  "rules_summary": {...},
  "last_updated": "2025-11-21T12:00:00Z"
}
```

### 4. Get Events

```
GET /api/system/events
Response:
{
  "active_events": [
    {
      "type": "bonus",
      "description": "2x bonus points",
      "end_date": "2025-11-23T23:59:59Z"
    }
  ],
  "current_impact": "increase_download_rate"
}
```

---

## PHASE 1 SCHEDULED TASKS

### Task 1: Daily MAM Rules Scraping

```python
@tasks.schedule("0 12 * * *")  # Daily at 12:00 PM
async def scrape_mam_rules_task():
    """
    Daily task to scrape and update MAM rules.
    Runs every day at 12:00 PM.
    """
    service = MAMRulesService()
    new_rules = await service.scrape_rules_daily()
    await service.cache_rules(new_rules)

    # Log task execution
    task_service.create_task_record(
        name="scrape_mam_rules",
        status="success",
        items_processed=1,
        items_succeeded=1
    )
```

### Task 2: Continuous Ratio Monitoring

```python
@tasks.schedule("*/5 * * * *")  # Every 5 minutes
async def continuous_ratio_monitor_task():
    """
    Continuous task to monitor global ratio.
    Runs every 5 minutes around the clock.
    """
    service = RatioEmergencyService()
    current_ratio = await service.check_ratio_continuous()

    if current_ratio <= 1.00 and not service.is_emergency_active():
        await service.trigger_emergency_freeze()
        # Alert user
        logger.error(f"RATIO EMERGENCY: Global ratio {current_ratio}")

    elif current_ratio > 1.00 and service.is_emergency_active():
        await service.release_emergency_freeze()
        logger.info(f"Ratio recovered: {current_ratio}")
```

---

## PHASE 1 IMPLEMENTATION CHECKLIST

### Days 1-2: Database
- [ ] Create migration files for new tables
- [ ] Add fields to Book model
- [ ] Add fields to Download model
- [ ] Create MamRules model
- [ ] Create RatioLog model
- [ ] Create EventStatus model
- [ ] Run migrations
- [ ] Test database connections

### Days 2-3: MAMRulesService
- [ ] Create `backend/services/mam_rules_service.py`
- [ ] Implement `scrape_rules_daily()` using stealth crawler auth
- [ ] Implement `cache_rules()` to save to database
- [ ] Implement event detection (freeleech, bonus, multiplier)
- [ ] Add error handling and retry logic
- [ ] Write unit tests
- [ ] Test daily at 12:00 PM

### Days 3-4: RatioEmergencyService
- [ ] Create `backend/services/ratio_emergency_service.py`
- [ ] Implement `check_ratio_continuous()` (query MAM)
- [ ] Implement `trigger_emergency_freeze()` (prevent paid downloads)
- [ ] Implement `release_emergency_freeze()` (resume normal)
- [ ] Implement qBittorrent seeding adjustment
- [ ] Add logging and alerts
- [ ] Write unit tests
- [ ] Test emergency freeze/release

### Days 4-5: API & Deployment
- [ ] Create `/api/vip/status` endpoint in `backend/routes/system.py`
- [ ] Create `/api/compliance/ratio` endpoint
- [ ] Create `/api/system/mam-rules` endpoint
- [ ] Create `/api/system/events` endpoint
- [ ] Register both services in scheduler
- [ ] Integrate into FastAPI app
- [ ] Integration testing
- [ ] Deploy and monitor

---

## PHASE 1 SUCCESS CRITERIA

✅ **Database:**
- All migrations run successfully
- New fields exist on Book and Download models
- New tables created and accessible
- No data loss

✅ **MAMRulesService:**
- Scrapes all 7 pages daily
- Rules cached in database
- Event detection working
- API endpoint returns current rules
- Task runs at 12:00 PM every day
- Error handling and logging functional

✅ **RatioEmergencyService:**
- Ratio checked every 5 minutes
- Emergency activated when ratio ≤ 1.00
- Emergency deactivated when ratio > 1.00
- Paid downloads blocked in emergency
- VIP renewal still allowed in emergency
- Seeding allocation increased
- API endpoint shows current status
- Task runs continuously

✅ **API Endpoints:**
- `/api/vip/status` returns correct data
- `/api/compliance/ratio` returns correct data
- `/api/system/mam-rules` returns rules
- `/api/system/events` returns events
- All endpoints properly secured
- All endpoints tested

✅ **Integration:**
- Both services loaded at startup
- Both services integrated with qBittorrent
- Both services integrated with MAM
- Both services save to database
- Monitoring shows activity

---

## PHASE 1 ROLLBACK PLAN

If critical issues occur:

1. Stop scheduled tasks in APScheduler
2. Revert database migrations (keep data)
3. Disable RatioEmergencyService (allow all downloads)
4. Keep MAMRulesService disabled until fixed
5. API endpoints return cached data

**Automatic Rollback:**
- If RatioEmergencyService crashes 3x: disable, alert user
- If MAMRulesService fails: use cached rules, retry at next scheduled time
- If database migration fails: abort, alert DBA

---

## PHASE 1 READY

**Prerequisites Check:**
- [ ] FastAPI backend running (port 9000)
- [ ] Database initialized
- [ ] qBittorrent accessible
- [ ] MAM credentials valid
- [ ] APScheduler working

**Go/No-Go Decision:**
- Awaiting approval to begin Phase 1

---

**Phase 1 Estimated Completion:** Day 5
**Phase 2 Start:** Day 6

