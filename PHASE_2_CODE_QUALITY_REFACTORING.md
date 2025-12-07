# Phase 2: Code Quality Refactoring - Implementation Plan

**Date Created:** 2025-12-01
**Status:** PLANNED
**Priority:** HIGH
**Estimated Duration:** 2-3 weeks (modular, can be done incrementally)

---

## Overview

Phase 2 focuses on refactoring the codebase for maintainability, testability, and extensibility. Three major monolithic files will be split into focused, domain-specific modules. Common patterns will be extracted into reusable components.

**Key Objectives:**
1. Reduce monolithic files from 4,257 LOC to ~1,500 LOC average
2. Increase code reusability through pattern extraction
3. Improve testability through isolated modules
4. Establish clear architectural boundaries
5. Reduce cyclomatic complexity

---

## Phase 2 Scope

### In Scope
- ✓ Refactoring 3 monolithic files (abs_client, qbittorrent_client, ratio_emergency_service)
- ✓ Extracting 5 reusable patterns
- ✓ Updating all imports in dependent code
- ✓ Writing unit tests for refactored modules
- ✓ Integration testing to verify functionality

### Out of Scope
- Database schema changes
- API contract changes
- Performance optimization (Phase 3)
- Documentation updates (separate task)

---

## Detailed Refactoring Roadmap

### PART 1: Extract Base Patterns (Foundation)

#### Task 1.1: Create Authenticated Client Base Pattern
**File:** `backend/integrations/patterns/authenticated_client.py`
**LOC:** ~150 lines
**Deliverables:**
- `AuthenticatedAsyncClient` base class
- Retry decorator with exponential backoff
- Session management (aenter/aexit)
- Re-authentication on 403 errors
- Request wrapper with error handling

**Dependencies:**
- tenacity
- aiohttp
- logging

**Tests:**
- test_base_client_session_management
- test_base_client_retry_logic
- test_base_client_auth_expiry_handling

---

#### Task 1.2: Create Pagination Pattern
**File:** `backend/integrations/patterns/pagination.py`
**LOC:** ~80 lines
**Deliverables:**
- `PaginatedAsyncClient` mixin
- Generic `paginate()` method
- Configurable offset/limit handling
- Total count tracking

**Dependencies:**
- Inherits from AuthenticatedAsyncClient

**Tests:**
- test_pagination_single_page
- test_pagination_multiple_pages
- test_pagination_empty_results

---

#### Task 1.3: Create Batch Operations Pattern
**File:** `backend/integrations/patterns/batch_operations.py`
**LOC:** ~100 lines
**Deliverables:**
- `BatchOperationsMixin` class
- Generic batch wrapper
- Error aggregation
- Partial success handling

**Dependencies:**
- Standard library only

**Tests:**
- test_batch_all_success
- test_batch_partial_failure
- test_batch_all_failure

---

#### Task 1.4: Create Metadata Transformation Pattern
**File:** `backend/integrations/patterns/metadata_mapper.py`
**LOC:** ~120 lines
**Deliverables:**
- `MetadataMapper` base class
- Field transformation rules
- Validation hooks
- Extensible architecture

**Dependencies:**
- Standard library only

**Tests:**
- test_metadata_simple_mapping
- test_metadata_nested_mapping
- test_metadata_validation_rules

---

### PART 2: Refactor abs_client.py (2,117 LOC → ~400-450 avg)

#### Task 2.1: Create Directory Structure
```
backend/integrations/abs/
├── __init__.py              (50 lines - unified exports)
├── client.py                (200 lines - core HTTP, session mgmt)
├── library.py               (300 lines - CRUD + search)
├── collections.py           (200 lines - collection operations)
├── playlists.py             (250 lines - playlist operations)
├── progress.py              (200 lines - bookmarks, listening stats)
├── user.py                  (150 lines - profile, settings, permissions)
├── admin.py                 (250 lines - backups, RSS, API keys, notifications)
├── exceptions.py            (20 lines - AudiobookshelfError)
└── metadata_transformer.py  (80 lines - field mapping)
```

**Total: 1,700 LOC (20% reduction)**

---

#### Task 2.2: Extract Core Client
**File:** `backend/integrations/abs/client.py`
**Current Code:** Lines 1-100 (constructor, session, _request)
**Deliverables:**
- Inherit from `AuthenticatedAsyncClient`
- Move constructor to retain API compatibility
- Keep `_request()` override if needed
- Expose public interface

**Tests:**
- test_abs_client_initialization
- test_abs_client_session_management
- test_abs_client_authentication

---

#### Task 2.3: Extract Library Operations
**File:** `backend/integrations/abs/library.py`
**Current Code:** Lines 150-500 (get_library_items, get_book_by_id, etc.)
**Deliverables:**
- `LibraryClient` class (or mixin to main client)
- All book/item CRUD operations
- Search functionality
- Import/export operations
- Inherit pagination pattern

**Methods:**
- get_library_items() ← uses pagination pattern
- get_book_by_id()
- import_book()
- update_book_metadata()
- search_books()
- get_libraries()
- delete_book()
- scan_library()

**Tests:**
- test_get_library_items_pagination
- test_import_book_success
- test_update_book_metadata
- test_search_books
- test_delete_book

---

#### Task 2.4: Extract Collections Operations
**File:** `backend/integrations/abs/collections.py`
**Current Code:** Lines 550-750
**Deliverables:**
- `CollectionsClient` class (or mixin)
- All collection CRUD operations
- Batch add/remove operations
- Inherit batch operations pattern

**Methods:**
- create_collection()
- get_collections()
- get_collection()
- update_collection()
- delete_collection()
- add_book_to_collection() ← single op
- remove_book_from_collection() ← single op
- batch_add_to_collection() ← uses batch pattern
- batch_remove_from_collection() ← uses batch pattern

**Tests:**
- test_create_collection
- test_update_collection
- test_batch_add_to_collection
- test_batch_remove_from_collection

---

#### Task 2.5: Extract Playlists Operations
**File:** `backend/integrations/abs/playlists.py`
**Current Code:** Lines 800-1000
**Deliverables:**
- `PlaylistsClient` class (or mixin)
- All playlist CRUD operations
- Batch add/remove operations
- create_playlist_from_collection utility

**Methods:**
- create_playlist()
- get_playlists()
- get_playlist()
- update_playlist()
- delete_playlist()
- add_item_to_playlist()
- remove_item_from_playlist()
- batch_add_to_playlist()
- batch_remove_from_playlist()
- create_playlist_from_collection()

**Tests:**
- test_create_playlist
- test_create_playlist_from_collection
- test_batch_add_to_playlist

---

#### Task 2.6: Extract Progress/Bookmarks Operations
**File:** `backend/integrations/abs/progress.py`
**Current Code:** Lines 1100-1300
**Deliverables:**
- `ProgressClient` class (or mixin)
- Media progress tracking
- Bookmark management
- Listening statistics

**Methods:**
- get_media_progress()
- update_media_progress()
- batch_update_progress()
- remove_media_progress()
- create_bookmark()
- update_bookmark()
- remove_bookmark()
- get_listening_sessions()
- get_listening_stats()

**Tests:**
- test_update_media_progress
- test_create_bookmark
- test_get_listening_stats

---

#### Task 2.7: Extract User Profile Operations
**File:** `backend/integrations/abs/user.py`
**Current Code:** Lines 1350-1500
**Deliverables:**
- `UserClient` class (or mixin)
- User profile and settings management
- Password management
- User statistics

**Methods:**
- get_user_profile()
- update_user_profile()
- get_user_settings()
- update_user_settings()
- get_user_stats()
- get_user_permissions()
- change_password()

**Tests:**
- test_get_user_profile
- test_update_user_settings
- test_change_password

---

#### Task 2.8: Extract Admin Operations
**File:** `backend/integrations/abs/admin.py`
**Current Code:** Lines 1600-2000
**Deliverables:**
- `AdminClient` class (or mixin)
- Backup management
- RSS feed management
- API key management
- Notification configuration
- Email configuration

**Methods:**
- Backup: create_backup, get_backups, get_backup, update_backup, delete_backup, run_backup
- RSS: create_rss_feed, get_rss_feeds, update_rss_feed, delete_rss_feed
- Notifications: 8 notification methods
- API Keys: 4 API key methods
- Email: 3 email methods

**Tests:**
- test_create_backup
- test_rss_feed_operations
- test_api_key_management

---

#### Task 2.9: Extract Metadata Transformer
**File:** `backend/integrations/abs/metadata_transformer.py`
**Current Code:** Extracted from update_book_metadata()
**Deliverables:**
- Field name mapping logic
- Value transformation rules
- Validation
- Extensible for future fields

**Tests:**
- test_metadata_field_mapping
- test_metadata_transformation

---

#### Task 2.10: Create Unified __init__.py
**File:** `backend/integrations/abs/__init__.py`
**Deliverables:**
- Main `AudiobookshelfClient` that composes all mixins
- Backward-compatible exports
- Clean public API

```python
from .client import AudiobookshelfClient
from .exceptions import AudiobookshelfError

__all__ = ["AudiobookshelfClient", "AudiobookshelfError"]
```

---

### PART 3: Refactor qbittorrent_client.py (1,333 LOC → ~300-350 avg)

#### Task 3.1: Create Directory Structure
```
backend/integrations/qbittorrent/
├── __init__.py              (40 lines - unified exports)
├── client.py                (150 lines - core HTTP, session mgmt)
├── auth.py                  (120 lines - SID handling, login/logout)
├── torrents.py              (200 lines - add, status, list, pause, resume, delete)
├── config.py                (100 lines - categories, preferences, paths)
├── rss.py                   (180 lines - feeds, rules, items, articles)
├── bandwidth.py             (150 lines - speed limits, alternative modes)
├── exceptions.py            (25 lines - QBittorrentError, QBittorrentAuthError)
```

**Total: 965 LOC (28% reduction)**

---

#### Task 3.2: Extract Authentication Module
**File:** `backend/integrations/qbittorrent/auth.py`
**Current Code:** SID extraction/injection logic
**Deliverables:**
- SameSite=Strict cookie handling
- Manual SID extraction from response
- SID injection into subsequent requests
- Login/logout operations
- `QBittorrentAuthError` exception

**Methods:**
- _extract_sid()
- _inject_sid()
- _login()
- _logout()

**Tests:**
- test_sid_extraction
- test_sid_injection
- test_login_success
- test_auth_failure

---

#### Task 3.3: Extract Torrent Operations
**File:** `backend/integrations/qbittorrent/torrents.py`
**Current Code:** Torrent queue management
**Deliverables:**
- All torrent CRUD operations
- State filtering
- Category management

**Methods:**
- add_torrent()
- get_torrent_status()
- get_all_torrents()
- pause_torrent()
- resume_torrent()
- delete_torrent()

**Tests:**
- test_add_torrent_magnet
- test_get_torrents_filtered
- test_pause_resume_torrent

---

#### Task 3.4: Extract Configuration Module
**File:** `backend/integrations/qbittorrent/config.py`
**Current Code:** Settings and preferences
**Deliverables:**
- Path management
- Category management
- Server state queries
- Preferences management

**Methods:**
- get_download_path()
- get_server_state()
- set_category()
- get_categories()
- get_preferences()

**Tests:**
- test_get_download_path
- test_category_operations
- test_server_state

---

#### Task 3.5: Extract RSS Module
**File:** `backend/integrations/qbittorrent/rss.py`
**Current Code:** RSS feed and rule management
**Deliverables:**
- RSS feed management
- RSS rule management
- Article management
- Status queries

**Methods:**
- add_rss_feed()
- get_rss_items()
- remove_rss_item()
- move_rss_item()
- refresh_rss_item()
- set_rss_rule()
- get_rss_rules()
- remove_rss_rule()
- get_rss_matching_articles()
- mark_rss_article_as_read()
- create_rss_folder()
- get_rss_feeds_status()

**Tests:**
- test_add_rss_feed
- test_rss_rule_management
- test_article_operations

---

#### Task 3.6: Extract Bandwidth Module
**File:** `backend/integrations/qbittorrent/bandwidth.py`
**Current Code:** Speed limit management
**Deliverables:**
- Global bandwidth limits
- Torrent-specific limits
- Alternative speed modes
- Usage statistics

**Methods:**
- set_global_download_limit()
- get_global_download_limit()
- set_global_upload_limit()
- get_global_upload_limit()
- set_torrent_download_limit()
- get_torrent_download_limit()
- set_torrent_upload_limit()
- get_torrent_upload_limit()
- set_alternative_speed_limits_mode()
- set_alternative_speed_limits()
- get_alternative_speed_limits()
- get_bandwidth_usage_stats()

**Tests:**
- test_global_bandwidth_limits
- test_torrent_bandwidth_limits
- test_alternative_speed_modes
- test_bandwidth_stats

---

#### Task 3.7: Create Unified __init__.py
**File:** `backend/integrations/qbittorrent/__init__.py`
**Deliverables:**
- Main `QBittorrentClient` that composes all modules
- Backward-compatible exports
- Clean public API

---

### PART 4: Refactor ratio_emergency_service.py (807 LOC → ~150-200 avg)

#### Task 4.1: Create Directory Structure
```
backend/services/ratio_emergency/
├── __init__.py              (30 lines - unified exports)
├── service.py               (200 lines - main orchestration)
├── monitor.py               (150 lines - ratio fetching, parsing)
├── emergency.py             (200 lines - activate/deactivate logic)
├── control.py               (100 lines - torrent/download control)
├── metrics.py               (100 lines - analytics, recovery estimates)
├── persistence.py           (80 lines - DB logging)
└── constants.py             (30 lines - configuration)
```

**Total: 890 LOC (10% increase due to extracted constants, acceptable for clarity)**

---

#### Task 4.2: Extract Constants
**File:** `backend/services/ratio_emergency/constants.py`
**Deliverables:**
- RATIO_FLOOR = 1.00
- RATIO_RECOVERY = 1.05
- RATIO_CHECK_INTERVAL = 300
- EMERGENCY_ALERT_THRESHOLD = 0.95

**Tests:**
- test_constants_loaded

---

#### Task 4.3: Extract Monitor Module
**File:** `backend/services/ratio_emergency/monitor.py`
**Deliverables:**
- MAM ratio fetching
- HTML parsing
- Authentication handling
- Current ratio tracking

**Methods:**
- _fetch_current_ratio()
- _extract_ratio()
- _ensure_authenticated()
- get_current_ratio()

**Tests:**
- test_fetch_ratio_success
- test_extract_ratio_from_html
- test_auth_handling

---

#### Task 4.4: Extract Emergency Module
**File:** `backend/services/ratio_emergency/emergency.py`
**Deliverables:**
- Emergency activation workflow
- Emergency deactivation workflow
- State management (emergency_active, triggered_at)

**Methods:**
- handle_ratio_emergency()
- _deactivate_emergency_freeze()
- get_emergency_status()
- is_emergency_active()

**Tests:**
- test_activate_emergency
- test_deactivate_emergency
- test_emergency_state_transitions

---

#### Task 4.5: Extract Control Module
**File:** `backend/services/ratio_emergency/control.py`
**Deliverables:**
- Download blocking logic
- Torrent pause/resume logic (placeholder for real implementation)

**Methods:**
- block_paid_download()
- _activate_paid_download_block()
- _pause_non_seeding_torrents()
- _unpause_all_seeding()

**Tests:**
- test_block_paid_downloads
- test_pause_torrents (mocked)
- test_unpause_torrents (mocked)

---

#### Task 4.6: Extract Metrics Module
**File:** `backend/services/ratio_emergency/metrics.py`
**Deliverables:**
- Emergency event analytics
- Recovery time estimation
- Points generation tracking

**Methods:**
- get_emergency_metrics()
- calculate_recovery_time()
- track_point_generation()

**Tests:**
- test_emergency_metrics_calculation
- test_recovery_time_estimate
- test_point_tracking

---

#### Task 4.7: Extract Persistence Module
**File:** `backend/services/ratio_emergency/persistence.py`
**Deliverables:**
- Task table logging
- RatioLog table updates
- Centralized DB operations

**Methods:**
- _log_emergency_event()
- _log_emergency_deactivation()
- _log_to_ratio_log()

**Tests:**
- test_emergency_event_logging
- test_ratio_log_persistence

---

#### Task 4.8: Create Unified Service Orchestrator
**File:** `backend/services/ratio_emergency/service.py`
**Deliverables:**
- Main `RatioEmergencyService` class
- Orchestrates monitor, emergency, control, metrics
- Public interface for check_ratio_status()

**Methods:**
- check_ratio_status() (main entry point)
- Internal orchestration logic

**Tests:**
- test_full_ratio_check_workflow

---

#### Task 4.9: Create Unified __init__.py
**File:** `backend/services/ratio_emergency/__init__.py`
**Deliverables:**
- Export `RatioEmergencyService`
- Backward-compatible API

---

### PART 5: Import Updates

#### Task 5.1: Update abs_client Imports
**Files to Update:**
- `backend/integrations/__init__.py` - update import
- Any files importing from `abs_client` directly
- All workflow files using AudiobookshelfClient

**Search Pattern:** `from backend.integrations.abs_client import`

---

#### Task 5.2: Update qbittorrent_client Imports
**Files to Update:**
- `backend/integrations/__init__.py` - update import
- Any files importing directly
- Workflow files using QBittorrentClient

**Search Pattern:** `from backend.integrations.qbittorrent_client import`

---

#### Task 5.3: Update ratio_emergency_service Imports
**Files to Update:**
- `backend/services/__init__.py` - update import
- Workflow files using RatioEmergencyService

**Search Pattern:** `from backend.services.ratio_emergency_service import`

---

### PART 6: Testing

#### Task 6.1: Write Unit Tests for Pattern Modules
**Tests:** ~200 lines
**Coverage:** All pattern classes and methods

---

#### Task 6.2: Write Unit Tests for abs_client Refactoring
**Tests:** ~400 lines
**Modules:** client, library, collections, playlists, progress, user, admin
**Coverage:** All public methods

---

#### Task 6.3: Write Unit Tests for qbittorrent_client Refactoring
**Tests:** ~300 lines
**Modules:** auth, torrents, config, rss, bandwidth
**Coverage:** All public methods

---

#### Task 6.4: Write Unit Tests for ratio_emergency_service Refactoring
**Tests:** ~200 lines
**Modules:** monitor, emergency, control, metrics, persistence
**Coverage:** Key workflows

---

#### Task 6.5: Integration Testing
**Verification:**
- All imports resolve correctly
- No circular dependencies
- Backward compatibility maintained
- All existing functionality preserved

---

## Implementation Sequence

### Week 1: Foundation (Patterns)
```
Day 1-2: Create authenticated_client base pattern
Day 3-4: Create pagination, batch_operations, metadata_mapper
Day 5:   Write tests for patterns
```

### Week 2: Refactor Large Clients
```
Day 1-2: Refactor abs_client (split into 8 modules)
Day 3:   Refactor qbittorrent_client (split into 5 modules)
Day 4-5: Write unit tests and verify imports
```

### Week 3: Service Refactoring & Integration
```
Day 1-2: Refactor ratio_emergency_service (split into 8 modules)
Day 3:   Update all imports in dependent code
Day 4:   Integration testing and verification
Day 5:   Final validation and documentation
```

---

## Success Criteria

✓ All 3 monolithic files successfully refactored
✓ All monolithic files reduced to <450 LOC each
✓ 5 reusable pattern modules created
✓ 100% test pass rate for all new modules
✓ No circular dependencies
✓ Backward compatibility maintained
✓ All imports updated and working
✓ No functionality loss

---

## Risks and Mitigation

### Risk: Circular Dependencies
**Mitigation:**
- Use dependency injection
- Clear module boundaries
- No cross-imports between sibling modules

### Risk: Breaking Changes
**Mitigation:**
- Maintain backward-compatible __init__.py exports
- Keep public interface unchanged
- Test all workflows end-to-end

### Risk: Test Coverage Gaps
**Mitigation:**
- Write tests alongside refactoring
- Use code coverage tools
- Test real API interactions (mocked)

### Risk: Import Chain Issues
**Mitigation:**
- Systematically update all imports
- Use find/replace carefully
- Test imports after each change

---

## Files to Create

**Pattern Modules:**
- backend/integrations/patterns/authenticated_client.py
- backend/integrations/patterns/pagination.py
- backend/integrations/patterns/batch_operations.py
- backend/integrations/patterns/metadata_mapper.py

**Refactored abs_client:**
- backend/integrations/abs/__init__.py
- backend/integrations/abs/client.py
- backend/integrations/abs/library.py
- backend/integrations/abs/collections.py
- backend/integrations/abs/playlists.py
- backend/integrations/abs/progress.py
- backend/integrations/abs/user.py
- backend/integrations/abs/admin.py
- backend/integrations/abs/metadata_transformer.py
- backend/integrations/abs/exceptions.py

**Refactored qbittorrent_client:**
- backend/integrations/qbittorrent/__init__.py
- backend/integrations/qbittorrent/client.py
- backend/integrations/qbittorrent/auth.py
- backend/integrations/qbittorrent/torrents.py
- backend/integrations/qbittorrent/config.py
- backend/integrations/qbittorrent/rss.py
- backend/integrations/qbittorrent/bandwidth.py
- backend/integrations/qbittorrent/exceptions.py

**Refactored ratio_emergency_service:**
- backend/services/ratio_emergency/__init__.py
- backend/services/ratio_emergency/service.py
- backend/services/ratio_emergency/monitor.py
- backend/services/ratio_emergency/emergency.py
- backend/services/ratio_emergency/control.py
- backend/services/ratio_emergency/metrics.py
- backend/services/ratio_emergency/persistence.py
- backend/services/ratio_emergency/constants.py

**Test Files:**
- backend/tests/patterns/test_authenticated_client.py
- backend/tests/patterns/test_pagination.py
- backend/tests/patterns/test_batch_operations.py
- backend/tests/integrations/test_abs_client_refactored.py
- backend/tests/integrations/test_qbittorrent_client_refactored.py
- backend/tests/services/test_ratio_emergency_service_refactored.py

---

## Files to Delete

After successful refactoring and testing:
- backend/integrations/abs_client.py (archive to archive/ folder)
- backend/integrations/qbittorrent_client.py (archive)
- backend/services/ratio_emergency_service.py (archive)

---

## Metrics

### Code Quality Improvements

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Max Module LOC | 2,117 | 450 | <500 |
| Avg Module LOC | 1,419 | 300 | <350 |
| Cyclomatic Complexity | High | Low | <10 per method |
| Test Coverage | Partial | >90% | >85% |
| Circular Dependencies | Possible | None | 0 |

### File Statistics

| File | Current | After | Reduction |
|------|---------|-------|-----------|
| abs_client.py | 2,117 | 8 x 150-300 | 76% |
| qbittorrent_client.py | 1,333 | 5 x 150-300 | 70% |
| ratio_emergency_service.py | 807 | 8 x 80-200 | 10% (for clarity) |
| **Total** | **4,257** | **~2,200** | **48%** |

---

## Documentation

After Phase 2 completion:
- [ ] Update API documentation with new module structure
- [ ] Create architecture diagram showing module relationships
- [ ] Document each pattern with usage examples
- [ ] Update CLAUDE.md with refactored file locations
- [ ] Create module interdependency diagram

---

## Approval & Sign-off

**Ready for Implementation:** YES
**Estimated Start Date:** 2025-12-01
**Estimated Completion Date:** 2025-12-21 (3 weeks)

---

**Phase 2 Plan Created:** 2025-12-01
**Status:** READY FOR IMPLEMENTATION
