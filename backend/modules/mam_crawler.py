"""
MAM Crawler Module - Wrapper for stealth_mam_crawler.py
Provides async interface for FastAPI backend to execute MAM guide crawling
"""

import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.models.task import Task

logger = logging.getLogger(__name__)


async def crawl_mam_guides(
    db_session: Session,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Execute MAM guide crawler with stealth behavior

    Args:
        db_session: SQLAlchemy database session for task tracking
        config: Optional configuration dict with keys:
            - max_guides: Maximum number of guides to crawl (None = all)
            - resume: Whether to resume from saved state (default: True)
            - min_delay: Minimum delay between requests in seconds (default: 10)
            - max_delay: Maximum delay between requests in seconds (default: 30)
            - output_dir: Output directory for guide files (default: guides_output)

    Returns:
        Dict with keys:
            - guides_count: Number of guides successfully crawled
            - errors: Number of failed guides
            - timestamp: Completion timestamp
            - guides_output_dir: Path to output directory
            - failed_guides: List of failed guide info

    Raises:
        ValueError: If MAM credentials not configured
        Exception: For any critical errors during execution
    """
    task_record = None
    start_time = datetime.now()

    try:
        # Create task record
        task_record = Task(
            task_name="MAM_CRAWLER",
            scheduled_time=start_time,
            actual_start=start_time,
            status="running",
            metadata={"config": config or {}}
        )
        db_session.add(task_record)
        db_session.commit()

        logger.info(f"Starting MAM crawler (Task ID: {task_record.id})")

        # Import stealth crawler
        try:
            from stealth_mam_crawler import StealthMAMCrawler
        except ImportError as e:
            logger.error(f"Failed to import stealth_mam_crawler: {e}")
            raise ImportError(
                "stealth_mam_crawler.py not found. Ensure it exists in project root."
            ) from e

        # Apply config overrides if provided
        crawler = StealthMAMCrawler()

        if config:
            if "min_delay" in config:
                crawler.min_delay = config["min_delay"]
            if "max_delay" in config:
                crawler.max_delay = config["max_delay"]
            if "output_dir" in config:
                crawler.output_dir = Path(config["output_dir"])
                crawler.output_dir.mkdir(exist_ok=True)

        # Execute crawler
        logger.info("Executing stealth MAM crawler...")
        await crawler.run()

        # Gather results
        guides_count = len(crawler.state.get("completed", []))
        errors_count = len(crawler.state.get("failed", []))
        failed_guides = crawler.state.get("failed", [])

        result = {
            "guides_count": guides_count,
            "errors": errors_count,
            "timestamp": datetime.now().isoformat(),
            "guides_output_dir": str(crawler.output_dir.absolute()),
            "failed_guides": failed_guides
        }

        # Update task record
        end_time = datetime.now()
        duration = int((end_time - start_time).total_seconds())

        task_record.actual_end = end_time
        task_record.duration_seconds = duration
        task_record.status = "completed"
        task_record.items_processed = guides_count + errors_count
        task_record.items_succeeded = guides_count
        task_record.items_failed = errors_count
        task_record.metadata = {
            **task_record.metadata,
            "result": result
        }

        db_session.commit()

        logger.info(
            f"MAM crawler completed: {guides_count} guides crawled, "
            f"{errors_count} errors"
        )

        return result

    except ValueError as e:
        # Missing credentials
        logger.error(f"Configuration error: {e}")

        if task_record:
            task_record.status = "failed"
            task_record.error_message = str(e)
            task_record.actual_end = datetime.now()
            db_session.commit()

        raise

    except ImportError as e:
        # Missing dependencies
        logger.error(f"Import error: {e}")

        if task_record:
            task_record.status = "failed"
            task_record.error_message = f"Import error: {e}"
            task_record.actual_end = datetime.now()
            db_session.commit()

        raise

    except Exception as e:
        # Any other errors
        logger.exception(f"MAM crawler failed with error: {e}")

        if task_record:
            task_record.status = "failed"
            task_record.error_message = str(e)
            task_record.actual_end = datetime.now()
            db_session.commit()

        # Return error result instead of raising
        return {
            "guides_count": 0,
            "errors": 1,
            "timestamp": datetime.now().isoformat(),
            "guides_output_dir": "",
            "failed_guides": [],
            "error": str(e)
        }


async def get_crawler_status() -> Dict[str, Any]:
    """
    Get current status of MAM crawler from state file

    Returns:
        Dict with keys:
            - completed_count: Number of completed guides
            - failed_count: Number of failed guides
            - pending_count: Number of pending guides
            - last_run: ISO timestamp of last run
            - state_file_exists: Whether state file exists
    """
    try:
        from stealth_mam_crawler import StealthMAMCrawler

        # Load state without initializing full crawler
        state_file = Path("crawler_state.json")

        if not state_file.exists():
            return {
                "completed_count": 0,
                "failed_count": 0,
                "pending_count": 0,
                "last_run": None,
                "state_file_exists": False
            }

        import json
        with open(state_file, 'r') as f:
            state = json.load(f)

        return {
            "completed_count": len(state.get("completed", [])),
            "failed_count": len(state.get("failed", [])),
            "pending_count": len(state.get("pending", [])),
            "last_run": state.get("last_run"),
            "state_file_exists": True
        }

    except Exception as e:
        logger.error(f"Error getting crawler status: {e}")
        return {
            "completed_count": 0,
            "failed_count": 0,
            "pending_count": 0,
            "last_run": None,
            "state_file_exists": False,
            "error": str(e)
        }


async def reset_crawler_state() -> Dict[str, str]:
    """
    Reset crawler state file to start fresh

    Returns:
        Dict with status message
    """
    try:
        state_file = Path("crawler_state.json")

        if state_file.exists():
            state_file.unlink()
            logger.info("Crawler state file deleted")
            return {"status": "success", "message": "Crawler state reset successfully"}
        else:
            return {"status": "success", "message": "No state file to reset"}

    except Exception as e:
        logger.error(f"Error resetting crawler state: {e}")
        return {"status": "error", "message": str(e)}
