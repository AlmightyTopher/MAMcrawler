#!/usr/bin/env python3
"""
qBittorrent Session-Based Client
=================================
Direct implementation using requests with proper session-based authentication
instead of the problematic qbittorrentapi library

The qbittorrentapi library tries to use basic HTTP auth, but qBittorrent
requires session-based auth (login to get cookie, then use cookie for API calls)
"""

import requests
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class QBittorrentSessionClient:
    """Direct qBittorrent API client using session-based authentication"""

    def __init__(self, host: str, username: str, password: str, timeout: int = 30):
        """
        Initialize qBittorrent client

        Args:
            host: qBittorrent URL (e.g., 'http://192.168.0.48:52095')
            username: Web UI username
            password: Web UI password
            timeout: Request timeout in seconds
        """
        self.host = host.rstrip('/')
        self.username = username
        self.password = password
        self.timeout = timeout
        self.session = requests.Session()
        self.authenticated = False

        logger.info(f"Initialized qBittorrent client for {self.host}")

    def login(self) -> bool:
        """
        Authenticate with qBittorrent API

        Returns:
            True if login successful, False otherwise
        """
        try:
            login_url = urljoin(self.host, '/api/v2/auth/login')

            response = self.session.post(
                login_url,
                data={
                    'username': self.username,
                    'password': self.password
                },
                timeout=self.timeout
            )

            if response.status_code == 200 and response.text == 'Ok.':
                self.authenticated = True
                logger.info(f"Logged into qBittorrent: {self.host}")
                logger.info(f"Session cookie: {self.session.cookies}")
                return True
            else:
                logger.error(f"Login failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    def add_torrent(self, magnet_link: str, category: str = "audiobooks") -> bool:
        """
        Add torrent to qBittorrent queue

        Args:
            magnet_link: Magnet link URI
            category: Category name (default: "audiobooks")

        Returns:
            True if successfully added, False otherwise
        """
        if not self.authenticated:
            logger.error("Not authenticated. Call login() first")
            return False

        try:
            add_url = urljoin(self.host, '/api/v2/torrents/add')

            response = self.session.post(
                add_url,
                data={
                    'urls': magnet_link,
                    'category': category,
                    'paused': False
                },
                timeout=self.timeout
            )

            if response.status_code == 200:
                logger.info(f"Added torrent: {magnet_link[:50]}... to {category}")
                return True
            else:
                logger.warning(f"Failed to add torrent (status {response.status_code}): {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error adding torrent: {e}")
            return False

    def get_torrents(self) -> List[Dict[str, Any]]:
        """
        Get list of all torrents in qBittorrent

        Returns:
            List of torrent dictionaries
        """
        if not self.authenticated:
            logger.error("Not authenticated. Call login() first")
            return []

        try:
            torrents_url = urljoin(self.host, '/api/v2/torrents/info')

            response = self.session.get(
                torrents_url,
                timeout=self.timeout
            )

            if response.status_code == 200:
                torrents = response.json()
                logger.info(f"Retrieved {len(torrents)} torrents from qBittorrent")
                return torrents
            else:
                logger.warning(f"Failed to get torrents (status {response.status_code})")
                return []

        except Exception as e:
            logger.error(f"Error getting torrents: {e}")
            return []

    def get_torrent_count(self) -> int:
        """Get total count of torrents"""
        return len(self.get_torrents())

    def get_api_version(self) -> str:
        """Get qBittorrent API version"""
        if not self.authenticated:
            logger.error("Not authenticated. Call login() first")
            return ""

        try:
            version_url = urljoin(self.host, '/api/v2/app/webapiVersion')

            response = self.session.get(
                version_url,
                timeout=self.timeout
            )

            if response.status_code == 200:
                version = response.text
                logger.info(f"qBittorrent API version: {version}")
                return version
            else:
                logger.warning(f"Failed to get API version")
                return ""

        except Exception as e:
            logger.error(f"Error getting API version: {e}")
            return ""

    def torrents_info(self) -> List[Dict[str, Any]]:
        """Compatibility method for qbittorrentapi interface - get list of torrents"""
        return self.get_torrents()

    def torrents_add(self, urls: str, category: str = "audiobooks", tags: List[str] = None, is_paused: bool = False) -> bool:
        """Compatibility method for qbittorrentapi interface - add torrent by magnet link"""
        if not self.authenticated:
            logger.error("Not authenticated. Call login() first")
            return False

        try:
            add_url = urljoin(self.host, '/api/v2/torrents/add')

            data = {
                'urls': urls,
                'category': category,
                'paused': is_paused
            }

            # Add tags if provided
            if tags:
                data['tags'] = ','.join(tags)

            response = self.session.post(
                add_url,
                data=data,
                timeout=self.timeout
            )

            if response.status_code == 200:
                logger.info(f"Added torrent: {urls[:50]}... to {category}")
                return True
            else:
                logger.warning(f"Failed to add torrent (status {response.status_code}): {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error adding torrent: {e}")
            return False

    def test_connection(self) -> bool:
        """
        Test connection to qBittorrent

        Returns:
            True if connection successful and authenticated, False otherwise
        """
        try:
            # Test login
            if not self.login():
                return False

            # Test API call
            version = self.get_api_version()
            if version:
                logger.info(f"Connection test successful: {version}")
                return True
            else:
                logger.error("Connection test failed: Could not get API version")
                return False

        except Exception as e:
            logger.error(f"Connection test error: {e}")
            return False

    def __enter__(self):
        """Context manager entry"""
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            self.session.close()


# Testing code
if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    import os

    load_dotenv()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Get configuration from environment
    qb_host = os.getenv('QB_HOST', 'http://192.168.0.48')
    qb_port = os.getenv('QB_PORT', '52095')
    qb_user = os.getenv('QB_USERNAME', 'TopherGutbrod')
    qb_pass = os.getenv('QB_PASSWORD', '')

    qb_url = f"{qb_host}:{qb_port}" if not qb_host.endswith(qb_port) else qb_host

    print("=" * 70)
    print("qBittorrent Session Client Test")
    print("=" * 70)
    print(f"Host: {qb_url}")
    print(f"User: {qb_user}")
    print()

    # Test client
    client = QBittorrentSessionClient(qb_url, qb_user, qb_pass)

    print("Test 1: Connection")
    print("-" * 70)
    if client.test_connection():
        print("SUCCESS - qBittorrent is accessible!")
    else:
        print("FAILED - Could not connect to qBittorrent")
        sys.exit(1)

    print()
    print("Test 2: Get torrent count")
    print("-" * 70)
    count = client.get_torrent_count()
    print(f"Torrents in queue: {count}")

    if count > 0:
        print()
        print("Test 3: List first 5 torrents")
        print("-" * 70)
        torrents = client.get_torrents()[:5]
        for i, torrent in enumerate(torrents, 1):
            print(f"{i}. {torrent.get('name', 'Unknown')[:60]} [{torrent.get('state', 'unknown')}]")

    print()
    print("=" * 70)
    print("All tests passed!")
    print("=" * 70)
