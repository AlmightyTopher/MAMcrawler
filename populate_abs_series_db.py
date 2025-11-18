"""
Populate Audiobookshelf Series via Database

This script directly updates the Audiobookshelf SQLite database to create
series relationships and link books to them based on seriesName metadata.

WARNING: This modifies the Audiobookshelf database directly.
BACKUP YOUR DATABASE FIRST: F:/Audiobookshelf/config/absdatabase.sqlite
"""

import sqlite3
import logging
import re
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from datetime import datetime
import shutil

# Database path
DB_PATH = "F:/Audiobookshelf/config/absdatabase.sqlite"
BACKUP_PATH = f"F:/Audiobookshelf/config/absdatabase.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


class SeriesPopulator:
    """Populates Audiobookshelf series via direct database access"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self.series_created = 0
        self.books_linked = 0
        self.errors = []

    def connect(self):
        """Connect to the database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            # Disable strict schema checking for malformed triggers
            self.conn.execute("PRAGMA integrity_check")
            logger.info(f"Connected to database: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            # Try with URI and query_only
            try:
                logger.info("Trying alternative connection method...")
                self.conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
                self.conn.row_factory = sqlite3.Row
                logger.info("Connected in read-only mode")
            except Exception as e2:
                logger.error(f"Failed with alternative method: {e2}")
                raise

    def backup_database(self):
        """Create a backup of the database"""
        try:
            shutil.copy2(self.db_path, BACKUP_PATH)
            logger.info(f"Database backed up to: {BACKUP_PATH}")
        except Exception as e:
            logger.error(f"Failed to backup database: {e}")
            raise

    def get_schema_info(self):
        """Get information about the database schema"""
        if not self.conn:
            return

        cursor = self.conn.cursor()

        # Get tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"Tables: {tables}")

        # Get books table info
        if "book" in tables:
            cursor.execute("PRAGMA table_info(book)")
            columns = cursor.fetchall()
            logger.info("Book table columns:")
            for col in columns:
                logger.info(f"  - {col[1]} ({col[2]})")

        # Get series table info
        if "series" in tables:
            cursor.execute("PRAGMA table_info(series)")
            columns = cursor.fetchall()
            logger.info("Series table columns:")
            for col in columns:
                logger.info(f"  - {col[1]} ({col[2]})")

    def extract_series_from_metadata(self) -> Dict[str, List[Tuple[str, int]]]:
        """Extract series and their books from libraryItem metadata"""
        if not self.conn:
            return {}

        cursor = self.conn.cursor()
        series_map = defaultdict(list)

        try:
            # Query libraryItems with their metadata
            cursor.execute("""
                SELECT id, json_extract(media, '$.metadata.seriesName') as seriesName
                FROM libraryItem
                WHERE json_extract(media, '$.metadata.seriesName') IS NOT NULL
                AND json_extract(media, '$.metadata.seriesName') != ''
            """)

            for row in cursor.fetchall():
                book_id = row[0]
                series_name_full = row[1]

                if not series_name_full:
                    continue

                # Extract series name and position (format: "Series Name #Position")
                match = re.match(r"^(.+?)\s*#(\d+)$", series_name_full)
                if match:
                    series_name = match.group(1).strip()
                    position = int(match.group(2))
                else:
                    series_name = series_name_full
                    position = 0

                series_map[series_name].append((book_id, position))
                logger.debug(f"Found: {series_name} #{position} -> {book_id}")

            logger.info(f"Extracted {len(series_map)} series from metadata")
            return dict(series_map)

        except Exception as e:
            logger.error(f"Error extracting series: {e}")
            return {}

    def create_series_and_link_books(self, series_map: Dict[str, List[Tuple[str, int]]]):
        """Create series and link books to them"""
        if not self.conn:
            return

        cursor = self.conn.cursor()

        for series_name, books in series_map.items():
            try:
                # Check if series already exists
                cursor.execute("SELECT id FROM series WHERE name = ?", (series_name,))
                existing = cursor.fetchone()

                if existing:
                    series_id = existing[0]
                    logger.info(f"Series already exists: '{series_name}' (ID: {series_id})")
                else:
                    # Create new series
                    cursor.execute("""
                        INSERT INTO series (name, description, createdAt, updatedAt)
                        VALUES (?, ?, ?, ?)
                    """, (
                        series_name,
                        f"Auto-created from metadata enrichment",
                        int(datetime.now().timestamp() * 1000),
                        int(datetime.now().timestamp() * 1000)
                    ))
                    self.conn.commit()
                    series_id = cursor.lastrowid
                    self.series_created += 1
                    logger.info(f"Created series: '{series_name}' (ID: {series_id})")

                # Link books to series
                for book_id, position in sorted(books, key=lambda x: x[1]):
                    try:
                        # Check if link already exists
                        cursor.execute("""
                            SELECT id FROM book_series
                            WHERE seriesId = ? AND bookId = ?
                        """, (series_id, book_id))

                        if not cursor.fetchone():
                            # Create the link
                            cursor.execute("""
                                INSERT INTO book_series (seriesId, bookId, sequence)
                                VALUES (?, ?, ?)
                            """, (series_id, book_id, position if position > 0 else 1))
                            self.books_linked += 1

                    except Exception as e:
                        logger.error(f"Error linking book {book_id}: {e}")
                        self.errors.append(f"Book link error for {book_id}: {e}")

                # Commit books linking
                self.conn.commit()

            except Exception as e:
                logger.error(f"Error processing series '{series_name}': {e}")
                self.errors.append(f"Series error for '{series_name}': {e}")

    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def run(self):
        """Run the population process"""
        try:
            logger.info("="*80)
            logger.info("AUDIOBOOKSHELF SERIES POPULATION (DATABASE)")
            logger.info("="*80)

            # Backup
            self.backup_database()

            # Connect
            self.connect()

            # Get schema info (skip if there are schema issues)
            logger.info("\nSchema Information:")
            try:
                self.get_schema_info()
            except Exception as e:
                logger.warning(f"Could not get schema info (likely version issue): {e}")
                logger.info("Proceeding with population anyway...")

            # Extract series
            logger.info("\nExtracting series from metadata...")
            series_map = self.extract_series_from_metadata()

            if not series_map:
                logger.warning("No series found in metadata")
                return

            logger.info(f"Found {len(series_map)} series to process")

            # Create series and link books
            logger.info("\nCreating series and linking books...")
            self.create_series_and_link_books(series_map)

            # Close
            self.close()

            # Report
            logger.info("\n" + "="*80)
            logger.info("POPULATION RESULTS")
            logger.info("="*80)
            logger.info(f"Series Created:    {self.series_created}")
            logger.info(f"Books Linked:      {self.books_linked}")
            logger.info(f"Errors:            {len(self.errors)}")

            if self.errors:
                logger.info("\nErrors:")
                for error in self.errors[:10]:
                    logger.info(f"  - {error}")

            logger.info("="*80)
            logger.info("\nRESTART AUDIOBOOKSHELF to see changes!")

        except Exception as e:
            logger.error(f"Fatal error: {e}")
            self.close()
            raise


if __name__ == "__main__":
    populator = SeriesPopulator(DB_PATH)
    populator.run()
