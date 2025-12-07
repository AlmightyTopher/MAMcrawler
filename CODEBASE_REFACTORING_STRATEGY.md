# MAMcrawler Codebase Refactoring Strategy

**Objective**: Transform MAMcrawler from 1,050+ files into a lean, optimized **Best Audiobook Finder/Downloader/Organizer** system

**Status**: In Progress
**Last Updated**: November 29, 2025

---

## EXECUTIVE SUMMARY

### Current State
- **Total Files**: 1,050+
- **Core Python**: 377 files
- **Documentation**: 264 files (many redundant)
- **Data/Generated**: 62+ JSON, 44+ TXT files
- **Code Duplication**: 40+ duplicate/variant scripts

### Target State
- **Total Files**: ~250-300
- **Core Python**: 150-180 files (focused, no duplication)
- **Documentation**: 30-40 master guides
- **Data/Generated**: Organized in `/outputs` and `/reports`
- **Zero code duplication**

### Impact
- **Reduction**: 65-75% fewer files
- **Maintainability**: 80% easier to navigate
- **Clarity**: Single source of truth for each feature
- **Performance**: Faster repo operations (clone, search, etc.)

---

## PHASE 1: DUPLICATE CONSOLIDATION

### A. Author Search (4 variants → 2 files)

**Current Files** (consolidate):
1. `author_complete_search.py` - Basic version
2. `author_search_with_auth.py` - Enhanced with auth
3. `author_audiobook_search.py` - Advanced with WebDriver
4. `author_audiobook_search.py` (duplicate) - Same as above

**Action Plan**:
```
KEEP: author_search_with_auth.py (recommended version)
KEEP: author_audiobook_search.py (advanced variant with --webdriver flag)
DELETE: author_complete_search.py (basic version, functionality in above)
DELETE: Duplicate audiobook_search variant
```

**Consolidation**: Merge into single `author_search.py` with modes:
```python
# Usage:
python author_search.py "Author Name" --mode=basic      # Simple search
python author_search.py "Author Name" --mode=auth        # With authentication
python author_search.py "Author Name" --mode=webdriver   # Advanced with browser
```

---

### B. Prowlarr Search (2 versions → 1 file)

**Current Files**:
1. `search_prowlarr_curated_audiobooks.py` - v1 (legacy)
2. `search_prowlarr_curated_audiobooks_v2.py` - v2 (improvements)

**Action**:
```
DELETE: search_prowlarr_curated_audiobooks.py (v1)
KEEP: search_prowlarr_curated_audiobooks_v2.py
RENAME: → prowlarr_search.py (cleaner name)
```

---

### C. MAM Direct Search (2 versions → 1 file)

**Current Files**:
1. `mam_direct_search.py` - Original
2. `mam_direct_search_fixed.py` - Fixed version

**Action**:
```
DELETE: mam_direct_search.py (original, contains bugs)
KEEP: mam_direct_search_fixed.py
RENAME: → mam_search.py
```

---

### D. Verification Scripts (10+ → 3 files)

**Current Files** (consolidate):
1. `verify_all_metadata_post_restart.py`
2. `verify_all_uncertain_books.py`
3. `verify_implementation.py`
4. `verify_option_b.py`
5. `verify_randi_additions.py`
6. `verify_randi_darren_books.py`
7. `verify_randi_darren_correct.py`
8. `verify_randi_darren_fixed.py`
9. `verify_series_metadata.py`
10. + others

**Consolidated Approach**:
```
Create: mamcrawler/verification/verify.py (unified framework)
  - verify_metadata(library_id, mode='all')
  - verify_series(library_id, author=None)
  - verify_randi_library(library_id)
  - verify_uncertain_books(library_id)

Usage:
  python mamcrawler/verification/verify.py --library-id=123 --mode=all
  python mamcrawler/verification/verify.py --library-id=123 --mode=series
  python mamcrawler/verification/verify.py --library-id=123 --author="Author Name"

DELETE: All 10+ individual verify scripts
```

---

### E. Search Variants (10+ → 1-2 files)

**Current Files** (consolidate):
1. `search_fantasy_by_date.py`
2. `search_library_for_series.py`
3. `search_popular_audiobooks.py`
4. `search_queue_for_randi_titles.py`
5. `search_validated_corrector.py`
6. `specific_title_search.py`
7. `prowlarr_title_search.py`
8. `local_search.py`
9. + others

**Consolidated Approach**:
```
Create: mamcrawler/discovery/search.py (unified search interface)
  - search_fantasy(limit=10, sort_by='date')
  - search_series(title, author)
  - search_popular(limit=10)
  - search_local_library(query)
  - search_prowlarr(query, indexer=None)

Usage:
  python mamcrawler/discovery/search.py --fantasy --limit 20 --sort date
  python mamcrawler/discovery/search.py --series "Author Name"
  python mamcrawler/discovery/search.py --local "Book Title"

DELETE: All 10+ individual search scripts
```

---

### F. Diagnostic Scripts (10+ → 1 file)

**Current Files** (consolidate):
1. `debug_book_metadata.py`
2. `debug_fantasy_page.py`
3. `debug_magnet_link.py`
4. `debug_search.py`
5. `diagnostic_abs.py`
6. `prowlarr_diagnostic.py`
7. `mam_access_diagnosis.py`
8. `qbittorrent_mam_diagnostics.py`
9. `vpn_proxy_diagnostic.py`
10. `cloudflare_token_analysis.py`

**Consolidated Approach**:
```
Create: mamcrawler/diagnostics/health.py
  - check_goodreads_connection()
  - check_hardcover_api()
  - check_prowlarr_access()
  - check_mam_access()
  - check_qbittorrent_connection()
  - check_abs_connection()
  - check_vpn_connection()
  - full_system_diagnostic()

Usage:
  python mamcrawler/diagnostics/health.py --full
  python mamcrawler/diagnostics/health.py --service mam
  python mamcrawler/diagnostics/health.py --service qbittorrent

DELETE: All 10+ individual diagnostic scripts
```

---

### G. Sync Workflows (2 → 1 consolidated system)

**Current Files**:
1. `abs_hardcover_workflow.py` (16,057 lines) - Hardcover sync
2. `abs_goodreads_sync_workflow.py` (15,218 lines) - Goodreads sync
3. `abs_goodreads_sync_worker.py` (8,402 lines) - Worker process
4. `dual_abs_goodreads_sync_workflow.py` - Dual-worker variant

**Consolidated Approach**:
```
KEEP: Both Hardcover and Goodreads as separate modules (different APIs)
BUT: Consolidate into mamcrawler/sync/

Create: mamcrawler/sync/__init__.py
  - hardcover_sync.py (refactored from abs_hardcover_workflow.py)
  - goodreads_sync.py (refactored from abs_goodreads_sync_workflow.py)
  - sync_orchestrator.py (unified orchestration)

Usage:
  python mamcrawler/sync/hardcover_sync.py --limit 500 --auto-update
  python mamcrawler/sync/goodreads_sync.py --limit 500 --mode dual
  python mamcrawler/sync/sync_orchestrator.py --source all --limit 100

DELETE ROOT LEVEL: abs_hardcover_workflow.py, abs_goodreads_sync_workflow.py, etc.
ARCHIVE: Original 16K+ line files for reference
```

---

### H. Test Frameworks (4 → 1 unified)

**Current Files**:
1. `comprehensive_testing_framework.py`
2. `e2e_test_framework.py`
3. `end_to_end_test_suite.py`
4. `test_suite.py`
5. Plus 35+ individual test files

**Consolidated Approach**:
```
CONSOLIDATE: Merge into backend/tests/ as unified pytest framework
- Delete standalone test frameworks
- Use pytest exclusively
- Organize by module:
  backend/tests/
    - test_integrations/
    - test_api/
    - test_services/
    - test_workflows/
    - conftest.py (shared fixtures)

Usage:
  pytest backend/tests/                    # Run all tests
  pytest backend/tests/test_integrations/  # Integration tests only
  pytest backend/tests/ -v --cov           # With coverage
```

---

## PHASE 2: DEAD CODE REMOVAL

### A. Archive Legacy Crawlers (5 files)

Move to `archive/legacy_crawlers/`:
```
- improved_mam_crawler.py (18,397 lines)
- mam_crawler_secure.py (21,654 lines)
- stealth_mam_crawler.py (21,509 lines)
- stealth_mam_form_crawler.py (38,139 lines)
- automated_dual_scrape.py (4,765 lines)

Rationale: Replaced by max_stealth_crawler.py and mamcrawler/ package
```

### B. Delete Incomplete Prototypes

```
DELETE:
- check_vpn_connection.py (incomplete)
- mam_email_password_crawler.py (prototype)
- mam_requests_crawler.py (superseded)
- mam_selenium_crawler.py (superseded)
- mam_selenium_navigator.py (superseded)
- mam_selenium_navigator_fixed.py (superseded)

Rationale: Replaced by Crawl4AI in max_stealth_crawler.py
```

### C. Randi/Darren-Specific Variants

```
DELETE:
- mam_randi_darren_search.py
- mam_randi_darren_search_v2.py
- verify_randi_additions.py
- verify_randi_darren_books.py
- verify_randi_darren_correct.py
- verify_randi_darren_fixed.py

Rationale: These are single-user customizations. Functionality
  integrated into generic author_search.py and verify.py

PRESERVE: Randi Darren is example author for docs/testing
```

---

## PHASE 3: DOCUMENTATION CONSOLIDATION

### Current: 264 Files
**Problem**: Redundant guides, outdated workflows, version-specific docs

### Target: 30-40 Master Guides

**Consolidated Documentation Structure**:
```
docs/
├── README.md                          # Entry point
├── QUICK_START.md                     # 5-minute setup
├── ARCHITECTURE.md                    # System design
├── INSTALLATION.md                    # Detailed setup
├── CONFIGURATION.md                   # Config reference
├── USER_GUIDE.md                      # How to use features
├── API_REFERENCE.md                   # REST API docs
├── INTEGRATIONS.md                    # External services
│   ├── goodreads.md
│   ├── hardcover.md
│   ├── prowlarr.md
│   ├── audiobookshelf.md
│   └── qbittorrent.md
├── DEPLOYMENT.md                      # Production deployment
├── TROUBLESHOOTING.md                 # Common issues
├── DEVELOPMENT.md                     # For contributors
├── EXAMPLES.md                        # Usage examples
├── FAQ.md                             # Frequently asked questions
└── CHANGELOG.md                       # Version history
```

**DELETE**: Redundant files such as:
- HARDCOVER_INTEGRATION_GUIDE.md, HARDCOVER_INTEGRATION_STATUS.md, HARDCOVER_QUICKSTART.md → consolidate to docs/integrations/hardcover.md
- SECONDARY_QBITTORRENT_SETUP.md, SECONDARY_DEPLOYMENT_CHECKLIST.md → DEPLOYMENT.md
- Multiple "WORKFLOW_*" guides → USER_GUIDE.md
- Version-dated guides (CURRENT_SESSION_SUMMARY.txt, etc.) → CHANGELOG.md or archive

---

## PHASE 4: DATA & OUTPUT ORGANIZATION

### Current: Scattered in root directory
**Problem**: Hard to find, pollutes root directory

### Target: Organized structure
```
outputs/
├── reports/
│   ├── metadata_analysis/
│   ├── missing_books/
│   ├── library_analysis/
│   └── sync_reports/
├── data/
│   ├── library_catalog.json
│   ├── missing_books.json
│   └── audiobooks_to_download.json
├── logs/
│   ├── application.log
│   ├── errors.log
│   └── audit/
└── cache/
    ├── search_results/
    ├── metadata_cache/
    └── verification_cache/

state/
├── abs_crawler_state.json
├── stealth_crawler_state.json
└── crawler_state.json
```

**Action**: Move and create `.gitignore` to exclude generated files:
```
outputs/**
state/**
logs/**
*.sqlite
*.faiss
__pycache__/
.pytest_cache/
```

---

## PHASE 5: ROOT-LEVEL SCRIPT ORGANIZATION

### Current Structure
- 222 Python files in root directory
- No clear organization
- Hard to find entry points

### Target Structure

```
scripts/
├── discovery/
│   ├── author_search.py           # Consolidated from 4 variants
│   ├── prowlarr_search.py         # Consolidated from 2 variants
│   ├── mam_search.py              # Consolidated from 2 variants
│   └── search.py                  # Unified search interface
│
├── library/
│   ├── metadata_sync.py           # Goodreads + Hardcover unified
│   ├── series_completion.py       # Series gap detection
│   ├── verify.py                  # Unified verification (10+ scripts)
│   └── repair.py                  # Edition replacement
│
├── downloads/
│   ├── queue_manager.py           # qBittorrent management
│   ├── monitor.py                 # Download monitoring
│   └── ratio_recovery.py          # Ratio emergency procedures
│
├── diagnostics/
│   └── health.py                  # System health checks (10+ scripts)
│
├── maintenance/
│   ├── cleanup.py                 # Database cleanup
│   ├── backup.py                  # Backup procedures
│   └── statistics.py              # Library statistics
│
└── dev/
    ├── test_runner.py             # Run all tests
    ├── code_audit.py              # Code quality checks
    └── benchmark.py               # Performance testing
```

**Usage Examples**:
```bash
# Discovery
python scripts/discovery/author_search.py "Brandon Sanderson"
python scripts/discovery/mam_search.py --genre fantasy

# Library Management
python scripts/library/metadata_sync.py --source goodreads --limit 500
python scripts/library/series_completion.py --author "Patrick Rothfuss"
python scripts/library/verify.py --full

# Downloads
python scripts/downloads/queue_manager.py --status
python scripts/downloads/monitor.py --watch

# Diagnostics
python scripts/diagnostics/health.py --full

# Development
pytest scripts/dev/test_runner.py -v
python scripts/dev/code_audit.py
```

---

## PHASE 6: FEATURE INTEGRATION

### Identify Missing/Disconnected Features

**Audio Processing** (mamcrawler/audio_processing/)
- Status: Implemented but not integrated into main workflow
- Action: Create entry point in `scripts/library/audio_processing.py`

**Metadata Enrichment** (mamcrawler/metadata/)
- Status: Multiple sources available
- Action: Unify into single `metadata_enrichment.py` with strategy pattern

**RAG System** (cli.py, ingest.py, watcher.py)
- Status: Working but separate from backend
- Action: Integrate as `/api/rag/query` endpoint in FastAPI

**Series Completion** (mamcrawler/series_completion.py)
- Status: Implemented
- Action: Add API endpoint `/api/library/series/gaps`

---

## PHASE 7: NEW UTILITIES TO ADD

### Based on Missing Functionality

1. **Batch Operations** - Unified batch processing for multiple operations
2. **Progress Tracking** - Real-time progress for long-running tasks
3. **Notification System** - Email/webhook notifications on completion
4. **Conflict Resolution** - Handle duplicate metadata matches
5. **Quality Metrics** - Track metadata accuracy over time
6. **Export Utilities** - Export library in multiple formats (Calibre, CSV, etc.)

---

## CONSOLIDATION SUMMARY TABLE

| Category | Before | After | Reduction |
|----------|--------|-------|-----------|
| Author Search | 4 | 1 | 75% |
| Prowlarr Search | 2 | 1 | 50% |
| MAM Search | 2 | 1 | 50% |
| Verification | 10 | 1 | 90% |
| Search Variants | 10 | 1 | 90% |
| Diagnostics | 10 | 1 | 90% |
| Sync Workflows | 4 | 2 | 50% |
| Test Frameworks | 4 | 1 | 75% |
| Documentation | 264 | 40 | 85% |
| Root Scripts | 222 | 50 | 77% |
| **TOTAL FILES** | **1,050+** | **280-300** | **72%** |

---

## IMPLEMENTATION TIMELINE

### Week 1: Consolidation
- [ ] Consolidate duplicate scripts (Phase 1)
- [ ] Archive legacy code (Phase 2)
- [ ] Reorganize documentation (Phase 3)

### Week 2: Integration
- [ ] Create new script structure (Phase 5)
- [ ] Integrate audio processing
- [ ] Integrate RAG system with FastAPI

### Week 3: New Features
- [ ] Add utilities (Phase 7)
- [ ] Create unified entry points
- [ ] Update API documentation

### Week 4: Testing & Documentation
- [ ] Comprehensive testing
- [ ] Update all guides
- [ ] Create migration guide for existing users

---

## BEFORE & AFTER STRUCTURE

### BEFORE
```
MAMcrawler/
├── [222 root .py files - scattered]
├── author_search.py
├── author_search_with_auth.py
├── author_audiobook_search.py
├── author_audiobook_search.py (duplicate)
├── search_prowlarr_curated_audiobooks.py
├── search_prowlarr_curated_audiobooks_v2.py
├── mam_direct_search.py
├── mam_direct_search_fixed.py
├── verify_*.py [10+ variants]
├── debug_*.py [10+ variants]
├── search_*.py [10+ variants]
├── test_*.py [40+ variants]
├── [264 markdown docs - redundant]
├── backend/
├── mamcrawler/
├── archive/
├── guides_output/
└── [scattered JSON/TXT outputs]
```

### AFTER
```
MAMcrawler/
├── docs/                          [30-40 master guides]
│   ├── README.md
│   ├── QUICK_START.md
│   ├── INSTALLATION.md
│   └── ...
├── scripts/                       [50-60 organized tools]
│   ├── discovery/
│   ├── library/
│   ├── downloads/
│   ├── diagnostics/
│   ├── maintenance/
│   └── dev/
├── backend/                       [FastAPI system - unchanged]
├── mamcrawler/                    [Core package - enhanced]
├── tests/                         [Unified pytest]
├── outputs/                       [Generated reports/data]
├── state/                         [Crawler state files]
├── logs/                          [Application logs]
├── config/                        [Configuration files]
├── archive/
│   ├── legacy_crawlers/           [Old implementations]
│   └── deprecated_guides/         [Old documentation]
├── .env                           [Secrets]
├── .env.example                   [Template]
├── requirements.txt
├── setup.py
├── Makefile                       [Common commands]
└── README.md                      [Quick reference]
```

---

## SUCCESS METRICS

After consolidation:

- ✅ **File Reduction**: From 1,050+ to 280-300 (72% reduction)
- ✅ **Code Duplication**: 0 duplicate implementations
- ✅ **Navigation Time**: < 5 seconds to find any feature
- ✅ **Onboarding**: New developers can understand system in < 1 hour
- ✅ **Test Coverage**: > 90% of critical paths
- ✅ **Documentation**: Single source of truth for each feature
- ✅ **Maintainability**: Clear entry points for all operations

---

## NOTES FOR IMPLEMENTATION

1. **Backward Compatibility**: Some users may have scripts calling old file paths
   - Solution: Add deprecation notices and version bump
   - Provide migration script

2. **Data Migration**: Old JSON files must be moved to outputs/
   - Solution: Create migration script to reorganize

3. **Existing Workflows**: Users with scheduled tasks may break
   - Solution: Update cron/scheduler entries in documentation

4. **Git History**: Don't delete old files, keep as reference
   - Solution: Move to archive/ instead of deleting
   - Keep git history intact

---

**Next Step**: Execute Phase 1 consolidation (duplicate removal)

