"""
Optimized Database Connection Pooling for MAMcrawler

This module provides high-performance database connection pooling with advanced features
including connection health monitoring, automatic retry, query optimization, and resource pooling.

Author: Audiobook Automation System
Version: 1.0.0
"""

import asyncio
import logging
import time
import weakref
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from queue import Queue, Empty, Full
from threading import RLock, Event, Thread
from typing import Any, Dict, List, Optional, Tuple, Union, Callable, Set
from urllib.parse import urlparse
import ssl
import json


class ConnectionStatus(Enum):
    """Database connection status."""
    IDLE = "idle"
    ACTIVE = "active"
    TESTING = "testing"
    FAILED = "failed"
    CLOSED = "closed"


@dataclass
class ConnectionMetrics:
    """Metrics for database connection."""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    total_queries: int = 0
    failed_queries: int = 0
    avg_query_time: float = 0.0
    connection_timeouts: int = 0
    pool_hits: int = 0
    pool_misses: int = 0
    last_health_check: Optional[datetime] = None


@dataclass
class DatabaseConfig:
    """Enhanced database configuration."""
    connection_string: str
    max_connections: int = 20
    min_connections: int = 5
    max_idle_time: int = 300  # 5 minutes
    connection_timeout: int = 30
    query_timeout: int = 60
    health_check_interval: int = 60
    retry_attempts: int = 3
    retry_delay: float = 1.0
    ssl_mode: str = "prefer"
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None
    ssl_ca: Optional[str] = None
    connection_recycle: int = 3600  # 1 hour
    max_overflow: int = 10
    pool_pre_ping: bool = True
    pool_recycle: bool = True
    echo_queries: bool = False
    
    # Connection pool settings
    pool_size: int = 10
    pool_timeout: int = 30
    pool_recycle_time: int = -1
    pool_reset_on_return: bool = True
    
    # Performance settings
    enable_statement_cache: bool = True
    max_statement_cache_size: int = 1000
    enable_foreign_keys: bool = True
    enable_wal_mode: bool = True
    
    def __post_init__(self):
        """Validate configuration."""
        if self.max_connections < self.min_connections:
            raise ValueError("max_connections must be >= min_connections")
        
        if self.connection_timeout <= 0:
            raise ValueError("connection_timeout must be positive")


class DatabaseConnection:
    """Wrapper for database connection with health monitoring."""
    
    def __init__(self, conn: Any, config: DatabaseConfig, connection_id: str):
        self._conn = conn
        self.config = config
        self.connection_id = connection_id
        self.status = ConnectionStatus.IDLE
        self.created_at = datetime.now()
        self.last_used_at = datetime.now()
        self.last_health_check = datetime.now()
        self.query_count = 0
        self.failed_queries = 0
        self.total_query_time = 0.0
        self._lock = RLock()
        self.logger = logging.getLogger(f"db_conn.{connection_id}")
    
    async def execute(self, query: str, params: Optional[Dict] = None) -> Any:
        """Execute query with timing and error handling."""
        start_time = time.time()
        
        try:
            self.status = ConnectionStatus.ACTIVE
            self.last_used_at = datetime.now()
            self.query_count += 1
            
            # Execute query
            if params:
                result = await self._execute_with_params(query, params)
            else:
                result = await self._execute_query(query)
            
            execution_time = time.time() - start_time
            self.total_query_time += execution_time
            
            self.logger.debug(f"Query executed in {execution_time:.3f}s")
            return result
            
        except Exception as e:
            self.failed_queries += 1
            self.logger.error(f"Query failed: {e}")
            raise
            
        finally:
            self.status = ConnectionStatus.IDLE
    
    async def _execute_query(self, query: str) -> Any:
        """Execute raw query."""
        # This would be implemented based on specific database driver
        # For example, with asyncpg for PostgreSQL:
        # return await self._conn.fetch(query)
        pass
    
    async def _execute_with_params(self, query: str, params: Dict) -> Any:
        """Execute query with parameters."""
        # This would be implemented based on specific database driver
        pass
    
    async def health_check(self) -> bool:
        """Perform connection health check."""
        try:
            self.status = ConnectionStatus.TESTING
            
            # Simple health check query
            if hasattr(self._conn, 'execute'):
                await self._conn.execute("SELECT 1")
            elif hasattr(self._conn, 'ping'):
                await self._conn.ping()
            else:
                # Fallback: try a simple query
                await self._execute_query("SELECT 1")
            
            self.last_health_check = datetime.now()
            self.logger.debug("Health check passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
            
        finally:
            if self.status == ConnectionStatus.TESTING:
                self.status = ConnectionStatus.IDLE
    
    def is_healthy(self) -> bool:
        """Check if connection is healthy based on last health check."""
        time_since_check = datetime.now() - self.last_health_check
        return time_since_check.total_seconds() < self.config.health_check_interval
    
    def needs_health_check(self) -> bool:
        """Check if connection needs a health check."""
        time_since_check = datetime.now() - self.last_health_check
        return time_since_check.total_seconds() >= self.config.health_check_interval
    
    def is_expired(self) -> bool:
        """Check if connection is expired."""
        age = datetime.now() - self.created_at
        return age.total_seconds() >= self.config.connection_recycle
    
    def should_be_closed(self) -> bool:
        """Check if connection should be closed."""
        return (self.is_expired() or 
                self.status == ConnectionStatus.FAILED or
                not self.is_healthy())
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get connection metrics."""
        with self._lock:
            return {
                "connection_id": self.connection_id,
                "status": self.status.value,
                "created_at": self.created_at.isoformat(),
                "last_used_at": self.last_used_at.isoformat(),
                "last_health_check": self.last_health_check.isoformat(),
                "query_count": self.query_count,
                "failed_queries": self.failed_queries,
                "avg_query_time": (
                    self.total_query_time / self.query_count 
                    if self.query_count > 0 else 0.0
                ),
                "healthy": self.is_healthy(),
                "expired": self.is_expired()
            }
    
    async def close(self):
        """Close the connection."""
        try:
            if hasattr(self._conn, 'close'):
                await self._conn.close()
            self.status = ConnectionStatus.CLOSED
            self.logger.info("Connection closed")
        except Exception as e:
            self.logger.error(f"Error closing connection: {e}")


class ConnectionPool:
    """Advanced database connection pool."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.logger = logging.getLogger("db_pool")
        
        # Connection management
        self._connections: Dict[str, DatabaseConnection] = {}
        self._idle_connections: Queue = Queue(maxsize=config.max_connections)
        self._active_connections: Set[str] = set()
        self._connection_counter = 0
        
        # Lock for thread safety
        self._lock = RLock()
        self._shutdown_event = Event()
        
        # Health monitoring
        self._health_check_thread: Optional[Thread] = None
        self._metrics = ConnectionMetrics()
        
        # Pool statistics
        self._total_created = 0
        self._total_destroyed = 0
        self._peak_connections = 0
        
        # Start health monitoring
        self._start_health_monitor()
        
        # Initialize minimum connections
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize minimum number of connections."""
        self.logger.info("Initializing connection pool")
        
        for _ in range(self.config.min_connections):
            try:
                conn = self._create_connection()
                self._add_to_pool(conn)
            except Exception as e:
                self.logger.error(f"Failed to create initial connection: {e}")
    
    def _create_connection(self) -> DatabaseConnection:
        """Create new database connection."""
        self._connection_counter += 1
        connection_id = f"conn_{self._connection_counter}"
        
        try:
            # This would be implemented based on specific database driver
            # For example, with asyncpg:
            # import asyncpg
            # raw_conn = await asyncpg.connect(self.config.connection_string)
            
            # For now, create a mock connection
            raw_conn = self._create_mock_connection()
            
            # Configure SSL if needed
            if self.config.ssl_mode != "disable":
                self._configure_ssl(raw_conn)
            
            connection = DatabaseConnection(raw_conn, self.config, connection_id)
            
            with self._lock:
                self._total_created += 1
                self._metrics.total_connections += 1
            
            self.logger.debug(f"Created new connection: {connection_id}")
            return connection
            
        except Exception as e:
            self.logger.error(f"Failed to create connection: {e}")
            raise
    
    def _create_mock_connection(self) -> Any:
        """Create mock connection for testing."""
        # This would be replaced with actual database connection
        class MockConnection:
            def __init__(self):
                self.closed = False
            
            async def execute(self, query: str):
                return "OK"
            
            async def fetch(self, query: str):
                return []
            
            async def fetchval(self, query: str):
                return None
            
            async def close(self):
                self.closed = True
        
        return MockConnection()
    
    def _configure_ssl(self, conn: Any):
        """Configure SSL for connection."""
        if not self.config.ssl_mode or self.config.ssl_mode == "disable":
            return
        
        ssl_context = ssl.create_default_context()
        
        if self.config.ssl_ca:
            ssl_context.load_verify_locations(self.config.ssl_ca)
        
        if self.config.ssl_cert and self.config.ssl_key:
            ssl_context.load_cert_chain(self.config.ssl_cert, self.config.ssl_key)
        
        # Apply SSL context to connection
        # This would be implemented based on specific database driver
    
    def _add_to_pool(self, connection: DatabaseConnection):
        """Add connection to idle pool."""
        try:
            self._idle_connections.put_nowait(connection)
            self._connections[connection.connection_id] = connection
            
            with self._lock:
                current_size = len(self._connections)
                if current_size > self._peak_connections:
                    self._peak_connections = current_size
                
                self._metrics.idle_connections += 1
            
            self.logger.debug(f"Added connection {connection.connection_id} to pool")
            
        except Full:
            self.logger.warning("Pool is full, discarding connection")
            asyncio.create_task(connection.close())
    
    def _remove_from_pool(self, connection_id: str):
        """Remove connection from pool."""
        if connection_id in self._connections:
            connection = self._connections[connection_id]
            del self._connections[connection_id]
            
            with self._lock:
                self._metrics.total_connections -= 1
                self._metrics.idle_connections -= 1
            
            self.logger.debug(f"Removed connection {connection_id} from pool")
    
    @asynccontextmanager
    async def acquire(self, timeout: Optional[float] = None):
        """Acquire connection from pool."""
        timeout = timeout or self.config.pool_timeout
        connection = None
        
        try:
            # Try to get connection from pool
            connection = await self._get_connection(timeout)
            
            # Validate connection
            if not await self._validate_connection(connection):
                self.logger.warning("Connection validation failed, creating new one")
                await self._replace_connection(connection)
                connection = await self._get_connection(timeout)
            
            yield connection
            
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            if connection:
                await self._mark_connection_failed(connection)
            raise
            
        finally:
            if connection:
                await self._return_connection(connection)
    
    async def _get_connection(self, timeout: float) -> DatabaseConnection:
        """Get connection from pool with timeout."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Try to get from idle pool
            try:
                connection = self._idle_connections.get_nowait()
                
                with self._lock:
                    self._active_connections.add(connection.connection_id)
                    self._metrics.idle_connections -= 1
                    self._metrics.active_connections += 1
                    self._metrics.pool_hits += 1
                
                self.logger.debug(f"Acquired connection {connection.connection_id}")
                return connection
                
            except Empty:
                pass
            
            # Pool miss, check if we can create new connection
            with self._lock:
                current_size = len(self._connections)
                
                if current_size < self.config.max_connections:
                    # Create new connection
                    connection = self._create_connection()
                    self._connections[connection.connection_id] = connection
                    self._active_connections.add(connection.connection_id)
                    self._metrics.pool_misses += 1
                    
                    self.logger.debug(f"Created new connection {connection.connection_id}")
                    return connection
            
            # Wait a bit before retrying
            await asyncio.sleep(0.1)
        
        raise TimeoutError("Failed to acquire connection within timeout")
    
    async def _validate_connection(self, connection: DatabaseConnection) -> bool:
        """Validate connection health."""
        if connection.needs_health_check():
            return await connection.health_check()
        
        return connection.is_healthy()
    
    async def _replace_connection(self, failed_connection: DatabaseConnection):
        """Replace failed connection with new one."""
        await self._mark_connection_failed(failed_connection)
        
        # Create replacement
        try:
            new_connection = self._create_connection()
            self._add_to_pool(new_connection)
            self.logger.info(f"Replaced failed connection with {new_connection.connection_id}")
        except Exception as e:
            self.logger.error(f"Failed to create replacement connection: {e}")
    
    async def _mark_connection_failed(self, connection: DatabaseConnection):
        """Mark connection as failed and remove from pool."""
        connection.status = ConnectionStatus.FAILED
        
        with self._lock:
            self._active_connections.discard(connection.connection_id)
            self._metrics.active_connections -= 1
            self._metrics.failed_connections += 1
        
        self._remove_from_pool(connection.connection_id)
        asyncio.create_task(connection.close())
    
    async def _return_connection(self, connection: DatabaseConnection):
        """Return connection to pool."""
        if connection.should_be_closed():
            await self._mark_connection_failed(connection)
            return
        
        # Reset connection state
        connection.status = ConnectionStatus.IDLE
        
        with self._lock:
            self._active_connections.discard(connection.connection_id)
            self._metrics.active_connections -= 1
            self._metrics.idle_connections += 1
        
        # Try to add back to pool
        try:
            self._idle_connections.put_nowait(connection)
            self.logger.debug(f"Returned connection {connection.connection_id} to pool")
        except Full:
            # Pool is full, close connection
            await self._mark_connection_failed(connection)
    
    def _start_health_monitor(self):
        """Start background health monitoring thread."""
        def health_monitor():
            while not self._shutdown_event.is_set():
                try:
                    asyncio.run(self._perform_health_checks())
                    time.sleep(self.config.health_check_interval)
                except Exception as e:
                    self.logger.error(f"Health monitor error: {e}")
        
        self._health_check_thread = Thread(target=health_monitor, daemon=True)
        self._health_check_thread.start()
        self.logger.info("Health monitoring started")
    
    async def _perform_health_checks(self):
        """Perform health checks on all connections."""
        connections_to_check = []
        
        with self._lock:
            for connection in self._connections.values():
                if connection.needs_health_check():
                    connections_to_check.append(connection)
        
        for connection in connections_to_check:
            try:
                healthy = await connection.health_check()
                if not healthy:
                    await self._mark_connection_failed(connection)
            except Exception as e:
                self.logger.error(f"Health check error for {connection.connection_id}: {e}")
                await self._mark_connection_failed(connection)
    
    def get_metrics(self) -> ConnectionMetrics:
        """Get pool metrics."""
        with self._lock:
            # Update current metrics
            self._metrics.total_connections = len(self._connections)
            self._metrics.active_connections = len(self._active_connections)
            self._metrics.last_health_check = datetime.now()
            
            return self._metrics
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get detailed pool status."""
        metrics = self.get_metrics()
        
        with self._lock:
            return {
                "metrics": {
                    "total_connections": metrics.total_connections,
                    "active_connections": metrics.active_connections,
                    "idle_connections": metrics.idle_connections,
                    "failed_connections": metrics.failed_connections,
                    "total_queries": metrics.total_queries,
                    "failed_queries": metrics.failed_queries,
                    "avg_query_time": metrics.avg_query_time,
                    "connection_timeouts": metrics.connection_timeouts,
                    "pool_hits": metrics.pool_hits,
                    "pool_misses": metrics.pool_misses,
                    "hit_ratio": (
                        metrics.pool_hits / (metrics.pool_hits + metrics.pool_misses)
                        if (metrics.pool_hits + metrics.pool_misses) > 0 else 0.0
                    )
                },
                "configuration": {
                    "max_connections": self.config.max_connections,
                    "min_connections": self.config.min_connections,
                    "pool_size": self.config.pool_size,
                    "connection_timeout": self.config.connection_timeout,
                    "health_check_interval": self.config.health_check_interval
                },
                "statistics": {
                    "total_created": self._total_created,
                    "total_destroyed": self._total_destroyed,
                    "peak_connections": self._peak_connections
                },
                "connections": [
                    conn.get_metrics() for conn in self._connections.values()
                ]
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform overall pool health check."""
        try:
            metrics = self.get_metrics()
            
            # Check connection utilization
            utilization = (
                metrics.active_connections / self.config.max_connections
                if self.config.max_connections > 0 else 0.0
            )
            
            # Check failure rate
            total_queries = metrics.total_queries
            failure_rate = (
                metrics.failed_queries / total_queries
                if total_queries > 0 else 0.0
            )
            
            # Determine health status
            if utilization > 0.9:
                status = "critical"
                reason = "High connection utilization"
            elif utilization > 0.7:
                status = "warning"
                reason = "Moderate connection utilization"
            elif failure_rate > 0.1:
                status = "warning"
                reason = "High query failure rate"
            elif metrics.failed_connections > 0:
                status = "degraded"
                reason = "Some connections are failed"
            else:
                status = "healthy"
                reason = "All systems normal"
            
            return {
                "status": status,
                "reason": reason,
                "utilization": utilization,
                "failure_rate": failure_rate,
                "metrics": metrics.__dict__
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "reason": str(e),
                "utilization": 0.0,
                "failure_rate": 1.0
            }
    
    async def close(self):
        """Close all connections and shutdown pool."""
        self.logger.info("Closing connection pool")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Wait for health monitor thread
        if self._health_check_thread:
            self._health_check_thread.join(timeout=5)
        
        # Close all connections
        close_tasks = []
        with self._lock:
            for connection in self._connections.values():
                close_tasks.append(connection.close())
        
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        # Clear pools
        while not self._idle_connections.empty():
            try:
                self._idle_connections.get_nowait()
            except Empty:
                break
        
        self._connections.clear()
        self._active_connections.clear()
        
        self.logger.info("Connection pool closed")


class DatabaseManager:
    """High-level database manager with query optimization."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.logger = logging.getLogger("db_manager")
        self.pool: Optional[ConnectionPool] = None
        
        # Query optimization
        self._statement_cache: Dict[str, Any] = {}
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
        
        # Connection retry logic
        self._max_retries = config.retry_attempts
        self._retry_delay = config.retry_delay
    
    async def initialize(self):
        """Initialize database manager."""
        self.logger.info("Initializing database manager")
        
        try:
            # Create connection pool
            self.pool = ConnectionPool(self.config)
            
            # Test connection
            await self._test_connection()
            
            self.logger.info("Database manager initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database manager: {e}")
            raise
    
    async def _test_connection(self):
        """Test database connection."""
        async with self.pool.acquire() as conn:
            # This would be implemented based on specific database
            # For example, with asyncpg:
            # result = await conn.execute("SELECT 1")
            # assert "1" in str(result)
            pass
    
    @asynccontextmanager
    async def get_connection(self, timeout: Optional[float] = None):
        """Get database connection from pool."""
        if not self.pool:
            raise RuntimeError("Database manager not initialized")
        
        async with self.pool.acquire(timeout) as connection:
            yield connection
    
    async def execute_query(self, query: str, params: Optional[Dict] = None, 
                          timeout: Optional[float] = None) -> Any:
        """Execute query with retry and optimization."""
        query_key = self._get_cache_key(query, params)
        
        # Check cache for prepared statements
        cached_statement = self._get_cached_statement(query_key)
        
        for attempt in range(self._max_retries + 1):
            try:
                async with self.get_connection(timeout) as conn:
                    if cached_statement:
                        result = await conn.execute(cached_statement, params)
                    else:
                        result = await conn.execute(query, params)
                    
                    # Cache successful prepared statements
                    if not cached_statement and self.config.enable_statement_cache:
                        self._cache_statement(query_key, result)
                    
                    return result
                    
            except Exception as e:
                if attempt < self._max_retries:
                    wait_time = self._retry_delay * (2 ** attempt)
                    self.logger.warning(
                        f"Query attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"Query failed after {self._max_retries + 1} attempts: {e}")
                    raise
    
    async def fetch_all(self, query: str, params: Optional[Dict] = None,
                       timeout: Optional[float] = None) -> List[Any]:
        """Fetch all results from query."""
        query_key = self._get_cache_key(query, params)
        
        cached_statement = self._get_cached_statement(query_key)
        
        for attempt in range(self._max_retries + 1):
            try:
                async with self.get_connection(timeout) as conn:
                    if cached_statement:
                        result = await conn.fetch(cached_statement, params)
                    else:
                        result = await conn.fetch(query, params)
                    
                    # Cache successful prepared statements
                    if not cached_statement and self.config.enable_statement_cache:
                        self._cache_statement(query_key, result)
                    
                    return result
                    
            except Exception as e:
                if attempt < self._max_retries:
                    wait_time = self._retry_delay * (2 ** attempt)
                    self.logger.warning(
                        f"Fetch attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"Fetch failed after {self._max_retries + 1} attempts: {e}")
                    raise
    
    async def fetch_one(self, query: str, params: Optional[Dict] = None,
                       timeout: Optional[float] = None) -> Optional[Any]:
        """Fetch single result from query."""
        results = await self.fetch_all(query, params, timeout)
        return results[0] if results else None
    
    async def fetch_value(self, query: str, params: Optional[Dict] = None,
                         timeout: Optional[float] = None) -> Any:
        """Fetch single value from query."""
        result = await self.fetch_one(query, params, timeout)
        return result[0] if result else None
    
    def _get_cache_key(self, query: str, params: Optional[Dict]) -> str:
        """Generate cache key for query."""
        # Simple hash-based key
        import hashlib
        content = f"{query}_{hash(str(sorted(params.items()))) if params else ''}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cached_statement(self, query_key: str) -> Optional[str]:
        """Get cached prepared statement."""
        if query_key in self._statement_cache:
            self._cache_stats["hits"] += 1
            return self._statement_cache[query_key]
        
        self._cache_stats["misses"] += 1
        return None
    
    def _cache_statement(self, query_key: str, result: Any):
        """Cache prepared statement."""
        if len(self._statement_cache) >= self.config.max_statement_cache_size:
            # Simple LRU eviction
            oldest_key = next(iter(self._statement_cache))
            del self._statement_cache[oldest_key]
            self._cache_stats["evictions"] += 1
        
        # Extract prepared statement from result
        # This would be implemented based on specific database driver
        prepared_statement = str(result)  # Placeholder
        
        self._statement_cache[query_key] = prepared_statement
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statement cache statistics."""
        total_requests = self._cache_stats["hits"] + self._cache_stats["misses"]
        hit_ratio = (
            self._cache_stats["hits"] / total_requests
            if total_requests > 0 else 0.0
        )
        
        return {
            **self._cache_stats,
            "hit_ratio": hit_ratio,
            "cache_size": len(self._statement_cache),
            "max_cache_size": self.config.max_statement_cache_size
        }
    
    async def get_pool_status(self) -> Dict[str, Any]:
        """Get detailed pool status."""
        if not self.pool:
            return {"error": "Database manager not initialized"}
        
        return self.pool.get_pool_status()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        if not self.pool:
            return {"status": "unhealthy", "reason": "Not initialized"}
        
        pool_health = self.pool.health_check()
        cache_stats = self.get_cache_stats()
        
        return {
            "pool_health": pool_health,
            "cache_stats": cache_stats,
            "overall_status": pool_health["status"]
        }
    
    async def close(self):
        """Close database manager."""
        if self.pool:
            await self.pool.close()
            self.pool = None
        
        self.logger.info("Database manager closed")


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None
_init_lock = asyncio.Lock()


async def get_database_manager(config: Optional[DatabaseConfig] = None) -> DatabaseManager:
    """Get global database manager instance."""
    global _db_manager
    
    async with _init_lock:
        if _db_manager is None:
            if config is None:
                # Create default config from environment
                config = DatabaseConfig(
                    connection_string=os.getenv("DATABASE_URL", "sqlite:///default.db"),
                    max_connections=int(os.getenv("DB_MAX_CONNECTIONS", "10")),
                    min_connections=int(os.getenv("DB_MIN_CONNECTIONS", "2"))
                )
            
            _db_manager = DatabaseManager(config)
            await _db_manager.initialize()
        
        return _db_manager


async def close_database_manager():
    """Close global database manager."""
    global _db_manager
    
    if _db_manager:
        await _db_manager.close()
        _db_manager = None


# Export main classes and functions
__all__ = [
    'DatabaseManager',
    'ConnectionPool',
    'DatabaseConnection',
    'DatabaseConfig',
    'ConnectionMetrics',
    'ConnectionStatus',
    'get_database_manager',
    'close_database_manager'
]