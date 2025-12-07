"""
Audiobookshelf Client Manager Modules

Organizes AbsClient methods into focused, single-responsibility modules:
- LibraryManager: Book and library operations
- CollectionManager: Collection management
- PlaylistManager: Playlist operations
- ProgressManager: User progress and listening tracking
- UserManager: User profile and settings
- BackupManager: Backup operations
- NotificationManager: Notification management
- RSSManager: RSS feed management
- APIKeyManager: API key management
- EmailManager: Email operations

Usage:
    client = AudiobookshelfClient(base_url, token)
    client.libraries.get_library_items()
    client.collections.create_collection({...})
    client.playlists.get_playlists()
    # ... etc
"""

from backend.integrations.abs_managers.library_manager import LibraryManager
from backend.integrations.abs_managers.collection_manager import CollectionManager
from backend.integrations.abs_managers.playlist_manager import PlaylistManager
from backend.integrations.abs_managers.progress_manager import ProgressManager
from backend.integrations.abs_managers.user_manager import UserManager
from backend.integrations.abs_managers.backup_manager import BackupManager
from backend.integrations.abs_managers.notification_manager import NotificationManager
from backend.integrations.abs_managers.rss_manager import RSSManager
from backend.integrations.abs_managers.api_key_manager import APIKeyManager
from backend.integrations.abs_managers.email_manager import EmailManager

__all__ = [
    "LibraryManager",
    "CollectionManager",
    "PlaylistManager",
    "ProgressManager",
    "UserManager",
    "BackupManager",
    "NotificationManager",
    "RSSManager",
    "APIKeyManager",
    "EmailManager",
]
