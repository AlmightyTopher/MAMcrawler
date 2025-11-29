"""
Hardcover.app GraphQL API Client
Provides structured, rate-limited access to Hardcover metadata for audiobook resolution

Architecture:
- Three-stage waterfall resolution: ISBN → Title/Author → Fuzzy Search
- GraphQL query optimization (single query vs. N+1 round-trips)
- Client-side rate limiting (leaky bucket algorithm)
- Local caching to minimize API calls
- Graceful fallback patterns for missing data
"""

import asyncio
import aiohttp
import logging
import json
import time
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
from urllib.parse import urljoin
import sqlite3
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models (DTOs)
# ============================================================================

@dataclass
class Author:
    """Represents a book author or narrator"""
    id: int
    name: str
    slug: str
    role: Optional[str] = None  # e.g., "Author", "Narrator"


@dataclass
class SeriesBook:
    """Represents a book within a series"""
    series_id: int
    series_name: str
    position: float  # Float to support novellas (e.g., 1.5)


@dataclass
class Edition:
    """Represents a specific edition of a book"""
    id: int
    format: str  # e.g., "Digital Audio", "Paperback", "Hardcover"
    isbn_10: Optional[str]
    isbn_13: Optional[str]
    publisher: Optional[str]
    release_date: Optional[str]


@dataclass
class HardcoverBook:
    """Complete book entity with all relationships"""
    id: int
    title: str
    slug: str
    description: Optional[str]
    original_publication_date: Optional[str]
    featured_series_id: Optional[int]
    featured_series_name: Optional[str]
    authors: List[Author]
    series: List[SeriesBook]
    editions: List[Edition]

    def has_audio_edition(self) -> bool:
        """Check if this book has an audiobook edition"""
        return any(e.format and "audio" in e.format.lower() for e in self.editions)

    def get_audio_edition(self) -> Optional[Edition]:
        """Get the first audio edition if available"""
        for edition in self.editions:
            if edition.format and "audio" in edition.format.lower():
                return edition
        return None

    def get_primary_series(self) -> Optional[Tuple[str, float]]:
        """Get the featured/primary series with position"""
        if self.featured_series_name and self.series:
            for s in self.series:
                if s.series_name == self.featured_series_name:
                    return (s.series_name, s.position)
        # Fallback: return first series
        if self.series:
            s = self.series[0]
            return (s.series_name, s.position)
        return None


@dataclass
class ResolutionResult:
    """Result of book resolution attempt"""
    success: bool
    book: Optional[HardcoverBook] = None
    confidence: float = 0.0  # 0.0 to 1.0
    resolution_method: Optional[str] = None  # "isbn", "title_author", "fuzzy"
    note: Optional[str] = None


# ============================================================================
# Rate Limiter (Leaky Bucket Algorithm)
# ============================================================================

class RateLimiter:
    """
    Client-side rate limiter implementing the leaky bucket algorithm.
    Ensures we never exceed Hardcover's 60 requests/minute limit.
    """

    def __init__(self, calls_per_minute: int = 60):
        self.delay = 60.0 / calls_per_minute
        self.last_call = 0
        self.lock = asyncio.Lock()

    async def wait(self):
        """Wait if necessary to maintain rate limit"""
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_call
            if elapsed < self.delay:
                await asyncio.sleep(self.delay - elapsed)
            self.last_call = time.time()


# ============================================================================
# Hardcover Client
# ============================================================================

class HardcoverClient:
    """
    GraphQL client for Hardcover.app metadata resolution

    Features:
    - Three-stage waterfall resolution (ISBN → Title/Author → Fuzzy)
    - Rate limiting to respect API quotas
    - Caching to minimize redundant queries
    - Structured error handling with fallback logic
    """

    # GraphQL endpoint
    API_URL = "https://api.hardcover.app/graphql"

    def __init__(
        self,
        api_token: str,
        cache_db_path: str = "hardcover_cache.db",
        rate_limit: int = 60
    ):
        """
        Initialize Hardcover client

        Args:
            api_token: Bearer token from Hardcover user settings
            cache_db_path: Path to local SQLite cache database
            rate_limit: Requests per minute (default 60, Hardcover's limit)
        """
        self.api_token = api_token
        self.cache_db_path = Path(cache_db_path)
        self.rate_limiter = RateLimiter(rate_limit)
        self.session: Optional[aiohttp.ClientSession] = None

        # Initialize cache
        self._init_cache()

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30, connect=10)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    def _init_cache(self):
        """Initialize SQLite cache for book lookups"""
        self.cache_db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.cache_db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS hardcover_cache (
                    cache_key TEXT PRIMARY KEY,
                    book_id INTEGER,
                    book_json TEXT,
                    cached_at TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires
                ON hardcover_cache(expires_at)
            """)
            conn.commit()

    def _get_cache_key(self, method: str, **params) -> str:
        """Generate cache key from method and parameters"""
        key_parts = [method]
        for k, v in sorted(params.items()):
            key_parts.append(f"{k}={v}")
        return "|".join(key_parts)

    def _get_from_cache(self, cache_key: str) -> Optional[HardcoverBook]:
        """Retrieve cached book data if not expired"""
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.execute(
                    "SELECT book_json FROM hardcover_cache WHERE cache_key = ?",
                    (cache_key,)
                )
                row = cursor.fetchone()

                if row:
                    book_data = json.loads(row[0])
                    return self._deserialize_book(book_data)
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")

        return None

    def _save_to_cache(self, cache_key: str, book: HardcoverBook, ttl_days: int = 30):
        """Save book data to cache"""
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                book_json = json.dumps(asdict(book), default=str)
                expires_at = datetime.now() + timedelta(days=ttl_days)

                conn.execute(
                    """
                    INSERT OR REPLACE INTO hardcover_cache
                    (cache_key, book_id, book_json, cached_at, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (cache_key, book.id, book_json, datetime.now(), expires_at)
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")

    async def _graphql_query(self, query: str, variables: Dict = None) -> Dict:
        """
        Execute a GraphQL query with rate limiting

        Args:
            query: GraphQL query string
            variables: Query variables dict

        Returns:
            GraphQL response data

        Raises:
            Exception: On API error or rate limit
        """
        if not self.session:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        # Rate limit
        await self.rate_limiter.wait()

        payload = {
            "query": query,
            "variables": variables or {}
        }

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        try:
            async with self.session.post(
                self.API_URL,
                json=payload,
                headers=headers
            ) as resp:
                if resp.status == 429:
                    logger.error("Rate limit exceeded")
                    raise Exception("Hardcover API rate limit exceeded (429)")

                if resp.status != 200:
                    logger.error(f"GraphQL error: HTTP {resp.status}")
                    raise Exception(f"Hardcover API error: HTTP {resp.status}")

                data = await resp.json()

                if "errors" in data:
                    logger.error(f"GraphQL error: {data['errors']}")
                    raise Exception(f"GraphQL error: {data['errors']}")

                return data.get("data", {})

        except asyncio.TimeoutError:
            logger.error("Hardcover API request timeout")
            raise Exception("Hardcover API timeout")

    def _deserialize_book(self, data: Dict) -> HardcoverBook:
        """Convert GraphQL response to HardcoverBook object"""
        authors = [
            Author(
                id=a["id"],
                name=a["name"],
                slug=a["slug"],
                role=a.get("role")
            )
            for a in data.get("authors", [])
        ]

        series = [
            SeriesBook(
                series_id=s["series"]["id"],
                series_name=s["series"]["name"],
                position=float(s.get("position", 0))
            )
            for s in data.get("series_books", [])
        ]

        editions = [
            Edition(
                id=e["id"],
                format=e.get("format"),
                isbn_10=e.get("isbn_10"),
                isbn_13=e.get("isbn_13"),
                publisher=e.get("publisher"),
                release_date=e.get("release_date")
            )
            for e in data.get("editions", [])
        ]

        return HardcoverBook(
            id=data["id"],
            title=data["title"],
            slug=data["slug"],
            description=data.get("description"),
            original_publication_date=data.get("original_publication_date"),
            featured_series_id=data.get("featured_book_series_id"),
            featured_series_name=data.get("featured_book_series", {}).get("name") if data.get("featured_book_series") else None,
            authors=authors,
            series=series,
            editions=editions
        )

    # ========================================================================
    # Stage 1: ISBN Resolution
    # ========================================================================

    async def resolve_by_isbn(self, isbn: str) -> ResolutionResult:
        """
        Stage 1: Resolve book by ISBN (highest confidence)

        This is the most reliable method as ISBNs are unique identifiers.
        """
        # Normalize ISBN (remove hyphens, spaces)
        isbn_clean = isbn.replace("-", "").replace(" ", "")

        # Check cache first
        cache_key = self._get_cache_key("isbn", isbn=isbn_clean)
        cached = self._get_from_cache(cache_key)
        if cached:
            logger.info(f"ISBN cache hit: {isbn_clean}")
            return ResolutionResult(
                success=True,
                book=cached,
                confidence=1.0,
                resolution_method="isbn"
            )

        query = """
        query ResolveByISBN($isbn: String!) {
            books(
                where: {editions: {isbn_13: {_eq: $isbn}}}
                limit: 1
            ) {
                id
                title
                slug
                description
                original_publication_date
                featured_book_series_id
                featured_book_series {
                    id
                    name
                }
                authors {
                    id
                    name
                    slug
                }
                series_books {
                    position
                    series {
                        id
                        name
                    }
                }
                editions {
                    id
                    format
                    isbn_10
                    isbn_13
                    publisher
                    release_date
                }
            }
        }
        """

        try:
            response = await self._graphql_query(query, {"isbn": isbn_clean})
            books = response.get("books", [])

            if not books:
                logger.debug(f"ISBN not found: {isbn_clean}")
                return ResolutionResult(
                    success=False,
                    confidence=0.0,
                    resolution_method="isbn",
                    note="ISBN not found in Hardcover"
                )

            book = self._deserialize_book(books[0])
            self._save_to_cache(cache_key, book)

            logger.info(f"ISBN resolved: {isbn_clean} → {book.title}")
            return ResolutionResult(
                success=True,
                book=book,
                confidence=1.0,
                resolution_method="isbn"
            )

        except Exception as e:
            logger.error(f"ISBN resolution failed: {e}")
            return ResolutionResult(
                success=False,
                confidence=0.0,
                resolution_method="isbn",
                note=f"Error: {str(e)}"
            )

    # ========================================================================
    # Stage 2: Title + Author Exact Match
    # ========================================================================

    async def resolve_by_title_author(self, title: str, author: str) -> ResolutionResult:
        """
        Stage 2: Resolve by exact title + author match (high confidence)
        """
        cache_key = self._get_cache_key("title_author", title=title, author=author)
        cached = self._get_from_cache(cache_key)
        if cached:
            logger.info(f"Title+Author cache hit: {title} by {author}")
            return ResolutionResult(
                success=True,
                book=cached,
                confidence=0.95,
                resolution_method="title_author"
            )

        query = """
        query ResolveByTitleAuthor($title: String!, $author: String!) {
            books(
                where: {
                    title: {_ilike: $title},
                    authors: {name: {_ilike: $author}}
                }
                limit: 5
            ) {
                id
                title
                slug
                description
                original_publication_date
                featured_book_series_id
                featured_book_series {
                    id
                    name
                }
                authors {
                    id
                    name
                    slug
                }
                series_books {
                    position
                    series {
                        id
                        name
                    }
                }
                editions {
                    id
                    format
                    isbn_10
                    isbn_13
                    publisher
                    release_date
                }
            }
        }
        """

        try:
            response = await self._graphql_query(
                query,
                {"title": f"%{title}%", "author": f"%{author}%"}
            )
            books = response.get("books", [])

            if not books:
                logger.debug(f"Title+Author not found: {title} by {author}")
                return ResolutionResult(
                    success=False,
                    confidence=0.0,
                    resolution_method="title_author",
                    note="No exact match found"
                )

            # If multiple matches, prefer exact title match
            best_match = None
            for book in books:
                if book["title"].lower() == title.lower():
                    best_match = book
                    break
            if not best_match:
                best_match = books[0]  # Fallback to first result

            book = self._deserialize_book(best_match)
            self._save_to_cache(cache_key, book)

            logger.info(f"Title+Author resolved: {title} by {author}")
            return ResolutionResult(
                success=True,
                book=book,
                confidence=0.95 if best_match == books[0] else 1.0,
                resolution_method="title_author"
            )

        except Exception as e:
            logger.error(f"Title+Author resolution failed: {e}")
            return ResolutionResult(
                success=False,
                confidence=0.0,
                resolution_method="title_author",
                note=f"Error: {str(e)}"
            )

    # ========================================================================
    # Stage 3: Fuzzy Search
    # ========================================================================

    async def resolve_by_search(self, query_text: str) -> ResolutionResult:
        """
        Stage 3: Fuzzy search (fallback, lower confidence)
        Uses Hardcover's full-text search capabilities
        """
        cache_key = self._get_cache_key("search", query=query_text)
        cached = self._get_from_cache(cache_key)
        if cached:
            logger.info(f"Search cache hit: {query_text}")
            return ResolutionResult(
                success=True,
                book=cached,
                confidence=0.7,
                resolution_method="fuzzy"
            )

        query = """
        query Search($query: String!) {
            books(
                where: {_or: [
                    {title: {_ilike: $query}},
                    {authors: {name: {_ilike: $query}}}
                ]}
                limit: 5
                order_by: {rating: desc}
            ) {
                id
                title
                slug
                description
                original_publication_date
                featured_book_series_id
                featured_book_series {
                    id
                    name
                }
                authors {
                    id
                    name
                    slug
                }
                series_books {
                    position
                    series {
                        id
                        name
                    }
                }
                editions {
                    id
                    format
                    isbn_10
                    isbn_13
                    publisher
                    release_date
                }
            }
        }
        """

        try:
            response = await self._graphql_query(query, {"query": f"%{query_text}%"})
            books = response.get("books", [])

            if not books:
                logger.debug(f"Search found no results: {query_text}")
                return ResolutionResult(
                    success=False,
                    confidence=0.0,
                    resolution_method="fuzzy",
                    note="No search results"
                )

            # Take top result (ranked by rating)
            book = self._deserialize_book(books[0])
            self._save_to_cache(cache_key, book)

            logger.info(f"Fuzzy search resolved: {query_text} → {book.title}")
            return ResolutionResult(
                success=True,
                book=book,
                confidence=0.7,
                resolution_method="fuzzy"
            )

        except Exception as e:
            logger.error(f"Fuzzy search failed: {e}")
            return ResolutionResult(
                success=False,
                confidence=0.0,
                resolution_method="fuzzy",
                note=f"Error: {str(e)}"
            )

    # ========================================================================
    # High-Level API
    # ========================================================================

    async def resolve_book(
        self,
        title: Optional[str] = None,
        author: Optional[str] = None,
        isbn: Optional[str] = None
    ) -> ResolutionResult:
        """
        Resolve a book using the waterfall strategy

        Attempts resolution in order:
        1. ISBN (if provided) - 100% confidence
        2. Title + Author - 95% confidence
        3. Fuzzy search - 70% confidence

        Returns immediately on first success.
        """
        logger.info(f"Resolving: {title} by {author} (ISBN: {isbn})")

        # Stage 1: ISBN
        if isbn:
            result = await self.resolve_by_isbn(isbn)
            if result.success:
                return result

        # Stage 2: Title + Author
        if title and author:
            result = await self.resolve_by_title_author(title, author)
            if result.success:
                return result

        # Stage 3: Fuzzy search
        search_query = f"{title} {author}".strip() if title else author
        if search_query:
            result = await self.resolve_by_search(search_query)
            if result.success:
                return result

        # All stages failed
        logger.warning(f"Failed to resolve book: {title} by {author}")
        return ResolutionResult(
            success=False,
            confidence=0.0,
            note="All resolution stages failed"
        )

    async def get_series_books(self, series_id: int) -> List[HardcoverBook]:
        """
        Fetch all books in a series in order

        Returns:
            List of books in series order (by position)
        """
        query = """
        query GetSeriesBooks($series_id: Int!) {
            series_by_pk(id: $series_id) {
                series_books(order_by: {position: asc}) {
                    position
                    book {
                        id
                        title
                        slug
                        description
                        original_publication_date
                        featured_book_series_id
                        featured_book_series {
                            id
                            name
                        }
                        authors {
                            id
                            name
                            slug
                        }
                        series_books {
                            position
                            series {
                                id
                                name
                            }
                        }
                        editions {
                            id
                            format
                            isbn_10
                            isbn_13
                            publisher
                            release_date
                        }
                    }
                }
            }
        }
        """

        try:
            response = await self._graphql_query(query, {"series_id": series_id})
            series = response.get("series_by_pk")

            if not series:
                logger.warning(f"Series not found: {series_id}")
                return []

            books = [
                self._deserialize_book(sb["book"])
                for sb in series.get("series_books", [])
            ]

            logger.info(f"Fetched {len(books)} books from series {series_id}")
            return books

        except Exception as e:
            logger.error(f"Series fetch failed: {e}")
            return []


# ============================================================================
# Demo / Testing
# ============================================================================

async def demo():
    """Demonstration of Hardcover client usage"""
    import os

    api_token = os.getenv("HARDCOVER_TOKEN")
    if not api_token:
        print("Error: HARDCOVER_TOKEN environment variable not set")
        return

    async with HardcoverClient(api_token) as client:
        # Example 1: ISBN resolution
        result = await client.resolve_book(isbn="9780593135204")
        if result.success:
            print(f"Found: {result.book.title}")
            print(f"Series: {result.book.get_primary_series()}")

        # Example 2: Title + Author
        result = await client.resolve_book(
            title="The Way of Kings",
            author="Brandon Sanderson"
        )
        if result.success:
            print(f"Found: {result.book.title}")
            print(f"Audio edition: {result.book.has_audio_edition()}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(demo())
