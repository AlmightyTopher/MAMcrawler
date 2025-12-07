"""
MAM (MyAnonamouse) Diagnostic Module
Checks MAM connectivity, account status, and VIP status
"""

from typing import List, Dict, Any
from .base_diagnostic import BaseDiagnostic, DiagnosticResult


class MAMDiagnostic(BaseDiagnostic):
    """MAM diagnostic module"""

    def __init__(self):
        super().__init__("mam", "MyAnonamouse account and connectivity diagnostics")

    def run_diagnostics(self) -> List[DiagnosticResult]:
        """Run MAM diagnostics"""
        results = []

        # Check MAM credentials configuration
        results.append(self._check_credentials())

        # Check MAM connectivity
        results.append(self._check_connectivity())

        # Check account status (if credentials available)
        results.append(self._check_account_status())

        # Check VIP status
        results.append(self._check_vip_status())

        return results

    def _check_credentials(self) -> DiagnosticResult:
        """Check if MAM credentials are configured"""
        mam_user = self.get_env_var('MAM_USERNAME')
        mam_pass = self.get_env_var('MAM_PASSWORD')

        if not mam_user or not mam_pass:
            return self.add_result(
                "credentials",
                "ERROR",
                "MAM credentials not configured",
                recommendations=[
                    "Set MAM_USERNAME and MAM_PASSWORD in .env file",
                    "Obtain credentials from MyAnonamouse.net"
                ]
            )
        else:
            return self.add_result(
                "credentials",
                "OK",
                "MAM credentials configured",
                {"username": mam_user}
            )

    def _check_connectivity(self) -> DiagnosticResult:
        """Check MAM website connectivity"""
        # Test basic connectivity to MAM
        connectivity_check = self.run_http_check("https://www.myanonamouse.net/", timeout=10)

        if connectivity_check["success"]:
            return self.add_result(
                "connectivity",
                "OK",
                "MAM website is accessible"
            )
        else:
            return self.add_result(
                "connectivity",
                "ERROR",
                f"MAM website not accessible: {connectivity_check['error']}",
                recommendations=[
                    "Check internet connection",
                    "Verify MAM website is not blocked",
                    "Try accessing https://www.myanonamouse.net/ manually"
                ]
            )

    def _check_account_status(self) -> DiagnosticResult:
        """Check MAM account status"""
        mam_user = self.get_env_var('MAM_USERNAME')
        mam_pass = self.get_env_var('MAM_PASSWORD')

        if not mam_user or not mam_pass:
            return self.add_result(
                "account_status",
                "ERROR",
                "Cannot check account status - credentials not configured"
            )

        # For MAM, we'd need to implement login check
        # This is a placeholder - actual implementation would require stealth browsing
        return self.add_result(
            "account_status",
            "WARNING",
            "Account status check requires stealth browser implementation",
            recommendations=[
                "Use stealth crawler scripts to verify login",
                "Check MAM account manually at https://www.myanonamouse.net/"
            ]
        )

    def _check_vip_status(self) -> DiagnosticResult:
        """Check MAM VIP status"""
        # VIP status checking requires stealth browsing and login
        # This is a placeholder for the actual implementation
        return self.add_result(
            "vip_status",
            "WARNING",
            "VIP status check requires stealth browser implementation",
            recommendations=[
                "Use VIP status manager script to check VIP status",
                "Check VIP status manually on MAM website",
                "Ensure sufficient bonus points for VIP renewal"
            ]
        )