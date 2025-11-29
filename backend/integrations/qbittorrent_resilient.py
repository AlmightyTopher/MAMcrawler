"""
Resilient qBittorrent Client with VPN Health Checks and Fallback Support

Handles:
- VPN connectivity monitoring
- Automatic failover between primary and local instances
- Magnet link queueing when all services unavailable
- Detailed health status reporting
"""

import asyncio
import aiohttp
import logging
import re
import json
from typing import Optional, List, Dict, Tuple
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class VPNHealthChecker:
    """Monitor VPN connectivity status"""

    def __init__(self, gateway_ip: str = "192.168.0.1", timeout: int = 5):
        self.gateway_ip = gateway_ip
        self.timeout = timeout
        self.last_check = None
        self.is_connected = False

    async def check_vpn_connectivity(self) -> bool:
        """Check VPN gateway connectivity via ICMP ping"""
        try:
            # For Windows, use ping command
            import subprocess
            result = subprocess.run(
                ['ping', '-n', '1', '-w', str(self.timeout * 1000), self.gateway_ip],
                capture_output=True,
                text=True,
                timeout=self.timeout + 2
            )
            self.is_connected = result.returncode == 0
            self.last_check = datetime.now()
            return self.is_connected
        except Exception as e:
            logger.warning(f"VPN connectivity check failed: {e}")
            self.is_connected = False
            return False

    async def wait_for_vpn_reconnect(self, max_wait: int = 60) -> bool:
        """Wait for VPN to reconnect (with timeout)"""
        wait_interval = 2
        elapsed = 0

        while elapsed < max_wait:
            if await self.check_vpn_connectivity():
                logger.info(f"VPN reconnected after {elapsed}s")
                return True

            await asyncio.sleep(wait_interval)
            elapsed += wait_interval

        logger.warning(f"VPN did not reconnect within {max_wait}s")
        return False


class ResilientQBittorrentClient:
    """
    qBittorrent client with fallback support and VPN resilience

    Tries multiple instances in order:
    1. Primary (remote via VPN)
    2. Secondary (local fallback)
    3. Queue file (for manual addition later)
    """

    def __init__(
        self,
        primary_url: str,
        username: str,
        password: str,
        secondary_url: Optional[str] = None,
        queue_file: str = "qbittorrent_queue.json",
        savepath: Optional[str] = None
    ):
        self.primary_url = primary_url.rstrip("/")
        self.secondary_url = secondary_url.rstrip("/") if secondary_url else None
        self.username = username
        self.password = password
        self.queue_file = Path(queue_file)
        self.savepath = savepath

        self.vpn_checker = VPNHealthChecker()
        self.session: Optional[aiohttp.ClientSession] = None
        self._sid: Optional[str] = None
        self._authenticated = False
        self._current_url: Optional[str] = None

        # Health status
        self.health = {
            'primary': 'unknown',
            'secondary': 'unknown',
            'vpn_connected': None,
            'last_check': None,
            'active_instance': None
        }

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def perform_health_check(self) -> Dict[str, str]:
        """Check health of all available instances"""
        logger.info("Performing qBittorrent health check...")

        # Check VPN first
        self.health['vpn_connected'] = await self.vpn_checker.check_vpn_connectivity()
        self.health['last_check'] = datetime.now().isoformat()

        if not self.session:
            await self.__aenter__()

        # Check primary (remote via VPN)
        if self.health['vpn_connected']:
            self.health['primary'] = await self._check_endpoint(self.primary_url)
        else:
            self.health['primary'] = 'VPN_DOWN'

        # Check secondary (local)
        if self.secondary_url:
            self.health['secondary'] = await self._check_endpoint(self.secondary_url)
        else:
            self.health['secondary'] = 'NOT_CONFIGURED'

        logger.info(f"Health check results: {self.health}")
        return self.health

    async def _check_endpoint(self, url: str) -> str:
        """Check if endpoint is reachable and responding"""
        try:
            # First, try to login to get SID
            login_url = urljoin(url, "/api/v2/auth/login")
            login_data = aiohttp.FormData()
            login_data.add_field('username', self.username)
            login_data.add_field('password', self.password)

            sid = None
            async with self.session.post(login_url, data=login_data, ssl=False, timeout=5) as resp:
                if resp.status == 200:
                    auth_text = await resp.text()
                    if auth_text.strip() == 'Ok.':
                        # Extract SID
                        for header_name in resp.headers:
                            if header_name.lower() == 'set-cookie':
                                cookie_val = resp.headers[header_name]
                                match = re.search(r'SID=([^;]+)', cookie_val)
                                if match:
                                    sid = match.group(1)
                                    break

            if not sid:
                return "AUTH_FAILED"

            # Now check the API with authentication
            check_url = urljoin(url, "/api/v2/app/webapiVersion")
            headers = {'Cookie': f'SID={sid}'}
            async with self.session.get(check_url, headers=headers, ssl=False, timeout=5) as resp:
                if resp.status == 200:
                    return "OK"
                elif resp.status == 404:
                    return "HTTP_404"  # VPN down or wrong endpoint
                else:
                    return f"HTTP_{resp.status}"
        except asyncio.TimeoutError:
            return "TIMEOUT"
        except aiohttp.ClientError as e:
            return f"ERROR: {str(e)[:20]}"
        except Exception as e:
            return f"UNKNOWN: {str(e)[:20]}"

    async def add_torrents_with_fallback(
        self,
        magnet_links: List[str],
        max_retries: int = 3
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Add torrents with automatic fallback

        Returns:
            (successful_magnets, failed_magnets, queued_magnets)
        """
        successful = []
        failed = []
        queued = []

        if not self.session:
            await self.__aenter__()

        # Get health status
        health = await self.perform_health_check()

        # Determine which instance to use
        instance_urls = []

        if health['primary'] == 'OK':
            instance_urls.append(('primary', self.primary_url))
        elif health['primary'] == 'HTTP_404':
            logger.warning("Primary qBittorrent returning 404 (VPN issue?)")

        if self.secondary_url and health['secondary'] == 'OK':
            instance_urls.append(('secondary', self.secondary_url))

        # Try each magnet with each available instance
        for magnet in magnet_links:
            added = False

            for instance_name, instance_url in instance_urls:
                try:
                    logger.info(f"Attempting {instance_name} instance for magnet...")
                    result = await self._add_torrent_to_instance(instance_url, magnet, self.savepath)
                    if result:
                        successful.append(magnet)
                        logger.info(f"Successfully added via {instance_name}")
                        added = True
                        break
                except Exception as e:
                    logger.warning(f"{instance_name} failed: {e}")
                    continue

            # If all instances failed, queue for later
            if not added:
                logger.warning(f"All instances failed, queuing magnet")
                queued.append(magnet)

        # Save queued magnets to file
        if queued:
            await self._save_queue_file(queued)

        return successful, failed, queued

    async def _add_torrent_to_instance(self, url: str, magnet: str, savepath: Optional[str] = None) -> bool:
        """Add single torrent to specific instance"""
        try:
            # Authenticate
            login_url = urljoin(url, "/api/v2/auth/login")
            login_data = aiohttp.FormData()
            login_data.add_field('username', self.username)
            login_data.add_field('password', self.password)

            sid = None
            async with self.session.post(login_url, data=login_data, ssl=False) as resp:
                if resp.status != 200:
                    logger.warning(f"Authentication failed: HTTP {resp.status}")
                    return False

                auth_text = await resp.text()
                if auth_text.strip() != 'Ok.':
                    logger.warning(f"Authentication failed: {auth_text}")
                    return False

                # Extract SID
                for header_name in resp.headers:
                    if header_name.lower() == 'set-cookie':
                        cookie_val = resp.headers[header_name]
                        match = re.search(r'SID=([^;]+)', cookie_val)
                        if match:
                            sid = match.group(1)
                            break

            # Add torrent
            add_url = urljoin(url, "/api/v2/torrents/add")
            add_data = aiohttp.FormData()
            add_data.add_field('urls', magnet)
            add_data.add_field('paused', 'false')
            add_data.add_field('category', 'audiobooks')

            # Add savepath if provided
            if savepath:
                add_data.add_field('savepath', str(savepath))

            headers = {}
            if sid:
                headers['Cookie'] = f'SID={sid}'

            async with self.session.post(add_url, data=add_data, headers=headers, ssl=False) as resp:
                response_text = await resp.text()
                if resp.status == 200 and response_text.strip() == 'Ok.':
                    return True
                else:
                    logger.warning(f"Add torrent failed: HTTP {resp.status}")
                    return False

        except Exception as e:
            logger.error(f"Exception adding torrent: {e}")
            return False

    async def _save_queue_file(self, magnet_links: List[str]):
        """Save magnet links to queue file for manual addition"""
        try:
            queue_data = {
                'saved_at': datetime.now().isoformat(),
                'reason': 'VPN/qBittorrent unavailable',
                'magnets': magnet_links,
                'instructions': 'Manually add these to qBittorrent when available, or paste into web UI'
            }

            self.queue_file.write_text(json.dumps(queue_data, indent=2))
            logger.info(f"Saved {len(magnet_links)} magnets to queue file: {self.queue_file}")
        except Exception as e:
            logger.error(f"Failed to save queue file: {e}")

    async def process_queue_file(self) -> Tuple[List[str], List[str]]:
        """Process queued magnets that were previously saved"""
        if not self.queue_file.exists():
            return [], []

        try:
            queue_data = json.loads(self.queue_file.read_text())
            magnets = queue_data.get('magnets', [])

            logger.info(f"Processing {len(magnets)} queued magnets...")
            successful, failed, queued = await self.add_torrents_with_fallback(magnets)

            # Clean up file if all processed
            if not queued:
                self.queue_file.unlink()
                logger.info("Queue file processed and removed")

            return successful, failed
        except Exception as e:
            logger.error(f"Error processing queue file: {e}")
            return [], []


async def demo_resilient_client():
    """Demo usage of resilient client"""
    async with ResilientQBittorrentClient(
        primary_url="http://192.168.0.48:52095",
        secondary_url="http://localhost:52095",
        username="TopherGutbrod",
        password="Tesl@ismy#1"
    ) as client:
        # Perform health check
        health = await client.perform_health_check()
        print(f"Health check: {health}")

        # Try to add torrents
        test_magnets = [
            "magnet:?xt=urn:btih:test1&dn=Test+Book+1",
            "magnet:?xt=urn:btih:test2&dn=Test+Book+2",
        ]

        successful, failed, queued = await client.add_torrents_with_fallback(test_magnets)
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")
        print(f"Queued: {len(queued)}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(demo_resilient_client())
