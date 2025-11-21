#!/usr/bin/env python
"""
Initiate Downloads - Phase 1 Download Execution
Generates MAM search queries and prepares downloads for Priority 1-3 series
"""

import json
from datetime import datetime

# Load download manifest
with open('download_manifest.json', 'r') as f:
    manifest = json.load(f)

# Load missing books report for detailed info
with open('final_missing_books_report.json', 'r') as f:
    missing_books = json.load(f)

print("="*80)
print("DOWNLOAD PHASE 1 INITIATION")
print("="*80)
print(f"\nStart Time: {datetime.now().isoformat()}")
print(f"Total Books to Download: {manifest['total_to_download']}")

# Focus on Priority 1-3 for initial download phase
priority_1_3 = [item for item in manifest['download_queue'] if item['priority'] <= 3]

print(f"\n{'='*80}")
print("PRIORITY 1-3 SERIES (Initial Focus)")
print(f"{'='*80}\n")

total_phase1 = sum(item['missing_count'] for item in priority_1_3)
print(f"Total books to download in Phase 1: {total_phase1}\n")

for item in priority_1_3:
    series_name = item['series']
    missing_count = item['missing_count']
    missing_numbers = item['missing_numbers']

    print(f"PRIORITY {item['priority']}: {series_name}")
    print(f"  Status: {missing_count} books missing")
    print(f"  Books needed: {missing_numbers}")

    # Get details from missing books report
    if series_name in missing_books:
        data = missing_books[series_name]
        completion = 100 * data['have'] // data['total']
        print(f"  Current completion: {data['have']}/{data['total']} ({completion}%)")

    print()

# Generate search query file
search_queries = {
    'phase': 1,
    'timestamp': datetime.now().isoformat(),
    'total_books': total_phase1,
    'priority_1_3_series': {}
}

# Build search queries for Priority 1-3
for series_name, books in manifest['search_queries'].items():
    # Check if this series is in Priority 1-3
    series_key = None
    for item in priority_1_3:
        if series_name in item['series']:
            series_key = item['series']
            break

    if series_key:
        search_queries['priority_1_3_series'][series_name] = books

# Save search queries
with open('phase1_search_queries.json', 'w') as f:
    json.dump(search_queries, f, indent=2)

print(f"{'='*80}")
print("SEARCH QUERIES FOR PHASE 1")
print(f"{'='*80}\n")

for author, books in search_queries['priority_1_3_series'].items():
    print(f"\n{author}:")
    for book in books[:5]:  # Show first 5
        print(f"  Search: '{author} {book['series']} Book {book['book']}'")
    if len(books) > 5:
        print(f"  ... and {len(books) - 5} more books")

print(f"\n{'='*80}")
print("NEXT STEPS FOR DOWNLOAD PHASE 1")
print(f"{'='*80}\n")

print(f"""
1. Open MAM (MyAnonamouse.net)

2. For each author below, search and download:

   PRIORITY 1: Terry Pratchett - Discworld (21 books)
   - Start with books: 3, 4, 5, 6, 8
   - Look for: Same narrator as your existing books (usually Stephen Briggs)
   - Quality: Prefer 64k+ M4B format

   PRIORITY 2: Eric Ugland - The Good Guys (11 books)
   - Start with books: 1, 2, 4, 5, 6
   - Look for: Narrator consistency with books you have
   - Quality: Usually available in 64-128k M4B

   PRIORITY 3: Aleron Kong - The Land (10 books)
   - Start with books: 1, 2, 3, 4, 5
   - Note: Complete series start from Book 1 (Forging)
   - Quality: Verify bitrate and format

3. Use Prowlarr to add torrents to qBittorrent watch folder
   - Or manually add torrents to qBittorrent

4. Monitor downloads:
   - Check qBittorrent status
   - Verify ratio stays above 1.0
   - Track completion

5. After downloads complete:
   - Files will appear in Audiobookshelf
   - Verify metadata accuracy
   - Re-run analysis to confirm

6. Move to Phase 2 (Priorities 4-6) when Phase 1 is ~50% complete

Total Phase 1 Books: {total_phase1}
Estimated Time: 1-2 weeks depending on availability
Storage Required: ~50-100 GB (estimate)

Saved search queries to: phase1_search_queries.json
""")

print(f"{'='*80}")
print(f"Phase 1 initiation complete at {datetime.now().isoformat()}")
print(f"{'='*80}\n")

print("Files Generated:")
print("  - phase1_search_queries.json (MAM search queries)")
print("\nNext Action: Open MAM and begin searching for Priority 1-3 books")
