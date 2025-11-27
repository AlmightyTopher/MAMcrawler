#!/usr/bin/env python
import asyncio
import aiohttp
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# All Randi Darren book folders found in the filesystem
BOOKS_TO_UPDATE = [
    ('System Overclocked 2', 'System Overclocked'),
    ('Randi Darren - System Overclocked', 'System Overclocked'),
    ('System Overclocked by Randi Darren', 'System Overclocked'),
    ('Randi Darren - System Overclocked 3 [m4b]', 'System Overclocked'),
    ('Book 01 - Fostering Faust - Fostering Faust Series - Read by Andrea Parsneau - 2018', 'Fostering Faust'),
    ('Darren, Randi -- Fostering Faust, Vol. 01 (2018)', 'Fostering Faust'),
    ('Darren, Randi -- Fostering Faust, Vol. 02 (2019)', 'Fostering Faust'),
    ('Darren, Randi -- Fostering Faust, Vol. 03 (2019)', 'Fostering Faust'),
    ('Book 03 - Fostering Faust 3 - Fostering Faust Series - Read by Andrea Parsneau - 2019', 'Fostering Faust'),
    ('Randi Darren - Remnant 02 - Remnant II', 'Remnant / Palimar Saga'),
    ('01 - Remnant [B0CTSBKHLS]', 'Remnant / Palimar Saga'),
    ('Book 03 - Remnant III', 'Remnant / Palimar Saga'),
    ('Randi Darren - Wild Wastes 03 - Southern Storm', 'Wild Wastes'),
    ('Randi Darren - Wild Wastes 4 m4b', 'Wild Wastes'),
    ('Wild Wastes 4', 'Wild Wastes'),
    ('Wild Wastes 5', 'Wild Wastes'),
    ('Wild Wastes 6', 'Wild Wastes'),
    ('wild wastes', 'Wild Wastes'),
    ('Randi Darren and William D Arand - Incubus Inc Book 3', 'Incubus Inc.'),
    ('Incubus Inc. 3', 'Incubus Inc.'),
]

async def main():
    abs_url = os.getenv('ABS_URL', 'http://localhost:13378')
    abs_token = os.getenv('ABS_TOKEN')
    headers = {'Authorization': f'Bearer {abs_token}'}
    books_dir = Path('F:/Audiobookshelf/Books')
    
    async with aiohttp.ClientSession() as session:
        # Get library ID
        async with session.get(f'{abs_url}/api/libraries', headers=headers) as resp:
            libs = await resp.json()
            lib_id = libs['libraries'][0]['id']
        
        print("Scanning first 5000 library items to find Randi Darren books...")
        
        # Load first 5000 items and index by title
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
                print(f"  Loaded {len(all_items_by_title)} items...", end='\r')
        
        print(f"\nTotal indexed: {len(all_items_by_title)}")
        print("="*80)
        
        # Try to update each book
        updated_count = 0
        found_count = 0
        not_found_list = []
        
        for folder_name, series_name in BOOKS_TO_UPDATE:
            # Check if folder exists
            metadata_file = books_dir / folder_name / 'metadata.json'
            if not metadata_file.exists():
                continue
            
            # Read title from metadata file
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                title = metadata.get('title', '')
            except:
                title = None
            
            if not title:
                continue
            
            found_count += 1
            
            # Check if title is in library
            if title not in all_items_by_title:
                not_found_list.append((title, series_name))
                continue
            
            # Update via API
            item_id = all_items_by_title[title]
            update_payload = {'metadata': {'seriesName': series_name}}
            
            async with session.patch(
                f'{abs_url}/api/items/{item_id}/media',
                headers=headers,
                json=update_payload
            ) as resp:
                if resp.status == 200:
                    print(f"Updated: {title[:60]}")
                    updated_count += 1
                else:
                    print(f"FAILED: {title[:60]} ({resp.status})")
        
        print("\n" + "="*80)
        print(f"Books with metadata files on disk: {found_count}")
        print(f"Books found in Audiobookshelf library: {found_count - len(not_found_list)}")
        print(f"Books successfully updated via API: {updated_count}")
        
        if not_found_list:
            print(f"\nBooks NOT found in first 5000 library items ({len(not_found_list)}):")
            for title, series in not_found_list[:5]:
                print(f"  - {title} (should be series: {series})")
            if len(not_found_list) > 5:
                print(f"  ... and {len(not_found_list)-5} more")

asyncio.run(main())
