import logging
import os
import aiohttp
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from dataclasses import dataclass, field
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class Author:
    id: int
    name: str
    slug: str

@dataclass
class Edition:
    id: int
    format: Optional[str]
    isbn_10: Optional[str]
    isbn_13: Optional[str]
    publisher: Optional[str]
    release_date: Optional[str]

@dataclass
class Series:
    id: int
    name: str

@dataclass
class SeriesBook:
    series: Series
    position: Optional[float]

@dataclass
class HardcoverBook:
    id: int
    title: str
    slug: str
    description: Optional[str]
    authors: List[Author]
    editions: List[Edition] = field(default_factory=list)
    series_entries: List[SeriesBook] = field(default_factory=list)
    original_publication_date: Optional[str] = None

    def get_primary_series(self) -> Optional[tuple[str, Any]]:
        if not self.series_entries:
            return None
        # Return the first series found
        first = self.series_entries[0]
        return (first.series.name, first.position)

@dataclass
class ResolutionResult:
    success: bool
    confidence: float  # 0.0 to 1.0
    resolution_method: str  # 'isbn', 'title_author', 'fuzzy', 'manual'
    book: Optional[HardcoverBook] = None
    note: Optional[str] = None
    raw_payload: Optional[Dict[str, Any]] = None

class HardcoverClient:
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://api.hardcover.app/v1/graphql"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        self.session = None
        self._cache = {}  # Simple in-memory cache

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _graphql_query(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a GraphQL query safely handling sessions and rate limits"""
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.headers)

        payload = {"query": query, "variables": variables or {}}
        
        # Exponential backoff parameters
        max_retries = 10 
        base_delay = 5
        
        for attempt in range(max_retries):
            try:
                async with self.session.post(self.base_url, json=payload) as resp:
                    if resp.status == 429:
                        wait_time = base_delay * (2 ** attempt)
                        logger.warning(f"Hardcover API Rate Limit (429). Waiting {wait_time}s before retry (Attempt {attempt+1}/{max_retries})...")
                        await asyncio.sleep(wait_time)
                        continue

                    if resp.status != 200:
                        text = await resp.text()
                        logger.error(f"GraphQL error: HTTP {resp.status} - {text}")
                        raise Exception(f"Hardcover API error: HTTP {resp.status}")
                    
                    data = await resp.json()
                    if "errors" in data:
                        logger.error(f"GraphQL error: {data['errors']}")
                        raise Exception(f"GraphQL error: {data['errors']}")
                        
                    return data.get("data", {})
            
            except Exception as e:
                # Retrying network errors or 429s (handled above logic flow, but catches unexpected disconnects)
                if "Hardcover API error: HTTP 429" in str(e):
                     # Loop handles 429 checks on status, but if exception raised elsewhere:
                     pass
                
                # If we've exhausted retries, verify if we should just fail or keep waiting
                if attempt == max_retries - 1:
                    logger.error(f"Request failed after {max_retries} attempts: {e}")
                    raise
                
                # Check for network-like errors to retry
                if isinstance(e, (aiohttp.ClientError, asyncio.TimeoutError)):
                    wait_time = 5
                    logger.warning(f"Network error: {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                
                # Other exceptions raise immediately
                raise

        raise Exception("Max retries exceeded for Hardcover API")

    # ... Cache helpers ...
    def _get_cache_key(self, prefix: str, **kwargs) -> str:
        parts = [prefix]
        for k, v in sorted(kwargs.items()):
            parts.append(f"{k}:{v}")
        return "|".join(parts)

    def _get_from_cache(self, key: str) -> Optional[HardcoverBook]:
        return self._cache.get(key)

    def _save_to_cache(self, key: str, book: HardcoverBook):
        self._cache[key] = book

    def _deserialize_book(self, data: Dict[str, Any]) -> HardcoverBook:
        # Robust deserialization ignoring missing fields
        authors = []
        # Try 'contributions' first (newer schema)
        if "contributions" in data:
            for c in data["contributions"]:
                if c.get("author"):
                     authors.append(Author(id=0, name=c["author"].get("name", ""), slug=""))
        
        # Fallback to 'authors' if present (legacy or different query)
        if not authors and "authors" in data:
             for a in data["authors"]:
                authors.append(Author(id=0, name=a.get("name", ""), slug=""))

        editions = []
        for e in data.get("editions", []):
            editions.append(Edition(
                id=e.get("id", 0),
                format=e.get("format"),
                isbn_10=e.get("isbn_10"),
                isbn_13=e.get("isbn_13"),
                publisher=e.get("publisher"),
                release_date=e.get("release_date")
            ))

        series_entries = []
        # 'book_series' is the correct field name (formerly series_books)
        series_data = data.get("book_series") or data.get("series_books") or []
        for sb in series_data:
            if sb.get("series"):
                series_entries.append(SeriesBook(
                    series=Series(id=sb["series"].get("id", 0), name=sb["series"].get("name", "")),
                    position=sb.get("position")
                ))

        return HardcoverBook(
            id=data["id"],
            title=data["title"],
            slug=data.get("slug", ""),
            description=data.get("description"),
            authors=authors,
            editions=editions,
            series_entries=series_entries,
            original_publication_date=data.get("release_date")
        )

    async def resolve_book(self, title: str, author: str, isbn: str = None) -> ResolutionResult:
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

        # Stage 4: Google Books Fallback (Get ISBN -> Stage 1)
        logger.info(f"Falling back to Google Books for: {title} by {author}")
        google_isbn = await self._resolve_via_google_books(title, author)
        if google_isbn:
             logger.info(f"Google Books found ISBN: {google_isbn}. Retrying Hardcover...")
             result = await self.resolve_by_isbn(google_isbn)
             if result.success:
                 result.resolution_method = "google_books_isbn"
                 return result

        logger.warning(f"Failed to resolve book: {title} by {author}")
        return ResolutionResult(success=False, confidence=0.0, resolution_method="failed", note="All stages failed")

    async def _resolve_via_google_books(self, title: str, author: str) -> Optional[str]:
        try:
            from backend.integrations.google_books_client import GoogleBooksClient
            api_key = os.getenv("GOOGLE_BOOKS_API_KEY")
            async with GoogleBooksClient(api_key=api_key) as gb:
                metadata = await gb.search_and_extract(title, author)
                if metadata:
                    return metadata.get("isbn_13") or metadata.get("isbn_10")
        except Exception as e:
            logger.warning(f"Google Books fallback failed: {e}")
        return None

    # --- SIMPLIFIED QUERIES ---

    async def resolve_by_isbn(self, isbn: str) -> ResolutionResult:
        isbn_clean = isbn.replace("-", "").replace(" ", "")
        cache_key = self._get_cache_key("isbn", isbn=isbn_clean)
        if self._get_from_cache(cache_key):
            return ResolutionResult(success=True, book=self._get_from_cache(cache_key), confidence=1.0, resolution_method="isbn")

        query = """
        query GetBookByISBN($isbn: String!) {
            books(where: {editions: {isbn_13: {_eq: $isbn}}}, limit: 1) {
                id
                title
                slug
                description
                release_date
                contributions {
                    author {
                        name
                    }
                }
                editions {
                    id
                    isbn_10
                    isbn_13
                }
                series_books {
                    position
                    series {
                        id
                        name
                    }
                }
            }
        }
        """
        # Note: Hardcover doesn't have direct isbn search on root generally, but let's try searching editions or where
        # Actually previous valid query was searching `editions`.
        # Correct query for editions based search:
        query = """
        query GetBookByISBNString($isbn: String!) {
            books(where: {editions: {isbn_13: {_eq: $isbn}}}, limit: 1) {
                id
                title
                slug
                description
                release_date
                contributions {
                    author {
                        name
                    }
                }
                editions {
                    id
                    isbn_10
                    isbn_13
                }
                book_series {
                    position
                    series {
                        id
                        name
                    }
                }
            }
        }
        """
        
        try:
            response = await self._graphql_query(query, {"isbn": isbn_clean})
            books = response.get("books", [])
            if books:
                book = self._deserialize_book(books[0])
                self._save_to_cache(cache_key, book)
                return ResolutionResult(success=True, book=book, confidence=1.0, resolution_method="isbn", raw_payload=books[0])
        except Exception as e:
            logger.error(f"ISBN resolution failed: {e}")
        
        return ResolutionResult(success=False, confidence=0.0, resolution_method="isbn")

    async def resolve_by_title_author(self, title: str, author: str) -> ResolutionResult:
        cache_key = self._get_cache_key("title_author", title=title, author=author)
        if self._get_from_cache(cache_key):
             return ResolutionResult(success=True, book=self._get_from_cache(cache_key), confidence=0.95, resolution_method="title_author")

        query = """
        query ResolveByTitleAuthor($title: String!, $author: String!) {
            books(
                where: {
                    title: {_eq: $title},
                    contributions: {author: {name: {_eq: $author}}}
                }
                limit: 5
            ) {
                id
                title
                slug
                description
                release_date
                contributions {
                    author {
                        name
                    }
                }
                editions {
                    id
                    isbn_10
                    isbn_13
                }
                book_series {
                    position
                    series {
                        id
                        name
                    }
                }
            }
        }
        """
        try:
            response = await self._graphql_query(query, {"title": title, "author": author})
            books = response.get("books", [])
            
            if books:
                # Naive best match
                book = self._deserialize_book(books[0])
                self._save_to_cache(cache_key, book)
                return ResolutionResult(success=True, book=book, confidence=0.9, resolution_method="title_author", raw_payload=books[0])
        except Exception as e:
            logger.error(f"Title+Author resolution failed: {e}")

        return ResolutionResult(success=False, confidence=0.0, resolution_method="title_author")

    async def resolve_by_search(self, query_text: str) -> ResolutionResult:
        cache_key = self._get_cache_key("search", query=query_text)
        if self._get_from_cache(cache_key):
             return ResolutionResult(success=True, book=self._get_from_cache(cache_key), confidence=0.7, resolution_method="fuzzy")

        query = """
        query Search($query: String!) {
            books(
                where: {_or: [
                    {title: {_eq: $query}},
                    {contributions: {author: {name: {_eq: $query}}}}
                ]}
                limit: 5
                order_by: {rating: desc}
            ) {
                id
                title
                slug
                description
                release_date
                contributions {
                    author {
                        name
                    }
                }
                editions {
                    id
                    isbn_10
                    isbn_13
                }
                book_series {
                    position
                    series {
                        id
                        name
                    }
                }
            }
        }
        """
        try:
            response = await self._graphql_query(query, {"query": query_text})
            books = response.get("books", [])
            if books:
                book = self._deserialize_book(books[0])
                self._save_to_cache(cache_key, book)
                return ResolutionResult(success=True, book=book, confidence=0.7, resolution_method="fuzzy", raw_payload=books[0])
        except Exception as e:
            logger.error(f"Fuzzy search failed: {e}")

        return ResolutionResult(success=False, confidence=0.0, resolution_method="fuzzy")

    async def get_me(self) -> Optional[int]:
        query = """
        query {
            me {
                id
            }
        }
        """
        try:
            data = await self._graphql_query(query)
            if data and data.get("me") and len(data["me"]) > 0:
                return data["me"][0]["id"]
        except Exception as e:
            logger.error(f"Failed to get user ID: {e}")
        return None

    async def update_book_status(self, book_id: int, status_slug: str) -> bool:
        user_id = await self.get_me()
        if not user_id:
            logger.error("Cannot update status: User ID not found")
            return False

        status_map = {"read": 3, "want_to_read": 1, "currently_reading": 2}
        status_id = status_map.get(status_slug, 3)

        # 1. Check if user_book exists
        check_query = """
        query CheckUserBook($book_id: Int!, $user_id: Int!) {
            user_books(where: {book_id: {_eq: $book_id}, user_id: {_eq: $user_id}}, limit: 1) {
                id
                status_id
            }
        }
        """
        try:
            data = await self._graphql_query(check_query, {"book_id": book_id, "user_id": user_id})
            existing = data.get("user_books", [])
        except Exception as e:
            logger.error(f"Failed to check existing status: {e}")
            return False

        if existing:
            # Update
            ub_id = existing[0]["id"]
            current_status = existing[0].get("status_id")
            if current_status == status_id:
                return True # Already set

            update_query = """
            mutation UpdateUserBook($id: Int!, $status_id: Int!) {
                update_user_book(id: $id, object: {status_id: $status_id}) {
                    id
                }
            }
            """
            try:
                await self._graphql_query(update_query, {"id": ub_id, "status_id": status_id})
                return True
            except Exception as e:
                logger.error(f"Failed to update existing status: {e}")
                return False
        else:
            # Insert
            insert_query = """
            mutation InsertUserBook($book_id: Int!, $status_id: Int!) {
                insert_user_book(
                    object: {book_id: $book_id, status_id: $status_id}
                ) {
                    id
                }
            }
            """
            try:
                await self._graphql_query(insert_query, {"book_id": book_id, "status_id": status_id})
                return True
            except Exception as e:
                logger.error(f"Failed to insert status: {e}")
                return False

    async def get_user_library(self, user_id: int = None) -> List[Dict]:
        return [] # Not implemented for now, simplifying file
