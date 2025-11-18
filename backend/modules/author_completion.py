"""
Author Completion Module - Author catalog discovery
Discovers missing books by favorite authors and queues for download
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.models.book import Book
from backend.models.author import Author
from backend.models.missing_book import MissingBook
from backend.models.download import Download
from backend.integrations.google_books_client import GoogleBooksClient
from backend.integrations.qbittorrent_client import QBittorrentClient

logger = logging.getLogger(__name__)


async def find_missing_author_books(
    db_session: Session,
    author_name: Optional[str] = None,
    min_books_threshold: int = 2
) -> Dict[str, Any]:
    """
    Find missing books by favorite authors

    Strategy:
        1. Get all authors from library with ≥ min_books_threshold books
        2. For each author:
            - Query Google Books for author's complete catalog
            - Query Prowlarr/MAM for audiobook availability
            - Identify books not in library
            - Create MissingBook records with author_gap reason
        3. Return count of missing books

    Args:
        db_session: SQLAlchemy database session
        author_name: Optional specific author to check (None = all authors)
        min_books_threshold: Minimum books by author to consider them a "favorite" (default: 2)

    Returns:
        Dict with keys:
            - authors_checked: Number of authors checked
            - missing_books_found: Total missing books identified
            - authors_with_gaps: Number of authors with missing books
            - missing_books: List of dicts with missing book details
            - errors: List of error messages
    """
    logger.info(f"Finding missing books by author: {author_name or 'all'}")

    try:
        # Get all authors with at least min_books_threshold books
        query = db_session.query(Book.author, func.count(Book.id).label('count')) \
            .filter(Book.author.isnot(None)) \
            .filter(Book.status == "active") \
            .group_by(Book.author) \
            .having(func.count(Book.id) >= min_books_threshold)

        if author_name:
            query = query.filter(Book.author == author_name)

        author_data = query.all()

        logger.info(f"Found {len(author_data)} authors to check")

        google_client = GoogleBooksClient()
        authors_checked = 0
        missing_books_found = 0
        authors_with_gaps = 0
        missing_books = []
        errors = []

        for author_name_row, book_count in author_data:
            try:
                logger.info(f"Checking author: {author_name_row} ({book_count} books in library)")

                # Get existing books by this author
                existing_books = db_session.query(Book) \
                    .filter(Book.author == author_name_row) \
                    .filter(Book.status == "active") \
                    .all()

                existing_titles = {book.title.lower() for book in existing_books}
                existing_isbns = {book.isbn for book in existing_books if book.isbn}

                # Query Google Books for author's catalog
                try:
                    results = await google_client.search_books_by_author(
                        author=author_name_row,
                        max_results=40  # Get up to 40 books per author
                    )

                    if results:
                        # Find missing books
                        for book_data in results:
                            book_title = book_data.get("title", "")
                            book_isbn = book_data.get("isbn_13") or book_data.get("isbn_10")

                            # Skip if already in library (by title or ISBN)
                            if book_title.lower() in existing_titles:
                                continue
                            if book_isbn and book_isbn in existing_isbns:
                                continue

                            # This book is missing from library
                            logger.info(f"Missing book identified: {book_title} by {author_name_row}")

                            # Check if already tracked
                            existing_missing = db_session.query(MissingBook) \
                                .filter(MissingBook.title == book_title) \
                                .filter(MissingBook.author == author_name_row) \
                                .filter(MissingBook.status == "pending") \
                                .first()

                            if not existing_missing:
                                # Create MissingBook record
                                missing_book = MissingBook(
                                    title=book_title,
                                    author=author_name_row,
                                    series=book_data.get("series"),
                                    series_number=None,
                                    isbn=book_isbn,
                                    reason="author_gap",
                                    discovery_source="google_books",
                                    status="pending",
                                    priority_score=40,  # Slightly lower than series gaps
                                    date_discovered=datetime.now()
                                )
                                db_session.add(missing_book)

                                missing_books.append({
                                    "title": book_title,
                                    "author": author_name_row,
                                    "series": book_data.get("series"),
                                    "isbn": book_isbn
                                })

                                missing_books_found += 1

                        if missing_books_found > 0:
                            authors_with_gaps += 1

                except Exception as e:
                    logger.error(f"Error querying Google Books for author {author_name_row}: {e}")
                    errors.append(f"{author_name_row}: {str(e)}")

                authors_checked += 1

            except Exception as e:
                logger.error(f"Error processing author {author_name_row}: {e}")
                errors.append(f"{author_name_row}: {str(e)}")

        # Commit all MissingBook records
        db_session.commit()

        result = {
            "authors_checked": authors_checked,
            "missing_books_found": missing_books_found,
            "authors_with_gaps": authors_with_gaps,
            "missing_books": missing_books[:20],  # Return first 20
            "errors": errors[:10]  # Return first 10 errors
        }

        logger.info(
            f"Author gap analysis complete: {missing_books_found} missing books found "
            f"for {authors_with_gaps} authors"
        )

        return result

    except Exception as e:
        logger.exception(f"Error finding missing author books: {e}")
        return {
            "authors_checked": 0,
            "missing_books_found": 0,
            "authors_with_gaps": 0,
            "missing_books": [],
            "errors": [str(e)]
        }


async def download_missing_author_books(
    db_session: Session,
    batch_size: int = 10,
    max_priority: Optional[int] = None
) -> Dict[str, Any]:
    """
    Queue downloads for missing author books

    Strategy:
        1. Get missing books marked for download (status=pending, reason=author_gap)
        2. For each batch:
            - Try Prowlarr search first (MAM + other indexers)
            - Fall back to Google Books links
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
    logger.info(f"Downloading missing author books (batch size: {batch_size})")

    try:
        # Get pending missing books by author
        query = db_session.query(MissingBook) \
            .filter(MissingBook.status == "pending") \
            .filter(MissingBook.reason == "author_gap") \
            .order_by(MissingBook.priority_score.desc())

        if max_priority is not None:
            query = query.filter(MissingBook.priority_score >= max_priority)

        query = query.limit(batch_size)

        missing_books = query.all()

        logger.info(f"Found {len(missing_books)} missing author books to download")

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
                # TODO: Integrate with Prowlarr for MAM/audiobook search
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
                # This requires Prowlarr integration

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
        logger.exception(f"Error downloading missing author books: {e}")
        return {
            "download_queued_count": 0,
            "success_count": 0,
            "failed_count": 0,
            "skipped_count": 0,
            "errors": [str(e)]
        }


async def import_and_correct_authors(
    db_session: Session
) -> Dict[str, Any]:
    """
    Monitor completed downloads, import to Audiobookshelf, and correct metadata

    This is a placeholder for the full import pipeline:
        1. Monitor qBittorrent for completed downloads
        2. Import files to Audiobookshelf library
        3. Run metadata correction on imported books
        4. Update author catalog tracking
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
    logger.info("Importing and correcting completed author downloads")

    try:
        # Get completed downloads for author_gap books
        completed_downloads = db_session.query(Download) \
            .join(MissingBook, Download.missing_book_id == MissingBook.id) \
            .filter(Download.status == "completed") \
            .filter(Download.date_imported.is_(None)) \
            .filter(MissingBook.reason == "author_gap") \
            .all()

        logger.info(f"Found {len(completed_downloads)} completed author downloads to import")

        # TODO: Implement full import pipeline
        # This requires:
        # 1. qBittorrent integration to detect completed torrents
        # 2. Audiobookshelf integration to import files
        # 3. Metadata correction integration
        # 4. Author catalog tracking updates

        return {
            "completed_downloads": len(completed_downloads),
            "imported_count": 0,
            "corrected_count": 0,
            "errors": ["Not implemented - requires full import pipeline"]
        }

    except Exception as e:
        logger.exception(f"Error importing author downloads: {e}")
        return {
            "completed_downloads": 0,
            "imported_count": 0,
            "corrected_count": 0,
            "errors": [str(e)]
        }
