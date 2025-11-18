"""
Top 10 Discovery Module - MAM visual top-10 genre scraper
Scrapes MAM's visual top-10 lists by genre and queues for download
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.models.download import Download
from backend.models.book import Book
from backend.integrations.qbittorrent_client import QBittorrentClient

logger = logging.getLogger(__name__)


async def scrape_mam_top10(
    genre: str,
    db_session: Session
) -> Dict[str, Any]:
    """
    Scrape MAM's visual top-10 list for a specific genre

    Strategy:
        1. Connect to MAM using existing stealth crawler authentication
        2. Navigate to top-10 page for genre
        3. Extract torrent links and metadata
        4. Return list of torrents with magnet/download links

    Args:
        genre: Genre to scrape (e.g., "Fiction", "Science Fiction", "Mystery")
        db_session: SQLAlchemy database session

    Returns:
        Dict with keys:
            - genre: Genre scraped
            - books_found: Number of books found in top-10
            - books: List of dicts with book details (title, author, magnet_link, etc.)
            - timestamp: Scrape timestamp
            - errors: List of error messages

    Note:
        This is a placeholder implementation. Full implementation requires:
        1. MAM authentication integration
        2. HTML parsing of top-10 page structure
        3. Torrent link extraction
        4. Rate limiting and stealth behavior
    """
    logger.info(f"Scraping MAM top-10 for genre: {genre}")

    try:
        # TODO: Implement MAM top-10 scraping
        # This requires:
        # 1. Reuse stealth_mam_crawler authentication
        # 2. Navigate to /top10.php?cat={genre_id}
        # 3. Parse HTML for torrent entries
        # 4. Extract: title, author, magnet link, metadata
        # 5. Apply rate limiting (10-30s between requests)

        # Placeholder implementation
        logger.warning("MAM top-10 scraping not yet implemented")

        return {
            "genre": genre,
            "books_found": 0,
            "books": [],
            "timestamp": datetime.now().isoformat(),
            "errors": ["Not implemented - requires MAM scraping integration"]
        }

    except Exception as e:
        logger.exception(f"Error scraping MAM top-10 for {genre}: {e}")
        return {
            "genre": genre,
            "books_found": 0,
            "books": [],
            "timestamp": datetime.now().isoformat(),
            "errors": [str(e)]
        }


async def queue_top10_downloads(
    genres_list: List[str],
    db_session: Session,
    skip_existing: bool = True
) -> Dict[str, Any]:
    """
    Queue downloads for top-10 books across multiple genres

    Strategy:
        1. For each genre in enabled_genres:
            - Call scrape_mam_top10 to get top-10 list
            - Filter out books already in library (by title/author)
            - Send magnet links to qBittorrent
            - Create Download records
        2. Return summary stats

    Args:
        genres_list: List of genre names to scrape
        db_session: SQLAlchemy database session
        skip_existing: Skip books already in library (default: True)

    Returns:
        Dict with keys:
            - genres_processed: Number of genres processed
            - total_books_found: Total books found across all genres
            - queued_count: Number of downloads queued
            - duplicates_skipped: Number of books skipped (already in library)
            - errors: List of error messages
    """
    logger.info(f"Queueing top-10 downloads for {len(genres_list)} genres")

    try:
        genres_processed = 0
        total_books_found = 0
        queued_count = 0
        duplicates_skipped = 0
        errors = []

        # Initialize qBittorrent client
        qb_client = QBittorrentClient()

        try:
            await qb_client.login()
        except Exception as e:
            logger.error(f"Failed to login to qBittorrent: {e}")
            return {
                "genres_processed": 0,
                "total_books_found": 0,
                "queued_count": 0,
                "duplicates_skipped": 0,
                "errors": [f"qBittorrent login failed: {str(e)}"]
            }

        for genre in genres_list:
            try:
                logger.info(f"Processing genre: {genre}")

                # Scrape top-10 for this genre
                result = await scrape_mam_top10(genre, db_session)

                if result.get("errors"):
                    errors.extend(result["errors"])

                books = result.get("books", [])
                total_books_found += len(books)

                # Process each book
                for book_data in books:
                    try:
                        title = book_data.get("title")
                        author = book_data.get("author")
                        magnet_link = book_data.get("magnet_link")

                        if not title or not magnet_link:
                            logger.warning(f"Skipping book with missing title or magnet: {book_data}")
                            continue

                        # Check if already in library
                        if skip_existing:
                            existing = db_session.query(Book) \
                                .filter(Book.title == title) \
                                .filter(Book.author == author) \
                                .filter(Book.status == "active") \
                                .first()

                            if existing:
                                logger.info(f"Skipping duplicate: {title} by {author}")
                                duplicates_skipped += 1
                                continue

                        # Check if already queued
                        existing_download = db_session.query(Download) \
                            .filter(Download.title == title) \
                            .filter(Download.status.in_(["pending", "downloading", "completed"])) \
                            .first()

                        if existing_download:
                            logger.info(f"Already queued: {title}")
                            duplicates_skipped += 1
                            continue

                        # Create Download record
                        download = Download(
                            title=title,
                            author=author,
                            source="mam_top10",
                            magnet_link=magnet_link,
                            status="pending",
                            priority=60,  # Higher priority for top-10 books
                            date_queued=datetime.now(),
                            metadata={
                                "genre": genre,
                                "top10_rank": book_data.get("rank"),
                                "scraped_at": result.get("timestamp")
                            }
                        )
                        db_session.add(download)

                        # TODO: Send to qBittorrent
                        # await qb_client.add_torrent(magnet_link)

                        queued_count += 1
                        logger.info(f"Queued: {title} by {author}")

                    except Exception as e:
                        logger.error(f"Error processing book {book_data.get('title')}: {e}")
                        errors.append({
                            "book": book_data.get("title"),
                            "error": str(e)
                        })

                genres_processed += 1

            except Exception as e:
                logger.error(f"Error processing genre {genre}: {e}")
                errors.append({
                    "genre": genre,
                    "error": str(e)
                })

        # Commit all Download records
        db_session.commit()

        result = {
            "genres_processed": genres_processed,
            "total_books_found": total_books_found,
            "queued_count": queued_count,
            "duplicates_skipped": duplicates_skipped,
            "errors": errors[:10]  # Return first 10 errors
        }

        logger.info(
            f"Top-10 queueing complete: {queued_count} queued, "
            f"{duplicates_skipped} duplicates skipped across {genres_processed} genres"
        )

        return result

    except Exception as e:
        logger.exception(f"Error queueing top-10 downloads: {e}")
        return {
            "genres_processed": 0,
            "total_books_found": 0,
            "queued_count": 0,
            "duplicates_skipped": 0,
            "errors": [str(e)]
        }


async def get_available_genres() -> Dict[str, Any]:
    """
    Get list of available genres from MAM

    Returns:
        Dict with keys:
            - genres: List of available genre names
            - genre_ids: Dict mapping genre names to MAM category IDs
            - timestamp: Query timestamp

    Note:
        This is a placeholder. Full implementation requires MAM scraping.
    """
    logger.info("Getting available MAM genres")

    try:
        # TODO: Scrape MAM for available categories
        # For now, return common audiobook genres

        common_genres = [
            "Fiction",
            "Science Fiction",
            "Fantasy",
            "Mystery",
            "Thriller",
            "Romance",
            "Historical Fiction",
            "Literary Fiction",
            "Horror",
            "Non-Fiction",
            "Biography",
            "History",
            "Self-Help",
            "Business",
            "Science",
            "Philosophy",
            "True Crime"
        ]

        return {
            "genres": common_genres,
            "genre_ids": {},  # Mapping not available without MAM scraping
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.exception(f"Error getting available genres: {e}")
        return {
            "genres": [],
            "genre_ids": {},
            "timestamp": datetime.now().isoformat(),
            "errors": [str(e)]
        }
