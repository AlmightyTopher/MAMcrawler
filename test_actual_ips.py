#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test actual IPs used by each scraper
"""

import subprocess
import sys
import json
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("ACTUAL IP TEST - What Goodreads Would See")
print("=" * 70)
print()

# Define Python executables
system_python = "C:\\Program Files\\Python311\\python.exe"
venv_python = "C:\\Users\\dogma\\Projects\\MAMcrawler\\venv\\Scripts\\python.exe"

# Create test script that mimics scraper behavior
test_script = """
import requests
import sys

try:
    response = requests.get('http://httpbin.org/ip', timeout=10)
    data = response.json()
    print(f"IP: {data['origin']}")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
"""

# Save test script
with open('_test_ip_temp.py', 'w') as f:
    f.write(test_script)

print("[1] Testing VPN Scraper (System Python)...")
print("-" * 70)
vpn_result = subprocess.run(
    [system_python, '_test_ip_temp.py'],
    capture_output=True,
    text=True,
    timeout=15
)

if vpn_result.returncode == 0:
    vpn_ip = vpn_result.stdout.strip().replace('IP: ', '')
    print(f"  ✅ VPN Scraper would appear as: {vpn_ip}")
else:
    print(f"  ❌ Failed: {vpn_result.stderr}")
    vpn_ip = None

print()

print("[2] Testing Direct Scraper (venv Python)...")
print("-" * 70)
direct_result = subprocess.run(
    [venv_python, '_test_ip_temp.py'],
    capture_output=True,
    text=True,
    timeout=15
)

if direct_result.returncode == 0:
    direct_ip = direct_result.stdout.strip().replace('IP: ', '')
    print(f"  ✅ Direct Scraper would appear as: {direct_ip}")
else:
    print(f"  ❌ Failed: {direct_result.stderr}")
    direct_ip = None

print()
print("=" * 70)
print("WHAT GOODREADS WOULD SEE")
print("=" * 70)

if vpn_ip and direct_ip:
    if vpn_ip != direct_ip:
        print("✅ SUCCESS - Goodreads would see TWO DIFFERENT users!")
        print()
        print(f"  User 1 (VPN Scraper):    {vpn_ip}")
        print(f"  User 2 (Direct Scraper): {direct_ip}")
        print()
        print("🎉 Your dual scraper setup is WORKING!")
    else:
        print("⚠️  WARNING - Goodreads would see the SAME user (same IP)")
        print()
        print(f"  Both scrapers show: {vpn_ip}")
        print()
        print("ProtonVPN Split Tunneling Exclude mode is NOT working.")
        print()
        print("Options:")
        print("  A) Accept both use VPN (rely on different user agents/timing)")
        print("  B) Manually disconnect VPN, run one scraper, reconnect")
        print("  C) Use a different VPN/proxy service that supports split tunneling")
        print("  D) Run scrapers at different times (not simultaneously)")

# Cleanup
import os
if os.path.exists('_test_ip_temp.py'):
    os.remove('_test_ip_temp.py')

print("=" * 70)
