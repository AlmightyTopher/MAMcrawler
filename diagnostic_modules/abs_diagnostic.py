"""
Audiobookshelf Diagnostic Module
Checks ABS connectivity, database, and configuration
"""

import subprocess
import socket
import json
from pathlib import Path
from typing import List, Dict, Any
from .base_diagnostic import BaseDiagnostic, DiagnosticResult


class ABSDiagnostic(BaseDiagnostic):
    """Audiobookshelf diagnostic module"""

    def __init__(self):
        super().__init__("audiobookshelf", "Audiobookshelf connectivity and configuration diagnostics")

    def run_diagnostics(self) -> List[DiagnosticResult]:
        """Run ABS diagnostics"""
        results = []

        # Check if ABS process is running
        results.append(self._check_process_status())

        # Check port availability
        results.append(self._check_port_availability())

        # Check database location
        results.append(self._check_database_location())

        # Check configuration files
        results.extend(self._check_configuration_files())

        # Check API connectivity
        results.append(self._check_api_connectivity())

        return results

    def _check_process_status(self) -> DiagnosticResult:
        """Check if Audiobookshelf process is running"""
        try:
            result = subprocess.run(
                "tasklist | findstr /i node",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )

            if "node" in result.stdout.lower():
                return self.add_result(
                    "process_status",
                    "OK",
                    "Audiobookshelf process is running",
                    {"processes": result.stdout.strip()}
                )
            else:
                return self.add_result(
                    "process_status",
                    "ERROR",
                    "Audiobookshelf process is not running",
                    recommendations=[
                        "Start Audiobookshelf service",
                        "Check if Node.js is installed and accessible"
                    ]
                )
        except Exception as e:
            return self.add_result(
                "process_status",
                "ERROR",
                f"Failed to check process status: {e}"
            )

    def _check_port_availability(self) -> DiagnosticResult:
        """Check if ABS port is listening"""
        abs_port = int(self.get_env_var('ABS_PORT', '13378'))

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(("localhost", abs_port))
            sock.close()

            if result == 0:
                return self.add_result(
                    "port_availability",
                    "OK",
                    f"Port {abs_port} is listening"
                )
            else:
                return self.add_result(
                    "port_availability",
                    "ERROR",
                    f"Port {abs_port} is not responding",
                    recommendations=[
                        "Check if Audiobookshelf is running",
                        f"Verify ABS_PORT environment variable (currently: {abs_port})"
                    ]
                )
        except Exception as e:
            return self.add_result(
                "port_availability",
                "ERROR",
                f"Failed to check port {abs_port}: {e}"
            )

    def _check_database_location(self) -> DiagnosticResult:
        """Check ABS database location and size"""
        db_search_paths = [
            "C:\\Users\\dogma\\Audiobookshelf",
            "C:\\Users\\dogma\\AppData\\Local\\Audiobookshelf",
            "C:\\Users\\dogma\\AppData\\Roaming\\Audiobookshelf",
            "F:/Audiobookshelf",
            str(Path.home() / "Audiobookshelf"),
        ]

        found_databases = []
        total_size = 0

        for path in db_search_paths:
            p = Path(path)
            if p.exists():
                # Look for database files
                db_files = list(p.glob("**/absdatabase.sqlite")) + \
                          list(p.glob("**/database.sqlite")) + \
                          list(p.glob("**/metadata.sqlite"))

                for db_file in db_files:
                    try:
                        size_mb = db_file.stat().st_size / (1024*1024)
                        found_databases.append({
                            "path": str(db_file),
                            "size_mb": round(size_mb, 1)
                        })
                        total_size += size_mb
                    except:
                        found_databases.append({
                            "path": str(db_file),
                            "size_mb": 0
                        })

        if found_databases:
            return self.add_result(
                "database_location",
                "OK",
                f"Found {len(found_databases)} database file(s), total size: {total_size:.1f} MB",
                {"databases": found_databases}
            )
        else:
            return self.add_result(
                "database_location",
                "WARNING",
                "No database files found in standard locations",
                recommendations=[
                    "Check Audiobookshelf installation",
                    "Verify database path in ABS configuration"
                ]
            )

    def _check_configuration_files(self) -> List[DiagnosticResult]:
        """Check ABS configuration files"""
        results = []
        config_paths = [
            Path("C:\\Users\\dogma\\Audiobookshelf\\config.json"),
            Path("C:\\Users\\dogma\\Audiobookshelf\\settings.json"),
            Path("C:\\Users\\dogma\\AppData\\Local\\Audiobookshelf\\config.json"),
        ]

        found_configs = []
        for config_file in config_paths:
            if config_file.exists():
                found_configs.append(str(config_file))

                # Try to read and check for API key
                try:
                    with open(config_file) as f:
                        config = json.load(f)
                        has_api_key = "apiKey" in config or "token" in config
                        results.append(self.add_result(
                            f"config_{config_file.name}",
                            "OK",
                            f"Configuration file found: {config_file}",
                            {"has_api_key": has_api_key}
                        ))
                except Exception as e:
                    results.append(self.add_result(
                        f"config_{config_file.name}",
                        "WARNING",
                        f"Configuration file exists but cannot be read: {e}"
                    ))

        if not found_configs:
            results.append(self.add_result(
                "configuration_files",
                "WARNING",
                "No configuration files found",
                recommendations=[
                    "Check Audiobookshelf installation",
                    "Generate API token in ABS admin panel"
                ]
            ))

        return results

    def _check_api_connectivity(self) -> DiagnosticResult:
        """Check ABS API connectivity"""
        abs_url = self.get_env_var('ABS_URL', 'http://localhost:13378')
        abs_token = self.get_env_var('ABS_TOKEN')

        if not abs_token:
            return self.add_result(
                "api_connectivity",
                "ERROR",
                "ABS_TOKEN environment variable not set",
                recommendations=[
                    "Set ABS_TOKEN in .env file",
                    "Generate API token in Audiobookshelf admin panel"
                ]
            )

        # Test API connectivity
        api_check = self.run_async_http_check(
            f"{abs_url}/api/libraries",
            headers={'Authorization': f'Bearer {abs_token}'},
            timeout=10
        )

        if api_check["success"]:
            return self.add_result(
                "api_connectivity",
                "OK",
                "ABS API is accessible",
                {"libraries_endpoint": api_check["status_code"]}
            )
        else:
            return self.add_result(
                "api_connectivity",
                "ERROR",
                f"ABS API not accessible: {api_check['error']}",
                recommendations=[
                    "Check ABS_URL and ABS_TOKEN in .env",
                    "Verify Audiobookshelf is running",
                    "Check API token permissions"
                ]
            )