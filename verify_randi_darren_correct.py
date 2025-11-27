#!/usr/bin/env python3
"""
Verify Randi Darren books in Audiobookshelf library - Correct version
Groups by library item ID to account for multiple files per book
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

            # Get all books with pagination
            all_items = []
            offset = 0
            page_size = 100

            while True:
                url = f"{abs_url}/api/libraries/{lib_id}/items?limit={page_size}&offset={offset}"
                async with session.get(url, headers=headers) as resp:
                    result = await resp.json()
                    items = result.get('results', [])

                    if not items:
                        break

                    all_items.extend(items)
                    offset += page_size

                    if len(all_items) >= 2000:
                        break

            # Group items by their parent book ID to handle multiple files per book
            books_by_id = {}
            for item in all_items:
                item_id = item.get('id')
                metadata = item.get('media', {}).get('metadata', {})

                if item_id:
                    if item_id not in books_by_id:
                        books_by_id[item_id] = {
                            'title': metadata.get('title', ''),
                            'series': metadata.get('seriesName', ''),
                            'count': 0
                        }
                    books_by_id[item_id]['count'] += 1

            # Known Randi Darren series and book title keywords
            randi_keywords = [
                'system overclocked',
                'fostering fae',
                'remnant',
                'incubus',
                'eastern',
                'southern',
                'wild wastes'
            ]

            randi_books = []

            for item_id, book_info in books_by_id.items():
                title = book_info['title'].lower()
                series = book_info['series'].lower()

                # Check if matches any Randi Darren pattern
                found = False
                for keyword in randi_keywords:
                    if keyword in title or keyword in series:
                        found = True
                        break

                if found:
                    randi_books.append({
                        'title': book_info['title'],
                        'series': book_info['series'] or '[NO SERIES]',
                        'file_count': book_info['count']
                    })

            # Print results
            print("\n" + "="*80)
            print("RANDI DARREN BOOKS IN AUDIOBOOKSHELF LIBRARY")
            print("="*80)
            print(f"\nTotal unique books in library: {len(books_by_id)}")
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
                        print(f"  - {book['title']} ({book['file_count']} files)")
                    print()
            else:
                print("No Randi Darren books found!")

            print("="*80)
            print(f"RESULT: {len(randi_books)} of 17 expected books confirmed")
            if len(randi_books) >= 17:
                print("STATUS: ALL BOOKS DOWNLOADED AND IMPORTED!")
            else:
                print(f"STATUS: {17 - len(randi_books)} books still downloading...")
            print("="*80)

            # Save results to file for reference
            with open('randi_darren_library_status.json', 'w') as f:
                json.dump({
                    'total_found': len(randi_books),
                    'expected': 17,
                    'books': randi_books
                }, f, indent=2)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(verify_books())
