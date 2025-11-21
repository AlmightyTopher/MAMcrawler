#!/usr/bin/env python
"""
Generate comprehensive library catalog using actual Audiobookshelf metadata.
Uses authorName and seriesName from media metadata instead of parsing filenames.
"""

import json
from collections import defaultdict
from pathlib import Path

# Load library data
with open('library_books.json', 'r', encoding='utf-8') as f:
    response = json.load(f)

items = response.get('results', [])

# Build catalog structure
catalog = defaultdict(lambda: defaultdict(lambda: {
    'count': 0,
    'books': [],
    'book_numbers': set()
}))

print("="*80)
print("COMPREHENSIVE LIBRARY CATALOG GENERATION")
print("="*80)
print(f"\nProcessing {len(items)} items...\n")

# Track statistics
authors_found = set()
series_found = set()
matched_with_metadata = 0
unmatched_items = 0
items_with_series = 0
items_without_series = 0

# Process each item
for item in items:
    try:
        media = item.get('media', {})
        metadata = media.get('metadata', {})

        # Get author and series from metadata
        author = metadata.get('authorName', '').strip() or 'Unknown Author'
        series = metadata.get('seriesName', '').strip() or 'Standalone'
        title = metadata.get('title', '').strip() or item.get('relPath', 'Unknown')

        authors_found.add(author)
        series_found.add(series)

        if series != 'Standalone':
            items_with_series += 1
        else:
            items_without_series += 1

        # Add to catalog
        catalog[author][series]['count'] += 1
        catalog[author][series]['books'].append({
            'title': title,
            'path': item.get('relPath', ''),
            'id': item.get('id', '')
        })
        matched_with_metadata += 1

    except Exception as e:
        print(f"Error processing item: {e}")
        unmatched_items += 1

# Convert to JSON-serializable format
catalog_json = {}
for author in sorted(catalog.keys()):
    catalog_json[author] = {}
    for series in sorted(catalog[author].keys()):
        catalog_json[author][series] = {
            'count': catalog[author][series]['count'],
            'books': [b['title'] for b in catalog[author][series]['books']]
        }

# Save catalog
with open('comprehensive_catalog.json', 'w', encoding='utf-8') as f:
    json.dump(catalog_json, f, indent=2, ensure_ascii=False)

print(f"\nCatalog Statistics:")
print(f"  Total items processed: {len(items)}")
print(f"  Matched with metadata: {matched_with_metadata}")
print(f"  Unmatched items: {unmatched_items}")
print(f"  Unique authors: {len(authors_found)}")
print(f"  Unique series: {len(series_found)}")
print(f"  Items with series: {items_with_series}")
print(f"  Standalone items: {items_without_series}")

# Print top 20 authors by book count
print(f"\n{'='*80}")
print("TOP 20 AUTHORS BY BOOK COUNT")
print(f"{'='*80}\n")

author_counts = [(author, sum(s['count'] for s in catalog[author].values()))
                 for author in catalog.keys()]
author_counts.sort(key=lambda x: x[1], reverse=True)

for i, (author, count) in enumerate(author_counts[:20], 1):
    series_count = len(catalog[author])
    print(f"{i:2}. {author:40} {count:3} books in {series_count:2} series")

# Print all series for top 5 authors
print(f"\n{'='*80}")
print("SERIES BREAKDOWN FOR TOP 5 AUTHORS")
print(f"{'='*80}\n")

for author, count in author_counts[:5]:
    print(f"\n{author} ({count} books)")
    print("-" * 60)
    for series in sorted(catalog[author].keys()):
        series_count = catalog[author][series]['count']
        print(f"  {series:45} {series_count:3} books")

print(f"\n\nComprehensive catalog saved to: comprehensive_catalog.json")
