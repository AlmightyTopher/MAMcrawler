"""
VPN Diagnostic Module
Checks VPN connectivity, processes, and proxy configuration
"""

import subprocess
import socket
import sys
from typing import List, Dict, Any, Tuple
from .base_diagnostic import BaseDiagnostic, DiagnosticResult


class VPNDiagnostic(BaseDiagnostic):
    """VPN diagnostic module"""

    def __init__(self):
        super().__init__("vpn", "VPN connectivity and proxy configuration diagnostics")

    def run_diagnostics(self) -> List[DiagnosticResult]:
        """Run VPN diagnostics"""
        results = []

        # Check VPN processes
        results.append(self._check_vpn_processes())

        # Check network adapters
        results.append(self._check_network_adapters())

        # Check SOCKS proxy ports
        results.extend(self._check_proxy_ports())

        # Overall assessment
        results.append(self._assess_vpn_status())

        return results

    def _check_vpn_processes(self) -> DiagnosticResult:
        """Check for running VPN processes"""
        try:
            if sys.platform == 'win32':
                result = subprocess.run(
                    ['tasklist', '/FI', 'IMAGENAME eq ProtonVPN*'],
                    capture_output=True, text=True, timeout=5
                )
                lines = [l for l in result.stdout.split('\n') if 'ProtonVPN' in l]
            else:
                # Linux/macOS
                result = subprocess.run(
                    ['pgrep', '-f', 'protonvpn'],
                    capture_output=True, text=True, timeout=5
                )
                lines = result.stdout.strip().split('\n') if result.stdout.strip() else []

            if lines and lines[0]:
                return self.add_result(
                    "vpn_processes",
                    "OK",
                    f"Found {len(lines)} ProtonVPN process(es) running",
                    {"processes": lines}
                )
            else:
                return self.add_result(
                    "vpn_processes",
                    "ERROR",
                    "No ProtonVPN processes found",
                    recommendations=[
                        "Start ProtonVPN application",
                        "Connect to a VPN server",
                        "Check if ProtonVPN is installed"
                    ]
                )
        except Exception as e:
            return self.add_result(
                "vpn_processes",
                "ERROR",
                f"Failed to check VPN processes: {e}"
            )

    def _check_network_adapters(self) -> DiagnosticResult:
        """Check for VPN network adapters"""
        try:
            if sys.platform == 'win32':
                result = subprocess.run(['ipconfig'], capture_output=True, text=True, timeout=5)
                output = result.stdout
            else:
                result = subprocess.run(['ip', 'addr'], capture_output=True, text=True, timeout=5)
                output = result.stdout

            # Look for VPN-related adapters
            vpn_indicators = ['proton', 'wireguard', 'tap', 'vpn', 'tun']
            found_adapters = []

            lines = output.split('\n')
            current_adapter = None

            for line in lines:
                line_lower = line.lower()
                if 'adapter' in line_lower or 'interface' in line_lower:
                    for indicator in vpn_indicators:
                        if indicator in line_lower:
                            current_adapter = line.strip()
                            found_adapters.append(current_adapter)
                            break
                elif current_adapter and ('ipv4' in line_lower or 'inet ' in line_lower):
                    # Found IP for VPN adapter
                    found_adapters[-1] += f" - {line.strip()}"

            if found_adapters:
                return self.add_result(
                    "network_adapters",
                    "OK",
                    f"Found {len(found_adapters)} VPN network adapter(s)",
                    {"adapters": found_adapters}
                )
            else:
                return self.add_result(
                    "network_adapters",
                    "WARNING",
                    "No VPN network adapters detected",
                    recommendations=[
                        "Connect to a VPN server in ProtonVPN",
                        "Enable Split Tunneling if needed",
                        "Check VPN connection status"
                    ]
                )
        except Exception as e:
            return self.add_result(
                "network_adapters",
                "ERROR",
                f"Failed to check network adapters: {e}"
            )

    def _check_proxy_ports(self) -> List[DiagnosticResult]:
        """Check for open SOCKS proxy ports"""
        results = []

        # Extended port list for common proxy ports
        proxy_ports = list(range(1080, 1090)) + list(range(8080, 8090)) + \
                     list(range(9050, 9060)) + [54674, 62410, 3128, 8888]

        open_ports = []
        for port in proxy_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.3)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                if result == 0:
                    open_ports.append(port)
            except:
                pass

        if open_ports:
            results.append(self.add_result(
                "proxy_ports",
                "OK",
                f"Found {len(open_ports)} open proxy port(s): {', '.join(map(str, open_ports))}",
                {"open_ports": open_ports}
            ))

            # Test proxy functionality
            for port in open_ports[:3]:  # Test first 3 ports
                proxy_test = self._test_proxy_functionality(port)
                results.append(proxy_test)
        else:
            results.append(self.add_result(
                "proxy_ports",
                "WARNING",
                "No proxy ports detected",
                recommendations=[
                    "Enable Split Tunneling in ProtonVPN",
                    "Add Python to Included Apps in Split Tunneling",
                    "Restart ProtonVPN after enabling Split Tunneling"
                ]
            ))

        return results

    def _test_proxy_functionality(self, port: int) -> DiagnosticResult:
        """Test if proxy port is functional"""
        try:
            import socks
            import socket as sock_module

            # Create a socket through the proxy
            sock = socks.socksocket()
            sock.set_proxy(socks.SOCKS5, "127.0.0.1", port)
            sock.settimeout(5)

            # Try to connect to a test service
            sock.connect(("httpbin.org", 80))
            sock.close()

            return self.add_result(
                f"proxy_test_{port}",
                "OK",
                f"Proxy port {port} is functional"
            )
        except Exception as e:
            return self.add_result(
                f"proxy_test_{port}",
                "WARNING",
                f"Proxy port {port} detected but not functional: {e}",
                recommendations=[
                    "Verify Split Tunneling configuration",
                    "Restart ProtonVPN",
                    "Check firewall settings"
                ]
            )

    def _assess_vpn_status(self) -> DiagnosticResult:
        """Provide overall VPN status assessment"""
        # Get current results to assess overall status
        processes_ok = any(r.component == "vpn_processes" and r.status == "OK" for r in self.results)
        adapters_ok = any(r.component == "network_adapters" and r.status == "OK" for r in self.results)
        proxies_ok = any(r.component.startswith("proxy_ports") and r.status == "OK" for r in self.results)

        if processes_ok and adapters_ok:
            if proxies_ok:
                status = "OK"
                message = "VPN is connected and proxy is configured"
            else:
                status = "WARNING"
                message = "VPN is connected but proxy configuration may be incomplete"
        elif processes_ok:
            status = "WARNING"
            message = "VPN process running but connection may not be established"
        else:
            status = "ERROR"
            message = "VPN is not connected"

        recommendations = []
        if status != "OK":
            recommendations = [
                "Open ProtonVPN and connect to a server",
                "Enable Split Tunneling in Settings > Advanced",
                "Add Python executable to Included Apps",
                "Restart ProtonVPN after configuration changes"
            ]

        return self.add_result(
            "overall_vpn_status",
            status,
            message,
            recommendations=recommendations
        )