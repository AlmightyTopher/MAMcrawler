#!/usr/bin/env python3
"""
Automated qBittorrent Failover Testing Suite

Runs comprehensive tests of the VPN-resilient qBittorrent failover system.

Tests:
1. Normal Operation (VPN Up, Both Instances Running)
2. VPN Down Failover (Automatic Secondary Usage)
3. Manual Primary Block (Firewall Simulation)
4. All Services Down (Queue File Creation)
5. Queue File Processing (Recovery)

Usage:
    python test_failover.py [options]

Options:
    --skip-manual         Skip tests requiring manual VPN disconnect (Tests 2, 4)
    --verbose             Enable verbose output
    --quick               Run only Tests 1, 3, 5 (no VPN manipulation)
    --report-only         Generate report from previous test results

Examples:
    # Run all tests
    python test_failover.py

    # Run without VPN tests
    python test_failover.py --skip-manual

    # Quick test (no VPN manipulation)
    python test_failover.py --quick

    # Verbose output
    python test_failover.py --verbose
"""

import asyncio
import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add backend integrations to path
sys.path.insert(0, str(Path(__file__).parent / 'backend' / 'integrations'))
from qbittorrent_resilient import ResilientQBittorrentClient

load_dotenv()


class FailoverTestSuite:
    """Automated testing suite for qBittorrent failover system"""

    def __init__(self, skip_manual=False, verbose=False, quick=False):
        self.skip_manual = skip_manual
        self.verbose = verbose
        self.quick = quick
        self.results = {
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'tests': {},
            'summary': {},
            'environment': self._get_environment_info()
        }

    def _get_environment_info(self):
        """Collect environment information"""
        return {
            'python_version': sys.version,
            'platform': sys.platform,
            'primary_url': os.getenv('QBITTORRENT_URL', 'NOT_SET'),
            'secondary_url': os.getenv('QBITTORRENT_SECONDARY_URL', 'NOT_SET'),
            'test_mode': 'quick' if self.quick else ('skip_manual' if self.skip_manual else 'full')
        }

    def log(self, message, level="INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] [{level:5}] {message}"
        print(formatted)

        # Also log to file
        log_file = Path("failover_test_execution.log")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(formatted + "\n")

    def verbose_log(self, message):
        """Log only if verbose mode enabled"""
        if self.verbose:
            self.log(message, "DEBUG")

    async def test_1_normal_operation(self):
        """TEST 1: Normal operation with VPN up and both instances running"""
        self.log("=" * 70, "TEST")
        self.log("TEST 1: Normal Operation (VPN Up)", "TEST")
        self.log("=" * 70, "TEST")

        test_magnets = [
            "magnet:?xt=urn:btih:DD8255ECDC7CA55FB0BBF81323D87062DB1F6D1C&dn=Big+Buck+Bunny",
            "magnet:?xt=urn:btih:0B6B1A04F35EC6BD0EF9AA0F8AD1A1C7C2D1C1D1&dn=Test+Audiobook+1",
            "magnet:?xt=urn:btih:1C7C2D1C1D1B6B1A04F35EC6BD0EF9AA0F8AD1A1&dn=Test+Audiobook+2",
            "magnet:?xt=urn:btih:2D8D3E2E2E2C7C2D1C1D1B6B1A04F35EC6BD0EF9&dn=Test+Audiobook+3",
            "magnet:?xt=urn:btih:3E9E4F3F3F3D8D3E2E2E2C7C2D1C1D1B6B1A04F3&dn=Test+Audiobook+4"
        ]

        try:
            async with ResilientQBittorrentClient(
                primary_url=os.getenv('QBITTORRENT_URL'),
                secondary_url=os.getenv('QBITTORRENT_SECONDARY_URL'),
                username=os.getenv('QBITTORRENT_USERNAME'),
                password=os.getenv('QBITTORRENT_PASSWORD'),
                savepath="F:\\Audiobookshelf\\Books"
            ) as client:
                # Health check
                self.log("Performing health check...", "TEST")
                health = await client.perform_health_check()

                self.log(f"VPN Connected: {health['vpn_connected']}", "INFO")
                self.log(f"Primary Status: {health['primary']}", "INFO")
                self.log(f"Secondary Status: {health['secondary']}", "INFO")

                # Add magnets
                self.log(f"Adding {len(test_magnets)} test magnets...", "TEST")
                successful, failed, queued = await client.add_torrents_with_fallback(test_magnets)

                # Results
                self.log("Results:", "RESULT")
                self.log(f"  Successfully Added: {len(successful)}", "RESULT")
                self.log(f"  Failed: {len(failed)}", "RESULT")
                self.log(f"  Queued for Later: {len(queued)}", "RESULT")

                # Determine which instance was used
                instance_used = "unknown"
                if health['primary'] == 'OK' and len(successful) > 0:
                    instance_used = "primary"
                elif health['secondary'] == 'OK' and len(successful) > 0:
                    instance_used = "secondary"
                elif len(queued) > 0:
                    instance_used = "queued"

                # Store results
                result = {
                    'test_name': 'Normal Operation (VPN Up)',
                    'magnets_attempted': len(test_magnets),
                    'successful': len(successful),
                    'failed': len(failed),
                    'queued': len(queued),
                    'instance_used': instance_used,
                    'health': health,
                    'pass': len(successful) == len(test_magnets) and len(queued) == 0,
                    'timestamp': datetime.now().isoformat()
                }

                self.results['tests']['test_1'] = result

                # Log outcome
                if result['pass']:
                    self.log("TEST 1: PASS", "PASS")
                    self.log("All magnets added to primary instance successfully", "PASS")
                else:
                    self.log("TEST 1: FAIL", "FAIL")
                    if len(queued) > 0:
                        self.log(f"Expected 0 queued, got {len(queued)}", "FAIL")
                    if len(successful) != len(test_magnets):
                        self.log(f"Expected {len(test_magnets)} successful, got {len(successful)}", "FAIL")

                return result['pass']

        except Exception as e:
            self.log(f"TEST 1 ERROR: {e}", "ERROR")
            self.results['tests']['test_1'] = {
                'test_name': 'Normal Operation (VPN Up)',
                'pass': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            return False

    async def test_2_vpn_failover(self):
        """TEST 2: VPN down failover to secondary instance"""
        if self.skip_manual or self.quick:
            self.log("TEST 2: SKIPPED (requires manual VPN disconnect)", "SKIP")
            self.results['tests']['test_2'] = {
                'test_name': 'VPN Down Failover',
                'skipped': True,
                'reason': 'Manual VPN disconnect required',
                'timestamp': datetime.now().isoformat()
            }
            return True

        self.log("=" * 70, "TEST")
        self.log("TEST 2: VPN Down Failover", "TEST")
        self.log("=" * 70, "TEST")
        self.log("", "INFO")
        self.log("MANUAL ACTION REQUIRED:", "WARN")
        self.log("1. Disconnect ProtonVPN now", "WARN")
        self.log("2. Wait for disconnection confirmation", "WARN")
        self.log("3. Press Enter to continue test...", "WARN")

        input()  # Wait for user to disconnect VPN

        test_magnets = [
            "magnet:?xt=urn:btih:4F0F5G4G4G4E9E4F3F3F3D8D3E2E2E2C7C2D1C1D&dn=VPN+Test+1",
            "magnet:?xt=urn:btih:5G1G6H5H5H5F0F5G4G4G4E9E4F3F3F3D8D3E2E2E&dn=VPN+Test+2",
            "magnet:?xt=urn:btih:6H2H7I6I6I6G1G6H5H5H5F0F5G4G4G4E9E4F3F3F&dn=VPN+Test+3"
        ]

        try:
            async with ResilientQBittorrentClient(
                primary_url=os.getenv('QBITTORRENT_URL'),
                secondary_url=os.getenv('QBITTORRENT_SECONDARY_URL'),
                username=os.getenv('QBITTORRENT_USERNAME'),
                password=os.getenv('QBITTORRENT_PASSWORD'),
                savepath="F:\\Audiobookshelf\\Books"
            ) as client:
                # Health check
                self.log("Performing health check...", "TEST")
                health = await client.perform_health_check()

                self.log(f"VPN Connected: {health['vpn_connected']}", "INFO")
                self.log(f"Primary Status: {health['primary']}", "INFO")
                self.log(f"Secondary Status: {health['secondary']}", "INFO")

                if health['vpn_connected']:
                    self.log("WARNING: VPN still connected! Test may not behave as expected.", "WARN")

                # Add magnets
                self.log(f"Adding {len(test_magnets)} test magnets...", "TEST")
                self.log("Expected: Primary fails, secondary succeeds", "TEST")

                successful, failed, queued = await client.add_torrents_with_fallback(test_magnets)

                # Results
                self.log("Results:", "RESULT")
                self.log(f"  Successfully Added: {len(successful)}", "RESULT")
                self.log(f"  Failed: {len(failed)}", "RESULT")
                self.log(f"  Queued for Later: {len(queued)}", "RESULT")

                instance_used = "secondary" if len(successful) > 0 and health['secondary'] == 'OK' else "unknown"

                result = {
                    'test_name': 'VPN Down Failover',
                    'magnets_attempted': len(test_magnets),
                    'successful': len(successful),
                    'failed': len(failed),
                    'queued': len(queued),
                    'instance_used': instance_used,
                    'health': health,
                    'pass': len(successful) == len(test_magnets) and len(queued) == 0 and not health['vpn_connected'],
                    'timestamp': datetime.now().isoformat()
                }

                self.results['tests']['test_2'] = result

                if result['pass']:
                    self.log("TEST 2: PASS", "PASS")
                    self.log("Failover to secondary instance successful", "PASS")
                else:
                    self.log("TEST 2: FAIL", "FAIL")

                # Prompt to reconnect VPN
                self.log("", "INFO")
                self.log("MANUAL ACTION REQUIRED:", "WARN")
                self.log("1. Reconnect ProtonVPN now", "WARN")
                self.log("2. Press Enter to continue...", "WARN")
                input()

                return result['pass']

        except Exception as e:
            self.log(f"TEST 2 ERROR: {e}", "ERROR")
            self.results['tests']['test_2'] = {
                'test_name': 'VPN Down Failover',
                'pass': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            return False

    async def test_3_manual_block(self):
        """TEST 3: Manual firewall block (both instances running, primary blocked)"""
        self.log("=" * 70, "TEST")
        self.log("TEST 3: Manual Primary Block", "TEST")
        self.log("=" * 70, "TEST")
        self.log("", "INFO")
        self.log("NOTE: This test requires manual firewall rule creation", "INFO")
        self.log("Run in Administrator PowerShell:", "INFO")
        self.log('  New-NetFirewallRule -DisplayName "TEST: Block qBittorrent Primary" \\', "INFO")
        self.log('    -Direction Outbound -Protocol TCP -RemotePort 52095 \\', "INFO")
        self.log('    -RemoteAddress 192.168.0.48 -Action Block', "INFO")
        self.log("", "INFO")
        self.log("Press Enter when rule is created (or skip by typing 'skip')...", "INFO")

        user_input = input()
        if user_input.lower() == 'skip':
            self.log("TEST 3: SKIPPED by user", "SKIP")
            self.results['tests']['test_3'] = {
                'test_name': 'Manual Primary Block',
                'skipped': True,
                'reason': 'User skipped manual firewall setup',
                'timestamp': datetime.now().isoformat()
            }
            return True

        test_magnet = ["magnet:?xt=urn:btih:7I3I8J7J7J7H2H7I6I6I6G1G6H5H5H5F0F5G4G4G&dn=Block+Test+1"]

        try:
            async with ResilientQBittorrentClient(
                primary_url=os.getenv('QBITTORRENT_URL'),
                secondary_url=os.getenv('QBITTORRENT_SECONDARY_URL'),
                username=os.getenv('QBITTORRENT_USERNAME'),
                password=os.getenv('QBITTORRENT_PASSWORD'),
                savepath="F:\\Audiobookshelf\\Books"
            ) as client:
                # Health check
                self.log("Performing health check...", "TEST")
                health = await client.perform_health_check()

                self.log(f"Primary Status: {health['primary']}", "INFO")
                self.log(f"Secondary Status: {health['secondary']}", "INFO")

                # Add magnet
                self.log("Adding test magnet...", "TEST")
                successful, failed, queued = await client.add_torrents_with_fallback(test_magnet)

                result = {
                    'test_name': 'Manual Primary Block',
                    'magnets_attempted': 1,
                    'successful': len(successful),
                    'instance_used': 'secondary' if len(successful) > 0 else 'unknown',
                    'health': health,
                    'pass': len(successful) == 1,
                    'timestamp': datetime.now().isoformat()
                }

                self.results['tests']['test_3'] = result

                if result['pass']:
                    self.log("TEST 3: PASS", "PASS")
                    self.log("Fallback to secondary worked despite firewall block", "PASS")
                else:
                    self.log("TEST 3: FAIL", "FAIL")

                # Prompt to remove firewall rule
                self.log("", "INFO")
                self.log("MANUAL ACTION REQUIRED:", "WARN")
                self.log("Remove firewall rule in Administrator PowerShell:", "WARN")
                self.log('  Remove-NetFirewallRule -DisplayName "TEST: Block qBittorrent Primary"', "WARN")
                self.log("Press Enter when rule is removed...", "WARN")
                input()

                return result['pass']

        except Exception as e:
            self.log(f"TEST 3 ERROR: {e}", "ERROR")
            self.results['tests']['test_3'] = {
                'test_name': 'Manual Primary Block',
                'pass': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            return False

    async def test_4_queue_creation(self):
        """TEST 4: All services down - queue file creation"""
        if self.skip_manual or self.quick:
            self.log("TEST 4: SKIPPED (requires stopping all services)", "SKIP")
            self.results['tests']['test_4'] = {
                'test_name': 'Queue File Creation',
                'skipped': True,
                'reason': 'Manual service shutdown required',
                'timestamp': datetime.now().isoformat()
            }
            return True

        self.log("=" * 70, "TEST")
        self.log("TEST 4: All Services Down (Queue Creation)", "TEST")
        self.log("=" * 70, "TEST")
        self.log("", "INFO")
        self.log("MANUAL ACTION REQUIRED:", "WARN")
        self.log("1. Disconnect ProtonVPN", "WARN")
        self.log("2. Stop local qBittorrent: Stop-Process -Name qbittorrent -Force", "WARN")
        self.log("3. Verify both down: python monitor_qbittorrent_health.py", "WARN")
        self.log("4. Press Enter to continue...", "WARN")

        input()

        test_magnets = [
            "magnet:?xt=urn:btih:8J4J9K8K8K8I3I8J7J7J7H2H7I6I6I6G1G6H5H5H&dn=Queue+Test+1",
            "magnet:?xt=urn:btih:9K5K0L9L9L9J4J9K8K8K8I3I8J7J7J7H2H7I6I6I&dn=Queue+Test+2",
            "magnet:?xt=urn:btih:0L6L1M0M0M0K5K0L9L9L9J4J9K8K8K8I3I8J7J7J&dn=Queue+Test+3"
        ]

        queue_file = Path("qbittorrent_queue.json")

        # Delete existing queue file
        if queue_file.exists():
            queue_file.unlink()
            self.log("Removed existing queue file", "INFO")

        try:
            async with ResilientQBittorrentClient(
                primary_url=os.getenv('QBITTORRENT_URL'),
                secondary_url=os.getenv('QBITTORRENT_SECONDARY_URL'),
                username=os.getenv('QBITTORRENT_USERNAME'),
                password=os.getenv('QBITTORRENT_PASSWORD'),
                queue_file=str(queue_file),
                savepath="F:\\Audiobookshelf\\Books"
            ) as client:
                # Health check
                self.log("Performing health check...", "TEST")
                health = await client.perform_health_check()

                self.log(f"VPN Connected: {health['vpn_connected']}", "INFO")
                self.log(f"Primary Status: {health['primary']}", "INFO")
                self.log(f"Secondary Status: {health['secondary']}", "INFO")

                if health['primary'] == 'OK' or health['secondary'] == 'OK':
                    self.log("WARNING: At least one instance is still up!", "WARN")

                # Add magnets
                self.log(f"Adding {len(test_magnets)} test magnets...", "TEST")
                self.log("Expected: All should be queued to file", "TEST")

                successful, failed, queued = await client.add_torrents_with_fallback(test_magnets)

                # Results
                self.log("Results:", "RESULT")
                self.log(f"  Successfully Added: {len(successful)}", "RESULT")
                self.log(f"  Failed: {len(failed)}", "RESULT")
                self.log(f"  Queued to File: {len(queued)}", "RESULT")

                # Verify queue file
                queue_file_created = queue_file.exists()
                queue_data = None

                if queue_file_created:
                    self.log(f"Queue file created: {queue_file}", "INFO")
                    queue_data = json.loads(queue_file.read_text())
                    self.log(f"  Saved At: {queue_data['saved_at']}", "INFO")
                    self.log(f"  Reason: {queue_data['reason']}", "INFO")
                    self.log(f"  Magnets in Queue: {len(queue_data['magnets'])}", "INFO")
                else:
                    self.log("ERROR: Queue file not created!", "ERROR")

                result = {
                    'test_name': 'Queue File Creation',
                    'magnets_attempted': len(test_magnets),
                    'successful': len(successful),
                    'failed': len(failed),
                    'queued': len(queued),
                    'queue_file_created': queue_file_created,
                    'queue_data': queue_data,
                    'health': health,
                    'pass': len(queued) == len(test_magnets) and queue_file_created,
                    'timestamp': datetime.now().isoformat()
                }

                self.results['tests']['test_4'] = result

                if result['pass']:
                    self.log("TEST 4: PASS", "PASS")
                    self.log("Queue file created successfully", "PASS")
                else:
                    self.log("TEST 4: FAIL", "FAIL")

                return result['pass']

        except Exception as e:
            self.log(f"TEST 4 ERROR: {e}", "ERROR")
            self.results['tests']['test_4'] = {
                'test_name': 'Queue File Creation',
                'pass': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            return False

    async def test_5_queue_processing(self):
        """TEST 5: Process queued magnets when services restore"""
        self.log("=" * 70, "TEST")
        self.log("TEST 5: Queue File Processing (Recovery)", "TEST")
        self.log("=" * 70, "TEST")

        queue_file = Path("qbittorrent_queue.json")

        if not queue_file.exists():
            self.log("No queue file found - skipping queue processing test", "SKIP")
            self.results['tests']['test_5'] = {
                'test_name': 'Queue File Processing',
                'skipped': True,
                'reason': 'No queue file found (run Test 4 first)',
                'timestamp': datetime.now().isoformat()
            }
            return True

        # Read queue before processing
        queue_data = json.loads(queue_file.read_text())
        magnet_count_before = len(queue_data.get('magnets', []))

        self.log(f"Queue file found with {magnet_count_before} magnets", "INFO")
        self.log("", "INFO")
        self.log("MANUAL ACTION REQUIRED:", "WARN")
        self.log("1. Start at least one qBittorrent instance", "WARN")
        self.log("   - Reconnect VPN for primary, OR", "WARN")
        self.log("   - Start local qBittorrent for secondary", "WARN")
        self.log("2. Press Enter to continue...", "WARN")

        input()

        try:
            async with ResilientQBittorrentClient(
                primary_url=os.getenv('QBITTORRENT_URL'),
                secondary_url=os.getenv('QBITTORRENT_SECONDARY_URL'),
                username=os.getenv('QBITTORRENT_USERNAME'),
                password=os.getenv('QBITTORRENT_PASSWORD'),
                queue_file=str(queue_file),
                savepath="F:\\Audiobookshelf\\Books"
            ) as client:
                # Health check
                self.log("Performing health check...", "TEST")
                health = await client.perform_health_check()

                self.log(f"Primary Status: {health['primary']}", "INFO")
                self.log(f"Secondary Status: {health['secondary']}", "INFO")

                if health['primary'] != 'OK' and health['secondary'] != 'OK':
                    self.log("WARNING: Both instances still down!", "WARN")

                # Process queue
                self.log("Processing queue file...", "TEST")
                successful, failed = await client.process_queue_file()

                # Results
                self.log("Results:", "RESULT")
                self.log(f"  Successfully Recovered: {len(successful)}", "RESULT")
                self.log(f"  Failed: {len(failed)}", "RESULT")

                # Check if queue file deleted
                queue_file_deleted = not queue_file.exists()

                if queue_file_deleted:
                    self.log("Queue file cleaned up successfully", "INFO")
                else:
                    self.log("WARNING: Queue file still exists", "WARN")
                    if queue_file.exists():
                        remaining = json.loads(queue_file.read_text())
                        self.log(f"  Remaining magnets: {len(remaining.get('magnets', []))}", "WARN")

                result = {
                    'test_name': 'Queue File Processing',
                    'magnets_queued': magnet_count_before,
                    'recovered': len(successful),
                    'failed': len(failed),
                    'queue_file_deleted': queue_file_deleted,
                    'health': health,
                    'pass': len(successful) == magnet_count_before and queue_file_deleted,
                    'timestamp': datetime.now().isoformat()
                }

                self.results['tests']['test_5'] = result

                if result['pass']:
                    self.log("TEST 5: PASS", "PASS")
                    self.log("Queue processed and file cleaned up successfully", "PASS")
                else:
                    self.log("TEST 5: FAIL", "FAIL")

                return result['pass']

        except Exception as e:
            self.log(f"TEST 5 ERROR: {e}", "ERROR")
            self.results['tests']['test_5'] = {
                'test_name': 'Queue File Processing',
                'pass': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            return False

    def generate_report(self):
        """Generate comprehensive test report"""
        self.results['end_time'] = datetime.now().isoformat()

        # Calculate summary
        total_tests = len([t for t in self.results['tests'].values() if not t.get('skipped', False)])
        passed = sum(1 for t in self.results['tests'].values()
                     if not t.get('skipped', False) and t.get('pass', False))
        failed = total_tests - passed
        skipped = len([t for t in self.results['tests'].values() if t.get('skipped', False)])

        self.results['summary'] = {
            'total_tests': len(self.results['tests']),
            'tests_run': total_tests,
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'pass_rate': f"{(passed/total_tests*100):.1f}%" if total_tests > 0 else "N/A"
        }

        # Save to JSON
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = Path(f"failover_test_report_{timestamp}.json")
        report_file.write_text(json.dumps(self.results, indent=2))

        self.log(f"Report saved to: {report_file}", "INFO")

        # Print summary
        print("\n" + "=" * 70)
        print("FAILOVER TEST SUITE SUMMARY")
        print("=" * 70)
        print(f"Total Tests Defined: {self.results['summary']['total_tests']}")
        print(f"Tests Run: {total_tests}")
        print(f"Tests Skipped: {skipped}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Pass Rate: {self.results['summary']['pass_rate']}")
        print("=" * 70)

        # Individual test results
        for test_name, test_result in self.results['tests'].items():
            if test_result.get('skipped', False):
                print(f"{test_name}: SKIPPED ({test_result.get('reason', 'Unknown')})")
            elif test_result.get('pass', False):
                print(f"{test_name}: PASS")
            else:
                print(f"{test_name}: FAIL")
                if 'error' in test_result:
                    print(f"  Error: {test_result['error']}")

        print("=" * 70)

        return report_file


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='qBittorrent Failover Test Suite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_failover.py                 Run all tests
  python test_failover.py --skip-manual   Skip VPN manipulation tests
  python test_failover.py --quick         Run only quick tests (1, 3, 5)
  python test_failover.py --verbose       Enable verbose output
        """
    )

    parser.add_argument('--skip-manual', action='store_true',
                        help='Skip tests requiring manual VPN disconnect (Tests 2, 4)')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose debug output')
    parser.add_argument('--quick', action='store_true',
                        help='Run only quick tests (no VPN manipulation)')

    args = parser.parse_args()

    # Initialize test suite
    suite = FailoverTestSuite(
        skip_manual=args.skip_manual,
        verbose=args.verbose,
        quick=args.quick
    )

    print("=" * 70)
    print("qBittorrent Failover System - Automated Test Suite")
    print("=" * 70)
    print()
    print(f"Test Mode: {suite.results['environment']['test_mode']}")
    print(f"Primary URL: {suite.results['environment']['primary_url']}")
    print(f"Secondary URL: {suite.results['environment']['secondary_url']}")
    print()

    # Run tests
    suite.log("Starting test execution...", "INFO")
    print()

    await suite.test_1_normal_operation()
    print()

    if not args.quick:
        await suite.test_2_vpn_failover()
        print()

    await suite.test_3_manual_block()
    print()

    if not args.quick:
        await suite.test_4_queue_creation()
        print()

    await suite.test_5_queue_processing()
    print()

    # Generate report
    suite.log("Generating test report...", "INFO")
    report_file = suite.generate_report()

    print()
    print("=" * 70)
    print("Test execution complete!")
    print(f"Detailed report: {report_file}")
    print("=" * 70)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest execution cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
