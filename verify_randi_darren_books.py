#!/usr/bin/env python3
"""
Verify Randi Darren books are in Audiobookshelf library
"""
import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def verify_books():
    abs_url = os.getenv('ABS_URL', 'http://localhost:13378')
    abs_token = os.getenv('ABS_TOKEN')

    if not abs_token:
        print("ERROR: ABS_TOKEN not set")
        return

    headers = {"Authorization": f"Bearer {abs_token}"}

    try:
        async with aiohttp.ClientSession() as session:
            # Get libraries
            async with session.get(f"{abs_url}/api/libraries", headers=headers) as resp:
                libs = await resp.json()
                lib_id = libs['libraries'][0]['id']

            # Get all books - fetch with high limit and no pagination
            all_books = []
            offset = 0
            page_size = 100

            while True:
                url = f"{abs_url}/api/libraries/{lib_id}/items?limit={page_size}&offset={offset}"
                async with session.get(url, headers=headers) as resp:
                    result = await resp.json()
                    books = result.get('results', [])

                    if not books:
                        break

                    all_books.extend(books)
                    offset += page_size

                    # Stop if we've fetched enough (safety limit at 2000)
                    if len(all_books) >= 2000:
                        break

            # Find Randi Darren books by author/narrator name match
            randi_books = []
            seen_titles = set()

            for book in all_books:
                media = book.get('media', {})
                metadata = media.get('metadata', {})
                title = metadata.get('title', '')
                author = metadata.get('authors', [])
                narrator = metadata.get('narrators', [])

                # Skip duplicates
                if title in seen_titles:
                    continue

                # Check if "Randi Darren" is explicitly in author or narrator
                author_str = ' '.join([a.get('name', '').lower() if isinstance(a, dict) else str(a).lower() for a in author])
                narrator_str = ' '.join([n.get('name', '').lower() if isinstance(n, dict) else str(n).lower() for n in narrator])

                found = False
                if 'randi' in author_str and 'darren' in author_str:
                    found = True
                elif 'randi' in narrator_str and 'darren' in narrator_str:
                    found = True

                if found:
                    seen_titles.add(title)
                    randi_books.append({
                        'title': title,
                        'series': metadata.get('seriesName', '') or '[NO SERIES]',
                        'author': author_str[:80] if author_str else 'N/A'
                    })

            # Print results
            print("\n" + "="*80)
            print("RANDI DARREN BOOKS IN AUDIOBOOKSHELF LIBRARY")
            print("="*80)
            print(f"\nTotal books in library: {len(all_books)}")
            print(f"Randi Darren books found: {len(randi_books)}\n")

            if randi_books:
                # Group by series
                by_series = {}
                for book in randi_books:
                    series = book['series']
                    if series not in by_series:
                        by_series[series] = []
                    by_series[series].append(book)

                for series in sorted(by_series.keys()):
                    books = by_series[series]
                    print(f"\n[{series}] ({len(books)} books)")
                    for book in sorted(books, key=lambda b: b['title']):
                        print(f"  - {book['title']}")
                        if book['author'] and book['author'] != 'N/A':
                            print(f"    Author: {book['author']}")
                    print()
            else:
                print("No Randi Darren books found!")

            print("="*80)
            print(f"RESULT: {len(randi_books)} of 17 expected books confirmed")
            if len(randi_books) == 17:
                print("STATUS: ALL BOOKS DOWNLOADED AND IMPORTED!")
            else:
                print(f"STATUS: {17 - len(randi_books)} books still downloading...")
            print("="*80)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(verify_books())
