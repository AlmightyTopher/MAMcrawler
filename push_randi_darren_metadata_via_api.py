import asyncio
import aiohttp
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Map of book folder names to series names
RANDI_DARREN_SERIES_MAP = {
    'Book 01 - Fostering Faust - Fostering Faust Series': 'Fostering Faust',
    'Fostering Faust: Book 2': 'Fostering Faust',
    'Fostering Faust: Book 3': 'Fostering Faust',
    'Fostering Faust: Book 4': 'Fostering Faust',
    'Fostering Faust: Book 5': 'Fostering Faust',
    'System Overclocked': 'System Overclocked',
    'System Overclocked 2': 'System Overclocked',
    'Randi Darren - System Overclocked': 'System Overclocked',
    'Randi Darren - System Overclocked 3 [m4b]': 'System Overclocked',
    'Randi Darren - Remnant 01 - Remnant I': 'Remnant / Palimar Saga',
    'Randi Darren - Remnant 02 - Remnant II': 'Remnant / Palimar Saga',
    'Wild Wastes': 'Wild Wastes',
    'Wild Wastes 2': 'Wild Wastes',
    'Wild Wastes 3': 'Wild Wastes',
    'Wild Wastes 4': 'Wild Wastes',
    'Wild Wastes: Eastern Expansion': 'Wild Wastes',
    'Randi Darren and William D Arand - Incubus Inc Book 3': 'Incubus Inc.',
}

async def push_metadata_updates():
    abs_url = os.getenv('ABS_URL', 'http://localhost:13378')
    abs_token = os.getenv('ABS_TOKEN')
    headers = {'Authorization': f'Bearer {abs_token}'}
    
    async with aiohttp.ClientSession() as session:
        # Get library ID
        async with session.get(f'{abs_url}/api/libraries', headers=headers) as resp:
            libs = await resp.json()
            lib_id = libs['libraries'][0]['id']
        
        print("Scanning for Randi Darren books to update via API...")
        print("="*80)
        
        books_dir = Path('F:/Audiobookshelf/Books')
        updated_count = 0
        
        # Get all items from library (search only first 5000 to save time)
        all_items_by_title = {}
        offset = 0
        while offset < 5000:
            async with session.get(f'{abs_url}/api/libraries/{lib_id}/items?limit=500&offset={offset}', headers=headers) as resp:
                result = await resp.json()
                items = result.get('results', [])
                if not items:
                    break
                
                for item in items:
                    title = item.get('media', {}).get('metadata', {}).get('title', '')
                    if title:
                        all_items_by_title[title] = item.get('id')
                
                offset += 500
                print(f"Loaded {len(all_items_by_title)} items so far...")
        
        print(f"Total items indexed: {len(all_items_by_title)}")
        print("="*80)
        
        # Now try to find and update each book
        for book_folder_name, series_name in RANDI_DARREN_SERIES_MAP.items():
            # Check if metadata file exists on disk
            metadata_file = books_dir / book_folder_name / 'metadata.json'
            if not metadata_file.exists():
                print(f"Folder not found: {book_folder_name}")
                continue
            
            # Read the metadata file to get the actual title
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            title = metadata.get('title', '')
            current_series = metadata.get('seriesName', '')
            
            print(f"\nBook: {title}")
            print(f"  Expected Series: {series_name}")
            print(f"  Current Series (on disk): {current_series}")
            
            # Try to find this book in the library by title
            if title not in all_items_by_title:
                print(f"  Status: NOT FOUND in first 5000 items")
                continue
            
            item_id = all_items_by_title[title]
            
            # Update via API using PATCH /items/:id/media
            update_payload = {
                'metadata': {
                    'seriesName': series_name
                }
            }
            
            async with session.patch(
                f'{abs_url}/api/items/{item_id}/media',
                headers=headers,
                json=update_payload
            ) as resp:
                if resp.status == 200:
                    print(f"  Status: UPDATED via API [OK]")
                    updated_count += 1
                else:
                    error_text = await resp.text()
                    print(f"  Status: FAILED ({resp.status})")
                    print(f"  Response: {error_text[:200]}")
        
        print("\n" + "="*80)
        print(f"Total books updated via API: {updated_count}")

asyncio.run(push_metadata_updates())
