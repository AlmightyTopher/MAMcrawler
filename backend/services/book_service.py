"""
Book Service - Business logic for book operations
Handles CRUD operations, metadata tracking, and book management
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy import or_, func
from sqlalchemy.orm import Session
import logging

from backend.models.book import Book

logger = logging.getLogger(__name__)


class BookService:
    """
    Service layer for book operations

    Provides methods for creating, reading, updating, and deleting books
    with metadata completeness tracking and source attribution
    """

    @staticmethod
    def create_book(
        db: Session,
        title: str,
        author: Optional[str] = None,
        abs_id: Optional[str] = None,
        metadata_dict: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new book record

        Args:
            db: Database session
            title: Book title (required)
            author: Author name
            abs_id: Audiobookshelf ID (unique)
            metadata_dict: Dictionary of additional metadata fields
                {
                    'series': str,
                    'series_number': str,
                    'isbn': str,
                    'asin': str,
                    'publisher': str,
                    'published_year': int,
                    'duration_minutes': int,
                    'description': str,
                    'import_source': str,
                    'metadata_source': dict
                }

        Returns:
            Dict with:
                - success: bool
                - data: Book object if successful
                - error: str if failed
                - book_id: int if successful
        """
        try:
            # Check if book with abs_id already exists
            if abs_id:
                existing = db.query(Book).filter(Book.abs_id == abs_id).first()
                if existing:
                    logger.warning(f"Book with abs_id {abs_id} already exists: {existing.title}")
                    return {
                        "success": False,
                        "error": f"Book with abs_id {abs_id} already exists",
                        "data": existing,
                        "book_id": existing.id
                    }

            # Create new book
            book = Book(
                title=title,
                author=author,
                abs_id=abs_id
            )

            # Add optional metadata
            if metadata_dict:
                for key, value in metadata_dict.items():
                    if hasattr(book, key) and value is not None:
                        setattr(book, key, value)

            # Calculate metadata completeness
            book.metadata_completeness_percent = BookService._calculate_completeness(book)
            book.last_metadata_update = datetime.now()

            db.add(book)
            db.commit()
            db.refresh(book)

            logger.info(f"Created book: {book.title} (ID: {book.id})")

            return {
                "success": True,
                "data": book,
                "book_id": book.id,
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error creating book '{title}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None,
                "book_id": None
            }

    @staticmethod
    def get_book(db: Session, book_id: int) -> Dict[str, Any]:
        """
        Get book by ID

        Args:
            db: Database session
            book_id: Book ID

        Returns:
            Dict with success, data (Book or None), error
        """
        try:
            book = db.query(Book).filter(Book.id == book_id).first()

            if not book:
                return {
                    "success": False,
                    "error": f"Book with ID {book_id} not found",
                    "data": None
                }

            return {
                "success": True,
                "data": book,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting book {book_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    @staticmethod
    def get_book_by_abs_id(db: Session, abs_id: str) -> Dict[str, Any]:
        """
        Get book by Audiobookshelf ID

        Args:
            db: Database session
            abs_id: Audiobookshelf ID

        Returns:
            Dict with success, data (Book or None), error
        """
        try:
            book = db.query(Book).filter(Book.abs_id == abs_id).first()

            if not book:
                return {
                    "success": False,
                    "error": f"Book with abs_id {abs_id} not found",
                    "data": None
                }

            return {
                "success": True,
                "data": book,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting book by abs_id {abs_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    @staticmethod
    def search_books(
        db: Session,
        query: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search books by title or author

        Args:
            db: Database session
            query: Search query string
            limit: Maximum results to return

        Returns:
            Dict with success, data (list of Books), count, error
        """
        try:
            search_pattern = f"%{query}%"

            books = db.query(Book).filter(
                or_(
                    Book.title.ilike(search_pattern),
                    Book.author.ilike(search_pattern)
                )
            ).filter(
                Book.status == "active"
            ).limit(limit).all()

            return {
                "success": True,
                "data": books,
                "count": len(books),
                "error": None
            }

        except Exception as e:
            logger.error(f"Error searching books with query '{query}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0
            }

    @staticmethod
    def get_all_books(
        db: Session,
        status: str = "active",
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get paginated list of books

        Args:
            db: Database session
            status: Filter by status (active, duplicate, archived)
            limit: Maximum results per page
            offset: Number of records to skip

        Returns:
            Dict with success, data (list of Books), total, page_info, error
        """
        try:
            query = db.query(Book)

            if status:
                query = query.filter(Book.status == status)

            # Get total count
            total = query.count()

            # Get paginated results
            books = query.order_by(Book.date_added.desc()).limit(limit).offset(offset).all()

            return {
                "success": True,
                "data": books,
                "total": total,
                "page_info": {
                    "limit": limit,
                    "offset": offset,
                    "has_more": (offset + limit) < total
                },
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting all books: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "total": 0,
                "page_info": None
            }

    @staticmethod
    def update_book(
        db: Session,
        book_id: int,
        updates_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update book fields

        Args:
            db: Database session
            book_id: Book ID
            updates_dict: Dictionary of fields to update
                {
                    'title': str,
                    'author': str,
                    'series': str,
                    'series_number': str,
                    'isbn': str,
                    'asin': str,
                    'publisher': str,
                    'published_year': int,
                    'duration_minutes': int,
                    'description': str,
                    'status': str
                }

        Returns:
            Dict with success, data (updated Book), changes_made, error
        """
        try:
            book = db.query(Book).filter(Book.id == book_id).first()

            if not book:
                return {
                    "success": False,
                    "error": f"Book with ID {book_id} not found",
                    "data": None,
                    "changes_made": {}
                }

            changes_made = {}

            # Update fields
            for key, value in updates_dict.items():
                if hasattr(book, key):
                    old_value = getattr(book, key)
                    if old_value != value:
                        setattr(book, key, value)
                        changes_made[key] = {
                            "old": old_value,
                            "new": value
                        }

            # Recalculate metadata completeness if any metadata changed
            if changes_made:
                book.metadata_completeness_percent = BookService._calculate_completeness(book)
                book.last_metadata_update = datetime.now()
                book.date_updated = datetime.now()

            db.commit()
            db.refresh(book)

            logger.info(f"Updated book {book_id}: {len(changes_made)} fields changed")

            return {
                "success": True,
                "data": book,
                "changes_made": changes_made,
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating book {book_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None,
                "changes_made": {}
            }

    @staticmethod
    def update_metadata_source(
        db: Session,
        book_id: int,
        field_name: str,
        source: str
    ) -> Dict[str, Any]:
        """
        Track which source provided a specific metadata field

        Args:
            db: Database session
            book_id: Book ID
            field_name: Field name (e.g., 'title', 'author')
            source: Source name (e.g., 'GoogleBooks', 'Goodreads', 'Manual')

        Returns:
            Dict with success, data (updated Book), error
        """
        try:
            book = db.query(Book).filter(Book.id == book_id).first()

            if not book:
                return {
                    "success": False,
                    "error": f"Book with ID {book_id} not found",
                    "data": None
                }

            # Update metadata_source JSON field
            if not book.metadata_source:
                book.metadata_source = {}

            book.metadata_source[field_name] = source
            book.last_metadata_update = datetime.now()

            # Flag modified for SQLAlchemy to detect JSON change
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(book, "metadata_source")

            db.commit()
            db.refresh(book)

            logger.info(f"Updated metadata source for book {book_id}, field '{field_name}': {source}")

            return {
                "success": True,
                "data": book,
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating metadata source for book {book_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    @staticmethod
    def delete_book(db: Session, book_id: int) -> Dict[str, Any]:
        """
        Mark book as deleted (soft delete)

        Args:
            db: Database session
            book_id: Book ID

        Returns:
            Dict with success, message, error
        """
        try:
            book = db.query(Book).filter(Book.id == book_id).first()

            if not book:
                return {
                    "success": False,
                    "error": f"Book with ID {book_id} not found",
                    "message": None
                }

            book.status = "archived"
            book.date_updated = datetime.now()

            db.commit()

            logger.info(f"Deleted book {book_id}: {book.title}")

            return {
                "success": True,
                "message": f"Book '{book.title}' marked as archived",
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting book {book_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": None
            }

    @staticmethod
    def get_books_by_series(db: Session, series_name: str) -> Dict[str, Any]:
        """
        Get all books in a series

        Args:
            db: Database session
            series_name: Series name

        Returns:
            Dict with success, data (list of Books sorted by series_number), count, error
        """
        try:
            books = db.query(Book).filter(
                Book.series == series_name,
                Book.status == "active"
            ).order_by(Book.series_number).all()

            return {
                "success": True,
                "data": books,
                "count": len(books),
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting books by series '{series_name}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0
            }

    @staticmethod
    def get_books_needing_metadata_refresh(
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get books with stale metadata (not updated in X days)

        Args:
            db: Database session
            days: Number of days to consider metadata stale

        Returns:
            Dict with success, data (list of Books), count, error
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            books = db.query(Book).filter(
                or_(
                    Book.last_metadata_update < cutoff_date,
                    Book.last_metadata_update.is_(None)
                ),
                Book.status == "active"
            ).order_by(Book.metadata_completeness_percent.asc()).all()

            return {
                "success": True,
                "data": books,
                "count": len(books),
                "cutoff_date": cutoff_date.isoformat(),
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting books needing metadata refresh: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0,
                "cutoff_date": None
            }

    @staticmethod
    def _calculate_completeness(book: Book) -> int:
        """
        Calculate metadata completeness percentage

        Args:
            book: Book object

        Returns:
            Completeness percentage (0-100)
        """
        fields_to_check = [
            'title',
            'author',
            'series',
            'series_number',
            'isbn',
            'asin',
            'publisher',
            'published_year',
            'duration_minutes',
            'description'
        ]

        filled_fields = 0
        total_fields = len(fields_to_check)

        for field in fields_to_check:
            value = getattr(book, field, None)
            if value is not None and str(value).strip():
                filled_fields += 1

        return int((filled_fields / total_fields) * 100)
