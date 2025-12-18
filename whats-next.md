# UNIFICATION PLAN: Merging "Split Brain" Architecture

**Status:** IN PROGRESS
**Date:** 2025-12-15

## 🚨 The Issue: Split Brain
The project currently has two disconnected versions:
1.  **The Backend (`backend/`)**: Professional, architected FastAPI app (Low Utilization).
2.  **The Scripts (`execute_real_workflow_*.py`)**: Working logic, but manual and disconnected (High Utilization).
3.  **The Dashboard**: A frontend file with no server, expecting API endpoints that don't match the Backend.

## 🎯 The Goal: One Unified System
We will merge these components into a single, production-grade application where the Dashboard controls the Backend, and the Backend runs the Logic.

## 📋 Phase 1: The "Bridge" (Immediate)
*   [x] **Serve Dashboard**: Host `dashboard.html` via `backend/main.py` so it's accessible at `http://localhost:8000/`.
*   [x] **Compatibility Layer**: Create a specific API router (`backend/routes/dashboard_compat.py`) that matches exactly what the Dashboard expects (`/api/status`, `/api/actions/*`).
*   [x] **Wire Actions**: Connect the Dashboard buttons ("Top Search", "Sync Goodreads") to the actual services in `backend/services/`.
*   [x] **Cloudflare Tunnel**: Once unified, expose port 8000 via the tunnel.

## 📋 Phase 2: Logic Migration & Audit (Complete)
*   [x] **Port `MAMCrawler`**: Move logic from `execute_real_workflow_*.py` to `backend/services/mam_selenium_service.py`.
*   [x] **Port `LibraryScan`**: Move logic to `backend/services/discovery_service.py`.
*   [x] **Project Audit**: Identify "split brain" data issues and roadmap (See `PROJECT_HEALTH_AUDIT.md`).
*   [ ] **Eliminate Scripts**: Delete `execute_real_workflow_*.py` once functionality is verified in the backend.

## 📋 Phase 3: Database Unification (Completed)
**Goal:** Stop using JSON/SQLite/Text files. Make Postgres the Single Source of Truth.
*   [x] **Discovery -> Postgres**: Update `DiscoveryService` to write "wanted" books to `books` table (Via `Download` table currently).
*   [x] **Crawler -> Postgres**: Update `MAMSeleniumService` to read "wanted" books from DB and write "downloaded" status.
*   [x] **Metadata -> Postgres**: Refactor `AudiobookshelfHardcoverSync` to use Postgres instead of SQLite.
*   [ ] **Logs -> Postgres**: Create `SystemLog` table and API endpoint for dashboard logs (Moved to Phase 5).

## 🚀 How to Run (New Workflow)
1. Double-click `start_unified.bat`
2. Open `http://localhost:8000` (or `https://mamcrawler.tophertek.com`)
3. Use the Dashboard buttons to trigger searches and scans.
