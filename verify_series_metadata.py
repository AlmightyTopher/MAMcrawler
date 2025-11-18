"""
Verify that series metadata is correctly populated in Audiobookshelf
"""

import asyncio
from backend.integrations.abs_client import AudiobookshelfClient
from backend.config import get_settings

async def verify():
    settings = get_settings()
    client = AudiobookshelfClient(
        base_url=settings.ABS_URL,
        api_token=settings.ABS_TOKEN,
        timeout=30
    )

    print("\n" + "="*80)
    print("SERIES METADATA VERIFICATION")
    print("="*80)

    # Fetch sample books
    books = await client.get_library_items(limit=50, offset=0)

    books_with_series = []
    for book in books:
        meta = book['media']['metadata']
        series = meta.get('seriesName', '')
        if series:
            books_with_series.append({
                'title': meta.get('title'),
                'series': series,
                'author': meta.get('authorName')
            })

    if books_with_series:
        print(f"\nFound {len(books_with_series)} books with series metadata:\n")
        for book in sorted(books_with_series, key=lambda x: x['series'])[:20]:
            print(f"Title: {book['title']}")
            print(f"  Series: {book['series']}")
            print(f"  Author: {book['author']}")
            print()
    else:
        print("\nNo books with series metadata found")

    print("="*80)
    print(f"\nVerification complete!")
    print(f"Total books checked: {len(books)}")
    print(f"Books with series: {len(books_with_series)}")
    print(f"Success rate: {len(books_with_series)/len(books)*100:.1f}%")

if __name__ == "__main__":
    asyncio.run(verify())
