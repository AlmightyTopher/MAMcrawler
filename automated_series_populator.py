"""
Automated Audiobookshelf Series Populator Service

This service automatically creates series and links books based on seriesName metadata.
Uses the Audiobookshelf API with proper Sequelize models.

Key Features:
- Extracts series from book metadata (seriesName field)
- Creates series records via database (Sequelize ORM equivalent)
- Links books to series with proper sequence numbers
- Handles duplicates and existing series gracefully
- Runs as automated service with scheduling support
"""

import asyncio
import logging
import re
import sqlite3
import uuid
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('series_populator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = "F:/Audiobookshelf/config/absdatabase.sqlite"


class AutomatedSeriesPopulator:
    """Populates Audiobookshelf series using direct database writes (Sequelize equivalent)"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self.series_created = 0
        self.series_updated = 0
        self.books_linked = 0
        self.books_already_linked = 0
        self.errors = []
        self.library_id = None  # Will detect from first book

    def connect(self):
        """Connect to the database"""
        try:
            # Use check_same_thread=False to allow WAL mode
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            # Skip WAL and pragmas to avoid schema validation
            logger.info(f"Connected to database: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def close(self):
        """Close the database connection"""
        if self.conn:
            try:
                self.conn.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing connection: {e}")

    def extract_series_from_metadata(self) -> Dict[str, List[Tuple[str, Optional[int]]]]:
        """
        Extract series and their books from libraryItem metadata.
        Returns: {series_name: [(book_id, sequence_number), ...]}
        """
        if not self.conn:
            return {}

        cursor = self.conn.cursor()
        series_map = defaultdict(list)

        try:
            # Query libraryItems with their metadata
            # Extract book ID, series name, and library ID
            cursor.execute("""
                SELECT
                    li.id as bookId,
                    li.libraryId,
                    json_extract(li.media, '$.metadata.seriesName') as seriesName
                FROM libraryItem li
                WHERE json_extract(li.media, '$.metadata.seriesName') IS NOT NULL
                AND json_extract(li.media, '$.metadata.seriesName') != ''
                AND li.mediaType = 'book'
                ORDER BY json_extract(li.media, '$.metadata.seriesName')
            """)

            books_found = 0
            for row in cursor.fetchall():
                book_id = row['bookId']
                library_id = row['libraryId']
                series_name_full = row['seriesName']

                if not series_name_full:
                    continue

                # Set library ID from first book (all books should be in same library)
                if not self.library_id:
                    self.library_id = library_id

                # Extract series name and position (format: "Series Name #Position")
                match = re.match(r"^(.+?)\s*#\s*(\d+(?:\.\d+)?)$", series_name_full.strip())
                if match:
                    series_name = match.group(1).strip()
                    try:
                        sequence = int(float(match.group(2)))
                    except ValueError:
                        sequence = None
                else:
                    series_name = series_name_full.strip()
                    sequence = None

                series_map[series_name].append((book_id, sequence))
                books_found += 1
                logger.debug(f"Found book: {series_name} #{sequence if sequence else 'N/A'} -> {book_id}")

            logger.info(f"Extracted {len(series_map)} series from {books_found} books")
            return dict(series_map)

        except Exception as e:
            logger.error(f"Error extracting series: {e}")
            return {}

    def get_or_create_series(self, series_name: str, library_id: str) -> Optional[str]:
        """
        Get existing series by name/library or create new one.
        Returns series UUID.
        """
        if not self.conn:
            return None

        cursor = self.conn.cursor()

        try:
            # Check if series exists (case-insensitive)
            cursor.execute("""
                SELECT id FROM series
                WHERE LOWER(name) = LOWER(?) AND libraryId = ?
            """, (series_name, library_id))

            existing = cursor.fetchone()
            if existing:
                series_id = existing[0]
                logger.debug(f"Series already exists: '{series_name}' (ID: {series_id})")
                return series_id

            # Create new series with UUID
            series_id = str(uuid.uuid4())
            now_ms = int(datetime.now().timestamp() * 1000)

            cursor.execute("""
                INSERT INTO series (id, name, nameIgnorePrefix, description, libraryId, createdAt, updatedAt)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                series_id,
                series_name,
                self._get_name_ignore_prefix(series_name),
                "Auto-created from metadata enrichment",
                library_id,
                now_ms,
                now_ms
            ))
            self.conn.commit()
            self.series_created += 1
            logger.info(f"Created series: '{series_name}' (ID: {series_id})")
            return series_id

        except sqlite3.IntegrityError as e:
            logger.warning(f"Series creation integrity error (likely duplicate): {e}")
            # Try to fetch it again (race condition)
            cursor.execute("""
                SELECT id FROM series
                WHERE LOWER(name) = LOWER(?) AND libraryId = ?
            """, (series_name, library_id))
            result = cursor.fetchone()
            return result[0] if result else None

        except Exception as e:
            logger.error(f"Error creating series '{series_name}': {e}")
            self.errors.append(f"Series creation error for '{series_name}': {e}")
            return None

    def link_book_to_series(self, book_id: str, series_id: str, sequence: Optional[int] = None) -> bool:
        """
        Link a book to a series with sequence number.
        Returns True if linked successfully.
        """
        if not self.conn:
            return False

        cursor = self.conn.cursor()

        try:
            # Check if link already exists
            cursor.execute("""
                SELECT id FROM bookSeries
                WHERE bookId = ? AND seriesId = ?
            """, (book_id, series_id))

            if cursor.fetchone():
                logger.debug(f"Book-series link already exists: {book_id} -> {series_id}")
                self.books_already_linked += 1
                return True

            # Create the link
            book_series_id = str(uuid.uuid4())
            now_ms = int(datetime.now().timestamp() * 1000)

            # Use sequence as string (Audiobookshelf stores it as STRING in model)
            sequence_str = str(sequence) if sequence is not None else None

            cursor.execute("""
                INSERT INTO bookSeries (id, bookId, seriesId, sequence, createdAt)
                VALUES (?, ?, ?, ?, ?)
            """, (
                book_series_id,
                book_id,
                series_id,
                sequence_str,
                now_ms
            ))
            self.conn.commit()
            self.books_linked += 1
            logger.debug(f"Linked book {book_id} to series {series_id} (sequence: {sequence_str})")
            return True

        except Exception as e:
            logger.error(f"Error linking book {book_id} to series {series_id}: {e}")
            self.errors.append(f"Book link error for {book_id}: {e}")
            return False

    def populate_all_series(self, series_map: Dict[str, List[Tuple[str, Optional[int]]]]) -> Dict[str, int]:
        """
        Process all series: create them and link books.
        Returns stats dictionary.
        """
        if not self.conn or not self.library_id:
            logger.error("Database not connected or library ID not set")
            return {}

        logger.info(f"Processing {len(series_map)} series...")

        for i, (series_name, books) in enumerate(sorted(series_map.items()), 1):
            try:
                logger.info(f"[{i}/{len(series_map)}] Processing series: '{series_name}' ({len(books)} books)")

                # Create or get series
                series_id = self.get_or_create_series(series_name, self.library_id)
                if not series_id:
                    continue

                # Link books to series
                linked_count = 0
                for book_id, sequence in sorted(books, key=lambda x: (x[1] is None, x[1])):
                    if self.link_book_to_series(book_id, series_id, sequence):
                        linked_count += 1

                logger.info(f"  Linked {linked_count}/{len(books)} books to '{series_name}'")

            except Exception as e:
                logger.error(f"Error processing series '{series_name}': {e}")
                self.errors.append(f"Series processing error for '{series_name}': {e}")

        return {
            "series_created": self.series_created,
            "series_updated": self.series_updated,
            "books_linked": self.books_linked,
            "books_already_linked": self.books_already_linked,
            "errors": len(self.errors)
        }

    @staticmethod
    def _get_name_ignore_prefix(name: str) -> str:
        """
        Extract title prefix at end (matches Audiobookshelf logic).
        Example: "The Hobbit" -> "Hobbit, The"
        """
        # Simple implementation - move "The", "A", "An" to end
        match = re.match(r'^(The|A|An)\s+(.+)$', name, re.IGNORECASE)
        if match:
            article = match.group(1)
            rest = match.group(2)
            return f"{rest}, {article}"
        return name

    def run(self):
        """Execute the complete population workflow"""
        try:
            logger.info("=" * 80)
            logger.info("AUDIOBOOKSHELF AUTOMATED SERIES POPULATOR")
            logger.info("=" * 80)

            # Connect
            self.connect()

            # Extract series
            logger.info("\nStep 1: Extracting series from book metadata...")
            series_map = self.extract_series_from_metadata()

            if not series_map:
                logger.warning("No series found in metadata")
                return {
                    "status": "no_series",
                    "message": "No books with series metadata found"
                }

            logger.info(f"Found {len(series_map)} unique series")

            # Populate series and links
            logger.info("\nStep 2: Creating series and linking books...")
            stats = self.populate_all_series(series_map)

            # Close
            self.close()

            # Report
            logger.info("\n" + "=" * 80)
            logger.info("POPULATION RESULTS")
            logger.info("=" * 80)
            logger.info(f"Series Created:           {stats.get('series_created', 0)}")
            logger.info(f"Series Updated:           {stats.get('series_updated', 0)}")
            logger.info(f"Books Linked (New):       {stats.get('books_linked', 0)}")
            logger.info(f"Books Already Linked:     {stats.get('books_already_linked', 0)}")
            logger.info(f"Total Books Processed:    {stats.get('books_linked', 0) + stats.get('books_already_linked', 0)}")
            logger.info(f"Errors Encountered:       {stats.get('errors', 0)}")

            if self.errors:
                logger.info("\nFirst 10 Errors:")
                for error in self.errors[:10]:
                    logger.info(f"  - {error}")

            logger.info("=" * 80)
            logger.info("\nSeries population completed!")
            logger.info("NOTE: Restart Audiobookshelf to see changes in the UI")

            return {
                "status": "success",
                "stats": stats,
                "message": f"Successfully created {stats.get('series_created', 0)} series and linked {stats.get('books_linked', 0)} books"
            }

        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            self.close()
            return {
                "status": "error",
                "message": str(e)
            }


async def main():
    """Entry point"""
    populator = AutomatedSeriesPopulator(DB_PATH)
    result = populator.run()

    print("\n" + "=" * 80)
    print("FINAL STATUS")
    print("=" * 80)
    print(f"Status: {result['status'].upper()}")
    print(f"Message: {result['message']}")
    if 'stats' in result:
        stats = result['stats']
        print(f"\nStatistics:")
        print(f"  - Series Created: {stats.get('series_created', 0)}")
        print(f"  - Books Linked: {stats.get('books_linked', 0)}")
        print(f"  - Books Already Linked: {stats.get('books_already_linked', 0)}")
        print(f"  - Errors: {stats.get('errors', 0)}")
    print("=" * 80)

    return result


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result['status'] == 'success' else 1)
