"""
Prowlarr Diagnostic Module
Checks Prowlarr connectivity, indexers, and search functionality
"""

from typing import List, Dict, Any
from .base_diagnostic import BaseDiagnostic, DiagnosticResult


class ProwlarrDiagnostic(BaseDiagnostic):
    """Prowlarr diagnostic module"""

    def __init__(self):
        super().__init__("prowlarr", "Prowlarr indexer and search diagnostics")

    def run_diagnostics(self) -> List[DiagnosticResult]:
        """Run Prowlarr diagnostics"""
        results = []

        # Check Prowlarr connectivity
        results.append(self._check_connectivity())

        # Check system status
        results.append(self._check_system_status())

        # Check indexers
        results.append(self._check_indexers())

        # Test search functionality
        results.append(self._test_search())

        return results

    def _check_connectivity(self) -> DiagnosticResult:
        """Check Prowlarr API connectivity"""
        prowlarr_url = self.get_env_var('PROWLARR_URL', 'http://localhost:9696')
        prowlarr_key = self.get_env_var('PROWLARR_API_KEY')

        if not prowlarr_key:
            return self.add_result(
                "connectivity",
                "ERROR",
                "PROWLARR_API_KEY not configured",
                recommendations=["Set PROWLARR_API_KEY in .env file"]
            )

        # Test health endpoint
        health_url = f"{prowlarr_url}/api/v1/health"
        health_check = self.run_async_http_check(
            health_url,
            headers={'X-Api-Key': prowlarr_key},
            timeout=10
        )

        if health_check["success"]:
            return self.add_result(
                "connectivity",
                "OK",
                "Prowlarr API is accessible"
            )
        else:
            return self.add_result(
                "connectivity",
                "ERROR",
                f"Prowlarr API not accessible: {health_check['error']}",
                recommendations=[
                    "Check if Prowlarr is running",
                    "Verify PROWLARR_URL and PROWLARR_API_KEY",
                    "Check Prowlarr logs"
                ]
            )

    def _check_system_status(self) -> DiagnosticResult:
        """Check Prowlarr system status"""
        prowlarr_url = self.get_env_var('PROWLARR_URL', 'http://localhost:9696')
        prowlarr_key = self.get_env_var('PROWLARR_API_KEY')

        status_url = f"{prowlarr_url}/api/v1/system/status"
        status_check = self.run_async_http_check(
            status_url,
            headers={'X-Api-Key': prowlarr_key},
            timeout=10
        )

        if status_check["success"]:
            return self.add_result(
                "system_status",
                "OK",
                "Prowlarr system status retrieved"
            )
        else:
            return self.add_result(
                "system_status",
                "WARNING",
                f"Could not get system status: {status_check['error']}",
                recommendations=["Check Prowlarr system status manually"]
            )

    def _check_indexers(self) -> DiagnosticResult:
        """Check configured indexers"""
        prowlarr_url = self.get_env_var('PROWLARR_URL', 'http://localhost:9696')
        prowlarr_key = self.get_env_var('PROWLARR_API_KEY')

        indexers_url = f"{prowlarr_url}/api/v1/indexer"
        indexers_check = self.run_async_http_check(
            indexers_url,
            headers={'X-Api-Key': prowlarr_key},
            timeout=10
        )

        if indexers_check["success"]:
            # This would need actual JSON parsing in real implementation
            return self.add_result(
                "indexers",
                "OK",
                "Indexer configuration accessible"
            )
        else:
            return self.add_result(
                "indexers",
                "WARNING",
                f"Could not check indexers: {indexers_check['error']}",
                recommendations=[
                    "Check indexer configuration in Prowlarr UI",
                    "Ensure indexers are enabled and configured"
                ]
            )

    def _test_search(self) -> DiagnosticResult:
        """Test search functionality"""
        prowlarr_url = self.get_env_var('PROWLARR_URL', 'http://localhost:9696')
        prowlarr_key = self.get_env_var('PROWLARR_API_KEY')

        # Test basic search
        search_url = f"{prowlarr_url}/api/v1/search?query=test&type=search"
        search_check = self.run_async_http_check(
            search_url,
            headers={'X-Api-Key': prowlarr_key},
            timeout=15
        )

        if search_check["success"]:
            return self.add_result(
                "search_test",
                "OK",
                "Search functionality working"
            )
        else:
            return self.add_result(
                "search_test",
                "WARNING",
                f"Search test failed: {search_check['error']}",
                recommendations=[
                    "Test search manually in Prowlarr UI",
                    "Check indexer configurations",
                    "Verify API key permissions"
                ]
            )