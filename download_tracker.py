#!/usr/bin/env python
"""
Download Tracker - Monitor Phase 1-3 download progress
Tracks which books have been downloaded, ratio status, and completion
"""

import json
from datetime import datetime
from pathlib import Path

# Initialize tracker
tracker = {
    'created': datetime.now().isoformat(),
    'phase': 1,
    'phase_1_target': 42,  # Priority 1-3 series
    'total_target': 81,     # All missing books
    'progress': {
        'phase_1': {
            'discworld': {'target': 21, 'downloaded': 0, 'seeding': 0},
            'good_guys': {'target': 11, 'downloaded': 0, 'seeding': 0},
            'the_land': {'target': 10, 'downloaded': 0, 'seeding': 0},
        },
        'phase_2': {
            'expeditionary_force': {'target': 9, 'downloaded': 0, 'seeding': 0},
            'everybody_loves': {'target': 8, 'downloaded': 0, 'seeding': 0},
            'the_expanse': {'target': 7, 'downloaded': 0, 'seeding': 0},
        },
        'phase_3': {
            'aethers_revival': {'target': 5, 'downloaded': 0, 'seeding': 0},
            'dune': {'target': 4, 'downloaded': 0, 'seeding': 0},
            'stormlight': {'target': 3, 'downloaded': 0, 'seeding': 0},
            'old_mans_war': {'target': 2, 'downloaded': 0, 'seeding': 0},
            'mistborn': {'target': 1, 'downloaded': 0, 'seeding': 0},
        }
    },
    'downloads': [],  # List of downloaded torrents
    'ratio_status': {
        'current_ratio': 0.0,
        'target_ratio': 1.0,
        'min_ratio': 0.5,
        'last_checked': None
    },
    'milestones': [
        {'name': 'Complete Priority 1', 'target_books': 42, 'status': 'pending'},
        {'name': 'Complete Priorities 2-3', 'target_books': 42, 'status': 'pending'},
        {'name': 'Complete All 81 Books', 'target_books': 81, 'status': 'pending'},
        {'name': 'Achieve 100% Series Completion', 'target_books': 81, 'status': 'pending'},
    ]
}

# Save initial tracker
with open('download_tracker.json', 'w') as f:
    json.dump(tracker, f, indent=2)

print("="*80)
print("DOWNLOAD TRACKER INITIALIZED")
print("="*80)

print(f"\nStart Time: {datetime.now().isoformat()}\n")

print("PHASE 1 TARGETS (42 books):")
print("  - Terry Pratchett - Discworld: 21 books")
print("  - Eric Ugland - The Good Guys: 11 books")
print("  - Aleron Kong - The Land: 10 books")

print("\nPHASE 2 TARGETS (24 books):")
print("  - Craig Alanson - Expeditionary Force: 9 books")
print("  - Neven Iliev - Everybody Loves Large Chests: 8 books")
print("  - James S. A. Corey - The Expanse: 7 books")

print("\nPHASE 3 TARGETS (15 books):")
print("  - William D. Arand - Aether's Revival: 5 books")
print("  - Frank Herbert - Dune: 4 books")
print("  - Brandon Sanderson - Stormlight Archive: 3 books")
print("  - John Scalzi - Old Man's War: 2 books")
print("  - Brandon Sanderson - Mistborn: 1 book")

print("\n" + "="*80)
print("TRACKING INSTRUCTIONS")
print("="*80)

print("""
To update download progress:

1. After each download completes:
   python update_tracker.py --series "Discworld" --books 3,4,5 --ratio 1.15

2. To check current status:
   python check_tracker_status.py

3. To get next series to download:
   python get_next_priority.py

To manually update tracker.json:
- Edit download_tracker.json directly
- Update 'downloaded' count for each series
- Update 'ratio_status' as needed

Tracking Milestones:
  [ ] Complete Priority 1 (42 books)
  [ ] Complete Priorities 2-3 (24 + 15 books)
  [ ] Complete all 81 missing books
  [ ] Achieve 100% series completion

Current Status: READY FOR PHASE 1 DOWNLOADS
Files Created:
  - download_tracker.json (tracking data)
  - phase1_search_queries.json (MAM search queries)
""")

print("="*80)
print("Tracker file: download_tracker.json")
print("="*80)
