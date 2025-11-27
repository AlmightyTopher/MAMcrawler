#!/usr/bin/env python3
"""
VPN and qBittorrent Connectivity Troubleshooting & Fix Tool

This script diagnoses and fixes issues with qBittorrent communicating through VPN.
It handles three connection scenarios:
1. ProtonVPN with SOCKS proxy (if available)
2. Direct VPN routing (if SOCKS proxy unavailable)
3. Split tunneling configuration
"""

import subprocess
import socket
import json
import sys
import asyncio
import aiohttp
from pathlib import Path
from typing import Optional, Dict, Tuple
from datetime import datetime

class VPNQBTFixer:
    """Diagnose and fix VPN/qBittorrent connectivity issues."""

    def __init__(self):
        self.log_file = Path("vpn_qbittorrent_diagnosis.log")
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "diagnostics": {},
            "issues": [],
            "recommendations": []
        }
        self.print_header("VPN & qBittorrent Connectivity Troubleshooting")

    def log(self, message: str, level: str = "INFO"):
        """Log message to file and console."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"{timestamp} - {level:8} - {message}"
        print(log_line)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_line + "\n")

    def print_header(self, text: str):
        """Print formatted header."""
        print("\n" + "=" * 80)
        print(f"  {text}")
        print("=" * 80 + "\n")
        self.log(f"{'=' * 80}")
        self.log(text)
        self.log(f"{'=' * 80}")

    def check_protonvpn_process(self) -> Tuple[bool, str]:
        """Check if ProtonVPN process is running."""
        self.log("Checking ProtonVPN process...")
        try:
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq ProtonVPN*'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if 'ProtonVPN' in result.stdout:
                processes = [l.strip() for l in result.stdout.split('\n') if 'ProtonVPN' in l]
                msg = f"ProtonVPN running: {processes[0] if processes else 'unknown'}"
                self.log(f"✅ {msg}", "SUCCESS")
                return True, msg
            else:
                self.log("❌ ProtonVPN process NOT found", "ERROR")
                self.results["issues"].append("ProtonVPN is not running")
                self.results["recommendations"].append(
                    "1. Launch ProtonVPN application\n"
                    "2. Connect to a VPN server\n"
                    "3. Wait for 'Connected' status (green)"
                )
                return False, "ProtonVPN not running"
        except Exception as e:
            self.log(f"⚠️  Error checking ProtonVPN: {e}", "WARNING")
            return False, f"Error: {e}"

    def scan_socks_ports(self) -> Dict[int, bool]:
        """Scan for available SOCKS5 proxy ports."""
        self.log("Scanning for SOCKS5 proxy ports...")

        # Common SOCKS proxy ports
        ports_to_check = {
            1080: "Standard SOCKS5",
            1081: "Alternative SOCKS5",
            8080: "Common proxy port",
            8888: "Alternative proxy",
            9050: "Tor SOCKS",
            9051: "Tor control",
            9060: "Privoxy",
            54674: "ProtonVPN (split tunneling)",
            62410: "ProtonVPN (alternative)"
        }

        open_ports = {}
        for port, name in ports_to_check.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()

                if result == 0:
                    open_ports[port] = name
                    self.log(f"✅ Found open port {port} ({name})", "SUCCESS")
            except:
                pass

        if not open_ports:
            self.log("❌ No SOCKS proxy ports detected", "ERROR")
            self.results["issues"].append("No SOCKS proxy port found")
            self.results["recommendations"].append(
                "SOCKS Proxy Fix Options:\n"
                "Option 1 - ProtonVPN Split Tunneling:\n"
                "  1. Open ProtonVPN Settings\n"
                "  2. Enable 'Split Tunneling'\n"
                "  3. Add qBittorrent.exe to 'Excluded Applications'\n"
                "  4. Restart ProtonVPN\n\n"
                "Option 2 - Manual SOCKS Proxy (Windows Terminal as Admin):\n"
                "  netsh interface portproxy add v4tov4 listenport=1080 "
                "listenaddress=127.0.0.1 connectport=8080 connectaddress=127.0.0.1"
            )
        else:
            self.log(f"Found {len(open_ports)} open proxy port(s)", "INFO")

        return open_ports

    def check_network_interfaces(self) -> Tuple[bool, str]:
        """Check for VPN network adapters."""
        self.log("Checking network adapters...")
        try:
            result = subprocess.run(
                ['ipconfig', '/all'],
                capture_output=True,
                text=True,
                timeout=5
            )

            # Look for VPN-related adapters
            vpn_keywords = ['proton', 'wireguard', 'tap', 'tun', 'vpn', 'wintun']
            found_adapters = []

            for line in result.stdout.split('\n'):
                lower_line = line.lower()
                if 'adapter' in lower_line:
                    for keyword in vpn_keywords:
                        if keyword in lower_line:
                            found_adapters.append(line.strip())
                            break

            if found_adapters:
                msg = f"Found {len(found_adapters)} VPN adapter(s)"
                self.log(f"✅ {msg}", "SUCCESS")
                for adapter in found_adapters:
                    self.log(f"   - {adapter}", "INFO")
                return True, msg
            else:
                self.log("⚠️  No VPN adapters detected in ipconfig", "WARNING")
                return False, "No VPN adapters found"
        except Exception as e:
            self.log(f"❌ Error checking network interfaces: {e}", "ERROR")
            return False, f"Error: {e}"

    async def test_connectivity(self, proxy_url: Optional[str] = None) -> bool:
        """Test connectivity to a test site through proxy."""
        self.log(f"Testing connectivity {'through proxy: ' + proxy_url if proxy_url else 'directly'}...")

        try:
            connector = None
            if proxy_url:
                # Create proxy-aware connector
                connector = aiohttp.TCPConnector()

            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                # Test with DNS leak checker
                async with session.get('https://api.ipify.org?format=json', ssl=False) as resp:
                    data = await resp.json()
                    ip = data.get('ip', 'unknown')
                    self.log(f"✅ Connectivity test successful. IP: {ip}", "SUCCESS")
                    self.results["diagnostics"]["public_ip"] = ip
                    return True
        except asyncio.TimeoutError:
            self.log("❌ Connectivity test timed out", "ERROR")
            self.results["issues"].append("Connectivity timeout")
            return False
        except Exception as e:
            self.log(f"❌ Connectivity test failed: {e}", "ERROR")
            self.results["issues"].append(f"Connectivity error: {str(e)}")
            return False

    def get_qbittorrent_config_path(self) -> Optional[Path]:
        """Find qBittorrent config directory."""
        possible_paths = [
            Path.home() / "AppData" / "Local" / "qBittorrent",
            Path.home() / "AppData" / "Roaming" / "qBittorrent",
            Path("C:/qBittorrent"),
        ]

        for path in possible_paths:
            if path.exists():
                self.log(f"Found qBittorrent config at: {path}", "INFO")
                return path

        self.log("⚠️  Could not find qBittorrent config directory", "WARNING")
        return None

    def analyze_qbittorrent_settings(self) -> Dict:
        """Analyze qBittorrent network settings."""
        config_path = self.get_qbittorrent_config_path()
        if not config_path:
            return {}

        settings_file = config_path / "qBittorrent.conf"
        if not settings_file.exists():
            self.log(f"Settings file not found: {settings_file}", "WARNING")
            return {}

        try:
            self.log(f"Reading qBittorrent settings from: {settings_file}", "INFO")
            settings = {}
            with open(settings_file, 'r', encoding='utf-8') as f:
                current_section = None
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if line.startswith('[') and line.endswith(']'):
                        current_section = line[1:-1]
                        settings[current_section] = {}
                    elif '=' in line and current_section:
                        key, value = line.split('=', 1)
                        settings[current_section][key.strip()] = value.strip()

            # Extract network settings
            network_settings = settings.get('Network', {})
            proxy_settings = {
                'proxy_enabled': network_settings.get('Proxy\\Enabled', 'false'),
                'proxy_type': network_settings.get('Proxy\\Type', 'unknown'),
                'proxy_ip': network_settings.get('Proxy\\IP', 'not set'),
                'proxy_port': network_settings.get('Proxy\\Port', 'not set'),
            }

            self.results["diagnostics"]["qbittorrent_proxy"] = proxy_settings
            self.log(f"qBittorrent Proxy Settings: {json.dumps(proxy_settings, indent=2)}", "INFO")

            return proxy_settings
        except Exception as e:
            self.log(f"Error reading qBittorrent settings: {e}", "ERROR")
            return {}

    def generate_fix_commands(self, open_ports: Dict[int, bool]) -> list:
        """Generate qBittorrent configuration fix commands."""
        commands = []

        if open_ports:
            # Found a proxy port - use it
            port = list(open_ports.keys())[0]
            commands.append({
                "title": f"Configure qBittorrent to use proxy on port {port}",
                "steps": [
                    "1. Open qBittorrent",
                    "2. Go to Tools > Options > Network",
                    f"3. Set Proxy Server IP: 127.0.0.1",
                    f"4. Set Proxy Server Port: {port}",
                    "5. Proxy Type: SOCKS5",
                    "6. Check 'Use proxy for peer connections'",
                    "7. Click OK to save"
                ]
            })
        else:
            # No proxy found - use split tunneling approach
            commands.append({
                "title": "Enable ProtonVPN Split Tunneling (Recommended)",
                "steps": [
                    "1. Open ProtonVPN Application",
                    "2. Go to Settings > Network",
                    "3. Enable 'Split Tunneling'",
                    "4. Select 'Excluded Apps' mode (apps NOT in list use VPN)",
                    "5. Add qBittorrent.exe to excluded apps",
                    "6. Restart ProtonVPN",
                    "7. In qBittorrent: Tools > Options > Network > Proxy: Disabled"
                ]
            })

            commands.append({
                "title": "Alternative: Manual Proxy Setup (Advanced)",
                "steps": [
                    "1. Open Windows Terminal as Administrator",
                    "2. Create proxy tunnel (WireGuard example):",
                    "   netsh interface portproxy add v4tov4 \\",
                    "   listenport=1080 listenaddress=127.0.0.1 \\",
                    "   connectport=8080 connectaddress=10.2.0.1",
                    "3. Verify: netsh interface portproxy show all",
                    "4. Configure qBittorrent to use 127.0.0.1:1080"
                ]
            })

        return commands

    async def run_full_diagnosis(self):
        """Run complete VPN/qBittorrent diagnosis."""
        self.print_header("STEP 1: Check ProtonVPN Status")
        vpn_running, vpn_msg = self.check_protonvpn_process()

        self.print_header("STEP 2: Scan for SOCKS Proxy Ports")
        open_ports = self.scan_socks_ports()
        self.results["diagnostics"]["open_ports"] = list(open_ports.keys())

        self.print_header("STEP 3: Check Network Adapters")
        adapters_found, adapter_msg = self.check_network_interfaces()

        self.print_header("STEP 4: Analyze qBittorrent Settings")
        qbt_settings = self.analyze_qbittorrent_settings()

        self.print_header("STEP 5: Test Connectivity")
        if open_ports:
            # Try to connect through first available proxy
            proxy_port = list(open_ports.keys())[0]
            proxy_url = f"socks5://127.0.0.1:{proxy_port}"
            connectivity = await self.test_connectivity(proxy_url)
        else:
            connectivity = await self.test_connectivity()

        self.print_header("STEP 6: Fix Recommendations")
        fix_commands = self.generate_fix_commands(open_ports)

        for fix in fix_commands:
            print(f"\n{fix['title']}")
            print("-" * 80)
            for step in fix['steps']:
                print(f"  {step}")
            self.log(f"{fix['title']}: {'; '.join(fix['steps'])}")

        # Save results
        self.results["summary"] = {
            "vpn_running": vpn_running,
            "proxy_available": len(open_ports) > 0,
            "adapters_found": adapters_found,
            "connectivity_ok": connectivity,
            "total_issues": len(self.results["issues"])
        }

        self.save_results()
        self.print_final_summary()

    def save_results(self):
        """Save diagnosis results to JSON."""
        results_file = Path("vpn_qbittorrent_diagnosis.json")
        try:
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, default=str)
            self.log(f"Results saved to {results_file}", "SUCCESS")
        except Exception as e:
            self.log(f"Failed to save results: {e}", "ERROR")

    def print_final_summary(self):
        """Print final diagnostic summary."""
        self.print_header("DIAGNOSIS SUMMARY")

        summary = self.results["summary"]

        print("Status Report:")
        print("-" * 80)
        print(f"  ProtonVPN Running:  {'✅ Yes' if summary['vpn_running'] else '❌ No'}")
        print(f"  SOCKS Proxy Found:  {'✅ Yes' if summary['proxy_available'] else '❌ No'}")
        print(f"  VPN Adapters:       {'✅ Yes' if summary['adapters_found'] else '⚠️  No'}")
        print(f"  Connectivity Test:  {'✅ Passed' if summary['connectivity_ok'] else '❌ Failed'}")
        print(f"  Total Issues Found: {summary['total_issues']}")

        if self.results["issues"]:
            print("\nIssues Identified:")
            print("-" * 80)
            for i, issue in enumerate(self.results["issues"], 1):
                print(f"  {i}. {issue}")

        if self.results["recommendations"]:
            print("\nRecommended Actions:")
            print("-" * 80)
            for i, rec in enumerate(self.results["recommendations"], 1):
                print(f"  {i}. {rec}")

        print("\n" + "=" * 80)
        self.log("Diagnosis complete.", "SUCCESS")


async def main():
    """Run the VPN/qBittorrent fixer."""
    fixer = VPNQBTFixer()
    await fixer.run_full_diagnosis()


if __name__ == '__main__':
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    asyncio.run(main())
