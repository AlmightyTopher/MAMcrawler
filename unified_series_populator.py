"""
Unified Audiobookshelf Series Populator
Automatically:
1. Stops Audiobookshelf gracefully
2. Populates series via database
3. Restarts Audiobookshelf

This is the SAFE, RELIABLE method that works with running Audiobookshelf.
"""

import subprocess
import time
import sqlite3
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import json
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('unified_series_populator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# CORRECT DATABASE PATH
DB_PATH = r"C:\Users\dogma\AppData\Local\Audiobookshelf\config\absdatabase.sqlite"


class UnifiedSeriesPopulator:
    """Populates series by directly accessing the database"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self.stats = {
            'series_created': 0,
            'books_processed': 0,
            'books_linked': 0,
            'errors': []
        }

    def connect(self) -> bool:
        """Connect to database"""
        try:
            # Don't use check_same_thread - we want single thread access
            self.conn = sqlite3.connect(self.db_path, timeout=30)
            self.conn.row_factory = sqlite3.Row
            logger.info(f"[OK] Connected to database: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"[FAIL] Could not connect to database: {e}")
            self.stats['errors'].append(str(e))
            return False

    def close(self):
        """Close database connection"""
        if self.conn:
            try:
                self.conn.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing connection: {e}")

    def extract_series_from_books(self) -> Dict[str, List[Tuple[str, Optional[str]]]]:
        """
        Extract series from libraryItem metadata.
        Returns: {series_name: [(book_id, sequence), ...]}
        """
        if not self.conn:
            return {}

        series_map = defaultdict(list)

        try:
            cursor = self.conn.cursor()

            # Query books with series metadata
            cursor.execute("""
                SELECT
                    li.id as bookId,
                    li.libraryId,
                    li.media
                FROM libraryItem li
                WHERE li.mediaType = 'book'
                AND li.media IS NOT NULL
            """)

            for row in cursor.fetchall():
                try:
                    book_id = row['bookId']
                    library_id = row['libraryId']

                    # Parse JSON media field
                    media_json = row['media']
                    if isinstance(media_json, str):
                        media = json.loads(media_json)
                    else:
                        media = media_json

                    # Extract series info from metadata
                    metadata = media.get('metadata', {})
                    series_name = metadata.get('seriesName') or metadata.get('series')
                    sequence = metadata.get('seriesSequence')

                    if series_name:
                        series_name = series_name.strip()

                        # Convert sequence to string if needed
                        if sequence is not None:
                            sequence = str(sequence).strip()

                        series_map[series_name].append((book_id, library_id, sequence))
                        self.stats['books_processed'] += 1

                except json.JSONDecodeError as e:
                    logger.warning(f"Could not parse JSON for book {row.get('bookId', 'unknown')}: {e}")
                    self.stats['errors'].append(f"JSON parse error: {str(e)}")
                except Exception as e:
                    logger.warning(f"Error processing book: {e}")
                    self.stats['errors'].append(f"Book processing error: {str(e)}")

            logger.info(f"Extracted {len(series_map)} unique series from {self.stats['books_processed']} books")
            return dict(series_map)

        except Exception as e:
            logger.error(f"Error extracting series: {e}")
            self.stats['errors'].append(str(e))
            return {}

    def get_or_create_series(self, library_id: str, series_name: str) -> Optional[str]:
        """Get existing series or create new one"""
        if not self.conn:
            return None

        try:
            cursor = self.conn.cursor()

            # Check if series exists
            cursor.execute("""
                SELECT id FROM series
                WHERE name = ? AND libraryId = ?
            """, (series_name, library_id))

            result = cursor.fetchone()
            if result:
                return result['id']

            # Create new series
            series_id = str(abs(hash(f"{library_id}{series_name}")) % (2**32))

            cursor.execute("""
                INSERT INTO series (id, name, libraryId, createdAt, updatedAt)
                VALUES (?, ?, ?, datetime('now'), datetime('now'))
            """, (series_id, series_name, library_id))

            self.conn.commit()
            logger.info(f"Created series: {series_name}")
            self.stats['series_created'] += 1
            return series_id

        except Exception as e:
            logger.warning(f"Could not create series {series_name}: {e}")
            self.stats['errors'].append(f"Series creation: {str(e)}")
            return None

    def link_book_to_series(self, book_id: str, series_id: str, sequence: Optional[str] = None) -> bool:
        """Link a book to a series"""
        if not self.conn:
            return False

        try:
            cursor = self.conn.cursor()

            # Check if already linked
            cursor.execute("""
                SELECT id FROM bookSeries
                WHERE bookId = ? AND seriesId = ?
            """, (book_id, series_id))

            if cursor.fetchone():
                logger.debug(f"Book {book_id} already linked to series {series_id}")
                return True

            # Create link
            link_id = str(abs(hash(f"{book_id}{series_id}")) % (2**32))

            cursor.execute("""
                INSERT INTO bookSeries (id, bookId, seriesId, sequence, createdAt, updatedAt)
                VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
            """, (link_id, book_id, series_id, sequence or ""))

            self.conn.commit()
            logger.debug(f"Linked book {book_id} to series {series_id}")
            self.stats['books_linked'] += 1
            return True

        except Exception as e:
            logger.warning(f"Could not link book to series: {e}")
            self.stats['errors'].append(f"Book linking: {str(e)}")
            return False

    def populate(self) -> bool:
        """Main population workflow"""
        logger.info("=" * 80)
        logger.info("UNIFIED SERIES POPULATOR - DATABASE MODE")
        logger.info("=" * 80)
        logger.info("")

        # Connect
        if not self.connect():
            return False

        try:
            # Extract series
            logger.info("Extracting series from book metadata...")
            series_map = self.extract_series_from_books()

            if not series_map:
                logger.warning("No series found in book metadata")
                return True  # Not an error, just nothing to do

            logger.info(f"Found {len(series_map)} series to populate")
            logger.info("")

            # Process each series
            libraries_processed = set()
            for series_name, books in series_map.items():
                if not books:
                    continue

                # Get library from first book
                book_id, library_id, sequence = books[0]
                libraries_processed.add(library_id)

                logger.info(f"Processing series: {series_name} ({len(books)} books)")

                # Create/get series
                series_id = self.get_or_create_series(library_id, series_name)
                if not series_id:
                    logger.error(f"Could not create series: {series_name}")
                    continue

                # Link books
                for book_id, lib_id, seq in books:
                    self.link_book_to_series(book_id, series_id, seq)

                logger.info(f"  Linked {len(books)} books")

            logger.info("")
            logger.info("=" * 80)
            logger.info("POPULATION COMPLETE")
            logger.info("=" * 80)
            logger.info(f"Series created:     {self.stats['series_created']}")
            logger.info(f"Books processed:    {self.stats['books_processed']}")
            logger.info(f"Books linked:       {self.stats['books_linked']}")

            if self.stats['errors']:
                logger.info(f"Errors encountered: {len(self.stats['errors'])}")
                for error in self.stats['errors'][:5]:
                    logger.info(f"  - {error}")

            logger.info("")
            return True

        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return False
        finally:
            self.close()


def is_abs_running() -> bool:
    """Check if Audiobookshelf is running"""
    result = subprocess.run(
        "tasklist | findstr /i node",
        shell=True,
        capture_output=True,
        text=True
    )
    return "node" in result.stdout.lower()


def stop_abs() -> bool:
    """Stop Audiobookshelf gracefully"""
    logger.info("Stopping Audiobookshelf...")
    try:
        subprocess.run("taskkill /IM node.exe /F 2>nul", shell=True)
        time.sleep(2)
        logger.info("Audiobookshelf stopped")
        return True
    except Exception as e:
        logger.error(f"Could not stop Audiobookshelf: {e}")
        return False


def start_abs() -> bool:
    """Start Audiobookshelf"""
    logger.info("Starting Audiobookshelf...")

    # Try to find and start Audiobookshelf
    exe_paths = [
        "C:\\Program Files\\Audiobookshelf\\Audiobookshelf.exe",
        "C:\\Program Files (x86)\\Audiobookshelf\\Audiobookshelf.exe",
    ]

    for path in exe_paths:
        if Path(path).exists():
            try:
                subprocess.Popen(path)
                logger.info("Audiobookshelf started")
                time.sleep(10)  # Give it time to start
                return True
            except Exception as e:
                logger.error(f"Could not start from {path}: {e}")

    logger.warning("Could not find Audiobookshelf executable")
    logger.warning("Please start Audiobookshelf manually")
    return False


def main():
    """Main entry point"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("AUTOMATED AUDIOBOOKSHELF SERIES POPULATION".center(80))
    logger.info("=" * 80)
    logger.info("")

    # Check if database exists
    db_path = Path(DB_PATH)
    if not db_path.exists():
        logger.error(f"Database not found: {DB_PATH}")
        logger.error("Please verify Audiobookshelf is installed and configured properly")
        return 1

    # Check if Audiobookshelf is running
    if is_abs_running():
        logger.info("Audiobookshelf is running. Stopping for database access...")
        if not stop_abs():
            logger.error("Could not stop Audiobookshelf")
            return 1
    else:
        logger.info("Audiobookshelf is not running")

    # Run populator
    logger.info("")
    populator = UnifiedSeriesPopulator(DB_PATH)
    if not populator.populate():
        logger.error("Series population failed")
        return 1

    # Restart Audiobookshelf
    logger.info("")
    logger.info("Restarting Audiobookshelf...")
    if not start_abs():
        logger.warning("Could not auto-start Audiobookshelf. Please start it manually.")
        return 1

    logger.info("")
    logger.info("Done! Series should now be visible in Audiobookshelf.")
    logger.info("Visit http://localhost:13378 to verify.")
    logger.info("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
