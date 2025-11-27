"""
Gap Analysis Routes
FastAPI router for library gap analysis and automated acquisition
"""

import asyncio
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request, status, BackgroundTasks
from pydantic import BaseModel, Field
import logging

from backend.rate_limit import limiter, get_rate_limit

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# ============================================================================
# Pydantic Models (Request/Response schemas)
# ============================================================================

class GapAnalysisRequest(BaseModel):
    """Schema for gap analysis request"""
    analyze_only: bool = Field(False, description="Only analyze gaps, don't download")
    max_downloads: int = Field(10, ge=1, le=50, description="Maximum downloads to queue")
    series_priority: bool = Field(True, description="Prioritize series gaps")
    author_priority: bool = Field(True, description="Include author gaps")

    class Config:
        json_schema_extra = {
            "example": {
                "analyze_only": False,
                "max_downloads": 10,
                "series_priority": True,
                "author_priority": True
            }
        }


class StandardResponse(BaseModel):
    """Standard API response format"""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ============================================================================
# Helper function to run analysis
# ============================================================================

async def run_gap_analysis(
    analyze_only: bool = False,
    max_downloads: int = 10,
    series_priority: bool = True,
    author_priority: bool = True
) -> dict:
    """Run the gap analysis workflow."""
    # Import here to avoid circular imports
    import sys
    sys.path.insert(0, '/home/user/MAMcrawler')
    from audiobook_gap_analyzer import AudiobookGapAnalyzer

    analyzer = AudiobookGapAnalyzer()
    analyzer.config['max_downloads_per_run'] = max_downloads
    analyzer.config['series_priority'] = series_priority
    analyzer.config['author_priority'] = author_priority

    result = await analyzer.run_full_analysis(analyze_only=analyze_only)
    return result


# ============================================================================
# Route Handlers
# ============================================================================

@router.post(
    "/analyze",
    response_model=StandardResponse,
    summary="Analyze library gaps",
    description="Scan library and identify missing books (detection only)"
)
async def analyze_gaps():
    """
    Run gap analysis in detection-only mode.

    Scans the Audiobookshelf library, identifies series and authors,
    and calculates missing books without downloading.

    Returns:
        Standard response with gap analysis results
    """
    try:
        logger.info("Starting gap analysis (detection only)")

        result = await run_gap_analysis(analyze_only=True)

        return {
            "success": result.get("success", False),
            "data": {
                "stats": result.get("stats", {}),
                "gaps": result.get("gaps", []),
                "message": f"Found {len(result.get('gaps', []))} gaps in library"
            },
            "error": result.get("error"),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error during gap analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gap analysis failed: {str(e)}"
        )


@router.post(
    "/acquire",
    response_model=StandardResponse,
    summary="Search and queue missing books",
    description="Search MAM for identified gaps and queue downloads"
)
async def acquire_gaps(
    request: GapAnalysisRequest
):
    """
    Run full gap analysis with acquisition.

    1. Scans library for gaps
    2. Searches MAM for missing books
    3. Queues downloads

    Args:
        request: Configuration for the analysis run

    Returns:
        Standard response with analysis and download results
    """
    try:
        logger.info(f"Starting gap acquisition (max_downloads={request.max_downloads})")

        result = await run_gap_analysis(
            analyze_only=False,
            max_downloads=request.max_downloads,
            series_priority=request.series_priority,
            author_priority=request.author_priority
        )

        return {
            "success": result.get("success", False),
            "data": {
                "stats": result.get("stats", {}),
                "gaps": result.get("gaps", []),
                "downloads_queued": result.get("downloads_queued", []),
                "message": f"Queued {len(result.get('downloads_queued', []))} downloads"
            },
            "error": result.get("error"),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error during gap acquisition: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gap acquisition failed: {str(e)}"
        )


@router.post(
    "/analyze-and-acquire",
    response_model=StandardResponse,
    summary="Full gap analysis and acquisition",
    description="Complete workflow: detect gaps, search MAM, queue downloads"
)
async def analyze_and_acquire(
    max_downloads: int = Query(10, ge=1, le=50, description="Maximum downloads to queue"),
    series_priority: bool = Query(True, description="Prioritize series gaps"),
    author_priority: bool = Query(True, description="Include author gaps")
):
    """
    Run complete gap analysis and acquisition workflow.

    This is the main endpoint for automated library gap filling.

    Args:
        max_downloads: Maximum number of downloads to queue per run (1-50)
        series_priority: Whether to prioritize series gaps
        author_priority: Whether to include author gaps

    Returns:
        Standard response with complete results
    """
    try:
        logger.info(f"Starting full gap analysis and acquisition")

        result = await run_gap_analysis(
            analyze_only=False,
            max_downloads=max_downloads,
            series_priority=series_priority,
            author_priority=author_priority
        )

        return {
            "success": result.get("success", False),
            "data": {
                "stats": result.get("stats", {}),
                "gaps_identified": len(result.get("gaps", [])),
                "downloads_queued": len(result.get("downloads_queued", [])),
                "gaps": result.get("gaps", []),
                "downloads": result.get("downloads_queued", [])
            },
            "error": result.get("error"),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error during analyze-and-acquire: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analyze and acquire failed: {str(e)}"
        )


@router.post(
    "/analyze-async",
    response_model=StandardResponse,
    summary="Start gap analysis in background",
    description="Start gap analysis as a background task"
)
async def analyze_gaps_async(
    background_tasks: BackgroundTasks,
    request: GapAnalysisRequest
):
    """
    Start gap analysis as a background task.

    Returns immediately with a task ID. Use /report endpoint
    to check results after completion.

    Args:
        request: Configuration for the analysis run

    Returns:
        Standard response with task acknowledgment
    """
    try:
        logger.info("Starting background gap analysis")

        # Create async task
        async def background_analysis():
            await run_gap_analysis(
                analyze_only=request.analyze_only,
                max_downloads=request.max_downloads,
                series_priority=request.series_priority,
                author_priority=request.author_priority
            )

        # Add to background tasks
        background_tasks.add_task(asyncio.create_task, background_analysis())

        return {
            "success": True,
            "data": {
                "message": "Gap analysis started in background",
                "check_results": "Use GET /api/gaps/report to check results"
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error starting background analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start background analysis: {str(e)}"
        )


@router.get(
    "/report",
    response_model=StandardResponse,
    summary="Get latest gap analysis report",
    description="Get the most recent gap analysis results"
)
async def get_gap_report():
    """
    Get the most recent gap analysis report.

    Reads from gap_analysis_report.json generated by the analyzer.

    Returns:
        Standard response with report data
    """
    try:
        import json
        from pathlib import Path

        report_file = Path("/home/user/MAMcrawler/gap_analysis_report.json")

        if not report_file.exists():
            return {
                "success": False,
                "data": None,
                "error": "No gap analysis report found. Run /analyze first.",
                "timestamp": datetime.utcnow().isoformat()
            }

        with open(report_file, 'r') as f:
            report = json.load(f)

        return {
            "success": True,
            "data": report,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error reading gap report: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read report: {str(e)}"
        )


@router.get(
    "/history",
    response_model=StandardResponse,
    summary="Get gap analysis history",
    description="Get history of past gap analysis runs"
)
async def get_gap_history(
    limit: int = Query(10, ge=1, le=100, description="Number of recent runs to return")
):
    """
    Get history of gap analysis runs.

    Reads from gap_analyzer_state.json to show past runs.

    Args:
        limit: Maximum number of recent runs to return

    Returns:
        Standard response with analysis history
    """
    try:
        import json
        from pathlib import Path

        state_file = Path("/home/user/MAMcrawler/gap_analyzer_state.json")

        if not state_file.exists():
            return {
                "success": True,
                "data": {
                    "runs": [],
                    "total": 0
                },
                "error": None,
                "timestamp": datetime.utcnow().isoformat()
            }

        with open(state_file, 'r') as f:
            state = json.load(f)

        return {
            "success": True,
            "data": {
                "last_run": state.get("last_run"),
                "completed_searches": len(state.get("completed_searches", [])),
                "failed_searches": len(state.get("failed_searches", [])),
                "queued_downloads": state.get("queued_downloads", [])[-limit:]
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error reading gap history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read history: {str(e)}"
        )


@router.delete(
    "/reset-state",
    response_model=StandardResponse,
    summary="Reset gap analyzer state",
    description="Clear the analyzer state to allow re-searching"
)
async def reset_gap_state():
    """
    Reset the gap analyzer state.

    Clears completed_searches, failed_searches, and queued_downloads
    to allow re-searching for previously searched items.

    Returns:
        Standard response with reset confirmation
    """
    try:
        import json
        from pathlib import Path

        state_file = Path("/home/user/MAMcrawler/gap_analyzer_state.json")

        # Reset state
        new_state = {
            "last_run": None,
            "completed_searches": [],
            "failed_searches": [],
            "queued_downloads": []
        }

        with open(state_file, 'w') as f:
            json.dump(new_state, f, indent=2)

        logger.info("Gap analyzer state reset")

        return {
            "success": True,
            "data": {
                "message": "Gap analyzer state has been reset"
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error resetting gap state: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset state: {str(e)}"
        )
