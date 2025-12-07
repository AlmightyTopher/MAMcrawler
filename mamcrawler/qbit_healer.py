import logging
import os
import time
from typing import Dict, List, Optional
from dotenv import load_dotenv

try:
    import qbittorrentapi
except ImportError:
    qbittorrentapi = None

logger = logging.getLogger(__name__)

class QBitHealer:
    """
    Diagnoses and fixes common qBittorrent connectivity and stalling issues.
    """

    def __init__(self, host: str = None, port: int = None, username: str = None, password: str = None):
        load_dotenv()
        self.host = host or os.getenv('QB_HOST', 'http://localhost')
        self.port = port or os.getenv('QB_PORT', '8080')
        self.username = username or os.getenv('QB_USERNAME', 'admin')
        self.password = password or os.getenv('QB_PASSWORD', '')
        
        # Normalize host
        if not self.host.startswith('http'):
            self.host = f'http://{self.host}'
        if str(self.port) not in self.host:
            self.host = f"{self.host}:{self.port}"
            
        self.client = None

    def connect(self) -> bool:
        """Establish connection to qBittorrent."""
        if not qbittorrentapi:
            logger.error("qbittorrentapi not installed")
            return False
            
        try:
            self.client = qbittorrentapi.Client(
                host=self.host,
                username=self.username,
                password=self.password
            )
            self.client.auth_log_in()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to qBittorrent: {e}")
            return False

    def diagnose_and_heal(self) -> Dict[str, bool]:
        """
        Run full diagnosis and attempt repairs.
        Returns a dict of what was fixed.
        """
        results = {
            "connection_fixed": False,
            "binding_reset": False,
            "trackers_fixed": False,
            "torrents_resumed": False
        }

        if not self.connect():
            logger.error("Cannot heal qBittorrent: Connection failed")
            return results

        logger.info("Running qBittorrent diagnosis...")

        # 1. Check Network Binding
        if self._check_binding_issue():
            logger.warning("⚠️ Detected network binding issue. Attempting fix...")
            if self._fix_binding():
                results["binding_reset"] = True
                logger.info("✓ Network binding reset to ANY")

        # 2. Check Stalled Torrents & Trackers
        stalled = self.client.torrents_info(status_filter='stalled_downloading')
        if stalled:
            logger.warning(f"⚠️ Found {len(stalled)} stalled downloads. Checking trackers...")
            if self._fix_trackers(stalled):
                results["trackers_fixed"] = True
                logger.info("✓ Trackers re-announced")

        return results

    def _check_binding_issue(self) -> bool:
        """Check if qBit is bound to a specific interface that might be dead."""
        try:
            prefs = self.client.app.preferences
            interface = prefs.get('current_network_interface', '')
            # If bound to a specific interface (not empty/any), it's a risk
            if interface and interface != '':
                # We can't easily check if the interface is valid from here, 
                # but if we are running this, it's likely because things are broken.
                # A safe heuristic: if we have stalled torrents and a specific binding, assume it's the culprit.
                stalled = self.client.torrents_info(status_filter='stalled_downloading')
                return len(stalled) > 0
            return False
        except Exception:
            return False

    def _fix_binding(self) -> bool:
        """Reset network binding to listen on all interfaces."""
        try:
            self.client.app.set_preferences({
                'current_network_interface': '',
                'current_interface_address': ''
            })
            return True
        except Exception as e:
            logger.error(f"Failed to reset binding: {e}")
            return False

    def _fix_trackers(self, torrents: List) -> bool:
        """Force re-announce for torrents with non-working trackers."""
        fixed = False
        hashes_to_reannounce = []

        for t in torrents:
            trackers = self.client.torrents_trackers(t.hash)
            needs_fix = False
            for tr in trackers:
                # Status 1 (Not Contacted) or 0 (Disabled) or error messages
                if tr.status != 2: 
                    needs_fix = True
                    break
            
            if needs_fix:
                hashes_to_reannounce.append(t.hash)

        if hashes_to_reannounce:
            try:
                self.client.torrents_reannounce(torrent_hashes=hashes_to_reannounce)
                fixed = True
            except Exception as e:
                logger.error(f"Failed to re-announce: {e}")

        return fixed
