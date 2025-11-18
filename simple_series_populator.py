"""
SIMPLE Audiobookshelf Series Populator

This script does ONE THING ONLY: Populates series in the database.
It assumes Audiobookshelf is NOT running (so the database is accessible).

If you need to stop/start Audiobookshelf, do that manually first.
Then run this script to populate the series.
Then restart Audiobookshelf to see the changes.

This simplicity = reliability. No waiting, no timeouts, no crashes.
"""

import sqlite3
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import hashlib

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('simple_series_populator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = r"C:\Users\dogma\AppData\Local\Audiobookshelf\config\absdatabase.sqlite"


class SimpleSeriesPopulator:
    """Direct database access for series population"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self.stats = {
            'series_found': 0,
            'series_created': 0,
            'books_linked': 0,
            'errors': 0
        }

    def connect(self) -> bool:
        """Connect to the database"""
        try:
            # Simple connection - no pragmas
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row

            # Test connection with a simple query
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM libraryItem WHERE mediaType = 'book'")
            count = cursor.fetchone()['count']
            logger.info(f"Connected to database - found {count} books")
            return True
        except Exception as e:
            logger.error(f"Cannot connect to database: {e}")
            logger.error("")
            logger.error("SOLUTION:")
            logger.error("1. Make sure Audiobookshelf is STOPPED")
            logger.error("2. Try running this script again")
            logger.error("")
            self.stats['errors'] += 1
            return False

    def close(self):
        """Close database connection"""
        if self.conn:
            try:
                self.conn.close()
                logger.info("Database connection closed")
            except:
                pass

    def generate_id(self, *parts):
        """Generate a unique ID based on input parts"""
        combined = "".join(str(p) for p in parts)
        return hashlib.md5(combined.encode()).hexdigest()[:16]

    def extract_series(self) -> Dict[str, List[Tuple[str, str, Optional[str]]]]:
        """
        Extract series from book metadata.
        Returns: {series_name: [(book_id, library_id, sequence), ...]}
        """
        series_map = defaultdict(list)

        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, libraryId, media FROM libraryItem
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

                    # Extract series name
                    metadata = media.get('metadata', {})
                    series_name = metadata.get('seriesName') or metadata.get('series')
                    sequence = metadata.get('seriesSequence')

                    if series_name:
                        series_name = series_name.strip()
                        sequence_str = str(sequence) if sequence else None
                        series_map[series_name].append((book_id, library_id, sequence_str))
                        self.stats['series_found'] += 1

                except Exception as e:
                    logger.warning(f"Error processing book: {e}")
                    self.stats['errors'] += 1

            return dict(series_map)

        except Exception as e:
            logger.error(f"Error extracting series: {e}")
            self.stats['errors'] += 1
            return {}

    def populate(self) -> bool:
        """Populate series in the database"""
        logger.info("=" * 80)
        logger.info("SIMPLE SERIES POPULATOR")
        logger.info("=" * 80)
        logger.info("")

        # Connect
        if not self.connect():
            return False

        try:
            # Extract series
            logger.info("Extracting series from book metadata...")
            series_map = self.extract_series()

            if not series_map:
                logger.warning("No series found in metadata")
                return True

            logger.info(f"Found {len(series_map)} unique series")
            logger.info("")

            # Process each series
            for series_name, books in series_map.items():
                logger.info(f"Processing: {series_name} ({len(books)} books)")

                if not books:
                    continue

                # Get library from first book
                book_id, library_id, sequence = books[0]

                try:
                    cursor = self.conn.cursor()

                    # Check if series exists
                    cursor.execute("""
                        SELECT id FROM series
                        WHERE name = ? AND libraryId = ?
                    """, (series_name, library_id))

                    result = cursor.fetchone()
                    if result:
                        series_id = result['id']
                        logger.info(f"  Series already exists (ID: {series_id})")
                    else:
                        # Create series
                        series_id = self.generate_id(library_id, series_name)
                        cursor.execute("""
                            INSERT INTO series (id, name, libraryId, createdAt, updatedAt)
                            VALUES (?, ?, ?, datetime('now'), datetime('now'))
                        """, (series_id, series_name, library_id))
                        self.conn.commit()
                        logger.info(f"  Created series (ID: {series_id})")
                        self.stats['series_created'] += 1

                    # Link books
                    for book_id, lib_id, seq in books:
                        try:
                            # Check if already linked
                            cursor.execute("""
                                SELECT id FROM bookSeries
                                WHERE bookId = ? AND seriesId = ?
                            """, (book_id, series_id))

                            if not cursor.fetchone():
                                # Create link
                                link_id = self.generate_id(book_id, series_id)
                                cursor.execute("""
                                    INSERT INTO bookSeries
                                    (id, bookId, seriesId, sequence, createdAt, updatedAt)
                                    VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
                                """, (link_id, book_id, series_id, seq or ""))
                                self.conn.commit()
                                self.stats['books_linked'] += 1
                        except Exception as e:
                            logger.warning(f"    Error linking book {book_id}: {e}")
                            self.stats['errors'] += 1

                except Exception as e:
                    logger.error(f"  Error processing series: {e}")
                    self.stats['errors'] += 1

            # Summary
            logger.info("")
            logger.info("=" * 80)
            logger.info("POPULATION COMPLETE")
            logger.info("=" * 80)
            logger.info(f"Series found in metadata: {self.stats['series_found']}")
            logger.info(f"Series created:          {self.stats['series_created']}")
            logger.info(f"Books linked:            {self.stats['books_linked']}")
            logger.info(f"Errors:                  {self.stats['errors']}")
            logger.info("")

            return self.stats['errors'] == 0

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self.stats['errors'] += 1
            return False
        finally:
            self.close()


def main():
    """Main entry point"""
    # Check if database exists
    db_path = Path(DB_PATH)
    if not db_path.exists():
        logger.error(f"Database not found: {DB_PATH}")
        logger.error("")
        logger.error("Make sure:")
        logger.error("  1. Audiobookshelf is INSTALLED")
        logger.error("  2. Audiobookshelf is STOPPED (not running)")
        logger.error("  3. The path above is correct")
        logger.error("")
        return 1

    # Run populator
    populator = SimpleSeriesPopulator(DB_PATH)
    success = populator.populate()

    if success:
        logger.info("SUCCESS: Series have been populated!")
        logger.info("")
        logger.info("NEXT STEPS:")
        logger.info("1. Start Audiobookshelf")
        logger.info("2. Open http://localhost:13378")
        logger.info("3. Navigate to Books and check Series column")
        logger.info("")
        return 0
    else:
        logger.error("FAILED: There were errors during population")
        logger.error("Check the log file: simple_series_populator.log")
        return 1


if __name__ == "__main__":
    sys.exit(main())
