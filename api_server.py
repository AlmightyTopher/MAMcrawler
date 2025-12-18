import asyncio
import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends
import uvicorn
from dotenv import load_dotenv
import server_auth
from backend.middleware.csrf import csrf_protection_middleware
from backend.services.job_queue_service import JobQueueService

# Load environment variables
load_dotenv()

# Import our ServiceManager
try:
    from mamcrawler.service_manager import ServiceManager
except ImportError:
    # Fallback if run from wrong dir
    import sys
    sys.path.append(os.getcwd())
    from mamcrawler.service_manager import ServiceManager

# Import Selenium Integration for Stats
try:
    from selenium_integration import get_mam_user_stats
except ImportError:
    logging.warning("Could not import selenium_integration. Stats fetching will fail.")
    async def get_mam_user_stats():
        return None

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("APIServer")

app = FastAPI(
    title="MAM Crawler API",
    dependencies=[Depends(server_auth.get_current_user)]
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# State
service_manager = ServiceManager()
STATS_FILE = "mam_stats.json"

# Clean up orphaned jobs on startup
JobQueueService.cleanup_orphaned_jobs()

# Middleware order matters: CSRF first, then CORS
app.middleware("http")(csrf_protection_middleware)


def get_latest_log_lines(n=1000) -> List[str]:
    """Read the latest lines from the most recent log file."""
    try:
        log_files = list(Path(".").glob("master_manager_*.log"))
        if not log_files:
            return []
        
        latest_log = max(log_files, key=os.path.getctime)
        
        lines = []
        try:
            with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                # Return exactly the last n lines, stripping only trailing newline
                lines = [line.rstrip() for line in all_lines[-n:]]
        except Exception:
            pass # Transient read error
                
        return lines
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        return []
        return []

def load_stats() -> Dict:
    """Load stats from cache file."""
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading stats file: {e}")
    return {}

def save_stats(stats: Dict):
    """Save stats to cache file."""
    try:
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving stats file: {e}")

def write_to_log(level: str, message: str):
    """Append a message to the latest log file."""
    try:
        log_files = list(Path(".").glob("master_manager_*.log"))
        if not log_files:
            return
        
        latest_log = max(log_files, key=os.path.getctime)
        timestamp = datetime.now().strftime("%H:%M:%S,%f")[:-3]
        
        with open(latest_log, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}][{level}] - {message}\n")
    except Exception as e:
        logger.error(f"Failed to write to log: {e}")

async def refresh_stats_task():
    """Background task to refresh stats from MAM."""
    logger.info("Refreshing MAM stats...")
    try:
        stats = await get_mam_user_stats()
        if stats:
            save_stats(stats)
            logger.info("MAM stats refreshed successfully")
        else:
            logger.warning("MAM stats refresh returned no data")
    except Exception as e:
        logger.error(f"Failed to refresh MAM stats: {e}")

async def periodic_stats_refresh():
    """Periodically refresh stats every 12 hours."""
    while True:
        # Wait a bit on startup to let other things settle
        await asyncio.sleep(60) 
        await refresh_stats_task()
        await asyncio.sleep(12 * 3600) # 12 hours

@app.on_event("startup")
async def startup_event():
    # Start the periodic refresh loop
    asyncio.create_task(periodic_stats_refresh())

@app.get("/")
async def serve_dashboard():
    response = FileResponse("dashboard.html")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.get("/stats-panel")
async def serve_stats_panel():
    response = FileResponse("stats_panel.html")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.get("/api/status")
async def get_status():
    """Get full system status."""
    
    # Check services
    services = []
    for name, config in service_manager.services.items():
        is_running = service_manager.is_port_open(config['port'])
        display_name = config['name']
        if display_name == "Docker Desktop (for Prowlarr)":
            display_name = "Prowlarr"
            
        services.append({
            "name": display_name,
            "status": "running" if is_running else "stopped"
        })
        
    # Check active task
    active_task = None
    
    # Try to read granular status from active_status.json
    status_file = "active_status.json"
    if os.path.exists(status_file):
        try:
            with open(status_file, 'r') as f:
                task_data = json.load(f)
                # Check staleness (e.g. 30 seconds to be safe)
                if time.time() - task_data.get('timestamp', 0) < 30:
                    active_task = {
                        "name": task_data.get('name', 'Unknown Task'),
                        "progress": task_data.get('progress', 0),
                        "details": task_data.get('details', '')
                    }
        except Exception as e:
            logger.error(f"Failed to read status file: {e}")

    # Fallback: check database for running jobs
    if not active_task:
        running_jobs = JobQueueService.get_running_jobs()
        if running_jobs:
            job = running_jobs[0]
            active_task = {
                "name": job.get("name", "Running Task..."),
                "progress": 50, # Indeterminate
                "details": "Executing background process..."
            }
        
    # Get Logs
    recent_logs = get_latest_log_lines(5)
    
    # Get Stats (from cache)
    stats = load_stats()
    
    # Get qBittorrent Queue
    queue = []
    try:
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        
        def fetch_queue():
            try:
                # Import here to avoid startup issues if file missing
                from qbittorrent_session_client import QBittorrentSessionClient
                
                qb_host = os.getenv('QB_HOST', 'http://localhost')
                qb_port = os.getenv('QB_PORT', '8080')
                qb_user = os.getenv('QB_USERNAME', 'admin')
                qb_pass = os.getenv('QB_PASSWORD', '')
                
                # Handle host/port logic
                qb_url = f"{qb_host}:{qb_port}" if not qb_host.endswith(qb_port) else qb_host
                
                client = QBittorrentSessionClient(qb_url, qb_user, qb_pass, timeout=2)
                if client.login():
                    torrents = client.get_torrents()
                    
                    # Categorize
                    downloading = []
                    seeding = []
                    completed = []
                    others = []
                    
                    for t in torrents:
                        state = t.get('state', '').lower()
                        progress = t.get('progress', 0)
                        
                        # Downloading / Incomplete
                        if 'dl' in state or 'download' in state or progress < 1.0:
                            downloading.append(t)
                        # Seeding / Uploading
                        elif 'up' in state or 'upload' in state or 'seeding' in state:
                            seeding.append(t)
                        # Completed / Paused
                        elif progress >= 1.0:
                            completed.append(t)
                        else:
                            others.append(t)
                            
                    # Sort lists
                    # Downloading: by progress (desc)
                    downloading.sort(key=lambda x: x.get('progress', 0), reverse=True)
                    # Seeding: by upload speed (desc)
                    seeding.sort(key=lambda x: x.get('upspeed', 0), reverse=True)
                    # Completed: by added_on (desc)
                    completed.sort(key=lambda x: x.get('added_on', 0), reverse=True)
                    
                    # Combine for UI (Priority: Downloading -> Seeding -> Recent Completed)
                    # Limit total to 20 items
                    combined = []
                    combined.extend(downloading)
                    
                    # Add seeding (limit to 5 if we have downloads, else more)
                    remaining_slots = 20 - len(combined)
                    if remaining_slots > 0:
                        combined.extend(seeding[:remaining_slots])
                        
                    remaining_slots = 20 - len(combined)
                    if remaining_slots > 0:
                        combined.extend(completed[:remaining_slots])
                    
                    # Format for UI
                    formatted = []
                    for t in combined:
                        # Format size
                        size = t.get('size', 0)
                        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                            if size < 1024:
                                size_str = f"{size:.1f} {unit}"
                                break
                            size /= 1024
                        else:
                            size_str = f"{size:.1f} PB"
                            
                        # Format speeds
                        dlspeed = t.get('dlspeed', 0)
                        if dlspeed > 1024*1024:
                            dl_str = f"{dlspeed/1024/1024:.1f} MB/s"
                        elif dlspeed > 1024:
                            dl_str = f"{dlspeed/1024:.0f} KB/s"
                        else:
                            dl_str = f"{dlspeed} B/s"
                            
                        upspeed = t.get('upspeed', 0)
                        if upspeed > 1024*1024:
                            up_str = f"{upspeed/1024/1024:.1f} MB/s"
                        elif upspeed > 1024:
                            up_str = f"{upspeed/1024:.0f} KB/s"
                        else:
                            up_str = f"{upspeed} B/s"
                            
                        formatted.append({
                            "name": t.get('name', 'Unknown'),
                            "state": t.get('state', 'unknown'),
                            "size": size_str,
                            "dlspeed": dl_str,
                            "upspeed": up_str,
                            "progress": t.get('progress', 0),
                            "hash": t.get('hash', '')
                        })
                    return formatted
            except Exception as e:
                logger.error(f"Error fetching qBit queue: {e}")
                return []
            return []

        queue = await loop.run_in_executor(None, fetch_queue)
        
    except Exception as e:
        logger.error(f"Failed to get qBit queue: {e}")
    
    return {
        "stats": stats,
        "services": services,
        "active_task": active_task,
        "queue": queue,
        "recent_logs": recent_logs
    }

@app.get("/api/stats")
async def get_stats():
    """Get detailed stats."""
    return load_stats()

@app.post("/api/stats/refresh")
async def trigger_stats_refresh(background_tasks: BackgroundTasks):
    """Trigger a manual stats refresh."""
    background_tasks.add_task(refresh_stats_task)
    return {"status": "refresh_started", "message": "Stats refresh started in background"}

@app.post("/api/control/{action}")
async def control_action(action: str):
    """Trigger a crawler action."""
    # Check if a job is already running using database
    running_jobs = JobQueueService.get_running_jobs()
    if running_jobs:
        raise HTTPException(status_code=409, detail="A task is already running")

    cmd = ["python", "master_audiobook_manager.py"]
    
    if action == "top-search":
        cmd.append("--top-search")
    elif action == "update-metadata":
        cmd.append("--update-metadata")
    elif action == "missing-books":
        cmd.append("--missing-books")
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
        
    try:
        # Start job using job queue service
        task_id = JobQueueService.start_job(
            task_name=f"CONTROL_{action.upper()}",
            command=cmd,
            metadata={"action": action}
        )
        if task_id:
            return {"status": "success", "message": f"Started {action}", "task_id": task_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to start task")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def execute_task(action_name: str, flag: str):
    """Helper to execute a task with concurrency locking."""
    global current_process
    
    # SAFETY LOCK 1: Concurrency Guard
    if current_process and current_process.poll() is None:
        write_to_log("WARNING", f"Blocked attempt to start {action_name} while another task is running")
        return JSONResponse(
            status_code=409,
            content={"success": False, "error": "Task already running"}
        )
        
    cmd = ["python", "master_audiobook_manager.py", flag]
    
    try:
        write_to_log("INFO", f"API initiated {action_name}")
        task_id = JobQueueService.start_job(
            task_name=action_name,
            command=cmd,
            metadata={"flag": flag}
        )
        if task_id:
            return {"success": True, "task_id": task_id}
        else:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to start task"}
            )
    except Exception as e:
        write_to_log("ERROR", f"Failed to start {action_name}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.post("/api/actions/top-search")
async def action_top_search():
    return execute_task("Top Search", "--top-search")

@app.post("/api/actions/refresh-metadata")
async def action_refresh_metadata():
    return execute_task("Metadata Refresh", "--update-metadata")

@app.post("/api/actions/detect-missing")
async def action_detect_missing():
    return execute_task("Missing Books Detection", "--missing-books")

@app.post("/api/actions/sync-goodreads")
async def action_sync_goodreads():
    """Trigger Goodreads Sync."""
    global current_process
    
    # SAFETY LOCK
    if current_process and current_process.poll() is None:
        write_to_log("WARNING", "Blocked attempt to start Goodreads Sync while another task is running")
        return JSONResponse(
            status_code=409, 
            content={"success": False, "error": "Task already running"}
        )

    cmd = ["python", "goodreads_sync.py"]
    
    try:
        write_to_log("INFO", "API initiated Goodreads Sync")
        task_id = JobQueueService.start_job(
            task_name="GOODREADS_SYNC",
            command=cmd
        )
        if task_id:
            return {"success": True, "task_id": task_id}
        else:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to start task"}
            )
    except Exception as e:
        write_to_log("ERROR", f"Failed to start Goodreads Sync: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "1.0.0"}

if __name__ == "__main__":
    print("Starting MAM Crawler API Server...")
    server_auth.print_credentials()
    print("Dashboard available at: http://127.0.0.1:8081")
    uvicorn.run(app, host="127.0.0.1", port=8081)
