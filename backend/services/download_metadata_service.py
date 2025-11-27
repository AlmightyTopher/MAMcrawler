"""
Download Metadata Service - Integrated download + MAM metadata collection + ABS update

This service orchestrates the complete workflow:
1. Download starts (triggered via Prowlarr/manual)
2. Collect metadata from MAM during download
3. Monitor download progress
4. Upon completion, apply metadata to Audiobookshelf

Metadata is collected at download-time while book info is fresh in mind,
then applied post-completion after verifying successful import to ABS.
"""

import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from backend.models.download import Download
from backend.models.book import Book
from backend.integrations.mam_search_client import MAMDownloadMetadataCollector
from backend.integrations.abs_client import AudiobookshelfClient

logger = logging.getLogger(__name__)


class DownloadMetadataService:
    """
    Manages metadata collection and application for downloads.

    Workflow:
    1. create_download_with_metadata() - queues download + collects MAM metadata
    2. Metadata stored in download record as JSON
    3. on_download_completed() - verifies book in ABS + applies metadata
    4. Metadata updated in ABS + Book model
    """

    def __init__(
        self,
        mam_collector: MAMDownloadMetadataCollector,
        abs_client: AudiobookshelfClient,
        db: Session
    ):
        """
        Initialize service.

        Args:
            mam_collector: MAMDownloadMetadataCollector instance
            abs_client: Authenticated AudiobookshelfClient
            db: SQLAlchemy database session
        """
        self.mam_collector = mam_collector
        self.abs_client = abs_client
        self.db = db

    async def create_download_with_metadata(
        self,
        title: str,
        author: str = "",
        series: str = "",
        series_number: str = "",
        magnet_link: Optional[str] = None,
        torrent_url: Optional[str] = None,
        book_id: Optional[int] = None,
        missing_book_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a download record and collect MAM metadata.

        This is the PRIMARY entry point when a new book download is initiated.

        Args:
            title: Book title
            author: Author name
            series: Series name (if applicable)
            series_number: Position in series (if applicable)
            magnet_link: Magnet link to torrent
            torrent_url: Direct torrent URL
            book_id: If book already exists in library
            missing_book_id: If part of missing books list

        Returns:
            Download record with metadata, or None if failed
        """
        logger.info(f"Creating download with metadata collection: {title} by {author}")

        try:
            # Step 1: Collect metadata from MAM
            logger.info("Step 1: Collecting metadata from MAM...")
            metadata = await self.mam_collector.collect_metadata_for_download(
                title=title,
                author=author,
                series=series,
                series_number=series_number
            )

            if not metadata:
                logger.warning(f"No MAM metadata found for {title}, proceeding without it")
                metadata = {}
            else:
                logger.info(f"✓ Collected MAM metadata (completeness: {self._calc_completeness(metadata):.0%})")

            # Step 2: Create download record
            logger.info("Step 2: Creating download record...")
            download = Download(
                title=title,
                author=author,
                source="MAM",
                magnet_link=magnet_link,
                torrent_url=torrent_url,
                book_id=book_id,
                missing_book_id=missing_book_id,
                status="queued",
                metadata_json=json.dumps(metadata) if metadata else None
            )

            self.db.add(download)
            self.db.commit()
            self.db.refresh(download)

            logger.info(f"✓ Created download record (ID: {download.id})")

            return {
                'download_id': download.id,
                'title': title,
                'author': author,
                'metadata_collected': bool(metadata),
                'metadata_completeness': self._calc_completeness(metadata) if metadata else 0
            }

        except Exception as e:
            logger.error(f"Error creating download with metadata: {e}")
            self.db.rollback()
            return None

    async def on_download_completed(
        self,
        download_id: int,
        qbittorrent_hash: Optional[str] = None
    ) -> bool:
        """
        Apply MAM metadata to book after download completes.

        This should be called when:
        1. Download completes in qBittorrent
        2. Book has been imported to Audiobookshelf
        3. Ready for metadata application

        Args:
            download_id: Download record ID
            qbittorrent_hash: qBittorrent info hash (for verification)

        Returns:
            True if metadata applied successfully
        """
        logger.info(f"Processing completed download (ID: {download_id})")

        try:
            # Step 1: Get download record
            download = self.db.query(Download).filter(Download.id == download_id).first()

            if not download:
                logger.error(f"Download record not found: {download_id}")
                return False

            if not download.metadata_json:
                logger.info(f"No metadata stored for download {download_id}")
                return True

            # Step 2: Parse stored metadata
            metadata = json.loads(download.metadata_json)
            logger.info(f"Retrieved metadata for: {metadata.get('title')}")

            # Step 3: Find corresponding book in Audiobookshelf
            abs_book = None

            # If book_id is set, book already exists
            if download.book_id:
                book = self.db.query(Book).filter(Book.id == download.book_id).first()
                if book and book.abs_id:
                    abs_book = await self.abs_client.get_book(book.abs_id)
                    logger.info(f"Found existing book in ABS: {book.abs_id}")

            # Otherwise, search ABS for the book by title
            if not abs_book:
                logger.info(f"Searching ABS for new book: {download.title}")
                # Search in ABS libraries for matching title/author
                libs = await self.abs_client.get_libraries()
                for lib in libs.get('libraries', []):
                    lib_id = lib['id']
                    items = await self.abs_client.get_library_items(lib_id)
                    for item in items.get('items', []):
                        item_metadata = item.get('media', {}).get('metadata', {})
                        if self._match_book(item_metadata, download.title, download.author):
                            abs_book = item
                            logger.info(f"Found matching book in ABS: {item.get('id')}")
                            break
                    if abs_book:
                        break

            if not abs_book:
                logger.warning(f"Could not find book in ABS: {download.title}")
                return False

            # Step 4: Apply metadata
            abs_id = abs_book.get('id')
            logger.info(f"Applying metadata to ABS book: {abs_id}")

            update_dict = self._build_abs_update(metadata)

            if update_dict:
                success = await self.abs_client.update_book_metadata(abs_id, update_dict)

                if success:
                    logger.info(f"✓ Successfully applied metadata to ABS")

                    # Update download record
                    download.abs_import_status = "imported"
                    download.metadata_applied_at = datetime.now()
                    self.db.commit()

                    # Update Book model if exists
                    if download.book_id:
                        book = self.db.query(Book).filter(Book.id == download.book_id).first()
                        if book:
                            self._update_book_model(book, metadata)
                            self.db.commit()

                    return True
                else:
                    logger.error("Failed to update ABS metadata")
                    download.abs_import_status = "import_failed"
                    download.abs_import_error = "ABS update failed"
                    self.db.commit()
                    return False
            else:
                logger.warning("No metadata to apply")
                return True

        except Exception as e:
            logger.error(f"Error processing completed download: {e}")
            return False

    def _build_abs_update(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build Audiobookshelf metadata update from MAM metadata.

        Only includes fields that ABS supports and that we have data for.
        """
        update = {}

        # Title
        if metadata.get('title'):
            update['title'] = metadata['title']

        # Author(s)
        if metadata.get('author'):
            update['authorName'] = metadata['author']
        elif metadata.get('authors'):
            update['authorName'] = ', '.join(metadata['authors'])

        # Narrator (critical for audio)
        if metadata.get('narrators'):
            # ABS doesn't have dedicated narrator field, could store in description
            # For now, prepend to description
            pass

        # Description
        if metadata.get('description'):
            update['description'] = metadata['description']

        # Publisher
        if metadata.get('publisher'):
            update['publisher'] = metadata['publisher']

        # Series (if available)
        if metadata.get('series'):
            update['seriesName'] = metadata['series']
            if metadata.get('series_number'):
                update['sequence'] = metadata['series_number']

        # ISBN
        if metadata.get('isbn'):
            update['isbn'] = metadata['isbn']

        return update

    def _update_book_model(self, book: Book, metadata: Dict[str, Any]):
        """Update Book ORM model with extracted metadata."""
        if metadata.get('title') and not book.title:
            book.title = metadata['title']

        if metadata.get('author') and not book.author:
            book.author = metadata['author']

        if metadata.get('narrators') and not book.narrator:
            book.narrator = ', '.join(metadata['narrators'])

        if metadata.get('duration_minutes') and not book.duration_minutes:
            book.duration_minutes = metadata['duration_minutes']

        if metadata.get('publisher') and not book.publisher:
            book.publisher = metadata['publisher']

        if metadata.get('series') and not book.series:
            book.series = metadata['series']

        if metadata.get('series_number') and not book.series_number:
            book.series_number = metadata['series_number']

        if metadata.get('is_abridged') is not None and book.is_abridged is None:
            book.is_abridged = metadata['is_abridged']

        book.metadata_source = metadata.get('source', 'mam')
        book.last_metadata_update = datetime.now()

    def _match_book(self, abs_metadata: Dict[str, Any], title: str, author: str) -> bool:
        """Check if ABS book matches download criteria."""
        abs_title = abs_metadata.get('title', '').lower()
        abs_author = abs_metadata.get('authorName', '').lower()

        search_title = title.lower()
        search_author = author.lower() if author else ""

        # Title match (main requirement)
        title_match = abs_title and search_title in abs_title or abs_title in search_title

        if not title_match:
            return False

        # Author match (if provided)
        if search_author:
            author_match = search_author in abs_author or abs_author in search_author
            return author_match

        return True

    def _calc_completeness(self, metadata: Dict[str, Any]) -> float:
        """Calculate metadata completeness score."""
        if not metadata:
            return 0.0

        fields_present = sum([
            bool(metadata.get('title')),
            bool(metadata.get('author')),
            bool(metadata.get('narrators')),
            bool(metadata.get('duration_minutes')),
            bool(metadata.get('description')),
            bool(metadata.get('publisher')),
            bool(metadata.get('series')),
            bool(metadata.get('is_abridged')),
        ])

        return fields_present / 8.0  # 8 key fields

    async def get_download_status(self, download_id: int) -> Optional[Dict[str, Any]]:
        """Get current status and metadata for a download."""
        try:
            download = self.db.query(Download).filter(Download.id == download_id).first()

            if not download:
                return None

            result = {
                'download_id': download.id,
                'title': download.title,
                'author': download.author,
                'status': download.status,
                'qb_status': download.qbittorrent_status,
                'abs_import_status': download.abs_import_status
            }

            if download.metadata_json:
                metadata = json.loads(download.metadata_json)
                result['metadata'] = metadata
                result['metadata_completeness'] = self._calc_completeness(metadata)

            return result

        except Exception as e:
            logger.error(f"Error getting download status: {e}")
            return None
