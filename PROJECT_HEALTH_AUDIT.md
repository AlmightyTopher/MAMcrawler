# 🏥 Project Health Audit: MAMcrawler (Unified)
**Date:** 2025-12-15
**Auditor:** Antigravity Agent
**Status:** 🟡 **YELLOW (Security Hardened but Network Blocked)**

## 1. Executive Summary
The project has made significant progress in **Security Hardening** (resolved hardcoded secrets, added rate limiting). However, a critical **Network Architecture** blocker remains: the WireGuard "Split Tunnel" correctly assigned an IP but failed to route traffic exclusively, leading to both Python and System using the same interface in tests.

**Recent Wins:**
*   ✅ **Security:** Hardcoded secrets removed from `qbittorrent_resilient.py`.
*   ✅ **Protection:** Rate limiting added to public and admin routes.
*   ✅ **Infrastructure:** `beads` CLI fully integrated for issue tracking.

**Critical Blocker:**
*   ❌ **VPN Routing:** `verify_wireguard.py` confirms Python picks up the VPN IP, but so does the System (no split tunneling).

## 2. Completion Matrix

| Component | Status | Utilization | Notes |
| :--- | :--- | :--- | :--- |
| **Backend API** | 🟢 95% | 🟢 50% | Security hardened. Rate limits active. |
| **Dashboard UI** | 🟢 85% | 🟢 100% | Fully wired. |
| **Network/VPN** | 🔴 40% | 🔴 0% | Service runs, but split tunneling failed verification. |
| **MAM Crawler** | 🟢 95% | 🟢 100% | Logic ported to `MAMSeleniumService`. |
| **Library Scan** | 🟢 90% | 🟢 100% | Logic ported to `DiscoveryService`. |
| **Hardcover Sync** | 🟡 80% | 🔴 0% | Code exists but is **orphaned**. |
| **Database** | 🟢 80% | 🔴 5% | Postgres configured but active services ignore it. |

## 3. Critical Risks ("Plot Holes")

### 🚨 Plot Hole #1: The VPN Kill Switch
*   **Issue:** `verify_wireguard.py` shows Python and Windows sharing the same IP (`159.26.103.209`).
*   **Risk:** This defeats the purpose of the "Dual Scraper" (one on VPN, one off). If the VPN catches all traffic, we can't scrape "human-like" from a home IP simultaneously.
*   **Fix:** Requires advanced Windows Routing Table configuration or generic "All Traffic" VPN use (simpler but loses dual-home benefit).

### 🚨 Plot Hole #2: The Data Silo Trap
*   **Issue:** The `DiscoveryService` finds books and writes to memory/logs, and reads `audiobooks_to_download.json`. It *ignores* the `books` table in Postgres.
*   **Risk:** The Dashboard shows "0 Downloads" or "0 Books" in the stats panel because the API reads from Postgres, but the Worker writes to files.
*   **Fix:** Refactor services to use SQLAlchemy models (`Book`, `Download`) for all state.

### 🚨 Plot Hole #3: Orphaned Metadata Sync
*   **Issue:** The high-value "Hardcover Sync" logic (`audiobookshelf_hardcover_sync.py`) is completely disconnected.
*   **Risk:** Manual execution required.
*   **Fix:** Create a wrapper service and wire it to the "Sync Metadata" button.

## 4. The "Lost" Features
1.  **VPN/WireGuard Binding**: Addressed but currently failing verification.
2.  **Gap Analysis**: `GapAnalysis` module exists but isn't wired to UI.

## 5. Strategic Roadmap (To 100%)

### Phase 3: Database Unification (Priority: HIGH) - **COMPLETED**
- [x] **Migrate JSON to Postgres**: `audiobooks_to_download.json` migrated to `downloads` table.
- [x] **Refactor Services**: `DiscoveryService` and `MAMSeleniumService` now use Postgres.
- [x] **Eliminate SQLite**: `AudiobookshelfHardcoverSync` ported to Postgres `HardcoverSyncLog`.
- [x] **Unified Stats**: Dashboard and System routes query Postgres.
- [ ] **Delete Legacy Files**: (Clean up `.bak` files when confident).

### Phase 4: Feature Integration (Current Focus)
- [x] **Wire Hardcover Sync:** `AudiobookshelfHardcoverSync` connected to Dashboard `/actions/refresh-metadata`.
- [x] **Wire Goodreads Sync:** `GoodreadsService` ported and connected to `/actions/sync-goodreads`.
- [x] **Prowlarr Integration:** `CuratedListService` created for "Top 10 Fantasy", wired to Dashboard.
- [ ] **Frontend Polish:** Ensure Dashboard buttons provide good feedback.

### Phase 5: Hardening
- [ ] **Persist Logs:** Move logging to DB.
- [ ] **VPN Check:** Add a startup check for VPN IP before crawling.

## Recommendation
**Proceed immediately to Phase 3.** The system is working, but it's "hollow" until the data flows into the Database.
