#!/usr/bin/env python
"""
Final comprehensive missing books analysis.
Uses intelligent matching:
1. First tries Audiobookshelf metadata (authorName, seriesName)
2. Falls back to title parsing with regex when metadata is incomplete
3. Builds complete picture of what's missing
"""

import json
import re
from collections import defaultdict

# Load original library data
with open('library_books.json', 'r', encoding='utf-8') as f:
    response = json.load(f)

items = response.get('results', [])

print("="*80)
print("FINAL COMPREHENSIVE MISSING BOOKS ANALYSIS")
print("="*80)

# Extract book number from title using multiple strategies
def extract_book_number(title):
    """Try to extract book/chapter number from title."""
    patterns = [
        r'\bBook\s+(\d+)',
        r'#\s*(\d+)',
        r'\b(\d+)\b:\s',  # "1: Title"
        r'\:\s*Book\s+(\d+)',
        r'(?:Part|Chapter|Vol|Volume)\s+(\d+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return None

# Define major series to analyze
KNOWN_SERIES = {
    'Craig Alanson': {
        'Expeditionary Force': list(range(1, 22)),
    },
    'Brandon Sanderson': {
        'Mistborn': [1, 2, 3, 4, 5],
        'Stormlight Archive': [1, 2, 3, 4, 5],
    },
    'Robert Jordan': {
        'Wheel of Time': list(range(1, 15)),
    },
    'James S. A. Corey': {
        'The Expanse': list(range(1, 10)),
    },
    'Eric Ugland': {
        'The Good Guys': list(range(1, 16)),
    },
    'Aleron Kong': {
        'The Land': list(range(1, 11)),
    },
    'Terry Pratchett': {
        'Discworld': list(range(1, 31)),
    },
    'John Scalzi': {
        'Old Man\'s War': list(range(1, 7)),
    },
    'Frank Herbert': {
        'Dune': list(range(1, 7)),
    },
    'Neven Iliev': {
        'Everybody Loves Large Chests': list(range(1, 11)),
    },
    'William D. Arand': {
        'Aether\'s Revival': list(range(1, 6)),
    },
}

missing_summary = {}

for author_key, series_dict in KNOWN_SERIES.items():
    for series_key, expected_numbers in series_dict.items():
        print(f"\n{author_key} - {series_key}")
        print("-" * 70)

        have_numbers = set()
        have_titles = []

        # Search library for matching books
        for item in items:
            media = item.get('media', {})
            metadata = media.get('metadata', {})

            item_author = metadata.get('authorName', '').strip()
            item_series = metadata.get('seriesName', '').strip()
            item_title = metadata.get('title', '').strip()

            # Match by metadata first
            if item_author.lower() == author_key.lower() or \
               item_author.lower() in author_key.lower():
                # Check if series matches
                if series_key.lower() in item_series.lower() or \
                   item_series.lower() in series_key.lower():
                    # Extract number from metadata series
                    num = extract_book_number(item_series)
                    if num:
                        have_numbers.add(num)
                    have_titles.append(item_title)
                    continue

            # Fallback: Match by title if metadata is incomplete
            if item_author.lower() == author_key.lower() or \
               item_author.lower() in author_key.lower():
                if series_key.lower() in item_title.lower():
                    num = extract_book_number(item_title)
                    if num:
                        have_numbers.add(num)
                    have_titles.append(item_title)
                    print(f"  [Title match] {item_title}")

        have_list = sorted([n for n in expected_numbers if n in have_numbers])
        missing_numbers = sorted([n for n in expected_numbers if n not in have_numbers])

        print(f"  Have: {len(have_list)}/{len(expected_numbers)}")
        if have_list:
            print(f"  Book numbers: {have_list}")
        if missing_numbers:
            print(f"  Missing: {missing_numbers}")

        # Show a few example titles
        if have_titles:
            print(f"  Examples: {', '.join(have_titles[:2])}")

        missing_summary[f"{author_key} - {series_key}"] = {
            'total': len(expected_numbers),
            'have': len(have_list),
            'missing': len(missing_numbers),
            'have_numbers': have_list,
            'missing_numbers': missing_numbers,
            'example_titles': have_titles[:3] if have_titles else [],
        }

# Save and print summary
with open('final_missing_books_report.json', 'w') as f:
    json.dump(missing_summary, f, indent=2)

print("\n" + "="*80)
print("FINAL SUMMARY")
print("="*80)

total_books = sum(d['total'] for d in missing_summary.values())
total_have = sum(d['have'] for d in missing_summary.values())
total_missing = sum(d['missing'] for d in missing_summary.values())

print(f"\nTotal books analyzed: {total_books}")
print(f"Total you have: {total_have}")
print(f"Total missing: {total_missing}")
if total_books > 0:
    print(f"Overall completeness: {100*total_have//total_books}%")

# Breakdown by series
print(f"\n{'='*80}")
print("PRIORITY RANKING (Most Books Missing)")
print(f"{'='*80}\n")

sorted_series = sorted(missing_summary.items(),
                      key=lambda x: x[1]['missing'],
                      reverse=True)

for i, (series_name, data) in enumerate(sorted_series, 1):
    pct = 100 * data['have'] // data['total'] if data['total'] > 0 else 0
    print(f"{i:2}. {series_name:50}")
    print(f"    {data['have']:2}/{data['total']:2} ({pct:3}%) - Missing: {data['missing_numbers']}")

print(f"\nFinal report saved to: final_missing_books_report.json")
