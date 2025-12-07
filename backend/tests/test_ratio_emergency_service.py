"""Comprehensive tests for RatioEmergencyService"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime, timedelta
from backend.services.ratio_emergency_service import RatioEmergencyService


class TestInitialization:
    """Test RatioEmergencyService initialization"""
    
    def test_init_with_db(self):
        """Test initialization with database session"""
        db_mock = MagicMock()
        service = RatioEmergencyService(db=db_mock)
        assert service.db == db_mock
        assert service.RATIO_FLOOR == 1.00
        assert service.emergency_active is False
        assert service.last_ratio == 1.0


class TestRatioStatusChecking:
    """Test ratio status checking"""
    
    @pytest.mark.asyncio
    async def test_check_ratio_normal(self):
        """Test ratio check when ratio is normal (above floor)"""
        service = RatioEmergencyService()
        with patch.object(service, "_fetch_current_ratio", return_value=1.5):
            result = await service.check_ratio_status()
            assert result["current_ratio"] == 1.5
            assert result["emergency_active"] is False
            assert result["action_taken"] == "none"

    @pytest.mark.asyncio
    async def test_check_ratio_emergency_trigger(self):
        """Test ratio check triggers emergency when ratio < floor"""
        service = RatioEmergencyService()
        with patch.object(service, "_fetch_current_ratio", return_value=0.85),              patch.object(service, "handle_ratio_emergency", return_value={"status": "activated"}):
            result = await service.check_ratio_status()
            assert result["emergency_active"] is True
            assert result["action_taken"] == "freeze_activated"


class TestTorrentOperations:
    """Test torrent pause/resume operations"""
    
    @pytest.mark.asyncio
    async def test_pause_torrents(self):
        """Test pausing downloading torrents"""
        service = RatioEmergencyService()
        qb_mock = AsyncMock()
        qb_mock.get_all_torrents = AsyncMock(return_value=[
            {"hash": "h1", "name": "T1", "state": "downloading"},
            {"hash": "h2", "name": "T2", "state": "downloading"},
        ])
        qb_mock.pause_torrent = AsyncMock()
        
        with patch("backend.integrations.qbittorrent_client.QBittorrentClient") as qb_class:
            qb_class.return_value.__aenter__ = AsyncMock(return_value=qb_mock)
            qb_class.return_value.__aexit__ = AsyncMock(return_value=None)
            count = await service._pause_non_seeding_torrents()
            assert count == 2


class TestRecoveryTime:
    """Test recovery time calculation"""
    
    @pytest.mark.asyncio
    async def test_recovery_no_emergency(self):
        """Test recovery time when emergency not active"""
        service = RatioEmergencyService()
        service.emergency_active = False
        result = await service.calculate_recovery_time()
        assert result is None

    @pytest.mark.asyncio
    async def test_recovery_already_recovered(self):
        """Test recovery time when already recovered"""
        service = RatioEmergencyService()
        service.emergency_active = True
        service.last_ratio = 1.08
        result = await service.calculate_recovery_time()
        assert result == 0.0


class TestPointGeneration:
    """Test point generation tracking"""
    
    @pytest.mark.asyncio
    async def test_track_points(self):
        """Test point generation and ROI tracking"""
        db_mock = MagicMock()
        service = RatioEmergencyService(db=db_mock)
        
        paid_downloads = [
            MagicMock(points_cost=10),
            MagicMock(points_cost=15),
            MagicMock(points_cost=None),
        ]
        db_mock.query.return_value.filter.return_value.all.return_value = paid_downloads
        
        qb_mock = AsyncMock()
        qb_mock.get_server_state = AsyncMock(return_value={
            "total_uploaded": 100 * 1024**3,
        })
        qb_mock.get_all_torrents = AsyncMock(return_value=[
            {"uploaded": 50 * 1024**3}
        ])
        
        with patch("backend.integrations.qbittorrent_client.QBittorrentClient") as qb_class,              patch("backend.services.ratio_emergency_service.get_db_context") as db_ctx:
            qb_class.return_value.__aenter__ = AsyncMock(return_value=qb_mock)
            qb_class.return_value.__aexit__ = AsyncMock(return_value=None)
            db_ctx.return_value.__enter__.return_value = db_mock
            db_ctx.return_value.__exit__.return_value = None
            
            result = await service.track_point_generation()
            
            assert result["points_earned"] == 100
            assert result["points_spent"] == 40
            assert result["roi"] > 2.0
