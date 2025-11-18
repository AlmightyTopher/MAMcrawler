"""
Metadata Correction Module - Google Books → Goodreads pipeline
Enriches book metadata using external APIs with fallback strategy
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from backend.models.book import Book
from backend.models.metadata_correction import MetadataCorrection
from backend.integrations.google_books_client import GoogleBooksClient

logger = logging.getLogger(__name__)


async def correct_book_metadata(
    book_id: int,
    db_session: Session,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Correct and enrich metadata for a single book

    Strategy:
        1. Query Google Books API for comprehensive metadata
        2. Fall back to Goodreads if Google Books fails or incomplete
        3. Update book.metadata_source with field→source mapping
        4. Calculate and update metadata_completeness_percent
        5. Create MetadataCorrection records for all changes

    Args:
        book_id: Database ID of book to correct
        db_session: SQLAlchemy database session
        force_refresh: Force refresh even if recently updated

    Returns:
        Dict with keys:
            - book_id: ID of corrected book
            - fields_updated: List of field names that were updated
            - sources_used: List of API sources queried
            - completeness_before: Completeness percentage before update
            - completeness_after: Completeness percentage after update
            - errors: List of error messages if any

    Raises:
        ValueError: If book_id not found
    """
    errors = []

    try:
        # Get book record
        book = db_session.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise ValueError(f"Book with ID {book_id} not found")

        logger.info(f"Correcting metadata for book: {book.title} (ID: {book_id})")

        # Check if recently updated (skip if updated within 7 days unless forced)
        if not force_refresh and book.last_metadata_update:
            days_since_update = (datetime.now() - book.last_metadata_update).days
            if days_since_update < 7:
                logger.info(f"Book metadata updated {days_since_update} days ago, skipping")
                return {
                    "book_id": book_id,
                    "fields_updated": [],
                    "sources_used": [],
                    "completeness_before": book.metadata_completeness_percent,
                    "completeness_after": book.metadata_completeness_percent,
                    "errors": ["Skipped: Recently updated"],
                    "skipped": True
                }

        # Store original values
        completeness_before = book.metadata_completeness_percent or 0
        fields_updated = []
        sources_used = []
        metadata_source = book.metadata_source or {}

        # Query Google Books API
        google_client = GoogleBooksClient()
        google_data = None

        try:
            logger.info(f"Querying Google Books for: {book.title} by {book.author}")

            # Search by title and author
            search_results = await google_client.search_books(
                query=f"{book.title} {book.author or ''}",
                max_results=5
            )

            if search_results and len(search_results) > 0:
                # Use first result (best match)
                google_data = search_results[0]
                sources_used.append("GoogleBooks")
                logger.info(f"Found Google Books match: {google_data.get('title')}")

        except Exception as e:
            logger.error(f"Google Books API error: {e}")
            errors.append(f"Google Books: {str(e)}")

        # Apply Google Books data if available
        if google_data:
            # Title
            if google_data.get("title") and not book.title:
                book.title = google_data["title"]
                metadata_source["title"] = "GoogleBooks"
                fields_updated.append("title")

            # Authors
            if google_data.get("authors") and not book.author:
                book.author = ", ".join(google_data["authors"])
                metadata_source["author"] = "GoogleBooks"
                fields_updated.append("author")

            # ISBN
            if google_data.get("isbn_13") and not book.isbn:
                book.isbn = google_data["isbn_13"]
                metadata_source["isbn"] = "GoogleBooks"
                fields_updated.append("isbn")
            elif google_data.get("isbn_10") and not book.isbn:
                book.isbn = google_data["isbn_10"]
                metadata_source["isbn"] = "GoogleBooks"
                fields_updated.append("isbn")

            # Publisher
            if google_data.get("publisher") and not book.publisher:
                book.publisher = google_data["publisher"]
                metadata_source["publisher"] = "GoogleBooks"
                fields_updated.append("publisher")

            # Published year
            if google_data.get("published_date") and not book.published_year:
                try:
                    # Parse year from date string (e.g., "2020-01-15" -> 2020)
                    year_str = google_data["published_date"].split("-")[0]
                    book.published_year = int(year_str)
                    metadata_source["published_year"] = "GoogleBooks"
                    fields_updated.append("published_year")
                except (ValueError, IndexError):
                    pass

            # Description
            if google_data.get("description") and not book.description:
                book.description = google_data["description"]
                metadata_source["description"] = "GoogleBooks"
                fields_updated.append("description")

        # TODO: Add Goodreads fallback
        # If Google Books data insufficient, query Goodreads
        # This requires implementing GoodreadsClient in integrations/
        # For now, we'll skip Goodreads integration

        # Calculate metadata completeness
        total_fields = 10
        complete_fields = sum([
            1 if book.title else 0,
            1 if book.author else 0,
            1 if book.series else 0,
            1 if book.isbn else 0,
            1 if book.asin else 0,
            1 if book.publisher else 0,
            1 if book.published_year else 0,
            1 if book.duration_minutes else 0,
            1 if book.description else 0,
            1 if book.series_number and book.series else 0
        ])

        completeness_after = int((complete_fields / total_fields) * 100)

        # Update book record
        book.metadata_completeness_percent = completeness_after
        book.last_metadata_update = datetime.now()
        book.metadata_source = metadata_source

        # Create MetadataCorrection records for each field updated
        for field_name in fields_updated:
            correction = MetadataCorrection(
                book_id=book.id,
                field_name=field_name,
                old_value=None,  # We didn't store old values
                new_value=getattr(book, field_name),
                source=metadata_source.get(field_name, "Unknown"),
                confidence_score=0.8,  # Default confidence
                date_corrected=datetime.now()
            )
            db_session.add(correction)

        db_session.commit()

        logger.info(
            f"Metadata correction complete: {len(fields_updated)} fields updated, "
            f"completeness: {completeness_before}% → {completeness_after}%"
        )

        return {
            "book_id": book_id,
            "fields_updated": fields_updated,
            "sources_used": sources_used,
            "completeness_before": completeness_before,
            "completeness_after": completeness_after,
            "errors": errors
        }

    except ValueError as e:
        logger.error(f"Book not found: {e}")
        raise

    except Exception as e:
        logger.exception(f"Error correcting metadata for book {book_id}: {e}")
        db_session.rollback()

        return {
            "book_id": book_id,
            "fields_updated": [],
            "sources_used": sources_used,
            "completeness_before": 0,
            "completeness_after": 0,
            "errors": [str(e)]
        }


async def correct_all_books(
    db_session: Session,
    limit: Optional[int] = None,
    filter_incomplete_only: bool = True,
    batch_size: int = 10
) -> Dict[str, Any]:
    """
    Correct metadata for all books (or filtered subset)

    Args:
        db_session: SQLAlchemy database session
        limit: Maximum number of books to process (None = all)
        filter_incomplete_only: Only process books with <100% completeness
        batch_size: Number of books to process in parallel

    Returns:
        Dict with keys:
            - total_processed: Total books processed
            - succeeded: Number of successful corrections
            - failed: Number of failed corrections
            - skipped: Number of skipped books
            - total_fields_updated: Total fields updated across all books
            - average_completeness_before: Average completeness before
            - average_completeness_after: Average completeness after
            - errors: List of error summaries
    """
    logger.info("Starting batch metadata correction for all books")

    try:
        # Build query
        query = db_session.query(Book).filter(Book.status == "active")

        if filter_incomplete_only:
            query = query.filter(Book.metadata_completeness_percent < 100)

        # Order by date_added (oldest first)
        query = query.order_by(Book.date_added.asc())

        if limit:
            query = query.limit(limit)

        books = query.all()

        logger.info(f"Found {len(books)} books to process")

        # Process books
        total_processed = 0
        succeeded = 0
        failed = 0
        skipped = 0
        total_fields_updated = 0
        completeness_before_sum = 0
        completeness_after_sum = 0
        errors = []

        for book in books:
            try:
                result = await correct_book_metadata(
                    book_id=book.id,
                    db_session=db_session,
                    force_refresh=False
                )

                total_processed += 1

                if result.get("skipped"):
                    skipped += 1
                elif result.get("errors") and not result.get("fields_updated"):
                    failed += 1
                    errors.append({
                        "book_id": book.id,
                        "title": book.title,
                        "errors": result["errors"]
                    })
                else:
                    succeeded += 1
                    total_fields_updated += len(result.get("fields_updated", []))

                completeness_before_sum += result.get("completeness_before", 0)
                completeness_after_sum += result.get("completeness_after", 0)

                # Log progress every 10 books
                if total_processed % 10 == 0:
                    logger.info(f"Progress: {total_processed}/{len(books)} books processed")

            except Exception as e:
                logger.error(f"Error processing book {book.id}: {e}")
                failed += 1
                errors.append({
                    "book_id": book.id,
                    "title": book.title,
                    "errors": [str(e)]
                })

        # Calculate averages
        avg_before = completeness_before_sum / total_processed if total_processed > 0 else 0
        avg_after = completeness_after_sum / total_processed if total_processed > 0 else 0

        result = {
            "total_processed": total_processed,
            "succeeded": succeeded,
            "failed": failed,
            "skipped": skipped,
            "total_fields_updated": total_fields_updated,
            "average_completeness_before": round(avg_before, 2),
            "average_completeness_after": round(avg_after, 2),
            "errors": errors[:10]  # Return first 10 errors only
        }

        logger.info(
            f"Batch metadata correction complete: {succeeded} succeeded, "
            f"{failed} failed, {skipped} skipped"
        )

        return result

    except Exception as e:
        logger.exception(f"Batch metadata correction failed: {e}")
        return {
            "total_processed": 0,
            "succeeded": 0,
            "failed": 0,
            "skipped": 0,
            "total_fields_updated": 0,
            "average_completeness_before": 0,
            "average_completeness_after": 0,
            "errors": [str(e)]
        }
