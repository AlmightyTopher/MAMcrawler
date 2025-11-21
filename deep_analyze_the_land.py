#!/usr/bin/env python
"""Deep analysis of The Land series in library."""

import json
import re

with open('library_books.json', 'r', encoding='utf-8') as f:
    response = json.load(f)

items = response.get('results', [])

print("="*80)
print("THE LAND SERIES - DETAILED ANALYSIS")
print("="*80)

land_books = []

for item in items:
    media = item.get('media', {})
    metadata = media.get('metadata', {})

    author = metadata.get('authorName', '')
    title = metadata.get('title', '')

    if author == 'Aleron Kong':
        land_books.append({
            'title': title,
            'series': metadata.get('seriesName', ''),
            'author': author
        })

print(f"\nFound {len(land_books)} books by Aleron Kong\n")

# Group by series
series_groups = {}
for book in land_books:
    series = book['series'] if book['series'] else 'Unknown Series'
    if series not in series_groups:
        series_groups[series] = []
    series_groups[series].append(book['title'])

for series, titles in sorted(series_groups.items()):
    print(f"{series} ({len(titles)} books)")
    for title in titles:
        # Try to extract book number
        num_match = re.search(r'\b(\d+)\b', title)
        if num_match:
            print(f"  {num_match.group(1):2}: {title}")
        else:
            print(f"      {title}")

# Now try to match "The Land" books specifically
print("\n" + "="*80)
print("TRYING TO IDENTIFY THE LAND SEQUENCE")
print("="*80)

the_land_titles = [b for b in land_books if 'land' in b['title'].lower()]
print(f"\nBooks with 'Land' in title ({len(the_land_titles)}):")
for book in sorted(the_land_titles, key=lambda b: b['title']):
    print(f"  {book['title']}")
    # Try to extract sequence
    if 'forging' in book['title'].lower():
        print("    -> Appears to be Book 1 (Forging)")
    elif 'catacombs' in book['title'].lower():
        print("    -> Appears to be Book 2 (Catacombs)")
    elif 'swarm' in book['title'].lower():
        print("    -> Appears to be Book 3 (Swarm)")
    elif 'alliances' in book['title'].lower():
        print("    -> Appears to be Book 4 (Alliances)")
    elif 'raiders' in book['title'].lower():
        print("    -> Appears to be Book 5 (Raiders)")
    elif 'founding' in book['title'].lower():
        print("    -> Appears to be Book ? (Founding)")
