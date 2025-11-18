"""
Unit tests for database.py module.
"""

import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os
import sqlite3

from database import (
    create_tables,
    insert_chunk,
    get_file_details,
    insert_or_update_file,
    get_chunk_ids_for_file,
    delete_file_records,
    get_chunks_by_ids,
)


class TestDatabase(unittest.TestCase):
    """Test database functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite")
        self.temp_db.close()
        self.db_path = self.temp_db.name

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_create_tables(self):
        """Test create_tables function."""
        create_tables(self.db_path)

        # Verify tables were created
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check files table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='files'"
        )
        self.assertTrue(cursor.fetchone())

        # Check chunks table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='chunks'"
        )
        self.assertTrue(cursor.fetchone())

        conn.close()

    def test_insert_chunk(self):
        """Test insert_chunk function."""
        create_tables(self.db_path)

        chunk_id = insert_chunk(1, "test chunk text", "header metadata", self.db_path)

        self.assertIsInstance(chunk_id, int)
        self.assertGreater(chunk_id, 0)

        # Verify insertion
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,))
        row = cursor.fetchone()
        self.assertEqual(row[1], 1)  # file_id
        self.assertEqual(row[2], "test chunk text")  # chunk_text
        self.assertEqual(row[3], "header metadata")  # header_metadata
        conn.close()

    def test_get_file_details(self):
        """Test get_file_details function."""
        create_tables(self.db_path)

        # Insert test data
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO files (path, last_modified, file_hash) VALUES (?, ?, ?)",
            ("test/path.md", 1234567890.0, "hash123"),
        )
        conn.commit()
        conn.close()

        result = get_file_details("test/path.md", self.db_path)
        self.assertEqual(result, (1, "hash123"))

    def test_get_file_details_not_found(self):
        """Test get_file_details for non-existent file."""
        create_tables(self.db_path)

        result = get_file_details("nonexistent.md", self.db_path)
        self.assertIsNone(result)

    def test_insert_or_update_file_insert(self):
        """Test insert_or_update_file insert operation."""
        create_tables(self.db_path)

        file_id = insert_or_update_file(
            "test/path.md", 1234567890.0, "hash123", self.db_path
        )

        self.assertIsInstance(file_id, int)
        self.assertGreater(file_id, 0)

        # Verify insertion
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM files WHERE file_id = ?", (file_id,))
        row = cursor.fetchone()
        self.assertEqual(row[1], "test/path.md")  # path
        self.assertEqual(row[2], 1234567890.0)  # last_modified
        self.assertEqual(row[3], "hash123")  # file_hash
        conn.close()

    def test_insert_or_update_file_update(self):
        """Test insert_or_update_file update operation."""
        create_tables(self.db_path)

        # Insert first
        file_id1 = insert_or_update_file(
            "test/path.md", 1234567890.0, "hash123", self.db_path
        )

        # Update
        file_id2 = insert_or_update_file(
            "test/path.md", 1234567891.0, "hash456", self.db_path
        )

        # INSERT OR REPLACE may change the ID, so check the data was updated
        # Verify update
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM files WHERE path = ?", ("test/path.md",))
        row = cursor.fetchone()
        self.assertEqual(row[2], 1234567891.0)  # last_modified updated
        self.assertEqual(row[3], "hash456")  # file_hash updated
        conn.close()

    def test_get_chunk_ids_for_file(self):
        """Test get_chunk_ids_for_file function."""
        create_tables(self.db_path)

        # Insert file
        file_id = insert_or_update_file("test.md", 1234567890.0, "hash", self.db_path)

        # Insert chunks
        chunk_id1 = insert_chunk(file_id, "chunk1", "header1", self.db_path)
        chunk_id2 = insert_chunk(file_id, "chunk2", "header2", self.db_path)

        chunk_ids = get_chunk_ids_for_file(file_id, self.db_path)

        self.assertEqual(len(chunk_ids), 2)
        self.assertIn(chunk_id1, chunk_ids)
        self.assertIn(chunk_id2, chunk_ids)

    def test_get_chunk_ids_for_file_no_chunks(self):
        """Test get_chunk_ids_for_file with no chunks."""
        create_tables(self.db_path)

        file_id = insert_or_update_file("test.md", 1234567890.0, "hash", self.db_path)

        chunk_ids = get_chunk_ids_for_file(file_id, self.db_path)

        self.assertEqual(chunk_ids, [])

    def test_delete_file_records(self):
        """Test delete_file_records function."""
        create_tables(self.db_path)

        # Insert file and chunks
        file_id = insert_or_update_file("test.md", 1234567890.0, "hash", self.db_path)
        chunk_id1 = insert_chunk(file_id, "chunk1", "header1", self.db_path)
        chunk_id2 = insert_chunk(file_id, "chunk2", "header2", self.db_path)

        # Delete records
        delete_file_records(file_id, self.db_path)

        # Verify deletion
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM files WHERE file_id = ?", (file_id,))
        self.assertEqual(cursor.fetchone()[0], 0)
        cursor.execute("SELECT COUNT(*) FROM chunks WHERE file_id = ?", (file_id,))
        self.assertEqual(cursor.fetchone()[0], 0)
        conn.close()

    def test_get_chunks_by_ids(self):
        """Test get_chunks_by_ids function."""
        create_tables(self.db_path)

        # Insert file
        file_id = insert_or_update_file("test.md", 1234567890.0, "hash", self.db_path)

        # Insert chunks
        chunk_id1 = insert_chunk(file_id, "chunk text 1", "header1", self.db_path)
        chunk_id2 = insert_chunk(file_id, "chunk text 2", "header2", self.db_path)

        results = get_chunks_by_ids([chunk_id1, chunk_id2], self.db_path)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0][0], "chunk text 1")  # chunk_text
        self.assertEqual(results[0][1], "test.md")  # path
        self.assertEqual(results[0][2], "header1")  # header_metadata

        self.assertEqual(results[1][0], "chunk text 2")
        self.assertEqual(results[1][1], "test.md")
        self.assertEqual(results[1][2], "header2")

    def test_get_chunks_by_ids_empty(self):
        """Test get_chunks_by_ids with empty list."""
        create_tables(self.db_path)

        results = get_chunks_by_ids([], self.db_path)

        self.assertEqual(results, [])

    def test_get_chunks_by_ids_invalid_ids(self):
        """Test get_chunks_by_ids with non-existent IDs."""
        create_tables(self.db_path)

        results = get_chunks_by_ids([999, 1000], self.db_path)

        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
