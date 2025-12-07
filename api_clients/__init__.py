"""
API Client Implementations

Provides specialized API client implementations for different protocols and services:
- REST API clients
- GraphQL API clients
- WebSocket clients
- Web scraping clients
- Service-specific clients (Audiobookshelf, qBittorrent, etc.)

Author: Agent 10 - API Client Consolidation Specialist
"""

from .rest_client import RESTAPIClient
from .graphql_client import GraphQLAPIClient
from .websocket_client import WebSocketAPIClient
from .scraper_client import ScraperAPIClient
from .audiobookshelf_client import AudiobookshelfAPIClient
from .qbittorrent_client import QBittorrentAPIClient
from .prowlarr_client import ProwlarrAPIClient
from .mam_client import MAMAPIClient

__all__ = [
    'RESTAPIClient',
    'GraphQLAPIClient',
    'WebSocketAPIClient',
    'ScraperAPIClient',
    'AudiobookshelfAPIClient',
    'QBittorrentAPIClient',
    'ProwlarrAPIClient',
    'MAMAPIClient',
]