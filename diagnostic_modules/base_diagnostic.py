"""
Base Diagnostic Module
Provides common functionality for all diagnostic modules
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)-8s] %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class DiagnosticResult:
    """Standardized diagnostic result"""
    component: str
    status: str  # "OK", "WARNING", "ERROR", "CRITICAL"
    message: str
    details: Dict[str, Any] = None
    recommendations: List[str] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.details is None:
            self.details = {}
        if self.recommendations is None:
            self.recommendations = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    def is_success(self) -> bool:
        """Check if result indicates success"""
        return self.status in ["OK", "WARNING"]

    def is_error(self) -> bool:
        """Check if result indicates error"""
        return self.status in ["ERROR", "CRITICAL"]


class BaseDiagnostic(ABC):
    """Base class for all diagnostic modules"""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description or f"Diagnostic module for {name}"
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self.results: List[DiagnosticResult] = []

    def log(self, message: str, level: str = "INFO"):
        """Log a message with appropriate level"""
        if level == "ERROR":
            self.logger.error(message)
        elif level == "WARNING":
            self.logger.warning(message)
        elif level == "DEBUG":
            self.logger.debug(message)
        else:
            self.logger.info(message)

    def add_result(self, component: str, status: str, message: str,
                   details: Dict[str, Any] = None, recommendations: List[str] = None):
        """Add a diagnostic result"""
        result = DiagnosticResult(
            component=component,
            status=status,
            message=message,
            details=details or {},
            recommendations=recommendations or []
        )
        self.results.append(result)
        return result

    def get_env_var(self, key: str, default: str = "") -> str:
        """Get environment variable with fallback"""
        return os.getenv(key, default)

    def check_service_running(self, service_name: str, port: int = None) -> bool:
        """Check if a service is running on a port"""
        if not port:
            return False

        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result == 0
        except:
            return False

    def run_http_check(self, url: str, timeout: int = 10) -> Dict[str, Any]:
        """Run HTTP connectivity check"""
        try:
            import requests
            response = requests.get(url, timeout=timeout)
            return {
                "status_code": response.status_code,
                "success": response.status_code < 400,
                "error": None
            }
        except Exception as e:
            return {
                "status_code": None,
                "success": False,
                "error": str(e)
            }

    def run_async_http_check(self, url: str, headers: Dict[str, str] = None,
                           timeout: int = 10) -> Dict[str, Any]:
        """Run async HTTP connectivity check"""
        try:
            import aiohttp
            import asyncio

            async def check():
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers or {}, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                        return {
                            "status_code": resp.status,
                            "success": resp.status < 400,
                            "error": None
                        }

            return asyncio.run(check())
        except Exception as e:
            return {
                "status_code": None,
                "success": False,
                "error": str(e)
            }

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all diagnostic results"""
        total = len(self.results)
        ok_count = len([r for r in self.results if r.status == "OK"])
        warning_count = len([r for r in self.results if r.status == "WARNING"])
        error_count = len([r for r in self.results if r.status == "ERROR"])
        critical_count = len([r for r in self.results if r.status == "CRITICAL"])

        return {
            "module": self.name,
            "description": self.description,
            "total_checks": total,
            "ok": ok_count,
            "warnings": warning_count,
            "errors": error_count,
            "critical": critical_count,
            "success_rate": (ok_count / total * 100) if total > 0 else 0,
            "overall_status": self._calculate_overall_status(),
            "timestamp": datetime.now().isoformat(),
            "results": [r.to_dict() for r in self.results]
        }

    def _calculate_overall_status(self) -> str:
        """Calculate overall status based on results"""
        if any(r.status == "CRITICAL" for r in self.results):
            return "CRITICAL"
        elif any(r.status == "ERROR" for r in self.results):
            return "ERROR"
        elif any(r.status == "WARNING" for r in self.results):
            return "WARNING"
        elif self.results:
            return "OK"
        else:
            return "UNKNOWN"

    @abstractmethod
    def run_diagnostics(self) -> List[DiagnosticResult]:
        """Run the diagnostic checks - must be implemented by subclasses"""
        pass

    def run(self) -> Dict[str, Any]:
        """Run diagnostics and return summary"""
        self.log(f"Starting {self.name} diagnostics", "INFO")
        try:
            self.results = self.run_diagnostics()
            summary = self.get_summary()
            self.log(f"Completed {self.name} diagnostics: {summary['overall_status']}", "INFO")
            return summary
        except Exception as e:
            self.log(f"Error running {self.name} diagnostics: {e}", "ERROR")
            return {
                "module": self.name,
                "description": self.description,
                "error": str(e),
                "overall_status": "ERROR",
                "timestamp": datetime.now().isoformat()
            }