"""
Author Service - Business logic for author operations
Handles author tracking, completion status, and audiobook discovery
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
import logging

from backend.models.author import Author
from backend.models.book import Book

logger = logging.getLogger(__name__)


class AuthorService:
    """
    Service layer for author operations

    Provides methods for managing authors, tracking audiobook completeness,
    and external platform integration
    """

    @staticmethod
    def create_author(
        db: Session,
        name: str,
        goodreads_id: Optional[str] = None,
        google_books_id: Optional[str] = None,
        mam_author_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new author record

        Args:
            db: Database session
            name: Author name (unique)
            goodreads_id: Goodreads author ID
            google_books_id: Google Books author ID
            mam_author_id: MyAnonamouse author ID

        Returns:
            Dict with:
                - success: bool
                - data: Author object if successful
                - error: str if failed
                - author_id: int if successful
        """
        try:
            # Check if author already exists
            existing = db.query(Author).filter(Author.name == name).first()
            if existing:
                logger.warning(f"Author '{name}' already exists (ID: {existing.id})")
                return {
                    "success": False,
                    "error": f"Author '{name}' already exists",
                    "data": existing,
                    "author_id": existing.id
                }

            # Create new author
            author = Author(
                name=name,
                goodreads_id=goodreads_id,
                google_books_id=google_books_id,
                mam_author_id=mam_author_id
            )

            db.add(author)
            db.commit()
            db.refresh(author)

            # Calculate initial completion status
            AuthorService.update_completion_status(db, author.id)

            logger.info(f"Created author: {author.name} (ID: {author.id})")

            return {
                "success": True,
                "data": author,
                "author_id": author.id,
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error creating author '{name}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None,
                "author_id": None
            }

    @staticmethod
    def get_author(db: Session, author_id: int) -> Dict[str, Any]:
        """
        Get author by ID

        Args:
            db: Database session
            author_id: Author ID

        Returns:
            Dict with success, data (Author or None), error
        """
        try:
            author = db.query(Author).filter(Author.id == author_id).first()

            if not author:
                return {
                    "success": False,
                    "error": f"Author with ID {author_id} not found",
                    "data": None
                }

            return {
                "success": True,
                "data": author,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting author {author_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    @staticmethod
    def get_author_by_name(db: Session, name: str) -> Dict[str, Any]:
        """
        Get author by name (unique constraint)

        Args:
            db: Database session
            name: Author name

        Returns:
            Dict with success, data (Author or None), error
        """
        try:
            author = db.query(Author).filter(Author.name == name).first()

            if not author:
                return {
                    "success": False,
                    "error": f"Author '{name}' not found",
                    "data": None
                }

            return {
                "success": True,
                "data": author,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting author by name '{name}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    @staticmethod
    def search_authors(db: Session, query: str) -> Dict[str, Any]:
        """
        Search authors by name

        Args:
            db: Database session
            query: Search query string

        Returns:
            Dict with success, data (list of Authors), count, error
        """
        try:
            search_pattern = f"%{query}%"

            authors = db.query(Author).filter(
                Author.name.ilike(search_pattern)
            ).order_by(Author.name).all()

            return {
                "success": True,
                "data": authors,
                "count": len(authors),
                "error": None
            }

        except Exception as e:
            logger.error(f"Error searching authors with query '{query}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0
            }

    @staticmethod
    def get_all_authors(
        db: Session,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get paginated list of all authors

        Args:
            db: Database session
            limit: Maximum results per page
            offset: Number of records to skip

        Returns:
            Dict with success, data (list of Authors), total, page_info, error
        """
        try:
            # Get total count
            total = db.query(Author).count()

            # Get paginated results
            authors = db.query(Author).order_by(
                Author.audiobooks_owned.desc(),
                Author.name
            ).limit(limit).offset(offset).all()

            return {
                "success": True,
                "data": authors,
                "total": total,
                "page_info": {
                    "limit": limit,
                    "offset": offset,
                    "has_more": (offset + limit) < total
                },
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting all authors: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "total": 0,
                "page_info": None
            }

    @staticmethod
    def update_author(
        db: Session,
        author_id: int,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update author fields

        Args:
            db: Database session
            author_id: Author ID
            updates: Dictionary of fields to update
                {
                    'name': str,
                    'goodreads_id': str,
                    'google_books_id': str,
                    'mam_author_id': str,
                    'total_audiobooks_external': int
                }

        Returns:
            Dict with success, data (updated Author), changes_made, error
        """
        try:
            author = db.query(Author).filter(Author.id == author_id).first()

            if not author:
                return {
                    "success": False,
                    "error": f"Author with ID {author_id} not found",
                    "data": None,
                    "changes_made": {}
                }

            changes_made = {}

            # Update fields
            for key, value in updates.items():
                if hasattr(author, key):
                    old_value = getattr(author, key)
                    if old_value != value:
                        setattr(author, key, value)
                        changes_made[key] = {
                            "old": old_value,
                            "new": value
                        }

            # Update timestamp if changes were made
            if changes_made:
                author.date_updated = datetime.now()

            db.commit()
            db.refresh(author)

            # Recalculate completion if total_audiobooks_external changed
            if 'total_audiobooks_external' in changes_made:
                AuthorService.update_completion_status(db, author_id)

            logger.info(f"Updated author {author_id}: {len(changes_made)} fields changed")

            return {
                "success": True,
                "data": author,
                "changes_made": changes_made,
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating author {author_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None,
                "changes_made": {}
            }

    @staticmethod
    def get_author_books(db: Session, author_id: int) -> Dict[str, Any]:
        """
        Get all books by an author

        Args:
            db: Database session
            author_id: Author ID

        Returns:
            Dict with success, data (list of Books), count, error
        """
        try:
            author = db.query(Author).filter(Author.id == author_id).first()

            if not author:
                return {
                    "success": False,
                    "error": f"Author with ID {author_id} not found",
                    "data": [],
                    "count": 0
                }

            books = db.query(Book).filter(
                Book.author == author.name,
                Book.status == "active"
            ).order_by(Book.title).all()

            return {
                "success": True,
                "data": books,
                "count": len(books),
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting books for author {author_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0
            }

    @staticmethod
    def update_completion_status(db: Session, author_id: int) -> Dict[str, Any]:
        """
        Recalculate author completion status

        Counts audiobooks owned by the author and calculates completion

        Args:
            db: Database session
            author_id: Author ID

        Returns:
            Dict with success, data (updated Author), stats, error
        """
        try:
            author = db.query(Author).filter(Author.id == author_id).first()

            if not author:
                return {
                    "success": False,
                    "error": f"Author with ID {author_id} not found",
                    "data": None,
                    "stats": None
                }

            # Count audiobooks by author from books table
            audiobooks_owned = db.query(Book).filter(
                Book.author == author.name,
                Book.status == "active"
            ).count()

            author.audiobooks_owned = audiobooks_owned

            # Calculate missing
            if author.total_audiobooks_external:
                author.audiobooks_missing = max(
                    0,
                    author.total_audiobooks_external - audiobooks_owned
                )
                completion_percentage = int(
                    (audiobooks_owned / author.total_audiobooks_external) * 100
                )
            else:
                author.audiobooks_missing = 0
                completion_percentage = 0

            # Update status
            if completion_percentage == 100:
                author.completion_status = "complete"
            elif completion_percentage >= 50:
                author.completion_status = "partial"
            else:
                author.completion_status = "incomplete"

            author.last_completion_check = datetime.now()

            db.commit()
            db.refresh(author)

            stats = {
                "audiobooks_owned": author.audiobooks_owned,
                "audiobooks_missing": author.audiobooks_missing,
                "total_audiobooks_external": author.total_audiobooks_external,
                "completion_percentage": completion_percentage,
                "completion_status": author.completion_status
            }

            logger.info(f"Updated completion for author {author_id}: {stats}")

            return {
                "success": True,
                "data": author,
                "stats": stats,
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating completion status for author {author_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None,
                "stats": None
            }

    @staticmethod
    def get_favorite_authors(db: Session) -> Dict[str, Any]:
        """
        Get authors with 2+ audiobooks owned (favorite authors)

        Returns:
            Dict with success, data (list of Authors), count, error
        """
        try:
            authors = db.query(Author).filter(
                Author.audiobooks_owned >= 2
            ).order_by(Author.audiobooks_owned.desc()).all()

            return {
                "success": True,
                "data": authors,
                "count": len(authors),
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting favorite authors: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0
            }

    @staticmethod
    def get_author_completion_summary(db: Session) -> Dict[str, Any]:
        """
        Get summary statistics for all authors

        Returns:
            Dict with success, stats, error
        """
        try:
            # Count authors by status
            complete = db.query(Author).filter(Author.completion_status == "complete").count()
            partial = db.query(Author).filter(Author.completion_status == "partial").count()
            incomplete = db.query(Author).filter(Author.completion_status == "incomplete").count()

            # Total authors
            total_authors = db.query(Author).count()

            # Authors with 2+ books (favorites)
            favorite_authors = db.query(Author).filter(Author.audiobooks_owned >= 2).count()

            # Total audiobooks owned across all authors
            total_audiobooks_owned = db.query(func.sum(Author.audiobooks_owned)).scalar() or 0

            # Total audiobooks missing across all authors
            total_audiobooks_missing = db.query(func.sum(Author.audiobooks_missing)).scalar() or 0

            stats = {
                "total_authors": total_authors,
                "complete": complete,
                "partial": partial,
                "incomplete": incomplete,
                "favorite_authors": favorite_authors,
                "total_audiobooks_owned": total_audiobooks_owned,
                "total_audiobooks_missing": total_audiobooks_missing
            }

            return {
                "success": True,
                "stats": stats,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting author completion summary: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "stats": None
            }
