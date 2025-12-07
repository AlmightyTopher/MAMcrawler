#!/usr/bin/env python
"""Phase 1 Status Check - Simple utility"""

import json
from pathlib import Path

# Load tracker
with open('download_tracker.json', 'r') as f:
    tracker = json.load(f)

# Load search queries
with open('phase1_search_queries.json', 'r') as f:
    queries = json.load(f)

print("=" * 80)
print("PHASE 1 STATUS CHECK")
print("=" * 80)

print("\nConfiguration:")
env = Path('.env').exists()
print(f"  .env file: {'Found' if env else 'NOT FOUND'}")

print("\nSearch Queries Ready:")
print(f"  Total books: {queries['total_books']}")
for author in queries['priority_1_3_series']:
    count = len(queries['priority_1_3_series'][author])
    print(f"  {author}: {count} books")

print("\nPhase 1 Progress:")
phase1 = tracker['progress']['phase_1']
total = 0
for series, data in phase1.items():
    progress = data['downloaded']
    target = data['target']
    total += target
    print(f"  {series.replace('_', ' ').title():20} {progress:2}/{target:2} books")

print(f"\n  TOTAL: {sum(s['downloaded'] for s in phase1.values())}/{total} books")

print("\nNext Action:")
print("  1. Read PHASE_1_DOWNLOAD_PLAN.md")
print("  2. Open MAM: https://www.myanonamouse.net/tor/search.php")
print("  3. Search first book: Terry Pratchett Discworld Book 3")
print("  4. Download and monitor in qBittorrent")

print("\nStatus: READY TO START DOWNLOADS")
print("=" * 80)
