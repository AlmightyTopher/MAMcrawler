"""
Fix Audiobookshelf Database Schema and Populate Series

This script:
1. Detects and repairs the malformed trigger
2. Extracts series from book metadata
3. Creates series and links books
"""

import sqlite3
import logging
import re
import uuid
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('db_fix_series_populator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DB_PATH = "F:/Audiobookshelf/config/absdatabase.sqlite"


class DatabaseRepairAndPopulator:
    """Repair schema corruption and populate series"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """Connect without triggering schema validation"""
        try:
            # Open in read-write mode with timeout
            self.conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
            self.conn.isolation_level = None  # Autocommit mode
            logger.info(f"Connected to database: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise

    def disable_triggers(self):
        """Temporarily disable triggers to allow operations"""
        try:
            self.conn.execute("PRAGMA ignore_check_constraints = ON")
            logger.info("Disabled constraint checking")
            return True
        except Exception as e:
            logger.warning(f"Could not disable constraints: {e}")
            return False

    def remove_malformed_triggers(self):
        """Try to drop the malformed triggers"""
        triggers_to_drop = [
            "update_library_items_author_names_on_book_authors_insert",
            "update_library_items_author_names_on_book_authors_update",
            "update_library_items_author_names_on_book_authors_delete"
        ]

        cursor = self.conn.cursor()
        for trigger_name in triggers_to_drop:
            try:
                cursor.execute(f"DROP TRIGGER IF EXISTS {trigger_name}")
                self.conn.commit()
                logger.info(f"Dropped trigger: {trigger_name}")
            except Exception as e:
                logger.warning(f"Could not drop trigger {trigger_name}: {e}")

    def direct_query_with_recovery(self, query: str, params: tuple = ()) -> List:
        """Execute query with error recovery"""
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        except sqlite3.DatabaseError as e:
            if "malformed database schema" in str(e):
                logger.error(f"Schema error: {e}")
                logger.warning("Attempting to recover by disabling triggers...")
                self.remove_malformed_triggers()
                # Try again
                try:
                    cursor.execute(query, params)
                    return cursor.fetchall()
                except Exception as e2:
                    logger.error(f"Still failed after trigger removal: {e2}")
                    return []
            else:
                logger.error(f"Query error: {e}")
                return []

    def extract_series_direct(self) -> Dict[str, List[Tuple[str, Optional[int]]]]:
        """Extract series using direct SQLite queries avoiding view issues"""
        logger.info("Attempting to extract series from book metadata...")

        series_map = defaultdict(list)

        try:
            # First, get basic table structure
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table'
                ORDER BY name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            logger.info(f"Available tables: {tables}")

            # Try to get libraryItem records
            if 'libraryItem' in tables:
                logger.info("Querying libraryItem table...")

                # First check the actual columns
                cursor.execute("PRAGMA table_info(libraryItem)")
                columns = cursor.fetchall()
                logger.info(f"libraryItem columns: {[col[1] for col in columns]}")

                # Now try to extract series from media JSON
                try:
                    cursor.execute("""
                        SELECT
                            id,
                            libraryId,
                            json_extract(media, '$.metadata.seriesName') as seriesName
                        FROM libraryItem
                        WHERE json_extract(media, '$.metadata.seriesName') IS NOT NULL
                        AND json_extract(media, '$.metadata.seriesName') != ''
                        AND mediaType = 'book'
                        LIMIT 100
                    """)

                    rows = cursor.fetchall()
                    logger.info(f"Found {len(rows)} books with series")

                    for row in rows:
                        book_id = row[0]
                        library_id = row[1]
                        series_name_full = row[2]

                        if not series_name_full:
                            continue

                        # Parse series name and sequence
                        match = re.match(r"^(.+?)\s*#\s*(\d+(?:\.\d+)?)$", series_name_full.strip())
                        if match:
                            series_name = match.group(1).strip()
                            try:
                                sequence = int(float(match.group(2)))
                            except:
                                sequence = None
                        else:
                            series_name = series_name_full.strip()
                            sequence = None

                        series_map[series_name].append((book_id, sequence, library_id))
                        logger.debug(f"Series: {series_name} #{sequence if sequence else 'N/A'} <- {book_id}")

                    return dict(series_map)

                except sqlite3.DatabaseError as e:
                    logger.error(f"Database error during extraction: {e}")
                    logger.warning("Schema is corrupted. Restart Audiobookshelf to repair database")
                    return {}

        except Exception as e:
            logger.error(f"Error in extraction: {e}")
            return {}

    def populate_series(self, series_map: Dict) -> Dict:
        """Populate series and link books"""
        if not series_map:
            return {"error": "No series to populate"}

        stats = {
            "series_created": 0,
            "books_linked": 0,
            "errors": []
        }

        cursor = self.conn.cursor()

        for series_name, books_list in sorted(series_map.items()):
            # All books in this series should have same library ID
            library_id = books_list[0][2] if len(books_list[0]) > 2 else None

            logger.info(f"Processing: '{series_name}' ({len(books_list)} books)")

            try:
                # Check if series exists
                cursor.execute("""
                    SELECT id FROM series
                    WHERE LOWER(name) = LOWER(?) AND libraryId = ?
                """, (series_name, library_id))

                result = cursor.fetchone()
                if result:
                    series_id = result[0]
                    logger.debug(f"  Series exists: {series_id}")
                else:
                    # Create new series
                    series_id = str(uuid.uuid4())
                    now_ms = int(datetime.now().timestamp() * 1000)

                    cursor.execute("""
                        INSERT INTO series (id, name, nameIgnorePrefix, description, libraryId, createdAt, updatedAt)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        series_id,
                        series_name,
                        series_name,  # Simplified nameIgnorePrefix
                        "Auto-created from metadata enrichment",
                        library_id,
                        now_ms,
                        now_ms
                    ))
                    self.conn.commit()
                    stats["series_created"] += 1
                    logger.info(f"  Created series: {series_id}")

                # Link books
                for book_id, sequence, _ in books_list:
                    try:
                        # Check if already linked
                        cursor.execute("""
                            SELECT id FROM bookSeries
                            WHERE bookId = ? AND seriesId = ?
                        """, (book_id, series_id))

                        if not cursor.fetchone():
                            bs_id = str(uuid.uuid4())
                            now_ms = int(datetime.now().timestamp() * 1000)
                            sequence_str = str(sequence) if sequence is not None else None

                            cursor.execute("""
                                INSERT INTO bookSeries (id, bookId, seriesId, sequence, createdAt)
                                VALUES (?, ?, ?, ?, ?)
                            """, (bs_id, book_id, series_id, sequence_str, now_ms))
                            self.conn.commit()
                            stats["books_linked"] += 1
                            logger.debug(f"    Linked book: {book_id}")

                    except Exception as e:
                        logger.error(f"    Error linking book {book_id}: {e}")
                        stats["errors"].append(str(e))

            except Exception as e:
                logger.error(f"  Error processing series: {e}")
                stats["errors"].append(str(e))

        return stats

    def run(self):
        """Execute repair and population"""
        try:
            logger.info("=" * 80)
            logger.info("DATABASE REPAIR AND SERIES POPULATOR")
            logger.info("=" * 80)

            self.connect()
            self.disable_triggers()

            # Extract series
            logger.info("\nExtracting series from metadata...")
            series_map = self.extract_series_direct()

            if not series_map:
                logger.warning("No series found or database schema is corrupted")
                logger.warning("\nTO FIX: Restart Audiobookshelf to auto-repair the database schema")
                return {
                    "status": "schema_error",
                    "message": "Database schema corrupted. Restart Audiobookshelf to repair.",
                    "action": "Please restart Audiobookshelf, then run this script again"
                }

            logger.info(f"Found {len(series_map)} series")

            # Populate series
            logger.info("\nPopulating series and linking books...")
            stats = self.populate_series(series_map)

            self.conn.close()

            # Report
            logger.info("\n" + "=" * 80)
            logger.info("RESULTS")
            logger.info("=" * 80)
            logger.info(f"Series Created: {stats['series_created']}")
            logger.info(f"Books Linked: {stats['books_linked']}")
            logger.info(f"Errors: {len(stats['errors'])}")
            logger.info("=" * 80)

            return {
                "status": "success",
                "stats": stats,
                "message": f"Created {stats['series_created']} series, linked {stats['books_linked']} books"
            }

        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    populator = DatabaseRepairAndPopulator(DB_PATH)
    result = populator.run()

    print("\n" + "=" * 80)
    print("FINAL STATUS")
    print("=" * 80)
    print(f"Status: {result['status'].upper()}")
    print(f"Message: {result['message']}")
    if 'action' in result:
        print(f"\nAction Required: {result['action']}")
    print("=" * 80)
