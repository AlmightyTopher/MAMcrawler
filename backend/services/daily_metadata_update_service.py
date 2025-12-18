"""
Daily Google Books Metadata Update Service

Updates book metadata from Google Books API on a daily schedule.
Uses intelligent priority queue to efficiently use API quota:
1. Books with null last_metadata_updated first
2. Then books sorted by oldest last_metadata_updated timestamp
3. Respects daily API quota limit

No history tracking - only current metadata + timestamp stored.
"""

import logging
import json
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, asc, func

from backend.models.book import Book
from backend.integrations.google_books_client import GoogleBooksClient, GoogleBooksRateLimitError
from backend.services.evidence_service import EvidenceService

logger = logging.getLogger(__name__)


class DailyMetadataUpdateService:
    """
    Service for daily metadata updates via Google Books API.

    Workflow:
    1. Query books needing updates (null first, then oldest)
    2. Update up to DAILY_MAX books per run
    3. Set last_metadata_updated timestamp
    4. Store no history, only current metadata

    Output: Updated metadata records with timestamps only
    """

    def __init__(
        self,
        google_books_client: GoogleBooksClient,
        db: Session,
        daily_max: int = 100
    ):
        """
        Initialize service.

        Args:
            google_books_client: Authenticated GoogleBooksClient instance
            db: SQLAlchemy database session
            daily_max: Maximum books to update per daily run (default: 100)
        """
        self.google_books_client = google_books_client
        self.db = db
        self.daily_max = daily_max

        logger.info(f"Initialized DailyMetadataUpdateService (daily_max={daily_max})")

    async def run_daily_update(self) -> Dict[str, Any]:
        """
        Run the daily metadata update cycle.

        Priority order:
        1. Books with last_metadata_updated = null (new books)
        2. Books sorted by oldest last_metadata_updated (stale books)
        3. Respect daily_max quota

        Returns:
            {
                'success': bool,
                'books_processed': int,
                'books_updated': int,
                'updated_records': [
                    {
                        'book_id': int,
                        'title': str,
                        'fields_updated': List[str],
                        'updated_at': ISO8601 timestamp,
                        'metadata': {...}  # Only updated fields
                    },
                    ...
                ],
                'errors': List[str],
                'rate_limit_remaining': int
            }
        """
        logger.info(f"Starting daily metadata update (max {self.daily_max} books)...")

        try:
            # Get books to update in priority order
            books_to_update = self._get_priority_queue()

            logger.info(f"Found {len(books_to_update)} books needing updates")

            if not books_to_update:
                logger.info("No books need metadata updates")
                return {
                    'success': True,
                    'books_processed': 0,
                    'books_updated': 0,
                    'updated_records': [],
                    'errors': [],
                    'rate_limit_remaining': self.daily_max
                }

            # Process books
            updated_records = []
            errors = []
            books_processed = 0

            for book in books_to_update:
                if books_processed >= self.daily_max:
                    logger.info(f"Reached daily limit ({self.daily_max} books)")
                    break

                try:
                    result = await self._update_book_metadata(book)

                    if result:
                        updated_records.append(result)
                        logger.info(
                            f"✓ Updated {result['title']} "
                            f"({len(result['fields_updated'])} fields)"
                        )

                    books_processed += 1

                except GoogleBooksRateLimitError as e:
                    error_msg = f"Rate limit exceeded at book {books_processed + 1}: {str(e)}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                    break  # Stop processing on rate limit

                except Exception as e:
                    error_msg = f"Error updating {book.title} (ID: {book.id}): {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    books_processed += 1
                    continue

            return {
                'success': len(errors) == 0 or len(updated_records) > 0,
                'books_processed': books_processed,
                'books_updated': len(updated_records),
                'updated_records': updated_records,
                'errors': errors,
                'rate_limit_remaining': self.daily_max - books_processed
            }

        except Exception as e:
            error_msg = f"Daily update failed: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'books_processed': 0,
                'books_updated': 0,
                'updated_records': [],
                'errors': [error_msg],
                'rate_limit_remaining': 0
            }

    def _get_priority_queue(self) -> List[Book]:
        """
        Get books ordered by update priority.

        Priority:
        1. Books with last_metadata_updated = null (new books) FIRST
        2. Books sorted by oldest last_metadata_updated (stale books) SECOND
        3. Limit to daily_max

        Returns:
            List of Book objects in priority order
        """
        try:
            # Query: null first, then oldest timestamps
            books = self.db.query(Book).filter(
                Book.status == 'active'  # Only active books
            ).order_by(
                # This uses SQL COALESCE to sort nulls first
                # In SQLAlchemy, we need to handle this carefully
                asc(func.coalesce(Book.last_metadata_update, '1970-01-01'))
            ).limit(self.daily_max).all()

            logger.debug(
                f"Priority queue: {len(books)} books "
                f"({sum(1 for b in books if b.last_metadata_update is None)} new, "
                f"{sum(1 for b in books if b.last_metadata_update is not None)} stale)"
            )

            return books

        except Exception as e:
            logger.error(f"Error building priority queue: {e}")
            return []

    async def _update_book_metadata(self, book: Book) -> Optional[Dict[str, Any]]:
        """
        Update metadata for a single book.

        Args:
            book: Book object to update

        Returns:
            {
                'book_id': int,
                'title': str,
                'fields_updated': List[str],  # Only fields that changed
                'updated_at': ISO8601 timestamp,
                'metadata': {...}  # Only updated fields with values
            }
            or None if no updates
        """
        logger.debug(f"Updating metadata for: {book.title}")

        try:
            # Step 1: Search Google Books
            results = await self.google_books_client.search(
                title=book.title,
                author=book.author if book.author else None,
                max_results=5
            )

            if not results:
                logger.warning(f"No Google Books results for {book.title}")
                # Still update timestamp so we don't retry immediately
                book.last_metadata_update = datetime.now()
                self.db.commit()
                return None

            # Step 2: Extract metadata from top result
            result = results[0]
            extracted = self.google_books_client.extract_metadata(result)

            # Capture Evidence (Shadow Mode)
            try:
                EvidenceService.ingest_evidence(
                    self.db,
                    source_name="GoogleBooks",
                    book_id=book.id,
                    raw_payload=result,
                    normalized_data=extracted,
                    resolution_method="search"
                )
            except Exception as e:
                logger.error(f"Failed to capture evidence for book {book.id}: {e}")

            # Step 3: Identify what to update (gaps only, never overwrite)
            fields_updated = []
            metadata_to_update = {}

            # Title - never overwrite existing
            if extracted.get('title') and not book.title:
                book.title = extracted['title']
                fields_updated.append('title')
                metadata_to_update['title'] = extracted['title']

            # Authors - never overwrite existing
            if extracted.get('authors') and not book.author:
                authors_str = ', '.join(extracted['authors'])
                book.author = authors_str
                fields_updated.append('author')
                metadata_to_update['author'] = authors_str

            # Description - never overwrite existing
            if extracted.get('description') and not book.description:
                book.description = extracted['description']
                fields_updated.append('description')
                metadata_to_update['description'] = extracted['description']

            # Publisher - never overwrite existing
            if extracted.get('publisher') and not book.publisher:
                book.publisher = extracted['publisher']
                fields_updated.append('publisher')
                metadata_to_update['publisher'] = extracted['publisher']

            # Published year - extract from date if needed
            if extracted.get('published_date') and not book.published_year:
                try:
                    year = int(extracted['published_date'].split('-')[0])
                    book.published_year = year
                    fields_updated.append('published_year')
                    metadata_to_update['published_year'] = year
                except (ValueError, IndexError):
                    logger.debug(f"Could not parse year from {extracted.get('published_date')}")

            # ISBN - never overwrite existing
            isbn_found = False
            if extracted.get('isbn_13') and not book.isbn:
                book.isbn = extracted['isbn_13']
                fields_updated.append('isbn')
                metadata_to_update['isbn'] = extracted['isbn_13']
                isbn_found = True
            elif extracted.get('isbn_10') and not book.isbn:
                book.isbn = extracted['isbn_10']
                fields_updated.append('isbn')
                metadata_to_update['isbn'] = extracted['isbn_10']
                isbn_found = True

            # Step 4: Always update timestamp (even if no fields changed)
            now = datetime.now()
            book.last_metadata_update = now

            self.db.commit()

            # Step 5: Return result with only updated metadata
            return {
                'book_id': book.id,
                'title': book.title,
                'fields_updated': fields_updated,
                'updated_at': now.isoformat(),
                'metadata': metadata_to_update  # Only fields that were actually updated
            }

        except GoogleBooksRateLimitError as e:
            logger.warning(f"Rate limit hit for {book.title}: {e}")
            raise

        except Exception as e:
            logger.error(f"Error updating {book.title}: {e}")
            raise

    async def get_update_status(self) -> Dict[str, Any]:
        """
        Get current metadata update status across all books.

        Returns:
            {
                'total_books': int,
                'books_updated': int,
                'books_pending': int,
                'percent_updated': float,
                'oldest_update': ISO8601 timestamp or null,
                'newest_update': ISO8601 timestamp,
                'average_days_since_update': float
            }
        """
        try:
            total = self.db.query(func.count(Book.id)).filter(
                Book.status == 'active'
            ).scalar() or 0

            updated = self.db.query(func.count(Book.id)).filter(
                and_(
                    Book.status == 'active',
                    Book.last_metadata_update.isnot(None)
                )
            ).scalar() or 0

            pending = total - updated

            # Get oldest and newest update times
            oldest = self.db.query(Book.last_metadata_update).filter(
                and_(
                    Book.status == 'active',
                    Book.last_metadata_update.isnot(None)
                )
            ).order_by(asc(Book.last_metadata_update)).first()

            newest = self.db.query(Book.last_metadata_update).filter(
                and_(
                    Book.status == 'active',
                    Book.last_metadata_update.isnot(None)
                )
            ).order_by(func.desc(Book.last_metadata_update)).first()

            oldest_time = oldest[0] if oldest and oldest[0] else None
            newest_time = newest[0] if newest and newest[0] else None

            # Calculate average days since update
            avg_days = None
            if updated > 0:
                result = self.db.query(
                    func.avg(
                        func.julianday(datetime.now()) - func.julianday(Book.last_metadata_update)
                    )
                ).filter(
                    and_(
                        Book.status == 'active',
                        Book.last_metadata_update.isnot(None)
                    )
                ).scalar()
                avg_days = float(result) if result else None

            return {
                'total_books': total,
                'books_updated': updated,
                'books_pending': pending,
                'percent_updated': (updated / total * 100) if total > 0 else 0,
                'oldest_update': oldest_time.isoformat() if oldest_time else None,
                'newest_update': newest_time.isoformat() if newest_time else None,
                'average_days_since_update': avg_days
            }

        except Exception as e:
            logger.error(f"Error getting update status: {e}")
            return {
                'total_books': 0,
                'books_updated': 0,
                'books_pending': 0,
                'percent_updated': 0,
                'oldest_update': None,
                'newest_update': None,
                'average_days_since_update': None
            }
