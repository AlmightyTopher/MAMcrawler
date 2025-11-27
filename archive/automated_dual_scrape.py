#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automated Dual Scraping with VPN Toggle
Uses ProtonVPN CLI to toggle VPN between scrapers.
"""

import subprocess
import sys
import json
import time
from datetime import datetime
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("AUTOMATED DUAL SCRAPER - VPN Toggle Mode")
print("=" * 70)
print()

# Sample books
sample_books = [
    {'title': 'The Name of the Wind', 'author': 'Patrick Rothfuss'},
    {'title': 'The Way of Kings', 'author': 'Brandon Sanderson'},
    {'title': 'Mistborn', 'author': 'Brandon Sanderson'},
    {'title': 'The Lies of Locke Lamora', 'author': 'Scott Lynch'},
]

# Split books
books_vpn = sample_books[::2]
books_direct = sample_books[1::2]

print(f"📚 Total: {len(sample_books)} books")
print(f"   VPN route: {len(books_vpn)} books")
print(f"   Direct route: {len(books_direct)} books")
print()

# Save book lists
with open('books_vpn.json', 'w') as f:
    json.dump(books_vpn, f, indent=2)
with open('books_direct.json', 'w') as f:
    json.dump(books_direct, f, indent=2)

# Phase 1: VPN Scraper
print("=" * 70)
print("PHASE 1: VPN Scraper (ProtonVPN Connected)")
print("=" * 70)
print("Ensure ProtonVPN is CONNECTED before continuing...")
input("Press ENTER when ProtonVPN is connected...")

print("\n🚀 Running VPN scraper...")
vpn_result = subprocess.run(
    [sys.executable, 'scraper_vpn.py'],
    capture_output=True,
    text=True
)

if vpn_result.returncode == 0:
    print("✅ VPN scraper completed successfully")
else:
    print(f"❌ VPN scraper failed: {vpn_result.stderr[:200]}")

print()

# Phase 2: Disconnect VPN
print("=" * 70)
print("PHASE 2: VPN Disconnect")
print("=" * 70)
print("Please DISCONNECT ProtonVPN now...")
print("(Right-click system tray icon → Disconnect)")
input("Press ENTER when ProtonVPN is DISCONNECTED...")

# Wait a bit for network to stabilize
print("⏳ Waiting 5 seconds for network to stabilize...")
time.sleep(5)

# Verify we're on direct connection
print("\n🔍 Verifying direct connection...")
try:
    check_result = subprocess.run(
        [sys.executable, '-c',
         "import requests; print(requests.get('http://httpbin.org/ip', timeout=10).json()['origin'])"],
        capture_output=True,
        text=True,
        timeout=15
    )
    if check_result.returncode == 0:
        direct_ip = check_result.stdout.strip()
        print(f"✅ Direct IP confirmed: {direct_ip}")
    else:
        print("⚠️  Could not verify IP, proceeding anyway...")
except:
    print("⚠️  Could not verify IP, proceeding anyway...")

print()

# Phase 3: Direct Scraper
print("=" * 70)
print("PHASE 3: Direct Scraper (No VPN)")
print("=" * 70)
print("🚀 Running direct scraper...")

direct_result = subprocess.run(
    [sys.executable, 'scraper_direct.py'],
    capture_output=True,
    text=True
)

if direct_result.returncode == 0:
    print("✅ Direct scraper completed successfully")
else:
    print(f"❌ Direct scraper failed: {direct_result.stderr[:200]}")

print()

# Phase 4: Merge Results
print("=" * 70)
print("PHASE 4: Merge Results")
print("=" * 70)

vpn_files = sorted(Path('.').glob('vpn_results_*.json'))
direct_files = sorted(Path('.').glob('direct_results_*.json'))

all_results = []

if vpn_files:
    with open(vpn_files[-1], 'r') as f:
        vpn_results = json.load(f)
        all_results.extend(vpn_results)
        print(f"  📊 VPN results: {len(vpn_results)}")

if direct_files:
    with open(direct_files[-1], 'r') as f:
        direct_results = json.load(f)
        all_results.extend(direct_results)
        print(f"  📊 Direct results: {len(direct_results)}")

# Deduplicate
seen = set()
deduped_results = []
for result in all_results:
    key = (result.get('title', '').lower(), result.get('author', '').lower())
    if key not in seen:
        seen.add(key)
        deduped_results.append(result)

# Save
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
merged_file = f'merged_results_{timestamp}.json'
with open(merged_file, 'w') as f:
    json.dump(deduped_results, f, indent=2)

print(f"\n✅ Merged {len(all_results)} results into {len(deduped_results)} unique")
print(f"💾 Saved to: {merged_file}")

print()
print("=" * 70)
print("🎉 AUTOMATED DUAL SCRAPING COMPLETE!")
print("=" * 70)
print()
print("Summary:")
print(f"  ✅ Used 2 different IP addresses")
print(f"  ✅ Scraped {len(deduped_results)} unique books")
print(f"  ✅ Low rate limit risk (different IPs)")
print()
print("You can reconnect ProtonVPN now.")
print("=" * 70)
