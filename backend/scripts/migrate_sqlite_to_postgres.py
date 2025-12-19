#!/usr/bin/env python3
"""
Migrate SQLite state databases to Postgres

Migrates data from:
- downloaded_books.db -> downloaded_books table
- hardcover_user_sync.db -> hardcover_user_mappings table

Preserves all existing data during migration.
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from dotenv import load_dotenv
load_dotenv()

from backend.database import get_db_context, init_db
from backend.models import DownloadedBook, HardcoverUserMapping
from backend.config import get_settings

settings = get_settings()


def migrate_downloaded_books():
    """Migrate downloaded_books.db to Postgres"""
    sqlite_path = Path("downloaded_books.db")

    if not sqlite_path.exists():
        print(f"⚠️  {sqlite_path} not found, skipping...")
        return

    print(f"\n📦 Migrating {sqlite_path}...")

    try:
        # Connect to SQLite
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row
        cursor = sqlite_conn.cursor()

        # Get all books
        cursor.execute("SELECT * FROM books")
        books = cursor.fetchall()

        print(f"   Found {len(books)} books in SQLite")

        # Insert into Postgres
        with get_db_context() as db:
            migrated = 0
            skipped = 0

            for book in books:
                # Check if already exists
                exists = db.query(DownloadedBook).filter(
                    DownloadedBook.title == book['title']
                ).first()

                if exists:
                    skipped += 1
                    continue

                # Create new record
                new_book = DownloadedBook(
                    title=book['title'],
                    author=book['author'],
                    genre=book['genre'],
                    magnet_link=book['magnet_link'],
                    status=book['status'],
                    queued_time=book['queued_time'],
                    downloaded_time=book['downloaded_time'],
                    added_to_abs_time=book['added_to_abs_time'],
                    estimated_value=book['estimated_value'],
                    file_size=book['file_size'],
                    bitrate=book['bitrate'],
                    quality_check=bool(book['quality_check'])
                )

                db.add(new_book)
                migrated += 1

            db.commit()

        sqlite_conn.close()
        print(f"   ✅ Migrated {migrated} books, skipped {skipped} duplicates")

    except Exception as e:
        print(f"   ❌ Error migrating downloaded_books: {e}")
        raise


def migrate_hardcover_user_mappings():
    """Migrate hardcover_user_sync.db to Postgres"""
    sqlite_path = Path("hardcover_user_sync.db")

    if not sqlite_path.exists():
        print(f"⚠️  {sqlite_path} not found, skipping...")
        return

    print(f"\n📦 Migrating {sqlite_path}...")

    try:
        # Connect to SQLite
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row
        cursor = sqlite_conn.cursor()

        # Get all mappings
        cursor.execute("SELECT * FROM user_mappings")
        mappings = cursor.fetchall()

        print(f"   Found {len(mappings)} user mappings in SQLite")

        # Insert into Postgres
        with get_db_context() as db:
            migrated = 0
            skipped = 0

            for mapping in mappings:
                # Check if already exists
                exists = db.query(HardcoverUserMapping).filter(
                    HardcoverUserMapping.abs_user_id == mapping['abs_user_id']
                ).first()

                if exists:
                    skipped += 1
                    continue

                # Create new record
                new_mapping = HardcoverUserMapping(
                    abs_user_id=mapping['abs_user_id'],
                    abs_username=mapping['abs_username'],
                    hardcover_token=mapping['hardcover_token'],
                    last_synced_at=mapping['last_synced_at'],
                    is_active=bool(mapping['is_active'])
                )

                db.add(new_mapping)
                migrated += 1

            db.commit()

        sqlite_conn.close()
        print(f"   ✅ Migrated {migrated} mappings, skipped {skipped} duplicates")

    except Exception as e:
        print(f"   ❌ Error migrating hardcover_user_mappings: {e}")
        raise


def main():
    """Run all migrations"""
    print("=" * 60)
    print("SQLite to Postgres Migration")
    print("=" * 60)
    print(f"Target: {settings.DATABASE_URL}")
    print()

    # Ensure Postgres tables exist
    print("📋 Ensuring Postgres tables exist...")
    init_db()
    print("   ✅ Tables ready")

    # Migrate downloaded books
    migrate_downloaded_books()

    # Migrate hardcover user mappings
    migrate_hardcover_user_mappings()

    print()
    print("=" * 60)
    print("✅ Migration Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Verify data in Postgres:")
    print("   - SELECT COUNT(*) FROM downloaded_books;")
    print("   - SELECT COUNT(*) FROM hardcover_user_mappings;")
    print("2. Update code to use Postgres models")
    print("3. Backup and archive SQLite databases")
    print()


if __name__ == "__main__":
    main()
