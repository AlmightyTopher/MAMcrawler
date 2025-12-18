import json
import time
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

# Import database components
try:
    from backend.database import SessionLocal
    from backend.models.task import Task
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

STATUS_FILE = "active_status.json" # Keep file as fallback for now if DB fails
logger = logging.getLogger(__name__)

class StatusReporter:
    """
    Status reporter that writes to PostgreSQL Task table.
    Falls back to file/logging if DB is unavailable.
    """
    def __init__(self, task_name: str, total: Optional[int] = None):
        self.task_name = task_name
        self.total = total
        self.current_item = 0
        self.start_time = time.time()
        self.task_id = None
        self.db = None
        
        if DB_AVAILABLE:
            try:
                self.db = SessionLocal()
                new_task = Task(
                    task_name=task_name,
                    scheduled_time=datetime.utcnow(),
                    actual_start=datetime.utcnow(),
                    status="running",
                    items_processed=0,
                    task_metadata={"total_items": total, "progress_percent": 0}
                )
                self.db.add(new_task)
                self.db.commit()
                self.db.refresh(new_task)
                self.task_id = new_task.id
                logger.info(f"Created DB Task ID {self.task_id} for {task_name}")
            except Exception as e:
                logger.error(f"Failed to create DB task: {e}")
                self.db = None

        self.update(0, f"Starting {task_name}...")

    def update(self, current: Optional[int] = None, details: str = "", step_name: str = None):
        """Update the status in DB and file."""
        if current is not None:
            self.current_item = current
        
        progress = 0
        if self.total and self.total > 0:
            progress = int((self.current_item / self.total) * 100)
        elif self.total == 0:
            progress = 100
            
        # Cap progress at 99 until truly complete
        if progress >= 100 and self.total is None:
             progress = 99
        
        # Log to standard logger
        if details:
            msg = f"[{step_name or self.task_name}] {details}"
            logger.info(msg)

        # Update DB if available
        if self.task_id and self.db:
            try:
                task = self.db.query(Task).get(self.task_id)
                if task:
                    task.items_processed = self.current_item
                    # Update metadata with progress details
                    meta = dict(task.task_metadata or {})
                    meta.update({
                        "progress_percent": progress,
                        "current_step": step_name,
                        "last_update": details,
                        "updated_at": time.time()
                    })
                    task.task_metadata = meta
                    self.db.commit()
            except Exception as e:
                logger.error(f"Failed to update DB task: {e}")

        # Fallback/Legacy file update
        status_data = {
            "name": self.task_name,
            "step": step_name or self.task_name,
            "progress": progress,
            "details": details,
            "timestamp": time.time(),
            "status": "running",
            "task_id": self.task_id
        }
        self._save(status_data)

    def complete(self, message: str = "Completed"):
        """Mark the task as complete."""
        logger.info(f"[{self.task_name}] {message}")
        
        end_time = datetime.utcnow()
        duration = (time.time() - self.start_time)
        
        if self.task_id and self.db:
            try:
                task = self.db.query(Task).get(self.task_id)
                if task:
                    task.status = "completed"
                    task.actual_end = end_time
                    task.duration_seconds = int(duration)
                    task.items_succeeded = self.current_item # Assume current count is success count
                    task.log_output = message
                    
                    meta = dict(task.task_metadata or {})
                    meta["progress_percent"] = 100
                    task.task_metadata = meta
                    
                    self.db.commit()
                    self.db.close()
                    self.db = None
            except Exception as e:
                logger.error(f"Failed to complete DB task: {e}")

        status_data = {
            "name": self.task_name,
            "step": "Complete",
            "progress": 100,
            "details": message,
            "timestamp": time.time(),
            "status": "completed",
            "task_id": self.task_id
        }
        self._save(status_data)

    def error(self, message: str):
        """Mark the task as failed."""
        logger.error(f"[{self.task_name}] Failed: {message}")
        
        end_time = datetime.utcnow()
        duration = (time.time() - self.start_time)

        if self.task_id and self.db:
            try:
                task = self.db.query(Task).get(self.task_id)
                if task:
                    task.status = "failed"
                    task.actual_end = end_time
                    task.duration_seconds = int(duration)
                    task.error_message = message
                    
                    self.db.commit()
                    self.db.close()
                    self.db = None
            except Exception as e:
                logger.error(f"Failed to mark DB task error: {e}")

        status_data = {
            "name": self.task_name,
            "step": "Error",
            "progress": 0,
            "details": f"Error: {message}",
            "timestamp": time.time(),
            "status": "error",
            "task_id": self.task_id
        }
        self._save(status_data)

    def _save(self, data):
        """Write to file atomically-ish."""
        try:
            # write to temp then rename to avoid read conditions
            temp_file = STATUS_FILE + ".tmp"
            with open(temp_file, 'w') as f:
                json.dump(data, f)
            os.replace(temp_file, STATUS_FILE)
        except Exception:
            # Ignore file access errors (e.g. locked)
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.error(str(exc_val))
        else:
            self.complete()
