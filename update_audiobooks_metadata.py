#!/usr/bin/env python
"""
Update Audiobook Metadata with Series Linking
Syncs all books with Audiobookshelf and ensures proper series organization
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from dotenv import load_dotenv
import logging

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/metadata_update.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# IMPORTS
# ============================================================================

from backend.database import SessionLocal
from backend.models import Book, Series, Author
from backend.integrations.abs_client import AudiobookshelfClient
from backend.config import get_settings
from backend.utils.errors import AudiobookshelfError, ExternalAPIError

# ============================================================================
# CONFIGURATION
# ============================================================================

settings = get_settings()

class MetadataUpdateStats:
    """Track metadata update statistics"""
    def __init__(self):
        self.total_books = 0
        self.books_updated = 0
        self.books_with_series = 0
        self.series_linked = 0
        self.authors_updated = 0
        self.errors = []
        self.start_time = datetime.now()

    def print_summary(self):
        """Print statistics summary"""
        duration = datetime.now() - self.start_time
        print("\n" + "="*80)
        print("METADATA UPDATE SUMMARY")
        print("="*80)
        print(f"Total Books Processed:        {self.total_books}")
        print(f"Books Updated:                {self.books_updated}")
        print(f"Books with Series:            {self.books_with_series}")
        print(f"Series Linked:                {self.series_linked}")
        print(f"Authors Updated:              {self.authors_updated}")
        print(f"Errors Encountered:           {len(self.errors)}")
        print(f"Duration:                     {duration}")
        print("="*80 + "\n")

        if self.errors:
            print("ERRORS ENCOUNTERED:")
            for error in self.errors[:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more errors")

# ============================================================================
# METADATA UPDATE FUNCTIONS
# ============================================================================

async def get_abs_client() -> AudiobookshelfClient:
    """Create and return authenticated Audiobookshelf client"""
    client = AudiobookshelfClient(
        base_url=settings.ABS_URL,
        api_token=settings.ABS_TOKEN,
        timeout=30
    )
    return client

async def fetch_all_books_from_abs(client: AudiobookshelfClient) -> List[Dict[str, Any]]:
    """Fetch all books from Audiobookshelf library"""
    logger.info("Fetching all books from Audiobookshelf...")

    try:
        # Note: get_library_items() handles pagination internally
        # Just call it once with a large limit and it will return all items
        all_books = await client.get_library_items(limit=100, offset=0)

        logger.info(f"Total books retrieved from Audiobookshelf: {len(all_books)}")
        return all_books

    except Exception as e:
        logger.error(f"Error fetching books from Audiobookshelf: {str(e)}")
        raise

async def extract_series_info(book_data: Dict[str, Any]) -> tuple:
    """Extract series name and number from book metadata"""
    metadata = book_data.get('media', {}).get('metadata', {})

    series_name = metadata.get('series')
    series_number = metadata.get('seriesSequence')

    return series_name, series_number

async def create_or_update_series(
    db_session,
    series_name: str,
    book_ids: List[int]
) -> Series:
    """Create or update series in database"""
    existing_series = db_session.query(Series).filter_by(name=series_name).first()

    if existing_series:
        logger.info(f"Updating series: {series_name}")
        existing_series.book_count = len(book_ids)
        existing_series.books = [
            db_session.query(Book).filter_by(id=bid).first()
            for bid in book_ids if db_session.query(Book).filter_by(id=bid).first()
        ]
        db_session.commit()
        return existing_series
    else:
        logger.info(f"Creating new series: {series_name}")
        books = [
            db_session.query(Book).filter_by(id=bid).first()
            for bid in book_ids if db_session.query(Book).filter_by(id=bid).first()
        ]

        new_series = Series(
            name=series_name,
            book_count=len(books),
            books=books
        )
        db_session.add(new_series)
        db_session.commit()
        return new_series

async def update_book_metadata(
    client: AudiobookshelfClient,
    book_data: Dict[str, Any],
    db_book: Optional[Book] = None
) -> bool:
    """Update book metadata in Audiobookshelf"""
    try:
        book_id = book_data.get('id')
        metadata = book_data.get('media', {}).get('metadata', {})

        # Prepare update payload
        update_data = {
            'title': metadata.get('title', ''),
            'author': metadata.get('authors', [{}])[0].get('name', '') if metadata.get('authors') else '',
            'series': metadata.get('series'),
            'seriesSequence': metadata.get('seriesSequence'),
            'narrator': metadata.get('narrators', [{}])[0].get('name', '') if metadata.get('narrators') else '',
            'description': metadata.get('description', ''),
            'publishedYear': metadata.get('publishedYear'),
            'publisher': metadata.get('publisher'),
            'language': metadata.get('language'),
            'genres': metadata.get('genres', []),
            'tags': metadata.get('tags', [])
        }

        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            return False

        # Update in Audiobookshelf
        await client.update_book_metadata(book_id, update_data)
        logger.info(f"Updated metadata for book: {metadata.get('title', 'Unknown')}")

        return True

    except Exception as e:
        logger.error(f"Error updating book metadata: {str(e)}")
        return False

async def link_books_by_series(
    client: AudiobookshelfClient,
    books: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """Group books by series and ensure proper series links"""
    logger.info("Organizing books by series...")

    series_map = {}
    unseriesed_books = []

    for book in books:
        metadata = book.get('media', {}).get('metadata', {})
        series_name = metadata.get('series')

        if series_name:
            if series_name not in series_map:
                series_map[series_name] = []
            series_map[series_name].append(book)
        else:
            unseriesed_books.append(book)

    logger.info(f"Found {len(series_map)} series")
    logger.info(f"Books with series: {sum(len(v) for v in series_map.values())}")
    logger.info(f"Books without series: {len(unseriesed_books)}")

    return series_map

async def update_series_in_database(
    db_session,
    series_map: Dict[str, List[Dict[str, Any]]],
    stats: MetadataUpdateStats
) -> None:
    """Update series information in database"""
    logger.info("Updating series in database...")

    db_session.begin()

    try:
        for series_name, books in series_map.items():
            # Get or create series
            existing_series = db_session.query(Series).filter_by(name=series_name).first()

            if existing_series:
                existing_series.book_count = len(books)
            else:
                new_series = Series(
                    name=series_name,
                    book_count=len(books)
                )
                db_session.add(new_series)
                logger.info(f"Created series: {series_name} with {len(books)} books")

            stats.series_linked += 1

        db_session.commit()
        logger.info(f"Updated {stats.series_linked} series in database")

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error updating series: {str(e)}")
        stats.errors.append(f"Series update error: {str(e)}")

async def verify_audiobooks_metadata(
    client: AudiobookshelfClient,
    books: List[Dict[str, Any]],
    stats: MetadataUpdateStats
) -> None:
    """Verify and report on audiobook metadata"""
    logger.info("Verifying audiobook metadata...")

    print("\n" + "="*80)
    print("AUDIOBOOK METADATA VERIFICATION")
    print("="*80)

    stats.total_books = len(books)

    # Count books by series
    series_books = {}
    books_without_series = 0
    books_without_author = 0
    books_without_narrator = 0

    for book in books:
        metadata = book.get('media', {}).get('metadata', {})

        series = metadata.get('series')
        if series:
            if series not in series_books:
                series_books[series] = []
            series_books[series].append(metadata.get('title', 'Unknown'))
        else:
            books_without_series += 1

        if not metadata.get('authors'):
            books_without_author += 1

        if not metadata.get('narrators'):
            books_without_narrator += 1

    # Print series summary
    print(f"\nTotal Books: {stats.total_books}")
    print(f"Books with Series: {stats.total_books - books_without_series}")
    print(f"Books without Series: {books_without_series}")
    print(f"Books without Author: {books_without_author}")
    print(f"Books without Narrator: {books_without_narrator}")

    print(f"\nFound {len(series_books)} series:")
    for series_name in sorted(series_books.keys()):
        books_in_series = series_books[series_name]
        print(f"  - {series_name}: {len(books_in_series)} books")
        for i, title in enumerate(sorted(books_in_series), 1):
            print(f"      {i}. {title}")

    stats.books_with_series = stats.total_books - books_without_series
    print("\n" + "="*80 + "\n")

async def update_all_audiobooks_metadata() -> bool:
    """Main function to update all audiobooks metadata"""
    stats = MetadataUpdateStats()

    print("\n" + "="*80)
    print("AUDIOBOOK METADATA UPDATE WITH SERIES LINKING")
    print("="*80)
    print(f"Audiobookshelf URL: {settings.ABS_URL}")
    print(f"Database: {settings.DATABASE_URL}")
    print("="*80 + "\n")

    try:
        # Initialize Audiobookshelf client
        logger.info("Initializing Audiobookshelf client...")
        client = await get_abs_client()

        # Fetch all books
        logger.info("Fetching all audiobooks from Audiobookshelf...")
        all_books = await fetch_all_books_from_abs(client)

        if not all_books:
            logger.warning("No books found in Audiobookshelf library")
            print("[WARNING] No books found in Audiobookshelf library")
            return False

        # Get database session
        db_session = SessionLocal()

        # Verify metadata
        await verify_audiobooks_metadata(client, all_books, stats)

        # Link books by series
        series_map = await link_books_by_series(client, all_books)

        # Update series in database
        await update_series_in_database(db_session, series_map, stats)

        # Update book metadata
        logger.info("Updating individual book metadata...")
        for book in all_books:
            try:
                metadata = book.get('media', {}).get('metadata', {})
                title = metadata.get('title', 'Unknown')

                # Update in Audiobookshelf
                success = await update_book_metadata(client, book)

                if success:
                    stats.books_updated += 1
                    logger.info(f"[{stats.books_updated}/{stats.total_books}] Updated: {title}")
                else:
                    logger.warning(f"Skipped: {title}")

            except Exception as e:
                error_msg = f"Error updating {book.get('media', {}).get('metadata', {}).get('title', 'Unknown')}: {str(e)}"
                logger.error(error_msg)
                stats.errors.append(error_msg)

        # Close database session
        db_session.close()

        # Print summary
        stats.print_summary()

        logger.info("Audiobook metadata update completed successfully")
        return True

    except Exception as e:
        logger.error(f"Fatal error during metadata update: {str(e)}")
        print(f"\n[ERROR] Fatal error: {str(e)}")
        print("Check logs/metadata_update.log for details")
        return False

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    """Main entry point"""
    try:
        success = await update_all_audiobooks_metadata()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Metadata update cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {str(e)}")
        logger.exception("Unexpected error in main")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
