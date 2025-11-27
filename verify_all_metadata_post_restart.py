#!/usr/bin/env python
"""
Post-Restart Metadata Verification & Update
Verifies all series metadata is correctly reflected in Audiobookshelf after restart
"""

import asyncio
import aiohttp
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

async def main():
    abs_url = os.getenv('ABS_URL', 'http://localhost:13378')
    abs_token = os.getenv('ABS_TOKEN')
    headers = {'Authorization': f'Bearer {abs_token}'}
    books_dir = Path('F:/Audiobookshelf/Books')

    print("POST-RESTART METADATA VERIFICATION")
    print("=" * 80)
    print()

    async with aiohttp.ClientSession() as session:
        # Get library ID
        async with session.get(f'{abs_url}/api/libraries', headers=headers) as resp:
            libs = await resp.json()
            lib_id = libs['libraries'][0]['id']

        print(f"Library ID: {lib_id}")
        print()

        # Phase 1: Verify all metadata files on disk
        print("PHASE 1: FILESYSTEM METADATA VERIFICATION")
        print("-" * 80)

        if not books_dir.exists():
            print(f"ERROR: Books directory not found at {books_dir}")
            return

        # Get all book folders
        book_folders = [f for f in books_dir.iterdir() if f.is_dir()]
        print(f"Total book folders on disk: {len(book_folders)}")
        print()

        # Check which folders have metadata.json
        folders_with_metadata = []
        folders_without_metadata = []

        for folder in sorted(book_folders):
            metadata_file = folder / 'metadata.json'
            if metadata_file.exists():
                folders_with_metadata.append(folder)
            else:
                folders_without_metadata.append(folder)

        print(f"Folders with metadata.json: {len(folders_with_metadata)}")
        print(f"Folders without metadata.json: {len(folders_without_metadata)}")
        print()

        # Phase 2: Extract series information from metadata files
        print("PHASE 2: SERIES METADATA EXTRACTION FROM DISK")
        print("-" * 80)

        series_by_folder = {}
        for folder in folders_with_metadata:
            try:
                metadata_file = folder / 'metadata.json'
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                series_name = metadata.get('seriesName', '')
                series_by_folder[folder.name] = {
                    'series_on_disk': series_name,
                    'title': metadata.get('title', ''),
                }
            except Exception as e:
                print(f"ERROR reading {folder.name}: {e}")

        print(f"Successfully read {len(series_by_folder)} metadata files")
        print()

        # Phase 3: Query API to find books and compare
        print("PHASE 3: API VERIFICATION AND COMPARISON")
        print("-" * 80)

        print("Querying all library items from API...")
        all_items = []
        offset = 0
        page = 0

        while True:
            async with session.get(
                f'{abs_url}/api/libraries/{lib_id}/items?limit=500&offset={offset}',
                headers=headers
            ) as resp:
                result = await resp.json()
                items = result.get('results', [])
                if not items:
                    break
                all_items.extend(items)
                page += 1
                offset += 500
                print(f"  Page {page}: loaded {len(items)} items (total: {len(all_items)})", end='\r')

        print(f"\nTotal items in library: {len(all_items)}")
        print()

        # Index items by title for quick lookup
        items_by_title = {}
        for item in all_items:
            media_metadata = item.get('media', {}).get('metadata', {})
            title = media_metadata.get('title', '')
            if title:
                items_by_title[title] = item

        print(f"Items indexed by title: {len(items_by_title)}")
        print()

        # Phase 4: Compare disk vs API
        print("PHASE 4: DISK vs API COMPARISON")
        print("-" * 80)

        matches = 0
        mismatches = 0
        not_found_in_api = 0
        updates_needed = []

        for folder_name, disk_data in series_by_folder.items():
            title = disk_data['title']
            series_on_disk = disk_data['series_on_disk']

            if title not in items_by_title:
                not_found_in_api += 1
                continue

            item = items_by_title[title]
            api_metadata = item.get('media', {}).get('metadata', {})
            series_in_api = api_metadata.get('seriesName', '')

            if series_on_disk == series_in_api:
                matches += 1
            else:
                mismatches += 1
                item_id = item.get('id')
                updates_needed.append({
                    'item_id': item_id,
                    'title': title,
                    'series_on_disk': series_on_disk,
                    'series_in_api': series_in_api,
                })

        print(f"Metadata files checked: {len(series_by_folder)}")
        print(f"  - Matches (Disk = API): {matches}")
        print(f"  - Mismatches (Disk ≠ API): {mismatches}")
        print(f"  - Not found in API: {not_found_in_api}")
        print()

        # Phase 5: Fix mismatches via API
        if updates_needed:
            print("PHASE 5: FIXING MISMATCHES VIA API")
            print("-" * 80)
            print(f"Updating {len(updates_needed)} items...")
            print()

            updated_count = 0
            failed_count = 0

            for update_info in updates_needed:
                item_id = update_info['item_id']
                title = update_info['title']
                series_on_disk = update_info['series_on_disk']
                series_in_api = update_info['series_in_api']

                update_payload = {'metadata': {'seriesName': series_on_disk}}

                async with session.patch(
                    f'{abs_url}/api/items/{item_id}/media',
                    headers=headers,
                    json=update_payload
                ) as resp:
                    if resp.status == 200:
                        print(f"[OK] {title[:60]}")
                        print(f"     {series_in_api or '(no series)'} → {series_on_disk}")
                        updated_count += 1
                    else:
                        print(f"[FAILED] {title[:60]} (HTTP {resp.status})")
                        failed_count += 1

            print()
            print(f"Updates completed: {updated_count}")
            print(f"Failed updates: {failed_count}")
        else:
            print("PHASE 5: NO UPDATES NEEDED")
            print("-" * 80)
            print("All metadata in API matches disk. Verification passed.")

        print()
        print("=" * 80)
        print("VERIFICATION SUMMARY")
        print("=" * 80)
        print(f"Total book folders: {len(book_folders)}")
        print(f"Folders with metadata.json: {len(folders_with_metadata)}")
        print(f"Series metadata matches: {matches}")
        if mismatches > 0:
            print(f"Series metadata mismatches (now fixed): {mismatches}")
        print(f"Books not found in API: {not_found_in_api}")
        print()
        print("Metadata verification complete.")

asyncio.run(main())
