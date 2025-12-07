"""
qBittorrent Diagnostic Module
Checks qBittorrent connectivity, queue status, and configuration
"""

import requests
import json
from typing import List, Dict, Any
from .base_diagnostic import BaseDiagnostic, DiagnosticResult


class QBittorrentDiagnostic(BaseDiagnostic):
    """qBittorrent diagnostic module"""

    def __init__(self):
        super().__init__("qbittorrent", "qBittorrent connectivity and queue diagnostics")

    def run_diagnostics(self) -> List[DiagnosticResult]:
        """Run qBittorrent diagnostics"""
        results = []

        # Check connectivity and authentication
        auth_result = self._check_authentication()
        results.append(auth_result)

        if auth_result.status == "OK":
            # Only run these if authentication works
            results.append(self._check_queue_status())
            results.append(self._check_audiobooks_category())
            results.append(self._check_server_state())
            results.append(self._analyze_torrent_health())
        else:
            # Add failed checks
            results.extend([
                self.add_result("queue_status", "ERROR", "Cannot check queue - authentication failed"),
                self.add_result("audiobooks_category", "ERROR", "Cannot check category - authentication failed"),
                self.add_result("server_state", "ERROR", "Cannot check server - authentication failed"),
                self.add_result("torrent_health", "ERROR", "Cannot analyze health - authentication failed")
            ])

        return results

    def _check_authentication(self) -> DiagnosticResult:
        """Check qBittorrent authentication"""
        qb_url = self.get_env_var('QBITTORRENT_URL', 'http://192.168.0.48:52095/')
        qb_user = self.get_env_var('QBITTORRENT_USERNAME')
        qb_pass = self.get_env_var('QBITTORRENT_PASSWORD')

        if not qb_url.endswith('/'):
            qb_url += '/'

        if not all([qb_user, qb_pass]):
            return self.add_result(
                "authentication",
                "ERROR",
                "qBittorrent credentials not configured",
                recommendations=[
                    "Set QBITTORRENT_URL, QBITTORRENT_USERNAME, QBITTORRENT_PASSWORD in .env",
                    "Check qBittorrent WebUI settings"
                ]
            )

        try:
            session = requests.Session()
            login_url = f"{qb_url}api/v2/auth/login"
            login_data = {
                'username': qb_user,
                'password': qb_pass
            }

            login_response = session.post(login_url, data=login_data, timeout=10)

            if login_response.status_code == 200:
                return self.add_result(
                    "authentication",
                    "OK",
                    "Successfully authenticated with qBittorrent",
                    {"url": qb_url}
                )
            else:
                return self.add_result(
                    "authentication",
                    "ERROR",
                    f"Authentication failed: HTTP {login_response.status_code}",
                    {"response": login_response.text[:200]},
                    recommendations=[
                        "Verify username and password",
                        "Check if qBittorrent WebUI is enabled",
                        "Verify URL and port configuration"
                    ]
                )
        except requests.exceptions.ConnectionError:
            return self.add_result(
                "authentication",
                "ERROR",
                f"Cannot connect to qBittorrent at {qb_url}",
                recommendations=[
                    "Check if qBittorrent is running",
                    "Verify QBITTORRENT_URL in .env",
                    "Check firewall settings"
                ]
            )
        except Exception as e:
            return self.add_result(
                "authentication",
                "ERROR",
                f"Authentication error: {e}"
            )

    def _check_queue_status(self) -> DiagnosticResult:
        """Check overall torrent queue status"""
        qb_url = self.get_env_var('QBITTORRENT_URL', 'http://192.168.0.48:52095/')
        qb_user = self.get_env_var('QBITTORRENT_USERNAME')
        qb_pass = self.get_env_var('QBITTORRENT_PASSWORD')

        try:
            session = requests.Session()
            # Login first
            login_url = f"{qb_url}api/v2/auth/login"
            session.post(login_url, data={'username': qb_user, 'password': qb_pass}, timeout=10)

            # Get all torrents
            torrents_url = f"{qb_url}api/v2/torrents/info"
            torrents_response = session.get(torrents_url, timeout=10)

            if torrents_response.status_code == 200:
                torrents = torrents_response.json()
                total_count = len(torrents)

                # Categorize torrents
                stats = {
                    'total': total_count,
                    'downloading': len([t for t in torrents if t.get('state') in ['downloading', 'allocating', 'checkingResumeData']]),
                    'completed': len([t for t in torrents if t.get('state') in ['uploading', 'forcedUP']]),
                    'paused': len([t for t in torrents if t.get('state') == 'pausedDL']),
                    'errors': len([t for t in torrents if t.get('state') in ['missingFiles', 'error']]),
                    'queued': len([t for t in torrents if t.get('state') in ['queuedDL', 'queuedUP']])
                }

                # Check for issues
                issues = []
                if stats['errors'] > 0:
                    issues.append(f"{stats['errors']} torrents with errors")
                if stats['paused'] > 10:  # Arbitrary threshold
                    issues.append(f"{stats['paused']} torrents paused")

                status = "OK" if stats['errors'] == 0 else "WARNING"
                message = f"Queue status: {stats['total']} total torrents"

                return self.add_result(
                    "queue_status",
                    status,
                    message,
                    {"stats": stats, "issues": issues},
                    recommendations=["Review errored torrents"] if issues else []
                )
            else:
                return self.add_result(
                    "queue_status",
                    "ERROR",
                    f"Failed to get queue status: HTTP {torrents_response.status_code}"
                )
        except Exception as e:
            return self.add_result(
                "queue_status",
                "ERROR",
                f"Queue check failed: {e}"
            )

    def _check_audiobooks_category(self) -> DiagnosticResult:
        """Check audiobooks category specifically"""
        qb_url = self.get_env_var('QBITTORRENT_URL', 'http://192.168.0.48:52095/')
        qb_user = self.get_env_var('QBITTORRENT_USERNAME')
        qb_pass = self.get_env_var('QBITTORRENT_PASSWORD')

        try:
            session = requests.Session()
            # Login first
            login_url = f"{qb_url}api/v2/auth/login"
            session.post(login_url, data={'username': qb_user, 'password': qb_pass}, timeout=10)

            # Get audiobooks category
            audiobooks_url = f"{qb_url}api/v2/torrents/info?category=audiobooks"
            audiobooks_response = session.get(audiobooks_url, timeout=10)

            if audiobooks_response.status_code == 200:
                audiobooks = audiobooks_response.json()
                count = len(audiobooks)

                if count > 0:
                    # Get some stats
                    states = {}
                    for book in audiobooks:
                        state = book.get('state', 'unknown')
                        states[state] = states.get(state, 0) + 1

                    return self.add_result(
                        "audiobooks_category",
                        "OK",
                        f"Audiobooks category: {count} torrents",
                        {"count": count, "states": states}
                    )
                else:
                    return self.add_result(
                        "audiobooks_category",
                        "WARNING",
                        "Audiobooks category exists but is empty",
                        recommendations=[
                            "Check if torrents are being added to correct category",
                            "Verify category name in scripts"
                        ]
                    )
            else:
                return self.add_result(
                    "audiobooks_category",
                    "WARNING",
                    f"Could not query audiobooks category: HTTP {audiobooks_response.status_code}",
                    recommendations=["Check if 'audiobooks' category exists in qBittorrent"]
                )
        except Exception as e:
            return self.add_result(
                "audiobooks_category",
                "ERROR",
                f"Audiobooks category check failed: {e}"
            )

    def _check_server_state(self) -> DiagnosticResult:
        """Check qBittorrent server state"""
        qb_url = self.get_env_var('QBITTORRENT_URL', 'http://192.168.0.48:52095/')
        qb_user = self.get_env_var('QBITTORRENT_USERNAME')
        qb_pass = self.get_env_var('QBITTORRENT_PASSWORD')

        try:
            session = requests.Session()
            # Login first
            login_url = f"{qb_url}api/v2/auth/login"
            session.post(login_url, data={'username': qb_user, 'password': qb_pass}, timeout=10)

            # Check server state via preferences
            prefs_url = f"{qb_url}api/v2/app/preferences"
            prefs_response = session.get(prefs_url, timeout=10)

            if prefs_response.status_code == 200:
                prefs = prefs_response.json()
                server_stats = {
                    "version": prefs.get("version", "unknown"),
                    "web_ui_enabled": prefs.get("web_ui", True),
                    "max_active_downloads": prefs.get("max_active_downloads", 0),
                    "max_active_uploads": prefs.get("max_active_uploads", 0),
                    "download_speed_limit": prefs.get("dl_speed_limit", 0),
                    "upload_speed_limit": prefs.get("up_speed_limit", 0)
                }

                return self.add_result(
                    "server_state",
                    "OK",
                    f"qBittorrent {server_stats['version']} is responsive",
                    {"server_stats": server_stats}
                )
            else:
                return self.add_result(
                    "server_state",
                    "ERROR",
                    f"Server state check failed: HTTP {prefs_response.status_code}"
                )
        except Exception as e:
            return self.add_result(
                "server_state",
                "ERROR",
                f"Server state check failed: {e}"
            )

    def _analyze_torrent_health(self) -> DiagnosticResult:
        """Analyze overall torrent health"""
        qb_url = self.get_env_var('QBITTORRENT_URL', 'http://192.168.0.48:52095/')
        qb_user = self.get_env_var('QBITTORRENT_USERNAME')
        qb_pass = self.get_env_var('QBITTORRENT_PASSWORD')

        try:
            session = requests.Session()
            # Login first
            login_url = f"{qb_url}api/v2/auth/login"
            session.post(login_url, data={'username': qb_user, 'password': qb_pass}, timeout=10)

            # Get all torrents for health analysis
            torrents_url = f"{qb_url}api/v2/torrents/info"
            torrents_response = session.get(torrents_url, timeout=10)

            if torrents_response.status_code == 200:
                torrents = torrents_response.json()

                # Analyze health
                health_stats = {
                    "total_torrents": len(torrents),
                    "healthy": 0,
                    "stalled": 0,
                    "errored": 0,
                    "low_ratio": 0
                }

                issues = []

                for torrent in torrents:
                    state = torrent.get('state', '')
                    ratio = torrent.get('ratio', 0)

                    if state in ['missingFiles', 'error']:
                        health_stats["errored"] += 1
                        issues.append(f"Errored: {torrent.get('name', 'Unknown')}")
                    elif state in ['stalledDL', 'stalledUP']:
                        health_stats["stalled"] += 1
                    elif ratio < 1.0 and state in ['uploading', 'forcedUP']:
                        health_stats["low_ratio"] += 1
                    else:
                        health_stats["healthy"] += 1

                # Determine overall health
                if health_stats["errored"] > 0:
                    status = "ERROR"
                    message = f"Torrent health issues: {health_stats['errored']} errored, {health_stats['stalled']} stalled"
                elif health_stats["stalled"] > 5:  # Arbitrary threshold
                    status = "WARNING"
                    message = f"Torrent health warning: {health_stats['stalled']} stalled torrents"
                else:
                    status = "OK"
                    message = f"Torrent health good: {health_stats['healthy']} healthy torrents"

                return self.add_result(
                    "torrent_health",
                    status,
                    message,
                    {"health_stats": health_stats, "issues": issues[:10]},  # Limit issues shown
                    recommendations=[
                        "Review and fix errored torrents",
                        "Check stalled downloads",
                        "Monitor upload ratios"
                    ] if status != "OK" else []
                )
            else:
                return self.add_result(
                    "torrent_health",
                    "ERROR",
                    f"Health analysis failed: HTTP {torrents_response.status_code}"
                )
        except Exception as e:
            return self.add_result(
                "torrent_health",
                "ERROR",
                f"Health analysis failed: {e}"
            )