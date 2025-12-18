"""
Dashboard Compatibility Layer
===========================
This router bridges the gap between the standalone Dashboard (frontend)
and the Backend architecture. It maps the Dashboard's expected endpoints
to the actual Backend services.

Status: Phase 1 (Unification)
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime
import logging
import json
import os
from backend.config import get_settings

from backend.routes.system import get_system_stats

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()

# Mock data for initial bridge (will replace with real service calls)
RECENT_LOGS = []

def _get_db_queue():
    """Fetch active downloads from DB"""
    try:
        from backend.database import get_db_context
        from backend.models.download import Download
        
        queue_items = []
        with get_db_context() as db:
            # Check for queued or downloading
            pending = db.query(Download).filter(
                Download.status.in_(["queued", "downloading", "pending"])
            ).order_by(Download.date_queued.desc()).limit(20).all()
            
            for d in pending:
                queue_items.append({
                    "name": d.title,  # Frontend expects 'name'
                    "title": d.title,
                    "author": d.author,
                    "status": d.status,
                    "size": getattr(d, 'size_mb', '0 MB'), # Placeholder if not in model
                    "dlspeed": "0 KB/s",
                    "upspeed": "0 KB/s",
                    "progress": 0
                })
        return queue_items
    except Exception as e:
        logger.error(f"Failed to fetch queue: {e}")
        return []

# Custom Handler to intercept logs for Dashboard
class DashboardLogHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            # Store in RECENT_LOGS
            # Format: "[Time] Message" - simplistic
            time_str = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
            RECENT_LOGS.append(f"[{time_str}] {msg}")
            
            # Keep size manageable
            if len(RECENT_LOGS) > 100:
                RECENT_LOGS.pop(0)
        except Exception:
            self.handleError(record)

# Attach handler to root logger
dashboard_handler = DashboardLogHandler()
dashboard_handler.setFormatter(logging.Formatter('%(message)s'))
logging.getLogger().addHandler(dashboard_handler)

@router.get("/status")
async def get_dashboard_status():
    """
    Returns the exact structure expected by dashboard.html
    """
    # 1. Get System Stats from the real backend
    # We can reuse the logic, but for now let's construct what dashboard expects
    
    # Simulate reading from the "Real Workflow" logs if possible, 
    # or just return backend status.
    
    try:
        # Read the latest logs from the "Real" execution log if it exists
        # to show something familiar to the user
        logs = []
        if os.path.exists("execution_log_real_final.txt"):
            with open("execution_log_real_final.txt", "r") as f:
                # Get last 20 lines
                lines = f.readlines()[-20:]
                logs = [line.strip() for line in lines if line.strip()]
        
        # Format file logs
        formatted_logs = []
        for log in logs:
            parts = log.split('] ', 1)
            time_part = log[1:20] if len(log) > 20 else datetime.now().strftime("%H:%M:%S")
            msg_part = parts[1] if len(parts) > 1 else log
            formatted_logs.append({
                "time": time_part,
                "level": "HIST", 
                "message": msg_part
            })

        # Add recent memory logs
        for log in RECENT_LOGS:
             parts = log.split('] ', 1)
             time_part = log[1:20] if len(log) > 20 else datetime.now().strftime("%H:%M:%S")
             msg_part = parts[1] if len(parts) > 1 else log
             formatted_logs.append({
                "time": time_part,
                "level": "LIVE", 
                "message": msg_part
            })
            
        # Sort by time (simple string sort might be enough for now, or just append)
        # formatted_logs.sort(key=lambda x: x['time']) 

        return {
            "stats": {
                "shorthand": f"MAM Crawler Online | {datetime.now().strftime('%H:%M')} | System Unified"
            },
            "services": [
                {"name": "Audiobookshelf", "status": "running", "url": settings.ABS_URL},
                {"name": "qBittorrent", "status": "running", "url": f"{settings.QB_HOST}:{settings.QB_PORT}"},
                {"name": "Backend API", "status": "running", "url": f"http://localhost:{settings.APP_PORT}"}
            ],
            "queue": _get_db_queue(),
            "recent_logs": formatted_logs[-50:] # Return last 50 logs
        }
    except Exception as e:
        logger.error(f"Dashboard status error: {e}")
        return {"error": str(e)}

from backend.services.mam_selenium_service import MAMSeleniumService
from backend.services.discovery_service import DiscoveryService

# Global service instances (lazy loaded or singleton)
mam_service = MAMSeleniumService()
discovery_service = DiscoveryService()

@router.post("/actions/top-search")
async def action_top_search(background_tasks: BackgroundTasks):
    """Trigger Search & Download Workflow"""
    RECENT_LOGS.append(f"[{datetime.now()}] Action triggered: Top Search & Download")
    
    async def run_workflow():
        try:
            RECENT_LOGS.append(f"[{datetime.now()}] Scanning library...")
            books_to_download = await discovery_service.find_new_books()
            
            if not books_to_download:
                RECENT_LOGS.append(f"[{datetime.now()}] No new books found to download.")
                return

            RECENT_LOGS.append(f"[{datetime.now()}] Found {len(books_to_download)} books to acquire. Starting MAM Crawler...")
            downloaded = await mam_service.run_search_and_download(books_to_download)
            
            RECENT_LOGS.append(f"[{datetime.now()}] Workflow complete. Queued {len(downloaded)} downloads.")
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            RECENT_LOGS.append(f"[{datetime.now()}] Workflow failed: {str(e)}")

    background_tasks.add_task(run_workflow)
    return {"status": "triggered", "message": "Search workflow started"}

@router.post("/actions/detect-missing")
async def action_detect_missing(background_tasks: BackgroundTasks):
    """Trigger Missing Books Detection"""
    RECENT_LOGS.append(f"[{datetime.now()}] Action triggered: Missing Books Detection")
    
    async def run_scan():
        try:
            result = await discovery_service.scan_library()
            total = result.get('total_items', 0)
            RECENT_LOGS.append(f"[{datetime.now()}] Scan complete. Library contains {total} items.")
        except Exception as e:
            logger.error(f"Scan failed: {e}")
            RECENT_LOGS.append(f"[{datetime.now()}] Scan failed: {str(e)}")

    background_tasks.add_task(run_scan)
    return {"status": "triggered", "message": "Library scan started"}

@router.post("/actions/refresh-metadata")
async def action_refresh_metadata(background_tasks: BackgroundTasks):
    """Trigger Metadata Refresh (ABS <-> Hardcover)"""
    RECENT_LOGS.append(f"[{datetime.now()}] Action triggered: Metadata Refresh")
    
    async def run_sync():
        try:
            from backend.integrations.audiobookshelf_hardcover_sync import AudiobookShelfHardcoverSync
            
            if not settings.ABS_TOKEN or not settings.HARDCOVER_TOKEN:
                RECENT_LOGS.append(f"[{datetime.now()}] Failed: Missing ABS_TOKEN or HARDCOVER_TOKEN")
                return

            syncer = AudiobookShelfHardcoverSync(
                settings.ABS_URL,
                settings.ABS_TOKEN,
                settings.HARDCOVER_TOKEN
            )
            
            # Use first library for now
            lib_id = None
            lib_name = "Unknown"
            
            # Step 1: Get Library ID
            async with syncer.abs_client:
                libs = await syncer.abs_client.get_libraries()
                if libs:
                    lib_id = libs[0]['id']
                    lib_name = libs[0]['name']

            if not lib_id:
                RECENT_LOGS.append(f"[{datetime.now()}] No libraries found.")
                return

            RECENT_LOGS.append(f"[{datetime.now()}] Syncing library: {lib_name}...")
            
            # Step 2: Run Sync (manages its own connection)
            results = await syncer.sync_library(lib_id, limit=None, auto_update=False)
            
            stats = syncer.generate_report(results)["summary"]
            RECENT_LOGS.append(f"[{datetime.now()}] Sync complete. Updated: {stats['updated']}, Unknown: {stats['failed']}")

        except Exception as e:
            logger.error(f"Metadata refresh failed: {e}")
            RECENT_LOGS.append(f"[{datetime.now()}] Metadata refresh failed: {str(e)}")

    background_tasks.add_task(run_sync)
    return {"status": "triggered", "message": "Metadata refresh started"}

@router.post("/actions/sync-goodreads")
async def action_sync_goodreads(background_tasks: BackgroundTasks):
    """Trigger Goodreads Sync"""
    RECENT_LOGS.append(f"[{datetime.now()}] Action triggered: Goodreads Sync")
    
    async def run_goodreads():
        try:
            from backend.services.goodreads_service import GoodreadsService
            service = GoodreadsService()
            
            RECENT_LOGS.append(f"[{datetime.now()}] Fetching Goodreads RSS...")
            stats = await service.sync_goodreads()
            
            RECENT_LOGS.append(f"[{datetime.now()}] Goodreads sync complete. Processed: {stats['processed']}, ABS Updated: {stats['abs_updated']}")
        except Exception as e:
            logger.error(f"Goodreads sync failed: {e}")
            RECENT_LOGS.append(f"[{datetime.now()}] Goodreads sync failed: {str(e)}")

    background_tasks.add_task(run_goodreads)
    return {"status": "triggered", "message": "Goodreads sync started"}

@router.post("/actions/scan-fantasy")
async def action_scan_fantasy(background_tasks: BackgroundTasks):
    """Trigger Curated Fantasy Scan"""
    RECENT_LOGS.append(f"[{datetime.now()}] Action triggered: Top Fantasy Scan")
    
    async def run_scan():
        try:
            from backend.services.curated_list_service import CuratedListService
            service = CuratedListService()
            
            RECENT_LOGS.append(f"[{datetime.now()}] Scanning MAM for Top 10 Fantasy (Last 7 Days)...")
            stats = await service.scan_fantasy_top10()
            
            RECENT_LOGS.append(f"[{datetime.now()}] Scan complete. Found: {stats['found']}, Sent to Prowlarr: {stats['sent_to_prowlarr']}")
        except Exception as e:
            logger.error(f"Fantasy scan failed: {e}")
            RECENT_LOGS.append(f"[{datetime.now()}] Fantasy scan failed: {str(e)}")

    background_tasks.add_task(run_scan)
    return {"status": "triggered", "message": "Fantasy scan started"}
@router.post("/actions/full-workflow")
async def action_full_workflow(background_tasks: BackgroundTasks):
    """Trigger Legacy Full Workflow (Project Megazord)"""
    RECENT_LOGS.append(f"[{datetime.now()}] Action triggered: Full Workflow (Legacy)")
    
    async def run_full_workflow():
        try:
            from backend.schedulers.tasks import execute_full_workflow_task
            await execute_full_workflow_task()
            RECENT_LOGS.append(f"[{datetime.now()}] Full workflow completed successfully.")
        except Exception as e:
            logger.error(f"Full workflow failed: {e}")
            RECENT_LOGS.append(f"[{datetime.now()}] Full workflow failed: {str(e)}")

    background_tasks.add_task(run_full_workflow)
    return {"status": "triggered", "message": "Full workflow started"}
