#!/usr/bin/env python3
"""
Update Randi Darren books with proper series metadata in Audiobookshelf
Directly modifies metadata.json files in each book folder
"""
import os
import json
import shutil
from datetime import datetime

# Mapping of book titles to their proper series names
RANDI_DARREN_SERIES_MAP = {
    # Fostering Faust Series
    'Book 01 - Fostering Faust - Fostering Faust Series': 'Fostering Faust',
    'Book 03 - Fostering Faust 3 - Fostering Faust Series': 'Fostering Faust',
    'Fostering Faust: Book 2': 'Fostering Faust',
    'Fostering Faust: Book 3': 'Fostering Faust',
    'Fostering Faust: Fostering Faust, Book 1': 'Fostering Faust',

    # Remnant / Palimar Saga Series
    'Remnant (Unabridged)': 'Remnant / Palimar Saga',
    'Remnant: Book 2': 'Remnant / Palimar Saga',
    'Remnant III': 'Remnant / Palimar Saga',

    # System Overclocked Series
    'System Overclocked': 'System Overclocked',
    'System Overclocked 2: System Overclocked, Book 2': 'System Overclocked',
    'System Overclocked 3': 'System Overclocked',

    # Wild Wastes Series
    'Randi Darren - Wild Wastes 03 - Southern Storm': 'Wild Wastes',
    'Wild Wastes: Eastern Expansion (Unabridged)': 'Wild Wastes',
    'Wild Wastes 4': 'Wild Wastes',
    'Wild Wastes 6 (Unabridged)': 'Wild Wastes',

    # Incubus Inc. Series
    'Incubus Inc. Book 2': 'Incubus Inc.',
    'Incubus Inc., Book 3': 'Incubus Inc.',
    'Incubus Inc. 3': 'Incubus Inc.',  # Alternative naming
    'Randi Darren and William D Arand - Incubus Inc Book 3': 'Incubus Inc.',  # Alternative naming

    # Wild Wastes - Additional entries
    'Wild Wastes: Eastern Expansion (Unabridged)': 'Wild Wastes',
    'Wild Wastes: Eastern Expansion': 'Wild Wastes',
}

abs_books_path = 'F:/Audiobookshelf/Books'

print("="*80)
print("UPDATING RANDI DARREN BOOK SERIES METADATA")
print("="*80)
print(f"\nSearching for books in: {abs_books_path}")
print(f"Total books to update: {len(RANDI_DARREN_SERIES_MAP)}\n")

updated = 0
errors = 0
backup_dir = 'metadata_backups'

# Create backup directory
if not os.path.exists(backup_dir):
    os.makedirs(backup_dir)

for folder in os.listdir(abs_books_path):
    folder_path = os.path.join(abs_books_path, folder)

    if not os.path.isdir(folder_path):
        continue

    metadata_path = os.path.join(folder_path, 'metadata.json')

    if not os.path.exists(metadata_path):
        continue

    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        title = metadata.get('title', '')

        # Check if this book needs updating
        if title in RANDI_DARREN_SERIES_MAP:
            old_series = metadata.get('seriesName', '[NO SERIES]')
            new_series = RANDI_DARREN_SERIES_MAP[title]

            # Create backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(backup_dir, f'{folder}_{timestamp}_metadata.json.bak')
            shutil.copy2(metadata_path, backup_path)

            # Update series name
            metadata['seriesName'] = new_series

            # Write updated metadata
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            print(f"[OK] {title}")
            print(f"     Series: {old_series} -> {new_series}")
            print()

            updated += 1

    except Exception as e:
        print(f"[ERROR] {folder}: {e}")
        errors += 1

print("="*80)
print(f"RESULTS:")
print(f"  Updated: {updated}")
print(f"  Errors: {errors}")
print(f"  Backups: {backup_dir}/")
print("="*80)
print("\nNext steps:")
print("1. Restart Audiobookshelf for changes to take effect")
print("2. Navigate to your library and verify series grouping")
print("3. Click on any series name to see all books in that series grouped together")
