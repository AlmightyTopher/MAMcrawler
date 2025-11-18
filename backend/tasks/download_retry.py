"""
Download Retry Task
Scheduled task to retry failed downloads with exponential backoff
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.database import SessionLocal
from backend.models.download import Download
from backend.integrations.qbittorrent_client import QBittorrentClient

logger = logging.getLogger(__name__)


async def retry_failed_downloads() -> Dict[str, Any]:
    """
    Retry failed downloads that are due for retry

    Strategy:
        1. Find downloads with status='failed' where:
           - retry_count < max_retries
           - next_retry <= now (or next_retry is null)
        2. For each download:
           - Increment retry_count
           - Re-send to qBittorrent
           - Update status to 'downloading' or 'failed'
           - Set next_retry with exponential backoff if failed

    Returns:
        Dict with retry statistics
    """
    logger.info("Starting download retry task")

    db: Session = SessionLocal()
    retried_count = 0
    success_count = 0
    failed_count = 0
    abandoned_count = 0
    errors = []

    try:
        # Find downloads eligible for retry
        now = datetime.now()

        eligible_downloads = db.query(Download).filter(
            Download.status == "failed",
            Download.retry_count < Download.max_retries,
            (Download.next_retry <= now) | (Download.next_retry.is_(None))
        ).all()

        logger.info(f"Found {len(eligible_downloads)} downloads eligible for retry")

        if not eligible_downloads:
            return {
                "retried": 0,
                "succeeded": 0,
                "failed": 0,
                "abandoned": 0,
                "errors": []
            }

        # Initialize qBittorrent client
        qb_client = QBittorrentClient()

        try:
            await qb_client.login()
        except Exception as e:
            logger.error(f"Failed to login to qBittorrent: {e}")
            return {
                "retried": 0,
                "succeeded": 0,
                "failed": 0,
                "abandoned": 0,
                "errors": [f"qBittorrent login failed: {str(e)}"]
            }

        for download in eligible_downloads:
            try:
                logger.info(
                    f"Retrying download {download.id}: {download.title} "
                    f"(attempt {download.retry_count + 1}/{download.max_retries})"
                )

                # Increment retry count
                download.retry_count += 1
                download.last_attempt = now
                retried_count += 1

                # Check if we have a magnet link or torrent URL
                if not download.magnet_link and not download.torrent_url:
                    logger.warning(f"Download {download.id} has no magnet/torrent link")
                    download.status = "abandoned"
                    abandoned_count += 1
                    continue

                # Try to add to qBittorrent
                try:
                    link = download.magnet_link or download.torrent_url

                    # Add torrent to qBittorrent
                    result = await qb_client.add_torrent(link)

                    if result:
                        download.status = "downloading"
                        download.qbittorrent_hash = result.get("hash")
                        download.next_retry = None
                        success_count += 1
                        logger.info(f"Successfully re-queued download {download.id}")
                    else:
                        raise Exception("qBittorrent returned no result")

                except Exception as qb_error:
                    logger.error(f"qBittorrent error for download {download.id}: {qb_error}")

                    # Check if max retries reached
                    if download.retry_count >= download.max_retries:
                        download.status = "abandoned"
                        download.next_retry = None
                        abandoned_count += 1
                        logger.warning(
                            f"Download {download.id} abandoned after "
                            f"{download.retry_count} retries"
                        )
                    else:
                        # Schedule next retry with exponential backoff
                        # 2^retry_count hours: 2h, 4h, 8h...
                        backoff_hours = 2 ** download.retry_count
                        download.next_retry = now + timedelta(hours=backoff_hours)
                        failed_count += 1
                        logger.info(
                            f"Download {download.id} will retry in {backoff_hours} hours"
                        )

                    errors.append({
                        "download_id": download.id,
                        "title": download.title,
                        "error": str(qb_error)
                    })

            except Exception as e:
                logger.error(f"Error processing download {download.id}: {e}")
                errors.append({
                    "download_id": download.id,
                    "title": download.title,
                    "error": str(e)
                })
                failed_count += 1

        # Commit all changes
        db.commit()

        result = {
            "retried": retried_count,
            "succeeded": success_count,
            "failed": failed_count,
            "abandoned": abandoned_count,
            "errors": errors[:10]  # Limit error list
        }

        logger.info(
            f"Download retry task complete: {success_count} succeeded, "
            f"{failed_count} failed, {abandoned_count} abandoned"
        )

        return result

    except Exception as e:
        db.rollback()
        logger.exception(f"Error in download retry task: {e}")
        return {
            "retried": retried_count,
            "succeeded": success_count,
            "failed": failed_count,
            "abandoned": abandoned_count,
            "errors": [str(e)]
        }
    finally:
        db.close()


def register_download_retry_task(scheduler: AsyncIOScheduler) -> None:
    """
    Register the download retry task with APScheduler

    Args:
        scheduler: APScheduler instance

    The task runs every hour by default.
    """
    from backend.config import get_settings
    settings = get_settings()

    # Get interval from config or default to 1 hour
    interval_hours = getattr(settings, 'DOWNLOAD_RETRY_INTERVAL_HOURS', 1)

    scheduler.add_job(
        retry_failed_downloads,
        'interval',
        hours=interval_hours,
        id='download_retry_task',
        name='Retry Failed Downloads',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )

    logger.info(f"Registered download retry task (runs every {interval_hours} hour(s))")
