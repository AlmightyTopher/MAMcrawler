"""
Backend Integration Clients

This package provides async API clients for external services used in the
audiobook management system.

Available Clients:
- AudiobookshelfClient: Manage audiobook library (import, metadata, search)
- QBittorrentClient: Control torrent downloads
- ProwlarrClient: Search torrent indexers
- GoogleBooksClient: Enrich metadata from Google Books API

Example:
    >>> from backend.integrations import (
    ...     AudiobookshelfClient,
    ...     QBittorrentClient,
    ...     ProwlarrClient,
    ...     GoogleBooksClient
    ... )
    >>>
    >>> # Use with async context managers
    >>> async with AudiobookshelfClient(url, token) as abs_client:
    ...     books = await abs_client.get_library_items()
    >>>
    >>> async with QBittorrentClient(url, user, password) as qb_client:
    ...     await qb_client.add_torrent(magnet_link)
"""

from .abs_client import AudiobookshelfClient, AudiobookshelfError
from .qbittorrent_client import (
    QBittorrentClient,
    QBittorrentError,
    QBittorrentAuthError,
)
from .prowlarr_client import ProwlarrClient, ProwlarrError
from .google_books_client import (
    GoogleBooksClient,
    GoogleBooksError,
    GoogleBooksRateLimitError,
)

__all__ = [
    # Audiobookshelf
    "AudiobookshelfClient",
    "AudiobookshelfError",
    # qBittorrent
    "QBittorrentClient",
    "QBittorrentError",
    "QBittorrentAuthError",
    # Prowlarr
    "ProwlarrClient",
    "ProwlarrError",
    # Google Books
    "GoogleBooksClient",
    "GoogleBooksError",
    "GoogleBooksRateLimitError",
]

__version__ = "1.0.0"
