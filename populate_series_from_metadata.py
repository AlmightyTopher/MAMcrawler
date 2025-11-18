"""
Audiobookshelf Series Populator (Metadata-Based)

This script extracts series data directly from Audiobookshelf book metadata
and populates the series table without requiring any external data sources.

REQUIREMENTS:
1. Audiobookshelf must be STOPPED (database cannot be locked)
2. Books must have seriesName and/or seriesSequence in their metadata

WHAT IT DOES:
1. Connects to the Audiobookshelf SQLite database
2. Reads all books from the libraryItem table
3. Extracts seriesName and seriesSequence from book metadata JSON
4. Creates series records in the series table (if they don't exist)
5. Links books to series via the bookSeries junction table

USAGE:
1. Stop Audiobookshelf
2. Run: python populate_series_from_metadata.py
3. Start Audiobookshelf
4. Check your library - series should now be visible!
"""

import sqlite3
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import hashlib
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('populate_series_from_metadata.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database path (default Audiobookshelf location)
DB_PATH = r"C:\Users\dogma\AppData\Local\Audiobookshelf\config\absdatabase.sqlite"


class SeriesPopulator:
    """Extract series from book metadata and populate the database"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self.stats = {
            'books_total': 0,
            'books_with_series': 0,
            'unique_series': 0,
            'series_created': 0,
            'series_existing': 0,
            'books_linked': 0,
            'books_already_linked': 0,
            'errors': 0
        }

    def check_database_exists(self) -> bool:
        """Check if database file exists"""
        db_file = Path(self.db_path)
        if not db_file.exists():
            logger.error(f"Database not found: {self.db_path}")
            logger.error("")
            logger.error("SOLUTION:")
            logger.error("  1. Make sure Audiobookshelf is installed")
            logger.error("  2. Verify the database path is correct")
            logger.error("")
            return False
        return True

    def connect(self) -> bool:
        """Connect to the database with lock detection"""
        try:
            # Try to connect with a short timeout to detect locks
            self.conn = sqlite3.connect(self.db_path, timeout=5.0)
            self.conn.row_factory = sqlite3.Row

            # Test the connection with a simple query
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM libraryItem WHERE mediaType = 'book'")
            result = cursor.fetchone()
            self.stats['books_total'] = result['count']

            logger.info(f"Connected to database successfully")
            logger.info(f"Found {self.stats['books_total']} books in library")
            return True

        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                logger.error("Database is LOCKED - Audiobookshelf is still running!")
                logger.error("")
                logger.error("SOLUTION:")
                logger.error("  1. Stop Audiobookshelf completely")
                logger.error("  2. Wait 10 seconds for database to unlock")
                logger.error("  3. Run this script again")
                logger.error("")
            else:
                logger.error(f"Cannot connect to database: {e}")
            self.stats['errors'] += 1
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to database: {e}")
            self.stats['errors'] += 1
            return False

    def close(self):
        """Close database connection"""
        if self.conn:
            try:
                self.conn.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")

    def generate_id(self, *parts) -> str:
        """Generate a consistent ID based on input parts"""
        combined = "".join(str(p) for p in parts)
        return hashlib.md5(combined.encode()).hexdigest()[:16]

    def extract_series_from_metadata(self) -> Dict[str, List[Tuple[str, str, Optional[str]]]]:
        """
        Extract series information from book metadata.

        Returns:
            Dictionary mapping series_name to list of (book_id, library_id, sequence)
        """
        series_map = defaultdict(list)

        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, libraryId, media
                FROM libraryItem
                WHERE mediaType = 'book' AND media IS NOT NULL
            """)

            for row in cursor.fetchall():
                try:
                    book_id = row['id']
                    library_id = row['libraryId']

                    # Parse media JSON
                    media_json = row['media']
                    if isinstance(media_json, str):
                        media = json.loads(media_json)
                    else:
                        media = media_json

                    # Extract series information from metadata
                    metadata = media.get('metadata', {})
                    series_name = metadata.get('seriesName') or metadata.get('series')
                    sequence = metadata.get('seriesSequence')

                    if series_name:
                        series_name = series_name.strip()
                        if series_name:  # Only add if not empty after stripping
                            sequence_str = str(sequence) if sequence else None
                            series_map[series_name].append((book_id, library_id, sequence_str))
                            self.stats['books_with_series'] += 1

                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON in book {book_id}: {e}")
                    self.stats['errors'] += 1
                except Exception as e:
                    logger.warning(f"Error processing book metadata: {e}")
                    self.stats['errors'] += 1

            self.stats['unique_series'] = len(series_map)
            return dict(series_map)

        except Exception as e:
            logger.error(f"Error extracting series from metadata: {e}")
            self.stats['errors'] += 1
            return {}

    def create_or_get_series(self, series_name: str, library_id: str) -> Optional[str]:
        """
        Create a series if it doesn't exist, or return existing series ID.

        Args:
            series_name: Name of the series
            library_id: Library ID for the series

        Returns:
            Series ID if successful, None otherwise
        """
        try:
            cursor = self.conn.cursor()

            # Check if series already exists
            cursor.execute("""
                SELECT id FROM series
                WHERE name = ? AND libraryId = ?
            """, (series_name, library_id))

            result = cursor.fetchone()
            if result:
                self.stats['series_existing'] += 1
                return result['id']

            # Create new series
            series_id = self.generate_id(library_id, series_name)
            now = datetime.utcnow().isoformat()

            cursor.execute("""
                INSERT INTO series (id, name, libraryId, createdAt, updatedAt)
                VALUES (?, ?, ?, ?, ?)
            """, (series_id, series_name, library_id, now, now))

            self.conn.commit()
            self.stats['series_created'] += 1
            return series_id

        except Exception as e:
            logger.error(f"Error creating series '{series_name}': {e}")
            self.stats['errors'] += 1
            return None

    def link_book_to_series(self, book_id: str, series_id: str, sequence: Optional[str]) -> bool:
        """
        Link a book to a series via the bookSeries junction table.

        Args:
            book_id: Book ID
            series_id: Series ID
            sequence: Sequence number (can be None)

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()

            # Check if link already exists
            cursor.execute("""
                SELECT id FROM bookSeries
                WHERE bookId = ? AND seriesId = ?
            """, (book_id, series_id))

            if cursor.fetchone():
                self.stats['books_already_linked'] += 1
                return True

            # Create new link
            link_id = self.generate_id(book_id, series_id)
            now = datetime.utcnow().isoformat()

            cursor.execute("""
                INSERT INTO bookSeries (id, bookId, seriesId, sequence, createdAt, updatedAt)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (link_id, book_id, series_id, sequence or "", now, now))

            self.conn.commit()
            self.stats['books_linked'] += 1
            return True

        except Exception as e:
            logger.warning(f"Error linking book {book_id} to series: {e}")
            self.stats['errors'] += 1
            return False

    def populate_series(self) -> bool:
        """
        Main method to populate series from book metadata.

        Returns:
            True if successful (even with some errors), False if critical failure
        """
        logger.info("=" * 80)
        logger.info("AUDIOBOOKSHELF SERIES POPULATOR (METADATA-BASED)")
        logger.info("=" * 80)
        logger.info("")

        # Check database exists
        if not self.check_database_exists():
            return False

        # Connect to database
        if not self.connect():
            return False

        try:
            # Extract series from metadata
            logger.info("Step 1: Extracting series from book metadata...")
            series_map = self.extract_series_from_metadata()

            if not series_map:
                logger.warning("No series information found in any book metadata!")
                logger.warning("")
                logger.warning("This means:")
                logger.warning("  - No books have the 'seriesName' field in their metadata")
                logger.warning("  - You may need to match/scan your library first")
                logger.warning("")
                return True

            logger.info(f"Found {self.stats['books_with_series']} books with series data")
            logger.info(f"Found {self.stats['unique_series']} unique series names")
            logger.info("")

            # Process each series
            logger.info("Step 2: Creating series and linking books...")
            for series_name, books in series_map.items():
                logger.info(f"  Processing: {series_name} ({len(books)} books)")

                # Get library from first book
                _, library_id, _ = books[0]

                # Create or get series
                series_id = self.create_or_get_series(series_name, library_id)
                if not series_id:
                    logger.error(f"    Failed to create series '{series_name}'")
                    continue

                # Link all books to this series
                for book_id, _, sequence in books:
                    self.link_book_to_series(book_id, series_id, sequence)

            # Print summary
            logger.info("")
            logger.info("=" * 80)
            logger.info("POPULATION COMPLETE")
            logger.info("=" * 80)
            logger.info(f"Total books in library:     {self.stats['books_total']}")
            logger.info(f"Books with series data:     {self.stats['books_with_series']}")
            logger.info(f"Unique series found:        {self.stats['unique_series']}")
            logger.info(f"Series created:             {self.stats['series_created']}")
            logger.info(f"Series already existed:     {self.stats['series_existing']}")
            logger.info(f"Books linked to series:     {self.stats['books_linked']}")
            logger.info(f"Books already linked:       {self.stats['books_already_linked']}")
            logger.info(f"Errors encountered:         {self.stats['errors']}")
            logger.info("")

            # Success if we had no critical errors
            return True

        except Exception as e:
            logger.error(f"Unexpected error during population: {e}")
            self.stats['errors'] += 1
            return False

        finally:
            self.close()


def main():
    """Main entry point"""
    logger.info("Starting Audiobookshelf Series Populator...")
    logger.info("")

    # Create populator
    populator = SeriesPopulator(DB_PATH)

    # Run population
    success = populator.populate_series()

    # Print final status
    if success:
        if populator.stats['series_created'] > 0 or populator.stats['books_linked'] > 0:
            logger.info("SUCCESS: Series have been populated!")
            logger.info("")
            logger.info("NEXT STEPS:")
            logger.info("  1. Start Audiobookshelf")
            logger.info("  2. Open http://localhost:13378")
            logger.info("  3. Navigate to Books library")
            logger.info("  4. Check the Series column - your series should now be visible!")
            logger.info("")
        else:
            logger.warning("Script completed but no changes were made")
            logger.warning("Check the warnings above for details")
            logger.warning("")
        return 0
    else:
        logger.error("FAILED: Critical errors occurred during population")
        logger.error("Check the log file: populate_series_from_metadata.log")
        logger.error("")
        return 1


if __name__ == "__main__":
    sys.exit(main())
