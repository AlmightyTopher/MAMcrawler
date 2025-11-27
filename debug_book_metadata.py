#!/usr/bin/env python3
"""
Debug script to see what the actual metadata structure looks like
"""
import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def debug_metadata():
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

            # Get first 20 books
            async with session.get(f"{abs_url}/api/libraries/{lib_id}/items?limit=20&offset=0", headers=headers) as resp:
                result = await resp.json()
                books = result.get('results', [])

            # Display metadata structure
            for i, book in enumerate(books[:5]):
                print("\n" + "="*80)
                print(f"BOOK {i+1}: {book.get('media', {}).get('metadata', {}).get('title', 'N/A')}")
                print("="*80)

                media = book.get('media', {})
                metadata = media.get('metadata', {})

                print(f"Title: {metadata.get('title', 'N/A')}")
                print(f"Series: {metadata.get('seriesName', 'N/A')}")

                authors = metadata.get('authors', [])
                print(f"\nAuthors ({len(authors)}):")
                for author in authors:
                    print(f"  Type: {type(author)}")
                    print(f"  Value: {author}")
                    if isinstance(author, dict):
                        print(f"    Keys: {author.keys()}")

                narrators = metadata.get('narrators', [])
                print(f"\nNarrators ({len(narrators)}):")
                for narrator in narrators:
                    print(f"  Type: {type(narrator)}")
                    print(f"  Value: {narrator}")
                    if isinstance(narrator, dict):
                        print(f"    Keys: {narrator.keys()}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(debug_metadata())
