"""
Repair & Replacement API Routes

Endpoints for evaluating, executing, and managing audiobook repairs and replacements.
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from mamcrawler.repair import get_repair_orchestrator, get_repair_reporter
from backend.logging.operation_logger import get_operation_logger

router = APIRouter(prefix="/api/repairs", tags=["repairs"])
logger_service = get_operation_logger()
orchestrator = get_repair_orchestrator()
reporter = get_repair_reporter()


# ============================================================================
# Request/Response Models
# ============================================================================

class EvaluateReplacementRequest(BaseModel):
    """Request to evaluate a replacement file"""
    original_file: str
    replacement_file: str
    audiobook_title: str = "Unknown"
    author: str = "Unknown"


class ExecuteReplacementRequest(BaseModel):
    """Request to execute a replacement"""
    original_file: str
    replacement_file: str
    audiobook_title: str = "Unknown"


class BatchEvaluateRequest(BaseModel):
    """Request to evaluate multiple replacement candidates"""
    original_file: str
    replacement_candidates: List[str]
    audiobook_title: str = "Unknown"
    author: str = "Unknown"


class EvaluationResponse(BaseModel):
    """Response from replacement evaluation"""
    is_acceptable: bool
    decision: str
    reason: str
    quality_comparison: dict
    audiobook_title: str
    author: str


class ExecutionResponse(BaseModel):
    """Response from replacement execution"""
    success: bool
    message: str
    original_file: str
    replacement_file: str
    backup_file: Optional[str] = None
    error: Optional[str] = None


class BatchEvaluationResponse(BaseModel):
    """Response from batch evaluation"""
    audiobook_title: str
    author: str
    candidates_evaluated: int
    candidates_submitted: int
    acceptable_candidates: List[str]
    best_replacement: Optional[str]
    evaluations: list


class RepairReportResponse(BaseModel):
    """Repair report response"""
    report_type: str
    timestamp: str
    success: bool
    details: dict


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_replacement(request: EvaluateReplacementRequest):
    """
    Evaluate if a replacement file is acceptable.

    Compares audio quality metrics (codec, bitrate, duration) to determine
    if the replacement is suitable for the original audiobook.

    Args:
        original_file: Path to original audio file
        replacement_file: Path to replacement audio file
        audiobook_title: Title of the audiobook
        author: Author name

    Returns:
        EvaluationResponse with decision and quality comparison

    Raises:
        HTTPException: If files don't exist or evaluation fails
    """
    try:
        from pathlib import Path

        # Validate files exist
        if not Path(request.original_file).exists():
            raise HTTPException(status_code=400, detail=f"Original file not found: {request.original_file}")
        if not Path(request.replacement_file).exists():
            raise HTTPException(status_code=400, detail=f"Replacement file not found: {request.replacement_file}")

        # Evaluate replacement
        result = orchestrator.evaluate_replacement(
            request.original_file,
            request.replacement_file,
            request.audiobook_title,
            request.author
        )

        return EvaluationResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@router.post("/execute", response_model=ExecutionResponse)
async def execute_replacement(request: ExecuteReplacementRequest):
    """
    Execute audiobook replacement with backup.

    Performs safe replacement of original file with replacement file.
    Automatically creates backup before replacement and restores on failure.

    Args:
        original_file: Path to original audio file
        replacement_file: Path to replacement audio file
        audiobook_title: Title of the audiobook

    Returns:
        ExecutionResponse with success status and backup file location

    Raises:
        HTTPException: If replacement fails
    """
    try:
        from pathlib import Path

        # Validate files exist
        if not Path(request.original_file).exists():
            raise HTTPException(status_code=400, detail=f"Original file not found: {request.original_file}")
        if not Path(request.replacement_file).exists():
            raise HTTPException(status_code=400, detail=f"Replacement file not found: {request.replacement_file}")

        # Execute replacement
        result = orchestrator.execute_replacement(
            request.original_file,
            request.replacement_file,
            request.audiobook_title
        )

        return ExecutionResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


@router.post("/batch-evaluate", response_model=BatchEvaluationResponse)
async def batch_evaluate_replacements(request: BatchEvaluateRequest):
    """
    Evaluate multiple replacement candidates and rank them.

    Evaluates all provided candidates and returns the best match
    based on audio quality metrics (bitrate preference).

    Args:
        original_file: Path to original audio file
        replacement_candidates: List of replacement file paths
        audiobook_title: Title of the audiobook
        author: Author name

    Returns:
        BatchEvaluationResponse with rankings and best candidate

    Raises:
        HTTPException: If batch evaluation fails
    """
    try:
        from pathlib import Path

        # Validate original file exists
        if not Path(request.original_file).exists():
            raise HTTPException(status_code=400, detail=f"Original file not found: {request.original_file}")

        # Validate candidate files exist
        for candidate in request.replacement_candidates:
            if not Path(candidate).exists():
                raise HTTPException(status_code=400, detail=f"Candidate file not found: {candidate}")

        # Batch evaluate
        result = orchestrator.batch_evaluate_replacements(
            request.original_file,
            request.replacement_candidates,
            request.audiobook_title,
            request.author
        )

        return BatchEvaluationResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch evaluation failed: {str(e)}")


@router.get("/health")
async def repair_health():
    """Health check for repair service"""
    return {
        "status": "healthy",
        "service": "repair_orchestrator",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/report/evaluation", response_model=RepairReportResponse)
async def generate_evaluation_report(evaluation: dict = Body(...)):
    """
    Generate a formatted report for an evaluation result.

    Args:
        evaluation: Evaluation result from evaluate_replacement

    Returns:
        RepairReportResponse with formatted report
    """
    try:
        report = reporter.generate_evaluation_report(evaluation)
        return RepairReportResponse(
            report_type="EVALUATION",
            timestamp=datetime.utcnow().isoformat(),
            success=True,
            details=report
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@router.post("/report/execution", response_model=RepairReportResponse)
async def generate_execution_report(execution: dict = Body(...)):
    """
    Generate a formatted report for an execution result.

    Args:
        execution: Execution result from execute_replacement

    Returns:
        RepairReportResponse with formatted report
    """
    try:
        report = reporter.generate_execution_report(execution)
        return RepairReportResponse(
            report_type="EXECUTION",
            timestamp=datetime.utcnow().isoformat(),
            success=report.get("success", False),
            details=report
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@router.post("/report/batch", response_model=RepairReportResponse)
async def generate_batch_report(batch_result: dict = Body(...)):
    """
    Generate a formatted report for a batch evaluation result.

    Args:
        batch_result: Batch evaluation result from batch_evaluate_replacements

    Returns:
        RepairReportResponse with formatted report
    """
    try:
        report = reporter.generate_batch_report(batch_result)
        return RepairReportResponse(
            report_type="BATCH_EVALUATION",
            timestamp=datetime.utcnow().isoformat(),
            success=True,
            details=report
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@router.get("/stats")
async def get_repair_statistics():
    """Get repair operation statistics from operation logger"""
    try:
        # This would be implemented by the operation logger
        # For now, return basic structure
        return {
            "status": "available",
            "note": "Implement repair statistics retrieval"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve statistics: {str(e)}")
