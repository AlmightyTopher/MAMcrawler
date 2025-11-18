#!/usr/bin/env python3
"""
Simple series populator for Audiobookshelf.

This script ONLY does the series population. No automation, no lifecycle management.
User runs this manually after stopping Audiobookshelf.

Requirements:
    - Audiobookshelf service must be STOPPED before running
    - Google Sheets data must be available
    - .env file must have GOOGLE_SHEETS_URL
"""

import os
import sys
import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Optional

# Try to load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Using system environment variables only.")

# Configuration
ABS_DATABASE = Path(r"C:\Users\dogma\AppData\Local\Audiobookshelf\config\absdatabase.sqlite")
GOOGLE_SHEETS_URL = os.getenv("GOOGLE_SHEETS_URL")


def print_banner():
    """Print a simple banner."""
    print("=" * 80)
    print("AUDIOBOOKSHELF SERIES POPULATOR")
    print("=" * 80)
    print()


def check_prerequisites() -> bool:
    """Check if all prerequisites are met."""
    print("Checking prerequisites...")

    # Check database exists
    if not ABS_DATABASE.exists():
        print(f"❌ ERROR: Database not found at {ABS_DATABASE}")
        print(f"   Expected location: {ABS_DATABASE}")
        print(f"   Make sure Audiobookshelf is installed and has run at least once.")
        return False
    print(f"✓ Database found: {ABS_DATABASE}")

    # Check Google Sheets URL
    if not GOOGLE_SHEETS_URL:
        print("❌ ERROR: GOOGLE_SHEETS_URL not set in environment")
        print("   Add this to your .env file:")
        print("   GOOGLE_SHEETS_URL=https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/...")
        return False
    print(f"✓ Google Sheets URL configured")

    # Check database is not locked (Audiobookshelf should be stopped)
    try:
        conn = sqlite3.connect(ABS_DATABASE, timeout=1)
        conn.execute("PRAGMA query_only = ON")
        cursor = conn.execute("SELECT COUNT(*) FROM libraryItems LIMIT 1")
        count = cursor.fetchone()[0]
        conn.close()
        print(f"✓ Database accessible ({count} library items found)")
    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower():
            print("❌ ERROR: Database is locked")
            print("   Audiobookshelf service is probably still running.")
            print("   Stop the service first:")
            print("   Stop-Service -Name 'audiobookshelf'")
            return False
        else:
            print(f"❌ ERROR: Database error: {e}")
            return False

    print()
    return True


def fetch_google_sheets_data() -> List[Dict[str, str]]:
    """Fetch series data from Google Sheets."""
    print("Fetching series data from Google Sheets...")

    try:
        import pandas as pd
    except ImportError:
        print("❌ ERROR: pandas not installed")
        print("   Install with: pip install pandas")
        sys.exit(1)

    try:
        # Convert sharing URL to export URL
        if "/edit" in GOOGLE_SHEETS_URL:
            csv_url = GOOGLE_SHEETS_URL.replace("/edit", "/export?format=csv")
        else:
            csv_url = GOOGLE_SHEETS_URL

        # Fetch the sheet
        df = pd.read_csv(csv_url)

        # Check required columns
        required_columns = {"Title", "Series Name", "Series Sequence"}
        missing = required_columns - set(df.columns)
        if missing:
            print(f"❌ ERROR: Missing required columns in Google Sheet: {missing}")
            print(f"   Found columns: {list(df.columns)}")
            return []

        # Filter to rows with series data
        df = df.dropna(subset=["Series Name", "Series Sequence"])

        # Convert to list of dicts
        data = df.to_dict("records")

        print(f"✓ Fetched {len(data)} books with series data")
        print()
        return data

    except Exception as e:
        print(f"❌ ERROR: Failed to fetch Google Sheets data: {e}")
        return []


def normalize_title(title: str) -> str:
    """Normalize a title for matching."""
    if not title:
        return ""

    # Convert to lowercase
    title = title.lower().strip()

    # Remove common punctuation
    for char in ".,;:!?-_'\"":
        title = title.replace(char, " ")

    # Collapse multiple spaces
    title = " ".join(title.split())

    return title


def populate_series(sheets_data: List[Dict[str, str]]) -> int:
    """Populate series data in Audiobookshelf database."""
    print("Populating series data in Audiobookshelf...")
    print()

    conn = sqlite3.connect(ABS_DATABASE)
    cursor = conn.cursor()

    # Build lookup map: normalized title -> series data
    series_map = {}
    for row in sheets_data:
        title = normalize_title(row.get("Title", ""))
        if title:
            series_map[title] = {
                "series_name": row.get("Series Name", "").strip(),
                "sequence": str(row.get("Series Sequence", "")).strip()
            }

    # Fetch all books from Audiobookshelf
    cursor.execute("""
        SELECT id, mediaId, mediaType, mediaMetadata
        FROM libraryItems
        WHERE mediaType = 'book'
    """)

    books = cursor.fetchall()
    print(f"Found {len(books)} books in Audiobookshelf")
    print()

    updated_count = 0

    for book_id, media_id, media_type, metadata_json in books:
        if not metadata_json:
            continue

        import json
        try:
            metadata = json.loads(metadata_json)
        except json.JSONDecodeError:
            continue

        # Get book title
        book_title = metadata.get("title", "")
        if not book_title:
            continue

        # Normalize and look up in series map
        norm_title = normalize_title(book_title)

        if norm_title in series_map:
            series_data = series_map[norm_title]
            series_name = series_data["series_name"]
            sequence = series_data["sequence"]

            # Update metadata with series info
            if "series" not in metadata or not isinstance(metadata["series"], list):
                metadata["series"] = []

            # Add or update series entry
            series_entry = {
                "id": series_name.lower().replace(" ", "-"),
                "name": series_name,
                "sequence": sequence
            }

            # Remove existing entry for this series if present
            metadata["series"] = [
                s for s in metadata["series"]
                if s.get("name") != series_name
            ]

            # Add new entry
            metadata["series"].append(series_entry)

            # Update database
            updated_json = json.dumps(metadata)
            cursor.execute("""
                UPDATE libraryItems
                SET mediaMetadata = ?
                WHERE id = ?
            """, (updated_json, book_id))

            print(f"✓ Updated: {book_title}")
            print(f"  Series: {series_name} (#{sequence})")
            print()

            updated_count += 1

    # Commit changes
    conn.commit()
    conn.close()

    return updated_count


def main():
    """Main entry point."""
    print_banner()

    # Check prerequisites
    if not check_prerequisites():
        print()
        print("Please fix the issues above and try again.")
        sys.exit(1)

    # Fetch Google Sheets data
    sheets_data = fetch_google_sheets_data()
    if not sheets_data:
        print()
        print("No series data found or error fetching data.")
        sys.exit(1)

    # Populate series
    updated_count = populate_series(sheets_data)

    # Summary
    print()
    print("=" * 80)
    print(f"COMPLETE! Updated {updated_count} books with series data.")
    print()
    print("Next steps:")
    print("1. Start Audiobookshelf service:")
    print("   Start-Service -Name 'audiobookshelf'")
    print()
    print("2. Wait 30-60 seconds for service to start")
    print()
    print("3. Open Audiobookshelf and verify series data appears")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print("Interrupted by user. Exiting...")
        sys.exit(1)
    except Exception as e:
        print()
        print(f"❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
