#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProtonVPN SOCKS5 Proxy Diagnostic Tool
Comprehensive check for ProtonVPN configuration and proxy availability.
"""

import socket
import subprocess
import sys
import os
from typing import Optional, List, Tuple

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def check_process_running(process_name: str) -> bool:
    """Check if a process is running."""
    try:
        result = subprocess.run(
            ['tasklist'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return process_name.lower() in result.stdout.lower()
    except:
        return False

def find_python_paths() -> List[str]:
    """Find all Python executable paths."""
    paths = []

    # System Python
    try:
        result = subprocess.run(
            ['where', 'python'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            paths.extend([p.strip() for p in result.stdout.split('\n') if p.strip()])
    except:
        pass

    # Virtual env Python
    venv_python = os.path.join(os.getcwd(), 'venv', 'Scripts', 'python.exe')
    if os.path.exists(venv_python):
        paths.append(venv_python)

    return list(set(paths))  # Remove duplicates

def scan_proxy_ports() -> List[Tuple[int, bool]]:
    """Scan common SOCKS5 proxy ports."""
    common_ports = [
        1080,   # Classic SOCKS5
        8080,   # ProtonVPN v4.x default
        9050,   # Tor
        9150,   # Tor Browser
        54674,  # ProtonVPN alternate
        62410,  # User-reported port
        1081,   # Alternate SOCKS
        8888,   # Alternate proxy
        3128,   # Squid proxy
    ]

    results = []
    for port in common_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            if result == 0:
                results.append((port, True))
        except:
            pass

    return results

def test_proxy_with_requests(port: int) -> Optional[str]:
    """Test proxy functionality with HTTP request."""
    try:
        import requests
        proxies = {
            'http': f'socks5://127.0.0.1:{port}',
            'https': f'socks5://127.0.0.1:{port}'
        }
        response = requests.get('http://httpbin.org/ip', proxies=proxies, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('origin', 'Unknown')
    except ImportError:
        return "requests library not installed"
    except Exception as e:
        return f"Error: {str(e)[:100]}"
    return None

def check_pysocks_installed() -> bool:
    """Check if PySocks is installed."""
    try:
        import socks
        return True
    except ImportError:
        return False

def main():
    print("=" * 70)
    print("ProtonVPN SOCKS5 Proxy Diagnostic Tool")
    print("=" * 70)
    print()

    # Step 1: Check ProtonVPN processes
    print("[1] Checking ProtonVPN Status...")
    print("-" * 70)

    vpn_processes = [
        'ProtonVPN.exe',
        'ProtonVPN.Client.exe',
        'ProtonVPNService.exe',
        'ProtonVPN.WireGuardService.exe'
    ]

    running_processes = []
    for process in vpn_processes:
        if check_process_running(process):
            running_processes.append(process)
            print(f"  ✅ {process} is running")

    if not running_processes:
        print("  ❌ ProtonVPN is NOT running")
        print()
        print("⚠️  SOLUTION: Start ProtonVPN and connect to a server")
        return
    else:
        print(f"  ✅ ProtonVPN is RUNNING ({len(running_processes)} processes)")

    print()

    # Step 2: Check Python paths
    print("[2] Checking Python Installations...")
    print("-" * 70)

    python_paths = find_python_paths()
    if python_paths:
        for path in python_paths:
            print(f"  📍 {path}")
    else:
        print("  ⚠️  No Python installations found in PATH")

    print()
    print("  💡 Add these paths to ProtonVPN Split Tunneling 'Included Apps'")
    print()

    # Step 3: Scan for proxy ports
    print("[3] Scanning for SOCKS5 Proxy Ports...")
    print("-" * 70)

    open_ports = scan_proxy_ports()

    if not open_ports:
        print("  ❌ No proxy ports detected on localhost")
        print()
        print("  ⚠️  SOLUTION: Enable Split Tunneling in ProtonVPN")
        print("     1. ProtonVPN → Settings → Advanced → Split Tunneling")
        print("     2. Enable Split Tunneling")
        print("     3. Select 'Include only selected apps in VPN tunnel'")
        print("     4. Add Python executables to 'Included Apps'")
        print("     5. Restart ProtonVPN")
        print()
    else:
        print(f"  ✅ Found {len(open_ports)} open port(s):")
        for port, _ in open_ports:
            print(f"     • Port {port}")
        print()

    # Step 4: Test proxy functionality
    if open_ports:
        print("[4] Testing Proxy Functionality...")
        print("-" * 70)

        if not check_pysocks_installed():
            print("  ⚠️  PySocks not installed (required for SOCKS5 proxy)")
            print("     Install with: pip install pysocks")
            print()

        working_proxy = None
        for port, _ in open_ports:
            print(f"  Testing port {port}...")
            result = test_proxy_with_requests(port)

            if result and not result.startswith("Error"):
                print(f"    ✅ WORKING! External IP: {result}")
                working_proxy = port
                break
            elif result:
                print(f"    ❌ Failed: {result}")
            else:
                print(f"    ❌ No response")

        print()

        if working_proxy:
            print("=" * 70)
            print("🎉 SUCCESS - ProtonVPN SOCKS5 Proxy is Working!")
            print("=" * 70)
            print()
            print(f"Proxy Configuration:")
            print(f"  • Address: socks5://127.0.0.1:{working_proxy}")
            print(f"  • External IP: {test_proxy_with_requests(working_proxy)}")
            print()
            print("✅ Your dual scraper will use this proxy automatically")
            print("   Run: python dual_goodreads_scraper.py")
            print()
        else:
            print("=" * 70)
            print("⚠️  ISSUE - Proxy Ports Open but Not Functional")
            print("=" * 70)
            print()
            print("Possible causes:")
            print("  1. PySocks library not installed: pip install pysocks")
            print("  2. ProtonVPN not connected to a server")
            print("  3. Kill Switch blocking proxy traffic")
            print("  4. Firewall blocking localhost connections")
            print()
    else:
        print("[4] Skipping proxy test (no ports detected)")
        print()

    # Step 5: Summary and recommendations
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    if running_processes and open_ports and any(test_proxy_with_requests(p) for p, _ in open_ports):
        print("✅ ProtonVPN is configured correctly")
        print("✅ SOCKS5 proxy is available and working")
        print("✅ Ready to run dual scraper")
    elif running_processes and open_ports:
        print("⚠️  ProtonVPN is running but proxy is not functional")
        print("   Install PySocks: pip install pysocks")
        print("   Verify ProtonVPN is connected to a server")
    elif running_processes:
        print("⚠️  ProtonVPN is running but Split Tunneling is not enabled")
        print("   Enable Split Tunneling in ProtonVPN settings")
        print("   Add Python to 'Included Apps'")
    else:
        print("❌ ProtonVPN is not running")
        print("   Start ProtonVPN and connect to a server")

    print()
    print("For detailed setup instructions, see: protonvpn_setup_guide.md")
    print("=" * 70)

if __name__ == "__main__":
    main()
