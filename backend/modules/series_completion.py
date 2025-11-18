"""
Series Completion Module - Series discovery and auto-download
Identifies missing books in series and queues them for download
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.models.book import Book
from backend.models.series import Series
from backend.models.missing_book import MissingBook
from backend.models.download import Download
from backend.integrations.google_books_client import GoogleBooksClient
from backend.integrations.qbittorrent_client import QBittorrentClient

logger = logging.getLogger(__name__)


async def find_missing_series_books(
    db_session: Session,
    series_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Find missing books in all series (or specific series)

    Strategy:
        1. Get all series from library with ≥1 book
        2. For each series:
            - Query Google Books API for complete series info
            - Identify books not in library
            - Create MissingBook records with series_gap reason
        3. Return count of missing books identified

    Args:
        db_session: SQLAlchemy database session
        series_name: Optional specific series to check (None = all series)

    Returns:
        Dict with keys:
            - series_checked: Number of series checked
            - missing_books_found: Total missing books identified
            - series_with_gaps: Number of series with missing books
            - missing_books: List of dicts with missing book details
            - errors: List of error messages
    """
    logger.info(f"Finding missing books in series: {series_name or 'all'}")

    try:
        # Get all series with at least 1 book
        query = db_session.query(Book.series, func.count(Book.id).label('count')) \
            .filter(Book.series.isnot(None)) \
            .filter(Book.status == "active") \
            .group_by(Book.series) \
            .having(func.count(Book.id) >= 1)

        if series_name:
            query = query.filter(Book.series == series_name)

        series_data = query.all()

        logger.info(f"Found {len(series_data)} series to check")

        google_client = GoogleBooksClient()
        series_checked = 0
        missing_books_found = 0
        series_with_gaps = 0
        missing_books = []
        errors = []

        for series_name_row, book_count in series_data:
            try:
                logger.info(f"Checking series: {series_name_row} ({book_count} books in library)")

                # Get existing books in this series
                existing_books = db_session.query(Book) \
                    .filter(Book.series == series_name_row) \
                    .filter(Book.status == "active") \
                    .all()

                existing_titles = {book.title.lower() for book in existing_books}

                # Query Google Books for series
                # Note: Google Books doesn't have great series support
                # This is a simplified approach - you may want to enhance with Goodreads
                search_query = f"series:{series_name_row}"
                try:
                    results = await google_client.search_books(
                        query=search_query,
                        max_results=40  # Most series have <40 books
                    )

                    if results:
                        series_books = []
                        for result in results:
                            # Filter to only books that mention the series in metadata
                            if series_name_row.lower() in result.get("title", "").lower():
                                series_books.append(result)

                        # Find missing books
                        for book_data in series_books:
                            book_title = book_data.get("title", "")

                            if book_title.lower() not in existing_titles:
                                # This book is missing from library
                                logger.info(f"Missing book identified: {book_title}")

                                # Check if already tracked
                                existing_missing = db_session.query(MissingBook) \
                                    .filter(MissingBook.title == book_title) \
                                    .filter(MissingBook.series == series_name_row) \
                                    .filter(MissingBook.status == "pending") \
                                    .first()

                                if not existing_missing:
                                    # Create MissingBook record
                                    missing_book = MissingBook(
                                        title=book_title,
                                        author=", ".join(book_data.get("authors", [])),
                                        series=series_name_row,
                                        series_number=None,  # Extract if available
                                        isbn=book_data.get("isbn_13"),
                                        reason="series_gap",
                                        discovery_source="google_books",
                                        status="pending",
                                        priority_score=50,  # Default priority
                                        date_discovered=datetime.now()
                                    )
                                    db_session.add(missing_book)

                                    missing_books.append({
                                        "title": book_title,
                                        "author": missing_book.author,
                                        "series": series_name_row,
                                        "isbn": missing_book.isbn
                                    })

                                    missing_books_found += 1

                        if missing_books_found > 0:
                            series_with_gaps += 1

                except Exception as e:
                    logger.error(f"Error querying Google Books for series {series_name_row}: {e}")
                    errors.append(f"{series_name_row}: {str(e)}")

                series_checked += 1

            except Exception as e:
                logger.error(f"Error processing series {series_name_row}: {e}")
                errors.append(f"{series_name_row}: {str(e)}")

        # Commit all MissingBook records
        db_session.commit()

        result = {
            "series_checked": series_checked,
            "missing_books_found": missing_books_found,
            "series_with_gaps": series_with_gaps,
            "missing_books": missing_books[:20],  # Return first 20
            "errors": errors[:10]  # Return first 10 errors
        }

        logger.info(
            f"Series gap analysis complete: {missing_books_found} missing books found "
            f"across {series_with_gaps} series"
        )

        return result

    except Exception as e:
        logger.exception(f"Error finding missing series books: {e}")
        return {
            "series_checked": 0,
            "missing_books_found": 0,
            "series_with_gaps": 0,
            "missing_books": [],
            "errors": [str(e)]
        }


async def download_missing_series_books(
    db_session: Session,
    batch_size: int = 10,
    max_priority: Optional[int] = None
) -> Dict[str, Any]:
    """
    Queue downloads for missing series books

    Strategy:
        1. Get missing books marked for download (status=pending)
        2. For each batch:
            - Try Prowlarr search first (MAM + other indexers)
            - Fall back to Google Books download links
            - Create Download queue record
            - Send to qBittorrent if torrent/magnet obtained
        3. Return download stats

    Args:
        db_session: SQLAlchemy database session
        batch_size: Number of books to process (default: 10)
        max_priority: Only process books with priority >= this (None = all)

    Returns:
        Dict with keys:
            - download_queued_count: Number of downloads queued
            - success_count: Number successfully sent to qBittorrent
            - failed_count: Number that failed
            - skipped_count: Number skipped (no sources found)
            - errors: List of error messages
    """
    logger.info(f"Downloading missing series books (batch size: {batch_size})")

    try:
        # Get pending missing books
        query = db_session.query(MissingBook) \
            .filter(MissingBook.status == "pending") \
            .filter(MissingBook.reason == "series_gap") \
            .order_by(MissingBook.priority_score.desc())

        if max_priority is not None:
            query = query.filter(MissingBook.priority_score >= max_priority)

        query = query.limit(batch_size)

        missing_books = query.all()

        logger.info(f"Found {len(missing_books)} missing books to download")

        download_queued_count = 0
        success_count = 0
        failed_count = 0
        skipped_count = 0
        errors = []

        # Initialize clients
        qb_client = QBittorrentClient()

        # Login to qBittorrent
        try:
            await qb_client.login()
        except Exception as e:
            logger.error(f"Failed to login to qBittorrent: {e}")
            return {
                "download_queued_count": 0,
                "success_count": 0,
                "failed_count": 0,
                "skipped_count": 0,
                "errors": [f"qBittorrent login failed: {str(e)}"]
            }

        for missing_book in missing_books:
            try:
                logger.info(f"Processing: {missing_book.title} by {missing_book.author}")

                # Try to find download source
                # TODO: Integrate with Prowlarr for MAM search
                # For now, we'll skip actual download and just mark as attempted

                # Create Download record
                download = Download(
                    missing_book_id=missing_book.id,
                    title=missing_book.title,
                    author=missing_book.author,
                    source="prowlarr",  # Placeholder
                    download_url=None,  # Will be set by actual implementation
                    magnet_link=None,  # Will be set by actual implementation
                    status="pending",
                    priority=missing_book.priority_score,
                    date_queued=datetime.now()
                )
                db_session.add(download)

                # TODO: Actually search and queue download
                # This requires Prowlarr integration which needs implementation

                # For now, mark as attempted
                missing_book.status = "download_attempted"
                missing_book.date_last_attempted = datetime.now()

                download_queued_count += 1
                skipped_count += 1  # Since we're not actually downloading yet

                logger.info(f"Queued download for: {missing_book.title}")

            except Exception as e:
                logger.error(f"Error processing {missing_book.title}: {e}")
                failed_count += 1
                errors.append({
                    "title": missing_book.title,
                    "error": str(e)
                })

        # Commit changes
        db_session.commit()

        result = {
            "download_queued_count": download_queued_count,
            "success_count": success_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "errors": errors[:10]
        }

        logger.info(
            f"Download queueing complete: {download_queued_count} queued, "
            f"{success_count} successful, {skipped_count} skipped"
        )

        return result

    except Exception as e:
        logger.exception(f"Error downloading missing series books: {e}")
        return {
            "download_queued_count": 0,
            "success_count": 0,
            "failed_count": 0,
            "skipped_count": 0,
            "errors": [str(e)]
        }


async def import_and_correct_series(
    db_session: Session
) -> Dict[str, Any]:
    """
    Monitor completed downloads, import to Audiobookshelf, and correct metadata

    This is a placeholder for the full import pipeline:
        1. Monitor qBittorrent for completed downloads
        2. Import files to Audiobookshelf library
        3. Run metadata correction on imported books
        4. Update series completion tracking
        5. Update MissingBook and Download records

    Args:
        db_session: SQLAlchemy database session

    Returns:
        Dict with keys:
            - completed_downloads: Number of completed downloads found
            - imported_count: Number successfully imported
            - corrected_count: Number with metadata corrected
            - errors: List of error messages
    """
    logger.info("Importing and correcting completed series downloads")

    try:
        # Get completed downloads
        completed_downloads = db_session.query(Download) \
            .filter(Download.status == "completed") \
            .filter(Download.date_imported.is_(None)) \
            .all()

        logger.info(f"Found {len(completed_downloads)} completed downloads to import")

        # TODO: Implement full import pipeline
        # This requires:
        # 1. qBittorrent integration to detect completed torrents
        # 2. Audiobookshelf integration to import files
        # 3. Metadata correction integration
        # 4. Series tracking updates

        return {
            "completed_downloads": len(completed_downloads),
            "imported_count": 0,
            "corrected_count": 0,
            "errors": ["Not implemented - requires full import pipeline"]
        }

    except Exception as e:
        logger.exception(f"Error importing series downloads: {e}")
        return {
            "completed_downloads": 0,
            "imported_count": 0,
            "corrected_count": 0,
            "errors": [str(e)]
        }
