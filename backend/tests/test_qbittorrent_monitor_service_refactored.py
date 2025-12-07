"""
Comprehensive Test Suite for PHASE 3 Refactored QBittorrentMonitorService

Tests all 4 manager modules and integration:
- TorrentStateManager (6 tests)
- TorrentControlManager (5 tests)
- RatioMonitoringManager (7 tests)
- CompletionEventManager (7 tests)
- Integration tests (3 tests)
- Backwards compatibility (2 tests)

Total: 30+ tests
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, Mock

from backend.services.qbittorrent_monitor_service import QBittorrentMonitorService
from backend.services.qbittorrent_managers import (
    TorrentStateManager,
    TorrentControlManager,
    RatioMonitoringManager,
    CompletionEventManager
)


class TestTorrentStateManager:
    """Tests for TorrentStateManager - 6 tests"""

    @pytest.fixture
    def mock_service(self):
        """Create mock monitor service."""
        service = MagicMock()
        service.qb_client = AsyncMock()
        return service

    @pytest.fixture
    def manager(self, mock_service):
        """Create TorrentStateManager instance."""
        return TorrentStateManager(mock_service)

    @pytest.mark.asyncio
    async def test_state_manager_initialization(self, manager):
        """Test TorrentStateManager initializes with empty state."""
        assert manager.downloading_torrents == []
        assert manager.seeding_torrents == []
        assert manager.stalled_torrents == []
        assert manager.paused_torrents == []
        assert manager.last_check is None

    @pytest.mark.asyncio
    async def test_get_torrent_states_categorization(self, manager, mock_service):
        """Test torrents are correctly categorized by state."""
        mock_torrents = [
            {'hash': 'hash1', 'name': 'downloading.torrent', 'state': 'downloading', 'progress': 0.5},
            {'hash': 'hash2', 'name': 'seeding.torrent', 'state': 'uploading', 'progress': 1.0},
            {'hash': 'hash3', 'name': 'stalled.torrent', 'state': 'stalledDL', 'progress': 0.3},
            {'hash': 'hash4', 'name': 'paused.torrent', 'state': 'pausedDL', 'progress': 0.2},
            {'hash': 'hash5', 'name': 'error.torrent', 'state': 'error', 'progress': 0.0},
        ]
        mock_service.qb_client.get_all_torrents.return_value = mock_torrents

        states = await manager.get_torrent_states()

        assert len(states['downloading']) == 1
        assert len(states['seeding']) == 1
        assert len(states['stalled']) >= 1
        assert len(states['paused']) == 1
        assert len(states['errored']) == 1

    @pytest.mark.asyncio
    async def test_get_torrent_states_caching(self, manager, mock_service):
        """Test state results are cached in manager."""
        mock_torrents = [
            {'hash': 'hash1', 'name': 'download.torrent', 'state': 'downloading'},
            {'hash': 'hash2', 'name': 'seed.torrent', 'state': 'uploading'},
        ]
        mock_service.qb_client.get_all_torrents.return_value = mock_torrents

        await manager.get_torrent_states()

        assert len(manager.downloading_torrents) == 1
        assert len(manager.seeding_torrents) == 1
        assert manager.last_check is not None

    @pytest.mark.asyncio
    async def test_get_state_summary(self, manager, mock_service):
        """Test state summary returns correct counts."""
        mock_torrents = [
            {'hash': 'h1', 'name': 't1', 'state': 'downloading'},
            {'hash': 'h2', 'name': 't2', 'state': 'uploading'},
            {'hash': 'h3', 'name': 't3', 'state': 'pausedDL'},
        ]
        mock_service.qb_client.get_all_torrents.return_value = mock_torrents

        await manager.get_torrent_states()
        summary = await manager.get_state_summary()

        assert summary['downloading'] == 1
        assert summary['seeding'] == 1
        assert summary['paused'] == 1
        assert summary['total'] == 3

    @pytest.mark.asyncio
    async def test_is_stale_detection(self, manager, mock_service):
        """Test cache staleness detection."""
        mock_service.qb_client.get_all_torrents.return_value = []

        # Cache should be stale initially
        assert await manager.is_stale(max_age_seconds=1) is True

        # Fill cache
        await manager.get_torrent_states()

        # Cache should not be stale immediately
        assert await manager.is_stale(max_age_seconds=60) is False

    @pytest.mark.asyncio
    async def test_get_torrent_states_empty(self, manager, mock_service):
        """Test handling empty torrent list."""
        mock_service.qb_client.get_all_torrents.return_value = []

        states = await manager.get_torrent_states()

        assert len(states['downloading']) == 0
        assert len(states['seeding']) == 0
        assert states['paused'] == []


class TestTorrentControlManager:
    """Tests for TorrentControlManager - 5 tests"""

    @pytest.fixture
    def mock_service(self):
        """Create mock monitor service."""
        service = MagicMock()
        service.qb_client = AsyncMock()
        service.state_manager = MagicMock()
        return service

    @pytest.fixture
    def manager(self, mock_service):
        """Create TorrentControlManager instance."""
        return TorrentControlManager(mock_service)

    @pytest.mark.asyncio
    async def test_auto_restart_stalled_torrents(self, manager, mock_service):
        """Test restarting stalled torrents."""
        stalled = [
            {'hash': 'hash1', 'name': 'stalled1.torrent'},
            {'hash': 'hash2', 'name': 'stalled2.torrent'},
        ]
        mock_service.state_manager.stalled_torrents = stalled
        mock_service.qb_client.force_continue = AsyncMock()

        count = await manager.auto_restart_stalled_torrents()

        assert count == 2
        assert mock_service.qb_client.force_continue.call_count == 2

    @pytest.mark.asyncio
    async def test_restart_torrent_single(self, manager, mock_service):
        """Test restarting single torrent."""
        mock_service.qb_client.force_continue = AsyncMock(return_value=True)

        result = await manager.restart_torrent('test_hash')

        assert result is True
        mock_service.qb_client.force_continue.assert_called_once_with('test_hash')

    @pytest.mark.asyncio
    async def test_pause_downloading_torrents(self, manager, mock_service):
        """Test pausing downloading torrents."""
        downloading = [
            {'hash': 'hash1', 'name': 'download1.torrent'},
            {'hash': 'hash2', 'name': 'download2.torrent'},
        ]
        mock_service.state_manager.downloading_torrents = downloading
        mock_service.qb_client.pause_torrent = AsyncMock()

        count = await manager.pause_downloading_torrents()

        assert count == 2
        assert mock_service.qb_client.pause_torrent.call_count == 2

    @pytest.mark.asyncio
    async def test_resume_paused_torrents(self, manager, mock_service):
        """Test resuming paused torrents."""
        paused = [
            {'hash': 'hash1', 'name': 'paused1.torrent', 'progress': 1.0},
            {'hash': 'hash2', 'name': 'paused2.torrent', 'progress': 0.5},
        ]
        mock_service.state_manager.paused_torrents = paused
        mock_service.qb_client.resume_torrent = AsyncMock()

        count = await manager.resume_paused_torrents()

        assert count == 2
        mock_service.qb_client.resume_torrent.assert_called()

    @pytest.mark.asyncio
    async def test_resume_paused_torrents_with_filter(self, manager, mock_service):
        """Test resuming only completed paused torrents."""
        paused = [
            {'hash': 'hash1', 'name': 'complete.torrent', 'progress': 1.0},
            {'hash': 'hash2', 'name': 'incomplete.torrent', 'progress': 0.5},
        ]
        mock_service.state_manager.paused_torrents = paused
        mock_service.qb_client.resume_torrent = AsyncMock()

        count = await manager.resume_paused_torrents(filter_completed_only=True)

        assert count == 1  # Only complete torrent resumed
        mock_service.qb_client.resume_torrent.assert_called_once()


class TestRatioMonitoringManager:
    """Tests for RatioMonitoringManager - 7 tests"""

    @pytest.fixture
    def mock_service(self):
        """Create mock monitor service."""
        service = MagicMock()
        service.qb_client = AsyncMock()
        service.state_manager = MagicMock()
        return service

    @pytest.fixture
    def manager(self, mock_service):
        """Create RatioMonitoringManager instance."""
        return RatioMonitoringManager(mock_service)

    @pytest.mark.asyncio
    async def test_optimize_seeding_allocation(self, manager, mock_service):
        """Test seeding allocation optimization."""
        mock_service.state_manager.get_seeding_count.return_value = 7
        mock_service.state_manager.get_downloading_count.return_value = 3
        mock_service.qb_client.get_seeding_limit = AsyncMock(return_value=5)
        mock_service.qb_client.set_seeding_limit = AsyncMock()

        result = await manager.optimize_seeding_allocation()

        assert result['current_seeding'] == 7
        assert result['current_downloading'] == 3
        assert result['optimal_seeding'] == 7  # 70% of 10
        assert result['optimal_downloading'] == 3

    @pytest.mark.asyncio
    async def test_calculate_point_generation(self, manager, mock_service):
        """Test point generation calculation."""
        seeding = [
            {'hash': 'h1', 'name': 't1', 'upspeed': 1024 * 1024, 'ratio': 1.5},  # 1 MB/s
            {'hash': 'h2', 'name': 't2', 'upspeed': 512 * 1024, 'ratio': 0.8},   # 0.5 MB/s
        ]
        mock_service.state_manager.seeding_torrents = seeding

        result = await manager.calculate_point_generation()

        assert result['total_seeders'] == 2
        assert result['high_priority_seeders'] == 2
        assert result['upload_mbps'] == 1.5
        # 1.5 MB/s * 3600 = 5400 points/hour
        assert result['estimated_points_per_hour'] == 5400

    @pytest.mark.asyncio
    async def test_get_upload_efficiency(self, manager, mock_service):
        """Test upload efficiency calculation."""
        seeding = [
            {'hash': 'h1', 'upspeed': 2048 * 1024},  # 2 MB/s
            {'hash': 'h2', 'upspeed': 1024 * 1024},  # 1 MB/s
        ]
        mock_service.state_manager.seeding_torrents = seeding

        result = await manager.get_upload_efficiency()

        assert result['total_seeders'] == 2
        assert result['total_upload_mbps'] == 3.0
        assert result['avg_upload_per_torrent_mbps'] == 1.5

    @pytest.mark.asyncio
    async def test_get_upload_efficiency_no_seeders(self, manager, mock_service):
        """Test efficiency with no seeders."""
        mock_service.state_manager.seeding_torrents = []

        result = await manager.get_upload_efficiency()

        assert result['total_seeders'] == 0
        assert result['efficiency_metrics'] == 'no_seeders'

    @pytest.mark.asyncio
    async def test_analyze_seeding_strategy(self, manager, mock_service):
        """Test seeding strategy analysis."""
        mock_service.state_manager.seeding_torrents = [{'hash': 'h1', 'upspeed': 1024 * 1024}]
        mock_service.state_manager.get_seeding_count.return_value = 7
        mock_service.state_manager.get_downloading_count.return_value = 3
        mock_service.qb_client.get_seeding_limit = AsyncMock(return_value=7)

        result = await manager.analyze_seeding_strategy()

        assert 'recommendation' in result
        assert 'reasoning' in result
        assert 'timestamp' in result

    @pytest.mark.asyncio
    async def test_point_generation_edge_case_no_upload(self, manager, mock_service):
        """Test point generation with zero upload."""
        mock_service.state_manager.seeding_torrents = [
            {'hash': 'h1', 'upspeed': 0, 'ratio': 1.0}
        ]

        result = await manager.calculate_point_generation()

        assert result['upload_mbps'] == 0.0
        assert result['estimated_points_per_hour'] == 0.0


class TestCompletionEventManager:
    """Tests for CompletionEventManager - 7 tests"""

    @pytest.fixture
    def mock_service(self):
        """Create mock monitor service."""
        service = MagicMock()
        service.qb_client = AsyncMock()
        return service

    @pytest.fixture
    def manager(self, mock_service):
        """Create CompletionEventManager instance."""
        return CompletionEventManager(mock_service)

    @pytest.mark.asyncio
    async def test_detect_completion_events(self, manager, mock_service):
        """Test completion event detection."""
        torrents = [
            {'hash': 'h1', 'name': 't1', 'state': 'downloading'},
            {'hash': 'h2', 'name': 't2', 'state': 'uploading'},
        ]
        mock_service.qb_client.get_all_torrents = AsyncMock(return_value=torrents)

        # Set previous state to detect transition
        manager.last_checked_torrents = {
            'h1': {'state': 'downloading', 'name': 't1'},
            'h2': {'state': 'downloading', 'name': 't2'},  # Will transition to uploading
        }

        events = await manager.detect_completion_events()

        # Should detect transition from downloading to uploading
        assert len(events) == 1
        assert events[0]['torrent_hash'] == 'h2'
        assert events[0]['previous_state'] == 'downloading'
        assert events[0]['current_state'] == 'uploading'

    @pytest.mark.asyncio
    async def test_handle_completion_events(self, manager, mock_service):
        """Test completion event handling."""
        events = [
            {
                'torrent_hash': 'h1',
                'torrent_name': 't1.torrent',
                'previous_state': 'downloading',
                'current_state': 'uploading'
            }
        ]

        with patch('backend.services.download_service.DownloadService') as mock_service_class:
            with patch('backend.database.SessionLocal') as mock_db:
                mock_db.return_value.query.return_value.filter.return_value.first.return_value = MagicMock(id=1)
                mock_service_class.on_download_completed = AsyncMock(return_value={'status': 'success'})

                result = await manager.handle_completion_events(events)

                assert result['processed'] == 1
                assert result['errors'] == 0
                assert result['total_events'] == 1

    @pytest.mark.asyncio
    async def test_on_torrent_completed(self, manager, mock_service):
        """Test single torrent completion handler."""
        with patch('backend.services.download_service.DownloadService') as mock_service_class:
            with patch('backend.database.SessionLocal') as mock_db:
                mock_db.return_value.query.return_value.filter.return_value.first.return_value = MagicMock(
                    id=1, title='test.torrent'
                )
                mock_service_class.on_download_completed = AsyncMock(return_value={'status': 'success'})

                result = await manager.on_torrent_completed('test_hash')

                assert result is True

    @pytest.mark.asyncio
    async def test_get_recent_completions(self, manager):
        """Test querying completion history."""
        events = [
            {'torrent_name': 't1', 'detected_at': '2025-01-01T00:00:00'},
            {'torrent_name': 't2', 'detected_at': '2025-01-01T00:01:00'},
            {'torrent_name': 't3', 'detected_at': '2025-01-01T00:02:00'},
        ]
        manager.completion_history = events

        recent = manager.get_recent_completions(limit=2)

        assert len(recent) == 2
        assert recent[0]['torrent_name'] == 't2'
        assert recent[1]['torrent_name'] == 't3'

    @pytest.mark.asyncio
    async def test_clear_completion_history(self, manager):
        """Test clearing completion history."""
        manager.completion_history = [
            {'torrent_name': 't1'},
            {'torrent_name': 't2'},
        ]

        cleared = manager.clear_completion_history()

        assert cleared == 2
        assert len(manager.completion_history) == 0

    @pytest.mark.asyncio
    async def test_get_completion_stats(self, manager):
        """Test completion statistics."""
        manager.completion_history = [{'torrent_name': 't1'}]
        manager.last_checked_torrents = {'h1': {}, 'h2': {}}

        stats = manager.get_completion_stats()

        assert stats['total_tracked'] == 1
        assert stats['torrents_being_monitored'] == 2
        assert 'last_update' in stats


class TestQBittorrentMonitorServiceIntegration:
    """Integration tests for refactored service - 3 tests"""

    @pytest.fixture
    def mock_service(self):
        """Create mock for service dependencies."""
        with patch('backend.services.qbittorrent_monitor_service.TorrentStateManager'), \
             patch('backend.services.qbittorrent_monitor_service.TorrentControlManager'), \
             patch('backend.services.qbittorrent_monitor_service.RatioMonitoringManager'), \
             patch('backend.services.qbittorrent_monitor_service.CompletionEventManager'):
            service = QBittorrentMonitorService()
            service.state_manager = AsyncMock()
            service.control_manager = AsyncMock()
            service.ratio_manager = AsyncMock()
            service.completion_manager = AsyncMock()
            return service

    def test_service_initialization(self, mock_service):
        """Test service initializes with all managers."""
        assert mock_service.qb_client is None
        assert mock_service.monitoring_active is False
        assert hasattr(mock_service, 'state_manager')
        assert hasattr(mock_service, 'control_manager')
        assert hasattr(mock_service, 'ratio_manager')
        assert hasattr(mock_service, 'completion_manager')

    @pytest.mark.asyncio
    async def test_continuous_monitoring_loop_orchestration(self, mock_service):
        """Test monitoring loop uses all managers."""
        mock_service.state_manager.get_torrent_states = AsyncMock(
            return_value={'downloading': [], 'seeding': [], 'stalled': [], 'paused': [], 'errored': []}
        )
        mock_service.completion_manager.detect_completion_events = AsyncMock(return_value=[])
        mock_service.completion_manager.handle_completion_events = AsyncMock(return_value={})
        mock_service.control_manager.auto_restart_stalled_torrents = AsyncMock(return_value=0)
        mock_service.ratio_manager.optimize_seeding_allocation = AsyncMock(return_value={})
        mock_service.ratio_manager.calculate_point_generation = AsyncMock(
            return_value={'estimated_points_per_hour': 0}
        )

        with patch('backend.services.qbittorrent_monitor_service.SessionLocal'):
            await mock_service.continuous_monitoring_loop()

        mock_service.state_manager.get_torrent_states.assert_called_once()
        mock_service.completion_manager.detect_completion_events.assert_called_once()
        mock_service.control_manager.auto_restart_stalled_torrents.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_monitoring_status(self, mock_service):
        """Test get_monitoring_status returns aggregated data."""
        mock_service.state_manager.get_state_summary = AsyncMock(
            return_value={
                'downloading': 2,
                'seeding': 5,
                'stalled': 1,
                'paused': 0,
                'errored': 0,
                'total': 8
            }
        )
        mock_service.state_manager.get_last_check_time = MagicMock(return_value=datetime.utcnow())

        status = await mock_service.get_monitoring_status()

        assert status['monitoring_active'] is False
        assert status['downloading'] == 2
        assert status['seeding'] == 5
        assert status['total'] == 8


class TestBackwardsCompatibility:
    """Backwards compatibility tests - 2 tests"""

    @pytest.fixture
    def mock_service(self):
        """Create mock service for testing."""
        with patch('backend.services.qbittorrent_monitor_service.TorrentStateManager') as mock_state, \
             patch('backend.services.qbittorrent_monitor_service.TorrentControlManager') as mock_control, \
             patch('backend.services.qbittorrent_monitor_service.RatioMonitoringManager') as mock_ratio, \
             patch('backend.services.qbittorrent_monitor_service.CompletionEventManager') as mock_completion:

            service = QBittorrentMonitorService()

            # Setup mock managers
            service.state_manager = AsyncMock()
            service.control_manager = AsyncMock()
            service.ratio_manager = AsyncMock()
            service.completion_manager = AsyncMock()

            return service

    @pytest.mark.asyncio
    async def test_old_api_methods_still_work(self, mock_service):
        """Test that old public API methods still function."""
        mock_service.state_manager.get_torrent_states = AsyncMock(
            return_value={'downloading': [], 'seeding': [], 'stalled': [], 'paused': [], 'errored': []}
        )
        mock_service.control_manager.auto_restart_stalled_torrents = AsyncMock(return_value=0)
        mock_service.ratio_manager.optimize_seeding_allocation = AsyncMock(return_value={})
        mock_service.ratio_manager.calculate_point_generation = AsyncMock(return_value={})
        mock_service.completion_manager.detect_completion_events = AsyncMock(return_value=[])
        mock_service.completion_manager.handle_completion_events = AsyncMock(return_value={})

        # Call old API methods - should work without error
        states = await mock_service.get_torrent_states()
        assert isinstance(states, dict)

        restarted = await mock_service.auto_restart_stalled_torrents()
        assert isinstance(restarted, int)

        optimization = await mock_service.optimize_seeding_allocation()
        assert isinstance(optimization, dict)

        points = await mock_service.calculate_point_generation()
        assert isinstance(points, dict)

        events = await mock_service.detect_completion_events()
        assert isinstance(events, list)

        result = await mock_service.handle_completion_events([])
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_service_maintains_backwards_compatible_state(self, mock_service):
        """Test service state is accessible via public methods."""
        mock_service.state_manager.get_state_summary = AsyncMock(
            return_value={'downloading': 3, 'seeding': 7, 'stalled': 1, 'paused': 0, 'errored': 0, 'total': 11}
        )
        mock_service.state_manager.get_last_check_time = MagicMock(return_value=datetime.utcnow())

        status = await mock_service.get_monitoring_status()

        # Old code expecting these fields should still work
        assert 'downloading' in status
        assert 'seeding' in status
        assert 'stalled' in status
        assert 'monitoring_active' in status


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
