#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify WireGuard Python-Only Tunnel Setup
Tests that System Python uses WireGuard VPN and other traffic uses normal WAN.
"""

import subprocess
import sys
import json

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("WIREGUARD TUNNEL VERIFICATION")
print("=" * 70)
print()

# Define Python executables
system_python = "C:\\Program Files\\Python311\\python.exe"

# Test command to get external IP
test_command = 'import requests; print(requests.get("http://httpbin.org/ip", timeout=10).json()["origin"])'

print("[1] Testing System Python (should use WireGuard tunnel)...")
print("-" * 70)
print(f"  Python: {system_python}")

try:
    result = subprocess.run(
        [system_python, '-c', test_command],
        capture_output=True,
        text=True,
        timeout=15
    )

    if result.returncode == 0:
        python_ip = result.stdout.strip()
        print(f"  ✅ External IP: {python_ip}")
    else:
        print(f"  ❌ Failed: {result.stderr}")
        python_ip = None
except Exception as e:
    print(f"  ❌ Error: {e}")
    python_ip = None

print()

print("[2] Testing Windows Default Route (should bypass tunnel)...")
print("-" * 70)
print("  Using: curl (Windows native)")

try:
    # Test with curl (not bound to Python firewall rules)
    result = subprocess.run(
        ['curl', '-s', 'http://httpbin.org/ip'],
        capture_output=True,
        text=True,
        timeout=15
    )

    if result.returncode == 0:
        data = json.loads(result.stdout)
        windows_ip = data.get('origin', 'Unknown')
        print(f"  ✅ External IP: {windows_ip}")
    else:
        print(f"  ❌ Failed: {result.stderr}")
        windows_ip = None
except Exception as e:
    print(f"  ❌ Error: {e}")
    windows_ip = None

print()
print("=" * 70)
print("RESULTS")
print("=" * 70)

if python_ip and windows_ip:
    if python_ip != windows_ip:
        print("✅ SUCCESS - Two different routes detected!")
        print()
        print(f"  Python traffic:  {python_ip} (via WireGuard VPN)")
        print(f"  Windows traffic: {windows_ip} (direct WAN)")
        print()
        print("🎉 Your WireGuard tunnel is working correctly!")
        print("   Python will use VPN, everything else uses normal internet.")
        print()
        print("Next steps:")
        print("  1. Update scraper scripts to use system Python")
        print("  2. Run: python run_dual_scraper.py")
        print()
    else:
        print("⚠️  WARNING - Both use the SAME IP!")
        print()
        print(f"  Both show: {python_ip}")
        print()
        print("Possible issues:")
        print("  1. WireGuard tunnel not running")
        print("  2. Firewall rules not applied correctly")
        print("  3. Interface metric not set (tunnel taking all traffic)")
        print()
        print("Run this in Administrator PowerShell:")
        print('  Get-Service | Where-Object {$_.DisplayName -like "*TopherTek*"}')
        print('  Get-NetFirewallRule | Where-Object {$_.DisplayName -like "PythonVPN*"}')
        print()
elif python_ip:
    print("⚠️  Windows traffic test failed but Python works")
    print(f"  Python IP: {python_ip}")
    print()
    print("This is okay - Windows might not have curl installed.")
    print("Try manually testing in your browser: http://httpbin.org/ip")
elif windows_ip:
    print("⚠️  Python test failed but Windows works")
    print(f"  Windows IP: {windows_ip}")
    print()
    print("Fix: Check that Python and requests library are installed correctly")
else:
    print("❌ Both tests failed")
    print()
    print("Possible issues:")
    print("  1. No internet connection")
    print("  2. requests library not installed: pip install requests")
    print("  3. httpbin.org is down")

print("=" * 70)
