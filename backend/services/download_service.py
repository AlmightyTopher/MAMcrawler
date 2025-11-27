"""
Download Service - Business logic for download queue operations
Handles download tracking, retry logic, and qBittorrent integration
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging
import asyncio

from backend.models.download import Download
from backend.models.book import Book

logger = logging.getLogger(__name__)


class DownloadService:
    """
    Service layer for download operations

    Provides methods for managing download queue, retry logic,
    and qBittorrent/Audiobookshelf integration
    """

    @staticmethod
    def create_download(
        db: Session,
        book_id: Optional[int],
        source: str,
        title: str,
        author: Optional[str] = None,
        magnet_link: Optional[str] = None,
        torrent_url: Optional[str] = None,
        missing_book_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new download record

        Args:
            db: Database session
            book_id: Book ID (if book exists)
            source: Download source (MAM, GoogleBooks, Goodreads, Manual)
            title: Book title
            author: Author name
            magnet_link: Magnet link for torrent
            torrent_url: URL to torrent file
            missing_book_id: Missing book ID (if applicable)

        Returns:
            Dict with:
                - success: bool
                - data: Download object if successful
                - error: str if failed
                - download_id: int if successful
        """
        try:
            if not magnet_link and not torrent_url:
                return {
                    "success": False,
                    "error": "Either magnet_link or torrent_url is required",
                    "data": None,
                    "download_id": None
                }

            # Create new download
            download = Download(
                book_id=book_id,
                missing_book_id=missing_book_id,
                title=title,
                author=author,
                source=source,
                magnet_link=magnet_link,
                torrent_url=torrent_url,
                status="queued"
            )

            db.add(download)
            db.commit()
            db.refresh(download)

            logger.info(f"Created download: {download.title} from {source} (ID: {download.id})")

            return {
                "success": True,
                "data": download,
                "download_id": download.id,
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error creating download for '{title}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None,
                "download_id": None
            }

    @staticmethod
    def get_download(db: Session, download_id: int) -> Dict[str, Any]:
        """
        Get download by ID

        Args:
            db: Database session
            download_id: Download ID

        Returns:
            Dict with success, data (Download or None), error
        """
        try:
            download = db.query(Download).filter(Download.id == download_id).first()

            if not download:
                return {
                    "success": False,
                    "error": f"Download with ID {download_id} not found",
                    "data": None
                }

            return {
                "success": True,
                "data": download,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting download {download_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    @staticmethod
    def get_all_pending(db: Session) -> Dict[str, Any]:
        """
        Get all queued downloads

        Returns:
            Dict with success, data (list of Downloads), count, error
        """
        try:
            downloads = db.query(Download).filter(
                Download.status == "queued"
            ).order_by(Download.date_queued).all()

            return {
                "success": True,
                "data": downloads,
                "count": len(downloads),
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting pending downloads: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0
            }

    @staticmethod
    def get_downloads_for_book(db: Session, book_id: int) -> Dict[str, Any]:
        """
        Get all download attempts for a book

        Args:
            db: Database session
            book_id: Book ID

        Returns:
            Dict with success, data (list of Downloads), count, error
        """
        try:
            downloads = db.query(Download).filter(
                Download.book_id == book_id
            ).order_by(Download.date_queued.desc()).all()

            return {
                "success": True,
                "data": downloads,
                "count": len(downloads),
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting downloads for book {book_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0
            }

    @staticmethod
    def update_status(
        db: Session,
        download_id: int,
        status: str,
        qb_hash: Optional[str] = None,
        qb_status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update download status

        Args:
            db: Database session
            download_id: Download ID
            status: New status (queued, downloading, completed, failed, abandoned)
            qb_hash: qBittorrent info hash
            qb_status: qBittorrent status (downloading, seeding, completed)

        Returns:
            Dict with success, data (updated Download), error
        """
        try:
            download = db.query(Download).filter(Download.id == download_id).first()

            if not download:
                return {
                    "success": False,
                    "error": f"Download with ID {download_id} not found",
                    "data": None
                }

            download.status = status
            download.last_attempt = datetime.now()

            if qb_hash:
                download.qbittorrent_hash = qb_hash

            if qb_status:
                download.qbittorrent_status = qb_status

            db.commit()
            db.refresh(download)

            logger.info(f"Updated download {download_id} status to '{status}'")

            return {
                "success": True,
                "data": download,
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating download {download_id} status: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    @staticmethod
    def mark_completed(
        db: Session,
        download_id: int,
        abs_import_status: str = "pending"
    ) -> Dict[str, Any]:
        """
        Mark download as completed

        Args:
            db: Database session
            download_id: Download ID
            abs_import_status: Audiobookshelf import status (pending, imported, import_failed)

        Returns:
            Dict with success, data (updated Download), error
        """
        try:
            download = db.query(Download).filter(Download.id == download_id).first()

            if not download:
                return {
                    "success": False,
                    "error": f"Download with ID {download_id} not found",
                    "data": None
                }

            download.status = "completed"
            download.date_completed = datetime.now()
            download.abs_import_status = abs_import_status
            download.qbittorrent_status = "completed"

            db.commit()
            db.refresh(download)

            logger.info(f"Marked download {download_id} as completed: {download.title}")

            return {
                "success": True,
                "data": download,
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error marking download {download_id} as completed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    @staticmethod
    def mark_failed(
        db: Session,
        download_id: int,
        error_msg: str,
        retry_attempt: int = 1
    ) -> Dict[str, Any]:
        """
        Mark download as failed

        Args:
            db: Database session
            download_id: Download ID
            error_msg: Error message
            retry_attempt: Current retry attempt number

        Returns:
            Dict with success, data (updated Download), error
        """
        try:
            download = db.query(Download).filter(Download.id == download_id).first()

            if not download:
                return {
                    "success": False,
                    "error": f"Download with ID {download_id} not found",
                    "data": None
                }

            download.retry_count = retry_attempt
            download.last_attempt = datetime.now()

            # Check if we've exceeded max retries
            if download.retry_count >= download.max_retries:
                download.status = "abandoned"
                download.abs_import_error = f"Max retries exceeded: {error_msg}"
                logger.warning(f"Download {download_id} abandoned after {download.retry_count} retries")
            else:
                download.status = "failed"
                download.abs_import_error = error_msg
                logger.warning(f"Download {download_id} failed (attempt {retry_attempt}): {error_msg}")

            db.commit()
            db.refresh(download)

            return {
                "success": True,
                "data": download,
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error marking download {download_id} as failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    @staticmethod
    def schedule_retry(
        db: Session,
        download_id: int,
        days_until_retry: int = 1
    ) -> Dict[str, Any]:
        """
        Schedule download for retry

        Args:
            db: Database session
            download_id: Download ID
            days_until_retry: Number of days to wait before retry

        Returns:
            Dict with success, data (updated Download), next_retry, error
        """
        try:
            download = db.query(Download).filter(Download.id == download_id).first()

            if not download:
                return {
                    "success": False,
                    "error": f"Download with ID {download_id} not found",
                    "data": None,
                    "next_retry": None
                }

            # Calculate next retry time
            next_retry = datetime.now() + timedelta(days=days_until_retry)
            download.next_retry = next_retry
            download.status = "queued"

            db.commit()
            db.refresh(download)

            logger.info(f"Scheduled download {download_id} for retry at {next_retry}")

            return {
                "success": True,
                "data": download,
                "next_retry": next_retry.isoformat(),
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error scheduling retry for download {download_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None,
                "next_retry": None
            }

    @staticmethod
    def get_failed_downloads(db: Session) -> Dict[str, Any]:
        """
        Get all failed downloads

        Returns:
            Dict with success, data (list of Downloads), count, error
        """
        try:
            downloads = db.query(Download).filter(
                Download.status.in_(["failed", "abandoned"])
            ).order_by(Download.last_attempt.desc()).all()

            return {
                "success": True,
                "data": downloads,
                "count": len(downloads),
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting failed downloads: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0
            }

    @staticmethod
    def get_retry_due(db: Session) -> Dict[str, Any]:
        """
        Get downloads ready to retry (next_retry <= now)

        Returns:
            Dict with success, data (list of Downloads), count, error
        """
        try:
            now = datetime.now()

            downloads = db.query(Download).filter(
                Download.status == "queued",
                Download.next_retry.isnot(None),
                Download.next_retry <= now
            ).order_by(Download.next_retry).all()

            return {
                "success": True,
                "data": downloads,
                "count": len(downloads),
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting downloads ready for retry: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0
            }

    @staticmethod
    async def on_download_completed(
        db: Session,
        download_id: int,
        torrent_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        GAP 1 + GAP 4 IMPLEMENTATION: Handle download completion event.

        Triggered when qBittorrent marks torrent as complete.

        Workflow:
        1. Verify download record exists
        2. GAP 4: Run integrity check
        3. If integrity fails: queue alternate release
        4. If integrity passes: GAP 1: Trigger metadata scan
        5. Mark as seeding

        Args:
            db: Database session
            download_id: Download ID
            torrent_name: Torrent name (optional, loaded from DB if not provided)

        Returns:
            Dict with status, scan_result, integrity_result, errors
        """
        try:
            from backend.services.integrity_check_service import IntegrityCheckService

            # 1. Load download record
            download = db.query(Download).filter(
                Download.id == download_id
            ).first()

            if not download:
                error_msg = f"Download {download_id} not found"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "error": error_msg,
                    "download_id": download_id
                }

            logger.info(f"Processing download completion for download {download_id}: {download.title}")

            # 2. Update status to integrity_checking
            download.status = "integrity_checking"
            download.last_attempt = datetime.now()
            db.commit()

            # GAP 4: Run integrity check
            integrity_service = IntegrityCheckService(db)
            integrity_result = await integrity_service.verify_download(
                download_id=download_id,
                torrent_hash=download.qbittorrent_hash
            )

            logger.info(f"Integrity check result: {integrity_result.get('status')}")

            # Check integrity result
            if integrity_result.get("status") == "failed":
                logger.warning(f"Integrity check failed for download {download_id}")

                # Try to handle failure (queue alternate)
                alternate_download_id = await integrity_service.handle_integrity_failure(
                    download_id=download_id
                )

                download.status = "integrity_failed"
                if alternate_download_id:
                    download.status = "integrity_failed_retrying"

                db.commit()

                return {
                    "status": "integrity_failed",
                    "download_id": download_id,
                    "title": download.title,
                    "integrity_result": integrity_result,
                    "retry_download_id": alternate_download_id,
                    "timestamp": datetime.now().isoformat()
                }

            # GAP 1: Trigger metadata scan if integrity passed and book exists
            if download.book_id:
                # Update status to metadata_processing
                download.status = "metadata_processing"
                db.commit()

                try:
                    from backend.services.metadata_service import MetadataService

                    # Perform full scan
                    scan_result = MetadataService.perform_full_scan(
                        db=db,
                        book_id=download.book_id,
                        source="download_completion"
                    )

                    logger.info(
                        f"Metadata scan completed for book {download.book_id}: "
                        f"{scan_result.get('fields_updated', 0)} fields updated"
                    )

                except Exception as scan_error:
                    logger.warning(
                        f"Metadata scan failed for download {download_id}: {scan_error}"
                    )
                    # Don't fail the entire process if scan fails
                    scan_result = {
                        "status": "scan_error",
                        "error": str(scan_error)
                    }

                # Mark as fully processed and seeding
                download.status = "seeding"
                download.metadata_processed_at = datetime.now()
                download.fully_processed = True
                download.abs_import_status = "imported"
                db.commit()

                return {
                    "status": "success",
                    "download_id": download_id,
                    "title": download.title,
                    "integrity_result": integrity_result,
                    "scan_result": scan_result,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # No book associated, just mark as seeding
                download.status = "seeding"
                download.metadata_processed_at = datetime.now()
                download.fully_processed = True
                db.commit()

                return {
                    "status": "success",
                    "download_id": download_id,
                    "title": download.title,
                    "integrity_result": integrity_result,
                    "note": "No book associated, skipped metadata scan",
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Error processing download completion for {download_id}: {e}", exc_info=True)
            try:
                download = db.query(Download).filter(Download.id == download_id).first()
                if download:
                    download.status = "processing_error"
                    download.abs_import_error = str(e)
                    db.commit()
            except:
                pass

            return {
                "status": "error",
                "download_id": download_id,
                "error": str(e)
            }

    @staticmethod
    def get_downloads_needing_scan(
        db: Session,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get downloads that completed but need metadata scan.

        Returns:
            Dict with success, data (list of Downloads), count
        """
        try:
            # Find downloads that are completed but not yet fully processed
            downloads = db.query(Download).filter(
                Download.status.in_(["seeding", "metadata_processing"]),
                (Download.fully_processed == False) | (Download.fully_processed.is_(None))
            ).order_by(
                Download.date_completed.desc()
            ).limit(limit).all()

            return {
                "success": True,
                "data": downloads,
                "count": len(downloads),
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting downloads needing scan: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0
            }
