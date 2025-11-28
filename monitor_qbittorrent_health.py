#!/usr/bin/env python3
"""
Monitor qBittorrent Redundancy Health Status

This script provides real-time health monitoring for the redundant qBittorrent setup:
- Primary instance (remote via VPN)
- Secondary instance (local fallback)
- VPN connectivity status

Usage:
    python monitor_qbittorrent_health.py
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.integrations.qbittorrent_resilient import ResilientQBittorrentClient

# Load environment variables
load_dotenv()


async def monitor():
    """Perform health check and display results"""
    primary_url = os.getenv('QBITTORRENT_URL', 'http://192.168.0.48:52095/')
    secondary_url = os.getenv('QBITTORRENT_SECONDARY_URL', 'http://localhost:52095/')
    username = os.getenv('QBITTORRENT_USERNAME')
    password = os.getenv('QBITTORRENT_PASSWORD')

    if not username or not password:
        print("ERROR: QBITTORRENT_USERNAME and QBITTORRENT_PASSWORD must be set in .env")
        return

    print("=" * 70)
    print("qBittorrent Redundancy Health Check")
    print("=" * 70)
    print()

    try:
        async with ResilientQBittorrentClient(
            primary_url=primary_url,
            secondary_url=secondary_url,
            username=username,
            password=password
        ) as client:
            # Perform health check
            health = await client.perform_health_check()

            # Display results
            print(f"VPN Status:        {'✓ Connected' if health['vpn_connected'] else '✗ Disconnected'}")
            print(f"Primary Instance:  {format_status(health['primary'])} ({primary_url})")
            print(f"Secondary Instance: {format_status(health['secondary'])} ({secondary_url})")
            print(f"Last Check:        {health['last_check']}")
            print()

            # Check for queue file
            queue_file = Path("qbittorrent_queue.json")
            if queue_file.exists():
                import json
                queue_data = json.loads(queue_file.read_text())
                magnet_count = len(queue_data.get('magnets', []))
                print(f"⚠️  Queue File Found: {magnet_count} magnets waiting for recovery")
                print(f"   → File: {queue_file.absolute()}")
                print(f"   → Saved at: {queue_data.get('saved_at', 'Unknown')}")
                print()

            # Provide recommendations
            print("Status Analysis:")
            print("-" * 70)

            if health['primary'] != 'OK' and health['secondary'] != 'OK':
                print("⚠️  CRITICAL: Both instances unavailable!")
                print()
                print("   Impact:")
                print("   → New downloads will be queued to qbittorrent_queue.json")
                print("   → Workflow will continue but magnets won't download immediately")
                print()
                print("   Recommended Actions:")
                print("   1. Check VPN connection:")
                print("      - Reconnect ProtonVPN")
                print("      - Verify VPN adapter has IP 10.2.0.2")
                print("      - Test: ping 192.168.0.1")
                print()
                print("   2. Start local qBittorrent:")
                print("      - Launch from Start Menu")
                print("      - Or run: \"C:\\Program Files\\qBittorrent\\qbittorrent.exe\"")
                print()
                print("   3. Process queue file when service restores:")
                print("      - Run: python -c \"import asyncio; from backend.integrations.qbittorrent_resilient import ResilientQBittorrentClient; asyncio.run(ResilientQBittorrentClient('http://localhost:52095', 'TopherGutbrod', 'Tesl@ismy#1').process_queue_file())\"")

            elif health['primary'] != 'OK':
                print("⚠️  WARNING: Primary instance unavailable")
                print()
                print("   Current State:")
                print("   → Secondary instance is handling downloads")
                print("   → Downloads will use local qBittorrent")
                print()
                print("   Primary Issue Details:")
                if health['primary'] == 'VPN_DOWN':
                    print("   → VPN disconnected or gateway unreachable")
                    print("   → Check ProtonVPN status and reconnect")
                elif health['primary'] == 'HTTP_403':
                    print("   → IP not whitelisted in qBittorrent Web UI")
                    print("   → Update Web UI settings on remote server (192.168.0.48)")
                elif health['primary'] == 'HTTP_404':
                    print("   → VPN routing issue or remote server down")
                    print("   → Verify VPN connection and remote server status")
                elif health['primary'] == 'TIMEOUT':
                    print("   → Network timeout connecting to remote server")
                    print("   → Check firewall rules and network latency")
                else:
                    print(f"   → Status: {health['primary']}")
                print()
                print("   Recommended Actions:")
                print("   1. Verify VPN connection")
                print("   2. Test remote server: ping 192.168.0.48")
                print("   3. Check port proxy: netsh interface portproxy show all")

            elif health['secondary'] != 'OK':
                print("ℹ️  INFO: Secondary instance unavailable (primary OK)")
                print()
                print("   Current State:")
                print("   → Primary instance is operational")
                print("   → Full redundancy not available (but not required)")
                print()
                print("   Secondary Issue Details:")
                if health['secondary'] == 'NOT_CONFIGURED':
                    print("   → QBITTORRENT_SECONDARY_URL not set in .env")
                    print("   → Add: QBITTORRENT_SECONDARY_URL=http://localhost:52095/")
                elif health['secondary'] == 'TIMEOUT':
                    print("   → Local qBittorrent not running or port conflict")
                    print("   → Start qBittorrent from Start Menu")
                else:
                    print(f"   → Status: {health['secondary']}")
                print()
                print("   Optional Actions (for full redundancy):")
                print("   1. Install qBittorrent locally if not installed")
                print("   2. Configure Web UI on localhost:52095")
                print("   3. Set QBITTORRENT_SECONDARY_URL in .env")

            else:
                print("✓ EXCELLENT: Full redundancy operational")
                print()
                print("   Status:")
                print("   → Both instances healthy and ready")
                print("   → Automatic failover available if VPN drops")
                print("   → Zero downtime configuration active")
                print()
                print("   System Capabilities:")
                print("   • Primary failure → Automatic failover to secondary")
                print("   • Both fail → Queue to JSON for manual recovery")
                print("   • Services restore → Auto-process queued magnets")

            print("=" * 70)

    except Exception as e:
        print(f"ERROR: Health check failed")
        print(f"Details: {str(e)}")
        print()
        print("Troubleshooting:")
        print("1. Verify .env file has correct credentials")
        print("2. Check network connectivity")
        print("3. Ensure at least one qBittorrent instance is running")


def format_status(status: str) -> str:
    """Format status with color indicators"""
    status_map = {
        'OK': '✓ OK',
        'VPN_DOWN': '✗ VPN Down',
        'HTTP_403': '✗ Forbidden (403)',
        'HTTP_404': '✗ Not Found (404)',
        'TIMEOUT': '✗ Timeout',
        'NOT_CONFIGURED': '- Not Configured',
        'UNKNOWN': '? Unknown',
    }
    return status_map.get(status, f'? {status}')


if __name__ == '__main__':
    try:
        asyncio.run(monitor())
    except KeyboardInterrupt:
        print("\nMonitoring cancelled by user")
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        sys.exit(1)
