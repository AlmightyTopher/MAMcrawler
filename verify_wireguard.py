#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify WireGuard Python-Only Tunnel Setup
Tests that System Python uses WireGuard VPN and other traffic uses normal WAN.
"""

import subprocess
import sys
import json
import socket
import time

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("WIREGUARD TUNNEL VERIFICATION")
print("=" * 70)
print()

# Define Python executables
system_python = "C:\\Program Files\\Python311\\python.exe"

# We will use this script payload to test the external IP from within the target python process
# It tries multiple services
check_script = """
import requests
import sys

services = [
    "http://httpbin.org/ip",
    "https://api.ipify.org?format=json",
    "https://api.myip.com"
]

for url in services:
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            try:
                data = resp.json()
                # Handle different formats
                ip = data.get('origin') or data.get('ip')
                if ip:
                    print(ip.split(',')[0].strip()) # httpbin sometimes returns multiple
                    sys.exit(0)
            except:
                pass
    except:
        pass

print("FAILED")
sys.exit(1)
"""

print("[1] Testing System Python (should use WireGuard tunnel)...")
print("-" * 70)
print(f"  Python: {system_python}")

try:
    result = subprocess.run(
        [system_python, '-c', check_script],
        capture_output=True,
        text=True,
        timeout=30
    )

    if result.returncode == 0:
        python_ip = result.stdout.strip()
        print(f"  ✅ External IP: {python_ip}")
    else:
        print(f"  ❌ Failed. Output: {result.stdout}")
        print(f"  ❌ Error: {result.stderr}")
        python_ip = None
except Exception as e:
    print(f"  ❌ Exception: {e}")
    python_ip = None

print()

print("[2] Testing Windows Default Route (should bypass tunnel)...")
print("-" * 70)
print("  Using: curl (Windows native)")

windows_ip = None
try:
    # Try ipify first as it returns plain text by default (easier for curl)
    result = subprocess.run(
        ['curl', '-s', 'https://api.ipify.org'],
        capture_output=True,
        text=True,
        timeout=15
    )

    if result.returncode == 0 and result.stdout.strip():
        windows_ip = result.stdout.strip()
        print(f"  ✅ External IP: {windows_ip}")
    else:
        # Fallback to httpbin
        result = subprocess.run(
           ['curl', '-s', 'http://httpbin.org/ip'],
           capture_output=True,
           text=True,
           timeout=15
        )
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                windows_ip = data.get('origin')
                print(f"  ✅ External IP: {windows_ip}")
            except:
                 print(f"  ❌ Failed to parse JSON: {result.stdout[:100]}")
        else:
            print(f"  ❌ Failed: {result.stderr}")

except Exception as e:
    print(f"  ❌ Error: {e}")

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
elif python_ip:
    print("⚠️  Windows traffic test failed but Python works")
    print(f"  Python IP: {python_ip}")
    print("  This means the VPN might be working for Python, but local internet is flaky.")
elif windows_ip:
    print("⚠️  Python test failed but Windows works")
    print(f"  Windows IP: {windows_ip}")
    print("  This likely means the VPN is BLOCKING traffic (Kill Switch?) or misconfigured.")
else:
    print("❌ Both tests failed. No internet connectivity detected.")

print("=" * 70)
