import sqlite3
import os

def create_tables(db_path='metadata.sqlite'):
    """Create the SQLite database tables for storing file and chunk metadata."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Table to track files and their processed state
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS files (
        file_id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT UNIQUE NOT NULL,
        last_modified REAL NOT NULL,
        file_hash TEXT NOT NULL
    )''')

    # Table to store the actual text chunks and their metadata
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chunks (
        chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id INTEGER NOT NULL,
        chunk_text TEXT NOT NULL,
        header_metadata TEXT,
        FOREIGN KEY(file_id) REFERENCES files(file_id)
    )''')
    conn.commit()
    conn.close()

def insert_chunk(file_id, text, metadata, db_path='metadata.sqlite'):
    """Insert a chunk into the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chunks (file_id, chunk_text, header_metadata) VALUES (?, ?, ?)",
        (file_id, text, metadata)
    )
    chunk_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return chunk_id

def get_file_details(path, db_path='metadata.sqlite'):
    """Get file details from database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT file_id, file_hash FROM files WHERE path = ?", (path,))
    result = cursor.fetchone()
    conn.close()
    return result

def insert_or_update_file(path, last_modified, file_hash, db_path='metadata.sqlite'):
    """Insert or update file record."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO files (path, last_modified, file_hash) VALUES (?, ?, ?)",
        (path, last_modified, file_hash)
    )
    file_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return file_id

def get_chunk_ids_for_file(file_id, db_path='metadata.sqlite'):
    """Get all chunk IDs for a file."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT chunk_id FROM chunks WHERE file_id = ?", (file_id,))
    chunk_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return chunk_ids

def delete_file_records(file_id, db_path='metadata.sqlite'):
    """Delete all records for a file."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chunks WHERE file_id = ?", (file_id,))
    cursor.execute("DELETE FROM files WHERE file_id = ?", (file_id,))
    conn.commit()
    conn.close()

def get_chunks_by_ids(chunk_ids, db_path='metadata.sqlite'):
    """Get chunks by their IDs."""
    if not chunk_ids:
        return []
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    placeholders = ','.join(['?'] * len(chunk_ids))
    query = f"""
    SELECT c.chunk_text, f.path, c.header_metadata
    FROM chunks c
    JOIN files f ON c.file_id = f.file_id
    WHERE c.chunk_id IN ({placeholders})
    """
    results = cursor.fetchall()
    conn.close()
    return results