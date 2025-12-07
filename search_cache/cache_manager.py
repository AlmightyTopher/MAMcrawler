#!/usr/bin/env python3
"""
Caching system for the unified search system.
Provides TTL-based caching with SQLite backend.
"""

import asyncio
import sqlite3
import json
import time
import logging
import os
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from search_types import CacheInterface

logger = logging.getLogger(__name__)


class SearchCache(CacheInterface):
    """
    SQLite-based cache with TTL support for search results.

    Features:
    - TTL (Time To Live) based expiration
    - Automatic cleanup of expired entries
    - Thread-safe operations
    - JSON serialization for complex objects
    """

    def __init__(self, db_path: str = "search_cache/cache.db", max_size_mb: int = 100):
        """
        Initialize the cache

        Args:
            db_path: Path to SQLite database file
            max_size_mb: Maximum cache size in MB before cleanup
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_size_mb = max_size_mb
        self._connection = None
        self._lock = asyncio.Lock()

        # Default TTL values for different provider types (in seconds)
        self.default_ttl = {
            'audiobookshelf': 300,   # 5 minutes for local library
            'prowlarr': 1800,        # 30 minutes for indexer results
            'mam': 900,              # 15 minutes for direct searches
            'goodreads': 3600,       # 1 hour for metadata
            'local': 60              # 1 minute for local searches
        }

        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    ttl INTEGER NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    last_accessed REAL
                )
            ''')

            # Create indexes for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_ttl ON cache(ttl)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_created ON cache(created_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_access ON cache(last_accessed)')

            conn.commit()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection (creates if needed)"""
        if self._connection is None:
            self._connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
        return self._connection

    def _serialize_value(self, value: Any) -> str:
        """Serialize value to JSON string"""
        if hasattr(value, 'to_dict'):
            return json.dumps(value.to_dict())
        elif isinstance(value, (list, dict)):
            # Handle SearchResult objects in lists
            if isinstance(value, list) and value and hasattr(value[0], 'to_dict'):
                return json.dumps([item.to_dict() for item in value])
            return json.dumps(value)
        else:
            return json.dumps(value)

    def _deserialize_value(self, value_str: str) -> Any:
        """Deserialize value from JSON string"""
        return json.loads(value_str)

    async def get(self, key: str) -> Optional[Any]:
        """
        Get cached value by key

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()

                # Get value and check if expired
                cursor.execute('''
                    SELECT value, created_at, ttl, access_count
                    FROM cache
                    WHERE key = ?
                ''', (key,))

                row = cursor.fetchone()
                if not row:
                    return None

                value_str, created_at, ttl, access_count = row
                current_time = time.time()

                # Check if expired
                if current_time - created_at > ttl:
                    # Remove expired entry
                    await self.delete(key)
                    return None

                # Update access statistics
                cursor.execute('''
                    UPDATE cache
                    SET access_count = ?, last_accessed = ?
                    WHERE key = ?
                ''', (access_count + 1, current_time, key))
                conn.commit()

                # Deserialize and return
                return self._deserialize_value(value_str)

            except Exception as e:
                logger.error(f"Cache get error for key '{key}': {e}")
                return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set cached value

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if None)

        Returns:
            True if successful
        """
        async with self._lock:
            try:
                # Determine TTL
                if ttl is None:
                    # Extract provider type from key for default TTL
                    provider_type = key.split(':')[0] if ':' in key else 'default'
                    ttl = self.default_ttl.get(provider_type, 1800)  # 30 min default

                conn = self._get_connection()
                cursor = conn.cursor()

                # Serialize value
                value_str = self._serialize_value(value)
                current_time = time.time()

                # Insert or replace
                cursor.execute('''
                    INSERT OR REPLACE INTO cache
                    (key, value, created_at, ttl, access_count, last_accessed)
                    VALUES (?, ?, ?, ?, 0, ?)
                ''', (key, value_str, current_time, ttl, current_time))

                conn.commit()

                # Check if we need to cleanup (size limit)
                await self._check_size_limit()

                return True

            except Exception as e:
                logger.error(f"Cache set error for key '{key}': {e}")
                return False

    async def delete(self, key: str) -> bool:
        """
        Delete cached value

        Args:
            key: Cache key

        Returns:
            True if successful
        """
        async with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute('DELETE FROM cache WHERE key = ?', (key,))
                conn.commit()

                return cursor.rowcount > 0

            except Exception as e:
                logger.error(f"Cache delete error for key '{key}': {e}")
                return False

    async def clear(self) -> bool:
        """
        Clear all cached values

        Returns:
            True if successful
        """
        async with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute('DELETE FROM cache')
                conn.commit()

                return True

            except Exception as e:
                logger.error(f"Cache clear error: {e}")
                return False

    async def cleanup(self):
        """Cleanup expired entries and close connections"""
        try:
            await self._cleanup_expired()
            if self._connection:
                self._connection.close()
                self._connection = None
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")

    async def _cleanup_expired(self):
        """Remove expired cache entries"""
        async with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()

                current_time = time.time()
                cursor.execute('DELETE FROM cache WHERE (created_at + ttl) < ?', (current_time,))
                deleted_count = cursor.rowcount

                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} expired cache entries")

                conn.commit()

            except Exception as e:
                logger.error(f"Expired cleanup error: {e}")

    async def _check_size_limit(self):
        """Check if cache size exceeds limit and cleanup if needed"""
        try:
            # Get current database size
            if os.path.exists(self.db_path):
                size_mb = os.path.getsize(self.db_path) / (1024 * 1024)

                if size_mb > self.max_size_mb:
                    logger.info(f"Cache size {size_mb:.1f}MB exceeds limit {self.max_size_mb}MB, cleaning up...")

                    # Remove oldest entries first (LRU-style)
                    conn = self._get_connection()
                    cursor = conn.cursor()

                    # Keep only the most recently accessed entries
                    cursor.execute('''
                        DELETE FROM cache
                        WHERE key NOT IN (
                            SELECT key FROM cache
                            ORDER BY last_accessed DESC
                            LIMIT (SELECT COUNT(*) FROM cache) / 2
                        )
                    ''')

                    deleted_count = cursor.rowcount
                    conn.commit()

                    logger.info(f"Removed {deleted_count} old cache entries")

        except Exception as e:
            logger.error(f"Size limit check error: {e}")

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache stats
        """
        async with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()

                # Get total entries
                cursor.execute('SELECT COUNT(*) FROM cache')
                total_entries = cursor.fetchone()[0]

                # Get expired entries
                current_time = time.time()
                cursor.execute('SELECT COUNT(*) FROM cache WHERE (created_at + ttl) < ?', (current_time,))
                expired_entries = cursor.fetchone()[0]

                # Get total size
                size_bytes = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                size_mb = size_bytes / (1024 * 1024)

                # Get hit statistics
                cursor.execute('SELECT SUM(access_count), AVG(access_count) FROM cache')
                total_accesses, avg_accesses = cursor.fetchone()

                return {
                    'total_entries': total_entries,
                    'expired_entries': expired_entries,
                    'active_entries': total_entries - expired_entries,
                    'size_mb': round(size_mb, 2),
                    'max_size_mb': self.max_size_mb,
                    'total_accesses': total_accesses or 0,
                    'avg_accesses_per_entry': round(avg_accesses or 0, 2),
                    'db_path': str(self.db_path)
                }

            except Exception as e:
                logger.error(f"Cache stats error: {e}")
                return {'error': str(e)}

    async def get_keys(self, pattern: Optional[str] = None) -> List[str]:
        """
        Get all cache keys (optionally filtered by pattern)

        Args:
            pattern: SQL LIKE pattern to filter keys

        Returns:
            List of cache keys
        """
        async with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()

                if pattern:
                    cursor.execute('SELECT key FROM cache WHERE key LIKE ?', (pattern,))
                else:
                    cursor.execute('SELECT key FROM cache')

                return [row[0] for row in cursor.fetchall()]

            except Exception as e:
                logger.error(f"Get keys error: {e}")
                return []

    def __del__(self):
        """Destructor - ensure connection is closed"""
        if self._connection:
            try:
                self._connection.close()
            except:
                pass