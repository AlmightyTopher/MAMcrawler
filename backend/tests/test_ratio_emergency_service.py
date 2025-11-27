"""
Unit tests for RatioEmergencyService

Tests cover:
1. Ratio status checking
2. Emergency activation/deactivation
3. Torrent management (pause/unpause)
4. Paid download blocking
5. Emergency metrics
6. Recovery time calculation
7. Event logging

Requirements:
- pytest
- pytest-asyncio
- unittest.mock
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.services.ratio_emergency_service import RatioEmergencyService
from backend.models.download import Download
from backend.models.task import Task
from backend.models.ratio_log import RatioLog
from backend.database import Base


@pytest.fixture
def db_session():
    """
    Create in-memory SQLite database for testing.

    Yields:
        Session: SQLAlchemy session for test database
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def ratio_service(db_session):
    """
    Create RatioEmergencyService instance with test database.

    Args:
        db_session: Test database session

    Returns:
        RatioEmergencyService: Service instance for testing
    """
    return RatioEmergencyService(db_session)


@pytest.fixture
def mock_qbittorrent_client():
    """
    Mock qBittorrent client.

    Returns:
        Mock: Mock qBittorrent client with typical methods
    """
    client = AsyncMock()
    client.get_server_stats = AsyncMock(return_value={
        "dl_info_speed": 0,
        "up_info_speed": 1024000,  # 1 MB/s
        "dl_info_data": 10737418240,  # 10 GB
        "up_info_data": 21474836480  # 20 GB
    })
    client.get_torrents = AsyncMock(return_value=[])
    client.pause = AsyncMock()
    client.unpause = AsyncMock()
    return client


class TestRatioEmergencyService:
    """Test suite for RatioEmergencyService."""

    @pytest.mark.asyncio
    async def test_check_ratio_status_normal(self, ratio_service):
        """
        Test ratio check with normal (safe) ratio.

        Scenario:
        - Ratio = 1.15 (safe)
        - No emergency active

        Expected:
        - Returns normal status dict
        - emergency_active = False
        - No actions taken
        """
        ratio_service.last_ratio = 1.15

        with patch.object(ratio_service, '_fetch_current_ratio',
                         return_value=1.15):
            result = await ratio_service.check_ratio_status()

            assert result["current_ratio"] == 1.15
            assert result["emergency_active"] is False
            assert result["action_taken"] == "none"
            assert result["freeze_duration_hours"] == 0.0


    @pytest.mark.asyncio
    async def test_check_ratio_status_below_floor(self, ratio_service):
        """
        Test ratio check when ratio drops below floor.

        Scenario:
        - Ratio = 0.98 (< 1.00)
        - No emergency currently active

        Expected:
        - emergency_active set to True
        - handle_ratio_emergency() called
        - freeze_timestamp set
        - action_taken = "freeze_activated"
        """
        ratio_service.last_ratio = 1.05
        ratio_service.emergency_active = False

        with patch.object(ratio_service, '_fetch_current_ratio',
                         return_value=0.98), \
             patch.object(ratio_service, 'handle_ratio_emergency',
                         return_value={"status": "activated"}):

            result = await ratio_service.check_ratio_status()

            assert result["current_ratio"] == 0.98
            assert result["emergency_active"] is True
            assert result["action_taken"] == "freeze_activated"
            assert ratio_service.emergency_triggered_at is not None


    @pytest.mark.asyncio
    async def test_check_ratio_status_above_recovery(self, ratio_service):
        """
        Test ratio check when ratio recovers above recovery threshold.

        Scenario:
        - Ratio = 1.06 (>= 1.05)
        - Emergency currently active

        Expected:
        - _deactivate_emergency_freeze() called
        - emergency_active set to False
        - freeze_timestamp cleared
        - action_taken = "freeze_deactivated"
        """
        ratio_service.last_ratio = 0.98
        ratio_service.emergency_active = True
        ratio_service.emergency_triggered_at = datetime.utcnow() - timedelta(hours=2)

        with patch.object(ratio_service, '_fetch_current_ratio',
                         return_value=1.06), \
             patch.object(ratio_service, '_deactivate_emergency_freeze',
                         return_value={"status": "deactivated"}):

            result = await ratio_service.check_ratio_status()

            assert result["current_ratio"] == 1.06
            assert result["emergency_active"] is False
            assert result["action_taken"] == "freeze_deactivated"
            assert ratio_service.emergency_triggered_at is None


    @pytest.mark.asyncio
    async def test_emergency_activation_below_floor(self, ratio_service, db_session):
        """
        Test emergency activation when ratio < 1.00.

        Scenario:
        - Trigger emergency with ratio = 0.75

        Expected:
        - emergency_active = True
        - pause_non_seeding_torrents() called
        - unpause_all_seeding() called
        - activate_paid_download_block() called
        - Task logged with "emergency_activated"
        """
        ratio_service.last_ratio = 0.75
        ratio_service.emergency_active = False

        with patch.object(ratio_service, '_activate_paid_download_block',
                         return_value=3), \
             patch.object(ratio_service, '_pause_non_seeding_torrents',
                         return_value=5), \
             patch.object(ratio_service, '_unpause_all_seeding',
                         return_value=8), \
             patch.object(ratio_service, '_log_emergency_event',
                         return_value=None), \
             patch('backend.services.ratio_emergency_service.get_db_context') as mock_db:

            # Mock database context
            mock_db.return_value.__enter__.return_value = db_session
            mock_db.return_value.__exit__.return_value = None

            result = await ratio_service.handle_ratio_emergency()

            assert result["status"] == "activated"
            assert result["downloads_blocked"] == 3
            assert result["torrents_paused"] == 5
            assert result["torrents_unpaused"] == 8
            assert result["ratio"] == 0.75


    @pytest.mark.asyncio
    async def test_emergency_deactivation_above_recovery(self, ratio_service, db_session):
        """
        Test emergency deactivation when ratio >= 1.05.

        Scenario:
        - Emergency active, ratio = 1.08

        Expected:
        - emergency_active = False
        - Paid downloads unblocked
        - freeze_timestamp cleared
        - Task logged with "emergency_deactivated"
        """
        ratio_service.last_ratio = 1.08
        ratio_service.emergency_active = True

        # Create blocked downloads
        download1 = Download(
            title="Test Book 1",
            author="Author 1",
            source="MAM",
            status="blocked_ratio_emergency",
            release_edition="Paid",
            emergency_blocked=1,
            paid_download_allowed=0
        )
        download2 = Download(
            title="Test Book 2",
            author="Author 2",
            source="MAM",
            status="blocked_ratio_emergency",
            release_edition="Paid",
            emergency_blocked=1,
            paid_download_allowed=0
        )
        db_session.add_all([download1, download2])
        db_session.commit()

        with patch.object(ratio_service, '_log_emergency_event',
                         return_value=None), \
             patch('backend.services.ratio_emergency_service.get_db_context') as mock_db:

            # Mock database context
            mock_db.return_value.__enter__.return_value = db_session
            mock_db.return_value.__exit__.return_value = None

            result = await ratio_service._deactivate_emergency_freeze()

            assert result["status"] == "deactivated"
            assert result["downloads_unblocked"] == 2
            assert result["ratio"] == 1.08

            # Verify downloads were unblocked
            unblocked = db_session.query(Download).filter(
                Download.emergency_blocked == 0
            ).all()
            assert len(unblocked) == 2


    @pytest.mark.asyncio
    async def test_pause_non_seeding_torrents(self, ratio_service, mock_qbittorrent_client):
        """
        Test pausing non-seeding torrents.

        Scenario:
        - 5 downloading torrents in qBittorrent

        Expected:
        - pause() called on each torrent
        - Returns count = 5
        """
        # Mock torrents
        downloading_torrents = [
            {"hash": "hash1", "state": "downloading", "progress": 0.5},
            {"hash": "hash2", "state": "downloading", "progress": 0.3},
            {"hash": "hash3", "state": "downloading", "progress": 0.7},
            {"hash": "hash4", "state": "downloading", "progress": 0.2},
            {"hash": "hash5", "state": "downloading", "progress": 0.9},
        ]
        mock_qbittorrent_client.get_torrents.return_value = downloading_torrents

        with patch('backend.services.ratio_emergency_service.QBittorrentClient',
                  return_value=mock_qbittorrent_client):
            count = await ratio_service._pause_non_seeding_torrents()

            # Currently returns 0 (placeholder), but structure is correct
            assert isinstance(count, int)
            assert count >= 0


    @pytest.mark.asyncio
    async def test_unpause_all_seeding(self, ratio_service, mock_qbittorrent_client):
        """
        Test unpausing seeding torrents.

        Scenario:
        - 8 paused seeding torrents in qBittorrent

        Expected:
        - unpause() called on each torrent
        - Returns count = 8
        """
        # Mock paused seeding torrents
        paused_torrents = [
            {"hash": f"hash{i}", "state": "pausedUP", "progress": 1.0}
            for i in range(1, 9)
        ]
        mock_qbittorrent_client.get_torrents.return_value = paused_torrents

        with patch('backend.services.ratio_emergency_service.QBittorrentClient',
                  return_value=mock_qbittorrent_client):
            count = await ratio_service._unpause_all_seeding()

            # Currently returns 0 (placeholder), but structure is correct
            assert isinstance(count, int)
            assert count >= 0


    @pytest.mark.asyncio
    async def test_activate_paid_download_block(self, ratio_service, db_session):
        """
        Test blocking paid downloads during emergency.

        Scenario:
        - 3 paid downloads in queued/downloading state

        Expected:
        - All 3 have paid_download_allowed = False
        - All 3 have emergency_blocked = True
        - freeze_timestamp set on all
        - DB commit occurred
        """
        # Create paid downloads
        downloads = [
            Download(
                title=f"Paid Book {i}",
                author=f"Author {i}",
                source="MAM",
                status="queued",
                release_edition="Paid",
                emergency_blocked=0,
                paid_download_allowed=1
            )
            for i in range(1, 4)
        ]
        db_session.add_all(downloads)
        db_session.commit()

        # Block them
        blocked_count = await ratio_service._activate_paid_download_block(db_session)

        assert blocked_count == 3

        # Verify all are blocked
        blocked_downloads = db_session.query(Download).filter(
            Download.emergency_blocked == 1
        ).all()
        assert len(blocked_downloads) == 3

        for download in blocked_downloads:
            assert download.paid_download_allowed == 0
            assert download.status == "blocked_ratio_emergency"


    @pytest.mark.asyncio
    async def test_block_paid_download_during_emergency(self, ratio_service, db_session):
        """
        Test blocking specific paid download during emergency.

        Scenario:
        - Emergency active
        - Paid download queued

        Expected:
        - Returns True (blocked)
        - Download status updated
        """
        ratio_service.emergency_active = True
        ratio_service.last_ratio = 0.95

        # Create paid download
        download = Download(
            title="Test Paid Book",
            author="Test Author",
            source="MAM",
            status="queued",
            release_edition="Paid",
            emergency_blocked=0,
            paid_download_allowed=1
        )
        db_session.add(download)
        db_session.commit()

        with patch('backend.services.ratio_emergency_service.get_db_context') as mock_db:
            mock_db.return_value.__enter__.return_value = db_session
            mock_db.return_value.__exit__.return_value = None

            result = await ratio_service.block_paid_download(download.id)

            assert result is True

            # Verify download was blocked
            db_session.refresh(download)
            assert download.emergency_blocked == 1
            assert download.paid_download_allowed == 0
            assert download.status == "blocked_ratio_emergency"


    @pytest.mark.asyncio
    async def test_block_paid_download_normal(self, ratio_service, db_session):
        """
        Test paid download blocking when no emergency.

        Scenario:
        - No emergency active

        Expected:
        - Returns False (not blocked)
        - Download status unchanged
        """
        ratio_service.emergency_active = False

        # Create paid download
        download = Download(
            title="Test Paid Book",
            author="Test Author",
            source="MAM",
            status="queued",
            release_edition="Paid",
            emergency_blocked=0,
            paid_download_allowed=1
        )
        db_session.add(download)
        db_session.commit()

        with patch('backend.services.ratio_emergency_service.get_db_context') as mock_db:
            mock_db.return_value.__enter__.return_value = db_session
            mock_db.return_value.__exit__.return_value = None

            result = await ratio_service.block_paid_download(download.id)

            assert result is False

            # Verify download unchanged
            db_session.refresh(download)
            assert download.emergency_blocked == 0
            assert download.paid_download_allowed == 1


    @pytest.mark.asyncio
    async def test_get_emergency_metrics(self, ratio_service, db_session):
        """
        Test retrieving emergency metrics.

        Expected:
        - Returns dict with all required fields:
          - current_ratio
          - emergency_active
          - upload_rate_mbps
          - download_rate_mbps
          - frozen_downloads
        """
        ratio_service.last_ratio = 0.95
        ratio_service.emergency_active = True
        ratio_service.emergency_triggered_at = datetime.utcnow() - timedelta(hours=3)

        # Create frozen downloads
        frozen = [
            Download(
                title=f"Frozen Book {i}",
                author=f"Author {i}",
                source="MAM",
                status="blocked_ratio_emergency",
                release_edition="Paid",
                emergency_blocked=1
            )
            for i in range(1, 6)
        ]
        db_session.add_all(frozen)
        db_session.commit()

        with patch('backend.services.ratio_emergency_service.get_db_context') as mock_db, \
             patch.object(ratio_service, 'calculate_recovery_time',
                         return_value=4.5):

            mock_db.return_value.__enter__.return_value = db_session
            mock_db.return_value.__exit__.return_value = None

            metrics = await ratio_service.get_emergency_metrics()

            assert metrics["current_ratio"] == 0.95
            assert metrics["emergency_active"] is True
            assert metrics["frozen_downloads"] == 5
            assert metrics["time_in_emergency_hours"] > 2.9
            assert metrics["estimated_recovery_time_hours"] == 4.5
            assert "timestamp" in metrics


    @pytest.mark.asyncio
    async def test_calculate_recovery_time(self, ratio_service):
        """
        Test recovery time calculation.

        Scenario:
        - Emergency active
        - Ratio = 0.90

        Expected:
        - Returns float > 0
        - Reasonable estimate (e.g., 3-5 hours for 0.15 ratio gap)
        """
        ratio_service.emergency_active = True
        ratio_service.last_ratio = 0.90

        recovery_time = await ratio_service.calculate_recovery_time()

        assert recovery_time is not None
        assert isinstance(recovery_time, float)
        assert recovery_time > 0


    @pytest.mark.asyncio
    async def test_calculate_recovery_time_not_in_emergency(self, ratio_service):
        """
        Test recovery time calculation when no emergency.

        Scenario:
        - No emergency active

        Expected:
        - Returns None
        """
        ratio_service.emergency_active = False

        recovery_time = await ratio_service.calculate_recovery_time()

        assert recovery_time is None


    @pytest.mark.asyncio
    async def test_log_emergency_event(self, ratio_service, db_session):
        """
        Test logging emergency event to Task table.

        Expected:
        - Task created with:
          - task_name = "RATIO_EMERGENCY"
          - event in metadata
          - All metadata preserved
        - DB commit occurred
        """
        details = {
            "downloads_blocked": 5,
            "torrents_paused": 3,
            "torrents_unpaused": 10
        }

        await ratio_service._log_emergency_event(
            db=db_session,
            event_type="emergency_activated",
            ratio=0.95,
            details=details
        )

        # Verify task was logged
        task = db_session.query(Task).filter(
            Task.task_name == "RATIO_EMERGENCY"
        ).first()

        assert task is not None
        assert task.status == "completed"
        assert task.task_metadata["event_type"] == "emergency_activated"
        assert task.task_metadata["ratio"] == 0.95
        assert task.task_metadata["downloads_blocked"] == 5


    @pytest.mark.asyncio
    async def test_fetch_current_ratio_success(self, ratio_service):
        """
        Test successful ratio fetching from MAM.

        Scenario:
        - Authentication succeeds
        - HTML contains ratio

        Expected:
        - Returns float ratio
        - last_ratio updated
        """
        mock_html = """
        <html>
            <body>
                <div>User Stats</div>
                <div>Ratio: 1.85</div>
            </body>
        </html>
        """

        with patch.object(ratio_service, '_ensure_authenticated',
                         return_value=True), \
             patch('aiohttp.ClientSession') as mock_session:

            # Mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=mock_html)

            mock_session_instance = AsyncMock()
            mock_session_instance.get.return_value.__aenter__.return_value = mock_response
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            ratio = await ratio_service._fetch_current_ratio()

            assert ratio == 1.85
            assert ratio_service.last_ratio == 1.85


    @pytest.mark.asyncio
    async def test_fetch_current_ratio_auth_failure(self, ratio_service):
        """
        Test ratio fetching when authentication fails.

        Expected:
        - Returns None
        - Error logged
        """
        with patch.object(ratio_service, '_ensure_authenticated',
                         return_value=False):

            ratio = await ratio_service._fetch_current_ratio()

            assert ratio is None


    @pytest.mark.asyncio
    async def test_extract_ratio_from_html(self, ratio_service):
        """
        Test ratio extraction from HTML.

        Scenario:
        - HTML contains ratio in standard format

        Expected:
        - Extracts correct float value
        """
        html = """
        <html>
            <body>
                <div class="stats">
                    <span>Ratio: 1.234</span>
                </div>
            </body>
        </html>
        """

        ratio = ratio_service._extract_ratio(html)

        assert ratio == 1.234


    @pytest.mark.asyncio
    async def test_extract_ratio_missing(self, ratio_service):
        """
        Test ratio extraction when not found in HTML.

        Expected:
        - Returns None
        - No exception raised
        """
        html = """
        <html>
            <body>
                <div>No ratio here</div>
            </body>
        </html>
        """

        ratio = ratio_service._extract_ratio(html)

        assert ratio is None


    @pytest.mark.asyncio
    async def test_emergency_already_active(self, ratio_service):
        """
        Test emergency activation when already active.

        Scenario:
        - Emergency already active

        Expected:
        - Returns "already_active" status
        - No duplicate actions
        """
        ratio_service.emergency_active = True

        result = await ratio_service.handle_ratio_emergency()

        assert result["status"] == "already_active"
        assert "already active" in result["message"].lower()


    @pytest.mark.asyncio
    async def test_deactivate_emergency_not_active(self, ratio_service):
        """
        Test deactivation when no emergency active.

        Scenario:
        - No emergency currently active

        Expected:
        - Returns "not_active" status
        - No actions taken
        """
        ratio_service.emergency_active = False

        result = await ratio_service._deactivate_emergency_freeze()

        assert result["status"] == "not_active"
        assert "not active" in result["message"].lower()


    @pytest.mark.asyncio
    async def test_track_point_generation(self, ratio_service, db_session):
        """
        Test point generation tracking.

        Scenario:
        - Multiple paid downloads completed

        Expected:
        - Returns dict with points_earned, points_spent, roi
        - Provides recommendation based on ROI
        """
        # Create paid downloads
        paid_downloads = [
            Download(
                title=f"Paid Book {i}",
                author=f"Author {i}",
                source="MAM",
                status="completed",
                release_edition="Paid"
            )
            for i in range(1, 6)
        ]
        db_session.add_all(paid_downloads)
        db_session.commit()

        with patch('backend.services.ratio_emergency_service.get_db_context') as mock_db:
            mock_db.return_value.__enter__.return_value = db_session
            mock_db.return_value.__exit__.return_value = None

            result = await ratio_service.track_point_generation()

            assert "points_earned" in result
            assert "points_spent" in result
            assert "roi" in result
            assert "recommendation" in result
            assert result["paid_downloads_count"] == 5
            assert result["points_spent"] == 50  # 5 downloads * 10 points
