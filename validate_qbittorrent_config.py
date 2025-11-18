#!/usr/bin/env python3
"""
qBittorrent Configuration Validator for MAM
Validates qBittorrent settings against MAM best practices
"""

import os
import sys
import json
import requests
from typing import Dict, List, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set UTF-8 for Windows
if sys.platform == 'win32':
    os.system('chcp 65001 >nul')
    # Force UTF-8 encoding for stdout
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None


class QBittorrentConfigValidator:
    """Validate qBittorrent configuration against MAM best practices."""

    def __init__(self):
        self.qb_host = os.getenv('QBITTORRENT_HOST', 'localhost')
        self.qb_port = os.getenv('QBITTORRENT_PORT', '8080')
        self.qb_username = os.getenv('QBITTORRENT_USERNAME', 'admin')
        self.qb_password = os.getenv('QBITTORRENT_PASSWORD')
        self.base_url = f"http://{self.qb_host}:{self.qb_port}/api/v2"

        self.session = None
        self.preferences = None

        # Load MAM automation rules
        with open('mam_automation_rules.json', 'r') as f:
            self.rules = json.load(f)['qbittorrent_settings']

    def connect(self) -> bool:
        """Connect to qBittorrent Web UI."""
        try:
            self.session = requests.Session()
            login_data = {
                'username': self.qb_username,
                'password': self.qb_password
            }
            response = self.session.post(
                f"{self.base_url}/auth/login",
                data=login_data,
                timeout=10
            )

            if response.status_code == 200 and response.text == "Ok.":
                return True
            else:
                print(f"❌ Failed to connect: {response.text}")
                return False

        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to qBittorrent at {self.base_url}")
            print("   Make sure qBittorrent is running and Web UI is enabled")
            return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False

    def get_preferences(self) -> Dict:
        """Get current qBittorrent preferences."""
        try:
            response = self.session.get(
                f"{self.base_url}/app/preferences",
                timeout=10
            )
            self.preferences = response.json()
            return self.preferences
        except Exception as e:
            print(f"❌ Failed to get preferences: {e}")
            return {}

    def check_port_configuration(self) -> Tuple[str, str]:
        """Check if port is within recommended range."""
        listen_port = self.preferences.get('listen_port', 0)

        min_port = self.rules['port_configuration']['recommended_range_min']
        max_port = self.rules['port_configuration']['recommended_range_max']

        if min_port <= listen_port <= max_port:
            return "✓", f"Port {listen_port} is within recommended range ({min_port}-{max_port})"
        else:
            return "⚠", f"Port {listen_port} is OUTSIDE recommended range ({min_port}-{max_port})"

    def check_upload_limits(self) -> Tuple[str, str]:
        """Check upload speed limits."""
        upload_limit = self.preferences.get('up_limit', -1)

        if upload_limit == -1:
            return "⚠", "Upload limit: UNLIMITED (recommend capping at 80% of max speed)"
        elif upload_limit > 0:
            upload_mbps = upload_limit / 1024 / 1024
            return "✓", f"Upload limit: {upload_mbps:.2f} MB/s (verify it's 80% of max)"
        else:
            return "✓", "Upload limit: Configured"

    def check_connection_settings(self) -> List[Tuple[str, str]]:
        """Check connection settings."""
        results = []

        # Max connections
        max_connec = self.preferences.get('max_connec', 0)
        recommended_min = self.rules['connection_settings']['global_max_connections']

        if max_connec >= recommended_min:
            results.append(("✓", f"Global max connections: {max_connec} (≥{recommended_min} recommended)"))
        else:
            results.append(("⚠", f"Global max connections: {max_connec} (recommend ≥{recommended_min} for large collections)"))

        # UPnP/NAT-PMP
        upnp = self.preferences.get('upnp', False)
        if upnp:
            results.append(("✓", "UPnP/NAT-PMP: ENABLED"))
        else:
            results.append(("ℹ", "UPnP/NAT-PMP: DISABLED (enable for automatic port forwarding)"))

        # Port forwarding
        results.append(("ℹ", "Manual port verification recommended at canyouseeme.org"))

        return results

    def check_anonymous_mode(self) -> Tuple[str, str]:
        """Check if anonymous mode is disabled (CRITICAL for MAM)."""
        anonymous_mode = self.preferences.get('anonymous_mode', False)

        if not anonymous_mode:
            return "✓", "Anonymous mode: DISABLED (correct for MAM)"
        else:
            return "✗", "Anonymous mode: ENABLED (MUST DISABLE - causes MAM rejection)"

    def check_queuing_settings(self) -> Tuple[str, str]:
        """Check torrent queueing settings."""
        queueing_enabled = self.preferences.get('queueing_enabled', True)
        max_active_torrents = self.preferences.get('max_active_torrents', 0)

        if not queueing_enabled:
            return "✓", "Torrent queuing: DISABLED (unlimited seeding - good if bandwidth allows)"
        else:
            return "ℹ", f"Torrent queuing: ENABLED (max {max_active_torrents} active - fine for limited bandwidth)"

    def check_disk_io(self) -> List[Tuple[str, str]]:
        """Check disk I/O settings."""
        results = []

        # Disk cache
        disk_cache = self.preferences.get('disk_cache', 0)
        disk_cache_mb = disk_cache // 1024
        results.append(("ℹ", f"Disk cache: {disk_cache_mb} MB"))

        # Async I/O threads
        async_io_threads = self.preferences.get('async_io_threads', 0)
        results.append(("ℹ", f"Async I/O threads: {async_io_threads}"))

        return results

    def check_vpn_considerations(self) -> List[Tuple[str, str]]:
        """Check VPN-related settings and recommendations."""
        results = []

        # Check if using VPN (can't detect directly, so just recommendations)
        results.append(("ℹ", "VPN Integration Recommendations:"))
        results.append(("ℹ", "  - If using VPN, ensure port forwarding is enabled in VPN"))
        results.append(("ℹ", "  - Use ASN-locked sessions in MAM (not IP-locked)"))
        results.append(("ℹ", "  - Consider Gluetun Docker for automatic port management"))
        results.append(("ℹ", "  - ProtonVPN/PIA/Windscribe recommended for port forwarding"))

        return results

    def run_validation(self):
        """Run all validation checks."""
        print("=" * 70)
        print("qBITTORRENT CONFIGURATION VALIDATOR FOR MAM")
        print("=" * 70)
        print()

        # Connect to qBittorrent
        print("🔌 Connecting to qBittorrent...")
        if not self.connect():
            print("\n❌ VALIDATION FAILED - Cannot connect to qBittorrent")
            print("   Check .env file for correct QBITTORRENT_HOST, PORT, USERNAME, PASSWORD")
            return False

        print("✓ Connected successfully\n")

        # Get preferences
        print("⚙️  Fetching preferences...")
        if not self.get_preferences():
            print("❌ Failed to retrieve preferences")
            return False

        print("✓ Preferences retrieved\n")
        print("-" * 70)
        print("CONFIGURATION CHECKS")
        print("-" * 70)
        print()

        # Run checks
        checks_passed = 0
        checks_warning = 0
        checks_failed = 0
        checks_info = 0

        # Port configuration
        status, msg = self.check_port_configuration()
        print(f"{status} {msg}")
        if status == "✓": checks_passed += 1
        elif status == "⚠": checks_warning += 1
        elif status == "✗": checks_failed += 1
        else: checks_info += 1

        # Upload limits
        status, msg = self.check_upload_limits()
        print(f"{status} {msg}")
        if status == "✓": checks_passed += 1
        elif status == "⚠": checks_warning += 1
        elif status == "✗": checks_failed += 1
        else: checks_info += 1

        # Anonymous mode (CRITICAL)
        print()
        status, msg = self.check_anonymous_mode()
        print(f"{status} {msg}")
        if status == "✓": checks_passed += 1
        elif status == "⚠": checks_warning += 1
        elif status == "✗": checks_failed += 1
        else: checks_info += 1

        # Connection settings
        print()
        for status, msg in self.check_connection_settings():
            print(f"{status} {msg}")
            if status == "✓": checks_passed += 1
            elif status == "⚠": checks_warning += 1
            elif status == "✗": checks_failed += 1
            else: checks_info += 1

        # Queuing
        print()
        status, msg = self.check_queuing_settings()
        print(f"{status} {msg}")
        if status == "✓": checks_passed += 1
        elif status == "⚠": checks_warning += 1
        elif status == "✗": checks_failed += 1
        else: checks_info += 1

        # Disk I/O
        print()
        for status, msg in self.check_disk_io():
            print(f"{status} {msg}")
            if status == "✓": checks_passed += 1
            elif status == "⚠": checks_warning += 1
            elif status == "✗": checks_failed += 1
            else: checks_info += 1

        # VPN considerations
        print()
        for status, msg in self.check_vpn_considerations():
            print(f"{status} {msg}")
            if status == "✓": checks_passed += 1
            elif status == "⚠": checks_warning += 1
            elif status == "✗": checks_failed += 1
            else: checks_info += 1

        # Summary
        print()
        print("=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        print(f"✓ Passed:   {checks_passed}")
        print(f"⚠ Warnings: {checks_warning}")
        print(f"✗ Failed:   {checks_failed}")
        print(f"ℹ Info:     {checks_info}")
        print()

        if checks_failed > 0:
            print("STATUS: ✗ CRITICAL ISSUES FOUND")
            print("   Fix failed checks before using with MAM")
        elif checks_warning > 0:
            print("STATUS: ⚠ GOOD - Some optimizations recommended")
        else:
            print("STATUS: ✓ EXCELLENT - All checks passed")

        print("=" * 70)

        return checks_failed == 0


def main():
    """Main entry point."""
    validator = QBittorrentConfigValidator()
    success = validator.run_validation()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
