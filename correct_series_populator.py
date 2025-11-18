#!/usr/bin/env python3
"""
Audiobookshelf Series Relationship Reporter

This script reads and reports on the existing series relationships in the
Audiobookshelf database. It does NOT create or modify any data - it only
displays what series relationships already exist.

The Audiobookshelf database uses a many-to-many relationship for series:
- books table (id, title, etc.)
- series table (id, name, libraryId)
- bookSeries junction table (id, bookId, seriesId, sequence, createdAt)

Usage:
    python correct_series_populator.py [database_path]

If database_path is not provided, it will look for common locations.
"""

import sqlite3
import sys
from pathlib import Path
from typing import Optional, List, Tuple
import json


class AudiobookshelfSeriesReporter:
    """Reports on existing series relationships in Audiobookshelf database."""

    def __init__(self, db_path: str):
        """
        Initialize the reporter with database path.

        Args:
            db_path: Path to the Audiobookshelf SQLite database
        """
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self) -> bool:
        """
        Connect to the database and verify structure.

        Returns:
            True if connection successful and tables exist, False otherwise
        """
        if not self.db_path.exists():
            print(f"❌ Database not found: {self.db_path}")
            return False

        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row

            # Verify required tables exist
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name IN ('books', 'series', 'bookSeries')
            """)
            tables = [row[0] for row in cursor.fetchall()]

            required_tables = {'books', 'series', 'bookSeries'}
            missing_tables = required_tables - set(tables)

            if missing_tables:
                print(f"❌ Missing required tables: {', '.join(missing_tables)}")
                return False

            print(f"✓ Connected to database: {self.db_path}")
            print(f"✓ All required tables found: {', '.join(required_tables)}")
            return True

        except sqlite3.Error as e:
            print(f"❌ Database connection error: {e}")
            return False

    def get_series_summary(self) -> dict:
        """
        Get summary statistics about series in the database.

        Returns:
            Dictionary with series statistics
        """
        if not self.conn:
            return {}

        cursor = self.conn.cursor()

        # Count total series
        cursor.execute("SELECT COUNT(*) as count FROM series")
        series_count = cursor.fetchone()['count']

        # Count total book-series links
        cursor.execute("SELECT COUNT(*) as count FROM bookSeries")
        book_series_links = cursor.fetchone()['count']

        # Count books with at least one series
        cursor.execute("""
            SELECT COUNT(DISTINCT bookId) as count
            FROM bookSeries
        """)
        books_with_series = cursor.fetchone()['count']

        # Count total books
        cursor.execute("SELECT COUNT(*) as count FROM books")
        total_books = cursor.fetchone()['count']

        return {
            'total_series': series_count,
            'total_book_series_links': book_series_links,
            'books_with_series': books_with_series,
            'total_books': total_books,
            'books_without_series': total_books - books_with_series
        }

    def get_series_list(self) -> List[dict]:
        """
        Get list of all series with their book counts.

        Returns:
            List of dictionaries with series information
        """
        if not self.conn:
            return []

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                s.id,
                s.name,
                s.libraryId,
                COUNT(bs.id) as book_count
            FROM series s
            LEFT JOIN bookSeries bs ON s.id = bs.seriesId
            GROUP BY s.id, s.name, s.libraryId
            ORDER BY s.name
        """)

        return [dict(row) for row in cursor.fetchall()]

    def get_books_with_series(self, limit: Optional[int] = None) -> List[dict]:
        """
        Get list of books with their series information.

        Args:
            limit: Optional limit on number of books to return

        Returns:
            List of dictionaries with book and series information
        """
        if not self.conn:
            return []

        cursor = self.conn.cursor()
        query = """
            SELECT
                b.id as book_id,
                b.title as book_title,
                s.id as series_id,
                s.name as series_name,
                bs.sequence
            FROM books b
            LEFT JOIN bookSeries bs ON b.id = bs.bookId
            LEFT JOIN series s ON bs.seriesId = s.id
            WHERE bs.id IS NOT NULL
            ORDER BY s.name, bs.sequence
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]

    def get_books_without_series(self, limit: Optional[int] = None) -> List[dict]:
        """
        Get list of books that are not linked to any series.

        Args:
            limit: Optional limit on number of books to return

        Returns:
            List of dictionaries with book information
        """
        if not self.conn:
            return []

        cursor = self.conn.cursor()
        query = """
            SELECT
                b.id,
                b.title
            FROM books b
            LEFT JOIN bookSeries bs ON b.id = bs.bookId
            WHERE bs.id IS NULL
            ORDER BY b.title
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]

    def get_series_details(self, series_id: str) -> dict:
        """
        Get detailed information about a specific series.

        Args:
            series_id: The series ID to look up

        Returns:
            Dictionary with series details including all books
        """
        if not self.conn:
            return {}

        cursor = self.conn.cursor()

        # Get series info
        cursor.execute("""
            SELECT id, name, libraryId
            FROM series
            WHERE id = ?
        """, (series_id,))

        series_row = cursor.fetchone()
        if not series_row:
            return {}

        series_info = dict(series_row)

        # Get all books in this series
        cursor.execute("""
            SELECT
                b.id,
                b.title,
                bs.sequence
            FROM books b
            JOIN bookSeries bs ON b.id = bs.bookId
            WHERE bs.seriesId = ?
            ORDER BY bs.sequence
        """, (series_id,))

        series_info['books'] = [dict(row) for row in cursor.fetchall()]
        series_info['book_count'] = len(series_info['books'])

        return series_info

    def print_summary(self):
        """Print a summary of series relationships in the database."""
        print("\n" + "="*70)
        print("AUDIOBOOKSHELF SERIES RELATIONSHIP REPORT")
        print("="*70 + "\n")

        summary = self.get_series_summary()

        print("📊 DATABASE SUMMARY")
        print("-" * 70)
        print(f"Total Books:              {summary['total_books']}")
        print(f"Books with Series:        {summary['books_with_series']}")
        print(f"Books without Series:     {summary['books_without_series']}")
        print(f"Total Series:             {summary['total_series']}")
        print(f"Total Book-Series Links:  {summary['total_book_series_links']}")

        if summary['total_books'] > 0:
            percentage = (summary['books_with_series'] / summary['total_books']) * 100
            print(f"Series Coverage:          {percentage:.1f}%")

        print("\n" + "="*70 + "\n")

    def print_series_list(self, show_empty: bool = True):
        """
        Print list of all series.

        Args:
            show_empty: Whether to show series with no books
        """
        series_list = self.get_series_list()

        if not series_list:
            print("No series found in database.")
            return

        print("📚 SERIES LIST")
        print("-" * 70)

        for series in series_list:
            if not show_empty and series['book_count'] == 0:
                continue

            print(f"\nSeries ID: {series['id']}")
            print(f"  Name:       {series['name']}")
            print(f"  Library ID: {series['libraryId']}")
            print(f"  Books:      {series['book_count']}")

        print("\n" + "="*70 + "\n")

    def print_sample_books(self, sample_size: int = 20):
        """
        Print a sample of books with their series.

        Args:
            sample_size: Number of books to display
        """
        books = self.get_books_with_series(limit=sample_size)

        if not books:
            print("No books with series found in database.")
            return

        print(f"📖 SAMPLE BOOKS WITH SERIES (showing {min(sample_size, len(books))} books)")
        print("-" * 70)

        current_series = None
        for book in books:
            if book['series_name'] != current_series:
                current_series = book['series_name']
                print(f"\n{current_series}:")

            sequence_str = f"Book {book['sequence']}" if book['sequence'] else "No sequence"
            print(f"  [{sequence_str}] {book['book_title']}")

        print("\n" + "="*70 + "\n")

    def print_books_without_series(self, sample_size: int = 10):
        """
        Print sample of books without series assignments.

        Args:
            sample_size: Number of books to display
        """
        books = self.get_books_without_series(limit=sample_size)

        if not books:
            print("✓ All books are assigned to series!")
            return

        print(f"📕 BOOKS WITHOUT SERIES (showing {min(sample_size, len(books))} books)")
        print("-" * 70)

        for book in books:
            print(f"  - {book['title']}")

        total_without = self.get_series_summary()['books_without_series']
        if total_without > sample_size:
            print(f"\n  ... and {total_without - sample_size} more books without series")

        print("\n" + "="*70 + "\n")

    def export_to_json(self, output_path: str):
        """
        Export full series report to JSON file.

        Args:
            output_path: Path to output JSON file
        """
        report = {
            'summary': self.get_series_summary(),
            'series': self.get_series_list(),
            'books_with_series': self.get_books_with_series(),
            'books_without_series': self.get_books_without_series()
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"✓ Report exported to: {output_path}")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def find_audiobookshelf_db() -> Optional[Path]:
    """
    Try to find the Audiobookshelf database in common locations.

    Returns:
        Path to database if found, None otherwise
    """
    # Common locations to check
    possible_paths = [
        Path("C:/Users/dogma/AppData/Local/audiobookshelf/data/absdatabase.sqlite"),
        Path("C:/ProgramData/audiobookshelf/data/absdatabase.sqlite"),
        Path.home() / "AppData" / "Local" / "audiobookshelf" / "data" / "absdatabase.sqlite",
        Path.cwd() / "absdatabase.sqlite",
        Path.cwd() / "data" / "absdatabase.sqlite",
    ]

    for path in possible_paths:
        if path.exists():
            return path

    return None


def main():
    """Main entry point for the script."""
    print("\n" + "="*70)
    print("Audiobookshelf Series Relationship Reporter")
    print("="*70 + "\n")

    # Determine database path
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
        print(f"Using provided database path: {db_path}")
    else:
        print("No database path provided, searching common locations...")
        db_path = find_audiobookshelf_db()
        if db_path:
            print(f"✓ Found database at: {db_path}")
        else:
            print("\n❌ Could not find Audiobookshelf database.")
            print("\nPlease provide the database path as an argument:")
            print("  python correct_series_populator.py /path/to/absdatabase.sqlite")
            print("\nCommon locations:")
            print("  - C:/Users/[username]/AppData/Local/audiobookshelf/data/absdatabase.sqlite")
            print("  - C:/ProgramData/audiobookshelf/data/absdatabase.sqlite")
            sys.exit(1)

    # Initialize reporter
    reporter = AudiobookshelfSeriesReporter(str(db_path))

    if not reporter.connect():
        sys.exit(1)

    try:
        # Print comprehensive report
        reporter.print_summary()
        reporter.print_series_list(show_empty=False)
        reporter.print_sample_books(sample_size=30)
        reporter.print_books_without_series(sample_size=10)

        # Ask if user wants to export to JSON
        print("\n" + "="*70)
        export = input("\nExport full report to JSON? (y/n): ").strip().lower()
        if export == 'y':
            output_path = "audiobookshelf_series_report.json"
            reporter.export_to_json(output_path)

    finally:
        reporter.close()

    print("\n✓ Report complete!\n")


if __name__ == "__main__":
    main()
