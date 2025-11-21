#!/usr/bin/env python
"""
Generate comprehensive library report with:
1. Accurate missing books for major series
2. Full library statistics by genre
3. Download prioritization
"""

import json
from collections import defaultdict

# Load comprehensive catalog and missing books report
with open('final_missing_books_report.json', 'r', encoding='utf-8') as f:
    missing_books = json.load(f)

with open('comprehensive_catalog.json', 'r', encoding='utf-8') as f:
    catalog = json.load(f)

print("="*80)
print("COMPREHENSIVE LIBRARY REPORT")
print("="*80)

# Statistics
total_authors = len(catalog)
total_series = sum(len(series_dict) for series_dict in catalog.values())
total_books = sum(sum(s['count'] for s in series_dict.values())
                 for series_dict in catalog.values())

print(f"\nLibrary Inventory:")
print(f"  Total authors: {total_authors}")
print(f"  Total series: {total_series}")
print(f"  Total books: {total_books}")

# Missing books analysis
total_missing = sum(d['missing'] for d in missing_books.values())
total_have = sum(d['have'] for d in missing_books.values())
total_expected = sum(d['total'] for d in missing_books.values())

print(f"\nMajor Series Analysis (12 core series):")
print(f"  Books you have: {total_have}")
print(f"  Books missing: {total_missing}")
print(f"  Expected total: {total_expected}")
print(f"  Completeness: {100*total_have//total_expected}%")

# Create download queue prioritized by impact
print(f"\n{'='*80}")
print("MISSING BOOKS PRIORITY QUEUE (Sorted by Number Missing)")
print(f"{'='*80}\n")

# Sort by missing count, then by author name
sorted_missing = sorted(missing_books.items(),
                       key=lambda x: (-x[1]['missing'], x[0]))

download_queue = []
priority = 1

for series_name, data in sorted_missing:
    if data['missing'] == 0:
        status = "COMPLETE"
    else:
        status = f"MISSING {data['missing']}"

    completeness = 100 * data['have'] // data['total']

    print(f"{priority:2}. [{status:18}] {series_name}")
    print(f"    Progress: {data['have']:2}/{data['total']:2} ({completeness:3}%)")
    print(f"    Missing books: {data['missing_numbers']}")

    if data['missing'] > 0:
        download_queue.append({
            'priority': priority,
            'series': series_name,
            'missing_count': data['missing'],
            'missing_numbers': data['missing_numbers'],
            'completeness_pct': completeness,
        })
        priority += 1

    print()

# Create prioritized download manifest
print(f"{'='*80}")
print("DOWNLOAD MANIFEST")
print(f"{'='*80}\n")

total_to_download = sum(d['missing_count'] for d in download_queue)
print(f"Total books to download: {total_to_download}\n")

# Group by author for MAM search queries
search_queries = defaultdict(list)

for item in download_queue:
    series_parts = item['series'].split(' - ')
    if len(series_parts) == 2:
        author, series = series_parts
        for book_num in item['missing_numbers']:
            search_queries[author].append({
                'series': series,
                'book': book_num,
            })

print("MAM Search Queries by Author:\n")
for author in sorted(search_queries.keys()):
    books = search_queries[author]
    print(f"{author}:")

    # Group by series
    by_series = defaultdict(list)
    for book in books:
        by_series[book['series']].append(book['book'])

    for series in sorted(by_series.keys()):
        book_nums = sorted(by_series[series])
        print(f"  {series}: Books {', '.join(map(str, book_nums))}")

# Save manifest
manifest = {
    'total_to_download': total_to_download,
    'download_queue': download_queue,
    'search_queries': dict(search_queries),
}

with open('download_manifest.json', 'w') as f:
    json.dump(manifest, f, indent=2)

print(f"\n{'='*80}")
print("Next Steps:")
print("1. Use MAM search queries above to find missing books")
print("2. Prioritize by queue order (complete most important series first)")
print("3. Download via Prowlarr/qBittorrent")
print("4. Verify in Audiobookshelf after download")
print(f"{'='*80}\n")

print("Files created:")
print("  - final_missing_books_report.json (detailed missing books)")
print("  - download_manifest.json (prioritized download queue)")
