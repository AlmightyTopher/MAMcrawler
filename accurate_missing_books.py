#!/usr/bin/env python
"""
Accurate Missing Books Report - Fixed matching logic
"""

import json
import re
from collections import defaultdict

# Load library
with open('library_books.json', 'r', encoding='utf-8') as f:
    response = json.load(f)

items = response.get('results', [])

# Build comprehensive library index
library_index = defaultdict(lambda: {'full_paths': [], 'series': set()})

for item in items:
    path = item.get('relPath', '').lower()

    # Extract author if possible
    # Try pattern: "Author - Title"
    author_match = re.match(r'^([^-]+?)\s*-\s*(.+)$', path)
    if author_match:
        author = author_match.group(1).strip()
        title = author_match.group(2).strip()
    else:
        author = 'Unknown'
        title = path

    # Extract series name and number
    series_match = re.search(r'(.+?)\s*(?:book|#|vol|series)\s*(\d+)', title, re.IGNORECASE)
    if series_match:
        series = series_match.group(1).strip()
        num = int(series_match.group(2))
    else:
        series = title
        num = None

    library_index[(author.title(), series)]['full_paths'].append(path)
    if num:
        library_index[(author.title(), series)]['series'].add(num)

print('='*80)
print('ACCURATE MISSING BOOKS ANALYSIS')
print('='*80)

# Known series to analyze
series_to_check = {
    ('Craig Alanson', 'Expeditionary Force'): list(range(1, 22)),  # Books 1-21
    ('Brandon Sanderson', 'Mistborn'): [1, 2, 3, 4, 5],
    ('Brandon Sanderson', 'Stormlight Archive'): [1, 2, 3, 4, 5],
    ('Robert Jordan', 'Wheel of Time'): list(range(1, 15)),
    ('James S. A. Corey', 'The Expanse'): list(range(1, 10)),
    ('Eric Ugland', 'The Good Guys'): list(range(1, 16)),
    ('Aleron Kong', 'The Land'): list(range(1, 11)),
    ('Terry Pratchett', 'Discworld'): list(range(1, 31)),
    ('John Scalzi', 'Old Man\'s War'): list(range(1, 7)),
    ('Frank Herbert', 'Dune'): list(range(1, 7)),
    ('Neven Iliev', 'Everybody Loves Large Chests'): list(range(1, 11)),
    ('William D. Arand', 'Aether\'s Revival'): list(range(1, 6)),
}

missing_summary = {}

for (author, series), book_numbers in series_to_check.items():
    # Find all case variations
    found_books = set()

    for (lib_author, lib_series), data in library_index.items():
        if (author.lower() in lib_author.lower() or lib_author.lower() in author.lower()) and \
           (series.lower() in lib_series.lower() or lib_series.lower() in series.lower()):
            found_books.update(data['series'])

    missing = [num for num in book_numbers if num not in found_books]
    have = [num for num in book_numbers if num in found_books]

    if missing or have:
        missing_summary[f'{author} - {series}'] = {
            'total': len(book_numbers),
            'have': len(have),
            'missing': len(missing),
            'have_numbers': sorted(have),
            'missing_numbers': sorted(missing),
        }

        print(f'\n{author} - {series}')
        print(f'  Have: {len(have)}/{len(book_numbers)}')
        print(f'  Books: {sorted(have)}')
        if missing:
            print(f'  Missing: {sorted(missing)}')

# Save accurate report
with open('accurate_missing_books.json', 'w') as f:
    json.dump(missing_summary, f, indent=2)

print('\n\n' + '='*80)
print('SUMMARY')
print('='*80)

total_books = sum(data['total'] for data in missing_summary.values())
total_have = sum(data['have'] for data in missing_summary.values())
total_missing = sum(data['missing'] for data in missing_summary.values())

print(f'\nTotal books analyzed: {total_books}')
print(f'Total you have: {total_have}')
print(f'Total missing: {total_missing}')
print(f'Completeness: {100*total_have//total_books}%')

print('\nReport saved to: accurate_missing_books.json')
