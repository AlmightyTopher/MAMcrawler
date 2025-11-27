#!/usr/bin/env python3
"""
Verify Randi Darren books in Audiobookshelf library - Fixed version
Searches by series names and keywords we know are Randi Darren works
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

                    if len(all_books) >= 2000:
                        break

            # Known Randi Darren series and book titles
            # Based on our search results from Phase 1-5
            randi_series = [
                'System Overclocked',
                'Fostering Fae',
                'Remnant Chronicles',
                'Incubus',
                'Eastern Roman Empire',
                'Southern Cultures',
                'Wild Wastes Chronicles'
            ]

            # Known Randi Darren book title keywords
            randi_keywords = [
                'system overclocked',
                'fostering fae',
                'remnant chronicles',
                'incubus',
                'eastern roman',
                'southern',
                'wild wastes'
            ]

            randi_books = []
            seen_titles = set()

            for book in all_books:
                media = book.get('media', {})
                metadata = media.get('metadata', {})
                title = metadata.get('title', '')
                series = metadata.get('seriesName', '')

                if not title or title in seen_titles:
                    continue

                title_lower = title.lower()
                series_lower = series.lower()

                # Check if matches any Randi Darren pattern
                found = False

                # Check series name
                for randi_series_name in randi_series:
                    if randi_series_name.lower() in series_lower:
                        found = True
                        break

                # Check title keywords
                if not found:
                    for keyword in randi_keywords:
                        if keyword in title_lower:
                            found = True
                            break

                if found:
                    seen_titles.add(title)
                    randi_books.append({
                        'title': title,
                        'series': series or '[NO SERIES]'
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
                    by_series[series].append(book['title'])

                for series in sorted(by_series.keys()):
                    books = by_series[series]
                    print(f"\n[{series}] ({len(books)} books)")
                    for title in sorted(books):
                        print(f"  - {title}")
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
