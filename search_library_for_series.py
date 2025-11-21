#!/usr/bin/env python
"""Search library for specific authors/series."""

import json

with open('library_books.json', 'r', encoding='utf-8') as f:
    response = json.load(f)

items = response.get('results', [])

# Search for Aleron Kong and The Land
print("="*80)
print("SEARCHING FOR ALERON KONG - THE LAND SERIES")
print("="*80)

for item in items:
    media = item.get('media', {})
    metadata = media.get('metadata', {})
    author = metadata.get('authorName', '').lower()
    series = metadata.get('seriesName', '').lower()
    title = metadata.get('title', '')

    if 'aleron' in author or 'land' in series.lower():
        print(f"\nAuthor: {metadata.get('authorName')}")
        print(f"Series: {metadata.get('seriesName')}")
        print(f"Title: {title}")

print("\n" + "="*80)
print("SEARCHING FOR WILLIAM D. ARAND - AETHER'S REVIVAL")
print("="*80)

for item in items:
    media = item.get('media', {})
    metadata = media.get('metadata', {})
    author = metadata.get('authorName', '').lower()
    title = metadata.get('title', '').lower()

    if 'arand' in author or 'aether' in title:
        print(f"\nAuthor: {metadata.get('authorName')}")
        print(f"Series: {metadata.get('seriesName')}")
        print(f"Title: {metadata.get('title')}")
