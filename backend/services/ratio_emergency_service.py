"""
SECTION 2: Ratio Emergency Management Service
==============================================

Ratio Emergency Management - Hard Floor at 1.00

Implements Section 2 of the MAMcrawler specification: Continuous ratio monitoring
with emergency freeze when ratio drops below 1.00.

Key Features:
- Monitor global ratio continuously (every 5 minutes)
- Enforce hard floor at 1.00 - cannot go below
- Freeze all paid downloads when ratio < 1.00
- Unpause all seeding torrents to maximize upload
- Block premium features during emergency
- Thaw freezes when ratio recovers above 1.05
- Track point generation and optimization
- Log all emergency events to Task table

Configuration:
- RATIO_FLOOR = 1.00 (hard floor threshold)
- RATIO_RECOVERY = 1.05 (resume normal operations threshold)
- RATIO_CHECK_INTERVAL = 300 seconds (5 minutes)
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import os

from backend.config import get_settings

import aiohttp
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.models.download import Download
from backend.models.task import Task
from backend.models.ratio_log import RatioLog
from backend.database import SessionLocal, get_db_context

logger = logging.getLogger(__name__)


class RatioEmergencyService:
    """
    SECTION 2: Ratio Emergency Management

    Continuously monitors global ratio and triggers emergency freeze when
    ratio drops below 1.00. Manages recovery when ratio climbs above 1.05.

    Responsibilities:
    - Check ratio every 5 minutes via MAM scraping
    - Activate emergency freeze at ratio <= 1.00
    - Pause all non-seeding torrents
    - Unpause all seeding torrents to maximize upload
    - Block all paid downloads
    - Track point generation vs spending
    - Calculate recovery time estimates
    - Log all events to Task table
    - Deactivate freeze when ratio >= 1.05
    """

    # Configuration constants
    RATIO_FLOOR = 1.00  # Hard floor - cannot go below
    RATIO_RECOVERY = 1.05  # Resume normal operations above this
    RATIO_CHECK_INTERVAL = 300  # Check every 5 minutes (seconds)

    def __init__(self, db: Session = None):
        """
        Initialize RatioEmergencyService.

        Args:
            db: Optional database session. If not provided, creates new session.
        """
        self.db = db
        self.base_url = "https://www.myanonamouse.net"
        self.username = os.getenv('MAM_USERNAME')
        self.password = os.getenv('MAM_PASSWORD')

        # State tracking
        self.emergency_active = False
        self.last_ratio = 1.0
        self.emergency_triggered_at = None
        self.session_cookies = None
        self.is_authenticated = False

        logger.info("SECTION 2: RatioEmergencyService initialized")

    async def check_ratio_status(self) -> Dict[str, Any]:
        """
        Check current global ratio and determine emergency status.

        Main entry point for ratio monitoring. Called by scheduler every 5 minutes.

        Returns:
            Dict with:
                - current_ratio: float (e.g., 1.234)
                - emergency_active: bool
                - freeze_timestamp: Optional[datetime]
                - freeze_duration_hours: float
                - action_taken: str (none|freeze_activated|freeze_deactivated)
        """
        try:
            logger.info("SECTION 2: Checking ratio status")

            # Fetch current ratio from MAM
            current_ratio = await self._fetch_current_ratio()

            if current_ratio is None:
                logger.error("SECTION 2: Failed to fetch ratio, using last known value")
                current_ratio = self.last_ratio

            # Determine if emergency action needed
            action_taken = "none"

            # Check if we need to activate emergency
            if current_ratio < self.RATIO_FLOOR and not self.emergency_active:
                logger.warning(
                    f"SECTION 2: Ratio {current_ratio:.3f} dropped below floor {self.RATIO_FLOOR}! "
                    f"Activating emergency freeze"
                )
                await self.handle_ratio_emergency()
                action_taken = "freeze_activated"
                self.emergency_active = True
                self.emergency_triggered_at = datetime.utcnow()

            # Check if we can deactivate emergency
            elif current_ratio >= self.RATIO_RECOVERY and self.emergency_active:
                logger.info(
                    f"SECTION 2: Ratio {current_ratio:.3f} recovered above {self.RATIO_RECOVERY}! "
                    f"Deactivating emergency freeze"
                )
                await self._deactivate_emergency_freeze()
                action_taken = "freeze_deactivated"
                self.emergency_active = False
                self.emergency_triggered_at = None

            # Calculate freeze duration
            freeze_duration_hours = 0.0
            if self.emergency_active and self.emergency_triggered_at:
                duration = datetime.utcnow() - self.emergency_triggered_at
                freeze_duration_hours = duration.total_seconds() / 3600.0

            result = {
                "current_ratio": current_ratio,
                "emergency_active": self.emergency_active,
                "freeze_timestamp": self.emergency_triggered_at,
                "freeze_duration_hours": freeze_duration_hours,
                "action_taken": action_taken
            }

            logger.info(
                f"SECTION 2: Ratio check complete - Ratio: {current_ratio:.3f}, "
                f"Emergency: {self.emergency_active}, Action: {action_taken}"
            )

            return result

        except Exception as e:
            logger.error(f"SECTION 2: Error checking ratio status: {e}", exc_info=True)
            return {
                "current_ratio": self.last_ratio,
                "emergency_active": self.emergency_active,
                "freeze_timestamp": self.emergency_triggered_at,
                "freeze_duration_hours": 0.0,
                "action_taken": "error",
                "error": str(e)
            }

    async def _fetch_current_ratio(self) -> Optional[float]:
        """
        Get global ratio from MAM user profile page.

        Authenticates with MAM if needed, then scrapes ratio from HTML.

        Returns:
            float: Current ratio (e.g., 1.234) or None if failed
        """
        connector = aiohttp.TCPConnector(ssl=False)
        timeout = aiohttp.ClientTimeout(total=15)

        try:
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                # Ensure authenticated
                if not await self._ensure_authenticated(session):
                    logger.warning("SECTION 2: Failed to authenticate for ratio check")
                    return None

                # Fetch user profile page
                user_url = f"{self.base_url}/userdetails.php"
                async with session.get(user_url, ssl=False) as response:
                    if response.status == 200:
                        html = await response.text()
                        ratio = self._extract_ratio(html)

                        if ratio is not None:
                            self.last_ratio = ratio
                            logger.info(f"SECTION 2: Current ratio fetched: {ratio:.3f}")
                            return ratio
                        else:
                            logger.warning("SECTION 2: Failed to extract ratio from HTML")
                            return None
                    else:
                        logger.error(f"SECTION 2: Failed to fetch user page: HTTP {response.status}")
                        return None

        except Exception as e:
            logger.error(f"SECTION 2: Error fetching ratio: {e}", exc_info=True)
            return None

    async def _ensure_authenticated(self, session: aiohttp.ClientSession) -> bool:
        """
        Ensure session is authenticated with MAM.

        Args:
            session: aiohttp session

        Returns:
            bool: True if authenticated, False otherwise
        """
        if self.is_authenticated:
            return True

        try:
            login_url = f"{self.base_url}/takelogin.php"

            data = {
                'username': self.username,
                'password': self.password,
                'login': 'Log in!'
            }

            logger.info("SECTION 2: Authenticating with MAM for ratio check")
            async with session.post(login_url, data=data, ssl=False) as response:
                if response.status == 200:
                    text = await response.text()
                    if "logout" in text.lower() or "my account" in text.lower():
                        self.is_authenticated = True
                        self.session_cookies = session.cookie_jar
                        logger.info("SECTION 2: Successfully authenticated with MAM")
                        return True

        except Exception as e:
            logger.error(f"SECTION 2: Authentication error: {e}")

        return False

    def _extract_ratio(self, html: str) -> Optional[float]:
        """
        Extract global ratio from user profile HTML.

        Args:
            html: HTML content from MAM user profile page

        Returns:
            float: Extracted ratio or None if not found
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            text = soup.get_text()

            # Search for ratio pattern (e.g., "Ratio: 1.85")
            import re
            ratio_match = re.search(r'[Rr]atio[:\s]+([0-9.]+)', text)
            if ratio_match:
                ratio = float(ratio_match.group(1))
                return ratio

            # Alternative: look for common ratio displays
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if 'ratio' in line.lower():
                    # Try to extract number from this line or next line
                    for word in line.split():
                        try:
                            return float(word)
                        except ValueError:
                            pass

        except Exception as e:
            logger.error(f"SECTION 2: Error extracting ratio from HTML: {e}")

        return None

    async def handle_ratio_emergency(self) -> Dict[str, Any]:
        """
        Activate emergency freeze when ratio < 1.00.

        Actions:
        1. Mark all paid downloads as emergency_blocked
        2. Pause all non-seeding torrents via qBittorrent
        3. Unpause all seeding torrents to maximize upload
        4. Activate paid download block
        5. Log emergency event to Task table
        6. Record to RatioLog

        Returns:
            Dict with:
                - status: str (activated|already_active|error)
                - downloads_blocked: int
                - torrents_paused: int
                - torrents_unpaused: int
                - timestamp: datetime
        """
        if self.emergency_active:
            return {
                "status": "already_active",
                "message": "Emergency freeze already active"
            }

        logger.error("SECTION 2: RATIO EMERGENCY - Activating emergency freeze")

        try:
            with get_db_context() as db:
                # 1. Block all paid downloads
                downloads_blocked = await self._activate_paid_download_block(db)

                # 2. Pause non-seeding torrents
                torrents_paused = await self._pause_non_seeding_torrents()

                # 3. Unpause all seeding torrents
                torrents_unpaused = await self._unpause_all_seeding()

                # 4. Log emergency event
                await self._log_emergency_event(
                    db=db,
                    event_type="emergency_activated",
                    ratio=self.last_ratio,
                    details={
                        "downloads_blocked": downloads_blocked,
                        "torrents_paused": torrents_paused,
                        "torrents_unpaused": torrents_unpaused
                    }
                )

                # 5. Record to RatioLog
                ratio_log = RatioLog(
                    timestamp=datetime.utcnow(),
                    global_ratio=self.last_ratio,
                    emergency_active=True,
                    seeding_allocation=torrents_unpaused
                )
                db.add(ratio_log)
                db.commit()

                result = {
                    "status": "activated",
                    "downloads_blocked": downloads_blocked,
                    "torrents_paused": torrents_paused,
                    "torrents_unpaused": torrents_unpaused,
                    "timestamp": datetime.utcnow(),
                    "ratio": self.last_ratio
                }

                logger.warning(
                    f"SECTION 2: Emergency freeze activated - "
                    f"{downloads_blocked} downloads blocked, "
                    f"{torrents_paused} torrents paused, "
                    f"{torrents_unpaused} torrents unpaused"
                )

                return result

        except Exception as e:
            logger.error(f"SECTION 2: Error activating emergency freeze: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow()
            }

    async def _deactivate_emergency_freeze(self) -> Dict[str, Any]:
        """
        Thaw freeze when ratio >= 1.05.

        Actions:
        1. Clear emergency_blocked flag on all downloads
        2. Restore paid_download_allowed = True
        3. Resume normal torrent management
        4. Log recovery event to Task table
        5. Record to RatioLog

        Returns:
            Dict with:
                - status: str (deactivated|not_active|error)
                - downloads_unblocked: int
                - timestamp: datetime
        """
        if not self.emergency_active:
            return {
                "status": "not_active",
                "message": "Emergency freeze not active"
            }

        logger.info("SECTION 2: Ratio recovered - Deactivating emergency freeze")

        try:
            with get_db_context() as db:
                # 1. Unblock paid downloads
                downloads_unblocked = db.query(Download).filter(
                    Download.emergency_blocked == 1
                ).update({
                    "emergency_blocked": 0,
                    "paid_download_allowed": 1
                }, synchronize_session=False)

                db.commit()

                # 2. Log recovery event
                await self._log_emergency_event(
                    db=db,
                    event_type="emergency_deactivated",
                    ratio=self.last_ratio,
                    details={
                        "downloads_unblocked": downloads_unblocked,
                        "recovery_ratio": self.last_ratio
                    }
                )

                # 3. Record to RatioLog
                ratio_log = RatioLog(
                    timestamp=datetime.utcnow(),
                    global_ratio=self.last_ratio,
                    emergency_active=False,
                    seeding_allocation=10  # Resume normal allocation
                )
                db.add(ratio_log)
                db.commit()

                result = {
                    "status": "deactivated",
                    "downloads_unblocked": downloads_unblocked,
                    "timestamp": datetime.utcnow(),
                    "ratio": self.last_ratio
                }

                logger.info(
                    f"SECTION 2: Emergency freeze deactivated - "
                    f"{downloads_unblocked} downloads unblocked"
                )

                return result

        except Exception as e:
            logger.error(f"SECTION 2: Error deactivating emergency freeze: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow()
            }

    async def block_paid_download(self, download_id: int) -> bool:
        """
        Check if paid download should be blocked due to ratio emergency.

        Called from DownloadService before queuing paid download.

        Args:
            download_id: Download ID to check

        Returns:
            bool: True if should block, False if allowed
        """
        try:
            if not self.emergency_active:
                return False  # No emergency, allow download

            with get_db_context() as db:
                download = db.query(Download).filter(Download.id == download_id).first()

                if not download:
                    logger.warning(f"SECTION 2: Download {download_id} not found")
                    return False

                # Check if this is a paid download
                if download.release_edition == "Paid":
                    logger.warning(
                        f"SECTION 2: Blocking paid download {download_id} ({download.title}) "
                        f"due to ratio emergency (ratio: {self.last_ratio:.3f})"
                    )

                    # Mark as blocked
                    download.emergency_blocked = 1
                    download.paid_download_allowed = 0
                    download.status = "blocked_ratio_emergency"
                    db.commit()

                    return True

                # Free downloads always allowed
                return False

        except Exception as e:
            logger.error(f"SECTION 2: Error checking paid download block: {e}", exc_info=True)
            return False

    async def get_emergency_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics about emergency status.

        Includes real-time bandwidth stats from qBittorrent and database metrics.

        Returns:
            Dict with:
                - current_ratio: float
                - emergency_active: bool
                - upload_rate_mbps: float (current)
                - download_rate_mbps: float (current)
                - active_uploads: int
                - active_downloads: int
                - frozen_downloads: int
                - time_in_emergency_hours: float
                - estimated_recovery_time_hours: float (or None)
                - timestamp: datetime
        """
        try:
            from backend.integrations.qbittorrent_client import QBittorrentClient

            settings = get_settings()
            qb_url = f"{settings.QB_HOST}:{settings.QB_PORT}"
            qb_user = os.getenv('QBITTORRENT_USER', 'admin')
            qb_pass = os.getenv('QBITTORRENT_PASSWORD', 'adminPassword')

            with get_db_context() as db:
                # Get real-time metrics from qBittorrent
                upload_rate_mbps = 0.0
                download_rate_mbps = 0.0
                active_uploads = 0
                active_downloads = 0

                async with QBittorrentClient(qb_url, qb_user, qb_pass) as qb:
                    # Get server state for bandwidth info
                    server_state = await qb.get_server_state()
                    upload_speed_bytes = server_state.get('up_info_speed', 0)
                    download_speed_bytes = server_state.get('dl_info_speed', 0)

                    # Convert to MB/s
                    upload_rate_mbps = upload_speed_bytes / (1024 * 1024)
                    download_rate_mbps = download_speed_bytes / (1024 * 1024)

                    # Count active torrents by state
                    uploading = await qb.get_all_torrents(filter_state="uploading")
                    downloading = await qb.get_all_torrents(filter_state="downloading")
                    seeding = await qb.get_all_torrents(filter_state="seeding")

                    active_uploads = len(uploading) + len(seeding)
                    active_downloads = len(downloading)

                # Count frozen downloads from database
                frozen_downloads = db.query(Download).filter(
                    Download.emergency_blocked == 1
                ).count()

                # Calculate time in emergency
                time_in_emergency_hours = 0.0
                if self.emergency_active and self.emergency_triggered_at:
                    duration = datetime.utcnow() - self.emergency_triggered_at
                    time_in_emergency_hours = duration.total_seconds() / 3600.0

                # Calculate recovery time estimate
                estimated_recovery_time_hours = await self.calculate_recovery_time()

                metrics = {
                    "current_ratio": self.last_ratio,
                    "emergency_active": self.emergency_active,
                    "upload_rate_mbps": round(upload_rate_mbps, 2),
                    "download_rate_mbps": round(download_rate_mbps, 2),
                    "active_uploads": active_uploads,
                    "active_downloads": active_downloads,
                    "frozen_downloads": frozen_downloads,
                    "time_in_emergency_hours": round(time_in_emergency_hours, 2),
                    "estimated_recovery_time_hours": round(estimated_recovery_time_hours, 2) if estimated_recovery_time_hours else None,
                    "timestamp": datetime.utcnow()
                }

                logger.info(
                    f"SECTION 2: Emergency metrics - Ratio: {self.last_ratio:.3f}, "
                    f"Active: {self.emergency_active}, "
                    f"Upload: {upload_rate_mbps:.2f} MB/s, "
                    f"Download: {download_rate_mbps:.2f} MB/s, "
                    f"Frozen: {frozen_downloads}, "
                    f"Recovery: {estimated_recovery_time_hours:.1f}h" if estimated_recovery_time_hours else "None"
                )

                return metrics

        except Exception as e:
            logger.error(f"SECTION 2: Error getting emergency metrics: {e}", exc_info=True)
            return {
                "current_ratio": self.last_ratio,
                "emergency_active": self.emergency_active,
                "error": str(e),
                "timestamp": datetime.utcnow()
            }

    async def calculate_recovery_time(self) -> Optional[float]:
        """
        Estimate hours until ratio recovers above 1.05.

        Uses actual qBittorrent upload/download rates to calculate recovery time:
        - Gets current upload and download speeds from qBittorrent
        - Calculates net ratio improvement per hour
        - Estimates hours needed to reach recovery threshold

        Formula:
        - Net ratio improvement = (upload_rate - download_rate) / total_uploaded
        - Hours to recovery = ratio_gap / (net improvement per hour)

        Returns:
            float: Estimated hours to recovery, or None if cannot calculate
        """
        try:
            if not self.emergency_active:
                return None

            from backend.integrations.qbittorrent_client import QBittorrentClient

            settings = get_settings()
            qb_url = f"{settings.QB_HOST}:{settings.QB_PORT}"
            qb_user = os.getenv('QBITTORRENT_USER', 'admin')
            qb_pass = os.getenv('QBITTORRENT_PASSWORD', 'adminPassword')

            ratio_gap = self.RATIO_RECOVERY - self.last_ratio

            if ratio_gap <= 0:
                return 0.0  # Already recovered

            logger.info(f"SECTION 2: Calculating recovery time (ratio gap: {ratio_gap:.3f})")

            async with QBittorrentClient(qb_url, qb_user, qb_pass) as qb:
                # Get server state with current speeds
                server_state = await qb.get_server_state()

                # Extract speeds (in bytes/s)
                upload_speed = server_state.get('up_info_speed', 0)  # bytes/sec
                download_speed = server_state.get('dl_info_speed', 0)  # bytes/sec

                # Convert to MB/s for logging
                upload_mbps = upload_speed / (1024 * 1024)
                download_mbps = download_speed / (1024 * 1024)

                logger.info(
                    f"SECTION 2: Current speeds - Upload: {upload_mbps:.2f} MB/s, "
                    f"Download: {download_mbps:.2f} MB/s"
                )

                # If no upload rate, recovery is unlikely
                if upload_speed <= 0:
                    logger.warning("SECTION 2: No upload speed detected, cannot estimate recovery")
                    return None

                # Get total seeding torrents to estimate total uploaded so far
                seeding = await qb.get_all_torrents(filter_state="seeding")
                total_uploaded = 0

                for torrent in seeding:
                    # Get torrent completion size
                    total_size = torrent.get('total_size', 0)
                    if total_size > 0:
                        total_uploaded += total_size

                logger.debug(f"SECTION 2: Total uploaded data: {total_uploaded / (1024**3):.2f} GB")

                # Calculate net ratio improvement per second
                # Ratio change = (uploaded - downloaded) / downloaded
                # If we have some seeding data, estimate based on upload surplus
                if total_uploaded > 0:
                    # Assume we need to upload enough to improve ratio
                    # Simple calculation: for each MB uploaded, ratio improves by MB / total_downloaded
                    # Since we don't have total_downloaded, assume it's inversely proportional to current ratio
                    estimated_download_data = total_uploaded / max(self.last_ratio, 0.1)

                    # Bytes needed to upload to reach recovery threshold
                    bytes_per_ratio_point = estimated_download_data * 0.01  # Per 0.01 ratio increase
                    bytes_needed = bytes_per_ratio_point * ratio_gap

                    if upload_speed > 0:
                        seconds_needed = bytes_needed / upload_speed
                        estimated_hours = seconds_needed / 3600.0
                    else:
                        return None
                else:
                    # Fallback: use conservative estimate based on upload speed alone
                    # Assume 1 TB uploaded improves ratio by 0.01
                    bytes_per_ratio_point = 1024 * 1024 * 1024 * 1024 * 0.01  # 1TB per 0.01 ratio
                    bytes_needed = bytes_per_ratio_point * ratio_gap

                    if upload_speed > 0:
                        seconds_needed = bytes_needed / upload_speed
                        estimated_hours = seconds_needed / 3600.0
                    else:
                        return None

                # Cap estimate at reasonable maximum (60 days)
                estimated_hours = min(estimated_hours, 60 * 24)

                logger.info(
                    f"SECTION 2: Recovery time estimate: {estimated_hours:.1f} hours "
                    f"(ratio gap: {ratio_gap:.3f}, upload: {upload_mbps:.2f} MB/s)"
                )

                return estimated_hours

        except Exception as e:
            logger.error(f"SECTION 2: Error calculating recovery time: {e}", exc_info=True)
            return None

    async def track_point_generation(self) -> Dict[str, Any]:
        """
        Track points generated vs spent for optimization.

        Process:
        1. Get total uploaded bytes from qBittorrent
        2. Estimate points earned (MAM awards points based on upload)
        3. Count points spent on paid downloads from database
        4. Calculate ROI (points_earned / points_spent)
        5. Recommend adjustments if ROI < 1.0

        MAM Point System (approximate):
        - Earn: ~1 point per GB uploaded (varies by content type)
        - Spend: Varies by release (typically 5-50 points per paid download)

        Returns:
            Dict with:
                - points_earned: int
                - points_spent: int
                - roi: float
                - recommendation: str
                - upload_gb: float (for reference)
                - paid_downloads_count: int
                - timestamp: datetime
        """
        try:
            from backend.integrations.qbittorrent_client import QBittorrentClient

            settings = get_settings()
            qb_url = f"{settings.QB_HOST}:{settings.QB_PORT}"
            qb_user = os.getenv('QBITTORRENT_USER', 'admin')
            qb_pass = os.getenv('QBITTORRENT_PASSWORD', 'adminPassword')

            logger.info("SECTION 2: Tracking point generation vs spending")

            with get_db_context() as db:
                # Get qBittorrent upload statistics
                total_uploaded_bytes = 0
                async with QBittorrentClient(qb_url, qb_user, qb_pass) as qb:
                    # Get server state for total upload info
                    server_state = await qb.get_server_state()
                    total_uploaded_bytes = server_state.get('total_uploaded', 0)

                    # Also sum up all seeding torrents' upload amounts
                    seeding = await qb.get_all_torrents(filter_state="seeding")
                    for torrent in seeding:
                        uploaded = torrent.get('uploaded', 0)
                        if uploaded > total_uploaded_bytes:
                            total_uploaded_bytes = uploaded

                # Convert to GB
                total_uploaded_gb = total_uploaded_bytes / (1024 ** 3)

                # Estimate points earned
                # Conservative estimate: 1 point per GB uploaded (MAM typically gives more)
                points_earned = max(int(total_uploaded_gb), 0)

                # Count paid downloads and estimate points spent
                paid_downloads = db.query(Download).filter(
                    Download.release_edition == "Paid",
                    Download.status.in_(["queued", "downloading", "completed", "seeding"])
                ).all()

                # Estimate points spent per download
                # This is approximate - actual values vary by release
                points_spent = 0
                for download in paid_downloads:
                    # Try to get actual points from metadata if available
                    if hasattr(download, 'points_cost') and download.points_cost:
                        points_spent += download.points_cost
                    else:
                        # Default estimate: 15 points per paid download
                        points_spent += 15

                paid_downloads_count = len(paid_downloads)

                # Calculate ROI
                if points_spent > 0:
                    roi = points_earned / points_spent
                else:
                    roi = 0.0 if points_earned == 0 else float('inf')

                # Generate recommendation
                if points_spent == 0:
                    recommendation = "no_paid_downloads"
                elif roi < 0.5:
                    recommendation = "critically_reduce_paid_downloads"
                elif roi < 1.0:
                    recommendation = "reduce_paid_downloads"
                elif roi >= 3.0:
                    recommendation = "can_significantly_increase_paid_downloads"
                elif roi >= 2.0:
                    recommendation = "can_increase_paid_downloads"
                elif roi >= 1.5:
                    recommendation = "can_moderately_increase_paid_downloads"
                else:
                    recommendation = "maintain_current_rate"

                result = {
                    "points_earned": points_earned,
                    "points_spent": points_spent,
                    "roi": roi,
                    "recommendation": recommendation,
                    "upload_gb": round(total_uploaded_gb, 2),
                    "paid_downloads_count": paid_downloads_count,
                    "timestamp": datetime.utcnow()
                }

                logger.info(
                    f"SECTION 2: Point tracking - Earned: {points_earned}, "
                    f"Spent: {points_spent}, ROI: {roi:.2f}, "
                    f"Upload: {total_uploaded_gb:.2f} GB, "
                    f"Paid Downloads: {paid_downloads_count}, "
                    f"Recommendation: {recommendation}"
                )

                return result

        except Exception as e:
            logger.error(f"SECTION 2: Error tracking point generation: {e}", exc_info=True)
            return {
                "error": str(e),
                "timestamp": datetime.utcnow()
            }

    async def _pause_non_seeding_torrents(self) -> int:
        """
        Pause all downloading torrents to conserve ratio.

        Pauses only downloading torrents while leaving seeding torrents alone.

        Returns:
            int: Number of torrents paused
        """
        try:
            from backend.integrations.qbittorrent_client import QBittorrentClient

            settings = get_settings()
            qb_url = f"{settings.QB_HOST}:{settings.QB_PORT}"
            qb_user = os.getenv('QBITTORRENT_USER', 'admin')
            qb_pass = os.getenv('QBITTORRENT_PASSWORD', 'adminPassword')

            logger.info("SECTION 2: Pausing non-seeding torrents")

            paused_count = 0
            async with QBittorrentClient(qb_url, qb_user, qb_pass) as qb:
                # Get all downloading torrents
                downloading = await qb.get_all_torrents(filter_state="downloading")
                logger.info(f"SECTION 2: Found {len(downloading)} downloading torrents to pause")

                for torrent in downloading:
                    try:
                        torrent_hash = torrent.get('hash')
                        torrent_name = torrent.get('name', 'Unknown')

                        await qb.pause_torrent(torrent_hash)
                        logger.info(f"SECTION 2: Paused downloading torrent: {torrent_name}")
                        paused_count += 1

                    except Exception as e:
                        logger.warning(f"SECTION 2: Failed to pause torrent: {e}")
                        # Continue with next torrent even if one fails
                        continue

            logger.info(f"SECTION 2: Successfully paused {paused_count} non-seeding torrents")
            return paused_count

        except Exception as e:
            logger.error(f"SECTION 2: Error pausing torrents: {e}", exc_info=True)
            return 0

    async def _unpause_all_seeding(self) -> int:
        """
        Unpause all paused seeding torrents to maximize upload.

        Only resumes torrents that are fully downloaded (progress >= 1.0).
        This maximizes upload rate during ratio emergency.

        Returns:
            int: Number of torrents unpaused
        """
        try:
            from backend.integrations.qbittorrent_client import QBittorrentClient

            settings = get_settings()
            qb_url = f"{settings.QB_HOST}:{settings.QB_PORT}"
            qb_user = os.getenv('QBITTORRENT_USER', 'admin')
            qb_pass = os.getenv('QBITTORRENT_PASSWORD', 'adminPassword')

            logger.info("SECTION 2: Unpausing all seeding torrents")

            unpaused_count = 0
            async with QBittorrentClient(qb_url, qb_user, qb_pass) as qb:
                # Get all paused torrents
                paused = await qb.get_all_torrents(filter_state="paused")
                logger.info(f"SECTION 2: Found {len(paused)} paused torrents")

                for torrent in paused:
                    try:
                        torrent_hash = torrent.get('hash')
                        torrent_name = torrent.get('name', 'Unknown')
                        progress = torrent.get('progress', 0)

                        # Only resume torrents that are fully downloaded (can seed)
                        if progress >= 1.0:
                            await qb.resume_torrent(torrent_hash)
                            logger.info(f"SECTION 2: Resumed seeding torrent: {torrent_name}")
                            unpaused_count += 1
                        else:
                            logger.debug(f"SECTION 2: Skipping incomplete torrent: {torrent_name} ({progress*100:.1f}%)")

                    except Exception as e:
                        logger.warning(f"SECTION 2: Failed to resume torrent: {e}")
                        # Continue with next torrent even if one fails
                        continue

            logger.info(f"SECTION 2: Successfully unpaused {unpaused_count} seeding torrents")
            return unpaused_count

        except Exception as e:
            logger.error(f"SECTION 2: Error unpausing torrents: {e}", exc_info=True)
            return 0

    async def _activate_paid_download_block(self, db: Session) -> int:
        """
        Block all paid downloads by setting flags in database.

        Args:
            db: Database session

        Returns:
            int: Number of downloads blocked
        """
        try:
            blocked_count = db.query(Download).filter(
                Download.release_edition == "Paid",
                Download.status.in_(["queued", "downloading"])
            ).update({
                "emergency_blocked": 1,
                "paid_download_allowed": 0,
                "status": "blocked_ratio_emergency"
            }, synchronize_session=False)

            db.commit()

            logger.warning(f"SECTION 2: Blocked {blocked_count} paid downloads")
            return blocked_count

        except Exception as e:
            logger.error(f"SECTION 2: Error blocking paid downloads: {e}", exc_info=True)
            db.rollback()
            return 0

    async def _log_emergency_event(
        self,
        db: Session,
        event_type: str,
        ratio: float,
        details: Dict[str, Any]
    ) -> None:
        """
        Log emergency event to Task table.

        Args:
            db: Database session
            event_type: Type of event (emergency_activated|emergency_deactivated)
            ratio: Current ratio
            details: Additional event details
        """
        try:
            task = Task(
                task_name="RATIO_EMERGENCY",
                scheduled_time=datetime.utcnow(),
                actual_start=datetime.utcnow(),
                actual_end=datetime.utcnow(),
                duration_seconds=0,
                status="completed",
                items_processed=1,
                items_succeeded=1,
                items_failed=0,
                log_output=f"SECTION 2: {event_type} - Ratio: {ratio:.3f}",
                task_metadata={
                    "event_type": event_type,
                    "ratio": ratio,
                    "ratio_floor": self.RATIO_FLOOR,
                    "ratio_recovery": self.RATIO_RECOVERY,
                    **details
                }
            )

            db.add(task)
            db.commit()

            logger.info(f"SECTION 2: Logged emergency event: {event_type}")

        except Exception as e:
            logger.error(f"SECTION 2: Error logging emergency event: {e}", exc_info=True)
            db.rollback()
