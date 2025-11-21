#!/usr/bin/env python
"""
Comprehensive Missing Books Analysis using accurate catalog.
Analyzes the actual library data to identify gaps in major series.
"""

import json
import re
from collections import defaultdict

# Load the comprehensive catalog
with open('comprehensive_catalog.json', 'r', encoding='utf-8') as f:
    catalog = json.load(f)

# Load original library data for book titles and metadata
with open('library_books.json', 'r', encoding='utf-8') as f:
    response = json.load(f)

items = response.get('results', [])

# Build a book lookup by title
books_by_title = {}
for item in items:
    media = item.get('media', {})
    metadata = media.get('metadata', {})
    title = metadata.get('title', '').strip()
    if title:
        books_by_title[title.lower()] = metadata

print("="*80)
print("COMPREHENSIVE MISSING BOOKS ANALYSIS")
print("="*80)

# Define major series that we expect to be complete or nearly complete
# Based on accuracy_missing_books.json
KNOWN_SERIES = {
    'Craig Alanson': {
        'Expeditionary Force': list(range(1, 22)),  # 1-21
    },
    'Brandon Sanderson': {
        'Mistborn': [1, 2, 3, 4, 5],
        'Stormlight Archive': [1, 2, 3, 4, 5],
    },
    'Robert Jordan': {
        'Wheel of Time': list(range(1, 15)),  # 1-14
    },
    'James S. A. Corey': {
        'The Expanse': list(range(1, 10)),  # 1-9
    },
    'Eric Ugland': {
        'The Good Guys': list(range(1, 16)),  # 1-15
    },
    'Aleron Kong': {
        'The Land': list(range(1, 11)),  # 1-10 (Chaos Seeds)
    },
    'Terry Pratchett': {
        'Discworld': list(range(1, 31)),  # 1-30
    },
    'John Scalzi': {
        'Old Man\'s War': list(range(1, 7)),  # 1-6
    },
    'Frank Herbert': {
        'Dune': list(range(1, 7)),  # 1-6
    },
    'Neven Iliev': {
        'Everybody Loves Large Chests': list(range(1, 11)),  # 1-10
    },
    'William D. Arand': {
        'Aether\'s Revival': list(range(1, 6)),  # 1-5
    },
}

# Function to extract series and book number from title
def extract_series_info(title):
    """Extract series name and book number from title."""
    # Pattern: "Series Name #N" or "Series Name Book N"
    patterns = [
        r'([^#]+)#\s*(\d+)',
        r'([^:]+):\s*(?:book|Book)\s*(\d+)',
        r'(.+?)\s+(?:book|Book)\s*(\d+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, title)
        if match:
            series = match.group(1).strip()
            number = int(match.group(2))
            return series, number

    return None, None

# Analyze catalog against known series
missing_summary = {}

for author, series_dict in KNOWN_SERIES.items():
    if author not in catalog:
        print(f"\nAuthor '{author}' not found in catalog")
        continue

    author_catalog = catalog[author]

    for series_name, expected_numbers in series_dict.items():
        print(f"\n{author} - {series_name}")
        print("-" * 60)

        # Find matching series in catalog (fuzzy match)
        matching_series = []
        for catalog_series in author_catalog.keys():
            if series_name.lower() in catalog_series.lower() or \
               catalog_series.lower() in series_name.lower():
                matching_series.append(catalog_series)

        if not matching_series:
            print(f"  No matching series found in catalog")
            print(f"  Expected: {expected_numbers[0]}-{expected_numbers[-1]} ({len(expected_numbers)} books)")
            print(f"  Have: 0 books")
            print(f"  Missing: All {len(expected_numbers)} books")

            missing_summary[f"{author} - {series_name}"] = {
                'total': len(expected_numbers),
                'have': 0,
                'missing': len(expected_numbers),
                'have_numbers': [],
                'missing_numbers': expected_numbers,
            }
            continue

        # Collect all books from matching series
        have_numbers = set()
        have_titles = []

        for series in matching_series:
            books = author_catalog[series]['books']
            for book_title in books:
                have_titles.append(book_title)
                # Try to extract book number
                _, num = extract_series_info(book_title)
                if num:
                    have_numbers.add(num)

        # Also check if numbers appear in the series name/key itself
        for series in matching_series:
            # Extract numbers from series name like "Expeditionary Force #1"
            nums = re.findall(r'#\s*(\d+)', series)
            for num_str in nums:
                have_numbers.add(int(num_str))

        missing_numbers = [n for n in expected_numbers if n not in have_numbers]
        have_list = sorted([n for n in expected_numbers if n in have_numbers])

        print(f"  Catalog series matched: {matching_series}")
        print(f"  Have: {len(have_list)}/{len(expected_numbers)}")
        print(f"  Book numbers: {have_list}")
        if missing_numbers:
            print(f"  Missing: {sorted(missing_numbers)}")

        missing_summary[f"{author} - {series_name}"] = {
            'total': len(expected_numbers),
            'have': len(have_list),
            'missing': len(missing_numbers),
            'have_numbers': have_list,
            'missing_numbers': sorted(missing_numbers),
        }

# Save summary
with open('comprehensive_missing_books_report.json', 'w') as f:
    json.dump(missing_summary, f, indent=2)

# Print overall summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)

total_books = sum(d['total'] for d in missing_summary.values())
total_have = sum(d['have'] for d in missing_summary.values())
total_missing = sum(d['missing'] for d in missing_summary.values())

print(f"\nTotal books analyzed: {total_books}")
print(f"Total you have: {total_have}")
print(f"Total missing: {total_missing}")
if total_books > 0:
    print(f"Completeness: {100*total_have//total_books}%")

print("\n" + "="*80)
print("SERIES STATUS")
print("="*80)

for series_name in sorted(missing_summary.keys()):
    data = missing_summary[series_name]
    pct = 100 * data['have'] // data['total'] if data['total'] > 0 else 0
    status = "COMPLETE" if data['missing'] == 0 else f"MISSING {data['missing']}"
    print(f"{series_name:50} {data['have']:2}/{data['total']:2} ({pct:3}%) {status}")

print("\nComprehensive report saved to: comprehensive_missing_books_report.json")
