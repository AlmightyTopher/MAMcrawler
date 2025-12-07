# PHASE 3 STEP 1: QBittorrentMonitorService Refactoring Plan

**Status:** PLANNING
**Target:** Decompose 437 LOC monolithic service into 4 focused managers
**Estimated Duration:** 1-2 days
**Complexity:** Small-Medium

---

## Current State Analysis

**File:** `backend/services/qbittorrent_monitor_service.py`
**LOC:** 437 total
**Methods:** 10

### Methods Breakdown by Responsibility

| Method | LOC | Category | Responsibility |
|--------|-----|----------|---|
| `__init__()` | 8 | Initialization | Initialize state |
| `initialize_qbittorrent()` | 11 | Setup | Create qBittorrent client |
| `get_torrent_states()` | 64 | **STATE MANAGEMENT** | Fetch and categorize torrents |
| `auto_restart_stalled_torrents()` | 29 | **TORRENT CONTROL** | Restart stalled torrents |
| `optimize_seeding_allocation()` | 46 | **RATIO MONITORING** | Optimize seeding slots |
| `calculate_point_generation()` | 42 | **RATIO MONITORING** | Estimate point generation |
| `continuous_monitoring_loop()` | 51 | Orchestration | Main monitoring loop |
| `get_monitoring_status()` | 9 | Status | Return current status |
| `detect_completion_events()` | 57 | **COMPLETION EVENTS** | Detect torrent completions |
| `handle_completion_events()` | 67 | **COMPLETION EVENTS** | Handle completion triggers |

---

## Proposed Manager Decomposition

### Manager 1: TorrentStateManager (64 LOC)
**Responsibility:** Fetch torrents and categorize by state

**Methods:**
- `get_torrent_states()` - Categorize all torrents into states (downloading, seeding, stalled, paused, errored)
- `update_state_cache()` - Update internal state tracking

**Used by:** All other managers + main service

**Benefits:**
- Single source of truth for torrent states
- Easy to test in isolation
- Reusable by other services

---

### Manager 2: TorrentControlManager (29 LOC)
**Responsibility:** Control torrent operations (pause, resume, restart)

**Methods:**
- `auto_restart_stalled_torrents()` - Force-continue stalled torrents
- `restart_torrent()` - Restart individual torrent
- `pause_downloading_torrents()` - Pause non-seeding torrents

**Used by:** RatioEmergencyService, scheduling

**Benefits:**
- Centralized torrent control
- Consistent error handling
- Easy to extend with new control operations

---

### Manager 3: RatioMonitoringManager (88 LOC)
**Responsibility:** Monitor ratio and optimize seeding efficiency

**Methods:**
- `optimize_seeding_allocation()` - Calculate optimal seeding/downloading ratio
- `calculate_point_generation()` - Estimate points from upload
- `get_efficiency_metrics()` - Calculate upload efficiency (new)
- `analyze_seeding_strategy()` - Recommend optimization (new)

**Used by:** Scheduler, monitoring dashboard, optimization service

**Benefits:**
- Focused on efficiency metrics
- Can be queried independently
- Forms basis for optimization recommendations

---

### Manager 4: CompletionEventManager (124 LOC)
**Responsibility:** Detect and handle torrent completion events

**Methods:**
- `detect_completion_events()` - Compare states, identify completions
- `handle_completion_events()` - Process completion triggers
- `on_torrent_completed()` - Single torrent completion handler (new)
- `get_completion_history()` - Query recent completions (new)

**Used by:** Main monitoring loop, event bus

**Benefits:**
- Isolated event handling
- Can be extended for other event types
- Database integration centralized here

---

## Integration Architecture

```
QBittorrentMonitorService (Coordinator)
├── TorrentStateManager
│   └── Uses: QBittorrentClient.get_all_torrents()
├── TorrentControlManager
│   ├── Uses: QBittorrentClient.pause_torrent(), resume_torrent(), force_continue()
│   └── Uses: TorrentStateManager
├── RatioMonitoringManager
│   ├── Uses: TorrentStateManager
│   └── Uses: Database for ratio logs
└── CompletionEventManager
    ├── Uses: TorrentStateManager
    ├── Uses: QBittorrentClient.get_all_torrents()
    └── Uses: Database (Download, DownloadService)

Main Loop (continuous_monitoring_loop):
1. Get states via TorrentStateManager
2. Restart stalled via TorrentControlManager
3. Optimize seeding via RatioMonitoringManager
4. Detect completions via CompletionEventManager
5. Handle completions via CompletionEventManager
6. Log results
```

---

## Implementation Steps

### STEP 1.1: Create TorrentStateManager
**File:** `backend/services/qbittorrent_managers/torrent_state_manager.py`

**Extracted Code:**
- `get_torrent_states()` method
- State categorization logic
- State caching mechanism

**Tests:** 5-6 tests covering:
- Torrent state categorization
- Error handling
- State transitions

---

### STEP 1.2: Create TorrentControlManager
**File:** `backend/services/qbittorrent_managers/torrent_control_manager.py`

**Extracted Code:**
- `auto_restart_stalled_torrents()` method
- Individual torrent restart logic
- Error recovery per torrent

**Tests:** 4-5 tests covering:
- Restart operations
- Individual torrent failures
- State filtering

---

### STEP 1.3: Create RatioMonitoringManager
**File:** `backend/services/qbittorrent_managers/ratio_monitoring_manager.py`

**Extracted Code:**
- `optimize_seeding_allocation()` method
- `calculate_point_generation()` method
- New efficiency analysis methods

**Tests:** 6-7 tests covering:
- Seeding optimization calculations
- Point generation estimation
- Edge cases (no torrents, no upload, etc.)

---

### STEP 1.4: Create CompletionEventManager
**File:** `backend/services/qbittorrent_managers/completion_event_manager.py`

**Extracted Code:**
- `detect_completion_events()` method
- `handle_completion_events()` method
- State transition tracking

**Tests:** 6-7 tests covering:
- Completion detection
- Event handling success/failure
- Database integration
- Error recovery

---

### STEP 1.5: Integrate into QBittorrentMonitorService
**File:** `backend/services/qbittorrent_monitor_service.py` (modified)

**Changes:**
- Import all 4 managers
- Initialize managers in `__init__()`
- Update `continuous_monitoring_loop()` to use managers
- Keep public API identical (backwards compatible)
- Remove original implementation methods

**Code:**
```python
def __init__(self):
    self.qb_client = None
    self.monitoring_active = False
    self.state_manager = TorrentStateManager(self)
    self.control_manager = TorrentControlManager(self)
    self.ratio_manager = RatioMonitoringManager(self)
    self.completion_manager = CompletionEventManager(self)
```

---

### STEP 1.6: Comprehensive Testing
**File:** `backend/tests/test_qbittorrent_monitor_service.py`

**Test Coverage:**
- TorrentStateManager: 6 tests
- TorrentControlManager: 5 tests
- RatioMonitoringManager: 7 tests
- CompletionEventManager: 7 tests
- Integration tests: 3 tests
- Backwards compatibility: 2 tests

**Total:** 30 comprehensive tests

---

## File Structure After Refactoring

```
backend/services/
├── qbittorrent_monitor_service.py (coordinator, 80 LOC - reduced from 437)
└── qbittorrent_managers/
    ├── __init__.py
    ├── torrent_state_manager.py (70 LOC)
    ├── torrent_control_manager.py (40 LOC)
    ├── ratio_monitoring_manager.py (100 LOC)
    └── completion_event_manager.py (140 LOC)

backend/tests/
└── test_qbittorrent_monitor_service.py (30+ tests)
```

---

## Success Criteria

✅ All 4 managers created and integrated
✅ All 30 tests passing
✅ Zero behavior changes (backwards compatible)
✅ 100% syntax validation
✅ Reduced main service LOC from 437 to ~80
✅ Clear separation of concerns
✅ Easy to extend with new operations

---

## Dependencies & Integration Points

**Services Using QBittorrentMonitorService:**
1. `ratio_emergency_service.py` - Uses torrent control
2. `download_service.py` - Uses completion events
3. `scheduler` - Calls continuous_monitoring_loop()
4. `category_sync_service.py` - Uses torrent states

**All integration points remain unchanged** - backwards compatible wrapper maintains current interface.

---

## Risk Assessment

**Low Risk** because:
- Refactoring doesn't change behavior (only organization)
- Main API surface unchanged
- Managers are extracted, not replaced
- Clear test coverage before/after
- Can be rolled back easily

---

## Timeline Estimate

| Task | Days | Status |
|------|------|--------|
| STEP 1.1: TorrentStateManager | 0.25 | Pending |
| STEP 1.2: TorrentControlManager | 0.25 | Pending |
| STEP 1.3: RatioMonitoringManager | 0.25 | Pending |
| STEP 1.4: CompletionEventManager | 0.5 | Pending |
| STEP 1.5: Service Integration | 0.25 | Pending |
| STEP 1.6: Comprehensive Testing | 0.5 | Pending |
| **TOTAL** | **2.0 days** | Pending |

---

**Next Action:** Begin STEP 1.1 - Create TorrentStateManager
