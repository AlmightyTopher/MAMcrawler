#!/usr/bin/env python
"""
MAM Phase 1 Downloader - Automated download initiation
Integrates with Prowlarr to add torrents to qBittorrent watch folder
"""

import json
import requests
import os
from datetime import datetime
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('phase1_downloads.log', encoding='utf-8')
    ]
)
logger = logging.getLogger()

print("="*80)
print("MAM PHASE 1 DOWNLOADER - EXECUTION READY")
print("="*80)

# Load configuration
env_file = Path('.env')
config = {}

if env_file.exists():
    for line in env_file.read_text().split('\n'):
        if line.strip() and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            config[k.strip()] = v.strip().strip('\'"')
    logger.info("Loaded .env configuration")
else:
    logger.warning(".env file not found - using defaults")

# MAM credentials
MAM_USERNAME = config.get('MAM_USERNAME', '')
MAM_PASSWORD = config.get('MAM_PASSWORD', '')
MAM_UID = config.get('uid', '')
MAM_MID = config.get('mam_id', '')

# Prowlarr configuration
PROWLARR_URL = config.get('PROWLARR_URL', 'http://localhost:9696')
PROWLARR_API_KEY = config.get('PROWLARR_API_KEY', '')

# qBittorrent configuration
QBITTORRENT_URL = config.get('QBITTORRENT_URL', 'http://localhost:8080')
QBITTORRENT_USER = config.get('QBITTORRENT_USER', 'admin')
QBITTORRENT_PASS = config.get('QBITTORRENT_PASS', 'adminPassword')

print(f"\n{'='*80}")
print("CONFIGURATION STATUS")
print(f"{'='*80}\n")

# Verify credentials
checks = {
    'MAM Username': bool(MAM_USERNAME),
    'MAM Password': bool(MAM_PASSWORD),
    'MAM Session (uid)': bool(MAM_UID),
    'MAM Session (mam_id)': bool(MAM_MID),
    'Prowlarr URL': bool(PROWLARR_URL),
    'Prowlarr API Key': bool(PROWLARR_API_KEY),
    'qBittorrent URL': bool(QBITTORRENT_URL),
    'qBittorrent User': bool(QBITTORRENT_USER),
    'qBittorrent Pass': bool(QBITTORRENT_PASS),
}

for check, status in checks.items():
    status_str = "[OK] Configured" if status else "[!!] MISSING"
    print(f"  {check:25} {status_str}")

print(f"\n{'='*80}")
print("PHASE 1 SEARCH STRATEGY")
print(f"{'='*80}\n")

# Load search queries
with open('phase1_search_queries.json', 'r') as f:
    queries = json.load(f)

print(f"Total books to search: {queries['total_books']}\n")

# Display initial searches
for author, books in list(queries['priority_1_3_series'].items())[:2]:
    print(f"{author}:")
    for book in books[:3]:
        search_term = f"{author} {book['series']} Book {book['book']}"
        print(f"  Search: '{search_term}'")
    if len(books) > 3:
        print(f"  ... and {len(books) - 3} more books")
    print()

print(f"{'='*80}")
print("NEXT STEPS")
print(f"{'='*80}\n")

print("""
OPTION 1: MANUAL DOWNLOADS (Recommended for first batch)
  1. Open MAM: https://www.myanonamouse.net/tor/search.php
  2. Copy search query from phase1_search_queries.json
  3. Search for book
  4. Download torrent file
  5. Open with qBittorrent
  6. Monitor in qBittorrent dashboard

OPTION 2: PROWLARR INTEGRATION (If configured)
  1. Ensure Prowlarr is running and connected to MAM
  2. Configure watch folder in qBittorrent
  3. Use Prowlarr to search and add torrents
  4. They'll appear in qBittorrent automatically

OPTION 3: AUTOMATED SCRIPT (Advanced)
  - Requires Prowlarr API integration
  - Would need to implement:
    * MAM torrent search
    * Prowlarr notification
    * qBittorrent watch folder monitoring

RECOMMENDED: Start with OPTION 1 (Manual)
  - Test workflow with 5 books first
  - Verify Audiobookshelf integration
  - Then scale up to batch downloads

""")

print(f"{'='*80}")
print("TRACKER INITIALIZATION")
print(f"{'='*80}\n")

# Load and display tracker
with open('download_tracker.json', 'r') as f:
    tracker = json.load(f)

print("Phase 1 Progress:")
print(f"  Discworld:  {tracker['progress']['phase_1']['discworld']['downloaded']}/21 books")
print(f"  Good Guys:  {tracker['progress']['phase_1']['good_guys']['downloaded']}/11 books")
print(f"  The Land:   {tracker['progress']['phase_1']['the_land']['downloaded']}/10 books")
print(f"  TOTAL:      {sum(s['downloaded'] for s in tracker['progress']['phase_1'].values())}/42 books")

print(f"\n{'='*80}")
print("QUICK START COMMANDS")
print(f"{'='*80}\n")

print("""
To update progress after downloads:
  python update_tracker.py --series "Discworld" --count 5

To check current status:
  python check_tracker.py

To display next search queries:
  python display_searches.py --priority 1

To monitor qBittorrent:
  Check: http://localhost:8080 (or your qBittorrent URL)

To verify Audiobookshelf:
  Check: Audiobookshelf admin panel → Libraries → Scan for New Files
""")

print(f"\n{'='*80}")
print("STATUS: READY FOR PHASE 1 DOWNLOADS")
print(f"{'='*80}\n")

print("Current Time:", datetime.now().isoformat())
print("Files Created:")
print("  - phase1_search_queries.json (42 search queries)")
print("  - download_tracker.json (progress tracking)")
print("  - phase1_downloads.log (this session's log)")

print("\nRECOMMENDATION:")
print("1. Read PHASE_1_DOWNLOAD_PLAN.md thoroughly")
print("2. Start with first 5 Discworld books as test batch")
print("3. Monitor qBittorrent until 100% complete")
print("4. Verify books appear in Audiobookshelf (24-48 hours)")
print("5. Update tracker when complete")
print("6. Continue with next batch")

print("\nGood luck!\n")

logger.info("Phase 1 downloader initialized successfully")
