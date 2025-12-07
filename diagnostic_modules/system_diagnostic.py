"""
System Diagnostic Module
Overall system health and configuration checks
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from .base_diagnostic import BaseDiagnostic, DiagnosticResult


class SystemDiagnostic(BaseDiagnostic):
    """System diagnostic module"""

    def __init__(self):
        super().__init__("system", "Overall system health and configuration diagnostics")

    def run_diagnostics(self) -> List[DiagnosticResult]:
        """Run system diagnostics"""
        results = []

        # Check environment configuration
        results.append(self._check_environment_config())

        # Check Python environment
        results.append(self._check_python_environment())

        # Check required directories
        results.append(self._check_required_directories())

        # Check log files
        results.append(self._check_log_files())

        # Overall system assessment
        results.append(self._assess_system_health())

        return results

    def _check_environment_config(self) -> DiagnosticResult:
        """Check environment configuration"""
        required_vars = [
            'ABS_URL', 'ABS_TOKEN',
            'QBITTORRENT_URL', 'QBITTORRENT_USERNAME', 'QBITTORRENT_PASSWORD',
            'PROWLARR_URL', 'PROWLARR_API_KEY'
        ]

        optional_vars = [
            'MAM_USERNAME', 'MAM_PASSWORD'
        ]

        configured_required = []
        missing_required = []
        configured_optional = []

        for var in required_vars:
            if self.get_env_var(var):
                configured_required.append(var)
            else:
                missing_required.append(var)

        for var in optional_vars:
            if self.get_env_var(var):
                configured_optional.append(var)

        if missing_required:
            return self.add_result(
                "environment_config",
                "ERROR",
                f"Missing {len(missing_required)} required environment variables",
                {
                    "missing_required": missing_required,
                    "configured_required": configured_required,
                    "configured_optional": configured_optional
                },
                recommendations=[
                    "Set missing environment variables in .env file",
                    "Check .env.example for required variables"
                ]
            )
        else:
            return self.add_result(
                "environment_config",
                "OK",
                f"All {len(configured_required)} required environment variables configured",
                {
                    "configured_required": configured_required,
                    "configured_optional": configured_optional
                }
            )

    def _check_python_environment(self) -> DiagnosticResult:
        """Check Python environment"""
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        # Check for virtual environment
        in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

        venv_path = None
        if in_venv:
            venv_path = sys.prefix

        return self.add_result(
            "python_environment",
            "OK",
            f"Python {python_version} {'(virtual environment)' if in_venv else '(system)'}",
            {
                "version": python_version,
                "in_virtual_env": in_venv,
                "venv_path": venv_path,
                "platform": sys.platform
            },
            recommendations=["Consider using virtual environment"] if not in_venv else []
        )

    def _check_required_directories(self) -> DiagnosticResult:
        """Check for required directories"""
        required_dirs = [
            "diagnostic_modules",
            "diagnostic_reports",
            "backend",
            "ABS"
        ]

        existing_dirs = []
        missing_dirs = []

        for dir_name in required_dirs:
            if Path(dir_name).exists():
                existing_dirs.append(dir_name)
            else:
                missing_dirs.append(dir_name)

        if missing_dirs:
            return self.add_result(
                "required_directories",
                "WARNING",
                f"Missing {len(missing_dirs)} required directories",
                {
                    "existing": existing_dirs,
                    "missing": missing_dirs
                },
                recommendations=[
                    "Create missing directories",
                    "Check project structure"
                ]
            )
        else:
            return self.add_result(
                "required_directories",
                "OK",
                f"All {len(existing_dirs)} required directories exist",
                {"directories": existing_dirs}
            )

    def _check_log_files(self) -> DiagnosticResult:
        """Check for log files and their status"""
        log_files = [
            "real_workflow_execution.log",
            "comprehensive_monitor.log",
            "execution_log.txt",
            "diagnostic.log"
        ]

        existing_logs = []
        for log_file in log_files:
            if Path(log_file).exists():
                existing_logs.append(log_file)

        if existing_logs:
            return self.add_result(
                "log_files",
                "OK",
                f"Found {len(existing_logs)} log files",
                {"log_files": existing_logs}
            )
        else:
            return self.add_result(
                "log_files",
                "INFO",
                "No log files found - system may not have run workflows yet",
                recommendations=[
                    "Run diagnostic system to generate logs",
                    "Execute workflow scripts to create activity logs"
                ]
            )

    def _assess_system_health(self) -> DiagnosticResult:
        """Overall system health assessment"""
        # This would analyze results from other diagnostics
        # For now, provide a basic assessment

        issues = []

        # Check if we're in a proper Python environment
        if not (hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)):
            issues.append("Not running in virtual environment")

        # Check basic environment
        if not self.get_env_var('ABS_URL'):
            issues.append("ABS_URL not configured")

        if not self.get_env_var('QBITTORRENT_URL'):
            issues.append("qBittorrent not configured")

        if issues:
            return self.add_result(
                "system_health",
                "WARNING",
                f"System health assessment: {len(issues)} issues found",
                {"issues": issues},
                recommendations=[
                    "Address configuration issues",
                    "Set up virtual environment",
                    "Configure all required services"
                ]
            )
        else:
            return self.add_result(
                "system_health",
                "OK",
                "System appears properly configured",
                recommendations=[
                    "Run full diagnostic suite",
                    "Monitor system regularly"
                ]
            )