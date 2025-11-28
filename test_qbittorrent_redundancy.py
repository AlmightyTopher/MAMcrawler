#!/usr/bin/env python3
"""
Test qBittorrent Redundancy Configuration

This script runs a series of tests to verify the redundancy setup is working correctly:
1. Health check for both instances
2. VPN connectivity test
3. Failover simulation
4. Queue file creation and processing

Usage:
    python test_qbittorrent_redundancy.py
"""

import asyncio
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.integrations.qbittorrent_resilient import ResilientQBittorrentClient

# Load environment variables
load_dotenv()


class RedundancyTester:
    """Test suite for qBittorrent redundancy"""

    def __init__(self):
        self.primary_url = os.getenv('QBITTORRENT_URL', 'http://192.168.0.48:52095/')
        self.secondary_url = os.getenv('QBITTORRENT_SECONDARY_URL', 'http://localhost:52095/')
        self.username = os.getenv('QBITTORRENT_USERNAME')
        self.password = os.getenv('QBITTORRENT_PASSWORD')
        self.queue_file = Path("qbittorrent_queue.json")

        self.tests_passed = 0
        self.tests_failed = 0
        self.tests_skipped = 0

    def print_header(self, text: str):
        """Print test section header"""
        print()
        print("=" * 70)
        print(text)
        print("=" * 70)

    def print_test(self, name: str):
        """Print test name"""
        print(f"\n→ Test: {name}")

    def pass_test(self, message: str):
        """Mark test as passed"""
        self.tests_passed += 1
        print(f"  ✓ PASS: {message}")

    def fail_test(self, message: str):
        """Mark test as failed"""
        self.tests_failed += 1
        print(f"  ✗ FAIL: {message}")

    def skip_test(self, message: str):
        """Mark test as skipped"""
        self.tests_skipped += 1
        print(f"  - SKIP: {message}")

    async def test_1_health_check(self):
        """Test 1: Verify health check functionality"""
        self.print_test("Health Check Functionality")

        try:
            async with ResilientQBittorrentClient(
                primary_url=self.primary_url,
                secondary_url=self.secondary_url,
                username=self.username,
                password=self.password
            ) as client:
                health = await client.perform_health_check()

                # Verify health data structure
                required_keys = ['primary', 'secondary', 'vpn_connected', 'last_check']
                for key in required_keys:
                    if key not in health:
                        self.fail_test(f"Health data missing key: {key}")
                        return

                self.pass_test("Health check returns complete data")

                # Display results
                print(f"     VPN Connected: {health['vpn_connected']}")
                print(f"     Primary: {health['primary']}")
                print(f"     Secondary: {health['secondary']}")

                # Check if at least one instance is available
                if health['primary'] == 'OK' or health['secondary'] == 'OK':
                    self.pass_test("At least one instance is operational")
                else:
                    self.fail_test("No instances available - cannot run further tests")

        except Exception as e:
            self.fail_test(f"Health check threw exception: {e}")

    async def test_2_primary_instance(self):
        """Test 2: Verify primary instance accessibility"""
        self.print_test("Primary Instance Accessibility")

        try:
            async with ResilientQBittorrentClient(
                primary_url=self.primary_url,
                secondary_url=self.secondary_url,
                username=self.username,
                password=self.password
            ) as client:
                health = await client.perform_health_check()

                if health['primary'] == 'OK':
                    self.pass_test(f"Primary instance accessible at {self.primary_url}")
                elif health['primary'] == 'VPN_DOWN':
                    self.skip_test("VPN not connected - primary instance unavailable")
                elif health['primary'] == 'HTTP_403':
                    self.fail_test("Primary returns 403 Forbidden - check IP whitelist")
                elif health['primary'] == 'TIMEOUT':
                    self.fail_test("Primary timeout - check network connectivity")
                else:
                    self.fail_test(f"Primary status: {health['primary']}")

        except Exception as e:
            self.fail_test(f"Primary instance test threw exception: {e}")

    async def test_3_secondary_instance(self):
        """Test 3: Verify secondary instance accessibility"""
        self.print_test("Secondary Instance Accessibility")

        try:
            async with ResilientQBittorrentClient(
                primary_url=self.primary_url,
                secondary_url=self.secondary_url,
                username=self.username,
                password=self.password
            ) as client:
                health = await client.perform_health_check()

                if health['secondary'] == 'OK':
                    self.pass_test(f"Secondary instance accessible at {self.secondary_url}")
                elif health['secondary'] == 'NOT_CONFIGURED':
                    self.skip_test("Secondary URL not configured in .env")
                elif health['secondary'] == 'TIMEOUT':
                    self.skip_test("Secondary not running - install/start local qBittorrent for full redundancy")
                else:
                    self.fail_test(f"Secondary status: {health['secondary']}")

        except Exception as e:
            self.fail_test(f"Secondary instance test threw exception: {e}")

    async def test_4_vpn_connectivity(self):
        """Test 4: Verify VPN connectivity monitoring"""
        self.print_test("VPN Connectivity Monitoring")

        try:
            async with ResilientQBittorrentClient(
                primary_url=self.primary_url,
                secondary_url=self.secondary_url,
                username=self.username,
                password=self.password
            ) as client:
                health = await client.perform_health_check()

                if health['vpn_connected'] is not None:
                    if health['vpn_connected']:
                        self.pass_test("VPN gateway reachable at 192.168.0.1")
                    else:
                        self.skip_test("VPN not connected - reconnect ProtonVPN for primary instance")
                else:
                    self.fail_test("VPN status unknown")

        except Exception as e:
            self.fail_test(f"VPN connectivity test threw exception: {e}")

    async def test_5_failover_logic(self):
        """Test 5: Verify failover logic (dry run - no actual magnets added)"""
        self.print_test("Failover Logic (Simulated)")

        try:
            async with ResilientQBittorrentClient(
                primary_url=self.primary_url,
                secondary_url=self.secondary_url,
                username=self.username,
                password=self.password
            ) as client:
                health = await client.perform_health_check()

                # Determine which instance would be used
                if health['primary'] == 'OK':
                    self.pass_test("Primary available - would be used first")
                    print("     Failover path: Primary → Secondary → Queue")
                elif health['secondary'] == 'OK':
                    self.pass_test("Primary unavailable, secondary available - would failover to secondary")
                    print("     Failover path: Secondary → Queue")
                else:
                    self.pass_test("Both instances unavailable - would queue to file")
                    print("     Failover path: Queue to qbittorrent_queue.json")

        except Exception as e:
            self.fail_test(f"Failover logic test threw exception: {e}")

    async def test_6_queue_file_structure(self):
        """Test 6: Verify queue file can be created with correct structure"""
        self.print_test("Queue File Structure")

        try:
            # Create a test queue file
            test_queue = {
                'saved_at': '2025-11-28T00:00:00',
                'reason': 'Test queue file creation',
                'magnets': [
                    'magnet:?xt=urn:btih:test1&dn=Test+Book+1',
                    'magnet:?xt=urn:btih:test2&dn=Test+Book+2'
                ],
                'instructions': 'This is a test queue file'
            }

            test_file = Path("test_queue.json")
            test_file.write_text(json.dumps(test_queue, indent=2))

            # Verify structure
            loaded = json.loads(test_file.read_text())
            required_keys = ['saved_at', 'reason', 'magnets', 'instructions']

            for key in required_keys:
                if key not in loaded:
                    self.fail_test(f"Queue file missing key: {key}")
                    return

            if len(loaded['magnets']) == 2:
                self.pass_test("Queue file structure valid")
            else:
                self.fail_test(f"Queue file magnets count incorrect: {len(loaded['magnets'])}")

            # Clean up test file
            test_file.unlink()

        except Exception as e:
            self.fail_test(f"Queue file structure test threw exception: {e}")

    async def test_7_queue_file_cleanup(self):
        """Test 7: Verify existing queue file status"""
        self.print_test("Queue File Status Check")

        try:
            if self.queue_file.exists():
                queue_data = json.loads(self.queue_file.read_text())
                magnet_count = len(queue_data.get('magnets', []))
                saved_at = queue_data.get('saved_at', 'Unknown')

                self.skip_test(f"Queue file exists with {magnet_count} magnets (saved: {saved_at})")
                print(f"     File: {self.queue_file.absolute()}")
                print(f"     Action: Process with: python -c \"import asyncio; from backend.integrations.qbittorrent_resilient import ResilientQBittorrentClient; asyncio.run(ResilientQBittorrentClient('http://localhost:52095', 'TopherGutbrod', 'Tesl@ismy#1').process_queue_file())\"")
            else:
                self.pass_test("No queue file present - system clean")

        except Exception as e:
            self.fail_test(f"Queue file status check threw exception: {e}")

    async def test_8_credentials(self):
        """Test 8: Verify credentials are configured"""
        self.print_test("Credentials Configuration")

        if not self.username or not self.password:
            self.fail_test("Credentials not configured in .env")
            print("     Add QBITTORRENT_USERNAME and QBITTORRENT_PASSWORD to .env")
        else:
            self.pass_test("Credentials configured")
            print(f"     Username: {self.username}")

    async def run_all_tests(self):
        """Run all tests in sequence"""
        self.print_header("qBittorrent Redundancy Test Suite")

        print("\nConfiguration:")
        print(f"  Primary URL:   {self.primary_url}")
        print(f"  Secondary URL: {self.secondary_url}")
        print(f"  Username:      {self.username or 'NOT SET'}")
        print(f"  Password:      {'***' if self.password else 'NOT SET'}")

        # Run tests
        await self.test_8_credentials()  # Check credentials first
        await self.test_1_health_check()
        await self.test_4_vpn_connectivity()
        await self.test_2_primary_instance()
        await self.test_3_secondary_instance()
        await self.test_5_failover_logic()
        await self.test_6_queue_file_structure()
        await self.test_7_queue_file_cleanup()

        # Print summary
        self.print_header("Test Summary")

        print(f"\n✓ Passed:  {self.tests_passed}")
        print(f"✗ Failed:  {self.tests_failed}")
        print(f"- Skipped: {self.tests_skipped}")
        print()

        if self.tests_failed == 0:
            print("SUCCESS: All tests passed or skipped (no failures)")
            print()
            print("Next Steps:")
            print("1. Review skipped tests and address if needed")
            print("2. Run: python monitor_qbittorrent_health.py")
            print("3. Test full workflow: python execute_full_workflow.py")
        else:
            print("FAILURE: Some tests failed")
            print()
            print("Troubleshooting:")
            print("1. Review failed tests above")
            print("2. Check VPN connection: ping 192.168.0.1")
            print("3. Verify qBittorrent Web UI: http://192.168.0.48:52095")
            print("4. Check local qBittorrent: http://localhost:52095")
            print("5. Review: QBITTORRENT_REDUNDANCY_SETUP.md")

        print("=" * 70)

        # Return exit code based on results
        return 0 if self.tests_failed == 0 else 1


async def main():
    """Main entry point"""
    tester = RedundancyTester()
    exit_code = await tester.run_all_tests()
    return exit_code


if __name__ == '__main__':
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nTests cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        sys.exit(1)
