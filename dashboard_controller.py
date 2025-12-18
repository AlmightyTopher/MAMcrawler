import asyncio
import logging
import os
import subprocess
import json
import re
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Configuration
LOG_FILE = "real_workflow_execution.log"
WORKFLOW_SCRIPT = "execute_full_workflow.py"
HOST = "127.0.0.1"
PORT = 8081

app = FastAPI(title="MAM Crawler Dashboard Controller")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
workflow_process: Optional[subprocess.Popen] = None

class Service(BaseModel):
    name: str
    status: str
    url: Optional[str] = None

class LogEntry(BaseModel):
    time: str
    level: str
    message: str

class ActiveTask(BaseModel):
    name: str
    progress: int
    details: str

class StatusResponse(BaseModel):
    stats: Dict[str, str]
    services: List[Service]
    queue: List[Dict]
    active_task: Optional[ActiveTask]
    recent_logs: List[LogEntry]

def parse_logs(lines: List[str]) -> List[LogEntry]:
    parsed = []
    # Regex for log format: [2025-12-11 12:21:00] [LEVEL ] Message
    log_pattern = re.compile(r'\[(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\]\s\[(\w+)\s*\]\s(.*)')
    
    for line in lines:
        match = log_pattern.match(line.strip())
        if match:
            timestamp_str, level, message = match.groups()
            # Convert timestamp to HH:MM:SS for display
            try:
                dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                time_display = dt.strftime("%H:%M:%S")
            except:
                time_display = timestamp_str[-8:]

            parsed.append(LogEntry(
                time=time_display,
                level=level.strip(),
                message=message
            ))
    return parsed

def get_last_n_logs(n: int = 50) -> List[LogEntry]:
    if not os.path.exists(LOG_FILE):
        return [LogEntry(time=datetime.now().strftime("%H:%M:%S"), level="INFO", message="Waiting for logs...")]
    
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            # Efficiently read last N lines
            lines = f.readlines()[-n:]
            return parse_logs(lines)
    except Exception as e:
        return [LogEntry(time=datetime.now().strftime("%H:%M:%S"), level="ERROR", message=f"Failed to read logs: {str(e)}")]

def check_service_status(port: int) -> str:
    # Simple check if port is open (rudimentary)
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return "running" if result == 0 else "stopped"

def determine_active_task(logs: List[LogEntry]) -> Optional[ActiveTask]:
    if not workflow_process or workflow_process.poll() is not None:
        return None
    
    # Try to infer phase from last log
    if not logs:
        return ActiveTask(name="Initializing", progress=0, details="Starting...")
    
    last_log = logs[-1]
    
    # Heuristic mapping of phases to progress
    phase_map = {
        "PHASE 1": ("Library Scan", 10),
        "PHASE 2": ("Sci-Fi Search", 20),
        "PHASE 3": ("Fantasy Search", 30),
        "PHASE 4": ("Queueing", 40),
        "PHASE 5": ("Adding to Client", 50),
        "PHASE 6": ("Downloading", 60),
        "PHASE 7": ("Sync to ABS", 70),
        "PHASE 8": ("Metadata Sync", 80),
        "PHASE 10": ("Missing Books", 90),
        "PHASE 12": ("Backup", 95)
    }
    
    for log in reversed(logs):
        for phase_key, (name, progress) in phase_map.items():
            if phase_key in log.message:
                return ActiveTask(name=name, progress=progress, details=last_log.message)
            
    return ActiveTask(name="Running Request", progress=50, details=last_log.message)

@app.get("/")
async def get_dashboard():
    if os.path.exists("dashboard.html"):
        return FileResponse("dashboard.html")
    return HTMLResponse("<h1>Dashboard file not found</h1>")

@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    logs = get_last_n_logs(20)
    
    # Check services
    services = [
        Service(name="Audiobookshelf", status=check_service_status(13378), url="http://localhost:13378"),
        Service(name="qBittorrent", status=check_service_status(52095) or check_service_status(8080), url="http://192.168.0.48:52095"), # Using logic to define status
        Service(name="Prowlarr", status=check_service_status(9696), url="http://localhost:9696")
    ]
    
    # Determine active task
    active_task = determine_active_task(logs)
    
    # Queue (simplified simulation or parsing logs for "Queued:")
    queue = []
    
    return StatusResponse(
        stats={"shorthand": "System Online - Ready"},
        services=services,
        queue=queue,
        active_task=active_task,
        recent_logs=logs
    )

@app.post("/api/actions/top-search")
async def run_top_search(background_tasks: BackgroundTasks):
    global workflow_process
    if workflow_process and workflow_process.poll() is None:
        return {"success": False, "error": "Workflow already running"}
    
    # Run in background
    try:
        # Use python from current venv if possible
        python_exe = "python"
        if os.path.exists("venv/Scripts/python.exe"):
            python_exe = "venv/Scripts/python.exe"
            
        workflow_process = subprocess.Popen(
            [python_exe, WORKFLOW_SCRIPT],
            stdout=subprocess.DEVNULL, # Lets it write to the file we are monitoring
            stderr=subprocess.DEVNULL,
            cwd=os.getcwd()
        )
        return {"success": True, "pid": workflow_process.pid}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/actions/refresh-metadata")
async def run_metadata_refresh():
    # Placeholder
    return {"success": True}

@app.post("/api/actions/detect-missing")
async def run_detect_missing():
    # Placeholder
    return {"success": True}

@app.post("/api/actions/sync-goodreads")
async def run_goodreads_sync():
    global workflow_process
    if workflow_process and workflow_process.poll() is None:
        return {"success": False, "error": "A process is already running"}
    
    try:
        python_exe = "venv/Scripts/python.exe" if os.path.exists("venv/Scripts/python.exe") else "python"
        
        # Open log file for appending
        log_file = open(LOG_FILE, "a")
        
        workflow_process = subprocess.Popen(
            [python_exe, "goodreads_sync.py"],
            stdout=log_file,
            stderr=log_file,
            cwd=os.getcwd()
        )
        return {"success": True, "pid": workflow_process.pid}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    print(f"Starting Dashboard Controller on http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)
