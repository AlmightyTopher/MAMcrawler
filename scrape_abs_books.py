#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Load books from AudiobookShelf database and scrape Goodreads data
"""

import sys
import json
import sqlite3
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Try to find AudiobookShelf database
abs_paths = [
    Path("../allgendownload/.abs_cache.sqlite"),
    Path("C:/Users/dogma/Projects/allgendownload/.abs_cache.sqlite"),
]

print("=" * 70)
print("AudiobookShelf Book Extractor")
print("=" * 70)
print()

# Find database
db_path = None
for path in abs_paths:
    if path.exists():
        db_path = path
        print(f"Found database: {db_path}")
        break

if not db_path:
    print("Could not find AudiobookShelf database")
    print("Checked paths:")
    for path in abs_paths:
        print(f"  - {path}")
    print()
    print("Alternative: Use AudiobookShelf web UI to export your library")
    sys.exit(1)

try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Try to find books table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"\nAvailable tables: {', '.join(tables)}")

    # Look for books/items
    books = []
    for table_name in ['items', 'books', 'audiobooks', 'media']:
        try:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
            columns = [description[0] for description in cursor.description]
            print(f"\n{table_name} columns: {columns}")

            if 'title' in columns or 'name' in columns:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"Found {count} items in {table_name}")

                if table_name == 'items':
                    cursor.execute("SELECT id, json FROM items LIMIT 10")
                    for row in cursor.fetchall():
                        try:
                            data = json.loads(row['json']) if isinstance(row['json'], str) else row['json']
                            books.append(data)
                        except:
                            pass
                else:
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 10")
                    for row in cursor.fetchall():
                        books.append(dict(row))
        except Exception as e:
            pass

    if books:
        print(f"\n\nExtracted {len(books)} books:")
        for i, book in enumerate(books[:5], 1):
            print(f"\n[{i}] {book}")

    conn.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
