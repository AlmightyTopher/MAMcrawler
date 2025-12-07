"""
QBittorrent Manager Modules

Specialized manager classes for QBittorrentMonitorService decomposition.
Each manager handles a specific domain responsibility following single responsibility principle.
"""

from .torrent_state_manager import TorrentStateManager
from .torrent_control_manager import TorrentControlManager
from .ratio_monitoring_manager import RatioMonitoringManager
from .completion_event_manager import CompletionEventManager

__all__ = [
    'TorrentStateManager',
    'TorrentControlManager',
    'RatioMonitoringManager',
    'CompletionEventManager'
]
