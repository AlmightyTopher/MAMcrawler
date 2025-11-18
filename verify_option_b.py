#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify Option B Setup
Tests that system Python uses VPN and venv Python bypasses VPN.
"""

import subprocess
import sys
import json

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("OPTION B VERIFICATION - Dual Route Test")
print("=" * 70)
print()

# Define Python executables
system_python = "C:\\Program Files\\Python311\\python.exe"
venv_python = "C:\\Users\\dogma\\Projects\\MAMcrawler\\venv\\Scripts\\python.exe"

# Test command to get external IP
test_command = "import requests; print(requests.get('http://httpbin.org/ip', timeout=10).json()['origin'])"

print("[1] Testing System Python (should use VPN)...")
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
        system_ip = result.stdout.strip()
        print(f"  ✅ External IP: {system_ip}")
    else:
        print(f"  ❌ Failed: {result.stderr}")
        system_ip = None
except Exception as e:
    print(f"  ❌ Error: {e}")
    system_ip = None

print()

print("[2] Testing venv Python (should bypass VPN)...")
print("-" * 70)
print(f"  Python: {venv_python}")

try:
    result = subprocess.run(
        [venv_python, '-c', test_command],
        capture_output=True,
        text=True,
        timeout=15
    )

    if result.returncode == 0:
        venv_ip = result.stdout.strip()
        print(f"  ✅ External IP: {venv_ip}")
    else:
        print(f"  ❌ Failed: {result.stderr}")
        venv_ip = None
except Exception as e:
    print(f"  ❌ Error: {e}")
    venv_ip = None

print()
print("=" * 70)
print("RESULTS")
print("=" * 70)

if system_ip and venv_ip:
    if system_ip != venv_ip:
        print("✅ SUCCESS - Two different routes detected!")
        print()
        print(f"  System Python IP: {system_ip} (via VPN)")
        print(f"  venv Python IP:   {venv_ip} (direct WAN)")
        print()
        print("🎉 Your dual scraper is ready to run!")
        print("   Run: python run_dual_scraper.py")
    else:
        print("⚠️  WARNING - Both Python executables use the SAME IP!")
        print()
        print(f"  Both show: {system_ip}")
        print()
        print("Possible issues:")
        print("  1. venv Python is NOT in Split Tunneling excluded apps")
        print("  2. Split Tunneling is in 'Include' mode (should be 'Exclude')")
        print("  3. ProtonVPN is not connected")
        print()
        print("Fix:")
        print("  1. ProtonVPN → Settings → Advanced → Split Tunneling")
        print("  2. Change to: 'Exclude selected apps from VPN tunnel'")
        print("  3. Add: C:\\Users\\dogma\\Projects\\MAMcrawler\\venv\\Scripts\\python.exe")
        print("  4. Restart ProtonVPN and reconnect")
elif system_ip:
    print("⚠️  venv Python test failed but system Python works")
    print(f"  System Python IP: {system_ip}")
    print()
    print("Fix: Check that venv exists and requests library is installed")
elif venv_ip:
    print("⚠️  System Python test failed but venv Python works")
    print(f"  venv Python IP: {venv_ip}")
    print()
    print("Fix: Check system Python path is correct")
else:
    print("❌ Both tests failed")
    print()
    print("Possible issues:")
    print("  1. ProtonVPN not connected")
    print("  2. No internet connection")
    print("  3. requests library not installed")
    print()
    print("Fix:")
    print("  pip install requests")

print("=" * 70)
