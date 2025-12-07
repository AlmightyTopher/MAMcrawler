"""
Workflow Diagnostic Module
Checks workflow execution status and progress monitoring
"""

from pathlib import Path
from typing import List, Dict, Any
from .base_diagnostic import BaseDiagnostic, DiagnosticResult


class WorkflowDiagnostic(BaseDiagnostic):
    """Workflow diagnostic module"""

    def __init__(self):
        super().__init__("workflow", "Workflow execution and progress diagnostics")

    def run_diagnostics(self) -> List[DiagnosticResult]:
        """Run workflow diagnostics"""
        results = []

        # Check workflow log files
        results.append(self._check_workflow_logs())

        # Check workflow progress
        results.append(self._check_workflow_progress())

        # Check for errors in recent logs
        results.append(self._check_recent_errors())

        return results

    def _check_workflow_logs(self) -> DiagnosticResult:
        """Check for workflow log files"""
        log_files = [
            "real_workflow_execution.log",
            "comprehensive_monitor.log",
            "execution_log.txt"
        ]

        found_logs = []
        for log_file in log_files:
            if Path(log_file).exists():
                found_logs.append(log_file)

        if found_logs:
            return self.add_result(
                "workflow_logs",
                "OK",
                f"Found {len(found_logs)} workflow log files",
                {"log_files": found_logs}
            )
        else:
            return self.add_result(
                "workflow_logs",
                "WARNING",
                "No workflow log files found",
                recommendations=[
                    "Run workflow scripts to generate logs",
                    "Check if workflows have been executed"
                ]
            )

    def _check_workflow_progress(self) -> DiagnosticResult:
        """Check workflow execution progress"""
        log_file = Path("real_workflow_execution.log")

        if not log_file.exists():
            return self.add_result(
                "workflow_progress",
                "WARNING",
                "Workflow execution log not found",
                recommendations=["Run main workflow scripts"]
            )

        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()

            if not lines:
                return self.add_result(
                    "workflow_progress",
                    "WARNING",
                    "Workflow log is empty",
                    recommendations=["Start workflow execution"]
                )

            # Analyze recent activity
            recent_lines = lines[-20:]  # Last 20 lines
            last_line = lines[-1].strip() if lines else ""

            # Count different types of log entries
            error_count = sum(1 for line in recent_lines if '[ERROR]' in line or '[FAIL]' in line)
            success_count = sum(1 for line in recent_lines if '[SUCCESS]' in line or '[OK]' in line)

            status = "OK" if error_count == 0 else "WARNING"

            return self.add_result(
                "workflow_progress",
                status,
                f"Workflow active - {len(lines)} total log entries",
                {
                    "total_lines": len(lines),
                    "recent_errors": error_count,
                    "recent_successes": success_count,
                    "last_activity": last_line[:100]
                },
                recommendations=["Review workflow logs for errors"] if error_count > 0 else []
            )

        except Exception as e:
            return self.add_result(
                "workflow_progress",
                "ERROR",
                f"Failed to read workflow log: {e}"
            )

    def _check_recent_errors(self) -> DiagnosticResult:
        """Check for recent errors in workflow logs"""
        log_files = [
            "real_workflow_execution.log",
            "comprehensive_monitor.log",
            "execution_log.txt"
        ]

        all_errors = []

        for log_file in log_files:
            log_path = Path(log_file)
            if log_path.exists():
                try:
                    with open(log_path, 'r') as f:
                        lines = f.readlines()

                    # Get last 100 lines
                    recent_lines = lines[-100:] if len(lines) > 100 else lines

                    errors = [line.strip() for line in recent_lines
                             if any(err in line.upper() for err in ['ERROR', 'FAIL', 'EXCEPTION', 'CRITICAL'])]

                    if errors:
                        all_errors.extend(errors[:5])  # Limit to 5 per file

                except Exception:
                    continue

        if all_errors:
            return self.add_result(
                "recent_errors",
                "WARNING",
                f"Found {len(all_errors)} recent errors in workflow logs",
                {"errors": all_errors},
                recommendations=[
                    "Review workflow logs for error details",
                    "Check system status and fix issues",
                    "Restart failed workflows if needed"
                ]
            )
        else:
            return self.add_result(
                "recent_errors",
                "OK",
                "No recent errors found in workflow logs"
            )