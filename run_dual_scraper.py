#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dual Scraper Orchestrator
Runs both VPN and Direct scrapers simultaneously in separate processes.
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
print("DUAL GOODREADS SCRAPER - OPTION B (NO SOCKS5)")
print("=" * 70)
print()
print("Architecture:")
print("  VPN Scraper:    System Python → ALL traffic through ProtonVPN")
print("  Direct Scraper: venv Python   → Excluded from VPN (direct WAN)")
print()
print("=" * 70)
print()

# Define Python executables
system_python = "C:\\Program Files\\Python311\\python.exe"
venv_python = "./venv/Scripts/python.exe"

# Sample books for testing
sample_books = [
    {'title': 'The Name of the Wind', 'author': 'Patrick Rothfuss'},
    {'title': 'The Way of Kings', 'author': 'Brandon Sanderson'},
    {'title': 'Mistborn', 'author': 'Brandon Sanderson'},
    {'title': 'The Lies of Locke Lamora', 'author': 'Scott Lynch'},
]

# Split books between scrapers
books_vpn = sample_books[::2]  # Even indices
books_direct = sample_books[1::2]  # Odd indices

print(f"Total books: {len(sample_books)}")
print(f"VPN route: {len(books_vpn)} books")
print(f"Direct route: {len(books_direct)} books")
print()

# Save book lists for each scraper
with open('books_vpn.json', 'w') as f:
    json.dump(books_vpn, f, indent=2)

with open('books_direct.json', 'w') as f:
    json.dump(books_direct, f, indent=2)

print("Starting scrapers in parallel...")
print("-" * 70)

# Launch both scrapers simultaneously
process_vpn = subprocess.Popen(
    [system_python, 'scraper_vpn.py'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

process_direct = subprocess.Popen(
    [venv_python, 'scraper_direct.py'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

print(f"  VPN Scraper launched (PID: {process_vpn.pid})")
print(f"  Direct Scraper launched (PID: {process_direct.pid})")
print()
print("Both scrapers running... (check log files for progress)")
print("  - scraper_vpn.log")
print("  - scraper_direct.log")
print()

# Wait for both to complete
print("Waiting for scrapers to complete...")
vpn_out, vpn_err = process_vpn.communicate()
direct_out, direct_err = process_direct.communicate()

print()
print("=" * 70)
print("SCRAPING COMPLETE")
print("=" * 70)

if process_vpn.returncode == 0:
    print("✅ VPN Scraper: Success")
else:
    print(f"❌ VPN Scraper: Failed (exit code {process_vpn.returncode})")
    if vpn_err:
        print(f"   Error: {vpn_err[:200]}")

if process_direct.returncode == 0:
    print("✅ Direct Scraper: Success")
else:
    print(f"❌ Direct Scraper: Failed (exit code {process_direct.returncode})")
    if direct_err:
        print(f"   Error: {direct_err[:200]}")

print()

# Merge results
print("Merging results...")
vpn_files = sorted(Path('.').glob('vpn_results_*.json'))
direct_files = sorted(Path('.').glob('direct_results_*.json'))

all_results = []

if vpn_files:
    with open(vpn_files[-1], 'r') as f:
        vpn_results = json.load(f)
        all_results.extend(vpn_results)
        print(f"  VPN results: {len(vpn_results)}")

if direct_files:
    with open(direct_files[-1], 'r') as f:
        direct_results = json.load(f)
        all_results.extend(direct_results)
        print(f"  Direct results: {len(direct_results)}")

# Deduplicate
seen = set()
deduped_results = []
for result in all_results:
    key = (result.get('title', '').lower(), result.get('author', '').lower())
    if key not in seen:
        seen.add(key)
        deduped_results.append(result)

# Save merged results
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
merged_file = f'merged_results_{timestamp}.json'
with open(merged_file, 'w') as f:
    json.dump(deduped_results, f, indent=2)

print()
print(f"📊 Merged {len(all_results)} raw results into {len(deduped_results)} unique results")
print(f"💾 Saved to: {merged_file}")
print()
print("=" * 70)
print("DONE!")
print("=" * 70)
